"""Job task implementations — shared by Celery and the inline executor (ADR-0008)."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

log = logging.getLogger("cineforge.tasks")


def execute_job(job_id: str) -> dict:
    """Entry point for both executors. Blocking on purpose (worker context)."""
    return asyncio.run(_execute_job(job_id))


async def _execute_job(job_id: str) -> dict:
    from backend.app import config as cfg
    from backend.app.db import SessionLocal
    from backend.app.models import Asset, Job, new_id
    from backend.app import storage

    async with SessionLocal() as session:
        job = await session.get(Job, job_id)
        if not job:
            log.error("job %s not found", job_id)
            return {"ok": False, "error": "job not found"}
        job.status = "running"
        job.progress = 0.05
        await session.commit()
        try:
            if job.kind == "render":
                result = await _run_render(session, job, cfg, storage, Asset, new_id)
            elif job.kind == "analyze":
                result = await _run_analyze(session, job, storage, Asset, new_id)
            else:
                raise ValueError(f"unsupported job kind: {job.kind}")
            job.status = "done"
            job.progress = 1.0
            job.result = result
            await session.commit()
            return result
        except Exception as exc:  # noqa: BLE001 — job failure must be visible, not a crash
            log.exception("job %s failed", job_id)
            job.status = "failed"
            job.error = f"{type(exc).__name__}: {exc}"
            await session.commit()
            return {"ok": False, "error": job.error}


async def _run_render(session, job, cfg, storage, Asset, new_id) -> dict:
    from cineforge_video.slideshow import render_slideshow

    payload = job.payload or {}
    storyboard = payload.get("storyboard") or {}
    project_id = job.project_id
    workdir = Path(cfg.STORAGE_ROOT) / project_id / "work" / job.id
    workdir.mkdir(parents=True, exist_ok=True)

    frame_paths: list[Path | None] = []
    for asset_id in (payload.get("frame_assets") or {}).values():
        asset = await session.get(Asset, asset_id)
        frame_paths.append(storage.resolve_rel(asset.path) if asset else None)

    from sqlalchemy import select

    res = await session.execute(
        select(Asset).where(Asset.project_id == project_id, Asset.kind == "audio"))
    audio_assets = list(res.scalars())
    narration_paths = [storage.resolve_rel(a.path) for a in audio_assets
                       if (a.meta or {}).get("kind") == "narration"]
    music = next((storage.resolve_rel(a.path) for a in audio_assets
                  if (a.meta or {}).get("kind") == "music"), None)

    job.progress = 0.2
    await session.commit()

    out = Path(cfg.STORAGE_ROOT) / project_id / "video" / f"final_{job.id[:8]}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)

    from cineforge_video.ffmpeg_tools import probe

    await render_slideshow(storyboard, frame_paths, narration_paths, music, out, workdir)
    job.progress = 0.9
    await session.commit()

    meta = probe(out)
    asset = Asset(id=new_id(), project_id=project_id, kind="video",
                  filename=out.name, path=storage.rel_to_root(out),
                  meta={"provider": "ffmpeg-slideshow", "duration_s": meta["duration_s"],
                        "width": meta["width"], "height": meta["height"], "fps": meta["fps"],
                        "engine": "cineforge-video/ADR-0006a"})
    session.add(asset)
    await session.flush()
    return {"asset_id": asset.id, "duration_s": meta["duration_s"],
            "width": meta["width"], "height": meta["height"]}


async def _run_analyze(session, job, storage, Asset, new_id) -> dict:
    from cineforge_video.analysis import analyze_video

    asset = await session.get(Asset, (job.payload or {}).get("asset_id"))
    if not asset:
        raise ValueError("source asset missing")
    report = analyze_video(storage.resolve_rel(asset.path))
    return {"report": report, "source_asset_id": asset.id}
