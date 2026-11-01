"""Health endpoint — GET /health per contracts (providers status + version)."""
from __future__ import annotations

from fastapi import APIRouter

from backend.app import config
from backend.app.schemas import HealthOut

router = APIRouter()


@router.get("/health", response_model=HealthOut)
async def health() -> HealthOut:
    return HealthOut(
        status="ok",
        version=config.VERSION,
        providers=config.provider_status(),
        storage_root=str(config.STORAGE_ROOT),
    )
