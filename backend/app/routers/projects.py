"""Project CRUD (docs/API_CONTRACTS.md §Projects)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import storage
from app.db import get_db
from app.models import Asset, Job, Message, Project
from app.schemas import AssetOut, JobOut, MessageOut, ProjectCreate, ProjectDetail, ProjectOut

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)) -> Project:
    project = Project(
        title=body.title,
        brief=body.brief,
        style=body.style,
        platform=body.platform,
        duration_hint_s=body.duration_hint_s,
        status="draft",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    storage.workspace(project.id)  # materialize the workspace eagerly
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)) -> list[Project]:
    return db.query(Project).order_by(Project.created_at.desc()).all()


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: str, db: Session = Depends(get_db)) -> ProjectDetail:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    messages = (
        db.query(Message)
        .filter(Message.project_id == project_id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )
    assets = (
        db.query(Asset)
        .filter(Asset.project_id == project_id)
        .order_by(Asset.created_at.asc(), Asset.id.asc())
        .all()
    )
    jobs = (
        db.query(Job)
        .filter(Job.project_id == project_id)
        .order_by(Job.created_at.asc(), Job.id.asc())
        .all()
    )
    return ProjectDetail(
        project=ProjectOut.model_validate(project),
        messages=[MessageOut.model_validate(m) for m in messages],
        assets=[AssetOut.model_validate(a) for a in assets],
        jobs=[JobOut.model_validate(j) for j in jobs],
    )


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str, db: Session = Depends(get_db)) -> None:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    db.query(Message).filter(Message.project_id == project_id).delete()
    db.query(Asset).filter(Asset.project_id == project_id).delete()
    db.query(Job).filter(Job.project_id == project_id).delete()
    db.delete(project)
    db.commit()
    storage.purge_project(project_id)
