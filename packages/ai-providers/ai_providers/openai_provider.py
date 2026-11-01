"""OpenAI provider — pure httpx (no vendor SDK).

Capabilities: llm (chat + tool loop), image (gpt-image-1), tts (tts-1), stt (whisper-1).
All calls raise ``ProviderError`` on non-2xx responses; metadata always carries
``"provider": "openai"``.
"""
from __future__ import annotations

import base64
import json
import os
import wave
from pathlib import Path

import httpx

from .base import ImageProvider, LLMProvider, ProviderError, STTProvider, TTSProvider

_TIMEOUT_S = 120.0


class OpenAIProvider(LLMProvider, ImageProvider, TTSProvider, STTProvider):
    name = "openai"

    def __init__(self) -> None:
        self.base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self.image_model = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1")
        self.tts_model = os.environ.get("OPENAI_TTS_MODEL", "tts-1")
        self.tts_voice = os.environ.get("OPENAI_TTS_VOICE", "onyx")
        self.stt_model = os.environ.get("OPENAI_STT_MODEL", "whisper-1")

    # -- plumbing ----------------------------------------------------------

    def available(self) -> bool:
        return bool(os.environ.get("OPENAI_API_KEY"))

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "Content-Type": "application/json",
        }

    def _post_json(self, path: str, payload: dict, timeout: float = _TIMEOUT_S) -> dict:
        try:
            resp = httpx.post(
                f"{self.base_url}{path}", headers=self._headers(), json=payload, timeout=timeout
            )
        except httpx.HTTPError as exc:
            raise ProviderError(f"openai request failed: {exc}") from exc
        if resp.status_code >= 300:
            raise ProviderError(f"openai {path} -> HTTP {resp.status_code}: {resp.text[:400]}")
        try:
            return resp.json()
        except json.JSONDecodeError as exc:
            raise ProviderError(f"openai {path}: invalid JSON response") from exc

    # -- llm ---------------------------------------------------------------

    def complete(self, system: str, messages: list[dict], json_mode: bool = False) -> str:
        self._require_available()
        payload: dict = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, *messages],
            "temperature": 0.7,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        data = self._post_json("/chat/completions", payload)
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"openai chat: unexpected response shape: {str(data)[:300]}") from exc
        return content or ""

    def chat_with_tools(self, system, messages, tools_schema, max_steps: int = 8) -> dict:
        """ONE OpenAI tool-mode request; the orchestrator loops up to ``max_steps``."""
        self._require_available()
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, *messages],
            "tools": tools_schema,
            "tool_choice": "auto",
            "temperature": 0.4,
        }
        data = self._post_json("/chat/completions", payload)
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("openai tool chat: unexpected response shape") from exc
        tool_calls = []
        for tc in message.get("tool_calls") or []:
            fn = tc.get("function") or {}
            try:
                arguments = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                arguments = {}
            tool_calls.append({"id": tc.get("id"), "name": fn.get("name"), "arguments": arguments})
        return {"content": message.get("content"), "tool_calls": tool_calls}

    # -- image -------------------------------------------------------------

    def generate_image(self, prompt, out_path, width=1080, height=1920, **kwargs) -> dict:
        self._require_available()
        size = (
            "1024x1024"
            if int(width) == int(height)
            else ("1024x1536" if height > width else "1536x1024")
        )
        data = self._post_json(
            "/images/generations",
            {"model": self.image_model, "prompt": prompt, "size": size, "n": 1},
            timeout=180.0,
        )
        item = (data.get("data") or [{}])[0]
        payload: bytes | None = None
        if item.get("b64_json"):
            payload = base64.b64decode(item["b64_json"])
        elif item.get("url"):
            try:
                payload = httpx.get(item["url"], timeout=120.0).content
            except httpx.HTTPError as exc:
                raise ProviderError(f"openai image download failed: {exc}") from exc
        if not payload:
            raise ProviderError("openai image: response contained neither b64_json nor url")
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(payload)
        return {
            "provider": "openai",
            "path": str(out),
            "width": int(width),
            "height": int(height),
            "model": self.image_model,
            "size": size,
            "prompt": prompt,
        }

    # -- tts ---------------------------------------------------------------

    def synthesize(self, text, out_path_wav) -> dict:
        self._require_available()
        payload = {
            "model": self.tts_model,
            "voice": self.tts_voice,
            "input": text,
            "response_format": "wav",
        }
        try:
            resp = httpx.post(
                f"{self.base_url}/audio/speech",
                headers=self._headers(),
                json=payload,
                timeout=_TIMEOUT_S,
            )
        except httpx.HTTPError as exc:
            raise ProviderError(f"openai tts request failed: {exc}") from exc
        if resp.status_code >= 300:
            raise ProviderError(f"openai tts -> HTTP {resp.status_code}: {resp.text[:300]}")
        out = Path(out_path_wav)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(resp.content)
        duration_s = 0.0
        try:
            with wave.open(str(out), "rb") as wf:
                duration_s = wf.getnframes() / float(wf.getframerate() or 22050)
        except Exception:
            duration_s = 0.0
        return {
            "provider": "openai",
            "path": str(out),
            "duration_s": round(duration_s, 3),
            "model": self.tts_model,
            "voice": self.tts_voice,
        }

    # -- stt ---------------------------------------------------------------

    def transcribe(self, wav_path) -> str:
        self._require_available()
        path = Path(wav_path)
        try:
            with httpx.Client(timeout=_TIMEOUT_S) as client:
                resp = client.post(
                    f"{self.base_url}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                    files={"file": (path.name, path.read_bytes(), "audio/wav")},
                    data={"model": self.stt_model},
                )
        except httpx.HTTPError as exc:
            raise ProviderError(f"openai stt request failed: {exc}") from exc
        if resp.status_code >= 300:
            raise ProviderError(f"openai stt -> HTTP {resp.status_code}: {resp.text[:300]}")
        return str(resp.json().get("text", ""))
