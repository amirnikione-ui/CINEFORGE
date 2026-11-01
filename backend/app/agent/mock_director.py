"""Deterministic offline director: storyboard building, normalization and revisions.

Used when no non-mock LLM is available (ADR-0005): plans a real, contract-valid
storyboard from the brief; also repairs/normalizes LLM-produced storyboards and
applies keyword-driven revisions to existing ones.
"""
from __future__ import annotations

import copy
import re

PALETTES: dict[str, dict[str, str]] = {
    "cinematic-dark": {"bg": "#0a0a12", "primary": "#7c5cff", "accent": "#00e5ff", "text": "#f5f5ff"},
    "vibrant-neon": {"bg": "#12041f", "primary": "#ff2fb3", "accent": "#00ffd5", "text": "#fff6fd"},
    "corporate-clean": {"bg": "#f4f7fb", "primary": "#1d4ed8", "accent": "#0ea5e9", "text": "#0f172a"},
    "warm-documentary": {"bg": "#1a120b", "primary": "#e0a458", "accent": "#f4ead5", "text": "#fdf6ec"},
}

MOODS: dict[str, str] = {
    "cinematic-dark": "dark-cinematic",
    "vibrant-neon": "vibrant-neon",
    "corporate-clean": "corporate-clean",
    "warm-documentary": "warm-documentary",
}

STYLE_TITLES: dict[str, str] = {
    "cinematic-dark": "Cinematic Promo",
    "vibrant-neon": "Neon Promo",
    "corporate-clean": "Product Story",
    "warm-documentary": "Mini Documentary",
}

VISUAL_BASES: dict[str, str] = {
    "cinematic-dark": (
        "dark moody atmosphere, deep shadows, violet and cyan rim light, cinematic haze, "
        "shallow depth of field, anamorphic flare"
    ),
    "vibrant-neon": (
        "vivid magenta and cyan neon light trails, glossy reflective surfaces, high contrast, "
        "energetic night city energy"
    ),
    "corporate-clean": (
        "bright minimal studio, soft daylight, clean geometric shapes, airy white and blue tones, "
        "crisp product macro"
    ),
    "warm-documentary": (
        "warm golden hour light, textured natural materials, documentary realism, gentle film grain"
    ),
}

MOTION_CYCLE = ["ken-burns", "zoom", "slide", "reveal"]
TRANSITION_CYCLE = ["fade", "cut", "fade", "slide"]

STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "with", "this", "that", "of", "to", "in", "on", "at",
    "by", "is", "are", "was", "were", "be", "make", "made", "create", "promo", "video", "film",
    "clip", "second", "seconds", "please", "new", "it", "its", "our", "your", "their", "we",
    "you", "i", "my", "me", "us", "they", "from", "into", "about", "as", "so", "very", "really",
    "just", "some", "any", "more", "most", "want", "need", "like", "show", "tell", "using",
    "use", "style", "mood", "vibe", "cinematic", "dark", "bright", "warm", "cool", "launch",
    "teaser", "story", "short", "long", "look", "feel",
}

_NOT_PRODUCT_WORDS = {
    "The", "This", "That", "A", "An", "Make", "Create", "Build", "For", "Meet", "Introducing",
    "New", "Our", "Your", "It", "Its", "Film", "Video", "Promo", "Cinematic", "Storyboard",
}

ASPECTS: dict[str, str] = {
    "instagram": "9:16",
    "tiktok": "9:16",
    "youtube": "16:9",
    "web": "16:9",
}

PLATFORM_LABELS: dict[str, str] = {
    "instagram": "Instagram",
    "tiktok": "TikTok",
    "youtube": "YouTube",
    "web": "the web",
}


# --------------------------------------------------------------------------- helpers


def _keywords(brief: str, limit: int = 6) -> list[str]:
    """Ordered significant keywords from the brief (deduped, stopwords stripped)."""
    out: list[str] = []
    for word in re.findall(r"[A-Za-z][A-Za-z0-9'&-]*", (brief or "").lower()):
        cleaned = word.strip("'&-")
        if len(cleaned) < 3 or cleaned in STOPWORDS or cleaned in out:
            continue
        out.append(cleaned)
        if len(out) >= limit:
            break
    return out


def _product_name(brief: str) -> str:
    """First plausible brand/proper noun in the brief, else 'NOVA'."""
    for word in re.findall(r"\b[A-Z][a-zA-Z0-9]{2,}\b", brief or ""):
        if word not in _NOT_PRODUCT_WORDS and word.lower() not in STOPWORDS:
            return word
    return "NOVA"


def _scene_count(duration_hint_s: float) -> int:
    if duration_hint_s <= 12:
        return 4
    if duration_hint_s <= 25:
        return 5
    return 6


def _plan(kinds: list[str]) -> list[tuple[str, float]]:
    """Kind -> duration share plans per scene count (sums to 1.0)."""
    if len(kinds) == 4:
        return [("hook", 0.25), ("reveal", 0.30), ("typography", 0.20), ("outro", 0.25)]
    if len(kinds) == 5:
        return [("hook", 0.20), ("reveal", 0.25), ("typography", 0.20), ("feature", 0.15), ("outro", 0.20)]
    return [
        ("hook", 0.18),
        ("reveal", 0.22),
        ("typography", 0.16),
        ("feature", 0.14),
        ("feature", 0.12),
        ("outro", 0.18),
    ]


def _headline_for(kind: str, i: int, name: str, topic: str, platform: str) -> str:
    name_u, topic_u = name.upper(), (topic or name).upper()
    if kind == "hook":
        return name_u if len(name_u) <= 14 else f"MEET {name_u}"
    if kind == "reveal":
        return f"{topic_u} REDEFINED" if len(topic_u) <= 12 else "A NEW KIND OF FILM"
    if kind == "typography":
        return f"BUILT FOR {PLATFORM_LABELS.get(platform, platform).upper()}"
    if kind == "feature":
        return f"{topic_u}, PERFECTED" if len(topic_u) <= 10 else "MADE TO MOVE"
    return f"{name_u}. START TONIGHT."


def _narration_for(kind: str, i: int, name: str, topic: str, platform: str, budget: int) -> str:
    """Product-aware narration sized to the scene (mock TTS ≈ 0.42s per word)."""
    platform_label = PLATFORM_LABELS.get(platform, platform)
    short = {
        "hook": f"This is {name}. A bolder way to experience {topic}.",
        "reveal": "Every frame is crafted with cinematic light and deep color.",
        "typography": f"{name} keeps your whole story moving at full speed.",
        "feature": "Smart scenes and rich sound handle every last detail.",
        "outro": f"{name} is ready whenever you are. Start creating tonight.",
    }[kind]
    extended = {
        "hook": f"This is {name}. A bolder way to experience {topic}, built for creators who move fast.",
        "reveal": "Every frame is crafted with cinematic light, deep color and motion that feels alive.",
        "typography": f"{name} keeps your story moving at full speed, from first idea to final cut.",
        "feature": "Smart scenes, rich sound and instant previews handle every detail for you.",
        "outro": f"{name} is made for {platform_label} and ready whenever you are. Start creating tonight.",
    }[kind]
    text = extended if budget >= len(extended.split()) else short
    return text


def _visual_prompt(kind: str, style: str, topic: str, keywords: list[str], i: int) -> str:
    base = VISUAL_BASES.get(style, VISUAL_BASES["cinematic-dark"])
    subject = topic or "the hero subject"
    beat = {
        "hook": f"dramatic establishing shot of {subject}",
        "reveal": f"{subject} unveiled in a shaft of light",
        "typography": "bold typographic composition over the atmosphere",
        "feature": f"dynamic close-up detail of {subject} in motion",
        "outro": f"final hero wide shot of {subject} with logo space",
    }.get(kind, f"cinematic shot of {subject}")
    extras = ", ".join(keywords[:3])
    tail = f", featuring {extras}" if extras else ""
    return f"{beat}, {base}, vertical social composition{tail}"


# --------------------------------------------------------------------------- build


def build_storyboard(
    brief: str,
    style: str = "cinematic-dark",
    platform: str = "instagram",
    duration_hint_s: int = 30,
) -> dict:
    """Deterministic director: brief -> contract-valid storyboard (schema_version 1)."""
    style = style if style in PALETTES else "cinematic-dark"
    platform = platform if platform in ASPECTS else "instagram"
    target = float(max(4, min(600, int(duration_hint_s or 30))))
    name = _product_name(brief)
    keywords = _keywords(brief)
    topic = keywords[0] if keywords else name.lower()
    plan = _plan(["x"] * _scene_count(target))
    kinds = [k for k, _ in plan]
    shares = [s for _, s in plan]

    scenes: list[dict] = []
    for i, (kind, share) in enumerate(zip(kinds, shares)):
        dur = round(max(1.0, target * share), 2)
        budget = int(dur / 0.42)
        scenes.append(
            {
                "id": f"scene-{i + 1:02d}",
                "kind": kind,
                "duration_s": dur,
                "headline": _headline_for(kind, i, name, topic, platform),
                "body": "",
                "narration": _narration_for(kind, i, name, topic, platform, budget),
                "visual_prompt": _visual_prompt(kind, style, topic, keywords, i),
                "motion": {
                    "style": MOTION_CYCLE[i % len(MOTION_CYCLE)],
                    "intensity": round(0.55 + 0.10 * (i % 3), 2),
                },
                "transition_in": "fade" if i == 0 else TRANSITION_CYCLE[i % len(TRANSITION_CYCLE)],
            }
        )

    title_style = STYLE_TITLES.get(style, "Cinematic Promo")
    storyboard = {
        "schema_version": 1,
        "title": f"{name} — {title_style}",
        "platform": platform,
        "aspect": ASPECTS[platform],
        "fps": 30,
        "duration_target_s": target,
        "palette": dict(PALETTES[style]),
        "music_mood": MOODS[style],
        "scenes": scenes,
    }
    return normalize_storyboard(storyboard, style, platform, int(target))


# --------------------------------------------------------------------------- normalize


def normalize_storyboard(
    storyboard: dict,
    style: str = "cinematic-dark",
    platform: str | None = None,
    duration_hint_s: int | None = None,
) -> dict:
    """Validate/repair any storyboard-ish dict into schema v1 (durations rescaled to target)."""
    style = style if style in PALETTES else "cinematic-dark"
    sb = copy.deepcopy(storyboard) if isinstance(storyboard, dict) else {}
    platform = (platform or sb.get("platform") or "instagram").lower()
    if platform not in ASPECTS:
        platform = "instagram"
    target = float(sb.get("duration_target_s") or duration_hint_s or 30)
    target = max(4.0, min(600.0, target))

    palette = dict(PALETTES[style])
    provided = sb.get("palette")
    if isinstance(provided, dict):
        for key in palette:
            value = provided.get(key)
            if isinstance(value, str) and re.fullmatch(r"#?[0-9a-fA-F]{3}([0-9a-fA-F]{3})?", value or ""):
                palette[key] = value if value.startswith("#") else f"#{value}"

    fps = sb.get("fps")
    fps = int(fps) if isinstance(fps, (int, float)) and 12 <= fps <= 60 else 30

    raw_scenes = sb.get("scenes")
    if not isinstance(raw_scenes, list) or not raw_scenes:
        raw_scenes = [{}]
    valid_motions = set(MOTION_CYCLE)
    valid_transitions = {"fade", "cut", "slide"}
    valid_kinds = {"hook", "reveal", "typography", "feature", "outro"}

    scenes: list[dict] = []
    for i, raw in enumerate(raw_scenes):
        raw = raw if isinstance(raw, dict) else {}
        dur = raw.get("duration_s")
        try:
            dur = float(dur)
        except (TypeError, ValueError):
            dur = 0.0
        motion = raw.get("motion") if isinstance(raw.get("motion"), dict) else {}
        m_style = str(motion.get("style") or MOTION_CYCLE[i % len(MOTION_CYCLE)]).lower()
        if m_style not in valid_motions:
            m_style = "ken-burns"
        try:
            m_intensity = max(0.0, min(1.0, float(motion.get("intensity", 0.6))))
        except (TypeError, ValueError):
            m_intensity = 0.6
        transition = str(raw.get("transition_in") or "fade").lower()
        if transition not in valid_transitions:
            transition = "fade"
        kind = str(raw.get("kind") or valid_kinds_list()[i % 4]).lower()
        if kind not in valid_kinds:
            kind = "reveal"
        scenes.append(
            {
                "id": str(raw.get("id") or f"scene-{i + 1:02d}"),
                "kind": kind,
                "duration_s": max(0.8, dur),
                "headline": str(raw.get("headline") or "").strip(),
                "body": str(raw.get("body") or "").strip(),
                "narration": str(raw.get("narration") or "").strip(),
                "visual_prompt": str(raw.get("visual_prompt") or raw.get("visualPrompt") or "").strip(),
                "motion": {"style": m_style, "intensity": round(m_intensity, 2)},
                "transition_in": transition,
            }
        )

    total = sum(s["duration_s"] for s in scenes)
    if total <= 0:
        for s in scenes:
            s["duration_s"] = target / len(scenes)
    else:
        scale = target / total
        for s in scenes:
            s["duration_s"] = round(max(1.0, s["duration_s"] * scale), 2)
    # Absorb rounding drift into the longest scene so the sum tracks the target.
    drift = round(target - sum(s["duration_s"] for s in scenes), 2)
    if abs(drift) >= 0.01:
        longest = max(scenes, key=lambda s: s["duration_s"])
        longest["duration_s"] = round(max(1.0, longest["duration_s"] + drift), 2)

    if not scenes[0]["visual_prompt"]:
        scenes[0]["visual_prompt"] = VISUAL_BASES[style]

    sb_out = {
        "schema_version": 1,
        "title": str(sb.get("title") or "Untitled Cut").strip() or "Untitled Cut",
        "platform": platform,
        "aspect": ASPECTS[platform],
        "fps": fps,
        "duration_target_s": target,
        "palette": palette,
        "music_mood": str(sb.get("music_mood") or MOODS[style]),
        "scenes": scenes,
    }
    return sb_out


def valid_kinds_list() -> list[str]:
    return ["hook", "reveal", "typography", "outro"]


# --------------------------------------------------------------------------- revisions


def apply_revision(storyboard: dict, instruction: str) -> dict:
    """Keyword-driven revision of an existing storyboard (returns a new dict)."""
    sb = copy.deepcopy(storyboard)
    instr = (instruction or "").lower()

    factor = 1.0
    if "shorter" in instr or "tighter" in instr or "punchier" in instr:
        factor = 0.75
    elif "longer" in instr or "more time" in instr or "slower pacing" in instr:
        factor = 1.25
    if factor != 1.0:
        sb["duration_target_s"] = round(max(4.0, float(sb.get("duration_target_s") or 30) * factor), 2)
        for scene in sb.get("scenes", []):
            scene["duration_s"] = round(max(1.0, float(scene.get("duration_s") or 4) * factor), 2)
        total = sum(s["duration_s"] for s in sb.get("scenes", [])) or 1.0
        scale = float(sb["duration_target_s"]) / total
        for scene in sb["scenes"]:
            scene["duration_s"] = round(max(1.0, scene["duration_s"] * scale), 2)

    if "faster" in instr or "snappier" in instr:
        for scene in sb.get("scenes", []):
            motion = scene.setdefault("motion", {})
            motion["intensity"] = 0.9
            if motion.get("style") == "reveal":
                motion["style"] = "zoom"
    if "slower" in instr and "pacing" in instr or "calmer" in instr:
        for scene in sb.get("scenes", []):
            scene.setdefault("motion", {})["intensity"] = 0.35

    palette_swaps = [
        (("blue", "icy", "cool"), "corporate-clean"),
        (("green", "emerald"), "warm-documentary"),
        (("warm", "golden", "sunset"), "warm-documentary"),
        (("neon", "electric", "bright"), "vibrant-neon"),
        (("darker", "darker palette", "moody"), "cinematic-dark"),
    ]
    for words, style in palette_swaps:
        if any(w in instr for w in words):
            sb["palette"] = dict(PALETTES[style])
            sb["music_mood"] = MOODS[style]
            break
    if "dark" in instr and "palette" in instr:
        sb["palette"] = dict(PALETTES["cinematic-dark"])
        sb["music_mood"] = MOODS["cinematic-dark"]
    if "professional" in instr or "corporate" in instr or "serious" in instr:
        sb["palette"] = dict(PALETTES["corporate-clean"])
        sb["music_mood"] = MOODS["corporate-clean"]

    if not isinstance(sb.get("palette"), dict) or not sb["palette"]:
        sb["palette"] = dict(PALETTES["cinematic-dark"])
    return sb
