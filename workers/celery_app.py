"""Celery worker entrypoint (ADR-0008).

Started by the compose worker service:  python -m workers.celery_app
Requires REDIS_URL; without it the API runs the same tasks inline.
"""
from __future__ import annotations

import os

import app.bootstrap_path  # noqa: F401  (sys.path bootstrap — keep first)

REDIS_URL = os.environ.get("REDIS_URL", "")

if not REDIS_URL:
    raise SystemExit(
        "workers.celery_app: REDIS_URL is not set. "
        "Without Redis the API executes jobs inline — start the worker only with Redis configured."
    )

from celery import Celery  # noqa: E402

celery_app = Celery(
    "cineforge",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["workers.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_max_tasks_per_child=20,  # recycle ffmpeg-heavy workers
)

if __name__ == "__main__":
    celery_app.start()
