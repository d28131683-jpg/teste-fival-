-- Extensões recomendadas
create extension if not exists pg_cron;
create extension if not exists pg_net;
create extension if not exists pgcrypto;

-- Tabelas obrigatórias
create table if not exists sports (
  id uuid primary key default gen_random_uuid(),
  slug text unique not null,
  name text not null,
  created_at timestamptz not null default now()
);

create table if not exists competitions (
  id uuid primary key default gen_random_uuid(),
  external_id text unique not null,
  sport_slug text not null references sports(slug),
  name text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists events (
  id uuid primary key default gen_random_uuid(),
  external_id text unique not null,
  sport_slug text not null references sports(slug),
  competition_external_id text not null references competitions(external_id),
  home_team_external_id text,
  away_team_external_id text,
  home_team_name text not null,
  away_team_name text not null,
  starts_at timestamptz not null,
  status text not null,
  segment text not null check (segment in ('live', 'day', 'week')),
  is_live boolean not null default false,
  raw_payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists teams (
  id uuid primary key default gen_random_uuid(),
  external_id text unique not null,
  sport_slug text not null references sports(slug),
  name text not null,
  short_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists players (
  id uuid primary key default gen_random_uuid(),
  external_id text unique not null,
  sport_slug text not null references sports(slug),
  team_external_id text,
  name text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists odds (
  id uuid primary key default gen_random_uuid(),
  event_external_id text not null references events(external_id) on delete cascade,
  market_key text not null,
  market_name text not null,
  selection_name text not null,
  price numeric(12,4) not null,
  line numeric(12,4),
  bookmaker text,
  source_last_update timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (event_external_id, market_key, selection_name, bookmaker, line)
);

create table if not exists recommendations (
  id uuid primary key default gen_random_uuid(),
  event_external_id text not null references events(external_id) on delete cascade,
  sport_slug text not null references sports(slug),
  segment text not null check (segment in ('live', 'day', 'week')),
  strategy_code text not null,
  market_key text not null,
  recommendation_label text not null,
  odds_value numeric(12,4) not null,
  confidence_score numeric(6,4) not null,
  hit_rate numeric(6,4) not null,
  explanation text not null,
  inputs jsonb not null default '{}'::jsonb,
  status text not null default 'open' check (status in ('open', 'won', 'lost', 'void')),
  published_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (event_external_id, strategy_code, recommendation_label)
);

create table if not exists prediction_results (
  id uuid primary key default gen_random_uuid(),
  recommendation_id uuid unique references recommendations(id) on delete set null,
  event_external_id text not null references events(external_id) on delete cascade,
  result_status text not null check (result_status in ('won', 'lost', 'open', 'void')),
  settled_at timestamptz,
  roi numeric(12,4),
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists strategies (
  id uuid primary key default gen_random_uuid(),
  code text unique not null,
  sport_slug text not null references sports(slug),
  name text not null,
  description text,
  is_active boolean not null default true,
  win_rate numeric(6,4) not null default 0,
  roi numeric(12,4) not null default 0,
  sample_size integer not null default 0,
  config jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists agent_logs (
  id bigserial primary key,
  agent_name text not null,
  level text not null,
  message text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists api_logs (
  id bigserial primary key,
  provider text not null,
  endpoint text not null,
  status text not null,
  latency_ms integer,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  email text unique,
  role text default 'viewer',
  created_at timestamptz not null default now()
);

-- Tabelas auxiliares de operação
create table if not exists analysis_queue (
  id bigserial primary key,
  event_external_id text unique not null references events(external_id) on delete cascade,
  status text not null default 'pending' check (status in ('pending', 'processing', 'done', 'failed')),
  attempts integer not null default 0,
  last_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists agent_locks (
  job_name text primary key,
  locked_until timestamptz not null,
  updated_at timestamptz not null default now()
);

create table if not exists event_stats_cache (
  id uuid primary key default gen_random_uuid(),
  event_external_id text unique not null references events(external_id) on delete cascade,
  sport_slug text not null references sports(slug),
  payload jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

-- Funções de lock
create or replace function acquire_job_lock(p_job_name text, p_ttl_seconds integer)
returns boolean
language plpgsql
security definer
as $$
declare
  v_now timestamptz := now();
begin
  insert into agent_locks(job_name, locked_until, updated_at)
  values (p_job_name, v_now + make_interval(secs => p_ttl_seconds), v_now)
  on conflict do nothing;

  if found then
    return true;
  end if;

  update agent_locks
     set locked_until = v_now + make_interval(secs => p_ttl_seconds),
         updated_at = v_now
   where job_name = p_job_name
     and locked_until < v_now;

  return found;
end;
$$;

create or replace function release_job_lock(p_job_name text)
returns void
language sql
security definer
as $$
  delete from agent_locks where job_name = p_job_name;
$$;

-- Função para consumir fila
create or replace function dequeue_analysis_queue(p_limit integer)
returns table(event_external_id text)
language plpgsql
security definer
as $$
begin
  return query
  with picked as (
    select q.event_external_id
    from analysis_queue q
    where q.status in ('pending', 'failed')
    order by q.updated_at asc, q.created_at asc
    limit p_limit
    for update skip locked
  )
  update analysis_queue q
     set status = 'processing',
         attempts = q.attempts + 1,
         updated_at = now()
    from picked
   where q.event_external_id = picked.event_external_id
  returning q.event_external_id;
end;
$$;

-- Snapshot de forma recente
create or replace function get_event_form_snapshot(p_event_external_id text)
returns jsonb
language sql
security definer
as $$
  with event_base as (
    select * from events where external_id = p_event_external_id
  )
  select jsonb_build_object(
    'recent_form', coalesce((select esc.payload -> 'recent_form' from event_stats_cache esc where esc.event_external_id = p_event_external_id), '{}'::jsonb),
    'players', coalesce((select esc.payload -> 'players' from event_stats_cache esc where esc.event_external_id = p_event_external_id), '[]'::jsonb)
  );
$$;

-- Atualiza performance agregada das estratégias
create or replace function refresh_strategy_metrics()
returns integer
language plpgsql
security definer
as $$
declare
  v_count integer := 0;
begin
  with strategy_rollup as (
    select
      r.strategy_code,
      r.sport_slug,
      count(pr.id)::int as sample_size,
      coalesce(avg(case when pr.result_status = 'won' then 1.0 when pr.result_status = 'lost' then 0.0 else null end), 0) as win_rate,
      coalesce(sum(pr.roi), 0) as roi
    from recommendations r
    left join prediction_results pr on pr.recommendation_id = r.id
    group by r.strategy_code, r.sport_slug
  )
  insert into strategies(code, sport_slug, name, description, sample_size, win_rate, roi, updated_at)
  select
    strategy_code,
    sport_slug,
    strategy_code,
    'Atualizado automaticamente pelo agente otimizador',
    sample_size,
    win_rate,
    roi,
    now()
  from strategy_rollup
  on conflict (code)
  do update set
    sport_slug = excluded.sport_slug,
    sample_size = excluded.sample_size,
    win_rate = excluded.win_rate,
    roi = excluded.roi,
    updated_at = now();

  get diagnostics v_count = row_count;
  return v_count;
end;
$$;

-- Exemplo opcional de agendamento HTTP a cada 30s com pg_net
-- Ajuste URL e token antes de usar.
-- select cron.schedule(
--   'sports-pipeline-every-30s',
--   '30 seconds',
--   $$
--   select net.http_post(
--     url := 'https://seu-backend.com/internal/pipeline/run',
--     headers := jsonb_build_object('x-internal-token', 'SEU_TOKEN_INTERNO')
--   );
--   $$
-- );
