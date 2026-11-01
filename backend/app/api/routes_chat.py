"""Chat endpoint — POST /api/projects/{pid}/chat per contract."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..director import orchestrator
from ..models import Project
from ..schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/projects", tags=["chat"])


@router.post("/{pid}/chat", response_model=ChatResponse)
def chat(pid: str, payload: ChatRequest, background: BackgroundTasks,
         db: Session = Depends(get_db)):
    project = db.get(Project, pid)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    user_msg, assistant_msg, assets, jobs = orchestrator.run(
        db, project, payload.message, background
    )
    return ChatResponse(
        user_message=user_msg,
        assistant_message=assistant_msg,
        assets=assets,
        jobs=jobs,
    )
