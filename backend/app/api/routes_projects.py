"""Projects REST — exact contract shapes (uuid ids, ProjectDetail aggregate)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..models import Asset, Job, Message, Project
from ..schemas import ProjectCreate, ProjectDetail, ProjectOut

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _get_or_404(db: Session, pid: str) -> Project:
    project = db.get(Project, pid)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    return project


@router.post("", status_code=201, response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(
        title=payload.title.strip(),
        brief=payload.brief,
        style=payload.style or "cinematic-dark",
        platform=payload.platform or "web",
        duration_hint_s=payload.duration_hint_s or 30.0,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.created_at.desc()).all()


@router.get("/{pid}", response_model=ProjectDetail)
def get_project(pid: str, db: Session = Depends(get_db)):
    project = _get_or_404(db, pid)
    return ProjectDetail(
        project=ProjectOut.model_validate(project),
        messages=[MessageOut_m(m) for m in project.messages],
        assets=[AssetOut_m(a) for a in project.assets],
        jobs=[JobOut_m(j) for j in project.jobs],
    )


def MessageOut_m(m):  # small local validators to avoid circular schema imports
    from ..schemas import MessageOut
    return MessageOut.model_validate(m)


def AssetOut_m(a):
    from ..schemas import AssetOut
    return AssetOut.model_validate(a)


def JobOut_m(j):
    from ..schemas import JobOut
    return JobOut.model_validate(j)


@router.delete("/{pid}", status_code=204)
def delete_project(pid: str, db: Session = Depends(get_db)):
    project = _get_or_404(db, pid)
    db.delete(project)
    db.commit()


@router.get("/{pid}/messages", response_model=list)
def list_messages(pid: str, db: Session = Depends(get_db)):
    """Convenience beyond the contract: full conversation, chronological."""
    project = _get_or_404(db, pid)
    from ..schemas import MessageOut
    return [MessageOut.model_validate(m) for m in sorted(project.messages, key=lambda m: m.created_at)]
