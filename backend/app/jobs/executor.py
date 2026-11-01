"""Inline job executor (ADR-0008 fallback tier) — BackgroundTasks now, Celery later (CF-017).

Runs a queued render job to completion against the same DB rows the API serves,
so the studio can poll /api/jobs/{id} regardless of which executor tier runs.
"""

from __future__ import annotations

import json
import logging

from fastapi import BackgroundTasks

from ..core.db import SessionLocal
from ..models import Job, Project

logger = logging.getLogger("cineforge.jobs")


def _execute_render(job_id: str, project_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        project = db.get(Project, project_id)
        if not job or not project:
            return
        job.status, job.progress = "running", 0.05
        db.commit()
        try:
            from ..director.tools import ToolCtx, render_slideshow

            ctx = ToolCtx(db=db, project=project)
            storyboard_asset = next((a for a in project.assets if a.kind == "storyboard"), None)
            if not storyboard_asset:
                raise RuntimeError("no storyboard asset on project")
            with open(storyboard_asset.path, encoding="utf-8") as fh:
                ctx.storyboard = json.load(fh)
            frame_paths: list[str] = []
            for asset in project.assets:
                if asset.kind == "frame":
                    frame_paths.append(asset.path)
                elif asset.kind == "audio" and asset.filename.startswith("narration"):
                    ctx.narration_path = asset.path
                elif asset.kind == "audio" and asset.filename.startswith("music"):
                    ctx.music_path = asset.path
            ctx.frame_paths = frame_paths
            result = render_slideshow(ctx, {})
            job.status, job.progress = "done", 1.0
            job.result = {"asset_id": result["assets"][0].id, "duration_s": result["render"]["duration_s"]}
            project.status = "ready"
            db.commit()
        except Exception as exc:  # noqa: BLE001 — job-level isolation
            logger.exception("render job %s failed", job_id)
            job.status, job.error = "failed", str(exc)[:2000]
            project.status = "failed"
            db.commit()
    finally:
        db.close()


def schedule_render(background: BackgroundTasks, job_id: str, project_id: str) -> None:
    """Inline executor via BackgroundTasks; swap for Celery in CF-017 without API change."""
    background.add_task(_execute_render, job_id, project_id)
