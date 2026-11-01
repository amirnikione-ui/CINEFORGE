"""Pytest fixtures — mock-only provider chains, isolated DB + storage.

Environment is pinned BEFORE any app import so ``get_settings()`` and the
provider registry cache see the test configuration.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"
for p in (
    str(BACKEND),
    str(REPO_ROOT),
    str(REPO_ROOT / "packages" / "ai-providers"),
    str(REPO_ROOT / "packages" / "video-engine"),
    str(REPO_ROOT / "packages" / "ai-agent"),
):
    if p not in sys.path:
        sys.path.insert(0, p)

_TMP = Path(tempfile.mkdtemp(prefix="cineforge-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP / 'test_cineforge.db'}"
os.environ["CINEFORGE_STORAGE_ROOT"] = str(_TMP / "storage")
os.environ["CINEFORGE_LLM_CHAIN"] = "mock"
os.environ["CINEFORGE_IMAGE_CHAIN"] = "mock"
os.environ["CINEFORGE_TTS_CHAIN"] = "mock"
os.environ["CINEFORGE_MUSIC_CHAIN"] = "mock"
os.environ["CINEFORGE_STT_CHAIN"] = "mock"
for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "ZAI_API_KEY", "ELEVENLABS_API_KEY", "REDIS_URL"):
    os.environ.pop(key, None)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session")
def client():
    from app.db import init_db
    from app.main import app

    init_db()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def project(client) -> dict:
    resp = client.post(
        "/api/projects",
        json={
            "title": "Nova Runners",
            "brief": "A 12-second cinematic promo for NOVA running shoes. Dark mood, neon city.",
            "style": "cinematic-dark",
            "platform": "instagram",
            "duration_hint_s": 12,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()
