"""Task functions shared by the Celery worker and the inline executor (ADR-0008).

Every task takes ``progress_cb`` first so ``app.jobs.submit`` can drive the
Job row regardless of which backend runs it.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable

import app.bootstrap_path  # noqa: F401  (sys.path bootstrap — keep first)
from app.db import SessionLocal
from app.models import Asset, Job, Project

log = logging.getLogger("cineforge.workers")


def run_chat_pipeline(progress_cb: Callable[[float], None], project_id: str, message: str) -> dict:
    """Full director turn for a project (used by the Celery path of POST /chat)."""
    from app.agent.orchestrator import Director

    progress_cb(0.05)
    with SessionLocal() as db:
        project = db.get(Project, project_id)
        if project is None:
            raise ValueError(f"project {project_id} not found")
        assistant, assets, _jobs = Director(db).handle_message(project, message)
        progress_cb(1.0)
        return {
            "assistant_message_id": assistant.id,
            "asset_ids": [a.id for a in assets],
            "status": project.status,
        }


def render_only(progress_cb: Callable[[float], None], project_id: str) -> dict:
    """Re-render a project's latest storyboard without new LLM/planning work."""
    from app.agent.tools import ToolContext, execute_tool
    from app import storage
    from ai_providers import get_registry

    progress_cb(0.05)
    with SessionLocal() as db:
        project = db.get(Project, project_id)
        if project is None:
            raise ValueError(f"project {project_id} not found")
        storyboard_asset = (
            db.query(Asset)
            .filter(Asset.project_id == project_id, Asset.kind == "storyboard")
            .order_by(Asset.created_at.desc())
            .first()
        )
        if storyboard_asset is None:
            raise ValueError("no storyboard to render — chat with the director first")
        storyboard = json.loads(Path(storyboard_asset.path).read_text(encoding="utf-8"))
        ctx = ToolContext(
            db=db,
            project=project,
            workspace=storage.workspace(project_id),
            registry=get_registry(),
        )
        result = execute_tool("render_slideshow", {"storyboard": storyboard}, ctx)
        job = Job(project_id=project_id, kind="render", status="done", progress=1.0,
                  result={"summary": result.summary})
        db.add(job)
        db.commit()
        progress_cb(1.0)
        return {"summary": result.summary, "job_id": job.id}
