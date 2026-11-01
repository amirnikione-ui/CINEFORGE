"""Capability base classes and shared errors for CINEFORGE providers (ADR-0004)."""
from __future__ import annotations

from typing import Any, Callable


class ProviderError(Exception):
    """Raised by any provider when a call fails; the registry falls back to the next."""


class BaseProvider:
    """Common provider surface: identity + availability probe."""

    name: str = "base"

    def available(self) -> bool:
        """True when this provider can serve calls in the current environment."""
        return True

    def _require_available(self) -> None:
        if not self.available():
            raise ProviderError(f"{self.name} provider unavailable (missing credentials?)")


class LLMProvider(BaseProvider):
    """Text generation. ``complete`` for one-shot; ``chat_with_tools`` for the agent loop."""

    def complete(self, system: str, messages: list[dict], json_mode: bool = False) -> str:
        """Return the assistant text for ``messages`` given a ``system`` prompt.

        ``json_mode`` asks the provider to constrain output to a single JSON object.
        """
        raise NotImplementedError

    def chat_with_tools(
        self, system: str, messages: list[dict], tools_schema: list[dict], max_steps: int = 8
    ) -> dict:
        """Perform ONE model request in tool mode (the orchestrator drives the loop).

        Returns ``{"content": str | None, "tool_calls": [{"id", "name", "arguments": dict}]}``.
        Providers without tool support raise ``NotImplementedError`` — the registry
        then treats them as unavailable for the tool loop and the orchestrator
        falls back to the deterministic mock director.
        """
        raise NotImplementedError


class ImageProvider(BaseProvider):
    """Frame/concept-art generation."""

    def generate_image(
        self,
        prompt: str,
        out_path: str,
        width: int = 1080,
        height: int = 1920,
        **kwargs: Any,
    ) -> dict:
        """Write an image file to ``out_path`` and return metadata (must include ``provider``).

        Extra keyword args (``palette``, ``headline``, ``scene_index``, ``scene_count``)
        are honored by the offline mock tier and ignored by real vendors.
        """
        raise NotImplementedError


class TTSProvider(BaseProvider):
    """Narration synthesis."""

    def synthesize(self, text: str, out_path_wav: str) -> dict:
        """Write a WAV file and return metadata incl. real ``duration_s``."""
        raise NotImplementedError


class MusicProvider(BaseProvider):
    """Background music generation."""

    def generate_music(self, mood: str, duration_s: float, out_path_wav: str) -> dict:
        """Write a WAV bed of ~``duration_s`` seconds; metadata incl. ``duration_s``."""
        raise NotImplementedError


class STTProvider(BaseProvider):
    """Speech-to-text (minimal in v0.1)."""

    def transcribe(self, wav_path: str) -> str:
        raise NotImplementedError


class VideoProvider(BaseProvider):
    """Direct text-to-video APIs (Runway/Pika-class; M2+). The mock tier renders
    through the local FFmpeg/Remotion pipeline instead."""

    def generate_video(self, prompt: str, out_path: str, **kwargs: Any) -> dict:
        raise NotImplementedError


def call_first_available(
    providers: list, fn: Callable[[Any], Any]
) -> tuple[Any, str]:
    """Tiny helper used outside the registry: try fn(p) over providers in order."""
    errors: list[str] = []
    for provider in providers:
        try:
            if not provider.available():
                errors.append(f"{provider.name}: unavailable")
                continue
            return fn(provider), provider.name
        except Exception as exc:  # noqa: BLE001 - fallback is the point
            errors.append(f"{provider.name}: {exc}")
    raise ProviderError("all providers failed: " + "; ".join(errors))
