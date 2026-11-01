"""Video-capability providers: the local FFmpeg slideshow engine (offline tier)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .base import Capability, MockProvider


@dataclass
class FFmpegSlideshowVideo(MockProvider):
    """Offline 'video' tier: the local FFmpeg engine (real rendering, no vendor).

    Per ADR-0005/0006 this is our code-driven renderer, not a fake. Vendor
    video-gen APIs plug in beside it in M2 (CF-034 chain slot).
    """

    name: str = "mock"
    capability: Capability = Capability.VIDEO

    def available(self) -> bool:
        import shutil

        return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None

    def describe(self) -> dict[str, Any]:
        return {"name": self.name, "kind": "ffmpeg-slideshow-local"}

    def render(
        self,
        storyboard: dict[str, Any],
        frames: list[Path],
        out_path: Path,
        music_path: Path | None = None,
        narration_path: Path | None = None,
        progress_cb: Any = None,
    ) -> dict[str, Any]:
        from video_engine.slideshow import render_slideshow

        return render_slideshow(
            storyboard,
            frames,
            out_path,
            music_path=music_path,
            narration_path=narration_path,
            progress_cb=progress_cb,
        )
