"""Offline-first mock tier — REAL artifacts, clearly labeled ``provider: "mock"`` (ADR-0005).

* ``MockLLM``    — deterministic storyboard-shaped JSON planner (safety net; the rich
                   deterministic director lives in ``backend/app/agent/mock_director.py``).
* ``MockImage``  — Pillow-rendered 1080x1920 key art: gradient, vignette, film grain,
                   headline typography, scene labels.
* ``MockTTS``    — pure-stdlib speech-like hum WAV (22050 Hz, 16-bit mono).
* ``MockMusic``  — pure-stdlib layered drone bed, mood-seeded and deterministic.
* ``MockSTT``    — honest local stub transcription.
* ``MockVideo``  — availability marker for /health; actual video renders via the
                   local FFmpeg/Remotion pipeline (see packages/video-engine).
"""
from __future__ import annotations

import json
import math
import os
import random
import struct
import wave
import zlib
from pathlib import Path

from .base import ImageProvider, LLMProvider, MusicProvider, ProviderError, STTProvider, TTSProvider, VideoProvider

SR = 22_050  # mock audio sample rate

_BOLD_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
)
_REG_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/chinese/NotoSansSC-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
)

_MOCK_PALETTES = {
    "cinematic-dark": {"bg": "#0a0a12", "primary": "#7c5cff", "accent": "#00e5ff", "text": "#f5f5ff"},
    "vibrant-neon": {"bg": "#12041f", "primary": "#ff2fb3", "accent": "#00ffd5", "text": "#fff6fd"},
    "corporate-clean": {"bg": "#f4f7fb", "primary": "#1d4ed8", "accent": "#0ea5e9", "text": "#0f172a"},
    "warm-documentary": {"bg": "#1a120b", "primary": "#e0a458", "accent": "#f4ead5", "text": "#fdf6ec"},
}

_STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "with", "this", "that", "of", "to", "in", "on", "at",
    "by", "is", "are", "was", "were", "be", "make", "made", "create", "promo", "video", "film",
    "clip", "second", "seconds", "please", "new", "it", "its", "our", "your", "their", "we",
    "you", "i", "my", "me", "us", "they", "from", "into", "about", "as", "so", "very", "really",
    "just", "some", "any", "more", "most", "want", "need", "like", "show", "tell", "using",
    "use", "style", "mood", "vibe", "cinematic", "dark", "bright", "warm", "cool",
}


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    v = str(value).lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    try:
        return tuple(int(v[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except (ValueError, IndexError):
        return (10, 10, 18)


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]


def _stable_seed(*parts: object) -> int:
    return zlib.crc32("|".join(str(p) for p in parts).encode("utf-8"))


def _keywords(text: str, limit: int = 5) -> list[str]:
    out: list[str] = []
    for word in text.lower().split():
        cleaned = "".join(ch for ch in word if ch.isalnum())
        if len(cleaned) < 3 or cleaned in _STOPWORDS or cleaned in out:
            continue
        out.append(cleaned)
        if len(out) >= limit:
            break
    return out


def _write_wav(path: str, samples: list[float], sample_rate: int = SR) -> float:
    """Write 16-bit mono PCM and return the real duration in seconds."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    frames = bytearray()
    for s in samples:
        clamped = max(-1.0, min(1.0, s))
        frames += struct.pack("<h", int(clamped * 32767))
    with wave.open(str(out), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))
    return len(samples) / float(sample_rate)


# --------------------------------------------------------------------------- LLM


class MockLLM(LLMProvider):
    """Deterministic offline LLM. ``complete()`` returns storyboard JSON built from
    the brief found in the conversation — the orchestrator can parse it directly."""

    name = "mock"

    def available(self) -> bool:
        return True

    def complete(self, system: str, messages: list[dict], json_mode: bool = False) -> str:
        brief = ""
        for msg in reversed(messages or []):
            content = str(msg.get("content") or "")
            if content.strip():
                brief = content
                break
        return _mini_storyboard_json(brief)

    def chat_with_tools(self, system, messages, tools_schema, max_steps: int = 8) -> dict:
        raise NotImplementedError("mock LLM has no tool loop; the orchestrator uses mock_director")


def _mini_storyboard_json(brief: str) -> str:
    """Self-contained heuristic planner (kept independent from backend code on purpose)."""
    words = _keywords(brief, 6)
    topic = (words[0].upper() if words else "NOVA")
    name = topic.title() if words else "NOVA"
    target = 30.0
    for token in brief.replace(",", " ").split():
        bare = token.rstrip("s").strip(".!?")
        if bare.isdigit() and 4 <= int(bare) <= 180:
            target = float(int(bare))
            break
    weights = [0.25, 0.30, 0.20, 0.25]
    kinds = ["hook", "reveal", "typography", "outro"]
    headlines = [f"MEET {name.upper()}", f"{topic} REDEFINED", "MADE TO MOVE", f"{name.upper()}. START TONIGHT."]
    narrations = [
        f"This is {name}. A bolder way to experience {topic.lower()}. Built for creators who move fast.",
        "Every frame is crafted with cinematic light, deep color and motion that feels alive.",
        f"{name} keeps your whole story moving at full speed, from first idea to final cut.",
        f"{name} is ready whenever you are. Start creating tonight.",
    ]
    scenes = []
    for i, (kind, share) in enumerate(zip(kinds, weights)):
        dur = round(max(1.0, target * share), 2)
        scenes.append(
            {
                "id": f"scene-{i + 1:02d}",
                "kind": kind,
                "duration_s": dur,
                "headline": headlines[i],
                "body": "",
                "narration": narrations[i],
                "visual_prompt": f"{topic.lower()} hero visual, cinematic lighting, high contrast, 9:16 composition",
                "motion": {"style": ["ken-burns", "zoom", "slide", "reveal"][i % 4], "intensity": 0.6},
                "transition_in": "fade" if i == 0 else ["cut", "fade", "slide"][i % 3],
            }
        )
    total = sum(s["duration_s"] for s in scenes) or 1.0
    scale = target / total
    for s in scenes:
        s["duration_s"] = round(max(1.0, s["duration_s"] * scale), 2)
    storyboard = {
        "schema_version": 1,
        "title": f"{name} — Offline Mock Promo",
        "platform": "instagram",
        "aspect": "9:16",
        "fps": 30,
        "duration_target_s": target,
        "palette": _MOCK_PALETTES["cinematic-dark"],
        "music_mood": "dark-cinematic",
        "scenes": scenes,
    }
    return json.dumps(storyboard)


# --------------------------------------------------------------------------- image


class MockImage(ImageProvider):
    """Pillow frame generator producing labeled key art with real composition."""

    name = "mock"

    def available(self) -> bool:
        return True

    def generate_image(
        self,
        prompt: str,
        out_path: str,
        width: int = 1080,
        height: int = 1920,
        **kwargs,
    ) -> dict:
        from PIL import Image, ImageDraw, ImageFilter

        width, height = int(width), int(height)
        rng = random.Random(_stable_seed(prompt, kwargs.get("headline"), kwargs.get("scene_index")))
        pal = (
            dict(kwargs["palette"])
            if isinstance(kwargs.get("palette"), dict) and kwargs["palette"]
            else self._palette_from(prompt)
        )
        bg = _hex_to_rgb(pal.get("bg", "#0a0a12"))
        primary = _hex_to_rgb(pal.get("primary", "#7c5cff"))
        accent = _hex_to_rgb(pal.get("accent", "#00e5ff"))
        text_col = _hex_to_rgb(pal.get("text", "#f5f5ff"))

        # Vertical gradient bg -> primary with a slight ease.
        base = Image.new("RGB", (width, height), bg)
        draw = ImageDraw.Draw(base)
        for y in range(height):
            t = (y / max(1, height - 1)) ** 1.2
            draw.line([(0, y), (width, y)], fill=_mix(bg, primary, t))
        img = base.convert("RGBA")

        # Accent glow blob (soft light source).
        glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gx = int(width * rng.uniform(-0.15, 0.15))
        gd.ellipse(
            [gx - int(width * 0.45), int(height * 0.52), gx + int(width * 1.45), int(height * 1.30)],
            fill=accent + (64,),
        )
        glow = glow.filter(ImageFilter.GaussianBlur(radius=max(10, min(width, height) // 9)))
        img = Image.alpha_composite(img, glow)

        # Vignette (radial darkening towards the edges).
        grad = Image.radial_gradient("L").resize((width, height))
        dark = Image.new("RGBA", (width, height), (0, 0, 0, 255))
        img = Image.composite(dark, img, grad.point(lambda v: int(v * 0.55)))

        # Film grain: gaussian noise composited at very low alpha.
        noise = Image.effect_noise((width, height), 18)
        grain = noise.convert("RGB").convert("RGBA")
        grain.putalpha(noise.point(lambda _: 10))
        img = Image.alpha_composite(img, grain)

        bold_path = self._first_font(_BOLD_FONT_CANDIDATES)
        reg_path = self._first_font(_REG_FONT_CANDIDATES)

        headline = str(kwargs.get("headline") or self._headline_from(prompt)).strip()
        if headline:
            try:
                img = self._draw_headline(img, headline, text_col, accent, bold_path, width, height)
            except Exception:  # glyph/geometry issue -> retry with the bitmap default font
                img = self._draw_headline(
                    img, headline, text_col, accent, None, width, height, default_font=True
                )

        # Corner scene label.
        scene_index = int(kwargs.get("scene_index") or 1)
        scene_count = int(kwargs.get("scene_count") or 1)
        label_font = self._load(reg_path, max(16, int(width * 0.022)))
        label = f"SCENE {scene_index:02d}/{scene_count:02d}"
        ImageDraw.Draw(img).text(
            (int(width * 0.07), int(height * 0.055)), label, font=label_font, fill=text_col + (210,)
        )

        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        img.convert("RGB").save(out, "PNG")
        return {
            "provider": "mock",
            "path": str(out),
            "width": width,
            "height": height,
            "headline": headline,
            "prompt": prompt,
        }

    # -- internals ---------------------------------------------------------

    def _palette_from(self, prompt: str) -> dict:
        p = prompt.lower()
        if "neon" in p:
            return _MOCK_PALETTES["vibrant-neon"]
        if "corporate" in p or "clean" in p:
            return _MOCK_PALETTES["corporate-clean"]
        if "warm" in p or "documentary" in p:
            return _MOCK_PALETTES["warm-documentary"]
        return _MOCK_PALETTES["cinematic-dark"]

    def _headline_from(self, prompt: str) -> str:
        words = _keywords(prompt, 4)
        return " ".join(w.upper() for w in words[:3]) if words else "CINEFORGE"

    def _first_font(self, candidates) -> str | None:
        for c in candidates:
            if c and os.path.exists(c):
                return c
        return None

    def _load(self, path: str | None, size: int):
        from PIL import ImageFont

        try:
            if path and os.path.exists(path):
                return ImageFont.truetype(path, size)
        except Exception:
            pass
        return ImageFont.load_default()

    def _wrap(self, draw, text: str, font, max_width: int) -> list[str]:
        lines: list[str] = []
        current = ""
        for word in text.split():
            trial = f"{current} {word}".strip()
            try:
                width_ok = draw.textlength(trial, font=font) <= max_width
            except Exception:
                width_ok = len(trial) * 12 <= max_width
            if width_ok or not current:
                current = trial
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines[:4]

    def _draw_headline(self, img, headline, text_col, accent, font_path, width, height, default_font=False):
        from PIL import Image, ImageDraw, ImageFilter, ImageFont

        if default_font:
            font = ImageFont.load_default()
        else:
            font = self._load(font_path, max(44, min(150, int(min(width, height) * 0.105))))
        probe = ImageDraw.Draw(img)
        lines = self._wrap(probe, headline, font, int(width * 0.86))
        font_size = getattr(font, "size", 40)
        line_h = int(max(font_size, 32) * 1.18)
        total_h = line_h * len(lines)
        y = int(height * 0.5 - total_h / 2)
        placed: list[tuple[str, float, int]] = []
        for line in lines:
            try:
                lw = probe.textlength(line, font=font)
            except Exception:
                lw = len(line) * 14
            placed.append((line, (width - lw) / 2, y))
            y += line_h

        shadow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        for line, x, ly in placed:
            sd.text((x + 6, ly + 6), line, font=font, fill=(0, 0, 0, 190))
        img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(8)))

        crisp = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        cd = ImageDraw.Draw(crisp)
        for line, x, ly in placed:
            cd.text((x, ly), line, font=font, fill=text_col + (255,))
        # Thin accent rule under the headline block.
        rule_w = int(width * 0.16)
        rule_y = int(y + 10)
        cd.rectangle(
            [(width - rule_w) // 2, rule_y, (width + rule_w) // 2, rule_y + max(4, height // 320)],
            fill=accent + (255,),
        )
        return Image.alpha_composite(img, crisp)


# --------------------------------------------------------------------------- tts


class MockTTS(TTSProvider):
    """Speech-like narration synthesized with stdlib only (no numpy). Deterministic per text."""

    name = "mock"

    def available(self) -> bool:
        return True

    def synthesize(self, text: str, out_path_wav: str) -> dict:
        words = [w for w in (text or "").split() if w.strip()]
        duration = min(12.0, max(1.5, 0.42 * max(1, len(words))))
        n = int(duration * SR)
        rng = random.Random(_stable_seed("tts", text))
        freq = rng.uniform(165.0, 185.0)
        samples: list[float] = []
        for i in range(n):
            t = i / SR
            if i % 220 == 0:  # slow random walk of the fundamental
                freq = min(210.0, max(150.0, freq + rng.uniform(-9.0, 9.0)))
            syllable = 0.5 - 0.5 * math.cos(2 * math.pi * ((t * 4.0) % 1.0))  # ~4 pulses/s
            cycle = t % 0.8  # breath pause roughly every 0.8 s
            gate = 1.0 if cycle < 0.64 else max(0.0, 1.0 - (cycle - 0.64) / 0.10)
            env = syllable * gate
            vibrato = 1.0 + 0.012 * math.sin(2 * math.pi * 5.0 * t)
            f = freq * vibrato
            sample = (
                0.55 * math.sin(2 * math.pi * f * t)
                + 0.22 * math.sin(2 * math.pi * 2 * f * t)
                + 0.10 * math.sin(2 * math.pi * 3 * f * t)
            )
            fade = 1.0
            if t < 0.08:
                fade = t / 0.08
            remaining = duration - t
            if remaining < 0.10:
                fade = max(0.0, remaining / 0.10)
            samples.append(sample * env * 0.5 * fade)
        real_duration = _write_wav(out_path_wav, samples)
        return {
            "provider": "mock",
            "path": str(out_path_wav),
            "duration_s": round(real_duration, 3),
            "text": text,
            "voice": "mock-hum",
        }


# --------------------------------------------------------------------------- music


_MOOD_BASE_FREQ = {
    "dark-cinematic": 55.0,
    "vibrant-neon": 110.0,
    "corporate-clean": 130.81,
    "warm-documentary": 98.0,
}


class MockMusic(MusicProvider):
    """Layered sine bed (root + fifth + octave + colour partials), mood-seeded, stdlib only."""

    name = "mock"

    def available(self) -> bool:
        return True

    def generate_music(self, mood: str, duration_s: float, out_path_wav: str) -> dict:
        duration = float(min(120.0, max(1.0, duration_s or 30.0)))
        base = _MOOD_BASE_FREQ.get((mood or "").lower(), 65.41)
        rng = random.Random(_stable_seed("music", mood))
        layers = [(0.5, 0.10), (1.0, 0.50), (1.5, 0.28), (2.0, 0.18), (3.0, 0.08)]
        detunes = [1.0 + rng.uniform(-0.004, 0.004) for _ in layers]
        phases = [rng.uniform(0.0, 2 * math.pi) for _ in layers]
        n = int(duration * SR)
        raw: list[float] = []
        peak = 1e-9
        for i in range(n):
            t = i / SR
            tremolo = 0.78 + 0.22 * math.sin(2 * math.pi * 0.25 * t)
            s = 0.0
            for (mult, amp), detune, phase in zip(layers, detunes, phases):
                s += amp * math.sin(2 * math.pi * base * mult * detune * t + phase)
            fade = 1.0
            if t < 0.5:
                fade = t / 0.5
            remaining = duration - t
            if remaining < 2.0:
                fade = min(fade, max(0.0, remaining / 2.0))
            v = s * tremolo * fade
            peak = max(peak, abs(v))
            raw.append(v)
        scale = 0.3 / peak  # keep the bed gentle under narration
        samples = [v * scale for v in raw]
        real_duration = _write_wav(out_path_wav, samples)
        return {
            "provider": "mock",
            "path": str(out_path_wav),
            "duration_s": round(real_duration, 3),
            "mood": mood,
            "base_freq_hz": base,
        }


# --------------------------------------------------------------------------- stt / video


class MockSTT(STTProvider):
    """Local honest stub: reports real audio duration, clearly labeled transcript."""

    name = "mock"

    def available(self) -> bool:
        return True

    def transcribe(self, wav_path: str) -> str:
        duration = 0.0
        try:
            with wave.open(str(wav_path), "rb") as wf:
                duration = wf.getnframes() / float(wf.getframerate() or SR)
        except Exception:
            pass
        return f"[mock transcript] {duration:.1f}s of audio transcribed locally (mock STT tier)."


class MockVideo(VideoProvider):
    """Availability marker for /health. Real video renders via the local
    FFmpeg/Remotion pipeline (``render_slideshow`` / ``build_remotion_project`` tools)."""

    name = "mock"

    def available(self) -> bool:
        return True

    def generate_video(self, prompt: str, out_path: str, **kwargs) -> dict:
        raise ProviderError(
            "mock video tier renders through the local FFmpeg/Remotion pipeline "
            "(tools: render_slideshow / build_remotion_project), not generate_video()"
        )
