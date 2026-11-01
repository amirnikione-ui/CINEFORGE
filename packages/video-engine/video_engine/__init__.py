"""CINEFORGE video engine.

Core pieces (v0 by AGENT-1, deepened by AGENT-4):
- ffmpeg: safe subprocess wrappers around ffmpeg/ffprobe
- timeline: Timeline/Track/Clip IR + compile to ordered FFmpeg step plans
- remotion_gen: scaffold code-driven Remotion projects from a Timeline
- analysis: media analysis reports (probe/scene/palette) for reverse-engineering
"""

from .timeline import (
    Animation,
    Clip,
    FFmpegPlan,
    Step,
    Timeline,
    Track,
    compile_ffmpeg_plan,
    timeline_from_dict,
    timeline_to_dict,
    total_duration,
)
from . import ffmpeg, timeline, remotion_gen, analysis  # noqa: F401

__all__ = [
    "Animation",
    "Clip",
    "FFmpegPlan",
    "Step",
    "Timeline",
    "Track",
    "compile_ffmpeg_plan",
    "timeline_from_dict",
    "timeline_to_dict",
    "total_duration",
    "ffmpeg",
    "timeline",
    "remotion_gen",
    "analysis",
]
__version__ = "0.1.0"
