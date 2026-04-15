from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Query

from app.core.config import get_settings
from app.repositories.supabase_repo import SupabaseRepository
from app.services.pipeline import PipelineService

router = APIRouter()
settings = get_settings()
repo = SupabaseRepository()


@router.get('/health')
def health() -> dict:
    return {'status': 'ok', 'service': settings.app_name}


@router.post('/internal/pipeline/run')
def run_pipeline(x_internal_token: str = Header(default='')) -> dict:
    if x_internal_token != settings.internal_cron_token:
        raise HTTPException(status_code=401, detail='Token interno inválido.')
    summary = PipelineService().run()
    return summary.model_dump()


@router.get('/api/v1/recommendations')
def recommendations(
    segment: str | None = Query(default=None, pattern='^(live|day|week)?$'),
    sport: str | None = Query(default=None, pattern='^(soccer|nba|tennis)?$'),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    return {'items': repo.list_recommendations(segment=segment, sport=sport, limit=limit)}


@router.get('/api/v1/history')
def history(
    status: str | None = Query(default=None, pattern='^(won|lost|open|void)?$'),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    return {'items': repo.list_history(status=status, limit=limit)}


@router.get('/api/v1/admin/status')
def admin_status() -> dict:
    return repo.admin_status()


@router.get('/api/v1/admin/logs')
def admin_logs(limit: int = Query(default=100, ge=1, le=500)) -> dict:
    return {'items': repo.list_logs(limit=limit)}
