"""Image providers: OpenAI Images (real) + Pillow procedural frames (mock tier, ADR-0005)."""
from __future__ import annotations

import io
import random
from typing import Any

from backend.app import config

from .base import Provider, ProviderError, _post_binary


class ImageOpenAI(Provider):
    name = "openai"
    capability = "image"

    def available(self) -> bool:
        return bool(config.OPENAI_API_KEY)

    async def run(self, *, prompt: str, size: str = "1024x1792", **_: Any) -> dict[str, Any]:
        try:
            data = await _post_json(
                f"{config.OPENAI_BASE_URL.rstrip('/')}/images/generations",
                headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
                json_body={"model": config.OPENAI_IMAGE_MODEL, "prompt": prompt,
                           "size": size, "n": 1},
                timeout=180.0,
            )
            url = data["data"][0].get("url")
            b64 = data["data"][0].get("b64_json")
            if b64:
                import base64

                return {"image_bytes": base64.b64decode(b64), "ext": "png"}
            if url:
                async with __import__("httpx").AsyncClient(timeout=120.0) as client:
                    r = await client.get(url)
                    r.raise_for_status()
                    return {"image_bytes": r.content, "ext": "png"}
            raise ProviderError("openai image: no url/b64 in response")
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"openai image: {exc}") from exc


class ImageMock(Provider):
    """Procedural cinematic frames with Pillow — real PNG artifacts, zero keys.

    Style: vertical/radial palette gradient + vignette + seeded grain + soft glow orb.
    """

    name = "mock"
    capability = "image"

    def available(self) -> bool:
        return True

    async def run(self, *, prompt: str, width: int = 1080, height: int = 1920,
                  palette: dict[str, str] | None = None, seed: int = 0, **_: Any) -> dict[str, Any]:
        try:
            from PIL import Image, ImageDraw, ImageFilter

            pal = palette or {"bg": "#0a0a12", "primary": "#7c5cff", "accent": "#00e5ff"}
            rng = random.Random(seed or abs(hash(prompt)) % (2**32))

            img = Image.new("RGB", (width, height), pal.get("bg", "#0a0a12"))
            draw = ImageDraw.Draw(img)

            # vertical gradient bg -> primary tint
            top = _hex(pal.get("bg", "#0a0a12"))
            bot = _blend(top, _hex(pal.get("primary", "#7c5cff")), 0.35)
            for y in range(height):
                t = y / max(1, height - 1)
                draw.line([(0, y), (width, y)], fill=_lerp(top, bot, t))

            # glow orbs (composition anchors)
            glow = Image.new("RGB", (width, height), (0, 0, 0))
            gdraw = ImageDraw.Draw(glow)
            for i in range(3):
                cx = rng.randint(int(width * 0.15), int(width * 0.85))
                cy = rng.randint(int(height * 0.15), int(height * 0.85))
                r = rng.randint(width // 8, width // 4)
                color = _hex(pal.get("accent", "#00e5ff")) if i == 0 else _hex(pal.get("primary", "#7c5cff"))
                gdraw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
            glow = glow.filter(ImageFilter.GaussianBlur(radius=width // 12))
            img = Image.blend(img, Image.blend(img, glow, 0.45), 0.6)

            # vignette
            mask = Image.new("L", (width, height), 0)
            mdraw = ImageDraw.Draw(mask)
            mdraw.ellipse([-width // 3, -height // 4, width + width // 3,
                           height + height // 4], fill=255)
            mask = mask.filter(ImageFilter.GaussianBlur(width // 8))
            dark = Image.new("RGB", (width, height), (2, 2, 6))
            img = Image.composite(img, dark, mask)

            # grain
            noise = Image.effect_noise((width, height), 18).convert("L")
            img = Image.blend(img, Image.merge("RGB", (noise, noise, noise)), 0.05)

            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return {"image_bytes": buf.getvalue(), "ext": "png", "provider": "mock",
                    "prompt": prompt, "seed": seed}
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"image mock: {exc}") from exc


# --- palette helpers ---------------------------------------------------------

def _hex(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]


def _blend(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return _lerp(a, b, t)
