"""Capability registry with env-configured fallback chains (ADR-0004).

Chain env vars (comma-separated, priority order):
  CINEFORGE_LLM_CHAIN=zai,openai,anthropic,mock
  CINEFORGE_IMAGE_CHAIN=openai,mock
  CINEFORGE_TTS_CHAIN=openai,elevenlabs,mock
  CINEFORGE_STT_CHAIN=openai,mock
  CINEFORGE_MUSIC_CHAIN=mock
  CINEFORGE_VIDEO_CHAIN=mock

The name "mock" always maps to the offline tier for that capability and is
always available, guaranteeing the pipeline completes with zero keys.
"""

from __future__ import annotations

import os
from typing import Any, Callable

from .base import CAPABILITY_ORDER, Attempt, Capability, FallbackResult, Provider, call_with_fallback
from .image import OpenAIImage, PillowArtImage
from .llm import AnthropicLLM, MockLLM, OpenAICompatLLM
from .music import ProceduralMusic
from .stt import MockSTT, OpenAISTT
from .tts import ElevenLabsTTS, OpenAITTS, SilentWavTTS
from .video import FFmpegSlideshowVideo

CHAIN_ENV = {
    Capability.LLM: "CINEFORGE_LLM_CHAIN",
    Capability.IMAGE: "CINEFORGE_IMAGE_CHAIN",
    Capability.TTS: "CINEFORGE_TTS_CHAIN",
    Capability.STT: "CINEFORGE_STT_CHAIN",
    Capability.MUSIC: "CINEFORGE_MUSIC_CHAIN",
    Capability.VIDEO: "CINEFORGE_VIDEO_CHAIN",
}

DEFAULT_CHAINS: dict[Capability, str] = {
    Capability.LLM: "zai,openai,anthropic,mock",
    Capability.IMAGE: "openai,mock",
    Capability.TTS: "openai,elevenlabs,mock",
    Capability.STT: "openai,mock",
    Capability.MUSIC: "mock",
    Capability.VIDEO: "mock",
}

_NAME_MAP = {
    "zai": lambda: OpenAICompatLLM(
        name="zai", api_key_env="ZAI_API_KEY", default_base_url="https://api.z.ai/api/paas/v4",
        default_model="glm-4.6", base_url_env="ZAI_BASE_URL", model_env="ZAI_MODEL",
    ),
    "openai": lambda: OpenAICompatLLM(
        name="openai", api_key_env="OPENAI_API_KEY", default_base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini", base_url_env="OPENAI_BASE_URL", model_env="OPENAI_MODEL",
    ),
    "anthropic": lambda: AnthropicLLM(),
    # capability-specific names (same "openai" name resolves per capability)
    "elevenlabs": lambda: ElevenLabsTTS(),
}


def _provider_for(capability: Capability, name: str) -> Provider | None:
    name = name.strip().lower()
    if name == "mock":
        return {
            Capability.LLM: MockLLM,
            Capability.IMAGE: PillowArtImage,
            Capability.TTS: SilentWavTTS,
            Capability.STT: MockSTT,
            Capability.MUSIC: ProceduralMusic,
            Capability.VIDEO: FFmpegSlideshowVideo,
        }[capability]()
    if capability == Capability.LLM and name in ("zai", "openai", "anthropic"):
        return _NAME_MAP[name]()
    if capability == Capability.IMAGE and name == "openai":
        return OpenAIImage()
    if capability == Capability.TTS and name == "openai":
        return OpenAITTS()
    if capability == Capability.TTS and name == "elevenlabs":
        return ElevenLabsTTS()
    if capability == Capability.STT and name == "openai":
        return OpenAISTT()
    if capability == Capability.MUSIC and name in ("openai", "elevenlabs", "zai"):
        return None  # music has no vendor impl yet (CF-033); skip unknown
    if capability == Capability.VIDEO and name in ("openai", "zai", "anthropic"):
        return None  # vendor video-gen lands in M2 (CF-034 chain slot)
    return None


class Registry:
    def __init__(self) -> None:
        self._chains: dict[Capability, list[Provider]] = {}
        self.build()

    def build(self) -> None:
        self._chains = {}
        for cap in Capability:
            raw = os.environ.get(CHAIN_ENV[cap]) or DEFAULT_CHAINS[cap]
            chain: list[Provider] = []
            for name in raw.split(","):
                provider = _provider_for(cap, name)
                if provider is not None and provider.name not in [p.name for p in chain]:
                    chain.append(provider)
            if not any(p.name == "mock" for p in chain):
                chain.append(_provider_for(cap, "mock"))
            self._chains[cap] = chain

    def chain(self, capability: Capability | str) -> list[Provider]:
        cap = Capability(capability)
        return list(self._chains[cap])

    def pick(self, capability: Capability | str) -> Provider:
        for provider in self.chain(capability):
            if provider.available():
                return provider
        raise RuntimeError(f"no available provider for {capability}")  # unreachable: mock always available

    def available_names(self, capability: Capability | str) -> list[str]:
        return [p.name for p in self.chain(capability) if p.available()]

    def call(
        self,
        capability: Capability | str,
        operation: str,
        invoke: Callable[[Provider], Any],
        *,
        require_non_mock: bool = False,
    ) -> FallbackResult:
        return call_with_fallback(self.chain(capability), operation, invoke, require_non_mock=require_non_mock)

    def describe(self) -> dict[str, list[str]]:
        """Contract shape for GET /health: available providers per capability, in order."""
        return {cap.value: self.available_names(cap) for cap in Capability}

    def detail(self) -> dict[str, list[dict[str, Any]]]:
        out: dict[str, list[dict[str, Any]]] = {}
        for cap in Capability:
            out[cap.value] = [
                {"name": p.name, "available": p.available(), **(p.describe() or {})}
                for p in self._chains[cap]
            ]
        return out


def build_default_registry() -> Registry:
    return Registry()
