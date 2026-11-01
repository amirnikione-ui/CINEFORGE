"""Pydantic v2 schemas — the Python mirror of docs/API_CONTRACTS.md."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Platform = Literal["instagram", "youtube", "tiktok", "web"]
AssetKind = Literal["storyboard", "frame", "audio", "video", "analysis", "project"]
JobKind = Literal["render", "generate", "analyze"]
JobStatus = Literal["pending", "running", "done", "failed"]


class _ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    brief: str = Field(min_length=1, max_length=8000)
    style: Optional[str] = "cinematic-dark"
    platform: Platform = "instagram"
    duration_hint_s: float = Field(default=30.0, gt=0, le=600)


class ProjectOut(_ORM):
    id: str
    title: str
    brief: str
    style: str
    platform: str
    duration_hint_s: float
    status: str
    created_at: datetime


class AssetOut(_ORM):
    id: str
    project_id: str
    kind: AssetKind
    filename: str
    path: str
    meta: dict[str, Any] = {}
    created_at: datetime


class MessageOut(_ORM):
    id: str
    project_id: str
    role: str
    content: str
    meta: dict[str, Any] = {}
    created_at: datetime


class JobOut(_ORM):
    id: str
    project_id: str
    kind: JobKind
    status: JobStatus
    progress: float
    result: dict[str, Any] = {}
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


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


# --- Storyboard JSON (schema_version 1) — central artifact -------------------

class SceneMotion(BaseModel):
    style: Literal["ken-burns", "slide", "zoom", "reveal"] = "ken-burns"
    intensity: float = Field(default=0.6, ge=0.0, le=1.0)


class Scene(BaseModel):
    id: str
    kind: Literal["hook", "reveal", "typography", "outro"]
    duration_s: float = Field(gt=0, le=120)
    headline: str = ""
    body: str = ""
    narration: str = ""
    visual_prompt: str = ""
    motion: SceneMotion = SceneMotion()
    transition_in: Literal["fade", "cut", "slide"] = "fade"


class Palette(BaseModel):
    bg: str = "#0a0a12"
    primary: str = "#7c5cff"
    accent: str = "#00e5ff"
    text: str = "#f5f5ff"


class Storyboard(BaseModel):
    schema_version: int = 1
    title: str = "Untitled"
    platform: str = "instagram"
    aspect: str = "9:16"
    fps: int = 30
    duration_target_s: float = 30.0
    palette: Palette = Palette()
    music_mood: str = "dark-cinematic"
    scenes: list[Scene]

    def normalized(self) -> "Storyboard":
        """Scale scene durations so the total matches duration_target_s (±10% rule)."""
        total = sum(s.duration_s for s in self.scenes)
        if self.scenes and total > 0 and abs(total - self.duration_target_s) / self.duration_target_s > 0.10:
            factor = self.duration_target_s / total
            for s in self.scenes:
                s.duration_s = round(s.duration_s * factor, 2)
        return self


class AnalysisReport(BaseModel):
    duration_s: float = 0.0
    fps_estimate: float = 0.0
    cuts: list[float] = []
    scenes: list[dict[str, Any]] = []
    pacing: dict[str, Any] = {}
    loudness: list[dict[str, Any]] = []
    palette: list[str] = []
    notes: list[str] = []


class HealthOut(BaseModel):
    status: str = "ok"
    version: str
    providers: dict[str, list[str]]
    storage_root: str
