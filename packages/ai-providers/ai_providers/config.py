"""Provider chain configuration (env-driven, see .env.example / ADR-0004)."""
from __future__ import annotations

import os

DEFAULT_CHAINS: dict[str, str] = {
    "llm": "zai,openai,anthropic,mock",
    "image": "openai,mock",
    "tts": "openai,mock",
    "music": "mock",
    "stt": "openai,mock",
    "video": "mock",
}


def get_chains() -> dict[str, list[str]]:
    """Resolve capability -> ordered provider names from CINEFORGE_<CAP>_CHAIN env vars."""
    chains: dict[str, list[str]] = {}
    for capability, default in DEFAULT_CHAINS.items():
        raw = os.environ.get(f"CINEFORGE_{capability.upper()}_CHAIN", default)
        names = [n.strip().lower() for n in raw.split(",") if n.strip()]
        chains[capability] = names or [d.strip() for d in default.split(",")]
    return chains
