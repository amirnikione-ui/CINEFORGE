"""Chat endpoint — the user talks to the Director (docs/API_CONTRACTS.md §Chat)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agent.orchestrator import Director
from app.db import get_db
from app.models import Asset, Job, Message, Project
from app.schemas import AssetOut, ChatRequest, ChatResponse, JobOut, MessageOut

router = APIRouter(prefix="/api/projects", tags=["chat"])


@router.post("/{project_id}/chat", response_model=ChatResponse)
def chat(project_id: str, body: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")

    assets_before = {
        a.id for a in db.query(Asset).filter(Asset.project_id == project_id).all()
    }
    jobs_before = {j.id for j in db.query(Job).filter(Job.project_id == project_id).all()}

    assistant, new_assets, new_jobs = Director(db).handle_message(project, body.message)

    # The Director persisted the user message; fetch it back for the response.
    user_row = (
        db.query(Message)
        .filter(Message.project_id == project_id, Message.role == "user")
        .order_by(Message.created_at.desc(), Message.id.desc())
        .first()
    )

    created_assets = (
        db.query(Asset)
        .filter(Asset.project_id == project_id, Asset.id.notin_(assets_before or {"-"}))
        .order_by(Asset.created_at.asc())
        .all()
        or new_assets
    )
    created_jobs = (
        db.query(Job)
        .filter(Job.project_id == project_id, Job.id.notin_(jobs_before or {"-"}))
        .order_by(Job.created_at.asc())
        .all()
        or new_jobs
    )

    return ChatResponse(
        user_message=MessageOut.model_validate(user_row) if user_row else MessageOut(
            id="", project_id=project_id, role="user", content=body.message, meta={}, created_at=""
        ),
        assistant_message=MessageOut.model_validate(assistant),
        assets=[AssetOut.model_validate(a) for a in created_assets],
        jobs=[JobOut.model_validate(j) for j in created_jobs],
    )
