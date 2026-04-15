from pathlib import Path

root = Path('/mnt/data/odds-premium-python')

# Add result evaluator
(root / 'app/services/result_evaluator.py').write_text('''from __future__ import annotations

from typing import Any


class ResultEvaluator:
    def evaluate(self, recommendation: dict[str, Any], event_payload: dict[str, Any], stats_payload: dict[str, Any]) -> dict[str, Any] | None:
        label = str(recommendation.get('recommendation_label', ''))
        strategy = str(recommendation.get('strategy_code', ''))
        sport = str(recommendation.get('sport_slug', ''))
        event_status = str(event_payload.get('status', '')).lower()

        if event_status not in {'finished', 'final', 'ended', 'completed'} and not stats_payload.get('is_final'):
            return None

        if sport == 'soccer' and 'Mais de 1.5 gols' in label:
            total_goals = self._score_total(stats_payload)
            if total_goals is None:
                return None
            return self._build_result(total_goals > 1.5, {'total_goals': total_goals})

        if sport == 'soccer' and 'Mais de 2.5 gols' in label:
            total_goals = self._score_total(stats_payload)
            if total_goals is None:
                return None
            return self._build_result(total_goals > 2.5, {'total_goals': total_goals})

        if sport == 'nba' and '20+ pontos' in label:
            player_name = label.replace(' 20+ pontos', '').strip()
            player_points = self._player_points(stats_payload, player_name)
            if player_points is None:
                return None
            return self._build_result(player_points >= 20, {'player_name': player_name, 'player_points': player_points})

        if sport == 'tennis' and strategy.startswith('tennis_moneyline'):
            player_name = label.replace('Vitória de', '').strip()
            winner = self._winner_name(stats_payload)
            if not winner:
                return None
            return self._build_result(winner.lower() == player_name.lower(), {'winner': winner})

        return None

    @staticmethod
    def _build_result(won: bool, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            'result_status': 'won' if won else 'lost',
            'roi': 1.0 if won else -1.0,
            'payload': payload,
        }

    @staticmethod
    def _score_total(stats_payload: dict[str, Any]) -> int | None:
        score = stats_payload.get('score') or stats_payload.get('scores') or {}
        home = score.get('home') if isinstance(score, dict) else None
        away = score.get('away') if isinstance(score, dict) else None
        if home is None or away is None:
            home = stats_payload.get('home_score')
            away = stats_payload.get('away_score')
        if home is None or away is None:
            return None
        return int(home) + int(away)

    @staticmethod
    def _player_points(stats_payload: dict[str, Any], player_name: str) -> int | None:
        for player in stats_payload.get('players', []):
            if str(player.get('name', '')).lower() == player_name.lower():
                value = player.get('points') or player.get('pts')
                return int(value) if value is not None else None
        return None

    @staticmethod
    def _winner_name(stats_payload: dict[str, Any]) -> str | None:
        winner = stats_payload.get('winner_name') or stats_payload.get('winner')
        if winner:
            return str(winner)
        for player in stats_payload.get('players', []):
            if player.get('is_winner'):
                return str(player.get('name'))
        return None
''', encoding='utf-8')

# Patch repository
repo_path = root / 'app/repositories/supabase_repo.py'
repo = repo_path.read_text(encoding='utf-8')
repo = repo.replace(
"""    def run_optimizer(self) -> int:\n        response = self.client.rpc('refresh_strategy_metrics').execute()\n        return int(response.data or 0)\n""",
"""    def list_open_recommendations(self, limit: int = 200) -> list[dict[str, Any]]:\n        return (\n            self.client.table('recommendations')\n            .select('*, events(*)')\n            .eq('status', 'open')\n            .order('published_at', desc=False)\n            .limit(limit)\n            .execute()\n            .data\n            or []\n        )\n\n    def save_prediction_result(self, recommendation_id: str, event_external_id: str, result_status: str, roi: float, payload: dict[str, Any]) -> None:\n        self.client.table('prediction_results').upsert(\n            [\n                {\n                    'recommendation_id': recommendation_id,\n                    'event_external_id': event_external_id,\n                    'result_status': result_status,\n                    'roi': roi,\n                    'payload': payload,\n                    'settled_at': utcnow().isoformat(),\n                }\n            ],\n            on_conflict='recommendation_id',\n        ).execute()\n        self.client.table('recommendations').update(\n            {'status': result_status, 'updated_at': utcnow().isoformat()}\n        ).eq('id', recommendation_id).execute()\n\n    def run_optimizer(self) -> int:\n        response = self.client.rpc('refresh_strategy_metrics').execute()\n        return int(response.data or 0)\n""")
repo_path.write_text(repo, encoding='utf-8')

# Patch collector for api logs
collector_path = root / 'app/agents/collector.py'
collector = collector_path.read_text(encoding='utf-8')
collector = collector.replace(
"""                raw_events = self.sports_data.collect_domain_events(sport=sport)\n                grouped_odds = self.odds_api.fetch_grouped_odds(domain_sport=sport)\n""",
"""                raw_events = self.sports_data.collect_domain_events(sport=sport)\n                self.repo.insert_api_log('sports_data', f'/events/*?sport={sport}', 'success', payload={'count': len(raw_events)})\n                grouped_odds = self.odds_api.fetch_grouped_odds(domain_sport=sport)\n                self.repo.insert_api_log('the_odds_api', f'/v4/sports/*/odds?sport={sport}', 'success', payload={'event_count_with_odds': len(grouped_odds)})\n""")
collector = collector.replace(
"""                logger.exception('Falha no coletor para %s', sport)\n                self.repo.insert_agent_log(self.name, 'error', f'Falha no coletor para {sport}', {'error': str(exc), 'sport': sport})\n""",
"""                logger.exception('Falha no coletor para %s', sport)\n                self.repo.insert_api_log('collector', sport, 'error', payload={'error': str(exc)})\n                self.repo.insert_agent_log(self.name, 'error', f'Falha no coletor para {sport}', {'error': str(exc), 'sport': sport})\n""")
collector_path.write_text(collector, encoding='utf-8')

# Patch optimizer
optimizer_path = root / 'app/agents/optimizer.py'
optimizer_path.write_text('''from __future__ import annotations\n\nfrom app.repositories.supabase_repo import SupabaseRepository\nfrom app.services.result_evaluator import ResultEvaluator\n\n\nclass OptimizerAgent:\n    name = 'optimizer'\n\n    def __init__(self, repo: SupabaseRepository | None = None) -> None:\n        self.repo = repo or SupabaseRepository()\n        self.evaluator = ResultEvaluator()\n\n    def run(self) -> int:\n        settled = 0\n        open_recommendations = self.repo.list_open_recommendations(limit=200)\n        for recommendation in open_recommendations:\n            event_payload = recommendation.get('events') or {}\n            stats_response = self.repo.get_event_bundle(recommendation['event_external_id']) or {}\n            stats_payload = stats_response.get('stats') or {}\n            result = self.evaluator.evaluate(recommendation, event_payload, stats_payload)\n            if not result:\n                continue\n            self.repo.save_prediction_result(\n                recommendation_id=recommendation['id'],\n                event_external_id=recommendation['event_external_id'],\n                result_status=result['result_status'],\n                roi=result['roi'],\n                payload=result['payload'],\n            )\n            settled += 1\n\n        optimized = self.repo.run_optimizer()\n        self.repo.insert_agent_log(self.name, 'info', 'Otimização concluída', {'optimized': optimized, 'settled': settled})\n        return optimized\n''', encoding='utf-8')

# Patch SQL for unique prediction_results and lock correctness
sql_path = root / 'db/schema.sql'
sql = sql_path.read_text(encoding='utf-8')
sql = sql.replace(
"""create table if not exists prediction_results (\n  id uuid primary key default gen_random_uuid(),\n  recommendation_id uuid references recommendations(id) on delete set null,\n""",
"""create table if not exists prediction_results (\n  id uuid primary key default gen_random_uuid(),\n  recommendation_id uuid unique references recommendations(id) on delete set null,\n"""
)
sql = sql.replace(
"""create or replace function acquire_job_lock(p_job_name text, p_ttl_seconds integer)\nreturns boolean\nlanguage plpgsql\nsecurity definer\nas $$\ndeclare\n  v_acquired boolean := false;\nbegin\n  insert into agent_locks(job_name, locked_until, updated_at)\n  values (p_job_name, now() + make_interval(secs => p_ttl_seconds), now())\n  on conflict (job_name)\n  do update set\n    locked_until = excluded.locked_until,\n    updated_at = now()\n  where agent_locks.locked_until < now();\n\n  select locked_until > now() into v_acquired\n  from agent_locks\n  where job_name = p_job_name;\n\n  return coalesce(v_acquired, false);\nend;\n$$;\n""",
"""create or replace function acquire_job_lock(p_job_name text, p_ttl_seconds integer)\nreturns boolean\nlanguage plpgsql\nsecurity definer\nas $$\ndeclare\n  v_now timestamptz := now();\nbegin\n  insert into agent_locks(job_name, locked_until, updated_at)\n  values (p_job_name, v_now + make_interval(secs => p_ttl_seconds), v_now)\n  on conflict do nothing;\n\n  if found then\n    return true;\n  end if;\n\n  update agent_locks\n     set locked_until = v_now + make_interval(secs => p_ttl_seconds),\n         updated_at = v_now\n   where job_name = p_job_name\n     and locked_until < v_now;\n\n  return found;\nend;\n$$;\n"""
)
sql_path.write_text(sql, encoding='utf-8')

# Add note to README
readme_path = root / 'README.md'
readme = readme_path.read_text(encoding='utf-8')
readme += '\n\n## O que já está coberto no backend\n\n- liquidação básica de resultados para futebol, NBA e tênis quando o provedor retorna placar/estatísticas finais;\n- atualização do status da recomendação (`open`, `won`, `lost`, `void`);\n- agregação de performance por estratégia em `strategies`.\n'
readme_path.write_text(readme, encoding='utf-8')

print('Patched project successfully')
