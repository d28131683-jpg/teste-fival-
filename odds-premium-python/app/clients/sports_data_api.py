from __future__ import annotations

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
