"""Video engine integration: the real FFmpeg slideshow pipeline (skip if no ffmpeg)."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

ffmpeg = shutil.which("ffmpeg")
pytestmark = pytest.mark.skipif(ffmpeg is None, reason="ffmpeg not available")

STORYBOARD = {
    "schema_version": 1,
    "title": "Engine Test",
    "platform": "instagram",
    "aspect": "9:16",
    "fps": 24,
    "duration_target_s": 4.0,
    "palette": {"bg": "#0a0a12", "primary": "#7c5cff", "accent": "#00e5ff", "text": "#f5f5ff"},
    "music_mood": "dark-cinematic",
    "scenes": [
        {
            "id": "scene-01",
            "kind": "hook",
            "duration_s": 2.0,
            "headline": "RUN BEYOND",
            "body": "",
            "narration": "This is Nova, a bolder way to run.",
            "visual_prompt": "dark city, neon",
            "motion": {"style": "ken-burns", "intensity": 0.5},
            "transition_in": "fade",
        },
        {
            "id": "scene-02",
            "kind": "outro",
            "duration_s": 2.0,
            "headline": "NOVA. START TONIGHT.",
            "body": "",
            "narration": "Nova is ready tonight.",
            "visual_prompt": "hero wide shot",
            "motion": {"style": "zoom", "intensity": 0.6},
            "transition_in": "cut",
        },
    ],
}


@pytest.fixture(scope="module")
def rendered(tmp_path_factory) -> dict:
    from ai_providers.mock import MockImage, MockMusic, MockTTS
    from video_engine.slideshow import render_slideshow

    tmp = tmp_path_factory.mktemp("engine")
    frames = []
    for i, scene in enumerate(STORYBOARD["scenes"]):
        p = tmp / f"scene-{i + 1:02d}.png"
        MockImage().generate_image(
            scene["visual_prompt"], str(p), width=1080, height=1920,
            palette=STORYBOARD["palette"], headline=scene["headline"],
            scene_index=i + 1, scene_count=2,
        )
        frames.append(str(p))
    narrations = []
    for i, scene in enumerate(STORYBOARD["scenes"]):
        p = tmp / f"narr-{i + 1:02d}.wav"
        MockTTS().synthesize(scene["narration"], str(p))
        narrations.append(str(p))
    music = tmp / "music.wav"
    MockMusic().generate_music("dark-cinematic", 4.0, str(music))

    out = tmp / "final.mp4"
    return render_slideshow(
        storyboard=STORYBOARD,
        frames=frames,
        narration_paths=narrations,
        music_path=str(music),
        out_path=str(out),
        workdir=str(tmp / "work"),
    )


def test_render_produces_real_video(rendered):
    path = Path(rendered["path"])
    assert path.exists() and path.stat().st_size > 50_000
    assert rendered["width"] == 1080 and rendered["height"] == 1920
    assert abs(rendered["duration_s"] - 4.0) / 4.0 < 0.15, rendered["duration_s"]


def test_probe_summary(rendered):
    from video_engine.ffmpeg_tools import summary

    info = summary(rendered["path"])
    assert info["duration_s"] > 0
    assert info["width"] == 1080
    assert info["has_audio"] is True
    assert info["fps"] == pytest.approx(24, rel=0.05)


def test_scene_detect_runs(rendered):
    from video_engine.ffmpeg_tools import scene_detect

    cuts = scene_detect(rendered["path"], threshold=0.2)
    assert isinstance(cuts, list)  # 0..N cuts — must not raise
