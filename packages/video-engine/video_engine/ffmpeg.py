"""Thin, safe wrappers around the ffmpeg/ffprobe binaries.

v0 (AGENT-1): run() with timeout + clear errors, probe() JSON metadata.
AGENT-4 owns deepening this module (scene detection, loudness, filters…).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any


class FFmpegNotFound(RuntimeError):
    """ffmpeg/ffprobe binary is not available on PATH."""


class FFmpegError(RuntimeError):
    """An ffmpeg/ffprobe invocation failed."""

    def __init__(self, message: str, argv: list[str], stderr: str):
        super().__init__(message)
        self.argv = argv
        self.stderr = stderr[-4000:]


@dataclass
class BinaryPaths:
    ffmpeg: str
    ffprobe: str


def binary_paths() -> BinaryPaths:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise FFmpegNotFound(
            "ffmpeg/ffprobe not found on PATH. Install FFmpeg (apt install ffmpeg / brew install ffmpeg)."
        )
    return BinaryPaths(ffmpeg=ffmpeg, ffprobe=ffprobe)


def run(
    args: list[str],
    *,
    timeout: float | None = None,
    capture: bool = True,
) -> subprocess.CompletedProcess:
    """Run ffmpeg with the given args (without the leading binary)."""
    paths = binary_paths()
    argv = [paths.ffmpeg, "-hide_banner", "-loglevel", "error", "-y", *args]
    timeout = timeout if timeout is not None else float(os.environ.get("FFMPEG_TIMEOUT", "120"))
    try:
        proc = subprocess.run(
            argv, capture_output=capture, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired as exc:  # pragma: no cover - timing dependent
        raise FFmpegError(f"ffmpeg timed out after {timeout}s", argv, str(exc.stderr or "")) from exc
    if proc.returncode != 0:
        raise FFmpegError(f"ffmpeg failed (exit {proc.returncode})", argv, proc.stderr or "")
    return proc


def probe(path: str) -> dict[str, Any]:
    """Return ffprobe JSON metadata (format + streams) for a media file."""
    paths = binary_paths()
    argv = [
        paths.ffprobe, "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", path,
    ]
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=60, check=False)
    if proc.returncode != 0:
        raise FFmpegError(f"ffprobe failed for {path}", argv, proc.stderr or "")
    return json.loads(proc.stdout or "{}")


def duration_of(path: str) -> float:
    info = probe(path)
    return float(info.get("format", {}).get("duration", 0.0) or 0.0)


def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
