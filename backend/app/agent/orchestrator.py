"""Director orchestrator: turns a chat message into a produced film.

Two execution tiers (ADR-0004/0005):
- LLM tool-loop: when a non-mock LLM provider is available, the model plans and
  calls tools itself (max ``max_steps`` iterations).
- Offline deterministic director: when no key is configured, ``mock_director``
  builds/normalizes the storyboard and the standard tool pipeline runs in order.

The assistant message always reports the provider tier honestly.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from ai_agent import TOOLS_JSON
from ai_providers import get_registry

from app import storage
from app.agent import mock_director
from app.agent.prompts import DIRECTOR_SYSTEM
from app.agent.tools import ToolContext, ToolResult, execute_tool
from app.models import Asset, Job, Message, Project, utc_now_iso

log = logging.getLogger("cineforge.director")

MAX_LLM_STEPS = 8
HISTORY_LIMIT = 10


@dataclass
class _RunState:
    plan: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    assets: list[Asset] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    llm_provider: str | None = None


class Director:
    """Handles one chat turn for a project."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------ entry

    def handle_message(self, project: Project, content: str) -> tuple[Message, list[Asset], list[Job]]:
        """Process a user message; returns (assistant_message, new_assets, new_jobs)."""
        started_at = utc_now_iso()
        ws = storage.workspace(project.id)
        ctx = ToolContext(db=self.db, project=project, workspace=ws, registry=get_registry())

        user_msg = Message(project_id=project.id, role="user", content=content, meta={})
        self.db.add(user_msg)
        project.status = "generating"
        self.db.commit()

        state = _RunState()
        revision = self._is_revision(project)
        try:
            if self._try_llm_path(ctx, content, state):
                project.status = "ready"
            else:
                self._mock_path(ctx, project, content, revision, state)
                project.status = "ready"
        except Exception as exc:  # noqa: BLE001 - the user gets an honest failure
            log.exception("director run failed for project %s", project.id)
            project.status = "failed"
            state.notes.append(f"pipeline error: {exc}")
            assistant = Message(
                project_id=project.id,
                role="assistant",
                content=(
                    f"⚠️ I hit a failure while producing this film: {exc}\n\n"
                    "Nothing fake was returned — the pipeline stopped at the error. "
                    "You can retry by sending the brief again, or ask me to adjust the plan."
                ),
                meta={
                    "plan": state.plan,
                    "tools_used": state.tools_used,
                    "llm_provider": state.llm_provider or "mock",
                    "notes": state.notes,
                    "revision": revision,
                    "error": str(exc)[:500],
                },
            )
            self.db.add(assistant)
            self.db.commit()
            return assistant, state.assets, self._jobs_since(project, started_at)

        assistant = Message(
            project_id=project.id,
            role="assistant",
            content=self._summarize(project, state),
            meta={
                "plan": state.plan,
                "tools_used": state.tools_used,
                "llm_provider": state.llm_provider or "mock",
                "notes": state.notes,
                "revision": revision,
            },
        )
        self.db.add(assistant)
        self.db.commit()
        self.db.refresh(assistant)
        return assistant, state.assets, self._jobs_since(project, started_at)

    # --------------------------------------------------------------- helpers

    def _is_revision(self, project: Project) -> bool:
        prior_user = (
            self.db.query(Message)
            .filter(Message.project_id == project.id, Message.role == "user")
            .count()
        )
        has_storyboard = (
            self.db.query(Asset)
            .filter(Asset.project_id == project.id, Asset.kind == "storyboard")
            .count()
            > 0
        )
        return prior_user > 0 and has_storyboard

    def _latest_storyboard(self, ctx: ToolContext) -> dict | None:
        asset = (
            ctx.db.query(Asset)
            .filter(Asset.project_id == ctx.project.id, Asset.kind == "storyboard")
            .order_by(Asset.created_at.desc(), Asset.id.desc())
            .first()
        )
        if asset is None:
            return None
        try:
            return json.loads(Path(asset.path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _jobs_since(self, project: Project, started_at: str) -> list[Job]:
        return (
            self.db.query(Job)
            .filter(Job.project_id == project.id, Job.created_at >= started_at)
            .order_by(Job.created_at.asc())
            .all()
        )

    # ------------------------------------------------------------- LLM path

    def _try_llm_path(self, ctx: ToolContext, content: str, state: _RunState) -> bool:
        """Run the model-driven tool loop. Returns True when it produced the film."""
        llm = ctx.registry.first_available("llm")
        if llm is None or llm.name == "mock":
            return False
        try:
            history = (
                self.db.query(Message)
                .filter(Message.project_id == ctx.project.id)
                .order_by(Message.created_at.asc())
                .all()
            )[-HISTORY_LIMIT:]
            messages: list[dict[str, Any]] = [
                {"role": m.role, "content": m.content} for m in history if m.role in ("user", "assistant")
            ]
            if not messages or messages[-1]["content"] != content:
                messages.append({"role": "user", "content": content})

            state.llm_provider = llm.name
            state.plan.append(f"LLM tool-loop with provider '{llm.name}' (max {MAX_LLM_STEPS} steps)")

            for step in range(MAX_LLM_STEPS):
                response = llm.chat_with_tools(DIRECTOR_SYSTEM, messages, TOOLS_JSON, max_steps=MAX_LLM_STEPS)
                tool_calls = response.get("tool_calls") or []
                if not tool_calls:
                    final_text = (response.get("content") or "").strip()
                    if final_text:
                        state.notes.append(f"director's final note: {final_text[:400]}")
                    break
                for call in tool_calls:
                    name = call.get("name") or ""
                    args = call.get("arguments") or {}
                    state.tools_used.append(name)
                    try:
                        result: ToolResult = execute_tool(name, args, ctx)
                        state.assets.extend(result.assets)
                        payload = {"ok": True, "summary": result.summary, "data_keys": list(result.data)}
                    except Exception as exc:  # noqa: BLE001 - tool errors go back to the model
                        payload = {"ok": False, "error": str(exc)[:400]}
                        state.notes.append(f"tool {name} failed: {exc}")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call.get("id"),
                        "name": name,
                        "content": json.dumps(payload)[:2000],
                    })
            return True
        except Exception as exc:  # noqa: BLE001 - fall through to the offline director
            state.notes.append(
                f"LLM tier '{llm.name}' failed ({exc}) — falling back to the offline director"
            )
            return False

    # ------------------------------------------------------------ mock path

    def _mock_path(
        self, ctx: ToolContext, project: Project, content: str, revision: bool, state: _RunState
    ) -> None:
        state.llm_provider = "mock"
        if revision:
            current = self._latest_storyboard(ctx)
            if current is not None:
                storyboard = mock_director.normalize_storyboard(
                    mock_director.apply_revision(current, content),
                    style=project.style,
                    platform=project.platform,
                )
                state.plan.append("Revise existing storyboard from your feedback (offline director)")
            else:
                storyboard = mock_director.build_storyboard(
                    content, style=project.style, platform=project.platform,
                    duration_hint_s=project.duration_hint_s,
                )
                state.plan.append("Plan a new storyboard from your brief (offline director)")
        else:
            brief = content or project.brief
            storyboard = mock_director.build_storyboard(
                brief, style=project.style, platform=project.platform,
                duration_hint_s=project.duration_hint_s,
            )
            state.plan.append("Plan a new storyboard from your brief (offline director)")

        state.plan += [
            "Generate concept frames per scene",
            "Synthesize narration",
            "Generate music bed",
            "Render the cut with the local FFmpeg pipeline",
            "Scaffold the editable Remotion project",
        ]

        pipeline: list[tuple[str, dict]] = [
            ("write_storyboard", {"brief": content or project.brief, "prepared": storyboard}),
            ("generate_concept_frames", {"storyboard": storyboard}),
            ("generate_narration", {"storyboard": storyboard}),
            (
                "generate_music",
                {
                    "mood": storyboard.get("music_mood") or "dark-cinematic",
                    "duration_s": storyboard.get("duration_target_s") or 30,
                },
            ),
            ("render_slideshow", {"storyboard": storyboard}),
            ("build_remotion_project", {"storyboard": storyboard}),
        ]
        for name, args in pipeline:
            result = execute_tool(name, args, ctx)
            state.tools_used.append(name)
            state.assets.extend(result.assets)
            state.plan.append(result.summary)

    # -------------------------------------------------------------- summary

    def _summarize(self, project: Project, state: _RunState) -> str:
        video = next((a for a in reversed(state.assets) if a.kind == "video"), None)
        sb_asset = next((a for a in reversed(state.assets) if a.kind == "storyboard"), None)
        project_asset = next((a for a in reversed(state.assets) if a.kind == "project"), None)

        lines: list[str] = []
        header = f"🎬 {project.title}"
        if sb_asset is not None:
            meta = sb_asset.meta or {}
            header += (
                f" — {meta.get('scenes_count', '?')} scenes, "
                f"{meta.get('duration_target_s', '?')}s target"
            )
        lines.append(header)

        if video is not None:
            meta = video.meta or {}
            size_mb = (meta.get("size_bytes") or 0) / (1024 * 1024)
            lines.append(
                f"Final cut rendered: {video.filename} "
                f"({meta.get('duration_s', 0):.1f}s, {meta.get('width')}×{meta.get('height')}, "
                f"{size_mb:.1f} MB) — provider tier: {meta.get('provider', 'unknown')}"
            )
        if project_asset is not None:
            lines.append(
                f"Editable project: {project_asset.filename} "
                f"({(project_asset.meta or {}).get('files_count', '?')} files) — open it in the "
                "Remotion studio to fine-tune the motion by code."
            )

        tier = state.llm_provider or "mock"
        if tier == "mock":
            lines.append(
                "Running on the offline mock tier (no LLM/image API keys configured) — every "
                "artifact above is real, produced locally with Pillow + FFmpeg. Add provider "
                "keys in .env to upgrade quality; the pipeline stays identical."
            )
        if state.notes:
            lines.append("Notes: " + " · ".join(state.notes[:3]))

        lines.append(
            "Next steps you can ask for: \"make it punchier and shorter\", "
            "\"warmer palette\", \"slower pacing\", or \"analyze the video structure\"."
        )
        return "\n".join(lines)
