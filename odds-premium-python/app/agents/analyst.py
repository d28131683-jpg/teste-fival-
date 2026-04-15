from __future__ import annotations

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
