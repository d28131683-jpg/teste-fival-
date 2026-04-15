from __future__ import annotations

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
                self.repo.insert_api_log('sports_data', f'/events/*?sport={sport}', 'success', payload={'count': len(raw_events)})
                grouped_odds = self.odds_api.fetch_grouped_odds(domain_sport=sport)
                self.repo.insert_api_log('the_odds_api', f'/v4/sports/*/odds?sport={sport}', 'success', payload={'event_count_with_odds': len(grouped_odds)})
                saved_ids = self._persist_sport_events(sport=sport, raw_events=raw_events, grouped_odds=grouped_odds)
                queued_event_ids.extend(saved_ids)
                self.repo.insert_agent_log(self.name, 'info', f'{sport}: {len(saved_ids)} eventos coletados', {'sport': sport})
            except Exception as exc:
                logger.exception('Falha no coletor para %s', sport)
                self.repo.insert_api_log('collector', sport, 'error', payload={'error': str(exc)})
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
