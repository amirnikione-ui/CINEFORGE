"""CINEFORGE backend — FastAPI application entrypoint.

Run from ``backend/``:  uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import app.bootstrap_path  # noqa: F401  (must be first: sys.path bootstrap)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import init_db
from app.routers import assets, chat, jobs, projects
from app.schemas import HealthOut

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("cineforge")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    log.info("CINEFORGE backend ready (storage: %s)", get_settings().storage_root)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="CINEFORGE API",
        version=settings.version,
        description=(
            "AI-native video production studio — the Director agent turns chat briefs "
            "into storyboards, frames, narration, music and rendered cuts."
        ),
        lifespan=lifespan,
    )
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(projects.router)
    app.include_router(chat.router)
    app.include_router(jobs.router)
    app.include_router(assets.router)

    @app.get("/health", response_model=HealthOut, tags=["health"])
    def health() -> HealthOut:
        from ai_providers import get_registry

        return HealthOut(
            status="ok",
            version=settings.version,
            providers=get_registry().status(),
            storage_root=str(settings.storage_root),
        )

    return app


app = create_app()
