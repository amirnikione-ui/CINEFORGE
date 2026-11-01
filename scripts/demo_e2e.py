#!/usr/bin/env python3
"""CINEFORGE end-to-end demo: brief -> storyboard -> frames/audio -> rendered MP4.

Works with ZERO API keys (offline mock tier + real FFmpeg rendering).

Usage:
  python scripts/demo_e2e.py                 # in-process API (no server needed)
  python scripts/demo_e2e.py --serve http://localhost:8000
  python scripts/demo_e2e.py --brief "..." --platform youtube --duration 12
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT / "packages" / "ai-providers"))
sys.path.insert(0, str(REPO_ROOT / "packages" / "video-engine"))

DEFAULT_BRIEF = (
    "Make a cinematic promo for Nova, a night-running app. Dark mood, city lights, "
    "energetic but elegant. English narration, professional motion graphics."
)


def _client(base_url: str | None):
    if base_url:
        import httpx

        return httpx.Client(base_url=base_url, timeout=300.0), False
    # in-process: isolated storage + sqlite db in a temp dir (no module reloads)
    tmp = Path(tempfile.mkdtemp(prefix="cineforge-demo-"))
    import sqlalchemy as sa

    import app.config as cfg

    cfg.settings.storage_root = tmp / "storage"
    cfg.settings.database_url = f"sqlite:///{tmp / 'demo.db'}"

    import app.db as dbmod

    dbmod.engine.dispose()
    dbmod.engine = sa.create_engine(
        f"sqlite:///{tmp / 'demo.db'}", connect_args={"check_same_thread": False}
    )
    dbmod.SessionLocal = sa.orm.sessionmaker(bind=dbmod.engine, expire_on_commit=False)

    from app.models import Base

    Base.metadata.create_all(dbmod.engine)

    import app.providers  # noqa: F401  (default registry)

    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app), True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--serve", default=None, help="base URL of a running API (default: in-process)")
    ap.add_argument("--brief", default=DEFAULT_BRIEF)
    ap.add_argument("--title", default="Nova Runners — Cinematic Promo")
    ap.add_argument("--platform", default="instagram", choices=["instagram", "youtube", "tiktok", "web"])
    ap.add_argument("--duration", type=float, default=14.0)
    ap.add_argument("--style", default="cinematic-dark")
    args, _ = ap.parse_known_args()

    client, inproc = _client(args.serve)
    print(f"▶ CINEFORGE e2e demo ({'in-process' if inproc else 'server: ' + args.serve})")

    health = client.get("/health").json()
    print(f"✓ API healthy — providers: {json.dumps(health['providers'])}")

    project = client.post(
        "/api/projects",
        json={
            "title": args.title,
            "brief": args.brief,
            "platform": args.platform,
            "duration_hint_s": args.duration,
            "style": args.style,
        },
    ).json()
    print(f"✓ project created: {project['id']}")

    chat = client.post(f"/api/projects/{project['id']}/chat", json={"message": args.brief}).json()
    plan = chat["assistant_message"]["meta"].get("plan", {})
    print(f"✓ director replied (brain: {chat['assistant_message']['meta'].get('llm_provider')})")
    for scene in plan.get("scenes", []):
        print(f"   • [{scene['kind']}] {scene['headline']} — {scene['duration_s']}s")
    print(f"✓ assets: {len(chat['assets'])}, jobs: {len(chat['jobs'])}")

    if not chat["jobs"]:
        print("ℹ auto-render disabled; storyboard + media assets are the deliverable")
        return 0

    job_id = chat["jobs"][0]["id"]
    print(f"▶ polling render job {job_id} …")
    deadline = time.time() + 300
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        sys.stdout.write(f"\r   status={job['status']:<8} progress={job['progress'] * 100:5.1f}%")
        sys.stdout.flush()
        if job["status"] in ("done", "failed"):
            print()
            break
        time.sleep(1.0)

    if job["status"] != "done":
        print(f"\n✗ render failed: {job.get('error')}")
        return 1

    video_asset_id = job["result"]["video_asset_id"]
    detail = client.get(f"/api/projects/{project['id']}").json()
    video_asset = next(a for a in detail["assets"] if a["id"] == video_asset_id)
    render_meta = job["result"].get("render", {})
    print("✓ rendered:")
    for k in ("duration_s", "width", "height", "fps", "has_audio", "size_bytes"):
        print(f"   {k}: {render_meta.get(k)}")
    storage_path = Path(detail.get("project", {}).get("id", ""))  # only for display
    print(f"   asset: {video_asset['kind']}/{video_asset['filename']} (id {video_asset_id})")
    print(f"   file:  {video_asset['path']}")
    print("\nDone — open the studio at http://localhost:3000 or GET /api/assets/%s/file" % video_asset_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
