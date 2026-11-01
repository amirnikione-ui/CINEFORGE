"""LLM providers: OpenAI-compatible (covers OpenAI + Z.ai GLM), Anthropic, mock."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

import httpx

from .base import Capability, MockProvider, ProviderError, ProviderUnavailable


@dataclass
class ChatMessage:
    role: str  # system | user | assistant
    content: str


def _post_json(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float = 90.0) -> dict[str, Any]:
    try:
        resp = httpx.post(url, headers=headers, json=payload, timeout=timeout)
    except httpx.HTTPError as exc:
        raise ProviderError(f"http error calling {url}: {exc}") from exc
    if resp.status_code == 401 or resp.status_code == 403:
        raise ProviderUnavailable(f"auth rejected by {url} ({resp.status_code})")
    if resp.status_code >= 400:
        raise ProviderError(f"{url} -> {resp.status_code}: {resp.text[:300]}")
    try:
        return resp.json()
    except ValueError as exc:
        raise ProviderError(f"non-JSON response from {url}") from exc


@dataclass
class OpenAICompatLLM:
    """OpenAI Chat Completions wire format; reused for OpenAI and Z.ai GLM."""

    name: str
    api_key_env: str
    default_base_url: str
    default_model: str
    base_url_env: str = ""
    model_env: str = ""
    capability: Capability = Capability.LLM

    def _base_url(self) -> str:
        base = os.environ.get(self.base_url_env) if self.base_url_env else None
        return (base or self.default_base_url).rstrip("/")

    def _model(self) -> str:
        return os.environ.get(self.model_env) if self.model_env else None or self.default_model

    def _key(self) -> str:
        return os.environ.get(self.api_key_env, "").strip()

    def available(self) -> bool:
        return bool(self._key())

    def is_mock(self) -> bool:
        return False

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": "openai-compatible",
            "model": self._model() if self.available() else None,
            "base_url": self._base_url(),
        }

    def chat(self, messages: list[ChatMessage], *, temperature: float = 0.7, json_mode: bool = False) -> str:
        key = self._key()
        if not key:
            raise ProviderUnavailable(f"{self.name}: {self.api_key_env} not set")
        payload: dict[str, Any] = {
            "model": self._model(),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        data = _post_json(
            f"{self._base_url()}/chat/completions",
            {"Authorization": f"Bearer {key}"},
            payload,
        )
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"{self.name}: unexpected response shape") from exc

    def chat_json(self, messages: list[ChatMessage], *, temperature: float = 0.4) -> dict[str, Any]:
        raw = self.chat(messages, temperature=temperature, json_mode=True)
        return extract_json_object(raw)


@dataclass
class AnthropicLLM:
    name: str = "anthropic"
    api_key_env: str = "ANTHROPIC_API_KEY"
    default_model: str = "claude-3-5-sonnet-latest"
    model_env: str = "ANTHROPIC_MODEL"
    base_url: str = "https://api.anthropic.com/v1"
    capability: Capability = Capability.LLM

    def _key(self) -> str:
        return os.environ.get(self.api_key_env, "").strip()

    def _model(self) -> str:
        return os.environ.get(self.model_env) or self.default_model

    def available(self) -> bool:
        return bool(self._key())

    def is_mock(self) -> bool:
        return False

    def describe(self) -> dict[str, Any]:
        return {"name": self.name, "kind": "anthropic", "model": self._model() if self.available() else None}

    def chat(self, messages: list[ChatMessage], *, temperature: float = 0.7, json_mode: bool = False) -> str:
        key = self._key()
        if not key:
            raise ProviderUnavailable(f"{self.name}: {self.api_key_env} not set")
        system = "\n\n".join(m.content for m in messages if m.role == "system")
        convo = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        payload: dict[str, Any] = {
            "model": self._model(),
            "max_tokens": 2048,
            "temperature": temperature,
            "messages": convo,
        }
        if system:
            payload["system"] = system
        data = _post_json(
            f"{self.base_url}/messages",
            {"x-api-key": key, "anthropic-version": "2023-06-01"},
            payload,
        )
        try:
            return "".join(block.get("text", "") for block in data["content"])
        except (KeyError, TypeError) as exc:
            raise ProviderError(f"{self.name}: unexpected response shape") from exc

    def chat_json(self, messages: list[ChatMessage], *, temperature: float = 0.4) -> dict[str, Any]:
        return extract_json_object(self.chat(messages, temperature=temperature))


@dataclass
class MockLLM(MockProvider):
    """Offline tier: deterministic, honest. Produces no network calls.

    The director uses the rule-based planner instead of this class for story
    generation; MockLLM exists so chains and health checks always resolve.
    """

    name: str = "mock"
    capability: Capability = Capability.LLM

    def available(self) -> bool:
        return True

    def describe(self) -> dict[str, Any]:
        return {"name": self.name, "kind": "offline-deterministic"}

    def chat(self, messages: list[ChatMessage], **_: Any) -> str:
        return json.dumps({"ok": True, "tier": "mock", "echo": messages[-1].content[:120]})

    def chat_json(self, messages: list[ChatMessage], **_: Any) -> dict[str, Any]:
        return {"ok": True, "tier": "mock"}


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_json_object(raw: str) -> dict[str, Any]:
    """Best-effort extraction of a JSON object from an LLM response."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except ValueError:
        pass
    match = _JSON_RE.search(text)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, dict):
                return parsed
        except ValueError:
            pass
    raise ProviderError("LLM returned a non-JSON payload")
