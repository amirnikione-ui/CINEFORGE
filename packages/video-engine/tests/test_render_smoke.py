"""Real render smoke test — skipped automatically when ffmpeg is absent."""

from __future__ import annotations

import os

import pytest

from video_engine import ffmpeg as ff
from video_engine import remotion_gen
from video_engine.timeline import (
    Clip,
    Timeline,
    Track,
    compile_ffmpeg_plan,
    to_remotion_props,
)

pytestmark = pytest.mark.skipif(not ff.has_ffmpeg(), reason="ffmpeg not installed")


def _timeline() -> Timeline:
    return Timeline(
        fps=30, width=640, height=360,
        tracks=[
            Track(name="base", kind="video", clips=[
                Clip.from_dict({"id": "a", "kind": "color", "start": 0, "duration": 1.5, "color": "#101623"}),
                Clip.from_dict({"id": "b", "kind": "color", "start": 1.5, "duration": 1.5, "color": "#0B0E14"}),
            ]),
            Track(name="t", kind="text", clips=[
                Clip.from_dict({"id": "t1", "kind": "text", "start": 0, "duration": 1.4,
                                "text": "HELLO CINEFORGE", "style": {"font_size": 48, "color": "#F5A524"},
                                "animation": {"in": 0.3, "out": 0.3}}),
            ]),
            Track(name="s", kind="audio", clips=[]),
        ],
    )


def test_real_render(tmp_path):
    out = tmp_path / "render.mp4"
    plan = compile_ffmpeg_plan(_timeline(), str(out), str(tmp_path / "work"))
    assert plan.command_count >= 3
    for step in plan.steps:
        ff.run(step.args, timeout=120)
    assert out.exists() and out.stat().st_size > 1000
    duration = ff.duration_of(str(out))
    assert 2.8 <= duration <= 3.4, f"expected ~3s, got {duration}"


def test_remotion_project_scaffold(tmp_path):
    manifest = remotion_gen.generate_remotion_project(_timeline(), str(tmp_path / "remotion"))
    assert (tmp_path / "remotion" / "src" / "CinematicComposition.tsx").exists()
    assert (tmp_path / "remotion" / "src" / "props.json").exists()
    assert manifest["composition"] == "Cinematic"
    props = to_remotion_props(_timeline())
    assert props["durationInFrames"] == 90
