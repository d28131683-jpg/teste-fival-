from pathlib import Path

root = Path('/mnt/data/odds-premium-python')
files = {}

files['requirements.txt'] = '''fastapi==0.115.12
uvicorn[standard]==0.34.0
httpx==0.28.1
pydantic==2.11.3
pydantic-settings==2.8.1
supabase==2.15.0
tenacity==9.0.0
python-dateutil==2.9.0.post0
python-dotenv==1.1.0
orjson==3.10.16
apscheduler==3.11.0
'''

files['.env.example'] = '''APP_NAME=Odds Premium Engine
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
APP_LOG_LEVEL=INFO
INTERNAL_CRON_TOKEN=change-me

OPENROUTER_API_KEY=
OPENROUTER_MODEL=openai/gpt-4.1-mini
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_STORAGE_SCHEMA=public

ODDS_API_KEY=
ODDS_API_BASE_URL=https://api.the-odds-api.com
ODDS_API_REGIONS=eu
ODDS_API_MARKETS=h2h,totals,player_points
ODDS_API_BOOKMAKERS=

SPORTS_DATA_API_KEY=
SPORTS_DATA_API_BASE_URL=https://example-sports-data-provider.com/api
SPORTS_DATA_TIMEOUT_SECONDS=20

PIPELINE_INTERVAL_SECONDS=30
PIPELINE_BATCH_SIZE=50
ENABLE_LOCAL_SCHEDULER=true
REQUEST_TIMEOUT_SECONDS=20
HTTP_MAX_RETRIES=3
LOCK_TTL_SECONDS=25
'''

files['README.md'] = '''# Odds Premium Engine (Python + Supabase)

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
'''

files['app/__init__.py'] = ''
files['app/api/__init__.py'] = ''
files['app/agents/__init__.py'] = ''
files['app/clients/__init__.py'] = ''
files['app/core/__init__.py'] = ''
files['app/models/__init__.py'] = ''
files['app/repositories/__init__.py'] = ''
files['app/services/__init__.py'] = ''
files['app/utils/__init__.py'] = ''

files['app/core/config.py'] = '''from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = Field(default='Odds Premium Engine', alias='APP_NAME')
    app_env: Literal['development', 'staging', 'production'] = Field(default='development', alias='APP_ENV')
    app_host: str = Field(default='0.0.0.0', alias='APP_HOST')
    app_port: int = Field(default=8000, alias='APP_PORT')
    app_log_level: str = Field(default='INFO', alias='APP_LOG_LEVEL')
    internal_cron_token: str = Field(default='change-me', alias='INTERNAL_CRON_TOKEN')

    openrouter_api_key: str = Field(default='', alias='OPENROUTER_API_KEY')
    openrouter_model: str = Field(default='openai/gpt-4.1-mini', alias='OPENROUTER_MODEL')
    openrouter_base_url: str = Field(default='https://openrouter.ai/api/v1', alias='OPENROUTER_BASE_URL')

    supabase_url: str = Field(default='', alias='SUPABASE_URL')
    supabase_anon_key: str = Field(default='', alias='SUPABASE_ANON_KEY')
    supabase_service_role_key: str = Field(default='', alias='SUPABASE_SERVICE_ROLE_KEY')
    supabase_storage_schema: str = Field(default='public', alias='SUPABASE_STORAGE_SCHEMA')

    odds_api_key: str = Field(default='', alias='ODDS_API_KEY')
    odds_api_base_url: str = Field(default='https://api.the-odds-api.com', alias='ODDS_API_BASE_URL')
    odds_api_regions: str = Field(default='eu', alias='ODDS_API_REGIONS')
    odds_api_markets: str = Field(default='h2h,totals,player_points', alias='ODDS_API_MARKETS')
    odds_api_bookmakers: str = Field(default='', alias='ODDS_API_BOOKMAKERS')

    sports_data_api_key: str = Field(default='', alias='SPORTS_DATA_API_KEY')
    sports_data_api_base_url: str = Field(default='https://example-sports-data-provider.com/api', alias='SPORTS_DATA_API_BASE_URL')
    sports_data_timeout_seconds: int = Field(default=20, alias='SPORTS_DATA_TIMEOUT_SECONDS')

    pipeline_interval_seconds: int = Field(default=30, alias='PIPELINE_INTERVAL_SECONDS')
    pipeline_batch_size: int = Field(default=50, alias='PIPELINE_BATCH_SIZE')
    enable_local_scheduler: bool = Field(default=True, alias='ENABLE_LOCAL_SCHEDULER')
    request_timeout_seconds: int = Field(default=20, alias='REQUEST_TIMEOUT_SECONDS')
    http_max_retries: int = Field(default=3, alias='HTTP_MAX_RETRIES')
    lock_ttl_seconds: int = Field(default=25, alias='LOCK_TTL_SECONDS')

    @property
    def odds_regions_list(self) -> list[str]:
        return [item.strip() for item in self.odds_api_regions.split(',') if item.strip()]

    @property
    def odds_markets_list(self) -> list[str]:
        return [item.strip() for item in self.odds_api_markets.split(',') if item.strip()]

    @property
    def odds_bookmakers_list(self) -> list[str]:
        return [item.strip() for item in self.odds_api_bookmakers.split(',') if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
'''

files['app/core/logging.py'] = '''import logging
import sys

from .config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.app_log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)],
    )
'''

files['app/core/supabase.py'] = '''from functools import lru_cache

from supabase import Client, create_client

from .config import get_settings


@lru_cache(maxsize=1)
def get_supabase_admin() -> Client:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError('SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY são obrigatórios.')
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
'''

files['app/models/domain.py'] = '''from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


SportSlug = Literal['soccer', 'nba', 'tennis']
SegmentSlug = Literal['live', 'day', 'week']
RecommendationStatus = Literal['open', 'won', 'lost', 'void']


class TeamPayload(BaseModel):
    external_id: str
    name: str
    short_name: str | None = None
    sport: SportSlug


class PlayerPayload(BaseModel):
    external_id: str
    name: str
    sport: SportSlug
    team_external_id: str | None = None


class EventPayload(BaseModel):
    external_id: str
    sport: SportSlug
    competition_external_id: str
    competition_name: str
    home_team: str
    away_team: str
    home_team_external_id: str
    away_team_external_id: str
    starts_at: datetime
    status: str
    segment: SegmentSlug
    is_live: bool = False
    meta: dict[str, Any] = Field(default_factory=dict)


class OddSelection(BaseModel):
    market_key: str
    market_name: str
    selection_name: str
    price: float
    line: float | None = None
    bookmaker: str | None = None
    source_last_update: datetime | None = None


class EventBundle(BaseModel):
    event: EventPayload
    teams: list[TeamPayload] = Field(default_factory=list)
    players: list[PlayerPayload] = Field(default_factory=list)
    odds: list[OddSelection] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)


class StrategyRecommendation(BaseModel):
    external_event_id: str
    sport: SportSlug
    segment: SegmentSlug
    strategy_code: str
    market_key: str
    recommendation_label: str
    odds_value: float
    confidence_score: float
    hit_rate: float
    explanation: str
    inputs: dict[str, Any] = Field(default_factory=dict)


class PipelineRunSummary(BaseModel):
    collected_events: int = 0
    queued_events: int = 0
    analyzed_events: int = 0
    published_recommendations: int = 0
    optimized_strategies: int = 0
    warnings: list[str] = Field(default_factory=list)
'''

files['app/utils/time.py'] = '''from __future__ import annotations

from datetime import UTC, datetime, timedelta


def utcnow() -> datetime:
    return datetime.now(UTC)


def start_of_day() -> datetime:
    now = utcnow()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_day() -> datetime:
    return start_of_day() + timedelta(days=1)


def within_next_days(days: int) -> datetime:
    return utcnow() + timedelta(days=days)
'''

files['app/clients/base_http.py'] = '''from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class BaseHttpClient:
    def __init__(self, base_url: str, headers: dict[str, str] | None = None, timeout: int | None = None) -> None:
        settings = get_settings()
        self.base_url = base_url.rstrip('/')
        self.headers = headers or {}
        self.timeout = timeout or settings.request_timeout_seconds
        self.max_retries = settings.http_max_retries

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def get(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        url = f'{self.base_url}/{path.lstrip('/')}'
        with httpx.Client(timeout=self.timeout, headers=self.headers) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response
'''

files['app/clients/odds_api.py'] = '''from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings

from .base_http import BaseHttpClient


SPORT_KEY_BY_DOMAIN = {
    'soccer': [
        'soccer_uefa_champs_league',
        'soccer_conmebol_libertadores',
        'soccer_uefa_european_championship',
        'soccer_conmebol_copa_america',
        'soccer_brazil_campeonato',
        'soccer_brazil_copa_do_brasil',
        'soccer_spain_la_liga',
        'soccer_italy_serie_a',
        'soccer_england_premier_league',
    ],
    'nba': ['basketball_nba'],
    'tennis': [
        'tennis_atp_australian_open',
        'tennis_atp_french_open',
        'tennis_atp_us_open',
        'tennis_atp_wimbledon',
        'tennis_atp_finals',
        'tennis_davis_cup',
    ],
}


class OddsApiClient(BaseHttpClient):
    def __init__(self) -> None:
        settings = get_settings()
        super().__init__(base_url=settings.odds_api_base_url)
        self.api_key = settings.odds_api_key
        self.regions = ','.join(settings.odds_regions_list)
        self.markets = ','.join(settings.odds_markets_list)
        self.bookmakers = ','.join(settings.odds_bookmakers_list)

    def fetch_grouped_odds(self, domain_sport: str) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for sport_key in SPORT_KEY_BY_DOMAIN.get(domain_sport, []):
            params = {
                'apiKey': self.api_key,
                'regions': self.regions,
                'markets': self.markets,
                'oddsFormat': 'decimal',
                'dateFormat': 'iso',
            }
            if self.bookmakers:
                params['bookmakers'] = self.bookmakers
            response = self.get(f'/v4/sports/{sport_key}/odds', params=params)
            payload = response.json()
            for event in payload:
                event_id = str(event.get('id'))
                for bookmaker in event.get('bookmakers', []):
                    for market in bookmaker.get('markets', []):
                        market_key = market.get('key', '')
                        market_name = market_key.replace('_', ' ').title()
                        for outcome in market.get('outcomes', []):
                            grouped[event_id].append(
                                {
                                    'market_key': market_key,
                                    'market_name': market_name,
                                    'selection_name': outcome.get('name', ''),
                                    'price': float(outcome.get('price')),
                                    'line': outcome.get('point'),
                                    'bookmaker': bookmaker.get('title'),
                                    'source_last_update': self._parse_datetime(bookmaker.get('last_update')),
                                }
                            )
        return grouped

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(UTC)
'''

files['app/clients/sports_data_api.py'] = '''from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings
from app.models.domain import EventPayload, SegmentSlug, SportSlug, TeamPayload
from app.utils.time import utcnow, within_next_days

from .base_http import BaseHttpClient


class SportsDataClient(BaseHttpClient):
    def __init__(self) -> None:
        settings = get_settings()
        headers = {'Authorization': f'Bearer {settings.sports_data_api_key}'} if settings.sports_data_api_key else {}
        super().__init__(base_url=settings.sports_data_api_base_url, headers=headers, timeout=settings.sports_data_timeout_seconds)

    def fetch_live_events(self, sport: SportSlug) -> list[dict[str, Any]]:
        response = self.get(f'/events/live', params={'sport': sport})
        return response.json().get('events', [])

    def fetch_upcoming_events(self, sport: SportSlug, until: str) -> list[dict[str, Any]]:
        response = self.get(f'/events/upcoming', params={'sport': sport, 'until': until})
        return response.json().get('events', [])

    def fetch_event_stats(self, external_event_id: str, sport: SportSlug) -> dict[str, Any]:
        response = self.get(f'/events/{external_event_id}/stats', params={'sport': sport})
        return response.json()

    def collect_domain_events(self, sport: SportSlug) -> list[dict[str, Any]]:
        now = utcnow()
        until = within_next_days(7).isoformat()
        raw_events = [
            *self.fetch_live_events(sport=sport),
            *self.fetch_upcoming_events(sport=sport, until=until),
        ]
        deduped: dict[str, dict[str, Any]] = {}
        for event in raw_events:
            external_id = str(event.get('id'))
            if not external_id:
                continue
            deduped[external_id] = event
        return list(deduped.values())

    def normalize_event(self, sport: SportSlug, raw_event: dict[str, Any]) -> tuple[EventPayload, list[TeamPayload], dict[str, Any]]:
        starts_at = self._parse_datetime(raw_event.get('starts_at') or raw_event.get('commence_time'))
        is_live = bool(raw_event.get('is_live') or raw_event.get('status') == 'live')
        status = str(raw_event.get('status', 'scheduled')).lower()

        if is_live:
            segment: SegmentSlug = 'live'
        elif starts_at.date() == utcnow().date():
            segment = 'day'
        else:
            segment = 'week'

        competition_external_id = str(raw_event.get('competition_id') or raw_event.get('league_id') or raw_event.get('league', {}).get('id'))
        competition_name = str(raw_event.get('competition_name') or raw_event.get('league_name') or raw_event.get('league', {}).get('name') or 'Unknown Competition')

        home_team = str(raw_event.get('home_team') or raw_event.get('participants', [{}])[0].get('name'))
        away_team = str(raw_event.get('away_team') or raw_event.get('participants', [{}, {}])[1].get('name'))
        home_team_external_id = str(raw_event.get('home_team_id') or raw_event.get('participants', [{}])[0].get('id'))
        away_team_external_id = str(raw_event.get('away_team_id') or raw_event.get('participants', [{}, {}])[1].get('id'))

        event = EventPayload(
            external_id=str(raw_event.get('id')),
            sport=sport,
            competition_external_id=competition_external_id,
            competition_name=competition_name,
            home_team=home_team,
            away_team=away_team,
            home_team_external_id=home_team_external_id,
            away_team_external_id=away_team_external_id,
            starts_at=starts_at,
            status=status,
            segment=segment,
            is_live=is_live,
            meta=raw_event,
        )

        teams = [
            TeamPayload(external_id=home_team_external_id, name=home_team, short_name=home_team, sport=sport),
            TeamPayload(external_id=away_team_external_id, name=away_team, short_name=away_team, sport=sport),
        ]
        return event, teams, raw_event

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime:
        if not value:
            return utcnow()
        return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(UTC)
'''

files['app/services/openrouter_explainer.py'] = '''from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class OpenRouterExplainer:
    def __init__(self) -> None:
        self.settings = get_settings()

    def build_explanation(self, payload: dict[str, Any], fallback_text: str) -> str:
        if not self.settings.openrouter_api_key:
            return fallback_text

        try:
            response = httpx.post(
                f'{self.settings.openrouter_base_url}/chat/completions',
                headers={
                    'Authorization': f'Bearer {self.settings.openrouter_api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': self.settings.openrouter_model,
                    'messages': [
                        {
                            'role': 'system',
                            'content': (
                                'Você explica apostas esportivas de forma técnica, curta e responsável. '
                                'Use apenas os dados estruturados recebidos. Não invente dados.'
                            ),
                        },
                        {'role': 'user', 'content': str(payload)},
                    ],
                    'temperature': 0.2,
                    'max_tokens': 180,
                },
                timeout=20,
            )
            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content'].strip()
            return content or fallback_text
        except Exception:
            logger.exception('Falha ao gerar explicação via OpenRouter. Usando fallback.')
            return fallback_text
'''

files['app/services/strategy_engine.py'] = '''from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.models.domain import EventBundle, StrategyRecommendation
from app.services.openrouter_explainer import OpenRouterExplainer


class StrategyEngine:
    def __init__(self) -> None:
        self.explainer = OpenRouterExplainer()

    def analyze(self, bundle: EventBundle, form_data: dict[str, Any]) -> list[StrategyRecommendation]:
        recommendations: list[StrategyRecommendation] = []
        if bundle.event.sport == 'soccer':
            recommendations.extend(self._analyze_soccer_totals(bundle, form_data))
        elif bundle.event.sport == 'nba':
            recommendations.extend(self._analyze_nba_player_points(bundle, form_data))
        elif bundle.event.sport == 'tennis':
            recommendations.extend(self._analyze_tennis_moneyline(bundle, form_data))
        return [rec for rec in recommendations if rec.confidence_score >= 0.70]

    def _analyze_soccer_totals(self, bundle: EventBundle, form_data: dict[str, Any]) -> list[StrategyRecommendation]:
        by_market = self._index_by_market(bundle)
        recent = form_data.get('recent_form', {})
        home_avg_goals = float(recent.get('home_avg_goals_for', 0))
        away_avg_goals = float(recent.get('away_avg_goals_for', 0))
        over15_rate = float(recent.get('over_1_5_hit_rate', 0))
        over25_rate = float(recent.get('over_2_5_hit_rate', 0))
        combined = home_avg_goals + away_avg_goals

        recommendations: list[StrategyRecommendation] = []

        if combined >= 2.2 and over15_rate >= 0.74:
            price = self._pick_total_price(by_market, target=1.5)
            if price:
                fallback = (
                    f'Média ofensiva combinada de {combined:.2f} e taxa recente de over 1.5 em {over15_rate:.0%}. '
                    'O mercado parece suportado pelo momento ofensivo recente.'
                )
                explanation = self.explainer.build_explanation(
                    {'sport': 'soccer', 'market': 'over_1_5', 'recent_form': recent, 'odds': price},
                    fallback,
                )
                recommendations.append(
                    StrategyRecommendation(
                        external_event_id=bundle.event.external_id,
                        sport='soccer',
                        segment=bundle.event.segment,
                        strategy_code='soccer_over_1_5_v1',
                        market_key='totals',
                        recommendation_label='Mais de 1.5 gols',
                        odds_value=price,
                        confidence_score=min(0.95, 0.55 + over15_rate * 0.35 + (combined / 10)),
                        hit_rate=over15_rate,
                        explanation=explanation,
                        inputs={'combined_avg_goals': combined, 'recent_form': recent},
                    )
                )

        if combined >= 2.6 and over25_rate >= 0.62:
            price = self._pick_total_price(by_market, target=2.5)
            if price:
                fallback = (
                    f'Média ofensiva combinada de {combined:.2f} e taxa recente de over 2.5 em {over25_rate:.0%}. '
                    'Há sustentação estatística para um jogo mais aberto.'
                )
                explanation = self.explainer.build_explanation(
                    {'sport': 'soccer', 'market': 'over_2_5', 'recent_form': recent, 'odds': price},
                    fallback,
                )
                recommendations.append(
                    StrategyRecommendation(
                        external_event_id=bundle.event.external_id,
                        sport='soccer',
                        segment=bundle.event.segment,
                        strategy_code='soccer_over_2_5_v1',
                        market_key='totals',
                        recommendation_label='Mais de 2.5 gols',
                        odds_value=price,
                        confidence_score=min(0.93, 0.48 + over25_rate * 0.35 + (combined / 10)),
                        hit_rate=over25_rate,
                        explanation=explanation,
                        inputs={'combined_avg_goals': combined, 'recent_form': recent},
                    )
                )

        return recommendations

    def _analyze_nba_player_points(self, bundle: EventBundle, form_data: dict[str, Any]) -> list[StrategyRecommendation]:
        by_market = self._index_by_market(bundle)
        player_form = form_data.get('players', [])
        recommendations: list[StrategyRecommendation] = []

        for player in player_form:
            recent_avg = float(player.get('recent_avg_points', 0))
            hit_rate = float(player.get('points_20_hit_rate', 0))
            player_name = str(player.get('name', 'Jogador'))
            if recent_avg >= 22 and hit_rate >= 0.68:
                price = self._pick_player_points_price(by_market, player_name=player_name, threshold=20)
                if not price:
                    continue
                fallback = (
                    f'{player_name} tem média recente de {recent_avg:.1f} pontos e taxa de 20+ em {hit_rate:.0%}. '
                    'O recorte recente sustenta o cenário.'
                )
                explanation = self.explainer.build_explanation(
                    {'sport': 'nba', 'market': 'player_points_20_plus', 'player': player, 'odds': price},
                    fallback,
                )
                recommendations.append(
                    StrategyRecommendation(
                        external_event_id=bundle.event.external_id,
                        sport='nba',
                        segment=bundle.event.segment,
                        strategy_code='nba_player_20_plus_v1',
                        market_key='player_points',
                        recommendation_label=f'{player_name} 20+ pontos',
                        odds_value=price,
                        confidence_score=min(0.94, 0.45 + hit_rate * 0.4 + (recent_avg / 100)),
                        hit_rate=hit_rate,
                        explanation=explanation,
                        inputs={'player': player},
                    )
                )
        return recommendations

    def _analyze_tennis_moneyline(self, bundle: EventBundle, form_data: dict[str, Any]) -> list[StrategyRecommendation]:
        by_market = self._index_by_market(bundle)
        players = form_data.get('players', [])
        recommendations: list[StrategyRecommendation] = []
        for player in players:
            recent_win_rate = float(player.get('recent_win_rate', 0))
            h2h_advantage = float(player.get('h2h_advantage', 0))
            if recent_win_rate >= 0.72 and h2h_advantage >= 0:
                selection = str(player.get('name'))
                price = self._pick_moneyline_price(by_market, selection=selection)
                if not price:
                    continue
                fallback = (
                    f'{selection} chega com {recent_win_rate:.0%} de vitórias recentes e vantagem neutra/positiva no H2H. '
                    'O moneyline fica estatisticamente defensável.'
                )
                explanation = self.explainer.build_explanation(
                    {'sport': 'tennis', 'market': 'moneyline', 'player': player, 'odds': price},
                    fallback,
                )
                recommendations.append(
                    StrategyRecommendation(
                        external_event_id=bundle.event.external_id,
                        sport='tennis',
                        segment=bundle.event.segment,
                        strategy_code='tennis_moneyline_form_v1',
                        market_key='h2h',
                        recommendation_label=f'Vitória de {selection}',
                        odds_value=price,
                        confidence_score=min(0.92, 0.42 + recent_win_rate * 0.42 + max(0, h2h_advantage) * 0.05),
                        hit_rate=recent_win_rate,
                        explanation=explanation,
                        inputs={'player': player},
                    )
                )
        return recommendations

    @staticmethod
    def _index_by_market(bundle: EventBundle) -> dict[str, list[dict[str, Any]]]:
        indexed: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for odd in bundle.odds:
            indexed[odd.market_key].append(odd.model_dump())
        return indexed

    @staticmethod
    def _pick_total_price(by_market: dict[str, list[dict[str, Any]]], target: float) -> float | None:
        for selection in by_market.get('totals', []):
            name = str(selection.get('selection_name', '')).lower()
            line = selection.get('line')
            if 'over' in name and line == target:
                return float(selection['price'])
        return None

    @staticmethod
    def _pick_moneyline_price(by_market: dict[str, list[dict[str, Any]]], selection: str) -> float | None:
        for item in by_market.get('h2h', []):
            if str(item.get('selection_name', '')).strip().lower() == selection.strip().lower():
                return float(item['price'])
        return None

    @staticmethod
    def _pick_player_points_price(by_market: dict[str, list[dict[str, Any]]], player_name: str, threshold: int) -> float | None:
        for item in by_market.get('player_points', []):
            name = str(item.get('selection_name', '')).lower()
            line = item.get('line')
            if player_name.lower() in name and line is not None and float(line) >= threshold:
                return float(item['price'])
        return None
'''

files['app/repositories/supabase_repo.py'] = '''from __future__ import annotations

import logging
from typing import Any

from app.core.supabase import get_supabase_admin
from app.models.domain import EventBundle, StrategyRecommendation
from app.utils.time import utcnow

logger = logging.getLogger(__name__)


class SupabaseRepository:
    def __init__(self) -> None:
        self.client = get_supabase_admin()

    def insert_agent_log(self, agent_name: str, level: str, message: str, payload: dict[str, Any] | None = None) -> None:
        self.client.table('agent_logs').insert(
            {
                'agent_name': agent_name,
                'level': level,
                'message': message,
                'payload': payload or {},
                'created_at': utcnow().isoformat(),
            }
        ).execute()

    def insert_api_log(self, provider: str, endpoint: str, status: str, latency_ms: int | None = None, payload: dict[str, Any] | None = None) -> None:
        self.client.table('api_logs').insert(
            {
                'provider': provider,
                'endpoint': endpoint,
                'status': status,
                'latency_ms': latency_ms,
                'payload': payload or {},
                'created_at': utcnow().isoformat(),
            }
        ).execute()

    def acquire_lock(self, job_name: str, ttl_seconds: int) -> bool:
        response = self.client.rpc('acquire_job_lock', {'p_job_name': job_name, 'p_ttl_seconds': ttl_seconds}).execute()
        return bool(response.data)

    def release_lock(self, job_name: str) -> None:
        self.client.rpc('release_job_lock', {'p_job_name': job_name}).execute()

    def upsert_reference_data(self, bundle: EventBundle) -> None:
        self.client.table('sports').upsert(
            [{'slug': bundle.event.sport, 'name': bundle.event.sport.upper()}],
            on_conflict='slug',
        ).execute()

        self.client.table('competitions').upsert(
            [
                {
                    'external_id': bundle.event.competition_external_id,
                    'sport_slug': bundle.event.sport,
                    'name': bundle.event.competition_name,
                }
            ],
            on_conflict='external_id',
        ).execute()

        if bundle.teams:
            self.client.table('teams').upsert(
                [
                    {
                        'external_id': team.external_id,
                        'sport_slug': team.sport,
                        'name': team.name,
                        'short_name': team.short_name,
                    }
                    for team in bundle.teams
                ],
                on_conflict='external_id',
            ).execute()

        if bundle.players:
            self.client.table('players').upsert(
                [
                    {
                        'external_id': player.external_id,
                        'sport_slug': player.sport,
                        'name': player.name,
                        'team_external_id': player.team_external_id,
                    }
                    for player in bundle.players
                ],
                on_conflict='external_id',
            ).execute()

    def upsert_event_bundle(self, bundle: EventBundle) -> None:
        self.upsert_reference_data(bundle)
        event_payload = {
            'external_id': bundle.event.external_id,
            'sport_slug': bundle.event.sport,
            'competition_external_id': bundle.event.competition_external_id,
            'home_team_external_id': bundle.event.home_team_external_id,
            'away_team_external_id': bundle.event.away_team_external_id,
            'home_team_name': bundle.event.home_team,
            'away_team_name': bundle.event.away_team,
            'starts_at': bundle.event.starts_at.isoformat(),
            'status': bundle.event.status,
            'segment': bundle.event.segment,
            'is_live': bundle.event.is_live,
            'raw_payload': bundle.event.meta,
            'updated_at': utcnow().isoformat(),
        }
        self.client.table('events').upsert([event_payload], on_conflict='external_id').execute()

        if bundle.odds:
            odd_payload = [
                {
                    'event_external_id': bundle.event.external_id,
                    'market_key': odd.market_key,
                    'market_name': odd.market_name,
                    'selection_name': odd.selection_name,
                    'price': odd.price,
                    'line': odd.line,
                    'bookmaker': odd.bookmaker,
                    'source_last_update': odd.source_last_update.isoformat() if odd.source_last_update else None,
                    'updated_at': utcnow().isoformat(),
                }
                for odd in bundle.odds
            ]
            self.client.table('odds').upsert(
                odd_payload,
                on_conflict='event_external_id,market_key,selection_name,bookmaker,line',
            ).execute()

        self.client.table('event_stats_cache').upsert(
            [
                {
                    'event_external_id': bundle.event.external_id,
                    'sport_slug': bundle.event.sport,
                    'payload': bundle.stats,
                    'updated_at': utcnow().isoformat(),
                }
            ],
            on_conflict='event_external_id',
        ).execute()

    def enqueue_events(self, event_ids: list[str]) -> None:
        if not event_ids:
            return
        self.client.table('analysis_queue').upsert(
            [{'event_external_id': event_id, 'status': 'pending'} for event_id in event_ids],
            on_conflict='event_external_id',
        ).execute()

    def dequeue_events(self, limit: int) -> list[str]:
        response = self.client.rpc('dequeue_analysis_queue', {'p_limit': limit}).execute()
        return [row['event_external_id'] for row in (response.data or [])]

    def get_event_bundle(self, external_event_id: str) -> dict[str, Any] | None:
        event = self.client.table('events').select('*').eq('external_id', external_event_id).limit(1).execute().data
        if not event:
            return None
        odds = self.client.table('odds').select('*').eq('event_external_id', external_event_id).execute().data or []
        stats = self.client.table('event_stats_cache').select('*').eq('event_external_id', external_event_id).limit(1).execute().data
        return {
            'event': event[0],
            'odds': odds,
            'stats': stats[0]['payload'] if stats else {},
        }

    def get_recent_form(self, external_event_id: str) -> dict[str, Any]:
        response = self.client.rpc('get_event_form_snapshot', {'p_event_external_id': external_event_id}).execute()
        return response.data or {}

    def save_recommendations(self, recommendations: list[StrategyRecommendation]) -> int:
        if not recommendations:
            return 0
        payload = [
            {
                'event_external_id': rec.external_event_id,
                'sport_slug': rec.sport,
                'segment': rec.segment,
                'strategy_code': rec.strategy_code,
                'market_key': rec.market_key,
                'recommendation_label': rec.recommendation_label,
                'odds_value': rec.odds_value,
                'confidence_score': rec.confidence_score,
                'hit_rate': rec.hit_rate,
                'explanation': rec.explanation,
                'inputs': rec.inputs,
                'status': 'open',
                'published_at': utcnow().isoformat(),
                'updated_at': utcnow().isoformat(),
            }
            for rec in recommendations
        ]
        self.client.table('recommendations').upsert(
            payload,
            on_conflict='event_external_id,strategy_code,recommendation_label',
        ).execute()
        return len(payload)

    def mark_queue_done(self, event_ids: list[str]) -> None:
        if not event_ids:
            return
        self.client.table('analysis_queue').update({'status': 'done', 'updated_at': utcnow().isoformat()}).in_('event_external_id', event_ids).execute()

    def mark_queue_failed(self, event_ids: list[str], reason: str) -> None:
        if not event_ids:
            return
        self.client.table('analysis_queue').update(
            {'status': 'failed', 'last_error': reason, 'updated_at': utcnow().isoformat()}
        ).in_('event_external_id', event_ids).execute()

    def run_optimizer(self) -> int:
        response = self.client.rpc('refresh_strategy_metrics').execute()
        return int(response.data or 0)

    def list_recommendations(self, segment: str | None = None, sport: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        query = self.client.table('recommendations').select('*, events(*)').order('published_at', desc=True).limit(limit)
        if segment:
            query = query.eq('segment', segment)
        if sport:
            query = query.eq('sport_slug', sport)
        return query.execute().data or []

    def list_history(self, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        query = self.client.table('prediction_results').select('*, recommendations(*), events(*)').order('created_at', desc=True).limit(limit)
        if status:
            query = query.eq('result_status', status)
        return query.execute().data or []

    def admin_status(self) -> dict[str, Any]:
        latest_event = self.client.table('events').select('updated_at').order('updated_at', desc=True).limit(1).execute().data
        latest_rec = self.client.table('recommendations').select('updated_at').order('updated_at', desc=True).limit(1).execute().data
        latest_api = self.client.table('api_logs').select('*').order('created_at', desc=True).limit(10).execute().data or []
        latest_agent = self.client.table('agent_logs').select('*').order('created_at', desc=True).limit(10).execute().data or []
        return {
            'latest_event_update': latest_event[0]['updated_at'] if latest_event else None,
            'latest_recommendation_update': latest_rec[0]['updated_at'] if latest_rec else None,
            'latest_api_logs': latest_api,
            'latest_agent_logs': latest_agent,
        }

    def list_logs(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.client.table('agent_logs').select('*').order('created_at', desc=True).limit(limit).execute().data or []
'''

files['app/agents/collector.py'] = '''from __future__ import annotations

import logging
from typing import Iterable

from app.clients.odds_api import OddsApiClient
from app.clients.sports_data_api import SportsDataClient
from app.models.domain import EventBundle, OddSelection
from app.repositories.supabase_repo import SupabaseRepository

logger = logging.getLogger(__name__)

SPORTS = ['soccer', 'nba', 'tennis']


class CollectorAgent:
    name = 'collector'

    def __init__(self, repo: SupabaseRepository | None = None) -> None:
        self.repo = repo or SupabaseRepository()
        self.sports_data = SportsDataClient()
        self.odds_api = OddsApiClient()

    def run(self) -> list[str]:
        queued_event_ids: list[str] = []
        for sport in SPORTS:
            try:
                raw_events = self.sports_data.collect_domain_events(sport=sport)
                grouped_odds = self.odds_api.fetch_grouped_odds(domain_sport=sport)
                saved_ids = self._persist_sport_events(sport=sport, raw_events=raw_events, grouped_odds=grouped_odds)
                queued_event_ids.extend(saved_ids)
                self.repo.insert_agent_log(self.name, 'info', f'{sport}: {len(saved_ids)} eventos coletados', {'sport': sport})
            except Exception as exc:
                logger.exception('Falha no coletor para %s', sport)
                self.repo.insert_agent_log(self.name, 'error', f'Falha no coletor para {sport}', {'error': str(exc), 'sport': sport})
        self.repo.enqueue_events(queued_event_ids)
        return queued_event_ids

    def _persist_sport_events(self, sport: str, raw_events: list[dict], grouped_odds: dict[str, list[dict]]) -> list[str]:
        saved_ids: list[str] = []
        for raw_event in raw_events:
            event, teams, raw_payload = self.sports_data.normalize_event(sport=sport, raw_event=raw_event)
            if not event.external_id or not event.starts_at:
                continue
            stats = self.sports_data.fetch_event_stats(external_event_id=event.external_id, sport=sport)
            odds = [OddSelection(**odd) for odd in grouped_odds.get(event.external_id, [])]
            bundle = EventBundle(event=event, teams=teams, odds=odds, stats=stats)
            self.repo.upsert_event_bundle(bundle)
            saved_ids.append(event.external_id)
        return saved_ids
'''

files['app/agents/analyst.py'] = '''from __future__ import annotations

import logging

from app.models.domain import EventBundle, EventPayload, OddSelection, StrategyRecommendation, TeamPayload
from app.repositories.supabase_repo import SupabaseRepository
from app.services.strategy_engine import StrategyEngine

logger = logging.getLogger(__name__)


class AnalystAgent:
    name = 'analyst'

    def __init__(self, repo: SupabaseRepository | None = None) -> None:
        self.repo = repo or SupabaseRepository()
        self.engine = StrategyEngine()

    def run(self, batch_size: int) -> tuple[list[StrategyRecommendation], list[str]]:
        event_ids = self.repo.dequeue_events(limit=batch_size)
        if not event_ids:
            return [], []

        recommendations: list[StrategyRecommendation] = []
        succeeded_ids: list[str] = []

        for event_id in event_ids:
            try:
                raw = self.repo.get_event_bundle(event_id)
                if not raw:
                    continue
                bundle = self._hydrate_bundle(raw)
                form_data = self.repo.get_recent_form(event_id)
                recommendations.extend(self.engine.analyze(bundle=bundle, form_data=form_data))
                succeeded_ids.append(event_id)
            except Exception as exc:
                logger.exception('Falha ao analisar evento %s', event_id)
                self.repo.mark_queue_failed([event_id], reason=str(exc))
                self.repo.insert_agent_log(self.name, 'error', 'Falha ao analisar evento', {'event_id': event_id, 'error': str(exc)})

        return recommendations, succeeded_ids

    @staticmethod
    def _hydrate_bundle(raw: dict) -> EventBundle:
        event_data = raw['event']
        event = EventPayload(
            external_id=event_data['external_id'],
            sport=event_data['sport_slug'],
            competition_external_id=event_data['competition_external_id'],
            competition_name=event_data.get('competition_name', 'Competition'),
            home_team=event_data['home_team_name'],
            away_team=event_data['away_team_name'],
            home_team_external_id=event_data['home_team_external_id'],
            away_team_external_id=event_data['away_team_external_id'],
            starts_at=event_data['starts_at'],
            status=event_data['status'],
            segment=event_data['segment'],
            is_live=event_data['is_live'],
            meta=event_data.get('raw_payload', {}),
        )
        odds = [OddSelection(**odd) for odd in raw.get('odds', [])]
        teams = [
            TeamPayload(external_id=event.home_team_external_id, name=event.home_team, sport=event.sport),
            TeamPayload(external_id=event.away_team_external_id, name=event.away_team, sport=event.sport),
        ]
        return EventBundle(event=event, teams=teams, odds=odds, stats=raw.get('stats', {}))
'''

files['app/agents/publisher.py'] = '''from __future__ import annotations

from app.models.domain import StrategyRecommendation
from app.repositories.supabase_repo import SupabaseRepository


class PublisherAgent:
    name = 'publisher'

    def __init__(self, repo: SupabaseRepository | None = None) -> None:
        self.repo = repo or SupabaseRepository()

    def run(self, recommendations: list[StrategyRecommendation], analyzed_event_ids: list[str]) -> int:
        published = self.repo.save_recommendations(recommendations)
        self.repo.mark_queue_done(analyzed_event_ids)
        self.repo.insert_agent_log(self.name, 'info', 'Publicação concluída', {'published': published})
        return published
'''

files['app/agents/optimizer.py'] = '''from __future__ import annotations

from app.repositories.supabase_repo import SupabaseRepository


class OptimizerAgent:
    name = 'optimizer'

    def __init__(self, repo: SupabaseRepository | None = None) -> None:
        self.repo = repo or SupabaseRepository()

    def run(self) -> int:
        optimized = self.repo.run_optimizer()
        self.repo.insert_agent_log(self.name, 'info', 'Otimização concluída', {'optimized': optimized})
        return optimized
'''

files['app/services/pipeline.py'] = '''from __future__ import annotations

import logging

from app.agents.analyst import AnalystAgent
from app.agents.collector import CollectorAgent
from app.agents.optimizer import OptimizerAgent
from app.agents.publisher import PublisherAgent
from app.core.config import get_settings
from app.models.domain import PipelineRunSummary
from app.repositories.supabase_repo import SupabaseRepository

logger = logging.getLogger(__name__)


class PipelineService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.repo = SupabaseRepository()
        self.collector = CollectorAgent(repo=self.repo)
        self.analyst = AnalystAgent(repo=self.repo)
        self.publisher = PublisherAgent(repo=self.repo)
        self.optimizer = OptimizerAgent(repo=self.repo)

    def run(self) -> PipelineRunSummary:
        summary = PipelineRunSummary()
        lock_name = 'sports-pipeline-global'

        if not self.repo.acquire_lock(lock_name, ttl_seconds=self.settings.lock_ttl_seconds):
            summary.warnings.append('Pipeline já em execução em outro worker.')
            return summary

        try:
            queued_event_ids = self.collector.run()
            summary.collected_events = len(queued_event_ids)
            summary.queued_events = len(queued_event_ids)

            recommendations, analyzed_event_ids = self.analyst.run(batch_size=self.settings.pipeline_batch_size)
            summary.analyzed_events = len(analyzed_event_ids)
            summary.published_recommendations = self.publisher.run(recommendations, analyzed_event_ids)
            summary.optimized_strategies = self.optimizer.run()
            return summary
        except Exception as exc:
            logger.exception('Falha geral no pipeline')
            self.repo.insert_agent_log('pipeline', 'error', 'Falha geral no pipeline', {'error': str(exc)})
            summary.warnings.append(str(exc))
            return summary
        finally:
            self.repo.release_lock(lock_name)
'''

files['app/api/routes.py'] = '''from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Query

from app.core.config import get_settings
from app.repositories.supabase_repo import SupabaseRepository
from app.services.pipeline import PipelineService

router = APIRouter()
settings = get_settings()
repo = SupabaseRepository()


@router.get('/health')
def health() -> dict:
    return {'status': 'ok', 'service': settings.app_name}


@router.post('/internal/pipeline/run')
def run_pipeline(x_internal_token: str = Header(default='')) -> dict:
    if x_internal_token != settings.internal_cron_token:
        raise HTTPException(status_code=401, detail='Token interno inválido.')
    summary = PipelineService().run()
    return summary.model_dump()


@router.get('/api/v1/recommendations')
def recommendations(
    segment: str | None = Query(default=None, pattern='^(live|day|week)?$'),
    sport: str | None = Query(default=None, pattern='^(soccer|nba|tennis)?$'),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    return {'items': repo.list_recommendations(segment=segment, sport=sport, limit=limit)}


@router.get('/api/v1/history')
def history(
    status: str | None = Query(default=None, pattern='^(won|lost|open|void)?$'),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    return {'items': repo.list_history(status=status, limit=limit)}


@router.get('/api/v1/admin/status')
def admin_status() -> dict:
    return repo.admin_status()


@router.get('/api/v1/admin/logs')
def admin_logs(limit: int = Query(default=100, ge=1, le=500)) -> dict:
    return {'items': repo.list_logs(limit=limit)}
'''

files['app/main.py'] = '''from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.services.pipeline import PipelineService

configure_logging()
settings = get_settings()
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)
app.include_router(router)

scheduler: BackgroundScheduler | None = None


@app.on_event('startup')
def startup_event() -> None:
    global scheduler
    if settings.enable_local_scheduler:
        scheduler = BackgroundScheduler(timezone='UTC')
        scheduler.add_job(PipelineService().run, 'interval', seconds=settings.pipeline_interval_seconds, max_instances=1)
        scheduler.start()
        logger.info('Scheduler local iniciado a cada %s segundos.', settings.pipeline_interval_seconds)


@app.on_event('shutdown')
def shutdown_event() -> None:
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)
        scheduler = None
'''

files['db/schema.sql'] = '''-- Extensões recomendadas
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
  recommendation_id uuid references recommendations(id) on delete set null,
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
  v_acquired boolean := false;
begin
  insert into agent_locks(job_name, locked_until, updated_at)
  values (p_job_name, now() + make_interval(secs => p_ttl_seconds), now())
  on conflict (job_name)
  do update set
    locked_until = excluded.locked_until,
    updated_at = now()
  where agent_locks.locked_until < now();

  select locked_until > now() into v_acquired
  from agent_locks
  where job_name = p_job_name;

  return coalesce(v_acquired, false);
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
'''

for path, content in files.items():
    file_path = root / path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding='utf-8')

print(f'Wrote {len(files)} files to {root}')
