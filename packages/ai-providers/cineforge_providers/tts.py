"""TTS providers: OpenAI, ElevenLabs (real) + silent WAV placeholder (mock tier).

The mock tier produces a real, duration-accurate WAV so the audio pipeline
(mixing, ducking, subtitle timing) is exercised end-to-end without keys.
"""
from __future__ import annotations

import io
import math
import struct
import wave
from typing import Any

from backend.app import config

from .base import Provider, ProviderError, _post_binary


def estimate_speech_seconds(text: str, wpm: float = 150.0) -> float:
    words = max(1, len(text.split()))
    return max(1.0, words / (wpm / 60.0))


class TTSOpenAI(Provider):
    name = "openai"
    capability = "tts"

    def available(self) -> bool:
        return bool(config.OPENAI_API_KEY)

    async def run(self, *, text: str, voice: str | None = None, **_: Any) -> dict[str, Any]:
        try:
            audio = await _post_binary(
                f"{config.OPENAI_BASE_URL.rstrip('/')}/audio/speech",
                headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
                json_body={"model": config.OPENAI_TTS_MODEL,
                           "voice": voice or config.OPENAI_TTS_VOICE, "input": text},
                timeout=180.0,
            )
            return {"audio_bytes": audio, "ext": "mp3", "voice": voice or config.OPENAI_TTS_VOICE}
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"openai tts: {exc}") from exc


class TTSElevenLabs(Provider):
    name = "elevenlabs"
    capability = "tts"

    def available(self) -> bool:
        return bool(config.ELEVENLABS_API_KEY)

    async def run(self, *, text: str, voice_id: str | None = None, **_: Any) -> dict[str, Any]:
        vid = voice_id or config.ELEVENLABS_VOICE_ID
        try:
            audio = await _post_binary(
                f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
                headers={"xi-api-key": config.ELEVENLABS_API_KEY,
                         "accept": "audio/mpeg"},
                json_body={"text": text, "model_id": "eleven_multilingual_v2"},
                timeout=180.0,
            )
            return {"audio_bytes": audio, "ext": "mp3", "voice": vid}
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"elevenlabs: {exc}") from exc


class TTSMock(Provider):
    """Duration-accurate silent narration WAV (placeholder voice track)."""

    name = "mock"
    capability = "tts"

    def available(self) -> bool:
        return True

    async def run(self, *, text: str, **_: Any) -> dict[str, Any]:
        try:
            seconds = estimate_speech_seconds(text)
            rate = 22050
            n = int(seconds * rate)
            # near-silence with a faint 120Hz room tone so players show a real track
            frames = bytearray()
            for i in range(n):
                v = int(120 * math.sin(2 * math.pi * 120 * i / rate) * 0.05)
                frames += struct.pack("<h", v)
            buf = io.BytesIO()
            with wave.open(buf, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(rate)
                w.writeframes(bytes(frames))
            return {"audio_bytes": buf.getvalue(), "ext": "wav", "duration_s": seconds,
                    "placeholder": True}
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"tts mock: {exc}") from exc
