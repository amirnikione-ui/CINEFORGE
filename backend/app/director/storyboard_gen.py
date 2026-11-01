"""Deterministic storyboard-v1 generator — the offline director's pen (ADR-0005).

Produces the binding schema from docs/API_CONTRACTS.md verbatim. When an LLM is
configured the orchestrator asks it first (same schema) and falls back to this.
"""

from __future__ import annotations

import re
from typing import Any

_STYLE_PALETTES: dict[str, dict[str, str]] = {
    "cinematic-dark": {"bg": "#0a0a12", "primary": "#7c5cff", "accent": "#00e5ff", "text": "#f5f5ff"},
    "bright-commercial": {"bg": "#101014", "primary": "#ffd166", "accent": "#ff5d73", "text": "#ffffff"},
    "clean-corporate": {"bg": "#0e1116", "primary": "#4f8cff", "accent": "#8ef6e4", "text": "#f2f5f7"},
}

_SCENE_ARC: list[str] = ["hook", "reveal", "typography", "typography", "reveal", "outro"]

_MOTIONS: list[dict[str, Any]] = [
    {"style": "ken-burns", "intensity": 0.6},
    {"style": "zoom", "intensity": 0.45},
    {"style": "reveal", "intensity": 0.5},
    {"style": "slide", "intensity": 0.35},
]


def _headlines_from(brief: str) -> list[str]:
    words = re.findall(r"[A-Za-z\u0600-\u06FF]{3,}", brief or "")
    stop = {"for", "with", "and", "the", "a", "an", "of", "to", "in", "on", "seconds", "second"}
    keys = [w for w in words if w.lower() not in stop][:6]
    product = " ".join(keys[:3]).upper() if keys else "YOUR PRODUCT"
    return [
        product or "SOMETHING NEW",
        f"MEET {product}" if product else "MEET THE FUTURE",
        "BUILT FOR YOU",
        "SIMPLE. POWERFUL.",
        "SEE IT IN ACTION",
        "AVAILABLE NOW",
    ]


def build_storyboard(brief: str, style: str = "cinematic-dark",
                     platform: str = "web", duration_hint_s: float = 30.0) -> dict[str, Any]:
    duration = float(duration_hint_s or 30)
    aspect = {"instagram": "9:16", "tiktok": "9:16", "youtube": "16:9", "web": "16:9"}.get(platform, "16:9")
    scene_count = max(2, min(6, round(duration / 5)))
    per = round(duration / scene_count, 2)
    headlines = _headlines_from(brief)
    palette = _STYLE_PALETTES.get(style or "cinematic-dark", _STYLE_PALETTES["cinematic-dark"])

    scenes: list[dict[str, Any]] = []
    for i in range(scene_count):
        kind = "outro" if i == scene_count - 1 else _SCENE_ARC[i % 4]
        dur = per if i < scene_count - 1 else round(duration - per * (scene_count - 1), 2)
        scenes.append({
            "id": f"scene-{i + 1:02d}",
            "kind": kind,
            "duration_s": max(dur, 0.8),
            "headline": headlines[i % len(headlines)],
            "body": (brief or "")[:120] if i == 1 else None,
            "narration": f"{headlines[i % len(headlines)].capitalize()}. {(brief or '')[:80]}".strip(),
            "visual_prompt": f"{(brief or 'product')}, {style or 'cinematic-dark'} mood, cinematic haze",
            "motion": _MOTIONS[i % len(_MOTIONS)],
            "transition_in": "fade" if i % 2 == 0 else "cut",
        })

    return {
        "schema_version": 1,
        "title": (brief or "Untitled production")[:80],
        "platform": platform or "web",
        "aspect": aspect,
        "fps": 30,
        "duration_target_s": duration,
        "palette": palette,
        "music_mood": "dark-cinematic" if "dark" in (style or "") else "uplifting",
        "scenes": scenes,
    }
