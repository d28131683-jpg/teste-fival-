from __future__ import annotations

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
