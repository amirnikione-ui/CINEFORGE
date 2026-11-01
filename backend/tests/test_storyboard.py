"""Offline director tests: storyboard builder, planner parsing, normalization."""
from __future__ import annotations

from cineforge_agent.planner import summarize_brief
from cineforge_agent.storyboard import build_offline_storyboard, dump_storyboard, validate_storyboard


def test_offline_storyboard_structure():
    sb = build_offline_storyboard("30s cinematic promo for Nova Runners, dark mood",
                                  title="Nova", platform="instagram",
                                  style="cinematic-dark", duration_hint_s=30)
    data = dump_storyboard(sb)
    assert data["schema_version"] == 1
    assert len(data["scenes"]) == 5
    total = sum(s["duration_s"] for s in data["scenes"])
    assert abs(total - 30) <= 3.0  # ±10% rule
    kinds = [s["kind"] for s in data["scenes"]]
    assert kinds[0] == "hook" and kinds[-1] == "outro"
    assert all(s["headline"] for s in data["scenes"])
    assert all(s["narration"] for s in data["scenes"])


def test_normalization_pulls_total_to_target():
    data = {"schema_version": 1, "title": "t", "platform": "instagram", "aspect": "9:16",
            "fps": 30, "duration_target_s": 20, "palette": {}, "music_mood": "m",
            "scenes": [{"id": "s1", "kind": "hook", "duration_s": 50, "headline": "H"},
                       {"id": "s2", "kind": "outro", "duration_s": 50, "headline": "O"}]}
    sb = validate_storyboard(data)
    total = sum(s.duration_s for s in sb.scenes)
    assert abs(total - 20) / 20 < 0.10


def test_brief_parsing():
    info = summarize_brief("make a 45 second teaser for youtube, energetic, فارسی narration")
    assert info["duration"] == 45
    assert info["platform"] == "youtube"
    assert info["style"] == "bold-energy"
    assert info["narration_language"] == "fa"


def test_llm_storyboard_validation():
    data = {"schema_version": 1, "title": "x", "platform": "instagram", "aspect": "9:16",
            "fps": 30, "duration_target_s": 30,
            "palette": {"bg": "#000000", "primary": "#111111", "accent": "#222222",
                        "text": "#ffffff"},
            "music_mood": "dark",
            "scenes": [{"id": "s1", "kind": "hook", "duration_s": 30, "headline": "HI"}]}
    sb = validate_storyboard(data)
    assert sb.scenes[0].motion.style == "ken-burns"  # defaults applied
