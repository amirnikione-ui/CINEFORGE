"""Provider chain & fallback tests (CF-012/CF-019) — no network access needed."""
from __future__ import annotations

import asyncio

import pytest

from cineforge_providers.base import CallResult, Provider, ProviderError, call_chain


class FlakyProvider(Provider):
    name, capability = "flaky", "llm"

    def __init__(self, fail: bool = True):
        self._fail = fail

    def available(self):
        return True

    async def run(self, **kw):
        if self._fail:
            raise ProviderError("boom")
        return {"text": "ok"}


class AbsentProvider(Provider):
    name, capability = "absent", "llm"

    def available(self):
        return False

    async def run(self, **kw):  # pragma: no cover
        raise AssertionError("must not be called")


class GoodProvider(Provider):
    name, capability = "good", "llm"

    def available(self):
        return True

    async def run(self, **kw):
        return {"text": "from-good"}


def test_fallback_walks_chain_on_error():
    res = asyncio.run(call_chain("llm", [FlakyProvider(True), GoodProvider()], {}))
    assert isinstance(res, CallResult)
    assert res.provider == "good"
    assert res.out["text"] == "from-good"


def test_fallback_skips_unavailable():
    res = asyncio.run(call_chain("llm", [AbsentProvider(), GoodProvider()], {}))
    assert res.provider == "good"


def test_chain_exhaustion_is_honest():
    with pytest.raises(ProviderError) as exc:
        asyncio.run(call_chain("llm", [AbsentProvider(), FlakyProvider(True)], {}))
    assert "absent" in str(exc.value) and "flaky" in str(exc.value)


def test_mock_llm_always_available():
    from cineforge_providers.llm import LLMMock

    res = asyncio.run(call_chain("llm", [LLMMock()], {"system": "s", "user": "brief"}))
    assert res.provider == "mock"


def test_registry_status_shape():
    from cineforge_providers.registry import Registry

    reg = Registry()
    status = reg.status()
    assert status["llm"][-1] == "mock"
    assert status["music"] == ["mock"]
    for cap, chain in status.items():
        assert chain, f"capability {cap} must never be empty"
