"""CINEFORGE backend configuration (env-driven, ADR-0003/0004)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _ensure_packages_on_path() -> None:
    """Make packages/ai-agent, ai-providers, video-engine importable without pip install.

    Proper installs (pip install -e packages/ai-agent ...) also work; this keeps
    `uvicorn app.main:app` zero-config as promised in the governance docs.
    """
    for name in ("ai-agent", "ai-providers", "video-engine"):
        p = REPO_ROOT / "packages" / name
        if p.is_dir() and str(p) not in sys.path:
            sys.path.insert(0, str(p))


_ensure_packages_on_path()


def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


VERSION = "0.1.0"

# --- storage ----------------------------------------------------------------
STORAGE_ROOT = Path(env("CINEFORGE_STORAGE_ROOT", str(REPO_ROOT / "storage"))).resolve()
MAX_PROJECT_MB = int(env("CINEFORGE_MAX_PROJECT_MB", "512") or "512")

# --- database ---------------------------------------------------------------
DATABASE_URL = env("DATABASE_URL", "sqlite:///./cineforge.db")
# harden against foreign/foreign-format URLs injected by hosting environments
if not DATABASE_URL.split(":", 1)[0] in (
    "sqlite", "postgresql", "postgres", "mysql", "mssql", "oracle",
):
    import warnings

    warnings.warn(
        f"ignoring non-SQL DATABASE_URL ({DATABASE_URL.split(':', 1)[0]}:…) — using SQLite")
    DATABASE_URL = "sqlite:///./cineforge.db"

# --- queue ------------------------------------------------------------------
REDIS_URL = env("REDIS_URL", "")

# --- provider chains (ADR-0004) ---------------------------------------------
LLM_CHAIN = [p for p in env("CINEFORGE_LLM_CHAIN", "zai,openai,anthropic,mock").split(",") if p]
IMAGE_CHAIN = [p for p in env("CINEFORGE_IMAGE_CHAIN", "openai,mock").split(",") if p]
TTS_CHAIN = [p for p in env("CINEFORGE_TTS_CHAIN", "openai,elevenlabs,mock").split(",") if p]
STT_CHAIN = [p for p in env("CINEFORGE_STT_CHAIN", "openai,mock").split(",") if p]
MUSIC_CHAIN = [p for p in env("CINEFORGE_MUSIC_CHAIN", "mock").split(",") if p]
VIDEO_CHAIN = [p for p in env("CINEFORGE_VIDEO_CHAIN", "mock").split(",") if p]

# --- per-vendor settings ----------------------------------------------------
ZAI_API_KEY = env("ZAI_API_KEY")
ZAI_BASE_URL = env("ZAI_BASE_URL", "https://api.z.ai/api/paas/v4")
ZAI_MODEL = env("ZAI_MODEL", "glm-4.6")
OPENAI_API_KEY = env("OPENAI_API_KEY")
OPENAI_BASE_URL = env("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = env("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_IMAGE_MODEL = env("OPENAI_IMAGE_MODEL", "gpt-image-1")
OPENAI_TTS_MODEL = env("OPENAI_TTS_MODEL", "tts-1")
OPENAI_TTS_VOICE = env("OPENAI_TTS_VOICE", "onyx")
OPENAI_STT_MODEL = env("OPENAI_STT_MODEL", "whisper-1")
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = env("ANTHROPIC_MODEL", "claude-3-5-haiku-latest")
ELEVENLABS_API_KEY = env("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = env("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

# --- render -----------------------------------------------------------------
FFMPEG_TIMEOUT_S = int(env("CINEFORGE_FFMPEG_TIMEOUT_S", "600") or "600")
JOB_TIMEOUT_S = int(env("CINEFORGE_JOB_TIMEOUT_S", "900") or "900")


def provider_status() -> dict[str, list[str]]:
    """Capability → ordered chain (mock always last & always available)."""
    return {
        "llm": LLM_CHAIN,
        "image": IMAGE_CHAIN,
        "tts": TTS_CHAIN,
        "stt": STT_CHAIN,
        "music": MUSIC_CHAIN,
        "video": VIDEO_CHAIN,
    }
