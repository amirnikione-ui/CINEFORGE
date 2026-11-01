"""Tool implementations for the Director agent (contract: docs/API_CONTRACTS.md §Tools).

Every tool receives a ``ToolContext`` and returns a ``ToolResult`` with a human
summary, the created ``Asset`` rows and arbitrary ``data``. All produced
artifacts carry ``meta.provider`` — the offline mock tier is always labeled.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from sqlalchemy.orm import Session

from ai_agent import TOOLS_JSON  # noqa: F401  (re-exported for the LLM tool loop)
from ai_providers import ProviderRegistry, ProviderError, get_registry
from video_engine import ffmpeg_tools as ff
from video_engine import remotion_runner
from video_engine import slideshow

from app import storage
from app.agent import mock_director
from app.agent.prompts import DIRECTOR_SYSTEM, build_storyboard_request
from app.jobs import submit as submit_job
from app.models import Asset, Job, Project, utc_now_iso

log = logging.getLogger("cineforge.tools")

ASPECT_DIMS: dict[str, tuple[int, int]] = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "1:1": (1080, 1080),
}


class ToolError(RuntimeError):
    """Raised when a tool cannot complete; the orchestrator reports it honestly."""


@dataclass
class ToolContext:
    db: Session
    project: Project
    workspace: dict[str, str]
    registry: ProviderRegistry


@dataclass
class ToolResult:
    summary: str
    assets: list[Asset] = field(default_factory=list)
    data: dict = field(default_factory=dict)


# --------------------------------------------------------------------- helpers


def _register_asset(ctx: ToolContext, kind: str, path: str, meta: dict) -> Asset:
    asset = Asset(
        project_id=ctx.project.id,
        kind=kind,
        filename=Path(path).name,
        path=str(path),
        meta=meta,
    )
    ctx.db.add(asset)
    ctx.db.flush()
    return asset


def _dims(storyboard: dict) -> tuple[int, int]:
    aspect = str(storyboard.get("aspect") or "9:16")
    return ASPECT_DIMS.get(aspect, ASPECT_DIMS["9:16"])


def _extract_json(text: str) -> dict:
    """Parse a JSON object out of an LLM reply (tolerates code fences)."""
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise ToolError("LLM reply contained no JSON object")
        return json.loads(match.group(0))


def _next_version(ctx: ToolContext, kind: str) -> int:
    count = (
        ctx.db.query(Asset)
        .filter(Asset.project_id == ctx.project.id, Asset.kind == kind)
        .count()
    )
    return count + 1


def _latest_asset(ctx: ToolContext, kind: str) -> Asset | None:
    return (
        ctx.db.query(Asset)
        .filter(Asset.project_id == ctx.project.id, Asset.kind == kind)
        .order_by(Asset.created_at.desc(), Asset.id.desc())
        .first()
    )


def _scene_assets(ctx: ToolContext, kind: str, exclude_music: bool = False) -> list[Asset]:
    rows = (
        ctx.db.query(Asset)
        .filter(Asset.project_id == ctx.project.id, Asset.kind == kind)
        .order_by(Asset.created_at.asc(), Asset.id.asc())
        .all()
    )
    if kind == "audio" and exclude_music:

        def _scene_index(asset: Asset) -> int:
            try:
                return int(asset.meta.get("scene_index", 0))
            except (TypeError, ValueError):
                return 0

        rows = [a for a in rows if not a.meta.get("music")]
        rows.sort(key=_scene_index)
    return rows


# ----------------------------------------------------------------------- tools


def tool_write_storyboard(ctx: ToolContext, args: dict) -> ToolResult:
    brief = str(args.get("brief") or ctx.project.brief or "").strip()
    style = str(args.get("style") or ctx.project.style or "cinematic-dark")
    platform = str(args.get("platform") or ctx.project.platform or "instagram")
    duration_hint = int(args.get("duration_hint_s") or ctx.project.duration_hint_s or 30)
    prepared = args.get("prepared")

    provider_name = "mock-director"
    if isinstance(prepared, dict):
        storyboard = mock_director.normalize_storyboard(
            prepared, style=style, platform=platform, duration_hint_s=duration_hint
        )
    else:
        llm = ctx.registry.first_available("llm")
        if llm is not None and llm.name != "mock":
            reply, provider_name = ctx.registry.run_with_fallback(
                "llm",
                lambda p: p.complete(
                    DIRECTOR_SYSTEM,
                    [
                        {"role": "user", "content": build_storyboard_request(
                            brief, style, platform, duration_hint
                        )}
                    ],
                    json_mode=True,
                ),
            )
            storyboard = mock_director.normalize_storyboard(
                _extract_json(reply), style=style, platform=platform, duration_hint_s=duration_hint
            )
        else:
            storyboard = mock_director.build_storyboard(
                brief, style=style, platform=platform, duration_hint_s=duration_hint
            )

    version = _next_version(ctx, "storyboard")
    out_path = storage.safe_join(ctx.workspace["storyboards"], f"storyboard-v{version}.json")
    Path(out_path).write_text(json.dumps(storyboard, indent=2, ensure_ascii=False), encoding="utf-8")
    asset = _register_asset(
        ctx,
        "storyboard",
        out_path,
        {
            "provider": provider_name,
            "schema_version": storyboard.get("schema_version", 1),
            "scenes_count": len(storyboard.get("scenes", [])),
            "duration_target_s": storyboard.get("duration_target_s"),
            "version": version,
        },
    )
    return ToolResult(
        summary=(
            f"Storyboard v{version} ready: '{storyboard.get('title')}' — "
            f"{len(storyboard['scenes'])} scenes, {storyboard.get('duration_target_s')}s "
            f"({storyboard.get('aspect')}, {storyboard.get('fps')} fps) [{provider_name}]"
        ),
        assets=[asset],
        data={"storyboard": storyboard},
    )


def tool_generate_concept_frames(ctx: ToolContext, args: dict) -> ToolResult:
    storyboard = args.get("storyboard") or (_latest_asset(ctx, "storyboard") and json.loads(
        Path(_latest_asset(ctx, "storyboard").path).read_text(encoding="utf-8")  # type: ignore[union-attr]
    ))
    if not isinstance(storyboard, dict) or not storyboard.get("scenes"):
        raise ToolError("generate_concept_frames: no storyboard available")
    width, height = _dims(storyboard)
    palette = storyboard.get("palette") or {}
    scenes = storyboard["scenes"]
    assets: list[Asset] = []
    by_provider: dict[str, int] = {}
    for i, scene in enumerate(scenes):
        out_path = storage.safe_join(ctx.workspace["frames"], f"scene-{i + 1:02d}.png")

        def make(provider, _i=i, _scene=scene, _out=out_path):
            return provider.generate_image(
                prompt=str(_scene.get("visual_prompt") or _scene.get("headline") or "cinematic frame"),
                out_path=_out,
                width=width,
                height=height,
                palette=palette,
                headline=str(_scene.get("headline") or ""),
                scene_index=_i + 1,
                scene_count=len(scenes),
            )

        try:
            meta_img, provider_name = ctx.registry.run_with_fallback("image", make)
        except ProviderError as exc:
            raise ToolError(f"frame generation failed for {scene.get('id')}: {exc}") from exc
        by_provider[provider_name] = by_provider.get(provider_name, 0) + 1
        asset = _register_asset(
            ctx,
            "frame",
            out_path,
            {
                "provider": provider_name,
                "scene_id": scene.get("id"),
                "scene_index": i,
                "width": meta_img.get("width", width),
                "height": meta_img.get("height", height),
                "prompt": str(scene.get("visual_prompt") or "")[:500],
            },
        )
        assets.append(asset)
    breakdown = ", ".join(f"{name}×{n}" for name, n in by_provider.items())
    return ToolResult(
        summary=f"Generated {len(assets)} concept frames ({breakdown})",
        assets=assets,
        data={"frames": [a.path for a in assets]},
    )


def tool_generate_narration(ctx: ToolContext, args: dict) -> ToolResult:
    storyboard = args.get("storyboard") or (_latest_asset(ctx, "storyboard") and json.loads(
        Path(_latest_asset(ctx, "storyboard").path).read_text(encoding="utf-8")  # type: ignore[union-attr]
    ))
    if not isinstance(storyboard, dict) or not storyboard.get("scenes"):
        raise ToolError("generate_narration: no storyboard available")
    assets: list[Asset] = []
    by_provider: dict[str, int] = {}
    for i, scene in enumerate(storyboard["scenes"]):
        text = str(scene.get("narration") or "").strip()
        if not text:
            continue
        out_path = storage.safe_join(ctx.workspace["audio"], f"scene-{i + 1:02d}.wav")
        try:
            meta_tts, provider_name = ctx.registry.run_with_fallback(
                "tts", lambda p, _t=text, _o=out_path: p.synthesize(_t, _o)
            )
        except ProviderError as exc:
            raise ToolError(f"narration synthesis failed for {scene.get('id')}: {exc}") from exc
        by_provider[provider_name] = by_provider.get(provider_name, 0) + 1
        asset = _register_asset(
            ctx,
            "audio",
            out_path,
            {
                "provider": provider_name,
                "scene_id": scene.get("id"),
                "scene_index": i,
                "duration_s": meta_tts.get("duration_s"),
                "text": text[:300],
            },
        )
        assets.append(asset)
    breakdown = ", ".join(f"{name}×{n}" for name, n in by_provider.items())
    return ToolResult(
        summary=f"Synthesized {len(assets)} narration clips ({breakdown})",
        assets=assets,
        data={"narrations": [a.path for a in assets]},
    )


def tool_generate_music(ctx: ToolContext, args: dict) -> ToolResult:
    mood = str(args.get("mood") or "dark-cinematic")
    duration = float(args.get("duration_s") or 30.0)
    out_path = storage.safe_join(ctx.workspace["audio"], "music.wav")
    try:
        meta_music, provider_name = ctx.registry.run_with_fallback(
            "music", lambda p: p.generate_music(mood, duration, out_path)
        )
    except ProviderError as exc:
        raise ToolError(f"music generation failed: {exc}") from exc
    asset = _register_asset(
        ctx,
        "audio",
        out_path,
        {
            "provider": provider_name,
            "music": True,
            "mood": mood,
            "duration_s": meta_music.get("duration_s", duration),
        },
    )
    return ToolResult(
        summary=f"Music bed '{mood}' ({meta_music.get('duration_s', duration):.1f}s) [{provider_name}]",
        assets=[asset],
        data={"music_path": out_path},
    )


def tool_render_slideshow(ctx: ToolContext, args: dict) -> ToolResult:
    storyboard = args.get("storyboard") or (_latest_asset(ctx, "storyboard") and json.loads(
        Path(_latest_asset(ctx, "storyboard").path).read_text(encoding="utf-8")  # type: ignore[union-attr]
    ))
    if not isinstance(storyboard, dict) or not storyboard.get("scenes"):
        raise ToolError("render_slideshow: no storyboard available")

    frames = [Path(a.path) for a in _scene_assets(ctx, "frame") if not a.meta.get("poster")]
    narrations = [a.path for a in _scene_assets(ctx, "audio", exclude_music=True)]
    music_row = next(
        (a for a in reversed(_scene_assets(ctx, "audio")) if a.meta.get("music")), None
    )
    if len(frames) < len(storyboard["scenes"]):
        raise ToolError(
            f"render_slideshow: have {len(frames)} frames for "
            f"{len(storyboard['scenes'])} scenes — run generate_concept_frames first"
        )

    version = _next_version(ctx, "video")
    out_path = storage.safe_join(ctx.workspace["video"], f"final_v{version}.mp4")
    job = Job(project_id=ctx.project.id, kind="render", status="pending", progress=0.0)
    ctx.db.add(job)
    # Commit BEFORE handing the job to the executor thread: the runner updates the
    # row through its own session and cannot see another session's uncommitted row.
    ctx.db.commit()
    ctx.db.refresh(job)

    def _run(progress_cb: Callable[[float], None]) -> dict:
        return slideshow.render_slideshow(
            storyboard=storyboard,
            frames=frames,
            narration_paths=narrations,
            music_path=music_row.path if music_row else None,
            out_path=out_path,
            workdir=storage.safe_join(ctx.workspace["video"], f".work-v{version}"),
            progress_cb=progress_cb,
        )

    try:
        result = submit_job(job.id, _run, wait=True, timeout=1800)
    except Exception as exc:
        raise ToolError(f"render failed: {exc}") from exc

    asset = _register_asset(
        ctx,
        "video",
        out_path,
        {
            "provider": "ffmpeg-local",
            "duration_s": result.get("duration_s"),
            "width": result.get("width"),
            "height": result.get("height"),
            "fps": result.get("fps"),
            "size_bytes": result.get("size_bytes"),
            "version": version,
            "job_id": job.id,
        },
    )

    # Poster thumbnail for the studio preview (best-effort).
    try:
        poster_path = storage.safe_join(ctx.workspace["video"], f"poster_v{version}.jpg")
        ff.extract_frame(out_path, 1.0, poster_path)
        _register_asset(ctx, "frame", poster_path, {"poster": True, "provider": "ffmpeg-local", "video_version": version})
    except Exception as exc:  # noqa: BLE001 - poster is optional
        log.warning("poster extraction failed: %s", exc)

    size_mb = result.get("size_bytes", 0) / (1024 * 1024)
    return ToolResult(
        summary=(
            f"Rendered final_v{version}.mp4 — {result.get('duration_s', 0):.1f}s, "
            f"{result.get('width')}×{result.get('height')} @ {result.get('fps')} fps, "
            f"{size_mb:.1f} MB [ffmpeg-local]"
        ),
        assets=[asset],
        data={"render": result, "job_id": job.id},
    )


def tool_build_remotion_project(ctx: ToolContext, args: dict) -> ToolResult:
    storyboard = args.get("storyboard") or (_latest_asset(ctx, "storyboard") and json.loads(
        Path(_latest_asset(ctx, "storyboard").path).read_text(encoding="utf-8")  # type: ignore[union-attr]
    ))
    if not isinstance(storyboard, dict) or not storyboard.get("scenes"):
        raise ToolError("build_remotion_project: no storyboard available")
    out_dir = storage.safe_join(ctx.workspace["projects"], "remotion-cinematicpromo")
    info = remotion_runner.scaffold_project(storyboard, out_dir)
    asset = _register_asset(
        ctx,
        "project",
        info["path"],
        {
            "provider": "remotion-template",
            "composition": info.get("composition"),
            "files_count": info.get("files_count"),
            "entry": info.get("entry"),
            "template": info.get("template"),
        },
    )
    return ToolResult(
        summary=(
            f"Editable Remotion project scaffolded ({info.get('files_count')} files, "
            f"composition '{info.get('composition')}')"
        ),
        assets=[asset],
        data={"scaffold": info},
    )


def _resolve_media(ctx: ToolContext, args: dict) -> str:
    asset_id = args.get("asset_id")
    path = args.get("path")
    if asset_id:
        asset = ctx.db.get(Asset, str(asset_id))
        if asset is None or str(asset.project_id) != str(ctx.project.id):
            raise ToolError(f"asset {asset_id} not found in this project")
        return asset.path
    if path:
        candidate = storage.safe_join(ctx.workspace["root"], str(path)) \
            if not Path(path).is_absolute() else str(path)
        if not Path(candidate).exists():
            raise ToolError(f"media file not found: {path}")
        return candidate
    latest_video = _latest_asset(ctx, "video")
    if latest_video is None:
        raise ToolError("no media available — render something first")
    return latest_video.path


def tool_probe_media(ctx: ToolContext, args: dict) -> ToolResult:
    path = _resolve_media(ctx, args)
    info = ff.summary(path)
    return ToolResult(
        summary=(
            f"{Path(path).name}: {info.get('duration_s', 0):.2f}s, {info.get('width')}×"
            f"{info.get('height')} @ {info.get('fps')} fps, audio={info.get('has_audio')}"
        ),
        data={"probe": info},
    )


def tool_analyze_video(ctx: ToolContext, args: dict) -> ToolResult:
    path = _resolve_media(ctx, args)
    info = ff.summary(path)
    cuts = ff.scene_detect(path)
    report = {
        "analyzed_at": utc_now_iso(),
        "media": info,
        "scene_cuts": cuts,
        "cut_count": len(cuts),
        "avg_shot_s": (info.get("duration_s", 0) / len(cuts)) if cuts else info.get("duration_s", 0),
    }
    out_path = storage.safe_join(ctx.workspace["video"], f"analysis_{utc_now_iso()[:19].replace(':', '')}.json")
    Path(out_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
    asset = _register_asset(ctx, "analysis", out_path, {"provider": "ffmpeg-analysis", "cut_count": len(cuts)})
    return ToolResult(
        summary=(
            f"Analysis of {Path(path).name}: {len(cuts)} scene cuts, "
            f"avg shot {report['avg_shot_s']:.2f}s [ffmpeg-analysis]"
        ),
        assets=[asset],
        data={"analysis": report},
    )


# --------------------------------------------------------------------- dispatch

_TOOLS: dict[str, Callable[[ToolContext, dict], ToolResult]] = {
    "write_storyboard": tool_write_storyboard,
    "generate_concept_frames": tool_generate_concept_frames,
    "generate_narration": tool_generate_narration,
    "generate_music": tool_generate_music,
    "render_slideshow": tool_render_slideshow,
    "build_remotion_project": tool_build_remotion_project,
    "probe_media": tool_probe_media,
    "analyze_video": tool_analyze_video,
}


def execute_tool(name: str, args: dict, ctx: ToolContext) -> ToolResult:
    """Execute a registered tool by name; raises ToolError on failure."""
    fn = _TOOLS.get(name)
    if fn is None:
        raise ToolError(f"unknown tool '{name}'")
    log.info("tool %s on project %s", name, ctx.project.id)
    return fn(ctx, dict(args or {}))
