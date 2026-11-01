"""cineforge_video — FFmpeg toolkit, slideshow renderer, analysis, Remotion runner (ADR-0006)."""
from .analysis import analyze_video
from .ffmpeg_tools import build_srt, concat_xfade_plan, drawtext_filter, probe, scale_pad_filter
from .remotion import build_project, render_remotion
from .slideshow import dims_for, render_scene_clip, render_slideshow

__all__ = ["analyze_video", "build_srt", "concat_xfade_plan", "drawtext_filter", "probe",
           "scale_pad_filter", "build_project", "render_remotion", "dims_for",
           "render_scene_clip", "render_slideshow"]
