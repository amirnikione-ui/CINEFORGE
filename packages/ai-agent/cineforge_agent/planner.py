"""Planning: LLM storyboard via provider chain, deterministic offline fallback.

The plan is recorded in message meta for full auditability:
`[{step: write_storyboard, ...}, {step: generate_concept_frames, ...}, ...]`.
"""
from __future__ import annotations

import re
from typing import Any

from backend.app.schemas import Storyboard

from cineforge_providers import get_registry
from cineforge_providers.base import ProviderError
from cineforge_providers.llm import extract_json

from .storyboard import build_offline_storyboard, validate_storyboard

_SYSTEM_PROMPT = """You are CINEFORGE's director-agent. Convert the user's brief into a storyboard JSON.
Rules:
- Output ONLY a JSON object matching this schema (schema_version 1):
{"schema_version":1,"title":str,"platform":"instagram|youtube|tiktok|web","aspect":"9:16|16:9",
 "fps":30,"duration_target_s":number,"palette":{"bg":hex,"primary":hex,"accent":hex,"text":hex},
 "music_mood":str,"scenes":[{"id":"scene-01","kind":"hook|reveal|typography|outro","duration_s":number,
 "headline":str,"body":str,"narration":str,"visual_prompt":str,
 "motion":{"style":"ken-burns|slide|zoom|reveal","intensity":0..1},"transition_in":"fade|cut|slide"}]}
- 4 to 6 scenes; sum(scenes.duration_s) within ±10% of duration_target_s.
- narration language: match the brief (default English). Punchy, cinematic copy.
- visual_prompt: concrete cinematography description per scene (no real people/brands).
- Never invent provider names, prices, or claims about the product beyond the brief."""


async def plan_storyboard(
    brief: str, *, title: str, platform: str, style: str, duration_hint_s: float,
) -> tuple[Storyboard, str, list[dict[str, Any]]]:
    """Returns (storyboard, llm_provider, plan_steps). llm_provider='mock' = offline."""
    plan_steps: list[dict[str, Any]] = [
        {"step": "plan", "strategy": "llm-chain", "note": "try configured LLM chain, fall back offline"},
        {"step": "write_storyboard"},
        {"step": "generate_concept_frames"},
        {"step": "generate_narration"},
        {"step": "generate_music"},
        {"step": "build_remotion_project"},
        {"step": "render_slideshow", "mode": "job"},
    ]
    user = (f"Brief: {brief}\nTitle: {title}\nPlatform: {platform}\n"
            f"Style: {style}\nTarget duration: {duration_hint_s}s")
    try:
        res = await get_registry().call("llm", system=_SYSTEM_PROMPT, user=user, json_mode=True)
        data = extract_json(res.out["text"])
        sb = validate_storyboard(data)
        sb.title = sb.title or title
        plan_steps[0]["provider"] = res.provider
        return sb, res.provider, plan_steps
    except (ProviderError, ValueError) as exc:
        sb = build_offline_storyboard(
            brief, title=title, platform=platform, style=style, duration_hint_s=duration_hint_s
        )
        plan_steps[0] = {"step": "plan", "strategy": "deterministic-offline", "reason": str(exc)[:200]}
        return sb, "mock", plan_steps


def summarize_brief(brief: str) -> dict[str, Any]:
    """Offline brief parsing stats used by the deterministic planner (testable)."""
    m = re.search(r"(\d{1,3})\s*(?:s\b|sec|second|ثانیه)", brief, flags=re.I)
    duration = float(m.group(1)) if m else 30.0
    platform = "youtube" if re.search(r"youtube|یوتیوب", brief, re.I) else \
        "tiktok" if re.search(r"tiktok|تیک\s?تاک", brief, re.I) else "instagram"
    style = "clean-light" if re.search(r"light|روشن|minimal", brief, re.I) else \
        "bold-energy" if re.search(r"energ|انرژی|bold", brief, re.I) else "cinematic-dark"
    lang = "fa" if re.search(r"[\u0600-\u06FF]", brief) else "en"
    return {"duration": min(duration, 600.0), "platform": platform, "style": style,
            "narration_language": lang}
