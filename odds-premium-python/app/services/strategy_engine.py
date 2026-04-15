from __future__ import annotations

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
