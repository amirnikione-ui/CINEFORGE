"""Provider registry + mock tier behavior (ADR-0004/0005)."""
from __future__ import annotations

import wave
from pathlib import Path

from ai_providers import ProviderError, ProviderRegistry
from ai_providers.base import BaseProvider


def test_mock_only_registry_status():
    registry = ProviderRegistry(chains={"llm": ["mock"], "image": ["mock"], "tts": ["mock"]})
    status = registry.status()
    assert status["llm"] == ["mock"]
    assert status["image"] == ["mock"]
    first = registry.first_available("llm")
    assert first is not None and first.name == "mock"


def test_fallback_walks_chain_on_error():
    class Failing(BaseProvider):
        name = "failing"

        def synthesize(self, text, out_path_wav):  # matches TTS signature
            raise ProviderError("boom")

    registry = ProviderRegistry(chains={"tts": ["failing", "mock"]})
    registry.register_provider("failing", "tts", Failing)
    meta, used = registry.run_with_fallback(
        "tts", lambda p: p.synthesize("hello world this is a narration test", "/tmp/fb.wav")
    )
    assert used == "mock"
    assert meta.get("duration_s", 0) > 0


def test_all_providers_failing_raises():
    class Failing(BaseProvider):
        name = "failing"

        def synthesize(self, text, out_path_wav):
            raise ProviderError("boom")

    registry = ProviderRegistry(chains={"tts": ["failing"]})
    registry.register_provider("failing", "tts", Failing)
    try:
        registry.run_with_fallback("tts", lambda p: p.synthesize("x", "/tmp/x.wav"))
        raise AssertionError("expected ProviderError")
    except ProviderError:
        pass


def _wav_duration(path: str) -> float:
    with wave.open(path, "rb") as w:
        return w.getnframes() / w.getframerate()


def test_mock_tts_duration_matches_word_budget(tmp_path: Path):
    from ai_providers.mock import MockTTS

    text = "one two three four five six seven eight nine ten"  # 10 words → ~4.2s
    out = str(tmp_path / "n.wav")
    meta = MockTTS().synthesize(text, out)
    duration = _wav_duration(out)
    expected = 10 * 0.42
    assert abs(duration - expected) / expected < 0.2, f"{duration} vs {expected}"
    assert abs(meta["duration_s"] - duration) < 0.2


def test_mock_music_bed(tmp_path: Path):
    from ai_providers.mock import MockMusic

    out = str(tmp_path / "m.wav")
    meta = MockMusic().generate_music("dark-cinematic", 6.0, out)
    duration = _wav_duration(out)
    assert 5.0 <= duration <= 7.0
    assert meta["provider"] == "mock"


def test_mock_image_real_png(tmp_path: Path):
    from PIL import Image

    from ai_providers.mock import MockImage

    out = str(tmp_path / "f.png")
    meta = MockImage().generate_image(
        "dark cityscape, neon reflections",
        out,
        width=1080,
        height=1920,
        palette={"bg": "#0a0a12", "primary": "#7c5cff", "accent": "#00e5ff", "text": "#f5f5ff"},
        headline="RUN BEYOND LIMITS",
        scene_index=1,
        scene_count=5,
    )
    with Image.open(out) as img:
        assert img.size == (1080, 1920)
    assert meta["provider"] == "mock"
    assert Path(out).stat().st_size > 20_000
