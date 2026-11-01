"""Application settings (pydantic-settings, 12-factor via environment)."""
from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_KNOWN_DB_SCHEMES = ("sqlite", "postgresql", "postgres", "mysql")


class Settings(BaseSettings):
    """Runtime settings. All values can be overridden via environment variables."""

    database_url: str = Field(
        "sqlite:///./cineforge.db",
        validation_alias=AliasChoices("DATABASE_URL"),
    )
    storage_root: str = Field(
        "./storage",
        validation_alias=AliasChoices("CINEFORGE_STORAGE_ROOT", "STORAGE_ROOT"),
    )
    max_project_mb: int = Field(
        512,
        validation_alias=AliasChoices("CINEFORGE_MAX_PROJECT_MB", "MAX_PROJECT_MB"),
    )
    version: str = Field("0.1.0", validation_alias=AliasChoices("CINEFORGE_VERSION", "VERSION"))
    cors_origins: str = Field(
        "http://localhost:3000",
        validation_alias=AliasChoices("CORS_ORIGINS", "CINEFORGE_CORS_ORIGINS"),
    )

    @field_validator("database_url", mode="after")
    @classmethod
    def _guard_foreign_database_url(cls, value: str) -> str:
        """Hostile/host environments may export unrelated DATABASE_URL values —
        fall back to the local default unless the scheme is one we support."""
        if value and value.split(":", 1)[0].lower() in _KNOWN_DB_SCHEMES:
            return value
        return "sqlite:///./cineforge.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor."""
    return Settings()
