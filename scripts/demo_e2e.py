#!/usr/bin/env python3
"""CINEFORGE end-to-end demo: chat brief → real rendered mp4 (zero API keys).

Usage:
    python scripts/demo_e2e.py                      # in-process (TestClient)
    CINEFORGE_API_URL=http://localhost:8000 python scripts/demo_e2e.py   # live server
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT))

BRIEF = (
    "A 30-second cinematic promo for NOVA running shoes. Dark mood, neon city, "
    "English narration, professional motion graphics, Instagram output."
)

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

    from app.db import init_db
    from app.main import app

    init_db()
    return TestClient(app)


def main() -> int:
    print(RULE)
    print("🎬 CINEFORGE — end-to-end demo: brief → rendered film (mock tier)")
    print(RULE)

    client = _client()

    health = client.get("/health").json()
    print(f"API      : {health['status']} v{health['version']}")
    print(f"providers: {health['providers']}")

    project = client.post(
        "/api/projects",
        json={"title": "Nova Runners Demo", "brief": BRIEF, "style": "cinematic-dark",
              "platform": "instagram", "duration_hint_s": 30},
    ).json()
    print(f"\nproject  : {project['id']}  ({project['title']})")

    print("\ndirector : planning and producing … (storyboard → frames → narration → music → render)")
    chat = client.post(f"/api/projects/{project['id']}/chat", json={"message": BRIEF}).json()

    print("\nassistant:")
    for line in chat["assistant_message"]["content"].splitlines():
        print(f"  {line}")
    print(f"\nplan     :")
    for step in chat["assistant_message"]["meta"].get("plan", []):
        print(f"  ✓ {step}")

    print("\nassets:")
    final_video = None
    for asset in chat["assets"]:
        size = Path(asset["path"]).stat().st_size if Path(asset["path"]).exists() else 0
        print(f"  [{asset['kind']:>10}] {asset['filename']:<28} {size / 1024:>8.1f} KB  "
              f"provider={asset['meta'].get('provider', '-')}")
        if asset["kind"] == "video":
            final_video = asset

    if final_video is None:
        print("\n❌ no video asset produced — check the API logs")
        return 1
    for job in chat["jobs"]:
        if job["kind"] == "render":
            print(f"\nrender job: {job['status']} ({job['progress'] * 100:.0f}%)")

    print(RULE)
    print(f"✅ FINAL CUT: {final_video['path']}")
    print(f"   OPEN IN STUDIO: http://localhost:3000/studio/{project['id']}")
    print(RULE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
