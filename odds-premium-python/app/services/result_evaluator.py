from __future__ import annotations

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
