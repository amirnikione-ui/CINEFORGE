"""STT providers: OpenAI Whisper + honest offline tier."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .base import Capability, MockProvider, ProviderError, ProviderUnavailable


@dataclass
class OpenAISTT:
    name: str = "openai"
    model_env: str = "OPENAI_STT_MODEL"
    default_model: str = "whisper-1"
    capability: Capability = Capability.STT

    def available(self) -> bool:
        return bool(os.environ.get("OPENAI_API_KEY", "").strip())

    def is_mock(self) -> bool:
        return False

    def describe(self) -> dict[str, Any]:
        return {"name": self.name, "kind": "openai-whisper"}

    def transcribe(self, audio_path: Path) -> dict[str, Any]:
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not key:
            raise ProviderUnavailable("openai stt: OPENAI_API_KEY not set")
        import httpx

        with open(audio_path, "rb") as fh:
            resp = httpx.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {key}"},
                data={"model": os.environ.get(self.model_env) or self.default_model},
                files={"file": (audio_path.name, fh, "audio/wav")},
                timeout=300.0,
            )
        if resp.status_code in (401, 403):
            raise ProviderUnavailable(f"openai stt auth rejected ({resp.status_code})")
        if resp.status_code >= 400:
            raise ProviderError(f"openai stt -> {resp.status_code}: {resp.text[:300]}")
        return {"provider": self.name, "text": resp.json().get("text", "")}


@dataclass
class MockSTT(MockProvider):
    name: str = "mock"
    capability: Capability = Capability.STT

    def available(self) -> bool:
        return True

    def describe(self) -> dict[str, Any]:
        return {"name": self.name, "kind": "unavailable-offline"}

    def transcribe(self, audio_path: Path) -> dict[str, Any]:
        raise ProviderError(
            "offline STT produces no transcript (audio kept for timing); "
            "configure OPENAI_API_KEY for transcription"
        )
