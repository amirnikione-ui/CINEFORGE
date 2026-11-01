"""Provider capability contracts (ADR-0004/0005).

Every provider implements `available()` and an async call; the registry walks the
configured chain (CINEFORGE_*_CHAIN) and falls back on absence/failure. The
terminal `mock` tier always produces REAL local artifacts (never fake success).
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

import httpx

from backend.app import config


class ProviderError(RuntimeError):
    """Raised by providers on failure — orchestrator falls back to the next one."""


class Provider(abc.ABC):
    name: str = "base"
    capability: str = "base"

    @abc.abstractmethod
    def available(self) -> bool: ...

    @abc.abstractmethod
    async def run(self, **kwargs: Any) -> dict[str, Any]: ...


@dataclass
class CallResult:
    """Uniform provider result: `out` is the artifact dict, `provider` the tier used."""

    provider: str
    out: dict[str, Any] = field(default_factory=dict)


async def call_chain(
    capability: str,
    providers: list[Provider],
    run_kwargs: dict[str, Any],
) -> CallResult:
    """Walk the chain: first `available()` provider wins; errors fall through."""
    errors: list[str] = []
    for p in providers:
        if p.capability != capability:
            continue
        if not p.available():
            errors.append(f"{p.name}: not configured")
            continue
        try:
            out = await p.run(**run_kwargs)
            return CallResult(provider=p.name, out=out)
        except (ProviderError, httpx.HTTPError, TimeoutError) as exc:
            errors.append(f"{p.name}: {type(exc).__name__}: {exc}")
    raise ProviderError(
        f"no provider available for capability '{capability}' — tried: "
        + "; ".join(errors or ["(empty chain)"])
    )


async def _post_json(
    url: str, *, headers: dict[str, str], json_body: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None, files: Any = None, timeout: float = 90.0,
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, headers=headers, json=json_body, data=data, files=files)
        resp.raise_for_status()
        return resp.json()


async def _post_binary(url: str, *, headers: dict[str, str], json_body: Any = None,
                       timeout: float = 120.0) -> bytes:
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, headers=headers, json=json_body)
        resp.raise_for_status()
        return resp.content
