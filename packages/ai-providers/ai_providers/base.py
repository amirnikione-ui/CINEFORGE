"""Provider base types — capability enums, protocols, fallback executor."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Protocol

log = logging.getLogger("cineforge.providers")


class Capability(str, Enum):
    LLM = "llm"
    IMAGE = "image"
    TTS = "tts"
    STT = "stt"
    MUSIC = "music"
    VIDEO = "video"


CAPABILITY_ORDER = [c.value for c in Capability]


class ProviderError(Exception):
    """A provider failed while executing a call (network, HTTP, decode...)."""


class ProviderUnavailable(Exception):
    """The provider is not configured/usable in this environment (e.g. no API key)."""


class Provider(Protocol):
    """Every provider exposes at least: name, capability, availability, describe()."""

    name: str
    capability: Capability

    def available(self) -> bool: ...

    def describe(self) -> dict[str, Any]: ...


@dataclass
class MockProvider:
    """Marker mixin for the offline tier (ADR-0005: real artifacts, honest label)."""

    def is_mock(self) -> bool:
        return True


@dataclass
class Attempt:
    provider: str
    ok: bool
    error: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class FallbackResult:
    value: Any
    provider: str
    is_mock: bool
    attempts: list[Attempt]

    def attempt_log(self) -> list[dict[str, Any]]:
        return [
            {"provider": a.provider, "ok": a.ok, "error": a.error}
            for a in self.attempts
        ]


def call_with_fallback(
    providers: list[Provider],
    operation: str,
    invoke: Callable[[Provider], Any],
    *,
    require_non_mock: bool = False,
) -> FallbackResult:
    """Walk the chain in priority order; first success wins.

    - ProviderUnavailable -> skip silently (not configured).
    - ProviderError -> log and continue to the next provider.
    - If `require_non_mock`, skip mock providers (used when the caller wants a
      genuine vendor attempt first but still degrades to mock at the end).
    """
    attempts: list[Attempt] = []
    chain = ", ".join(p.name for p in providers) or "<empty>"
    for provider in providers:
        if require_non_mock and getattr(provider, "is_mock", lambda: False)():
            continue
        if not provider.available():
            attempts.append(Attempt(provider=provider.name, ok=False, error="unavailable"))
            continue
        try:
            value = invoke(provider)
        except ProviderUnavailable as exc:
            attempts.append(Attempt(provider=provider.name, ok=False, error=str(exc)))
            continue
        except ProviderError as exc:
            log.warning("provider %s failed at %s: %s", provider.name, operation, exc)
            attempts.append(Attempt(provider=provider.name, ok=False, error=str(exc)))
            continue
        except Exception as exc:  # defensive: vendor SDKs raise anything
            log.warning("provider %s crashed at %s: %r", provider.name, operation, exc)
            attempts.append(Attempt(provider=provider.name, ok=False, error=repr(exc)))
            continue
        attempts.append(Attempt(provider=provider.name, ok=True))
        return FallbackResult(
            value=value,
            provider=provider.name,
            is_mock=getattr(provider, "is_mock", lambda: False)(),
            attempts=attempts,
        )
    raise ProviderError(
        f"all providers failed for capability chain [{chain}] during {operation}; "
        f"attempts={ [a.__dict__ for a in attempts] }"
    )
