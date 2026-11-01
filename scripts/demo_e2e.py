#!/usr/bin/env python3
"""CINEFORGE E2E demo (CF-020): chat brief → rendered MP4, zero API keys.

Usage:
  python scripts/demo_e2e.py                 # in-process (TestClient) — no server needed
  API_BASE=http://localhost:8000 python scripts/demo_e2e.py   # against a running API
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BRIEF = ("Make a 12-second cinematic promo for my product NOVA, dark mood, "
         "English narration, professional motion graphics, Instagram output.")


def main() -> int:
    api_base = os.environ.get("API_BASE")
    client = None
    if api_base:
        import httpx

        client = httpx.Client(base_url=api_base, timeout=60)
        mode = f"remote API {api_base}"
    else:
        from fastapi.testclient import TestClient

        from backend.app.main import create_app

        # context manager runs the app lifespan (init_db) — required for schema creation
        client = TestClient(create_app())
        client.__enter__()
        mode = "in-process (offline mock tier)"

    try:
        return _run(client, mode)
    finally:
        try:
            client.close()  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            pass


def _run(client, mode: str) -> int:
    print(f"▶ CINEFORGE E2E demo — {mode}")
    print(f"▶ Brief: {BRIEF}")

    project = client.post("/api/projects", json={
        "title": "NOVA — Cinematic Promo", "brief": BRIEF,
        "platform": "instagram", "duration_hint_s": 12}).json()
    print(f"▶ Project created: {project['id']}")

    chat = client.post(f"/api/projects/{project['id']}/chat", json={"message": "go"}).json()
    meta = chat["assistant_message"]["meta"]
    print(f"▶ Director plan ({meta['llm_provider']}): "
          + " → ".join(s.get("step", "?") for s in meta["plan"]))
    for t in meta["tools_used"]:
        mark = "✓" if t["ok"] else "✗"
        print(f"   {mark} {t['tool']:<24} [{t['provider']}] {t['summary']}")

    job_id = chat["jobs"][0]["id"]
    t0 = time.time()
    while True:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "failed"):
            break
        print(f"   … render {job['progress'] * 100:.0f}%")
        time.sleep(1.5)
        if time.time() - t0 > 600:
            print("✗ timeout waiting for render")
            return 1

    if job["status"] != "done":
        print(f"✗ render failed: {job.get('error')}")
        return 1

    res = job["result"]
    file_url = f"/api/assets/{res['asset_id']}/file"
    print(f"✓ DONE in {time.time() - t0:.0f}s — {res['width']}x{res['height']} "
          f"@ {res['duration_s']:.1f}s")
    print(f"  video: {file_url}")
    print(f"  (studio: http://localhost:3000/studio/{project['id']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
