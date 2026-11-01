"""TTS providers: OpenAI speech, ElevenLabs, offline silent-WAV tier."""

from __future__ import annotations

import os
import struct
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .base import Capability, MockProvider, ProviderError, ProviderUnavailable


@dataclass
class OpenAITTS:
    name: str = "openai"
    model_env: str = "OPENAI_TTS_MODEL"
    default_model: str = "tts-1"
    voice_env: str = "OPENAI_TTS_VOICE"
    default_voice: str = "alloy"
    capability: Capability = Capability.TTS

    def available(self) -> bool:
        return bool(os.environ.get("OPENAI_API_KEY", "").strip())

    def is_mock(self) -> bool:
        return False

    def describe(self) -> dict[str, Any]:
        return {"name": self.name, "kind": "openai-speech", "model": os.environ.get(self.model_env) or self.default_model}

    def synthesize(self, text: str, *, out_path: Path) -> dict[str, Any]:
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not key:
            raise ProviderUnavailable("openai tts: OPENAI_API_KEY not set")
        import httpx

        resp = httpx.post(
            "https://api.openai.com/v1/audio/speech",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": os.environ.get(self.model_env) or self.default_model,
                "voice": os.environ.get(self.voice_env) or self.default_voice,
                "input": text[:4096],
                "response_format": "mp3",
            },
            timeout=180.0,
        )
        if resp.status_code in (401, 403):
            raise ProviderUnavailable(f"openai tts auth rejected ({resp.status_code})")
        if resp.status_code >= 400:
            raise ProviderError(f"openai tts -> {resp.status_code}: {resp.text[:300]}")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(resp.content)
        return {"provider": self.name, "path": str(out_path)}


@dataclass
class ElevenLabsTTS:
    name: str = "elevenlabs"
    voice_env: str = "ELEVENLABS_VOICE_ID"
    default_voice: str = "21m00Tcm4TlvDq8ikWAM"
    model_env: str = "ELEVENLABS_MODEL"
    default_model: str = "eleven_multilingual_v2"
    base_url_env: str = "ELEVENLABS_BASE_URL"
    default_base_url: str = "https://api.elevenlabs.io/v1"
    capability: Capability = Capability.TTS

    def available(self) -> bool:
        return bool(os.environ.get("ELEVENLABS_API_KEY", "").strip())

    def is_mock(self) -> bool:
        return False

    def describe(self) -> dict[str, Any]:
        return {"name": self.name, "kind": "elevenlabs-tts"}

    def synthesize(self, text: str, *, out_path: Path) -> dict[str, Any]:
        key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
        if not key:
            raise ProviderUnavailable("elevenlabs: ELEVENLABS_API_KEY not set")
        import httpx

        base = (os.environ.get(self.base_url_env) or self.default_base_url).rstrip("/")
        voice = os.environ.get(self.voice_env) or self.default_voice
        resp = httpx.post(
            f"{base}/text-to-speech/{voice}",
            headers={"xi-api-key": key, "accept": "audio/mpeg"},
            json={
                "text": text[:5000],
                "model_id": os.environ.get(self.model_env) or self.default_model,
            },
            timeout=180.0,
        )
        if resp.status_code in (401, 403):
            raise ProviderUnavailable(f"elevenlabs auth rejected ({resp.status_code})")
        if resp.status_code == 429:
            raise ProviderError("elevenlabs rate limited (429)")
        if resp.status_code >= 400:
            raise ProviderError(f"elevenlabs -> {resp.status_code}: {resp.text[:300]}")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(resp.content)
        return {"provider": self.name, "path": str(out_path)}


@dataclass
class SilentWavTTS(MockProvider):
    """Offline tier: a correctly-timed silent WAV (real file, honest label).

    The slideshow engine uses it for audio timing and burns the narration text
    as subtitles/typography so the offline video still 'speaks' visually.
    """

    name: str = "mock"
    words_per_second: float = 2.6
    capability: Capability = Capability.TTS

    def available(self) -> bool:
        return True

    def describe(self) -> dict[str, Any]:
        return {"name": self.name, "kind": "silent-wav-timing"}

    def synthesize(self, text: str, *, out_path: Path, target_duration_s: float | None = None) -> dict[str, Any]:
        words = max(1, len(text.split()))
        duration = target_duration_s or min(30.0, words / self.words_per_second + 0.6)
        rate = 22050
        frames = int(rate * duration)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(out_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(rate)
            wf.writeframes(b"\x00\x00" * frames)
        return {"provider": self.name, "path": str(out_path), "duration_s": round(duration, 2), "silent": True}
