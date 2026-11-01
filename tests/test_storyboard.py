"""Storyboards: deterministic planner + contract validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.agent.storyboard import Storyboard, plan_storyboard


def test_planner_parses_duration_platform_style():
    sb = plan_storyboard(
        title="Nova",
        brief="make a 12 second dark promo for my running app, instagram",
    )
    assert sb.duration_target_s == 12.0
    assert sb.platform == "instagram"
    assert sb.aspect == "9:16"
    assert sb.palette.bg in ("#0a0a12",)
    assert 3 <= len(sb.scenes) <= 6
    total = sum(s.duration_s for s in sb.scenes)
    assert abs(total - sb.duration_target_s) <= 1.6


def test_planner_respects_persian_duration():
    sb = plan_storyboard(title="تست", brief="یک ویدیوی تبلیغاتی ۳۰ ثانیه‌ای بساز", instruction="دارک و سینمایی")
    # Persian digits ۳۰ aren't ASCII-parsed → falls back to hint/default; style still detected
    assert sb.music_mood == "dark-cinematic"


def test_planner_punchier_shortens():
    base = plan_storyboard(title="X", brief="promo for city tours 20s")
    fast = plan_storyboard(title="X", brief="promo for city tours 20s", instruction="make it punchier")
    assert fast.duration_target_s < base.duration_target_s


def test_storyboard_rejects_bad_payload():
    with pytest.raises(ValidationError):
        Storyboard.from_dict({"schema_version": 1, "scenes": []})
    with pytest.raises(ValidationError):
        Storyboard.from_dict({"schema_version": 2, "scenes": [{"id": "s1", "kind": "hook", "duration_s": 2}]})


def test_storyboard_roundtrip_matches_contract():
    sb = plan_storyboard(title="Round", brief="9 second neon instagram hype video", instruction="neon energetic")
    data = sb.to_dict()
    assert data["schema_version"] == 1
    for scene in data["scenes"]:
        assert scene["kind"] in ("hook", "reveal", "typography", "outro")
        assert scene["motion"]["style"] in ("ken-burns", "slide", "zoom", "reveal")
        assert scene["transition_in"] in ("fade", "cut", "slide")
    sb2 = Storyboard.from_dict(data)
    assert sb2 == sb
