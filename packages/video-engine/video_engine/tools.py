"""Engine-side implementations of the stable tool interface
(docs/API_CONTRACTS.md — director ↔ tools).

The director orchestrator (backend, FORGE) calls these; provider-backed tools
(generate_concept_frames / generate_narration / generate_music) live behind the
provider registry and hand file paths to the functions here. Tool results always
include `meta.provider` at the backend layer; engine functions return plain dicts.
"""

from __future__ import annotations

import os
from typing import Any

from . import analysis as va
from . import ffmpeg as ff
from . import timeline as vt
from .remotion_gen import generate_remotion_project
from .storyboard_adapter import storyboard_to_timeline, validate_storyboard

__all__ = [
    "probe_media", "render_slideshow", "build_remotion_project",
    "analyze_video", "render_storyboard", "StoryboardError",
]


class StoryboardError(ValueError):
    """Raised when a storyboard violates the binding v1 contract."""


def probe_media(path: str) -> dict[str, Any]:
    info = ff.probe(path)
    streams = info.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    return {
        "duration_s": float(info.get("format", {}).get("duration", 0) or 0),
        "width": video.get("width"),
        "height": video.get("height"),
        "fps": video.get("r_frame_rate"),
        "streams": streams,
    }


def render_storyboard(
    sb: dict[str, Any],
    out_path: str,
    work_dir: str,
    *,
    frames: list[str | None] | None = None,
    narration_path: str | None = None,
    music_path: str | None = None,
) -> dict[str, Any]:
    """Validate + lower a storyboard to a rendered MP4 (render_slideshow core)."""
    issues = validate_storyboard(sb)
    if issues:
        raise StoryboardError("; ".join(issues))
    tl = storyboard_to_timeline(sb, frames=frames, narration_path=narration_path,
                                music_path=music_path)
    plan = vt.compile_ffmpeg_plan(tl, out_path, work_dir)
    for step in plan.steps:
        ff.run(step.args, timeout=240)
    return {
        "path": out_path,
        "duration_s": round(plan.duration, 3),
        "width": plan.width,
        "height": plan.height,
        "fps": plan.fps,
        "steps": [s.name for s in plan.steps],
    }


# Alias matching the contract's tool name
def render_slideshow(sb: dict[str, Any], frames: list[str | None], narration: str | None,
                     music: str | None, out_path: str, work_dir: str) -> dict[str, Any]:
    return render_storyboard(sb, out_path, work_dir, frames=frames,
                             narration_path=narration, music_path=music)


def build_remotion_project(sb: dict[str, Any], project_dir: str) -> dict[str, Any]:
    """Scaffold an editable Remotion (React/TS) project from a storyboard."""
    issues = validate_storyboard(sb)
    if issues:
        raise StoryboardError("; ".join(issues))
    tl = storyboard_to_timeline(sb)
    manifest = generate_remotion_project(tl, project_dir)
    manifest["source"] = "storyboard-v1"
    return manifest


def analyze_video(path: str) -> dict[str, Any]:
    """M3 reverse-engineering entrypoint (M0 scope: probe/cuts/palette)."""
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    return va.analyze(path)
