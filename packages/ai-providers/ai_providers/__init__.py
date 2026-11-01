"""CINEFORGE ai-providers — vendor-agnostic provider abstraction (ADR-0004/0005).

Capabilities: llm, image, tts, stt, music, video.
Every capability resolves through a configurable fallback chain; the terminal
"mock" provider always produces real artifacts offline, clearly labeled.
"""

from .base import (
    Capability,
    MockProvider,
    Provider,
    ProviderError,
    ProviderUnavailable,
    call_with_fallback,
)
from .registry import Registry, build_default_registry

__all__ = [
    "Capability",
    "MockProvider",
    "Provider",
    "ProviderError",
    "ProviderUnavailable",
    "Registry",
    "build_default_registry",
    "call_with_fallback",
]
