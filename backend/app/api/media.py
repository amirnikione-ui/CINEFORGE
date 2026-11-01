"""Jobs + Assets + Media endpoints (contracts «Assets & Jobs», «media/analyze»)."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app import config, storage
from backend.app.api.projects import get_session
from backend.app.jobs_runner import dispatch
from backend.app.models import Asset, Job, new_id
from backend.app.schemas import AnalysisReport, JobOut

from cineforge_video.analysis import analyze_video
from cineforge_video.ffmpeg_tools import probe

router = APIRouter(tags=["jobs-assets-media"])

_CONTENT_TYPES = {"storyboard": "application/json", "frame": "image/png",
                  "audio": "audio/wav", "video": "video/mp4",
                  "analysis": "application/json", "project": "application/zip"}


@router.get("/api/jobs/{job_id}", response_model=JobOut)
async def get_job(job_id: str, session: AsyncSession = Depends(get_session)):
    job = await session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.get("/api/assets/{asset_id}/file")
async def asset_file(asset_id: str, session: AsyncSession = Depends(get_session)):
    asset = await session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="asset not found")
    path = storage.resolve_rel(asset.path)
    if not path.is_file():
        raise HTTPException(status_code=410, detail="asset file missing from storage")
    media = _CONTENT_TYPES.get(asset.kind, "application/octet-stream")
    if asset.kind == "project":
        return FileResponse(path.parent / "storyboard.json", media_type="application/json")
    return FileResponse(path, media_type=media, filename=asset.filename)


@router.post("/api/media/analyze", response_model=JobOut, status_code=202)
async def analyze(body: dict, session: AsyncSession = Depends(get_session)):
    """M3 reverse-engineering entrypoint — runs as a Job (inline/celery)."""
    asset_id = body.get("asset_id")
    if not asset_id:
        raise HTTPException(status_code=400, detail="asset_id required")
    asset = await session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="asset not found")
    if asset.kind not in ("video", "frame", "audio"):
        raise HTTPException(status_code=400, detail="asset is not a media file")
    job = Job(id=new_id(), project_id=asset.project_id, kind="analyze", status="pending",
              progress=0.0, payload={"asset_id": asset.id})
    session.add(job)
    await session.commit()
    await session.refresh(job)
    dispatch(job.id)
    return job


@router.post("/api/media/probe")
async def probe_media(body: dict, session: AsyncSession = Depends(get_session)):
    asset_id = body.get("asset_id")
    if not asset_id:
        raise HTTPException(status_code=400, detail="asset_id required")
    asset = await session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="asset not found")
    path = storage.resolve_rel(asset.path)
    try:
        return probe(path)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"probe failed: {exc}") from exc


@router.post("/api/projects/{pid}/upload", response_model=dict, status_code=201)
async def upload(pid: str, file: UploadFile = File(...), kind: str = "video",
                 session: AsyncSession = Depends(get_session)):
    """Reference-media upload (reverse-engineering input) with size+kind guard."""
    from backend.app.models import Project

    project = await session.get(Project, pid)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    if kind not in ("video", "audio", "frame"):
        raise HTTPException(status_code=400, detail="kind must be video|audio|frame")
    data = await file.read()
    if len(data) > config.MAX_PROJECT_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail="upload exceeds CINEFORGE_MAX_PROJECT_MB")
    path = storage.save_bytes(pid, kind, file.filename or "upload.bin", data)
    asset = Asset(id=new_id(), project_id=pid, kind=kind, filename=path.name,
                  path=storage.rel_to_root(path),
                  meta={"source": "upload", "bytes": len(data)})
    session.add(asset)
    await session.commit()
    await session.refresh(asset)
    return {"id": asset.id, "kind": asset.kind, "filename": asset.filename}


@router.get("/api/analysis/{job_id}", response_model=AnalysisReport)
async def analysis_result(job_id: str, session: AsyncSession = Depends(get_session)):
    job = await session.get(Job, job_id)
    if not job or job.kind != "analyze":
        raise HTTPException(status_code=404, detail="analysis job not found")
    if job.status != "done":
        raise HTTPException(status_code=202, detail=f"job status: {job.status}")
    return AnalysisReport.model_validate(job.result.get("report", {}))
