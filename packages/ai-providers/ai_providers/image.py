"""Image providers: OpenAI image generation + offline Pillow art tier."""

from __future__ import annotations

import base64
import hashlib
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .base import Capability, MockProvider, ProviderError, ProviderUnavailable

PLATFORM_SIZES: dict[str, tuple[int, int]] = {
    "instagram": (1080, 1920),
    "tiktok": (1080, 1920),
    "youtube": (1920, 1080),
    "web": (1920, 1080),
}


def size_for_platform(platform: str | None, width: int | None = None, height: int | None = None) -> tuple[int, int]:
    if width and height:
        return width, height
    return PLATFORM_SIZES.get((platform or "web").lower(), (1920, 1080))


@dataclass
class OpenAIImage:
    name: str = "openai"
    model_env: str = "OPENAI_IMAGE_MODEL"
    default_model: str = "gpt-image-1"
    capability: Capability = Capability.IMAGE

    def _key(self) -> str:
        return os.environ.get("OPENAI_API_KEY", "").strip()

    def available(self) -> bool:
        return bool(self._key())

    def is_mock(self) -> bool:
        return False

    def describe(self) -> dict[str, Any]:
        return {"name": self.name, "kind": "openai-images", "model": os.environ.get(self.model_env) or self.default_model}

    def generate(self, prompt: str, *, size: tuple[int, int], out_path: Path) -> dict[str, Any]:
        key = self._key()
        if not key:
            raise ProviderUnavailable("openai image: OPENAI_API_KEY not set")
        model = os.environ.get(self.model_env) or self.default_model
        # gpt-image-1 accepts arbitrary sizes; other models snap to presets.
        import httpx

        resp = httpx.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": model, "prompt": prompt[:4000], "size": _snap_size(size), "n": 1},
            timeout=180.0,
        )
        if resp.status_code in (401, 403):
            raise ProviderUnavailable(f"openai image auth rejected ({resp.status_code})")
        if resp.status_code >= 400:
            raise ProviderError(f"openai image -> {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        try:
            item = data["data"][0]
        except (KeyError, IndexError) as exc:
            raise ProviderError("openai image: unexpected response") from exc
        if item.get("b64_json"):
            out_path.write_bytes(base64.b64decode(item["b64_json"]))
        elif item.get("url"):
            import httpx as _hx

            img = _hx.get(item["url"], timeout=120.0)
            if img.status_code >= 400:
                raise ProviderError(f"openai image download -> {img.status_code}")
            out_path.write_bytes(img.content)
        else:
            raise ProviderError("openai image: neither b64_json nor url present")
        return {"provider": self.name, "model": model, "path": str(out_path)}


def _snap_size(size: tuple[int, int]) -> str:
    width, height = size
    if width == height:
        return "1024x1024"
    return "1024x1536" if height > width else "1536x1024"


@dataclass
class PillowArtImage(MockProvider):
    """Offline concept frames: real, deterministic generative art from the palette.

    Produces layered gradient art with seeded geometry — usable as actual video
    frames (the FFmpeg engine adds typography and motion on top).
    """

    name: str = "mock"
    capability: Capability = Capability.IMAGE

    def available(self) -> bool:
        return True

    def describe(self) -> dict[str, Any]:
        return {"name": self.name, "kind": "pillow-generative"}

    def generate(
        self,
        prompt: str,
        *,
        size: tuple[int, int],
        out_path: Path,
        palette: dict[str, str] | None = None,
        seed_text: str = "",
    ) -> dict[str, Any]:
        from PIL import Image, ImageDraw, ImageFilter

        from .art import hex_to_rgb, lerp_rgb

        width, height = size
        palette = palette or {"bg": "#0a0a12", "primary": "#7c5cff", "accent": "#00e5ff", "text": "#f5f5ff"}
        seed = int(hashlib.sha256(f"{seed_text}|{prompt}".encode()).hexdigest()[:12], 16)
        rng = _DetRandom(seed)

        top = hex_to_rgb(palette.get("bg", "#0a0a12"))
        bottom = hex_to_rgb(palette.get("primary", "#7c5cff"))
        bottom = tuple(int(c * 0.45) for c in bottom)  # keep it dark & cinematic
        accent = hex_to_rgb(palette.get("accent", "#00e5ff"))

        img = Image.new("RGB", (width, height), top)
        # vertical gradient with a slight diagonal bias
        px = img.load()
        for y in range(height):
            t = y / max(1, height - 1)
            row = tuple(int(lerp_rgb(top, bottom, t)[i]) for i in range(3))
            for x in range(0, width, 4):
                for dx in range(4):
                    if x + dx < width:
                        px[x + dx, y] = row

        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        # 3-5 glowing orbs seeded by the prompt
        for _ in range(rng.randint(3, 5)):
            cx, cy = rng.randint(0, width), rng.randint(0, height)
            r = rng.randint(width // 8, width // 3)
            alpha = rng.randint(28, 64)
            color = accent if rng.random() < 0.6 else hex_to_rgb(palette.get("primary", "#7c5cff"))
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color, alpha))
        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=width // 14))
        img = Image.alpha_composite(img.convert("RGBA"), overlay)

        # geometric accents (triangles / rings), deterministic per seed
        geo = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(geo)
        for _ in range(rng.randint(2, 4)):
            cx, cy = rng.randint(0, width), rng.randint(0, height)
            r = rng.randint(width // 16, width // 6)
            if rng.random() < 0.5:
                gdraw.ellipse(
                    [cx - r, cy - r, cx + r, cy + r],
                    outline=(*accent, rng.randint(70, 120)),
                    width=max(2, width // 300),
                )
            else:
                pts = [
                    (cx, cy - r),
                    (cx - r, cy + int(r * 0.9)),
                    (cx + r, cy + int(r * 0.9)),
                ]
                gdraw.polygon(pts, outline=(*accent, rng.randint(60, 110)))
        img = Image.alpha_composite(img, geo)

        # vignette
        vign = Image.new("L", (width, height), 0)
        vdraw = ImageDraw.Draw(vign)
        vdraw.ellipse(
            [-width // 3, -height // 4, width + width // 3, height + height // 4],
            fill=255,
        )
        vign = vign.filter(ImageFilter.GaussianBlur(radius=width // 6))
        black = Image.new("RGBA", (width, height), (0, 0, 0, 255))
        img = Image.composite(img, black, vign)

        # film grain
        grain = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        gpx = grain.load()
        for _ in range((width * height) // 900):
            x, y = rng.randint(0, width - 1), rng.randint(0, height - 1)
            gpx[x, y] = (255, 255, 255, rng.randint(4, 16))
        img = Image.alpha_composite(img.convert("RGBA"), grain)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.convert("RGB").save(out_path, format="PNG")
        return {"provider": self.name, "path": str(out_path), "width": width, "height": height}


class _DetRandom:
    """Small deterministic RNG (no global random state) for reproducible art."""

    def __init__(self, seed: int) -> None:
        self._state = seed or 1

    def _next(self) -> int:
        # xorshift64
        x = self._state
        x ^= (x << 13) & 0xFFFFFFFFFFFFFFFF
        x ^= x >> 7
        x ^= (x << 17) & 0xFFFFFFFFFFFFFFFF
        self._state = x
        return x

    def random(self) -> float:
        return (self._next() >> 11) / float(1 << 53)

    def randint(self, a: int, b: int) -> int:
        return a + int(self.random() * (b - a + 1)) % max(1, (b - a + 1))


def golden_ratio_pos(i: int, span: int) -> float:
    """Deterministic pseudo position in [0, span) for varied-but-stable layouts."""
    frac = (i * 0.618033988749895) % 1.0
    return math.floor(frac * span)
