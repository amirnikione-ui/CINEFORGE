"""Provider chain tests: fallback order, honest attempt log, mock tier guarantee."""

from __future__ import annotations

import os

import pytest

from ai_providers import Capability, ProviderError, ProviderUnavailable, call_with_fallback
from ai_providers.llm import ChatMessage, MockLLM
from ai_providers.registry import Registry


class FakeProvider:
    def __init__(self, name: str, *, available: bool = True, fail_with: Exception | None = None, mock: bool = False):
        self.name = name
        self.capability = Capability.LLM
        self._available = available
        self._fail = fail_with
        self._mock = mock
        self.calls = 0

    def available(self) -> bool:
        return self._available

    def is_mock(self) -> bool:
        return self._mock

    def describe(self):
        return {"name": self.name}

    def chat(self, messages, **_):
        self.calls += 1
        if self._fail:
            raise self._fail
        return "ok"


def test_fallback_skips_unavailable_then_failing_then_succeeds():
    a = FakeProvider("a", available=False)
    b = FakeProvider("b", fail_with=ProviderError("boom"))
    c = FakeProvider("c")
    result = call_with_fallback([a, b, c], "op", lambda p: p.chat([]))
    assert result.provider == "c"
    assert [x.provider for x in result.attempts] == ["a", "b", "c"]
    assert result.attempts[0].error == "unavailable"
    assert b.calls == 1 and c.calls == 1


def test_fallback_raises_when_all_fail():
    a = FakeProvider("a", fail_with=ProviderError("x"))
    b = FakeProvider("b", fail_with=ProviderError("y"))
    with pytest.raises(ProviderError):
        call_with_fallback([a, b], "op", lambda p: p.chat([]))


def test_require_non_mock_skips_mock_providers():
    mock = MockLLM()
    real = FakeProvider("real")
    result = call_with_fallback([mock, real], "op", lambda p: p.chat([]), require_non_mock=True)
    assert result.provider == "real"
    assert "mock" not in [a.provider for a in result.attempts]


def test_mock_llm_always_available_and_deterministic():
    llm = MockLLM()
    assert llm.available() is True
    out1 = llm.chat([ChatMessage(role="user", content="hello")])
    out2 = llm.chat([ChatMessage(role="user", content="hello")])
    assert out1 == out2


def test_registry_mock_terminal_guarantee():
    # even with a nonsense chain, the registry appends the mock tier
    os.environ["CINEFORGE_LLM_CHAIN"] = "doesnotexist,mock"
    try:
        reg = Registry()
        chain = reg.chain(Capability.LLM)
        assert chain[-1].name == "mock"
        assert reg.describe()[Capability.LLM.value][-1] == "mock"
    finally:
        os.environ.pop("CINEFORGE_LLM_CHAIN", None)


def test_registry_video_chain_resolves_ffmpeg_local():
    reg = Registry()
    names = reg.available_names(Capability.VIDEO)
    assert names, "video chain must resolve (mock = local ffmpeg)"


def test_registry_health_shape_matches_contract():
    reg = Registry()
    desc = reg.describe()
    for cap in ("llm", "image", "tts", "stt", "music", "video"):
        assert cap in desc, f"capability {cap} missing from health shape"
