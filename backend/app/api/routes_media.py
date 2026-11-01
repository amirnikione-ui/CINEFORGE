"""POST /api/media/analyze — M3 reverse-engineering entrypoint (M0 scope: engine analysis)."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..models import Asset
from ..storage import storage

router = APIRouter(prefix="/api", tags=["media"])


@router.post("/media/analyze")
def media_analyze(payload: dict, db: Session = Depends(get_db)):
    asset_id = payload.get("asset_id")
    url = payload.get("url")
    if url and not asset_id:
        raise HTTPException(status_code=501, detail="url analysis lands in M3 (CF-040..043)")
    if not asset_id:
        raise HTTPException(status_code=400, detail="asset_id required")
    asset = db.get(Asset, str(asset_id))
    if not asset:
        raise HTTPException(status_code=404, detail="asset not found")

    from video_engine.tools import analyze_video

    try:
        report = analyze_video(asset.path)
    except FileNotFoundError:
        raise HTTPException(status_code=410, detail="asset file missing from storage")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"analysis failed: {exc}")

    project_id = asset.project_id
    report_path = storage.new_path(project_id, "analysis", f"report_{asset.filename}.json")
    os_dir = report_path.rsplit("/", 1)[0]
    import os
    os.makedirs(os_dir, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    from ..models import Asset as AssetModel
    report_asset = AssetModel(
        project_id=project_id, kind="analysis", filename=report_path.rsplit("/", 1)[-1],
        path=report_path, meta={"source_asset_id": asset.id, "provider": "video-engine/analysis"},
    )
    db.add(report_asset)
    db.commit()
    db.refresh(report_asset)
    return {"report": report, "asset": {
        "id": report_asset.id, "kind": "analysis", "filename": report_asset.filename,
    }}
