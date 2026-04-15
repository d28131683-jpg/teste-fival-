from __future__ import annotations

from app.repositories.supabase_repo import SupabaseRepository
from app.services.result_evaluator import ResultEvaluator


class OptimizerAgent:
    name = 'optimizer'

    def __init__(self, repo: SupabaseRepository | None = None) -> None:
        self.repo = repo or SupabaseRepository()
        self.evaluator = ResultEvaluator()

    def run(self) -> int:
        settled = 0
        open_recommendations = self.repo.list_open_recommendations(limit=200)
        for recommendation in open_recommendations:
            event_payload = recommendation.get('events') or {}
            stats_response = self.repo.get_event_bundle(recommendation['event_external_id']) or {}
            stats_payload = stats_response.get('stats') or {}
            result = self.evaluator.evaluate(recommendation, event_payload, stats_payload)
            if not result:
                continue
            self.repo.save_prediction_result(
                recommendation_id=recommendation['id'],
                event_external_id=recommendation['event_external_id'],
                result_status=result['result_status'],
                roi=result['roi'],
                payload=result['payload'],
            )
            settled += 1

        optimized = self.repo.run_optimizer()
        self.repo.insert_agent_log(self.name, 'info', 'Otimização concluída', {'optimized': optimized, 'settled': settled})
        return optimized
