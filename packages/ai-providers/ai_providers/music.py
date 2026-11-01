"""Music providers: offline procedural cinematic bed via FFmpeg (real audio)."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .base import Capability, MockProvider, ProviderError

MOOD_PRESETS: dict[str, dict[str, Any]] = {
    "dark-cinematic": {
        "root": 110.0,          # A2
        "chord": [110.0, 164.81, 220.0],  # A2, E3, A3 (open fifth color)
        "sub": 55.0,            # A1
        "pulse_rate": 0.42,
        "noise": "brown",
        "noise_cut": 420,
        "echo": "0.8:0.85:480|900:0.28|0.18",
        "gain": 0.55,
    },
    "neon-energetic": {
        "root": 130.81,         # C3
        "chord": [130.81, 196.0, 261.63],  # C3, G3, C4
        "sub": 65.41,           # C2
        "pulse_rate": 0.9,
        "noise": "pink",
        "noise_cut": 900,
        "echo": "0.7:0.8:320|640:0.25|0.15",
        "gain": 0.62,
    },
    "clean-minimal": {
        "root": 146.83,         # D3
        "chord": [146.83, 220.0, 293.66],  # D3, A3, D4
        "sub": 73.42,           # D2
        "pulse_rate": 0.3,
        "noise": "pink",
        "noise_cut": 700,
        "echo": "0.85:0.8:560|1100:0.22|0.12",
        "gain": 0.5,
    },
    "luxury-gold": {
        "root": 123.47,         # B2
        "chord": [123.47, 185.0, 246.94],  # B2, F#3, B3
        "sub": 61.74,           # B1
        "pulse_rate": 0.36,
        "noise": "brown",
        "noise_cut": 500,
        "echo": "0.85:0.88:620|1200:0.26|0.16",
        "gain": 0.52,
    },
}


def preset_for_mood(mood: str | None) -> dict[str, Any]:
    key = (mood or "dark-cinematic").lower()
    if key in MOOD_PRESETS:
        return MOOD_PRESETS[key]
    for name, preset in MOOD_PRESETS.items():
        if any(part in key for part in name.split("-")):
            return preset
    return MOOD_PRESETS["dark-cinematic"]


@dataclass
class ProceduralMusic(MockProvider):
    """Offline tier: layered pad + sub pulse + air noise, mixed by FFmpeg.

    Real, listenable audio bed — chords and texture, honestly labeled mock.
    """

    name: str = "mock"
    capability: Capability = Capability.MUSIC

    def available(self) -> bool:
        return shutil.which("ffmpeg") is not None

    def describe(self) -> dict[str, Any]:
        return {"name": self.name, "kind": "ffmpeg-procedural", "moods": sorted(MOOD_PRESETS)}

    def generate(self, *, duration_s: float, mood: str | None, out_path: Path) -> dict[str, Any]:
        if shutil.which("ffmpeg") is None:
            raise ProviderError("procedural music requires ffmpeg on PATH")
        p = preset_for_mood(mood)
        duration_s = max(2.0, float(duration_s))
        fade_out_start = max(0.5, duration_s - 3.0)

        inputs: list[str] = []
        # chord pad: root + fifth + octave, slow tremolo for breathing
        for i, freq in enumerate(p["chord"]):
            inputs += [
                "-f", "lavfi", "-t", f"{duration_s:.3f}",
                "-i", f"sine=frequency={freq}:sample_rate=44100",
            ]
        # sub pulse
        inputs += [
            "-f", "lavfi", "-t", f"{duration_s:.3f}",
            "-i", f"sine=frequency={p['sub']}:sample_rate=44100",
        ]
        # air texture
        inputs += [
            "-f", "lavfi", "-t", f"{duration_s:.3f}",
            "-i", f"anoisesrc=color={p['noise']}:sample_rate=44100:amplitude=0.05",
        ]

        n_chord = len(p["chord"])
        parts: list[str] = []
        for i in range(n_chord):
            trem = 0.18 + 0.1 * (i % 2)
            parts.append(
                f"[{i}:a]tremolo=f={p['pulse_rate'] / (i + 1):.3f}:d={trem:.2f},volume={0.22 / (i + 1):.3f}[c{i}]"
            )
        sub_idx = n_chord
        parts.append(
            f"[{sub_idx}:a]tremolo=f={p['pulse_rate'] * 2:.3f}:d=0.85,volume=0.30[sub]"
        )
        air_idx = sub_idx + 1
        parts.append(f"[{air_idx}:a]lowpass=f={p['noise_cut']},volume=0.05[air]")
        mix_ins = "".join(f"[c{i}]" for i in range(n_chord)) + "[sub][air]"
        parts.append(
            f"{mix_ins}amix=inputs={n_chord + 2}:normalize=1,"
            f"lowpass=f=2400,highpass=f=40,"
            f"aecho={p['echo']},"
            f"afade=t=in:st=0:d=2.0,afade=t=out:st={fade_out_start:.3f}:d={duration_s - fade_out_start:.3f},"
            f"volume={p['gain']},alimiter=limit=0.9"
        )

        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs,
               "-filter_complex", ";".join(parts), "-ac", "2", "-ar", "44100"]
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cmd += ["-t", f"{duration_s:.3f}", str(out_path)]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            raise ProviderError(f"procedural music ffmpeg failed: {proc.stderr[-400:]}")
        return {"provider": self.name, "path": str(out_path), "mood": mood or "dark-cinematic", "duration_s": duration_s}
