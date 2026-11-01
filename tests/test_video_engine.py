"""video-engine tests: golden filters + real FFmpeg integration (skipif)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from video_engine.errors import VideoEngineError
from video_engine.ffmpeg import has_ffmpeg, probe
from video_engine.slideshow import build_scene_filter, canvas_size, render_slideshow

SB = {
    "schema_version": 1,
    "title": "T",
    "platform": "instagram",
    "aspect": "9:16",
    "fps": 30,
    "duration_target_s": 6.0,
    "palette": {"bg": "#0a0a12", "primary": "#7c5cff", "accent": "#00e5ff", "text": "#f5f5ff"},
    "music_mood": "dark-cinematic",
    "scenes": [
        {"id": "scene-01", "kind": "hook", "duration_s": 3.0, "headline": "RUN BEYOND LIMITS",
         "motion": {"style": "ken-burns", "intensity": 0.6}, "transition_in": "fade"},
        {"id": "scene-02", "kind": "outro", "duration_s": 3.0, "headline": "CINEFORGE",
         "motion": {"style": "reveal", "intensity": 0.5}, "transition_in": "cut"},
    ],
}


def test_canvas_size_aspect_then_platform_fallback():
    assert canvas_size(SB) == (1080, 1920)
    sb = dict(SB)
    sb["aspect"] = "16:9"
    assert canvas_size(sb) == (1920, 1080)
    sb["aspect"] = "weird"
    sb["platform"] = "tiktok"
    assert canvas_size(sb) == (1080, 1920)


def test_golden_scene_filter_contains_expected_pieces(tmp_path: Path):
    (tmp_path / "headline_00.txt").write_text("RUN BEYOND LIMITS")
    (tmp_path / "headline_00b.txt").write_text(" ")
    (tmp_path / "body_00.txt").write_text(" ")
    flt = build_scene_filter(
        SB["scenes"][0], index=0, width=1080, height=1920, fps=30, duration_s=3.0,
        palette=SB["palette"], font_path=Path("/tmp/fake.ttf"),
        headline_txt=str(tmp_path / "headline_00.txt"), body_txt=str(tmp_path / "body_00.txt"),
    )
    assert "zoompan" in flt
    assert "kenburns-like" not in flt  # no placeholder junk
    assert "drawtext" in flt and "fontfile='/tmp/fake.ttf'" in flt
    assert "fade=t=in:st=0:d=0.40" in flt
    assert "yuv420p" in flt


def test_golden_zoom_style_expression(tmp_path: Path):
    (tmp_path / "headline_00.txt").write_text("X")
    (tmp_path / "headline_00b.txt").write_text(" ")
    (tmp_path / "body_00.txt").write_text(" ")
    scene = dict(SB["scenes"][0])
    scene["motion"] = {"style": "zoom", "intensity": 1.0}
    flt = build_scene_filter(
        scene, index=0, width=1080, height=1920, fps=30, duration_s=3.0,
        palette=SB["palette"], font_path=Path("/tmp/f.ttf"),
        headline_txt=str(tmp_path / "headline_00.txt"), body_txt=str(tmp_path / "body_00.txt"),
    )
    assert "1-cos(2*PI*in/90)" in flt  # 3.0s * 30fps = 90 frames


def test_render_requires_frames(tmp_path: Path):
    with pytest.raises(VideoEngineError):
        render_slideshow(SB, [], tmp_path / "out.mp4")


@pytest.mark.skipif(not has_ffmpeg(), reason="ffmpeg not available")
def test_real_render_integration(tmp_path: Path):
    from ai_providers.image import PillowArtImage

    art = PillowArtImage()
    frames = []
    for i, scene in enumerate(SB["scenes"]):
        out = tmp_path / f"f{i}.png"
        art.generate(scene["headline"], size=(270, 480), out_path=out, palette=SB["palette"], seed_text=scene["id"])
        frames.append(out)
    out = tmp_path / "final.mp4"
    stages = []

    info = render_slideshow(
        SB, [str(f) for f in frames], out,
        progress_cb=lambda p, s: stages.append(p),
    )
    assert out.is_file() and out.stat().st_size > 10_000
    assert info["duration_s"] == pytest.approx(6.0, abs=0.6)
    assert info["width"] == 270 or info["width"] == 1080  # canvas_size says 1080x1920
    probed = probe(out)
    assert probed["video"]["width"] == 1080 and probed["video"]["height"] == 1920
    assert stages and stages[-1] == 1.0
