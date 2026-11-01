"""Settings — all secrets via env/.env only (docs/SECURITY.md)."""

from __future__ import annotations

import logging
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("cineforge.config")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "cineforge-api"
    version: str = "0.1.0"

    database_url: str = "sqlite:///./cineforge.db"
    storage_root: str = "./storage"
    cors_origins: str = "http://localhost:3000"

    # LLM — openai-compatible (works for Z.ai GLM, OpenAI, local vLLM…)
    llm_provider: str = "mock"            # mock | zai | openai
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "glm-4-flash"

    font_file: str = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

    def model_post_init(self, __context) -> None:  # noqa: ANN001
        # Some sandboxes export an unrelated DATABASE_URL (e.g. file:...).
        # Never let that break the zero-config dev experience (FORGE, CF-010).
        url = (self.database_url or "").strip()
        if not url.startswith(("sqlite", "postgresql", "postgres", "mysql")):
            logger.warning("DATABASE_URL=%r is not a SQLAlchemy URL; falling back to SQLite", url[:60])
            self.database_url = "sqlite:///./cineforge.db"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key and self.llm_base_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
