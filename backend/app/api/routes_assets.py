"""Assets & jobs — GET /api/jobs/{id}, GET /api/assets/{id}/file per contract."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..models import Asset, Job
from ..schemas import JobOut
from ..storage import content_type_for

router = APIRouter(prefix="/api", tags=["assets", "jobs"])


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.get("/assets/{asset_id}/file")
def get_asset_file(asset_id: str, db: Session = Depends(get_db)):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="asset not found")
    if not os.path.exists(asset.path):
        raise HTTPException(status_code=410, detail="asset file missing from storage")
    return FileResponse(
        asset.path,
        media_type=content_type_for(asset.kind, asset.filename),
        filename=asset.filename,
    )
