"""ai_agent — the director's tool contract (stable interface, see docs/API_CONTRACTS.md).

``TOOLS_JSON`` is the OpenAI-style tool schema list the LLM director uses in the
chat tool-loop. ``execute`` of each tool lives in ``backend/app/agent/tools.py``;
this package is the shared definition both sides import.

Helpers:
    tool_names() -> list[str]
    get_tool(name) -> dict | None
    contract_summary() -> str
"""
from __future__ import annotations

_TOOLS_JSON: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "write_storyboard",
            "description": (
                "Plan (or revise) the film: write storyboard JSON (schema_version 1) from a "
                "brief. Returns the storyboard asset and the normalized scene plan."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "brief": {
                        "type": "string",
                        "description": "Full creative brief: product, tone, audience, platform, target duration.",
                    },
                    "style": {
                        "type": "string",
                        "description": "Visual style preset: cinematic-dark | vibrant-neon | corporate-clean | warm-documentary.",
                    },
                    "platform": {
                        "type": "string",
                        "description": "Target platform: instagram | tiktok | youtube | web.",
                    },
                    "duration_hint_s": {"type": "integer", "description": "Target duration in seconds."},
                },
                "required": ["brief"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_concept_frames",
            "description": (
                "Generate one concept frame per storyboard scene (key art honoring the "
                "palette and headline). Uses the latest storyboard when omitted."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "storyboard": {
                        "type": "object",
                        "description": "Optional storyboard JSON (schema v1); defaults to the latest on disk.",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_narration",
            "description": "Synthesize narration audio per scene with narration text (TTS chain).",
            "parameters": {
                "type": "object",
                "properties": {
                    "storyboard": {
                        "type": "object",
                        "description": "Optional storyboard JSON (schema v1); defaults to the latest on disk.",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_music",
            "description": "Generate the background music bed for the storyboard's mood and duration.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mood": {
                        "type": "string",
                        "description": "Music mood, e.g. dark-cinematic | vibrant-neon | corporate-clean | warm-documentary.",
                    },
                    "duration_s": {"type": "number", "description": "Bed duration in seconds."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "render_slideshow",
            "description": (
                "Render the final mp4 from frames + narration + music (FFmpeg pipeline). "
                "Creates a Job row; returns the video asset (inline executor completes synchronously)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "storyboard": {
                        "type": "object",
                        "description": "Optional storyboard JSON (schema v1); defaults to the latest on disk.",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "build_remotion_project",
            "description": (
                "Scaffold an editable Remotion project (composition CinematicPromo) bound to "
                "the storyboard; registered as a directory asset."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "storyboard": {
                        "type": "object",
                        "description": "Optional storyboard JSON (schema v1); defaults to the latest on disk.",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "probe_media",
            "description": "Probe a media file (or asset id) and return duration/size/fps/audio metadata.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute path to the media file."},
                    "asset_id": {"type": "string", "description": "Alternatively, a project asset id."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_video",
            "description": (
                "M3 reverse-engineering entrypoint: probe summary + scene-detect cuts for a "
                "video (asset id or path)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute path to the video."},
                    "asset_id": {"type": "string", "description": "Alternatively, a project asset id."},
                },
                "required": [],
            },
        },
    },
]


def tool_names() -> list[str]:
    return [t["function"]["name"] for t in _TOOLS_JSON]


def get_tool(name: str) -> dict | None:
    for t in _TOOLS_JSON:
        if t["function"]["name"] == name:
            return t
    return None


def contract_summary() -> str:
    """Human-readable one-line-per-tool summary (used in prompts and docs)."""
    return "\n".join(
        f"- {t['function']['name']}: {t['function']['description'].split('. ')[0]}."
        for t in _TOOLS_JSON
    )


TOOLS_JSON = _TOOLS_JSON

__all__ = ["TOOLS_JSON", "tool_names", "get_tool", "contract_summary"]
