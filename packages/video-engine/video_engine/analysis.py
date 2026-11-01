"""Media analysis / reverse-engineering helpers (v0).

Given an input video, produce a structured report: container/stream metadata,
cut candidates (scene detection when supported by the local ffmpeg build),
and average-color palette per sampled window. AGENT-4 owns deepening this
(motion estimation, audio classification, OCR/caption extraction, narrative
pattern detection) per mission section 9.
"""

from __future__ import annotations

import os
import tempfile
from typing import Any

from . import ffmpeg as ff


def analyze(path: str, *, sample_count: int = 6) -> dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    probe = ff.probe(path)
    duration = float(probe.get("format", {}).get("duration", 0) or 0)
    streams = probe.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio = next((s for s in streams if s.get("codec_type") == "audio"), {})

    cuts = _scene_cuts(path, duration)
    palette = _palette_samples(path, duration, sample_count)

    return {
        "source": os.path.basename(path),
        "duration": duration,
        "video": {
            "codec": video.get("codec_name"),
            "width": video.get("width"),
            "height": video.get("height"),
            "fps": video.get("r_frame_rate"),
            "pix_fmt": video.get("pix_fmt"),
        },
        "audio": {
            "codec": audio.get("codec_name"),
            "sample_rate": audio.get("sample_rate"),
            "channels": audio.get("channels"),
        },
        "cuts": cuts,
        "palette": palette,
        "notes": [
            "Reverse-engineering output is inspiration for new original content, "
            "never a copy of protected material (mission section 9).",
        ],
    }


def _scene_cuts(path: str, duration: float) -> list[float]:
    """Scene-cut timestamps via the scene detection filter (best effort)."""
    if duration <= 0:
        return []
    try:
        paths = ff.binary_paths()
    except ff.FFmpegNotFound:
        return []
    import subprocess

    argv = [
        paths.ffmpeg, "-hide_banner", "-i", path,
        "-vf", "select='gt(scene,0.35)',showinfo", "-f", "null", "-",
    ]
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=120, check=False)
    except subprocess.TimeoutExpired:
        return []
    cuts: list[float] = []
    for line in (proc.stderr or "").splitlines():
        if "pts_time:" in line and "showinfo" in line:
            try:
                ts = float(line.split("pts_time:")[1].split()[0])
                if ts > 0.2:
                    cuts.append(round(ts, 2))
            except (ValueError, IndexError):
                continue
    return cuts


def _palette_samples(path: str, duration: float, count: int) -> list[dict[str, Any]]:
    """Average color of evenly spaced frames (best effort, uses ffmpeg signalstats)."""
    if duration <= 0:
        return []
    samples: list[dict[str, Any]] = []
    try:
        paths = ff.binary_paths()
    except ff.FFmpegNotFound:
        return samples
    import subprocess

    with tempfile.TemporaryDirectory() as tmp:
        for i in range(count):
            t = duration * (i + 0.5) / count
            frame = os.path.join(tmp, f"f{i}.jpg")
            argv = [
                paths.ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-ss", f"{t:.2f}", "-i", path, "-frames:v", "1", frame,
            ]
            proc = subprocess.run(argv, capture_output=True, text=True, timeout=30, check=False)
            if proc.returncode == 0 and os.path.exists(frame):
                avg = _average_color(frame)
                samples.append({"time": round(t, 2), "avg_rgb": avg})
    return samples


def _average_color(image_path: str) -> list[int] | None:
    try:
        from PIL import Image  # type: ignore
    except ImportError:
        return None
    try:
        with Image.open(image_path) as im:
            im_small = im.convert("RGB").resize((8, 8))
            pixels = list(im_small.getdata())
            r = sum(p[0] for p in pixels) // len(pixels)
            g = sum(p[1] for p in pixels) // len(pixels)
            b = sum(p[2] for p in pixels) // len(pixels)
            return [r, g, b]
    except Exception:
        return None
