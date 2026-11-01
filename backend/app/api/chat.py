"""Chat endpoint — the director-agent entry (contracts «Chat», sync plan+tools)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.projects import get_session
from backend.app.jobs_runner import dispatch
from backend.app.models import Project
from backend.app.schemas import ChatRequest, ChatResponse, JobOut, MessageOut

from cineforge_agent import run_director

log = logging.getLogger("cineforge.chat")

router = APIRouter(tags=["chat"])


@router.post("/api/projects/{pid}/chat", response_model=ChatResponse)
async def chat(pid: str, body: ChatRequest, session: AsyncSession = Depends(get_session)):
    project = await session.get(Project, pid)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    if project.status == "generating":
        raise HTTPException(status_code=409,
                            detail="a generation pass is already running for this project")
    try:
        result = await run_director(session, project, body.message, dispatch)
    except Exception as exc:  # noqa: BLE001 — convert orchestrator crash to honest 500
        log.exception("director failed for project %s", pid)
        project.status = "failed"
        await session.commit()
        raise HTTPException(status_code=500, detail=f"director failed: {exc}") from exc
    project.status = "ready"
    await session.commit()
    return ChatResponse(
        user_message=MessageOut.model_validate(result.user_message),
        assistant_message=MessageOut.model_validate(result.assistant_message),
        assets=[a for a in result.assets],
        jobs=[JobOut.model_validate(j) for j in result.jobs],
    )
