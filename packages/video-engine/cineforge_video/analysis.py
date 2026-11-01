"""Reference-video analysis (M3 entrypoint, contracts «media/analyze»).

Honest signal processing — style extraction, never content copying (D-010/ADR):
  • scene cuts   : downsampled frame diffs (Pillow RMS) → threshold peaks
  • pacing       : cut-interval stats + first-3s density (hook heuristic)
  • palette      : per-scene dominant colors (Pillow adaptive quantize)
  • motion       : mean frame-diff per shot (normalized)
  • loudness     : per-second RMS via ffmpeg astats
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .ffmpeg_tools import ffprobe_bin, ffmpeg_bin, probe

_FRAME_CAP = 240  # analysis safety cap


def _sample_frames(video: Path, fps: float, outdir: Path) -> list[Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = [ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
           "-i", str(video), "-vf", f"fps={fps},scale=160:-2",
           "-frames:v", str(_FRAME_CAP), str(outdir / "f%04d.png")]
    subprocess.run(cmd, capture_output=True, timeout=300, check=False)
    return sorted(outdir.glob("f*.png"))


def _rms_diff(a, b) -> float:
    from PIL import Image, ImageChops, ImageStat

    diff = ImageChops.difference(a, b)
    stat = ImageStat.Stat(diff)
    mean = sum(stat.mean) / max(1, len(stat.mean))
    return mean / 255.0


def analyze_video(video: str | Path, *, sample_fps: float = 3.0,
                  cut_threshold: float = 0.14) -> dict[str, Any]:
    video = Path(video)
    meta = probe(video)
    duration = meta.get("duration_s", 0.0)
    notes: list[str] = []

    with tempfile.TemporaryDirectory(prefix="cineforge-an-") as td:
        frames = _sample_frames(video, sample_fps, Path(td))
        if len(frames) < 2:
            notes.append("not enough frames sampled; raising thresholds confidence low")
        from PIL import Image

        imgs = [Image.open(f).convert("RGB") for f in frames]
        diffs = [_rms_diff(imgs[i], imgs[i + 1]) for i in range(len(imgs) - 1)]
        tpf = 1.0 / sample_fps
        cuts = [round((i + 1) * tpf, 2) for i, d in enumerate(diffs) if d > cut_threshold]

        # scenes between cuts
        bounds = [0.0] + cuts + [duration or (len(imgs) * tpf)]
        scenes = []
        palettes: list[str] = []
        for i in range(len(bounds) - 1):
            start, end = bounds[i], bounds[i + 1]
            if end - start < 0.2:
                continue
            seg = imgs[int(start * sample_fps): max(int(start * sample_fps) + 1,
                                                    int(end * sample_fps))]
            motion = sum(diffs[int(start * sample_fps): max(int(start * sample_fps) + 1,
                                                            int(end * sample_fps) - 1)] or [0]) \
                / max(1, len(seg))
            pal = _dominant_colors(seg[len(seg) // 2] if seg else imgs[0])
            palettes += pal[:3]
            scenes.append({"start": round(start, 2), "end": round(end, 2),
                           "duration": round(end - start, 2),
                           "motion": round(min(1.0, motion * 4), 3), "palette": pal})
        palettes = list(dict.fromkeys(palettes))[:8]

    intervals = [scenes[i + 1]["start"] - scenes[i]["start"] for i in range(len(scenes) - 1)] \
        if len(scenes) > 1 else []
    intervals.sort()
    median_cut = intervals[len(intervals) // 2] if intervals else (duration or 0)
    first3 = sum(1 for c in cuts if c <= 3.0)

    loudness = _loudness_envelope(video, duration)

    return {
        "duration_s": duration,
        "fps_estimate": meta.get("fps", 0.0),
        "cuts": cuts,
        "scenes": scenes,
        "pacing": {"median_cut_s": round(float(median_cut), 2),
                   "first3s_cuts": first3,
                   "hook_density": round(first3 / 3.0, 2)},
        "loudness": loudness,
        "palette": palettes,
        "notes": notes + ["style extraction only — source media is never re-exported (ADR-0009 ethics)"],
    }


def _dominant_colors(img, k: int = 5) -> list[str]:
    q = img.resize((64, 64)).quantize(colors=k, method=2).convert("RGB")
    counts: dict[tuple[int, int, int], int] = {}
    for px in q.getdata():
        counts[px] = counts.get(px, 0) + 1
    ordered = sorted(counts.items(), key=lambda kv: -kv[1])
    return ["#%02x%02x%02x" % c for c, _ in ordered[:k]]


def _loudness_envelope(video: Path, duration: float, per_second: bool = True) -> list[dict[str, Any]]:
    if duration <= 0:
        return []
    step = 1.0 if per_second else 0.5
    cmd = [ffmpeg_bin(), "-hide_banner", "-nostats",
           "-i", str(video), "-af", f"astats=metadata=1:reset={int(step)}",
           "-f", "null", "-"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)
    except subprocess.TimeoutExpired:
        return []
    env: list[dict[str, Any]] = []
    t = 0.0
    for line in (res.stderr or "").splitlines():
        if "RMS_level" in line and ":" in line:
            try:
                rms = float(line.split(":")[-1].strip().replace("-inf", "-90"))
            except ValueError:
                continue
            env.append({"t": round(t, 2), "rms": round(max(rms, -90.0), 1)})
            t += step
            if t > duration + 1:
                break
    return env
