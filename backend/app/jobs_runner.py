"""Job dispatch (ADR-0008): Celery when Redis is reachable, inline executor otherwise.

The SAME task function (workers.tasks.execute_job) runs in both modes.
"""
from __future__ import annotations

import logging
import socket
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from backend.app import config

log = logging.getLogger("cineforge.jobs")

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="cineforge-job")

import atexit

atexit.register(lambda: _executor.shutdown(wait=False, cancel_futures=True))


def _redis_reachable(url: str, timeout: float = 0.8) -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def dispatch(job_id: str) -> str:
    """Send the job to the best available executor. Returns mode used."""
    if _redis_reachable(config.REDIS_URL):
        try:
            from workers.celery_app import celery_app

            res = celery_app.send_task("cineforge.execute_job", args=[job_id])
            log.info("job %s → celery (%s)", job_id, res.id)
            return "celery"
        except Exception as exc:  # noqa: BLE001
            log.warning("celery dispatch failed (%s) — falling back inline", exc)
    _executor.submit(_inline_run, job_id)
    return "inline"


def _inline_run(job_id: str) -> None:
    try:
        from workers.tasks import execute_job

        execute_job(job_id)
    except Exception:  # noqa: BLE001
        log.exception("inline job %s crashed", job_id)
