"""Director tools — registry per docs/API_CONTRACTS.md «Tool interface».

Every tool returns real artifacts persisted as Asset rows and always reports
`meta.provider` (transparency rule ADR-0004/0005). Heavy work (render) is a Job.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app import config, storage
from backend.app.models import Asset, Job, new_id

from cineforge_providers import get_registry
from cineforge_providers.base import ProviderError

from .storyboard import StoryboardLike, dump_storyboard


@dataclass
class ToolContext:
    session: AsyncSession
    project_id: str
    assets: dict[str, Asset] = field(default_factory=dict)   # scene_id → frame asset
    created: list[Asset] = field(default_factory=list)        # every asset made this pass

    async def add_asset(self, kind: str, filename: str, path, meta: dict[str, Any]) -> Asset:
        asset = Asset(
            id=new_id(), project_id=self.project_id, kind=kind, filename=filename,
            path=storage.rel_to_root(path), meta=meta,
        )
        self.session.add(asset)
        await self.session.flush()
        self.created.append(asset)
        return asset


@dataclass
class ToolReport:
    name: str
    provider: str
    summary: str
    ok: bool = True


# ---------------------------------------------------------------- tools ----

async def write_storyboard(ctx: ToolContext, storyboard: StoryboardLike) -> ToolReport:
    data = dump_storyboard(storyboard)
    path = storage.new_file_path(ctx.project_id, "storyboard", "storyboard.json")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    await ctx.add_asset("storyboard", "storyboard.json", path,
                        {"schema_version": 1, "scenes": len(data["scenes"]),
                         "duration_s": data["duration_target_s"]})
    return ToolReport("write_storyboard", "orchestrator",
                      f"storyboard: {len(data['scenes'])} scenes, {data['duration_target_s']}s")


async def generate_concept_frames(ctx: ToolContext, storyboard: StoryboardLike) -> ToolReport:
    """One frame per scene via the image chain (openai → mock fallback)."""
    pal = storyboard_palette(storyboard)
    providers_used: list[str] = []
    n = len(storyboard_scenes(storyboard))
    for i, scene in enumerate(storyboard_scenes(storyboard)):
        prompt = scene.get("visual_prompt") or scene.get("headline", "") or storyboard_title(storyboard)
        try:
            res = await get_registry().call(
                "image", prompt=prompt,
                width=1920 if storyboard_aspect(storyboard) == "16:9" else 1080,
                height=1080 if storyboard_aspect(storyboard) == "16:9" else 1920,
                palette=pal, seed=i + 1,
            )
        except ProviderError as exc:
            return ToolReport("generate_concept_frames", "chain", f"frame {i + 1} failed: {exc}", ok=False)
        providers_used.append(res.provider)
        fname = f"scene-{i + 1:02d}.{res.out.get('ext', 'png')}"
        fpath = storage.new_file_path(ctx.project_id, "frame", fname)
        fpath.write_bytes(res.out["image_bytes"])
        asset = await ctx.add_asset(
            "frame", fname, fpath,
            {"scene_id": scene.get("id"), "provider": res.provider,
             "prompt": prompt, "index": i})
        ctx.assets[str(scene.get("id"))] = asset
    return ToolReport("generate_concept_frames", "+".join(sorted(set(providers_used)) or "none"),
                      f"{n} concept frames")


async def generate_narration(ctx: ToolContext, storyboard: StoryboardLike) -> ToolReport:
    """Per-scene narration via the TTS chain; returns total speech seconds."""
    providers_used: list[str] = []
    total = 0.0
    for i, scene in enumerate(storyboard_scenes(storyboard)):
        text = (scene.get("narration") or "").strip()
        if not text:
            continue
        try:
            res = await get_registry().call("tts", text=text)
        except ProviderError as exc:
            return ToolReport("generate_narration", "chain", f"scene {i + 1} failed: {exc}", ok=False)
        providers_used.append(res.provider)
        fname = f"narration-{i + 1:02d}.{res.out.get('ext', 'wav')}"
        fpath = storage.new_file_path(ctx.project_id, "audio", fname)
        fpath.write_bytes(res.out["audio_bytes"])
        dur = float(res.out.get("duration_s", 0.0))
        total += dur
        await ctx.add_asset("audio", fname, fpath,
                            {"scene_id": scene.get("id"), "provider": res.provider,
                             "duration_s": dur, "kind": "narration",
                             "placeholder": bool(res.out.get("placeholder"))})
    return ToolReport("generate_narration", "+".join(sorted(set(providers_used)) or "none"),
                      f"narration tracks, ~{total:.1f}s total")


async def generate_music(ctx: ToolContext, storyboard: StoryboardLike) -> ToolReport:
    duration = float(storyboard.get("duration_target_s", 30.0)) if isinstance(storyboard, dict) \
        else storyboard.duration_target_s
    out = storage.new_file_path(ctx.project_id, "audio", "music.wav")
    try:
        res = await get_registry().call(
            "music", mood=storyboard_mood(storyboard), duration_s=duration,
            out_path=str(out))
    except ProviderError as exc:
        return ToolReport("generate_music", "chain", str(exc), ok=False)
    await ctx.add_asset("audio", out.name, out,
                        {"provider": res.provider, "kind": "music",
                         "duration_s": res.out.get("duration_s"), "mood": storyboard_mood(storyboard)})
    return ToolReport("generate_music", res.provider,
                      f"music bed {res.out.get('duration_s', 0):.0f}s ({res.out.get('synth', 'api')})")


async def build_remotion_project(ctx: ToolContext, storyboard: StoryboardLike) -> ToolReport:
    """Copy the Remotion template into the project workspace with storyboard injected."""
    from cineforge_video.remotion import build_project

    data = dump_storyboard(storyboard)
    src_dir = storage.new_file_path(ctx.project_id, "project", f"remotion-{data['title'][:40]}")
    try:
        out = build_project(data, src_dir)
    except Exception as exc:  # noqa: BLE001
        return ToolReport("build_remotion_project", "template", f"failed: {exc}", ok=False)
    await ctx.add_asset("project", out.name, out,
                        {"template": "CinematicPromo", "editable": True,
                         "entry": "src/CinematicPromo.tsx", "render_cmd": "npx remotion render"})
    return ToolReport("build_remotion_project", "remotion-template",
                      "editable TS project with storyboard props")


async def probe_media(path: str | Any) -> dict[str, Any]:
    from cineforge_video.ffmpeg_tools import probe

    return probe(str(path))


# --------------------------------------------------------- adapters ----
# Storyboard accessors that accept both pydantic Storyboard and plain dict,
# so the orchestrator never branches on the planner mode.

def storyboard_scenes(sb: StoryboardLike) -> list[dict[str, Any]]:
    if isinstance(sb, dict):
        return list(sb.get("scenes", []))
    return [s.model_dump() for s in sb.scenes]


def storyboard_palette(sb: StoryboardLike) -> dict[str, str]:
    pal = sb.get("palette", {}) if isinstance(sb, dict) else sb.palette.model_dump()
    return {k: pal.get(k, "") for k in ("bg", "primary", "accent", "text")}


def storyboard_aspect(sb: StoryboardLike) -> str:
    return sb.get("aspect", "9:16") if isinstance(sb, dict) else sb.aspect


def storyboard_title(sb: StoryboardLike) -> str:
    return sb.get("title", "Untitled") if isinstance(sb, dict) else sb.title


def storyboard_mood(sb: StoryboardLike) -> str:
    return sb.get("music_mood", "dark-cinematic") if isinstance(sb, dict) else sb.music_mood


def storyboard_platform(sb: StoryboardLike) -> str:
    return sb.get("platform", "instagram") if isinstance(sb, dict) else sb.platform


def storyboard_duration(sb: StoryboardLike) -> float:
    return float(sb.get("duration_target_s", 30.0)) if isinstance(sb, dict) else float(sb.duration_target_s)


def storyboard_fps(sb: StoryboardLike) -> int:
    return int(sb.get("fps", 30)) if isinstance(sb, dict) else int(sb.fps)
