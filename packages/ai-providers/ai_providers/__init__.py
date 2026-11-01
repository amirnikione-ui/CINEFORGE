"""ai_providers — CINEFORGE capability interfaces, vendor providers, fallback chains.

Quick start:
    from ai_providers import get_registry

    registry = get_registry()
    result, provider_name = registry.run_with_fallback(
        "tts", lambda p: p.synthesize("Hello world", "/tmp/hello.wav")
    )
"""
from __future__ import annotations

from .base import (
    BaseProvider,
    ImageProvider,
    LLMProvider,
    MusicProvider,
    ProviderError,
    STTProvider,
    TTSProvider,
    VideoProvider,
)
from .config import DEFAULT_CHAINS, get_chains
from .registry import ProviderRegistry

_registry: ProviderRegistry | None = None


def get_registry() -> ProviderRegistry:
    """Process-wide cached registry (built from env chains on first use)."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry


__all__ = [
    "BaseProvider",
    "ImageProvider",
    "LLMProvider",
    "MusicProvider",
    "ProviderError",
    "ProviderRegistry",
    "STTProvider",
    "TTSProvider",
    "VideoProvider",
    "DEFAULT_CHAINS",
    "get_chains",
    "get_registry",
]
