from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.services.pipeline import PipelineService

configure_logging()
settings = get_settings()
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)
app.include_router(router)

scheduler: BackgroundScheduler | None = None


@app.on_event('startup')
def startup_event() -> None:
    global scheduler
    if settings.enable_local_scheduler:
        scheduler = BackgroundScheduler(timezone='UTC')
        scheduler.add_job(PipelineService().run, 'interval', seconds=settings.pipeline_interval_seconds, max_instances=1)
        scheduler.start()
        logger.info('Scheduler local iniciado a cada %s segundos.', settings.pipeline_interval_seconds)


@app.on_event('shutdown')
def shutdown_event() -> None:
    global scheduler
    if scheduler:
        scheduler.shutdown(wait=False)
        scheduler = None
