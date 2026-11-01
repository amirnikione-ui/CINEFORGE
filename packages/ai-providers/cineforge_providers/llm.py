"""LLM providers: Z.ai GLM, any OpenAI-compatible endpoint, Anthropic, and mock.

All real calls use plain httpx against documented HTTP APIs; no vendor SDK needed.
"""
from __future__ import annotations

import json
from typing import Any

from backend.app import config

from .base import Provider, ProviderError, _post_json

_TIMEOUT = 120.0


class LLMZai(Provider):
    name = "zai"
    capability = "llm"

    def available(self) -> bool:
        return bool(config.ZAI_API_KEY)

    async def run(self, *, system: str, user: str, json_mode: bool = False, **_: Any) -> dict[str, str]:
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        body: dict[str, Any] = {"model": config.ZAI_MODEL, "messages": messages, "temperature": 0.7}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        try:
            data = await _post_json(
                f"{config.ZAI_BASE_URL.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {config.ZAI_API_KEY}"},
                json_body=body, timeout=_TIMEOUT,
            )
        except Exception as exc:  # noqa: BLE001 - converted to ProviderError for chain fallback
            raise ProviderError(f"zai: {exc}") from exc
        try:
            return {"text": data["choices"][0]["message"]["content"]}
        except (KeyError, IndexError) as exc:
            raise ProviderError(f"zai: unexpected response shape: {data}") from exc


class LLMOpenAICompatible(Provider):
    """Works for OpenAI and any compatible gateway via OPENAI_BASE_URL (vLLM, Ollama, …)."""

    name = "openai"
    capability = "llm"

    def available(self) -> bool:
        return bool(config.OPENAI_API_KEY)

    async def run(self, *, system: str, user: str, json_mode: bool = False, **_: Any) -> dict[str, str]:
        body: dict[str, Any] = {
            "model": config.OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.7,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        try:
            data = await _post_json(
                f"{config.OPENAI_BASE_URL.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
                json_body=body, timeout=_TIMEOUT,
            )
            return {"text": data["choices"][0]["message"]["content"]}
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"openai: {exc}") from exc


class LLMAnthropic(Provider):
    name = "anthropic"
    capability = "llm"

    def available(self) -> bool:
        return bool(config.ANTHROPIC_API_KEY)

    async def run(self, *, system: str, user: str, **_: Any) -> dict[str, str]:
        try:
            data = await _post_json(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": config.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                },
                json_body={
                    "model": config.ANTHROPIC_MODEL,
                    "max_tokens": 4096,
                    "system": system,
                    "messages": [{"role": "user", "content": user}],
                },
                timeout=_TIMEOUT,
            )
            blocks = data.get("content", [])
            text = "".join(b.get("text", "") for b in blocks if isinstance(b, dict))
            return {"text": text}
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"anthropic: {exc}") from exc


class LLMMock(Provider):
    """Deterministic offline director brain — signals the orchestrator to use the
    rule-based storyboard builder. Produces a real (if simple) plan summary."""

    name = "mock"
    capability = "llm"

    def available(self) -> bool:
        return True

    async def run(self, *, system: str, user: str, **_: Any) -> dict[str, str]:
        return {"text": json.dumps({"mock": True, "brief_digest": user[:400]}), "mock": "1"}


def extract_json(text: str) -> dict[str, Any]:
    """Best-effort JSON extraction from an LLM reply (handles ``` fences)."""
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.startswith("json"):
            t = t[4:]
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end == -1:
        raise ProviderError("llm: no JSON object found in reply")
    return json.loads(t[start : end + 1])
