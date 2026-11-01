"""FFmpeg/FFprobe toolkit — every invocation is an argv list (no shell), timeouts everywhere."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import uuid
from pathlib import Path


class VideoEngineError(RuntimeError):
    """Raised when an ffmpeg/ffprobe invocation fails or the input is invalid."""


def run_ffmpeg(args: list[str], timeout: int = 600) -> subprocess.CompletedProcess:
    """Run ffmpeg with the standard quiet flags; raise VideoEngineError with stderr tail on failure."""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *[str(a) for a in args]]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise VideoEngineError("ffmpeg not found on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise VideoEngineError(f"ffmpeg timed out after {timeout}s") from exc
    if proc.returncode != 0:
        tail = "\n".join((proc.stderr or "").strip().splitlines()[-15:])
        raise VideoEngineError(f"ffmpeg failed (exit {proc.returncode}): {tail}")
    return proc


def run_ffprobe(args: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    """Run ffprobe; raise VideoEngineError with stderr tail on failure."""
    cmd = ["ffprobe", "-hide_banner", *[str(a) for a in args]]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise VideoEngineError("ffprobe not found on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise VideoEngineError(f"ffprobe timed out after {timeout}s") from exc
    if proc.returncode != 0:
        tail = "\n".join((proc.stderr or "").strip().splitlines()[-15:])
        raise VideoEngineError(f"ffprobe failed (exit {proc.returncode}): {tail}")
    return proc


def _require_file(path: str | Path) -> Path:
    p = Path(path)
    if not p.exists():
        raise VideoEngineError(f"media file not found: {p}")
    return p


def probe(path: str | Path) -> dict:
    """Full ffprobe JSON: format + streams."""
    p = _require_file(path)
    proc = run_ffprobe(["-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(p)])
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise VideoEngineError(f"ffprobe returned invalid JSON for {p}") from exc


def _parse_fps(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        if "/" in value:
            num, den = value.split("/", 1)
            den_f = float(den)
            return round(float(num) / den_f, 3) if den_f else 0.0
        return round(float(value), 3)
    except (ValueError, ZeroDivisionError):
        return 0.0


def summary(path: str | Path) -> dict:
    """Compact, renderer-agnostic media summary."""
    info = probe(path)
    fmt = info.get("format") or {}
    streams = info.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    duration = 0.0
    for candidate in (fmt.get("duration"), (video or {}).get("duration")):
        try:
            duration = float(candidate)
            break
        except (TypeError, ValueError):
            continue
    return {
        "duration_s": round(duration, 3),
        "width": int(video.get("width", 0)) if video else 0,
        "height": int(video.get("height", 0)) if video else 0,
        "fps": _parse_fps(video.get("avg_frame_rate") if video else None),
        "has_audio": audio is not None,
        "codec": video.get("codec_name") if video else None,
    }


def scene_detect(path: str | Path, threshold: float = 0.35) -> list[dict]:
    """Content-aware cut detection -> [{"start","end","score"}, ...].

    Uses the scene-select filter with metadata printing; interval boundaries are
    consecutive cut points (end of last interval = media duration).
    """
    p = _require_file(path)
    try:
        total = summary(p)["duration_s"]
    except VideoEngineError:
        total = 0.0
    proc = run_ffmpeg(
        [
            "-i", str(p),
            "-an",
            "-vf", f"select='gt(scene,{threshold})',metadata=print:file=-",
            "-f", "null",
            "-",
        ],
        timeout=600,
    )
    pts_times: list[float] = []
    scores: list[float] = []
    for line in (proc.stdout or "").splitlines():
        m = re.search(r"pts_time:([0-9]+\.?[0-9]*)", line)
        if m:
            pts_times.append(float(m.group(1)))
            continue
        m = re.search(r"lavfi\.scene_score=([0-9]+\.?[0-9]*(?:e-?[0-9]+)?)", line)
        if m:
            try:
                scores.append(float(m.group(1)))
            except ValueError:
                scores.append(0.0)
    cuts = list(zip(pts_times, scores))
    scenes: list[dict] = []
    for i, (cut_time, score) in enumerate(cuts):
        end = cuts[i + 1][0] if i + 1 < len(cuts) else (total or cut_time)
        if end <= cut_time:
            end = cut_time
        scenes.append({"start": round(cut_time, 3), "end": round(end, 3), "score": round(score, 4)})
    return scenes


def extract_frame(path: str | Path, t_seconds: float, out_png: str | Path) -> str:
    """Extract a single frame at ``t_seconds`` (input-side seek, frame-accurate on re-encode)."""
    p = _require_file(path)
    out = Path(out_png)
    out.parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg(["-ss", f"{max(0.0, float(t_seconds)):.3f}", "-i", str(p), "-frames:v", "1", str(out)])
    if not out.exists():
        raise VideoEngineError(f"frame extraction produced no file: {out}")
    return str(out)


def concat_clips(clip_paths: list[str | Path], out_path: str | Path) -> str:
    """Concatenate clips via the concat demuxer (stream copy first, re-encode fallback)."""
    clips = [Path(c) for c in clip_paths]
    if not clips:
        raise VideoEngineError("concat_clips: no clips given")
    for c in clips:
        if not c.exists():
            raise VideoEngineError(f"concat_clips: missing clip {c}")
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    list_file = out.parent / f"concat-{uuid.uuid4().hex}.txt"
    lines = [f"file '{str(c.resolve()).replace(chr(39), chr(39) * 2)}'" for c in clips]
    list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        try:
            run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(out)])
        except VideoEngineError:
            # Mixed parameters -> re-encode through the concat demuxer.
            run_ffmpeg(
                [
                    "-f", "concat", "-safe", "0", "-i", str(list_file),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    str(out),
                ]
            )
    finally:
        try:
            list_file.unlink(missing_ok=True)
        except OSError:
            pass
    return str(out)


def _audio_codec_args(out_path: Path) -> list[str]:
    if out_path.suffix.lower() in {".wav", ".pcm"}:
        return ["-c:a", "pcm_s16le"]
    return ["-c:a", "aac", "-b:a", "192k"]


def mix_audio(
    narration_paths: list[str | Path],
    music_path: str | Path | None,
    total_duration: float,
    out_path: str | Path,
) -> str:
    """Concatenate narration wavs (silence-padded to ``total_duration``), duck a looping
    music bed to 0.22 and amix them. Mono->stereo safe. Writes ``out_path`` (aac/wav)."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    total = max(0.5, float(total_duration))

    inputs: list[str] = []
    filters: list[str] = []
    labels: list[str] = []

    for i, narration in enumerate(narration_paths or []):
        if not Path(narration).exists():
            raise VideoEngineError(f"mix_audio: missing narration file {narration}")
        inputs += ["-i", str(narration)]
        filters.append(
            f"[{i}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo[na{i}]"
        )
        labels.append(f"[na{i}]")

    n = len(labels)
    if n:
        filters.append("".join(labels) + f"concat=n={n}:v=0:a=1[narr]")
        filters.append(f"[narr]atrim=end={total:.3f},apad=whole_dur={total:.3f}[np]")
    else:
        inputs += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
        filters.append(f"[0:a]atrim=end={total:.3f},asetpts=PTS-STARTPTS,apad=whole_dur={total:.3f}[np]")

    if music_path is not None:
        if not Path(music_path).exists():
            raise VideoEngineError(f"mix_audio: missing music file {music_path}")
        music_idx = n if n else 1
        inputs += ["-stream_loop", "-1", "-i", str(music_path)]
        filters.append(
            f"[{music_idx}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"volume=0.22[mus]"
        )
        filters.append("[np][mus]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[mx]")
    else:
        filters.append("[np]anull[mx]")

    filters.append("[mx]aresample=44100[out]")
    args = [
        *inputs,
        "-filter_complex", ";".join(filters),
        "-map", "[out]",
        "-t", f"{total:.3f}",
        *_audio_codec_args(out),
        str(out),
    ]
    run_ffmpeg(args, timeout=600)
    if not out.exists():
        raise VideoEngineError(f"mix_audio produced no file: {out}")
    return str(out)


def _srt_timestamp(seconds: float) -> str:
    ms = max(0, int(round(seconds * 1000)))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1_000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def make_srt(scenes: list[dict]) -> str:
    """Build an SRT subtitle document from storyboard scenes (headline + narration/body)."""
    blocks: list[str] = []
    cursor = 0.0
    for i, scene in enumerate(scenes, start=1):
        dur = float(scene.get("duration_s") or 0)
        headline = str(scene.get("headline") or "").strip()
        body = str(scene.get("narration") or scene.get("body") or "").strip()
        text = "\n".join(x for x in (headline, body) if x)
        if text:
            blocks.append(f"{i}\n{_srt_timestamp(cursor)} --> {_srt_timestamp(cursor + dur)}\n{text}\n")
        cursor += dur
    return "\n".join(blocks)


def _escape_filter_path(path: str | Path) -> str:
    """Escape a filesystem path for use inside an ffmpeg filter argument."""
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace(",", "\\,")


def burn_subtitles(video: str | Path, srt_path: str | Path, out_path: str | Path) -> str:
    """Re-encode ``video`` with burned-in subtitles from ``srt_path``."""
    _require_file(video)
    _require_file(srt_path)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    vf = f"subtitles=filename='{_escape_filter_path(srt_path)}'"
    run_ffmpeg(
        [
            "-i", str(video),
            "-vf", vf,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            str(out),
        ]
    )
    return str(out)


_FONT_CANDIDATES_BOLD = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
)
_FONT_CANDIDATES_REGULAR = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/chinese/NotoSansSC-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
)


def fonts() -> dict:
    """First existing bold/regular font paths from the candidate list (None when absent)."""
    def first(candidates) -> str | None:
        for c in candidates:
            if c and Path(c).exists():
                return c
        return None

    return {"bold": first(_FONT_CANDIDATES_BOLD), "regular": first(_FONT_CANDIDATES_REGULAR)}
