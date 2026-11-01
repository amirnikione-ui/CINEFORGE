"""Celery application (ADR-0008 Celery tier) — FORGE (agent-03), CF-017.

Wired to the CANONICAL backend (agent-05's PR #27 layout):
- broker/backend: REDIS_URL env (Settings has no redis field by design)
- task: cineforge.execute_job -> claims the Job row (pending→running CAS,
  single-flight) then runs app.jobs.executor._execute_render, the exact code
  path the inline BackgroundTasks executor uses.

Without Redis nothing changes: the API keeps its inline executor. With Redis:
  python -m workers.celery_app     # from repo root (compose worker service)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
for p in (_REPO_ROOT, _REPO_ROOT / "backend", _REPO_ROOT / "packages" / "video-engine"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

try:
    from celery import Celery
except ImportError as exc:  # pragma: no cover
    raise SystemExit("celery is not installed; pip install -r backend/requirements.txt") from exc

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("cineforge", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.update(
    task_default_queue="cineforge",
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    worker_max_tasks_per_child=20,  # recycle ffmpeg memory
    broker_connection_retry_on_startup=True,
)


@celery_app.task(name="cineforge.execute_job", ignore_result=False)
def execute_job_task(job_id: str) -> dict:
    from sqlalchemy import update

    from app.core.db import SessionLocal
    from app.jobs.executor import _execute_render
    from app.models import Job

    with SessionLocal() as db:
        claimed = db.execute(
            update(Job).where(Job.id == job_id, Job.status == "pending").values(status="running", progress=0.05)
        ).rowcount
        if not claimed:
            row = db.get(Job, job_id)
            return {"id": job_id, "status": row.status if row else "unknown", "note": "already claimed"}
        project_id = db.get(Job, job_id).project_id

    _execute_render(job_id, project_id)

    with SessionLocal() as db:
        row = db.get(Job, job_id)
        return {"id": job_id, "status": row.status if row else "unknown"}


if __name__ == "__main__":
    celery_app.worker_main(["worker", "--loglevel=info", "-Q", "cineforge"])
