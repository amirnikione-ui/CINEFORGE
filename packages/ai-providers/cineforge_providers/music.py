"""Music provider: procedural cinematic pad via FFmpeg synthesis (mock tier).

Real WAV artifact — a dark minor-chord pad with slow tremolo, synthesized with
ffmpeg `aevalsrc` (no samples, no keys). Real music generation arrives via the
CINEFORGE_MUSIC_CHAIN (CF-033).
"""
from __future__ import annotations

from typing import Any

from .base import Provider, ProviderError

# A minor 9 pad: A2 110Hz, C3 130.81, E3 164.81, B3 246.94 (very low amplitudes)
_FREQS = [110.0, 130.81, 164.81, 246.94]
_AMP = [0.22, 0.16, 0.14, 0.07]


class MusicMock(Provider):
    name = "mock"
    capability = "music"

    def available(self) -> bool:
        return True

    async def run(self, *, mood: str = "dark-cinematic", duration_s: float = 30.0,
                  out_path: str = "", fps: int = 30, **_: Any) -> dict[str, Any]:
        import asyncio
        import shutil

        if not out_path:
            raise ProviderError("music mock: out_path required")
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise ProviderError("music mock: ffmpeg not available")
        d = max(2.0, min(float(duration_s), 600.0))
        terms = "+".join(f"{a}*sin(2*PI*{f}*t)" for f, a in zip(_FREQS, _AMP))
        expr = f"0.55*(1+0.12*sin(2*PI*0.25*t))*({terms})"  # slow tremolo
        filt = "lowpass=f=900,aformat=sample_rates=44100:channel_layouts=stereo"
        cmd = [
            ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", f"aevalsrc={expr}:s=44100:d={d:.2f}",
            "-af", filt, "-c:a", "pcm_s16le", out_path,
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            _, err = await asyncio.wait_for(proc.communicate(), timeout=180)
            if proc.returncode != 0:
                raise ProviderError(f"music mock: ffmpeg failed: {err.decode()[-300:]}")
            return {"path": out_path, "duration_s": d, "mood": mood, "synth": "aevalsrc-pad"}
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"music mock: {exc}") from exc
