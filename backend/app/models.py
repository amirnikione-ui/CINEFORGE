"""ORM models — mirror of docs/API_CONTRACTS.md v0.1 (uuid ids, ISO timestamps)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .core.db import Base


def uid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    brief: Mapped[str | None] = mapped_column(Text, nullable=True)
    style: Mapped[str] = mapped_column(String(48), default="cinematic-dark", nullable=False)
    platform: Mapped[str] = mapped_column(String(24), default="web", nullable=False)
    duration_hint_s: Mapped[float] = mapped_column(Float, default=30.0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    messages: Mapped[list["Message"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    assets: Mapped[list["Asset"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    jobs: Mapped[list["Job"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user|assistant|system
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped[Project] = relationship(back_populates="messages")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)  # storyboard|frame|audio|video|analysis|project
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped[Project] = relationship(back_populates="assets")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)  # render|generate|analyze
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)  # pending|running|done|failed
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped[Project] = relationship(back_populates="jobs")
