"""Projects CRUD + ProjectDetail (contracts «Projects»)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app import storage
from backend.app.db import SessionLocal
from backend.app.models import Job, Message, Project
from backend.app.schemas import (JobOut, MessageOut, ProjectCreate, ProjectDetail,
                                 ProjectOut, AssetOut)

router = APIRouter(prefix="/api/projects", tags=["projects"])


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


async def _get_or_404(session: AsyncSession, pid: str) -> Project:
    """Eager-load relationships — async sessions forbid lazy IO (MissingGreenlet)."""
    res = await session.execute(
        select(Project)
        .where(Project.id == pid)
        .options(selectinload(Project.messages), selectinload(Project.assets),
                 selectinload(Project.jobs)))
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    return project


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(body: ProjectCreate, session: AsyncSession = Depends(get_session)):
    project = Project(title=body.title, brief=body.brief, style=body.style or "cinematic-dark",
                      platform=body.platform, duration_hint_s=body.duration_hint_s,
                      status="draft")
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


@router.get("", response_model=list[ProjectOut])
async def list_projects(session: AsyncSession = Depends(get_session)):
    res = await session.execute(select(Project).order_by(Project.created_at.desc()))
    return list(res.scalars())


@router.get("/{pid}", response_model=ProjectDetail)
async def get_project(pid: str, session: AsyncSession = Depends(get_session)):
    project = await _get_or_404(session, pid)
    return ProjectDetail(
        project=ProjectOut.model_validate(project),
        messages=[MessageOut.model_validate(m) for m in project.messages],
        assets=[AssetOut.model_validate(a) for a in project.assets],
        jobs=[JobOut.model_validate(j) for j in project.jobs],
    )


@router.delete("", status_code=204)
@router.delete("/{pid}", status_code=204)
async def delete_project(pid: str, session: AsyncSession = Depends(get_session)):
    project = await _get_or_404(session, pid)
    await session.delete(project)
    await session.commit()
    storage.purge_project(pid)
