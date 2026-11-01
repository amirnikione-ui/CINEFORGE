"""Director orchestrator: plan → execute (sync tools) → enqueue render → reply.

Contract: docs/API_CONTRACTS.md «Chat» — returns after plan+core tools complete;
rendering is a Job (ADR-0008 inline/celery). VERIFY step = ffprobe of the input
frames before enqueue (fail fast on corrupt assets).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Job, Message, Project, new_id

from cineforge_agent import tools as T
from cineforge_agent.planner import plan_storyboard
from cineforge_agent.storyboard import StoryboardLike


@dataclass
class OrchestratorResult:
    user_message: Message
    assistant_message: Message
    assets: list = field(default_factory=list)
    jobs: list = field(default_factory=list)


async def run_director(
    session: AsyncSession, project: Project, user_text: str, dispatch
) -> OrchestratorResult:
    """`dispatch` is injected (jobs_runner.dispatch) to avoid a import cycle."""
    t0 = time.monotonic()

    user_message = Message(id=new_id(), project_id=project.id, role="user",
                           content=user_text, meta={})
    session.add(user_message)
    await session.flush()

    project.status = "generating"

    # ---- 1. PLAN ---------------------------------------------------------
    sb: StoryboardLike
    sb, llm_provider, plan_steps = await plan_storyboard(
        project.brief, title=project.title, platform=project.platform,
        style=project.style, duration_hint_s=project.duration_hint_s,
    )
    # a mid-conversation user note can refine the plan (v0.1: appended to briefs context)
    if user_text and user_text.strip().lower() not in ("go", "start", "run", "build it"):
        plan_steps.append({"step": "user_note", "text": user_text[:200]})

    ctx = T.ToolContext(session=session, project_id=project.id)
    tools_used: list[dict[str, Any]] = []
    warnings: list[str] = []

    # ---- 2. EXECUTE sync tools ------------------------------------------
    async def _run(name: str, fn, *args) -> None:
        try:
            rep = await fn(*args)
            tools_used.append({"tool": rep.name, "provider": rep.provider,
                               "summary": rep.summary, "ok": rep.ok})
            if not rep.ok:
                warnings.append(f"{rep.name}: {rep.summary}")
        except Exception as exc:  # noqa: BLE001 — orchestrator must never 500 on one tool
            tools_used.append({"tool": name, "provider": "n/a",
                               "summary": f"unexpected: {type(exc).__name__}: {exc}", "ok": False})
            warnings.append(f"{name} crashed: {exc}")

    await _run("write_storyboard", T.write_storyboard, ctx, sb)
    await _run("generate_concept_frames", T.generate_concept_frames, ctx, sb)
    await _run("generate_narration", T.generate_narration, ctx, sb)
    await _run("generate_music", T.generate_music, ctx, sb)
    await _run("build_remotion_project", T.build_remotion_project, ctx, sb)

    # ---- 3. VERIFY frames before render (fail fast) ----------------------
    frame_assets = [a for a in ctx.assets.values()]
    verified = 0
    for asset in frame_assets:
        try:
            from backend.app import storage as st
            from cineforge_video.ffmpeg_tools import probe

            meta = probe(str(st.resolve_rel(asset.path)))
            if meta.get("duration_s", 0) >= 0:
                verified += 1
        except Exception:  # noqa: BLE001
            warnings.append(f"frame {asset.filename}: probe failed")

    # ---- 4. ENQUEUE render job -------------------------------------------
    job = Job(id=new_id(), project_id=project.id, kind="render", status="pending",
              progress=0.0,
              payload={"storyboard": T.dump_storyboard(sb),
                       "frame_assets": {sid: a.id for sid, a in ctx.assets.items()},
                       "verify": {"frames": verified}})
    session.add(job)
    await session.flush()

    summary = _assistant_summary(sb, tools_used, warnings, llm_provider, job, t0)
    assistant_message = Message(id=new_id(), project_id=project.id, role="assistant",
                                content=summary,
                                meta={"plan": plan_steps, "tools_used": tools_used,
                                      "llm_provider": llm_provider,
                                      "job_id": job.id, "warnings": warnings})
    session.add(assistant_message)
    # commit BEFORE dispatch: the inline/celery worker runs in another session
    # and must see the Job row + assets (SQLite WAL / connection isolation).
    await session.commit()

    dispatch(job.id)

    return OrchestratorResult(user_message=user_message, assistant_message=assistant_message,
                              assets=list(ctx.created), jobs=[job])


def _assistant_summary(sb: StoryboardLike, tools_used: list[dict[str, Any]],
                       warnings: list[str], llm_provider: str, job: Job, t0: float) -> str:
    n_scenes = len(sb.get("scenes", [])) if isinstance(sb, dict) else len(sb.scenes)
    dur = sb.get("duration_target_s", 30) if isinstance(sb, dict) else sb.duration_target_s
    title = sb.get("title", "Untitled") if isinstance(sb, dict) else sb.title
    lines = [
        f"🎬 Director's cut pipeline for “{title}” is running.",
        f"• Storyboard: {n_scenes} scenes, {dur:g}s target ({n_scenes}-beat structure: "
        "hook → reveal → proof → feature → CTA).",
        f"• Concept frames, narration and music bed generated "
        f"({'LLM: ' + llm_provider if llm_provider != 'mock' else 'offline mock tier — add an API key for AI-grade assets'}).",
        "• Editable Remotion project saved (packages/video-engine/remotion-template contract).",
        f"• Render job `{job.id[:8]}` queued — the final MP4 will appear in the preview panel.",
    ]
    if warnings:
        lines.append("⚠️ Warnings: " + "; ".join(warnings[:3]))
    lines.append(f"_(plan + tools: {time.monotonic() - t0:.1f}s)_")
    return "\n".join(lines)
