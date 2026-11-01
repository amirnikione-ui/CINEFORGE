"""Pydantic v2 API schemas — mirror of docs/API_CONTRACTS.md (and apps/web/src/types/api.ts)."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class _ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------- requests


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    brief: str = ""
    style: str = "cinematic-dark"
    platform: str = "instagram"  # instagram|youtube|tiktok|web
    duration_hint_s: int = Field(default=30, ge=4, le=600)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)


class MediaAnalyzeRequest(BaseModel):
    asset_id: Optional[str] = None
    url: Optional[str] = None  # remote URL analysis ships in M3


# ---------------------------------------------------------------- objects


class ProjectOut(_ORMModel):
    id: str
    title: str
    brief: str
    style: str
    platform: str
    duration_hint_s: int
    status: str
    created_at: str
    updated_at: str


class MessageOut(_ORMModel):
    id: str
    project_id: str
    role: str
    content: str
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class AssetOut(_ORMModel):
    id: str
    project_id: str
    kind: str
    filename: str
    path: str
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class JobOut(_ORMModel):
    id: str
    project_id: str
    kind: str
    status: str
    progress: float
    result: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    created_at: str
    updated_at: str


# ---------------------------------------------------------------- composites


class ProjectDetail(BaseModel):
    project: ProjectOut
    messages: list[MessageOut]
    assets: list[AssetOut]
    jobs: list[JobOut]


class ChatResponse(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut
    assets: list[AssetOut]
    jobs: list[JobOut]


class HealthOut(BaseModel):
    status: str
    version: str
    providers: dict[str, list[str]]
    storage_root: str
