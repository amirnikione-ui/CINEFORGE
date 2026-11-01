"""STT providers: OpenAI Whisper-compatible transcription + mock passthrough."""
from __future__ import annotations

from typing import Any

from backend.app import config

from .base import Provider, ProviderError


class STTOpenAI(Provider):
    name = "openai"
    capability = "stt"

    def available(self) -> bool:
        return bool(config.OPENAI_API_KEY)

    async def run(self, *, audio_bytes: bytes, filename: str = "audio.wav",
                  language: str | None = None, **_: Any) -> dict[str, Any]:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                files = {"file": (filename, audio_bytes, "application/octet-stream")}
                data = {"model": config.OPENAI_STT_MODEL}
                if language:
                    data["language"] = language
                resp = await client.post(
                    f"{config.OPENAI_BASE_URL.rstrip('/')}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
                    data=data, files=files,
                )
                resp.raise_for_status()
                return {"text": resp.json().get("text", "")}
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"openai stt: {exc}") from exc


class STTMock(Provider):
    name = "mock"
    capability = "stt"

    def available(self) -> bool:
        return True

    async def run(self, **_: Any) -> dict[str, Any]:
        raise ProviderError("mock stt: transcription unavailable offline (honest failure)")
