"""End-to-end offline test (CF-020): brief → chat → render job → real MP4.

Requires ffmpeg on PATH (skipped otherwise) — the mock tier must produce REAL
artifacts (ADR-0005): PNG frames, WAV narration/music, and a final H.264 MP4.
"""
from __future__ import annotations

import shutil
import time

import pytest

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None,
                                reason="ffmpeg required for e2e render test")


def wait_job(client, job_id: str, timeout_s: float = 300) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "failed"):
            return job
        time.sleep(0.5)
    raise TimeoutError(f"job {job_id} did not finish in {timeout_s}s")


def test_full_pipeline_offline(client, project):
    pid = project["id"]

    # 1. director pass (sync plan + tools; render enqueued)
    res = client.post(f"/api/projects/{pid}/chat",
                      json={"message": "make it punchy, shorter hook"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["assistant_message"]["meta"]["llm_provider"] == "mock"
    tools = body["assistant_message"]["meta"]["tools_used"]
    tool_names = [t["tool"] for t in tools]
    for expected in ("write_storyboard", "generate_concept_frames",
                     "generate_narration", "generate_music", "build_remotion_project"):
        assert expected in tool_names, tool_names

    # storyboard + frames + narration + music + project are real assets
    kinds = {a["kind"] for a in body["assets"]}
    assert {"storyboard", "frame", "audio", "project"} <= kinds

    # 2. render job completes with a real video artifact
    job_id = body["jobs"][0]["id"]
    job = wait_job(client, job_id)
    assert job["status"] == "done", job.get("error")
    assert job["result"]["duration_s"] > 0

    # 3. video asset streams back with correct content type + probes cleanly
    video_asset_id = job["result"]["asset_id"]
    file_res = client.get(f"/api/assets/{video_asset_id}/file")
    assert file_res.status_code == 200
    assert file_res.headers["content-type"].startswith("video/mp4")
    assert len(file_res.content) > 10_000  # a real render, not an empty shell

    probe_res = client.post("/api/media/probe", json={"asset_id": video_asset_id})
    assert probe_res.status_code == 200
    meta = probe_res.json()
    assert meta["codec"] == "h264"
    assert meta["duration_s"] == pytest.approx(job["result"]["duration_s"], abs=1.0)
    assert meta["width"] == 1080 and meta["height"] == 1920  # instagram preset
