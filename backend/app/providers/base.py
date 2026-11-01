"""Provider abstraction with fallback chains (ADR-0004, offline mock tier ADR-0005).

Capability tiers reported by /health must match what is actually configured here.
AGENT-05 v0.1: LLM tier (zai/openai via openai-compatible endpoint) + full mock tier.
Real image/TTS/music keys land with CF-030..033 (adapter seams below).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from dataclasses import dataclass
from typing import Any, Callable

import httpx

from video_engine import ffmpeg as vff

from ..core.config import get_settings

logger = logging.getLogger("cineforge.providers")


class ProviderError(RuntimeError):
    pass


@dataclass
class GenResult:
    provider: str
    text: str | None = None
    data: Any = None
    file_path: str | None = None
    meta: dict[str, Any] | None = None


# ------------------------------------------------------------------ LLM tier


class OpenAICompatLLM:
    """One adapter serves Z.ai GLM / OpenAI / any openai-compatible endpoint."""

    def __init__(self, name: str) -> None:
        s = get_settings()
        self.name = name
        self.base_url, self.api_key, self.model = s.llm_base_url, s.llm_api_key, s.llm_model

    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def complete(self, system: str, user: str, *, json_mode: bool = False) -> GenResult:
        if not self.is_configured():
            raise ProviderError(f"{self.name} not configured")
        try:
            resp = httpx.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                    "temperature": 0.4,
                },
                timeout=60,
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"{self.name} failed: {exc}") from exc
        data = None
        if json_mode:
            try:
                data = json.loads(text[text.find("{"): text.rfind("}") + 1])
            except (ValueError, AttributeError):
                data = None
        return GenResult(provider=self.name, text=text, data=data)


def llm_chain() -> list[OpenAICompatLLM]:
    """Priority chain for the llm capability, honoring LLM_PROVIDER ordering."""
    s = get_settings()
    chain: list[OpenAICompatLLM] = []
    preferred = s.llm_provider if s.llm_provider in ("zai", "openai") else None
    if preferred:
        chain.append(OpenAICompatLLM(preferred))
    for other in ("zai", "openai"):
        if other != preferred:
            chain.append(OpenAICompatLLM(other))
    return chain


# ------------------------------------------------------------- mock tier


def _seed_color(text: str) -> str:
    return "0x" + hashlib.md5(text.encode()).hexdigest()[:6]


def mock_llm_storyboard(brief: str, style: str, platform: str, duration_hint_s: float) -> dict[str, Any]:
    """Deterministic storyboard-v1 producer (the offline director's pen)."""
    from ..director.storyboard_gen import build_storyboard

    return build_storyboard(brief, style, platform, duration_hint_s)


def mock_image(prompt: str, out_path: str, width: int = 1080, height: int = 1920) -> str:
    """Real deterministic PNG (two-tone cinematic gradient seeded by the prompt)."""
    vff.run([
        "-f", "lavfi", "-i", f"color=c=0x0B0E14:s={width}x{height}:d=1",
        "-f", "lavfi", "-i", f"color=c={_seed_color(prompt)}:s={width}x{height}:d=1",
        "-filter_complex",
        "[1][0]scale2ref[ov][base];[ov]geq=r='r(X,Y)*0.22':g='g(X,Y)*0.20':b='b(X,Y)*0.32'[ovd];"
        "[base][ovd]blend=all_mode=screen:all_opacity=0.30",
        "-frames:v", "1", out_path,
    ], timeout=60)
    return out_path


def mock_narration(duration_s: float, out_path: str) -> str:
    """Silence bed with the right timing — placeholder narration track."""
    vff.run([
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-t", f"{duration_s:.2f}", "-c:a", "pcm_s16le", out_path,
    ], timeout=60)
    return out_path


def mock_music(mood: str, duration_s: float, out_path: str) -> str:
    base = 110.0 if "dark" in (mood or "").lower() else 146.83
    vff.run([
        "-f", "lavfi", "-i", f"sine=frequency={base}:duration={duration_s:.2f}",
        "-f", "lavfi", "-i", f"sine=frequency={base * 1.5:.2f}:duration={duration_s:.2f}",
        "-filter_complex",
        "[0][1]amix=inputs=2,volume=0.32,afade=t=in:d=1,afade=t=out:st=%.2f:d=1.5" % max(duration_s - 1.5, 0),
        "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", out_path,
    ], timeout=90)
    return out_path


def capability_map() -> dict[str, list[str]]:
    """Capability → providers ordered by availability (feeds GET /health)."""
    s = get_settings()
    llm: list[str] = []
    if s.llm_configured:
        llm.append(s.llm_provider if s.llm_provider in ("zai", "openai") else "openai")
    llm.append("mock")
    media_real = bool(s.llm_api_key) and s.llm_provider != "mock"  # honest: media keys not wired yet
    image = (["zai"] if media_real and s.llm_provider == "zai" else []) + ["mock"]
    return {
        "llm": llm,
        "image": image,
        "tts": ["mock"],
        "stt": ["mock"],
        "music": ["mock"],
        "video": ["mock"],
    }
