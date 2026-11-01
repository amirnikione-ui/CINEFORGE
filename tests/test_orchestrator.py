"""Director orchestrator end-to-end: brief → storyboard → frames → audio → mp4."""
from __future__ import annotations

import json
from pathlib import Path

from app.agent.orchestrator import Director
from app.db import SessionLocal
from app.models import Asset, Project


def _make_project(brief: str = "A 12-second cinematic promo for NOVA running shoes, dark mood") -> str:
    with SessionLocal() as db:
        project = Project(title="Nova Runners", brief=brief, style="cinematic-dark",
                          platform="instagram", duration_hint_s=12, status="draft")
        db.add(project)
        db.commit()
        return project.id


def test_mock_director_full_pipeline():
    pid = _make_project()
    with SessionLocal() as db:
        project = db.get(Project, pid)
        assistant, assets, jobs = Director(db).handle_message(
            project, "A 12-second cinematic promo for NOVA running shoes, dark mood"
        )
        kinds = {a.kind for a in assets}
        assert {"storyboard", "frame", "audio", "video", "project"} <= kinds
        assert assistant.meta["tools_used"] and assistant.meta["llm_provider"] == "mock"
        assert not assistant.meta["revision"]
        assert any(j.kind == "render" and j.status == "done" for j in jobs)

        video = next(a for a in assets if a.kind == "video")
        assert Path(video.path).exists() and Path(video.path).stat().st_size > 50_000

        sb_asset = next(a for a in assets if a.kind == "storyboard")
        sb = json.loads(Path(sb_asset.path).read_text(encoding="utf-8"))
        assert sb["schema_version"] == 1
        total = sum(s["duration_s"] for s in sb["scenes"])
        assert abs(total - 12.0) / 12.0 < 0.10, total

        project_asset = next(a for a in assets if a.kind == "project")
        assert Path(project_asset.path).is_dir()
        assert (Path(project_asset.path) / "public" / "storyboard.json").exists()


def test_revision_flow_shortens():
    pid = _make_project("A 16-second cinematic promo for PULSE headphones")
    with SessionLocal() as db:
        project = db.get(Project, pid)
        Director(db).handle_message(project, "A 16-second cinematic promo for PULSE headphones")
        project2 = db.get(Project, pid)
        assistant2, assets2, _ = Director(db).handle_message(
            project2, "make it punchier and shorter, warmer palette"
        )
        assert assistant2.meta["revision"] is True
        videos = [a for a in assets2 if a.kind == "video"]
        assert len(videos) == 1
        assert Path(videos[0].path).exists()
        sb_assets = [a for a in assets2 if a.kind == "storyboard"]
        assert len(sb_assets) == 1
        sb = json.loads(Path(sb_assets[0].path).read_text(encoding="utf-8"))
        assert sb["duration_target_s"] < 16.0  # "shorter" → 0.75 factor
