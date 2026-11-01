"""video_engine — FFmpeg toolkit + slideshow renderer + Remotion runner.

Requires ffmpeg/ffprobe on PATH for the Python toolkit; Remotion rendering
additionally requires Node.js >= 18 and Chromium (run in the worker container).
"""
from __future__ import annotations

from . import ffmpeg_tools, remotion_runner, slideshow
from .ffmpeg_tools import VideoEngineError

__all__ = ["ffmpeg_tools", "remotion_runner", "slideshow", "VideoEngineError"]
