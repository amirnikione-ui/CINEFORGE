"""System health per docs/API_CONTRACTS.md v0.1 (providers map + storage_root)."""

from __future__ import annotations

from fastapi import APIRouter

from ..core.config import get_settings
from ..providers.base import capability_map

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "version": s.version,
        "providers": capability_map(),
        "storage_root": s.storage_root,
    }
