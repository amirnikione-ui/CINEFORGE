"""FFmpeg toolkit (ADR-0006): probe, SRT, safe arg builders, timeout-guarded runs.

Security posture (docs/SECURITY.md): argv lists only — never shell strings;
every path resolved under the project workspace by callers.
"""
from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from typing import Any

from backend.app.config import FFMPEG_TIMEOUT_S


def ffmpeg_bin() -> str:
    p = shutil.which("ffmpeg")
    if not p:
        raise RuntimeError("ffmpeg binary not found on PATH")
    return p


def ffprobe_bin() -> str:
    p = shutil.which("ffprobe")
    if not p:
        raise RuntimeError("ffprobe binary not found on PATH")
    return p


async def _run(cmd: list[str], *, timeout: int | None = None) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout or FFMPEG_TIMEOUT_S)
    except TimeoutError:
        proc.kill()
        raise
    return proc.returncode or 0, out.decode(errors="replace"), err.decode(errors="replace")


def run_sync(cmd: list[str], *, timeout: int | None = None) -> tuple[int, str, str]:
    """Blocking wrapper for worker contexts."""
    import subprocess

    try:
        res = subprocess.run(cmd, capture_output=True, text=True,
                             timeout=timeout or FFMPEG_TIMEOUT_S, check=False)
        return res.returncode, res.stdout or "", res.stderr or ""
    except subprocess.TimeoutExpired:
        raise


def probe(path: str | Path) -> dict[str, Any]:
    """ffprobe → {duration_s, width, height, fps, codec, streams}."""
    cmd = [ffprobe_bin(), "-v", "error", "-print_format", "json",
           "-show_format", "-show_streams", str(path)]
    code, out, err = run_sync(cmd, timeout=60)
    if code != 0:
        raise RuntimeError(f"ffprobe failed: {err[-300:]}")
    data = json.loads(out or "{}")
    fmt = data.get("format", {})
    v_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    fps = 0.0
    rate = v_stream.get("r_frame_rate") or "0/1"
    try:
        num, den = rate.split("/")
        fps = float(num) / float(den) if float(den) else 0.0
    except (ValueError, ZeroDivisionError):
        pass
    return {
        "duration_s": float(fmt.get("duration", 0) or 0),
        "width": int(v_stream.get("width", 0) or 0),
        "height": int(v_stream.get("height", 0) or 0),
        "fps": round(fps, 3),
        "codec": v_stream.get("codec_name", ""),
        "streams": [{"codec_type": s.get("codec_type"), "codec_name": s.get("codec_name")}
                    for s in data.get("streams", [])],
    }


# ------------------------------------------------------------------ SRT ----

def _fmt_ts(seconds: float) -> str:
    ms = int(round(max(0.0, seconds) * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def chunk_text(text: str, max_chars: int = 42) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    cur = ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > max_chars:
            chunks.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        chunks.append(cur)
    return chunks


def build_srt(segments: list[dict[str, Any]]) -> str:
    """segments: [{start_s, end_s, text}] → SRT string (subtitle burn-in)."""
    out: list[str] = []
    idx = 1
    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        dur = seg.get("end_s", seg.get("start_s", 0) + 2) - seg.get("start_s", 0)
        pieces = chunk_text(text)
        per = dur / max(1, len(pieces))
        for i, piece in enumerate(pieces):
            start = seg["start_s"] + i * per
            out.append(f"{idx}\n{_fmt_ts(start)} --> {_fmt_ts(start + per)}\n{piece}\n")
            idx += 1
    return "\n".join(out)


# ------------------------------------------------- drawtext arg builders ----

_DRAWTEXT_ESCAPES = str.maketrans({
    "\\": "\\\\", ":": "\\:", "'": "\\'", "%": "\\%", ",": "\\,",
    "[": "\\[", "]": "\\]", ";": "\\;", "=": "\\=",
})


def esc_drawtext(text: str) -> str:
    return text.translate(_DRAWTEXT_ESCAPES)


def find_font() -> str | None:
    """First available TTF suitable for drawtext (DejaVu preferred)."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return None


def drawtext_filter(text: str, *, size: int, color: str, y_expr: str,
                    x_expr: str = "(w-text_w)/2", fade_in: float = 0.5,
                    fade_out_at: float | None = None) -> str:
    """Build one drawtext filter string with fade-in alpha (deterministic)."""
    alpha = f"if(lt(t,{fade_in}),t/{fade_in},1)"
    if fade_out_at is not None:
        alpha = f"if(lt(t,{fade_in}),t/{fade_in},if(gt(t,{fade_out_at}),max(0,1-(t-{fade_out_at})/0.4),1))"
    return (
        f"drawtext=fontfile={find_font() or 'Sans'}:text='{esc_drawtext(text)}'"
        f":fontsize={size}:fontcolor={color}:x={x_expr}:y={y_expr}"
        f":borderw=2:bordercolor=black@0.55:shadowx=0:shadowy=3:shadowcolor=black@0.5"
        f":alpha='{alpha}'"
    )


def scale_pad_filter(width: int, height: int) -> str:
    return (f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1")


# xfade transition name per storyboard transition_in
def xfade_name(transition_in: str) -> tuple[str, float]:
    if transition_in == "slide":
        return "slideleft", 0.5
    if transition_in == "cut":
        return "fade", 0.04
    return "fade", 0.5


def concat_xfade_plan(durations: list[float], transitions: list[str]) -> dict[str, Any]:
    """Compute xfade offsets & final duration for a chain of scene clips.

    xfade semantics: output_duration = offset + second_input_duration.
    transitions[i] is scene i's transition_in (join of clip i-1 → clip i).
    """
    if not durations:
        raise ValueError("no durations")
    offsets: list[float] = []
    total = float(durations[0])
    for i in range(1, len(durations)):
        _, fdur = xfade_name(transitions[i] if i < len(transitions) else "fade")
        off = max(0.04, total - fdur)
        offsets.append(round(off, 3))
        total = off + float(durations[i])
    return {"offsets": offsets, "duration": round(max(0.5, total), 3)}
