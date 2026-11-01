#!/usr/bin/env python3
"""CINEFORGE end-to-end demo: chat brief → real rendered mp4 (zero API keys).

Works against BOTH backend implementations (they share the docs/API_CONTRACTS.md v0.1 surface):
- live server:      CINEFORGE_API_URL=http://localhost:8000 python scripts/demo_e2e.py
- in-process:       python scripts/demo_e2e.py   (boots the FastAPI app via TestClient)

The chat endpoint may run the render pipeline synchronously or in the background;
this demo therefore polls the project until a video asset appears (or fails honestly).
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT))
# The backend imports its engine core from the monorepo packages (video_engine).
for _pkg in ("video-engine", "ai-providers", "ai-agent"):
    _p = REPO_ROOT / "packages" / _pkg
    if _p.is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

BRIEF = (
    "A {duration}-second cinematic promo for NOVA running shoes. Dark mood, neon city, "
    "English narration, professional motion graphics, Instagram output."
)
# Keep the default short — zoompan renders at 1080x1920 are CPU-bound.
DURATION_S = int(os.environ.get("CINEFORGE_DEMO_DURATION", "15"))
POLL_TIMEOUT_S = int(os.environ.get("CINEFORGE_DEMO_TIMEOUT", "600"))
POLL_INTERVAL_S = 3.0

RULE = "─" * 62


def _client():
    live = os.environ.get("CINEFORGE_API_URL")
    if live:
        import httpx

        class Live:
            base = live.rstrip("/")

            def post(self, path, json=None):
                return httpx.post(self.base + path, json=json, timeout=600)

            def get(self, path):
                return httpx.get(self.base + path, timeout=120)

        return Live()
    from fastapi.testclient import TestClient

    from app.main import app

    # Context manager so the app lifespan (init_db) actually runs in-process.
    return TestClient(app)


def _wait_for_video(client, project_id: str) -> dict | None:
    """Poll project detail until a video asset exists or the run fails/times out."""
    deadline = time.time() + POLL_TIMEOUT_S
    while time.time() < deadline:
        detail = client.get(f"/api/projects/{project_id}").json()
        videos = [a for a in detail.get("assets", []) if a.get("kind") == "video"]
        if videos:
            return videos[-1]
        status = detail.get("project", {}).get("status", "")
        if status == "failed":
            print("\n❌ project status = failed — check API logs")
            return None
        jobs = detail.get("jobs", [])
        running = [j for j in jobs if j.get("status") in ("pending", "running")]
        if running:
            pct = max((j.get("progress") or 0) for j in running) * 100
            print(f"  … rendering ({pct:.0f}%), polling every {POLL_INTERVAL_S:.0f}s")
        time.sleep(POLL_INTERVAL_S)
    print("\n❌ timed out waiting for a video asset")
    return None


def main() -> int:
    print(RULE)
    print("🎬 CINEFORGE — end-to-end demo: brief → rendered film (offline mock tier)")
    print(RULE)

    live = bool(os.environ.get("CINEFORGE_API_URL"))
    client = _client()
    if not live:
        client.__enter__()  # run app lifespan (init_db) in-process

    health = client.get("/health").json()
    print(f"API      : {health['status']} v{health['version']}")
    print(f"providers: {health['providers']}")

    project = client.post(
        "/api/projects",
        json={"title": "Nova Runners Demo", "brief": BRIEF.format(duration=DURATION_S),
              "style": "cinematic-dark",
              "platform": "instagram", "duration_hint_s": DURATION_S},
    ).json()
    print(f"\nproject  : {project['id']}  ({project['title']})")

    print("\ndirector : planning and producing … (storyboard → frames → narration → music → render)")
    chat = client.post(
        f"/api/projects/{project['id']}/chat",
        json={"message": BRIEF.format(duration=DURATION_S)},
    ).json()

    assistant = chat.get("assistant_message") or {}
    print("\nassistant:")
    for line in (assistant.get("content") or "").splitlines():
        print(f"  {line}")
    plan = (assistant.get("meta") or {}).get("plan") or []
    if plan:
        print("\nplan     :")
        for step in plan:
            print(f"  ✓ {step}")

    # Assets returned inline (sync pipelines)…
    assets = list(chat.get("assets") or [])
    final_video = next((a for a in reversed(assets) if a.get("kind") == "video"), None)
    # … otherwise poll until the background render lands.
    if final_video is None:
        print("\nrender   : running in background — waiting for the video asset …")
        final_video = _wait_for_video(client, project["id"])
        if final_video is not None:
            detail = client.get(f"/api/projects/{project['id']}").json()
            assets = detail.get("assets", [])

    if final_video is None:
        return 1

    print("\nassets:")
    for asset in assets:
        p = Path(asset["path"])
        size = p.stat().st_size if p.is_file() else 0
        kind = asset.get("kind", "?")
        print(f"  [{kind:>10}] {asset.get('filename', '?'):<28} {size / 1024:>8.1f} KB  "
              f"provider={(asset.get('meta') or {}).get('provider', '-')}")

    for job in chat.get("jobs") or []:
        if job.get("kind") == "render":
            print(f"\nrender job: {job['status']} ({(job.get('progress') or 0) * 100:.0f}%)")

    print(RULE)
    print(f"✅ FINAL CUT: {final_video.get('path')}")
    print(f"   OPEN IN STUDIO: http://localhost:3000/projects/{project['id']}")
    print(RULE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
