from __future__ import annotations

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
