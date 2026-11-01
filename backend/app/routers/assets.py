"""Asset file serving + media analysis (docs/API_CONTRACTS.md §Assets)."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import storage
from app.agent.tools import ToolContext, execute_tool
from app.db import get_db
from app.models import Asset, Project
from app.schemas import MediaAnalyzeRequest

router = APIRouter(tags=["assets"])

_MEDIA_TYPES: dict[str, str] = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/x-m4a",
    ".mp3": "audio/mpeg",
    ".json": "application/json",
    ".srt": "text/plain",
}


@router.get("/api/assets/{asset_id}/file")
def get_asset_file(asset_id: str, db: Session = Depends(get_db)) -> FileResponse:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="asset not found")
    path = Path(asset.path)
    if not path.exists() or path.is_dir():
        if asset.kind == "project":
            raise HTTPException(
                status_code=404,
                detail="directory asset — the editable project lives on the server workspace",
            )
        raise HTTPException(status_code=404, detail="asset file missing on disk")
    media_type = _MEDIA_TYPES.get(path.suffix.lower(), "application/octet-stream")
    return FileResponse(path, media_type=media_type, filename=asset.filename)


@router.post("/api/media/analyze")
def analyze_media(body: MediaAnalyzeRequest, db: Session = Depends(get_db)) -> dict:
    if not body.asset_id:
        raise HTTPException(
            status_code=400, detail="asset_id is required (URL analysis ships in M3)"
        )
    asset = db.get(Asset, body.asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="asset not found")
    project = db.get(Project, asset.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")

    from ai_providers import get_registry

    ctx = ToolContext(
        db=db,
        project=project,
        workspace=storage.workspace(project.id),
        registry=get_registry(),
    )
    result = execute_tool("analyze_video", {"asset_id": asset.id}, ctx)
    return {"summary": result.summary, "analysis": result.data.get("analysis", {})}
