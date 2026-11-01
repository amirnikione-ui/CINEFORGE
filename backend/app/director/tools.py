"""Director tools — the stable tool interface from docs/API_CONTRACTS.md.

| Tool                     | Source                                                |
| write_storyboard         | LLM (if configured) → deterministic fallback          |
| generate_concept_frames  | mock tier (real PNG files) — CF-031 upgrades          |
| generate_narration       | mock tier (timing bed) — CF-032 upgrades              |
| generate_music           | mock tier (synthesized) — CF-033 upgrades             |
| render_slideshow         | video_engine (FFmpeg plan compiler, real MP4)         |
| build_remotion_project   | video_engine (editable React/TS scaffold)             |
| probe_media/analyze_video| video_engine                                          |

Every result carries `provider` for the honest `meta.provider` convention.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.orm import Session

from video_engine import analysis as va
from video_engine import ffmpeg as vff
from video_engine.storyboard_adapter import validate_storyboard
from video_engine.tools import (
    StoryboardError,
    build_remotion_project as engine_build_remotion,
    render_storyboard as engine_render_storyboard,
)

from ..core.config import get_settings
from ..models import Asset, Project
from ..providers import base as pb
from ..storage import storage

logger = logging.getLogger("cineforge.director.tools")


class ToolError(RuntimeError):
    pass


@dataclass
class ToolCtx:
    db: Session
    project: Project
    storyboard: dict[str, Any] | None = None
    frame_paths: list[str] | None = None
    narration_path: str | None = None
    music_path: str | None = None

    def save_asset(self, kind: str, abs_path: str, filename: str, meta: dict) -> Asset:
        stored = storage.copy_in(self.project.id, kind, abs_path, filename)
        asset = Asset(project_id=self.project.id, kind=kind, filename=filename,
                      path=stored, meta=meta)
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)
        return asset


# ------------------------------------------------------------------ tools


def write_storyboard(ctx: ToolCtx, args: dict) -> dict:
    brief = str(args.get("brief") or ctx.project.brief or ctx.project.title)
    style = str(args.get("style") or ctx.project.style)
    platform = str(args.get("platform") or ctx.project.platform)
    duration = float(args.get("duration_hint_s") or ctx.project.duration_hint_s)

    provider, sb = "mock", None
    for llm in pb.llm_chain():
        if not llm.is_configured():
            continue
        try:
            system = ("You are CINEFORGE's director. Reply ONLY with a JSON storyboard matching "
                      "schema_version 1: {schema_version, title, platform, aspect, fps, "
                      "duration_target_s, palette{bg,primary,accent,text}, music_mood, scenes:[{id,kind,"
                      "duration_s,headline,body,narration,visual_prompt,motion{style,intensity},transition_in}]}. "
                      "sum(scenes.duration_s) within ±10% of duration_target_s. Kinds: hook|reveal|typography|outro.")
            result = llm.complete(system, f"Brief: {brief}\nStyle: {style}\nPlatform: {platform}\nDuration: {duration}s",
                                  json_mode=True)
            if result.data and not validate_storyboard(result.data):
                sb, provider = result.data, llm.name
                break
        except pb.ProviderError as exc:
            logger.warning("llm %s failed, trying next / falling back: %s", llm.name, exc)
    if sb is None:
        sb = pb.mock_llm_storyboard(brief, style, platform, duration)
    if validate_storyboard(sb):
        raise ToolError(f"storyboard invalid: {validate_storyboard(sb)}")

    ctx.storyboard = sb
    path = storage.new_path(ctx.project.id, "storyboard", "storyboard.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(sb, fh, ensure_ascii=False, indent=2)
    asset = ctx.save_asset("storyboard", path, "storyboard.json", {"provider": provider})
    return {"provider": provider, "assets": [asset], "storyboard": sb}


def generate_concept_frames(ctx: ToolCtx, args: dict) -> dict:
    if not ctx.storyboard:
        raise ToolError("write_storyboard must run first")
    frames: list[str] = []
    tmp_dir = storage.project_dir(ctx.project.id, "tmp_frames")
    for i, scene in enumerate(ctx.storyboard["scenes"]):
        width, height = _aspect_wh(ctx.storyboard.get("aspect", "16:9"))
        out = os.path.join(tmp_dir, f"frame_{i + 1:02d}.png")
        pb.mock_image(str(scene.get("visual_prompt", "frame")), out, width, height)
        frames.append(out)
    ctx.frame_paths = frames
    assets = [
        ctx.save_asset("frame", p, os.path.basename(p), {"provider": "mock", "scene": i + 1,
                                                         "prompt": ctx.storyboard["scenes"][i].get("visual_prompt", "")})
        for i, p in enumerate(frames)
    ]
    return {"provider": "mock", "assets": assets}


def generate_narration(ctx: ToolCtx, args: dict) -> dict:
    if not ctx.storyboard:
        raise ToolError("write_storyboard must run first")
    duration = float(ctx.storyboard.get("duration_target_s", 30))
    tmp = storage.project_dir(ctx.project.id, "tmp_audio")
    out = os.path.join(tmp, "narration.wav")
    pb.mock_narration(duration, out)
    ctx.narration_path = out
    asset = ctx.save_asset("audio", out, "narration.wav",
                           {"provider": "mock", "note": "placeholder narration bed — CF-032 wires real TTS",
                            "duration_s": duration})
    return {"provider": "mock", "assets": [asset]}


def generate_music(ctx: ToolCtx, args: dict) -> dict:
    if not ctx.storyboard:
        raise ToolError("write_storyboard must run first")
    mood = str(ctx.storyboard.get("music_mood", "dark-cinematic"))
    duration = float(ctx.storyboard.get("duration_target_s", 30))
    tmp = storage.project_dir(ctx.project.id, "tmp_audio")
    out = os.path.join(tmp, f"music_{uuid.uuid4().hex[:6]}.wav")
    pb.mock_music(mood, duration, out)
    ctx.music_path = out
    asset = ctx.save_asset("audio", out, os.path.basename(out),
                           {"provider": "mock", "mood": mood, "duration_s": duration})
    return {"provider": "mock", "assets": [asset]}


def render_slideshow(ctx: ToolCtx, args: dict) -> dict:
    if not ctx.storyboard:
        raise ToolError("write_storyboard must run first")
    out = storage.new_path(ctx.project.id, "video", "final_v1.mp4")
    work = storage.project_dir(ctx.project.id, "render_work")
    result = engine_render_storyboard(
        ctx.storyboard, out, work,
        frames=ctx.frame_paths, narration_path=ctx.narration_path, music_path=ctx.music_path,
    )
    asset = ctx.save_asset("video", out, "final_v1.mp4",
                           {"provider": "video-engine/ffmpeg", "duration_s": result["duration_s"],
                            "width": result["width"], "height": result["height"], "fps": result["fps"]})
    return {"provider": "video-engine/ffmpeg", "assets": [asset], "render": result}


def build_remotion_project_tool(ctx: ToolCtx, args: dict) -> dict:
    if not ctx.storyboard:
        raise ToolError("write_storyboard must run first")
    target_dir = storage.new_path(ctx.project.id, "project", "remotion")
    manifest = engine_build_remotion(ctx.storyboard, target_dir)
    asset = ctx.save_asset("project", os.path.join(target_dir, "src", "props.json"),
                           "remotion_props.json", {"provider": "video-engine/remotion",
                                                   "manifest": {"files": manifest["files"],
                                                                "composition": manifest["composition"]}})
    return {"provider": "video-engine/remotion", "assets": [asset]}


def probe_media(ctx: ToolCtx, args: dict) -> dict:
    path = args.get("path")
    if not path or not os.path.exists(path):
        raise ToolError("probe_media needs a valid path")
    return {"provider": "video-engine/ffprobe", "probe": vff.probe(str(path))}


def analyze_video(ctx: ToolCtx, args: dict) -> dict:
    path = args.get("path")
    if not path or not os.path.exists(path):
        raise ToolError("analyze_video needs a valid path")
    return {"provider": "video-engine/analysis", "report": va.analyze(str(path))}


TOOL_FUNCS: dict[str, Callable[[ToolCtx, dict], dict]] = {
    "write_storyboard": write_storyboard,
    "generate_concept_frames": generate_concept_frames,
    "generate_narration": generate_narration,
    "generate_music": generate_music,
    "render_slideshow": render_slideshow,
    "build_remotion_project": build_remotion_project_tool,
    "probe_media": probe_media,
    "analyze_video": analyze_video,
}


def _aspect_wh(aspect: str) -> tuple[int, int]:
    return {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080), "4:5": (1080, 1350)}.get(
        (aspect or "16:9").strip(), (1920, 1080))
