"""Test fixtures — isolated env (tmp storage, sqlite) BEFORE app imports."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for p in (REPO_ROOT, REPO_ROOT / "packages" / "ai-agent",
          REPO_ROOT / "packages" / "ai-providers", REPO_ROOT / "packages" / "video-engine"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

_TMP = tempfile.mkdtemp(prefix="cineforge-test-")
os.environ["CINEFORGE_STORAGE_ROOT"] = _TMP
os.environ["DATABASE_URL"] = "sqlite:///./cineforge-test.db"  # force: sandbox may inject a foreign URL
os.environ["REDIS_URL"] = ""  # force inline executor in tests
os.environ["CINEFORGE_FFMPEG_TIMEOUT_S"] = "120"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session")
def client():
    from backend.app.main import create_app
    from backend.app.db import init_db

    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def project(client):
    res = client.post("/api/projects", json={
        "title": "Nova Runners promo",
        "brief": "30s cinematic promo, dark mood, English narration, Instagram output",
        "platform": "instagram",
        "duration_hint_s": 12,  # small for fast e2e
    })
    assert res.status_code == 201, res.text
    return res.json()
