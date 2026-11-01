"""Capability registry: builds ordered provider lists from env chains (ADR-0004)."""
from __future__ import annotations

from typing import Any

from backend.app import config

from .base import CallResult, Provider, ProviderError, call_chain
from .image import ImageMock, ImageOpenAI
from .llm import LLMMock, LLMOpenAICompatible, LLMAnthropic, LLMZai
from .music import MusicMock
from .stt import STTMock, STTOpenAI
from .tts import TTSElevenLabs, TTSMock, TTSOpenAI
from .video import VideoMock

_LLMS: dict[str, type[Provider]] = {
    "zai": LLMZai, "openai": LLMOpenAICompatible, "anthropic": LLMAnthropic, "mock": LLMMock,
}
_IMAGES: dict[str, type[Provider]] = {"openai": ImageOpenAI, "mock": ImageMock}
_TTS: dict[str, type[Provider]] = {"openai": TTSOpenAI, "elevenlabs": TTSElevenLabs, "mock": TTSMock}
_STT: dict[str, type[Provider]] = {"openai": STTOpenAI, "mock": STTMock}
_MUSIC: dict[str, type[Provider]] = {"mock": MusicMock}
_VIDEO: dict[str, type[Provider]] = {"mock": VideoMock}

_CATALOG = {"llm": _LLMS, "image": _IMAGES, "tts": _TTS, "stt": _STT, "music": _MUSIC, "video": _VIDEO}


class Registry:
    def __init__(self) -> None:
        self._chains: dict[str, list[Provider]] = {}
        chains_env = {
            "llm": config.LLM_CHAIN, "image": config.IMAGE_CHAIN, "tts": config.TTS_CHAIN,
            "stt": config.STT_CHAIN, "music": config.MUSIC_CHAIN, "video": config.VIDEO_CHAIN,
        }
        for cap, chain in chains_env.items():
            instances: list[Provider] = []
            for name in chain:
                cls = _CATALOG[cap].get(name)
                if cls is None:
                    continue  # unknown provider name in env — skipped, logged by callers
                instances.append(cls())
            self._chains[cap] = instances

    def providers(self, capability: str) -> list[Provider]:
        return list(self._chains.get(capability, []))

    def status(self) -> dict[str, list[str]]:
        return {cap: [p.name for p in plist] for cap, plist in self._chains.items()}

    async def call(self, capability: str, **kwargs: Any) -> CallResult:
        return await call_chain(capability, self._chains.get(capability, []), kwargs)


_registry: Registry | None = None


def get_registry() -> Registry:
    global _registry
    if _registry is None:
        _registry = Registry()
    return _registry
