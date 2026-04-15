from __future__ import annotations

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
