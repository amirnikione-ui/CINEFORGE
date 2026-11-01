"""Media analyze endpoint (M3 groundwork via engine)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_media_analyze_requires_asset():
    with TestClient(app) as client:
        assert client.post("/api/media/analyze", json={}).status_code == 400
        assert client.post("/api/media/analyze", json={"asset_id": "missing"}).status_code == 404


@pytest.mark.skipif(not __import__("shutil").which("ffmpeg"), reason="ffmpeg not installed")
def test_media_analyze_on_video(tmp_path):
    """Generate a tiny video asset through the normal pipeline, then analyze it."""
    with TestClient(app) as client:
        pid = client.post("/api/projects", json={
            "title": "Analyze me", "brief": "6s clip", "platform": "web", "duration_hint_s": 6,
        }).json()["id"]
        chat = client.post(f"/api/projects/{pid}/chat",
                           json={"message": "make a 6 second promo"}).json()
        job = next(j for j in chat["jobs"] if j["kind"] == "render")
        for _ in range(60):
            job = client.get(f"/api/jobs/{job['id']}").json()
            if job["status"] in ("done", "failed"):
                break
            import time
            time.sleep(1)
        assert job["status"] == "done", job.get("error")
        video_asset = job["result"]["asset_id"]

        resp = client.post("/api/media/analyze", json={"asset_id": video_asset})
        assert resp.status_code == 200, resp.text
        report = resp.json()["report"]
        assert report["duration"] > 3
        assert "video" in report and "palette" in report
