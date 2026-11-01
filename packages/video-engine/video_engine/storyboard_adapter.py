"""Storyboard v1 (docs/API_CONTRACTS.md, binding) -> video_engine Timeline.

The team contract says renderer implementations MUST accept the storyboard schema
verbatim — this adapter is that promise, mapping the director's central artifact
onto the FFmpeg-compilable Timeline IR.

Storyboard (excerpt):
    { schema_version, title, platform, aspect, fps, duration_target_s,
      palette: {bg, primary, accent, text}, music_mood, scenes: [...] }
Scene:
    { id, kind, duration_s, headline, body, narration, visual_prompt,
      motion: {style, intensity}, transition_in }
"""

from __future__ import annotations

from typing import Any

from .timeline import Animation, Clip, Timeline, Track

_ASPECTS: dict[str, tuple[int, int]] = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
}

_TRANSITION_FADES: dict[str, float] = {
    "fade": 0.4,
    "cut": 0.0,
    "slide": 0.25,
    "reveal": 0.5,
}


def aspect_size(aspect: str) -> tuple[int, int]:
    return _ASPECTS.get((aspect or "16:9").strip(), (1920, 1080))


def validate_storyboard(sb: dict[str, Any]) -> list[str]:
    """Return a list of contract violations (empty list = valid)."""
    issues: list[str] = []
    if int(sb.get("schema_version", 0)) != 1:
        issues.append("schema_version must be 1")
    scenes = sb.get("scenes") or []
    if not scenes:
        issues.append("storyboard needs at least one scene")
    target = float(sb.get("duration_target_s", 0) or 0)
    total = sum(float(s.get("duration_s", 0) or 0) for s in scenes)
    if target > 0 and scenes and abs(total - target) > 0.1 * target:
        issues.append(f"sum(scenes.duration_s)={total:.2f} deviates >10% from duration_target_s={target:.2f}")
    for i, scene in enumerate(scenes):
        if float(scene.get("duration_s", 0) or 0) <= 0:
            issues.append(f"scene[{i}].duration_s must be > 0")
    return issues


def storyboard_to_timeline(
    sb: dict[str, Any],
    *,
    frames: list[str | None] | None = None,
    narration_path: str | None = None,
    music_path: str | None = None,
    narration_volume: float = 0.9,
    music_volume: float = 0.35,
) -> Timeline:
    """Lower a storyboard to a renderable Timeline.

    frames: optional per-scene image paths (None falls back to palette bg color
    clip — the pipeline never dead-ends while assets are still generating).
    """
    fps = int(sb.get("fps", 30))
    width, height = aspect_size(str(sb.get("aspect", "16:9")))
    palette = sb.get("palette") or {}
    bg = str(palette.get("bg", "#0A0C10"))
    accent = str(palette.get("accent", "#F5A524"))
    text_color = str(palette.get("text", "#FFFFFF"))

    scenes = list(sb.get("scenes") or [])
    base_clips: list[Clip] = []
    text_clips: list[Clip] = []
    cursor = 0.0
    for i, scene in enumerate(scenes):
        dur = max(float(scene.get("duration_s", 4.0) or 4.0), 0.2)
        frame = frames[i] if frames and i < len(frames) and frames[i] else None
        base_clips.append(Clip(
            id=str(scene.get("id", f"scene-{i + 1:02d}")),
            kind="image" if frame else "color",
            start=round(cursor, 3),
            duration=round(dur, 3),
            color=bg,
            asset_path=frame,
        ))
        headline = scene.get("headline")
        if headline:
            fade = _TRANSITION_FADES.get(str(scene.get("transition_in", "fade")), 0.4)
            text_clips.append(Clip(
                id=f"text-{i + 1:02d}",
                kind="text",
                start=round(cursor + min(0.3, dur / 8), 3),
                duration=round(max(dur - 0.4, 0.6), 3),
                text=str(headline),
                style={"font_size": max(30, height // 14), "color": accent if scene.get("kind") in ("hook", "outro") else text_color},
                animation=Animation(fade_in=fade, fade_out=min(fade, dur / 4)),
            ))
        cursor += dur

    audio_clips: list[Clip] = []
    total = round(cursor, 3)
    if narration_path:
        audio_clips.append(Clip(id="narration", kind="audio", start=0.0, duration=total,
                                asset_path=narration_path, volume=narration_volume))
    if music_path:
        audio_clips.append(Clip(id="music", kind="audio", start=0.0, duration=total,
                                asset_path=music_path, volume=music_volume))

    return Timeline(
        fps=fps, width=width, height=height, background=bg,
        tracks=[
            Track(name="base", kind="video", clips=base_clips),
            Track(name="titles", kind="text", clips=text_clips),
            Track(name="sound", kind="audio", clips=audio_clips),
        ],
    )
