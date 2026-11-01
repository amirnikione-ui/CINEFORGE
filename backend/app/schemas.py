"""Pydantic schemas — exact shapes of docs/API_CONTRACTS.md v0.1."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    brief: str | None = None
    style: str | None = None
    platform: str | None = None
    duration_hint_s: float | None = Field(default=None, gt=0, le=600)


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    brief: str | None
    style: str
    platform: str
    status: str
    created_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    role: str
    content: str
    meta: dict[str, Any]
    created_at: datetime


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    kind: str
    filename: str
    path: str
    meta: dict[str, Any]
    created_at: datetime


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    kind: str
    status: str
    progress: float
    result: dict[str, Any] | None
    error: str | None


class ProjectDetail(BaseModel):
    project: ProjectOut
    messages: list[MessageOut]
    assets: list[AssetOut]
    jobs: list[JobOut]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)


class ChatResponse(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut
    assets: list[AssetOut]
    jobs: list[JobOut]


class MediaAnalyzeRequest(BaseModel):
    asset_id: str | None = None
    url: str | None = None


class HealthOut(BaseModel):
    status: str
    version: str
    providers: dict[str, list[str]]
    storage_root: str
