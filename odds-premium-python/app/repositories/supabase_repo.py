from __future__ import annotations

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

    def list_open_recommendations(self, limit: int = 200) -> list[dict[str, Any]]:
        return (
            self.client.table('recommendations')
            .select('*, events(*)')
            .eq('status', 'open')
            .order('published_at', desc=False)
            .limit(limit)
            .execute()
            .data
            or []
        )

    def save_prediction_result(self, recommendation_id: str, event_external_id: str, result_status: str, roi: float, payload: dict[str, Any]) -> None:
        self.client.table('prediction_results').upsert(
            [
                {
                    'recommendation_id': recommendation_id,
                    'event_external_id': event_external_id,
                    'result_status': result_status,
                    'roi': roi,
                    'payload': payload,
                    'settled_at': utcnow().isoformat(),
                }
            ],
            on_conflict='recommendation_id',
        ).execute()
        self.client.table('recommendations').update(
            {'status': result_status, 'updated_at': utcnow().isoformat()}
        ).eq('id', recommendation_id).execute()

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
