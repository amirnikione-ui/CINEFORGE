"""CINEFORGE API — FastAPI app (docs/API_CONTRACTS.md v0.1)."""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import routes_assets, routes_chat, routes_health, routes_media, routes_projects
from .core.config import get_settings
from .core.db import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="CINEFORGE API",
        version=settings.version,
        description="Conversational AI video studio — binding contract: docs/API_CONTRACTS.md v0.1",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(routes_health.router)
    app.include_router(routes_projects.router)
    app.include_router(routes_chat.router)
    app.include_router(routes_assets.router)
    app.include_router(routes_media.router)

    @app.on_event("startup")
    def _startup() -> None:
        init_db()
        os.makedirs(settings.storage_root, exist_ok=True)

    return app


app = create_app()
