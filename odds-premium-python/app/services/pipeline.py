from __future__ import annotations

import logging

from app.agents.analyst import AnalystAgent
from app.agents.collector import CollectorAgent
from app.agents.optimizer import OptimizerAgent
from app.agents.publisher import PublisherAgent
from app.core.config import get_settings
from app.models.domain import PipelineRunSummary
from app.repositories.supabase_repo import SupabaseRepository

logger = logging.getLogger(__name__)


class PipelineService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.repo = SupabaseRepository()
        self.collector = CollectorAgent(repo=self.repo)
        self.analyst = AnalystAgent(repo=self.repo)
        self.publisher = PublisherAgent(repo=self.repo)
        self.optimizer = OptimizerAgent(repo=self.repo)

    def run(self) -> PipelineRunSummary:
        summary = PipelineRunSummary()
        lock_name = 'sports-pipeline-global'

        if not self.repo.acquire_lock(lock_name, ttl_seconds=self.settings.lock_ttl_seconds):
            summary.warnings.append('Pipeline já em execução em outro worker.')
            return summary

        try:
            queued_event_ids = self.collector.run()
            summary.collected_events = len(queued_event_ids)
            summary.queued_events = len(queued_event_ids)

            recommendations, analyzed_event_ids = self.analyst.run(batch_size=self.settings.pipeline_batch_size)
            summary.analyzed_events = len(analyzed_event_ids)
            summary.published_recommendations = self.publisher.run(recommendations, analyzed_event_ids)
            summary.optimized_strategies = self.optimizer.run()
            return summary
        except Exception as exc:
            logger.exception('Falha geral no pipeline')
            self.repo.insert_agent_log('pipeline', 'error', 'Falha geral no pipeline', {'error': str(exc)})
            summary.warnings.append(str(exc))
            return summary
        finally:
            self.repo.release_lock(lock_name)
