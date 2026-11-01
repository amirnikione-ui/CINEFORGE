"""Z.ai provider — OpenAI-compatible chat (GLM models) with the same tool-call shape."""
from __future__ import annotations

import os

from .base import ProviderError
from .openai_provider import OpenAIProvider


class ZAIProvider(OpenAIProvider):
    """GLM via Z.ai's OpenAI-compatible endpoint. LLM capability only."""

    name = "zai"

    def __init__(self) -> None:
        self.base_url = os.environ.get("ZAI_BASE_URL", "https://api.z.ai/api/paas/v4").rstrip("/")
        self.model = os.environ.get("ZAI_MODEL", "glm-4.6")
        self.image_model = os.environ.get("ZAI_IMAGE_MODEL", "")

    def available(self) -> bool:
        return bool(os.environ.get("ZAI_API_KEY"))

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {os.environ['ZAI_API_KEY']}",
            "Content-Type": "application/json",
        }

    # Z.ai serves chat only in this integration — fail honestly on other capabilities.
    def generate_image(self, prompt, out_path, width=1080, height=1920, **kwargs) -> dict:
        raise ProviderError("zai provider does not implement the image capability")

    def synthesize(self, text, out_path_wav) -> dict:
        raise ProviderError("zai provider does not implement the tts capability")

    def transcribe(self, wav_path) -> str:
        raise ProviderError("zai provider does not implement the stt capability")
