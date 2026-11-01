"""Provider registry: resolves capability chains, walks them with fallback (ADR-0004)."""
from __future__ import annotations

import logging
from typing import Any, Callable

from .base import ProviderError
from .config import get_chains

log = logging.getLogger("cineforge.providers")


class ProviderRegistry:
    """Capability -> ordered provider instances built from env chains.

    ``run_with_fallback`` iterates available providers and calls ``fn(provider)``;
    on any exception it logs, moves to the next provider, and raises the last
    error only when every provider failed. The terminal ``mock`` tier keeps the
    pipeline runnable with zero credentials.
    """

    def __init__(self, chains: dict[str, list[str]] | None = None) -> None:
        self._chains: dict[str, list[str]] = chains if chains is not None else get_chains()
        self._factories: dict[str, dict[str, Callable[[], Any]]] = {}
        self._instances: dict[str, list[Any]] = {}
        for capability, names in self._chains.items():
            for name in names:
                factory = self._builtin_factory(name, capability)
                if factory is None:
                    log.warning(
                        "unknown provider '%s' for capability '%s' — skipping", name, capability
                    )
                    continue
                self._factories.setdefault(capability, {})[name] = factory
            self._rebuild(capability)

    # -- construction ------------------------------------------------------

    @staticmethod
    def _builtin_factory(name: str, capability: str) -> Callable[[], Any] | None:
        if name == "mock":
            from . import mock as mock_module

            mapping = {
                "llm": mock_module.MockLLM,
                "image": mock_module.MockImage,
                "tts": mock_module.MockTTS,
                "music": mock_module.MockMusic,
                "stt": mock_module.MockSTT,
                "video": mock_module.MockVideo,
            }
            return mapping.get(capability)
        if name == "openai":
            from .openai_provider import OpenAIProvider

            return OpenAIProvider if capability in {"llm", "image", "tts", "stt"} else None
        if name == "anthropic":
            from .anthropic_provider import AnthropicProvider

            return AnthropicProvider if capability == "llm" else None
        if name == "zai":
            from .zai_provider import ZAIProvider

            return ZAIProvider if capability == "llm" else None
        return None

    def register_provider(
        self, name: str, capability: str, factory: Callable[[], Any], prepend: bool = True
    ) -> None:
        """Register (or override) a provider factory at runtime; prepends to the chain."""
        self._factories.setdefault(capability, {})[name] = factory
        chain = self._chains.setdefault(capability, [])
        if name not in chain:
            chain.insert(0 if prepend else len(chain), name)
        self._rebuild(capability)

    def _rebuild(self, capability: str) -> None:
        ordered: list[Any] = []
        for name in self._chains.get(capability, []):
            factory = self._factories.get(capability, {}).get(name)
            if factory is None:
                continue
            ordered.append(factory())
        self._instances[capability] = ordered

    # -- resolution --------------------------------------------------------

    def resolve(self, capability: str) -> list[Any]:
        """Ordered provider instances for a capability (may be empty)."""
        return list(self._instances.get(capability, []))

    def first_available(self, capability: str) -> Any | None:
        """First provider whose ``available()`` is True, else None."""
        for provider in self.resolve(capability):
            try:
                if provider.available():
                    return provider
            except Exception:  # noqa: BLE001
                continue
        return None

    def run_with_fallback(self, capability: str, fn: Callable[[Any], Any]) -> tuple[Any, str]:
        """Call fn(provider) walking the chain; returns (result, provider_name).

        Raises ProviderError summarizing every failure when all providers fail.
        """
        errors: list[str] = []
        for provider in self.resolve(capability):
            try:
                if not provider.available():
                    errors.append(f"{provider.name}: unavailable")
                    continue
                result = fn(provider)
                return result, provider.name
            except Exception as exc:  # noqa: BLE001 - fallback is the entire point
                log.warning("provider %s failed for %s: %s", provider.name, capability, exc)
                errors.append(f"{provider.name}: {exc}")
        raise ProviderError(
            f"all providers failed for capability '{capability}': " + "; ".join(errors)
        )

    # -- health ------------------------------------------------------------

    def status(self) -> dict[str, list[str]]:
        """Capability -> provider names, available ones first; unavailable suffixed with '*'.

        Matches the /health contract, e.g. {"llm": ["mock"], "image": ["mock"]} or
        {"llm": ["zai", "openai*", "mock"]} when a key is missing.
        """
        out: dict[str, list[str]] = {}
        for capability in self._instances:
            available_names: list[str] = []
            unavailable_names: list[str] = []
            for provider in self._instances[capability]:
                try:
                    ok = provider.available()
                except Exception:  # noqa: BLE001
                    ok = False
                (available_names if ok else unavailable_names).append(
                    provider.name if ok else f"{provider.name}*"
                )
            out[capability] = available_names + unavailable_names
        return out
