"""Chat pipeline e2e: brief → storyboard v1 → frames/audio → render job → final MP4.

Graceful when ffmpeg is absent: render job fails honestly, contract shapes still hold.
"""

from __future__ import annotations

import shutil
import time

from fastapi.testclient import TestClient

from app.main import app

BRIEF = "30 second dark cinematic promo for a night-runner sneaker, instagram"


def _wait_job(client: TestClient, job_id: str, timeout: float = 90.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "failed"):
            return job
        time.sleep(1.0)
    return client.get(f"/api/jobs/{job_id}").json()


def test_chat_to_render_pipeline():
    with TestClient(app) as client:
        pid = client.post("/api/projects", json={
            "title": "Night Runner", "brief": BRIEF,
            "platform": "instagram", "duration_hint_s": 12,
        }).json()["id"]

        chat = client.post(f"/api/projects/{pid}/chat", json={"message": f"make a 12s promo. {BRIEF}"})
        assert chat.status_code == 200, chat.text
        body = chat.json()

        # contract shape
        assert body["user_message"]["role"] == "user"
        assert body["assistant_message"]["role"] == "assistant"
        meta = body["assistant_message"]["meta"]
        assert meta["plan"] and meta["tools_used"]
        assert meta["llm_provider"] == "mock"
        assert body["assistant_message"]["content"], "assistant reply must not be empty"

        tools_used = meta["tools_used"]
        for expected in ("write_storyboard", "generate_concept_frames", "generate_narration",
                         "generate_music"):
            assert expected in tools_used

        # storyboard asset validates against the binding schema
        sb_assets = [a for a in body["assets"] if a["kind"] == "storyboard"]
        assert sb_assets, "storyboard asset must exist"
        assert all(a["meta"]["provider"] for a in body["assets"])

        # frame + audio assets exist
        kinds = {a["kind"] for a in body["assets"]}
        assert "frame" in kinds and "audio" in kinds

        # render job queued in the chat response (contract: long ops are Job rows)
        render_jobs = [j for j in body["jobs"] if j["kind"] == "render"]
        assert render_jobs, "render job must be queued"
        job = _wait_job(client, render_jobs[0]["id"])
        assert job["status"] in ("done", "failed")

        if shutil.which("ffmpeg") and job["status"] == "done":
            assert job["result"]["asset_id"]
            file_resp = client.get(f"/api/assets/{job['result']['asset_id']}/file")
            assert file_resp.status_code == 200
            assert file_resp.headers["content-type"].startswith("video/mp4")
            assert len(file_resp.content) > 10_000

        # project detail shows the full history
        detail = client.get(f"/api/projects/{pid}").json()
        assert len(detail["messages"]) >= 2
        assert detail["project"]["status"] in ("ready", "failed", "generating")
