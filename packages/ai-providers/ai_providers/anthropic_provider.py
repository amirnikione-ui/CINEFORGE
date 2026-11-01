"""Anthropic provider — /v1/messages via httpx. ``complete()`` only in v0.1."""
from __future__ import annotations

import os

import httpx

from .base import LLMProvider, ProviderError

_TIMEOUT_S = 120.0
_URL = "https://api.anthropic.com/v1/messages"


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def available(self) -> bool:
        return bool(os.environ.get("ANTHROPIC_API_KEY"))

    def complete(self, system: str, messages: list[dict], json_mode: bool = False) -> str:
        self._require_available()
        convo = [
            m for m in (messages or []) if m.get("role") in ("user", "assistant") and m.get("content")
        ]
        if not convo:
            convo = [{"role": "user", "content": "Plan the film."}]
        sys_prompt = system
        if json_mode:
            sys_prompt += "\n\nRespond ONLY with a single JSON object. No prose, no code fences."
        payload = {
            "model": os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
            "max_tokens": int(os.environ.get("ANTHROPIC_MAX_TOKENS", "4096")),
            "system": sys_prompt,
            "messages": convo,
        }
        try:
            resp = httpx.post(
                _URL,
                headers={
                    "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=payload,
                timeout=_TIMEOUT_S,
            )
        except httpx.HTTPError as exc:
            raise ProviderError(f"anthropic request failed: {exc}") from exc
        if resp.status_code >= 300:
            raise ProviderError(f"anthropic -> HTTP {resp.status_code}: {resp.text[:400]}")
        data = resp.json()
        blocks = data.get("content") or []
        text = "".join(
            b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text"
        )
        return text

    def chat_with_tools(self, system, messages, tools_schema, max_steps: int = 8) -> dict:
        raise NotImplementedError("anthropic tool loop is not wired in v0.1 (complete() only)")
