# Odds Premium Engine (Python + Supabase)

Backend em Python para um site premium de análise de apostas esportivas reais, com dados atuais, armazenamento integral no Supabase, automação de 30 segundos, fila, lock, logs e publicação para um frontend Next.js + TypeScript.

## O que este projeto entrega

- Coleta de eventos reais, odds reais e estatísticas reais.
- Pipeline com 4 agentes:
  - Coletor
  - Analista
  - Publicador
  - Otimizador
- Persistência total no Supabase.
- Logs completos de agentes e APIs.
- Controle de lock para evitar execução duplicada.
- Retry automático nas chamadas externas.
- Rotas prontas para o frontend consumir.
- Estrutura preparada para uso com Supabase Realtime no frontend.
- Uso do OpenRouter apenas no backend para explicações textuais.

## Observação importante sobre a arquitetura

Você pediu stack com **Next.js + TypeScript no frontend**, mas também pediu **código em Python**. Então este pacote entrega o **núcleo backend em Python**, que é a parte crítica de coleta, análise, publicação, cron e otimização. O frontend Next.js pode consumir as rotas deste serviço e/ou assinar o Realtime do Supabase.

Se você quiser a continuação, a próxima etapa é gerar o frontend premium em Next.js/Tailwind em cima destas rotas e tabelas.

## Estrutura

```text
app/
  api/
  agents/
  clients/
  core/
  models/
  repositories/
  services/
  utils/
db/
  schema.sql
scripts/
  generate_project.py
```

## Variáveis de ambiente

Copie `.env.example` para `.env`.

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Fluxo do pipeline

1. `/internal/pipeline/run` dispara o pipeline.
2. O lock global impede duplicação.
3. O Coletor busca dados reais em provedores confiáveis.
4. O Analista calcula recomendações apenas com dados reais.
5. O Publicador publica no Supabase.
6. O Otimizador recalibra estratégias com base no histórico.

## Como agendar a cada 30 segundos

### Opção A — serviço Python sempre ativo
Use `ENABLE_LOCAL_SCHEDULER=true` para rodar APScheduler localmente a cada 30 segundos.

### Opção B — Supabase Cron
Use o SQL em `db/schema.sql` para criar a função/lock e depois agende um webhook ou Edge Function que chame `POST /internal/pipeline/run` a cada 30 segundos.

## Rotas principais

- `GET /health`
- `POST /internal/pipeline/run`
- `GET /api/v1/recommendations?segment=live&sport=soccer`
- `GET /api/v1/history?status=won`
- `GET /api/v1/admin/status`
- `GET /api/v1/admin/logs?limit=100`

## Regras de integridade

- Nunca publica evento sem `starts_at` futuro ou status ao vivo válido.
- Nunca trata evento antigo como atual.
- Nunca usa odds mockadas.
- Se uma API falhar, o sistema registra em `api_logs` e segue no próximo ciclo.

## Frontend recomendado

- Next.js App Router
- Tailwind CSS
- Supabase Realtime para `recommendations`, `events`, `prediction_results`
- Polling de 30s como fallback

## Produção

- Coloque este serviço atrás de um reverse proxy.
- Mantenha `SUPABASE_SERVICE_ROLE_KEY` apenas no backend.
- Proteja `/internal/pipeline/run` com `INTERNAL_CRON_TOKEN`.
- Use observabilidade externa além dos logs do banco.


## O que já está coberto no backend

- liquidação básica de resultados para futebol, NBA e tênis quando o provedor retorna placar/estatísticas finais;
- atualização do status da recomendação (`open`, `won`, `lost`, `void`);
- agregação de performance por estratégia em `strategies`.
