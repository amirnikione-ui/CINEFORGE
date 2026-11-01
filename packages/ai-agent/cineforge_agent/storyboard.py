"""Storyboard schema-v1 helpers: deterministic offline builder + validation.

The storyboard is the director's central artifact (docs/API_CONTRACTS.md).
The offline builder produces a professional 5-beat structure from the brief:
hook → reveal → typography (proof) → typography (feature) → outro (CTA).
"""
from __future__ import annotations

import re
from typing import Any, Union

from backend.app.schemas import Palette, Scene, SceneMotion, Storyboard

StoryboardLike = Union[Storyboard, dict]

_BEATS = ("hook", "reveal", "typography", "typography", "outro")
_WEIGHTS = (0.18, 0.28, 0.22, 0.18, 0.14)

_PALETTES: dict[str, Palette] = {
    "cinematic-dark": Palette(bg="#0a0a12", primary="#7c5cff", accent="#00e5ff", text="#f5f5ff"),
    "clean-light": Palette(bg="#f7f7fb", primary="#3b5bfd", accent="#00b8d9", text="#101018"),
    "bold-energy": Palette(bg="#120608", primary="#ff3d5a", accent="#ffd166", text="#fff5f5"),
}


def _subject(brief: str) -> str:
    """Very light heuristic subject extraction for offline headlines."""
    cleaned = re.sub(r"\s+", " ", brief).strip()
    for sep in (".", "!", "?", "\n"):
        cleaned = cleaned.split(sep)[0]
    words = cleaned.split()
    stop = {"make", "create", "build", "a", "an", "the", "for", "with", "and",
            "of", "to", "in", "on", "please", "video", "promo", "teaser", "ad"}
    core = [w for w in words if w.lower() not in stop]
    return " ".join(core[:4]) if core else (cleaned[:40] or "Your Product")


def build_offline_storyboard(
    brief: str,
    *,
    title: str = "CINEFORGE Promo",
    platform: str = "instagram",
    style: str = "cinematic-dark",
    duration_hint_s: float = 30.0,
    narration_language: str = "en",
) -> Storyboard:
    subject = _subject(brief)
    motions = ["ken-burns", "zoom", "slide", "reveal", "ken-burns"]
    beats = [
        ("hook", "EVERY LEGEND", "starts in the dark", f"Cinematic establishing shot: {subject}"),
        ("reveal", subject.upper(), "the next generation", f"Product hero reveal: {subject}"),
        ("typography", "BUILT TO WIN", "precision in every frame", f"Feature montage: {subject}"),
        ("typography", "FEEL THE DIFFERENCE", "engineered for you", f"Lifestyle shot: {subject}"),
        ("outro", subject.upper(), "Get yours today", f"Logo + call to action: {subject}"),
    ]
    scenes: list[Scene] = []
    for i, (kind, headline, body, visual) in enumerate(beats):
        scenes.append(
            Scene(
                id=f"scene-{i + 1:02d}",
                kind=kind,  # type: ignore[arg-type]
                duration_s=round(duration_hint_s * _WEIGHTS[i], 2),
                headline=headline,
                body=body,
                narration=_narration_for(kind, subject, narration_language),
                visual_prompt=visual,
                motion=SceneMotion(style=motions[i], intensity=0.6),
                transition_in="fade" if i == 0 else "slide" if kind == "typography" else "cut",
            )
        )
    palette = _PALETTES.get(style, _PALETTES["cinematic-dark"])
    aspect = {"youtube": "16:9", "web": "16:9"}.get(platform, "9:16")
    return Storyboard(
        title=title, platform=platform, aspect=aspect, fps=30,
        duration_target_s=duration_hint_s, palette=palette,
        music_mood=style, scenes=scenes,
    ).normalized()


def _narration_for(kind: str, subject: str, lang: str) -> str:
    if lang.startswith("fa"):
        return {
            "hook": "در شهری که هرگز نمی‌ایستد، یک اسم همه را مکث می‌دهد.",
            "reveal": f"این {subject} است. نسخه‌ی بعدی.",
            "typography": "ساخته‌شده برای برد.",
            "outro": f"{subject} — همین امروز مالکش شو.",
        }.get(kind, "")
    return {
        "hook": "In a city that never slows down, one name stops everyone.",
        "reveal": f"This is {subject}. The next generation.",
        "typography": "Built to win. Designed for you.",
        "outro": f"{subject}. Get yours today.",
    }.get(kind, "")


def validate_storyboard(data: dict[str, Any]) -> Storyboard:
    sb = Storyboard.model_validate(data)
    if not sb.scenes:
        raise ValueError("storyboard must contain at least one scene")
    if sb.schema_version != 1:
        raise ValueError(f"unsupported storyboard schema_version: {sb.schema_version}")
    return sb.normalized()


def dump_storyboard(sb: StoryboardLike) -> dict[str, Any]:
    return sb.model_dump() if isinstance(sb, Storyboard) else dict(sb)
