"""Celery application (ADR-0008) — used only when REDIS_URL is reachable."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
for p in (_REPO_ROOT, _REPO_ROOT / "backend"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from app.config import settings  # noqa: E402

try:
    from celery import Celery
except ImportError as exc:  # pragma: no cover
    raise SystemExit("celery is not installed; pip install -r backend/requirements.txt") from exc

celery_app = Celery(
    "cineforge",
    broker=settings.redis_url or "redis://localhost:6379/0",
    backend=settings.redis_url or "redis://localhost:6379/0",
)

celery_app.conf.update(
    task_default_queue="cineforge",
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    worker_max_tasks_per_child=20,  # recycle ffmpeg memory
)


@celery_app.task(name="cineforge.execute_job", ignore_result=False)
def execute_job_task(job_id: str) -> dict:
    from app.jobs import execute_job

    execute_job(job_id)
    from app.db import session_scope
    from app.models import Job

    with session_scope() as session:
        job = session.get(Job, job_id)
        return {"id": job_id, "status": job.status if job else "unknown"}


if __name__ == "__main__":
    celery_app.worker_main(["worker", "--loglevel=info", "-Q", "cineforge"])
