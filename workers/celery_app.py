"""Celery app (ADR-0008). Runs from repo root: `python -m workers.celery_app`."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# ensure repo root + packages are importable when run from any cwd
_ROOT = Path(__file__).resolve().parents[1]
for p in (_ROOT, _ROOT / "packages" / "ai-agent", _ROOT / "packages" / "ai-providers",
          _ROOT / "packages" / "video-engine"):
    if p.is_dir() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

os.environ.setdefault("CINEFORGE_STORAGE_ROOT", str(_ROOT / "storage"))

from celery import Celery  # noqa: E402

from backend.app import config  # noqa: E402

celery_app = Celery("cineforge", broker=config.REDIS_URL or "redis://localhost:6379/0",
                    backend=config.REDIS_URL or "redis://localhost:6379/0")
celery_app.conf.update(
    task_serializer="json", result_serializer="json", accept_content=["json"],
    task_track_started=True, worker_max_tasks_per_child=20,
    task_time_limit=config.JOB_TIMEOUT_S + 120, task_soft_time_limit=config.JOB_TIMEOUT_S,
)

from workers import tasks as _tasks  # noqa: E402,F401  (registers tasks)

__all__ = ["celery_app"]
