"""FFmpeg plan & arg-builder tests (pure, no ffmpeg execution)."""
from __future__ import annotations

import pytest

from cineforge_video.ffmpeg_tools import (build_srt, chunk_text, concat_xfade_plan,
                                          esc_drawtext, scale_pad_filter, xfade_name)


def test_xfade_plan_offsets_and_duration():
    plan = concat_xfade_plan([4.0, 4.0, 4.0], ["fade", "fade", "fade"])
    # join1: offset = 4 - 0.5 = 3.5 ; total = 3.5 + 4 = 7.5
    # join2: offset = 7.5 - 0.5 = 7.0 ; total = 7.0 + 4 = 11.0
    assert plan["offsets"] == [3.5, 7.0]
    assert plan["duration"] == 11.0


def test_xfade_plan_cut_is_one_frame():
    plan = concat_xfade_plan([4.0, 4.0], ["fade", "cut"])
    assert plan["duration"] == 4.0 + 4.0 - 0.04
    assert xfade_name("slide")[1] == 0.5


def test_xfade_plan_single_scene():
    plan = concat_xfade_plan([5.0], ["fade"])
    assert plan["duration"] == 5.0 and plan["offsets"] == []


def test_srt_builder():
    srt = build_srt([{"start_s": 0.5, "end_s": 2.5, "text": "Hello world, this is CINEFORGE"}])
    assert srt.startswith("1\n00:00:00,500 --> 00:00:02,500")
    assert "Hello world," in srt


def test_chunk_text_wraps():
    words = " ".join(["word"] * 30)
    chunks = chunk_text(words, max_chars=42)
    assert all(len(c) <= 43 for c in chunks)
    assert " ".join(chunks) == words


def test_drawtext_escaping():
    assert esc_drawtext("a:b'c%d,e") == "a\\:b\\'c\\%d\\,e"


def test_scale_pad():
    assert scale_pad_filter(1080, 1920).startswith("scale=1080:1920:force_original_aspect_ratio=decrease")


def test_probe_missing_file_raises():
    from cineforge_video.ffmpeg_tools import probe

    with pytest.raises(Exception):
        probe("/nonexistent/path/file.mp4")
