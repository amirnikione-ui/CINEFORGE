"""Video generation capability (M2+). Mock tier reports honest unavailability —
code-driven rendering (FFmpeg slideshow / Remotion) is the real video path (ADR-0006)."""
from __future__ import annotations

from typing import Any

from .base import Provider, ProviderError


class VideoMock(Provider):
    name = "mock"
    capability = "video"

    def available(self) -> bool:
        return True

    async def run(self, **_: Any) -> dict[str, Any]:
        raise ProviderError(
            "mock video: text-to-video API unavailable offline; use the code-driven "
            "render path (render_slideshow / Remotion) — that is the CINEFORGE core."
        )
