"""Timeline compiler tests (pure Python — no ffmpeg needed)."""

from __future__ import annotations

import os

from video_engine.timeline import (
    Clip,
    Timeline,
    Track,
    compile_ffmpeg_plan,
    timeline_from_dict,
    to_remotion_props,
    total_duration,
)


def _sample_timeline() -> Timeline:
    return Timeline(
        fps=30, width=1920, height=1080, background="#0A0C10",
        tracks=[
            Track(name="base", kind="video", clips=[
                Clip.from_dict({"id": "bg1", "kind": "color", "start": 0, "duration": 4, "color": "#101623"}),
                Clip.from_dict({"id": "bg2", "kind": "color", "start": 4, "duration": 2, "color": "#0B0E14"}),
            ]),
            Track(name="titles", kind="text", clips=[
                Clip.from_dict({"id": "t1", "kind": "text", "start": 0.3, "duration": 3,
                                "text": "CINEFORGE", "style": {"font_size": 120, "color": "#F5A524"},
                                "animation": {"in": 0.5, "out": 0.5}}),
            ]),
            Track(name="sound", kind="audio", clips=[]),
        ],
    )


def test_total_duration():
    assert total_duration(_sample_timeline()) == 6.0


def test_compile_plan_shape():
    tl = _sample_timeline()
    plan = compile_ffmpeg_plan(tl, "/tmp/out.mp4", "/tmp/work")
    names = [s.name for s in plan.steps]
    assert names[0].startswith("segment:")
    assert "concat" in names
    assert names[-1] == "finalize"
    assert plan.duration == 6.0
    # text is composited in the finalize pass (never inflates duration)
    finalize = next(s for s in plan.steps if s.name == "finalize")
    joined = " ".join(finalize.args)
    assert "drawtext" in joined and "CINEFORGE" in joined
    assert "between(t" in joined  # enable window over global time


def test_roundtrip_from_dict():
    tl = _sample_timeline()
    from video_engine.timeline import timeline_to_dict
    clone = timeline_from_dict(timeline_to_dict(tl))
    assert total_duration(clone) == 6.0
    assert clone.tracks[1].clips[0].text == "CINEFORGE"
    assert clone.tracks[1].clips[0].animation.fade_in == 0.5


def test_remotion_projection():
    props = to_remotion_props(_sample_timeline())
    assert props["fps"] == 30
    assert props["durationInFrames"] == 180
    assert len(props["scenes"]) == 3
    assert props["scenes"][1]["text"] == "CINEFORGE"


def test_missing_asset_never_dead_ends():
    tl = Timeline(fps=30, width=1080, height=1920,
                  tracks=[Track(name="v", kind="video", clips=[
                      Clip.from_dict({"id": "x", "kind": "image", "start": 0, "duration": 2,
                                      "asset_path": "/nonexistent/frame.png"}),
                  ])])
    plan = compile_ffmpeg_plan(tl, "/tmp/out.mp4", "/tmp/work2")
    args = " ".join(plan.steps[0].args)
    assert "color=c=" in args  # falls back to a dark segment instead of failing
    assert "1080x1920" in args
