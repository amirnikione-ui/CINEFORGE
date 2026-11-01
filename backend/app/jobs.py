"""Job execution backend.

ADR-0008: if ``REDIS_URL`` is set and Celery is importable, jobs are dispatched to
Celery workers (named tasks); otherwise an in-process ``ThreadPoolExecutor``
(max_workers=2) runs the very same task functions. Job rows in the DB are the
single interface the UI polls (``GET /api/jobs/{id}``).

Task functions accept a ``progress_cb: Callable[[float], None]`` as their first
argument so they can stream 0.0–1.0 progress into the Job row.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable

log = logging.getLogger("cineforge.jobs")

_pool: ThreadPoolExecutor | None = None
_pool_lock = threading.Lock()


def _get_pool() -> ThreadPoolExecutor:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="cineforge-job")
    return _pool


def _celery_app():
    """Return the Celery app when Redis is configured, else None (inline mode)."""
    if not os.environ.get("REDIS_URL"):
        return None
    try:
        from workers.celery_app import celery_app
    except Exception as exc:  # pragma: no cover - depends on optional deps
        log.warning("celery backend unavailable (%s); falling back to inline executor", exc)
        return None
    return celery_app


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _set_job(job_id: str, **fields: Any) -> None:
    """Update a Job row from whatever thread we are on (fresh session)."""
    from app.db import SessionLocal
    from app.models import Job

    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None:
            return
        for key, value in fields.items():
            setattr(job, key, value)
        job.updated_at = _utc_now()
        db.commit()


def _jsonable(result: Any) -> Any:
    try:
        json.dumps(result)
        return result
    except (TypeError, ValueError):
        return {"ok": True, "detail": str(result)[:2000]}


def _execute(job_id: str, fn: Callable[..., Any], args: tuple) -> Any:
    """Run fn(progress_cb, *args), driving the Job row through its lifecycle."""

    def progress_cb(p: float) -> None:
        _set_job(job_id, progress=_clamp01(p))

    _set_job(job_id, status="running", progress=0.0)
    try:
        result = fn(progress_cb, *args)
    except Exception as exc:
        log.exception("job %s failed", job_id)
        _set_job(job_id, status="failed", error=str(exc)[:4000])
        raise
    _set_job(job_id, status="done", progress=1.0, result=_jsonable(result))
    return result


def submit(
    job_row_id: str,
    fn: Callable[..., Any],
    *args: Any,
    task_name: str | None = None,
    task_args: list | tuple | None = None,
    wait: bool = True,
    timeout: float | None = None,
) -> Any:
    """Execute the unit of work behind a Job row.

    - Celery mode (REDIS_URL set + celery importable + ``task_name`` given):
      dispatch ``task_name`` with ``task_args`` and return None immediately
      (clients poll GET /api/jobs/{id}).
    - Inline mode: run ``fn(progress_cb, *args)`` on the shared thread pool.
      ``wait=True`` (default) blocks until completion and returns the task's
      return value — the chat orchestrator relies on this to answer with the
      rendered artifacts in one round-trip.
    """
    celery = _celery_app()
    if celery is not None and task_name:
        celery.send_task(task_name, args=[str(a) for a in (task_args or [])])
        return None
    future: Future = _get_pool().submit(_execute, job_row_id, fn, args)
    if wait:
        return future.result(timeout=timeout)
    return future
