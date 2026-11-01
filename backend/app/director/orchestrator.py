"""Director orchestrator — plan → tools → chat response (CF-011 contract shape).

Deterministic offline director: brief → storyboard → frames + narration + music →
render job (background). Every assistant message carries meta.plan, meta.tools_used
and meta.llm_provider so the studio UI can show the agent's steps honestly.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..jobs.executor import schedule_render
from ..models import Asset, Job, Message, Project
from . import tools as T
from .tools import ToolCtx, ToolError

logger = logging.getLogger("cineforge.director")

CREATE_RE = ("make", "create", "build", "produce", "render", "generate", "بساز", "تولید")
ANALYZE_RE = ("analyze", "analyse", "reverse", "study", "تحلیل")


def plan(message: str, project: Project, has_storyboard: bool) -> list[dict[str, Any]]:
    """Deterministic plan (LLM planner lands with FORGE's CF-011 upgrade)."""
    text = (message or "").lower()
    if any(k in text for k in ANALYZE_RE):
        return [{"tool": "analyze_video", "args": {}, "note": "reverse-engineer the reference asset"}]
    if any(k in text for k in CREATE_RE) or not has_storyboard:
        return [
            {"tool": "write_storyboard", "args": {}, "note": "scenario → storyboard v1"},
            {"tool": "generate_concept_frames", "args": {}, "note": "one concept frame per scene"},
            {"tool": "generate_narration", "args": {}, "note": "narration timing bed"},
            {"tool": "generate_music", "args": {}, "note": "music bed for the mood"},
            {"tool": "render_slideshow", "args": {}, "note": "final cut via FFmpeg (background job)"},
        ]
    return [{"tool": "respond_only", "args": {}, "note": "conversational reply"}]


def run(db: Session, project: Project, user_message: str,
        background: BackgroundTasks) -> tuple[Message, Message, list[Asset], list[Job]]:
    """Execute a chat turn. Returns (user_message, assistant_message, assets, jobs)."""
    user_msg = Message(project_id=project.id, role="user", content=user_message.strip())
    db.add(user_msg)
    db.commit()

    has_storyboard = any(a.kind == "storyboard" for a in project.assets)
    steps = plan(user_message, project, has_storyboard)
    tools_used: list[str] = []
    assets: list[Asset] = []
    jobs: list[Job] = []
    ctx = ToolCtx(db=db, project=project)
    llm_provider = "mock"
    if get_settings().llm_configured:
        llm_provider = get_settings().llm_provider if get_settings().llm_provider != "mock" else "openai"

    project.status = "generating"
    db.commit()

    for step in steps:
        tool_name = step["tool"]
        if tool_name == "respond_only":
            continue
        fn = T.TOOL_FUNCS.get(tool_name)
        if fn is None:
            logger.warning("unknown tool %s", tool_name)
            continue
        try:
            result = fn(ctx, step.get("args") or {})
            tools_used.append(tool_name)
            assets.extend(result.get("assets", []))
        except ToolError as exc:
            logger.exception("tool %s failed", tool_name)
            project.status = "failed"
            db.commit()
            assistant = Message(
                project_id=project.id, role="assistant",
                content=(f"⚠️ Step “{tool_name}” failed: {exc}\n"
                         "The pipeline stops honestly instead of faking progress. "
                         "Adjust the brief and try again — artifacts produced so far are kept."),
                meta={"plan": steps, "tools_used": tools_used, "llm_provider": llm_provider,
                      "failed_tool": tool_name},
            )
            db.add(assistant)
            db.commit()
            db.refresh(assistant)
            return user_msg, assistant, assets, jobs

    if tools_used:
        job = Job(project_id=project.id, kind="render", status="pending",
                  result={"note": "render_slideshow queued"})
        db.add(job)
        db.commit()
        db.refresh(job)
        jobs.append(job)
        schedule_render(background, job.id, project.id)
        reply = (
            f"🎬 Production started for “{project.title}”.\n"
            f"- Storyboard: {len((ctx.storyboard or {}).get('scenes', []))} scenes "
            f"({(ctx.storyboard or {}).get('duration_target_s', 0)}s, {(ctx.storyboard or {}).get('aspect', '16:9')})\n"
            f"- Concept frames, narration bed and music generated\n"
            f"- Final cut is rendering in the background — poll the job for progress.\n"
            f"_Provider tier: {'LLM ' + llm_provider + ' + ' if llm_provider != 'mock' else ''}mock media / video-engine (fully offline)._"
        )
    else:
        reply = (
            f"I'm the CINEFORGE director for “{project.title}”. Tell me what to make — e.g. "
            f"“make a 30s {project.platform} promo” — and I'll storyboard, generate assets and render."
        )
        project.status = "draft"

    assistant = Message(project_id=project.id, role="assistant", content=reply,
                        meta={"plan": steps, "tools_used": tools_used, "llm_provider": llm_provider})
    db.add(assistant)
    db.commit()
    db.refresh(assistant)
    return user_msg, assistant, assets, jobs
