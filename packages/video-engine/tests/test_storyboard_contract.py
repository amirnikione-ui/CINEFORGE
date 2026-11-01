"""Contract tests: docs/API_CONTRACTS.md storyboard v1 must render end-to-end.

Uses the exact scene rules from the binding contract (durations ±10%, scene
kinds, palette, aspect). CI job: engine-tests.
"""

from __future__ import annotations

import pytest

from video_engine.storyboard_adapter import (
    aspect_size,
    storyboard_to_timeline,
    validate_storyboard,
)
from video_engine.timeline import compile_ffmpeg_plan, total_duration
from video_engine.tools import StoryboardError, build_remotion_project, render_storyboard


@pytest.fixture()
def nova_runners_storyboard() -> dict:
    """The contract's own example, trimmed to contract-valid durations."""
    return {
        "schema_version": 1,
        "title": "Nova Runners — Cinematic Promo",
        "platform": "instagram",
        "aspect": "9:16",
        "fps": 30,
        "duration_target_s": 12,
        "palette": {"bg": "#0a0a12", "primary": "#7c5cff", "accent": "#00e5ff", "text": "#f5f5ff"},
        "music_mood": "dark-cinematic",
        "scenes": [
            {
                "id": "scene-01", "kind": "hook", "duration_s": 4.0,
                "headline": "RUN BEYOND LIMITS",
                "narration": "In a city that never slows down…",
                "visual_prompt": "dark cityscape, neon reflections, cinematic haze",
                "motion": {"style": "ken-burns", "intensity": 0.6},
                "transition_in": "fade",
            },
            {
                "id": "scene-02", "kind": "reveal", "duration_s": 5.0,
                "headline": "MEET NOVA RUNNERS",
                "visual_prompt": "sneaker hero shot, rim light",
                "motion": {"style": "zoom", "intensity": 0.4},
                "transition_in": "cut",
            },
            {
                "id": "scene-03", "kind": "outro", "duration_s": 3.0,
                "headline": "AVAILABLE NOW",
                "transition_in": "fade",
            },
        ],
    }


def test_valid_storyboard_passes(nova_runners_storyboard):
    assert validate_storyboard(nova_runners_storyboard) == []


def test_duration_rule_enforced(nova_runners_storyboard):
    bad = {**nova_runners_storyboard, "duration_target_s": 60}
    issues = validate_storyboard(bad)
    assert any("deviates" in i for i in issues)


def test_aspect_mapping():
    assert aspect_size("9:16") == (1080, 1920)
    assert aspect_size("16:9") == (1920, 1080)
    assert aspect_size("meh") == (1920, 1080)  # safe default


def test_storyboard_lowers_to_timeline(nova_runners_storyboard):
    tl = storyboard_to_timeline(nova_runners_storyboard)
    assert (tl.width, tl.height) == (1080, 1920)
    assert tl.fps == 30
    assert abs(total_duration(tl) - 12.0) < 0.01
    base = tl.tracks[0].clips
    texts = tl.tracks[1].clips
    assert [c.kind for c in base] == ["color", "color", "color"]
    assert len(texts) == 3
    assert texts[0].text == "RUN BEYOND LIMITS"
    assert texts[0].style["color"] == "#00e5ff"  # hook scenes use accent
    assert texts[2].style["color"] == "#00e5ff"  # outro uses accent too


def test_frames_fill_without_dead_ends(nova_runners_storyboard, tmp_path):
    missing = [None, "/nonexistent/frame.png", None]
    tl = storyboard_to_timeline(nova_runners_storyboard, frames=missing)
    plan = compile_ffmpeg_plan(tl, str(tmp_path / "o.mp4"), str(tmp_path / "w"))
    # image scene with a missing file must fall back to a color segment
    assert "color=c=" in " ".join(plan.steps[1].args)


def test_invalid_storyboard_raises(nova_runners_storyboard):
    bad = {**nova_runners_storyboard}
    bad["schema_version"] = 2
    with pytest.raises(StoryboardError):
        render_storyboard(bad, "/tmp/x.mp4", "/tmp/w")


def test_render_storyboard_real_render(nova_runners_storyboard, tmp_path):
    from video_engine.ffmpeg import has_ffmpeg
    if not has_ffmpeg():
        pytest.skip("ffmpeg not installed")
    out = tmp_path / "nova.mp4"
    result = render_storyboard(nova_runners_storyboard, str(out), str(tmp_path / "work"))
    from video_engine import ffmpeg as ff
    assert out.exists()
    assert 11.4 <= ff.duration_of(str(out)) <= 12.6


def test_remotion_project_from_storyboard(nova_runners_storyboard, tmp_path):
    manifest = build_remotion_project(nova_runners_storyboard, str(tmp_path / "remotion"))
    assert manifest["source"] == "storyboard-v1"
    assert (tmp_path / "remotion" / "src" / "CinematicComposition.tsx").exists()
    props = manifest["props"]
    assert props["durationInFrames"] == 360  # 12s * 30fps
