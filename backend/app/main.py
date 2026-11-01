"""FastAPI application factory (ADR-0003)."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app import config, db
from backend.app.api import health, media, projects, chat

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    config.STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    yield
    await db.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="CINEFORGE API", version=config.VERSION,
                  description="AI-native video production studio — platform service",
                  lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://web:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(projects.router)
    app.include_router(chat.router)
    app.include_router(media.router)
    return app


app = create_app()
