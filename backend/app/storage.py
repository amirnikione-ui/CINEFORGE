"""Local filesystem storage for project workspaces.

Layout: ``{storage_root}/projects/{project_id}/{frames,audio,video,storyboards,projects}/``
(S3 adapter planned for M5 — this module is the single place that knows the layout).
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from app.config import get_settings

SUBDIRS = ("frames", "audio", "video", "storyboards", "projects")


def workspace(project_id: str) -> dict[str, str]:
    """Return (and create) the standard sub-directories for a project workspace."""
    root = Path(get_settings().storage_root).expanduser() / "projects" / project_id
    dirs = {"root": str(root)}
    root.mkdir(parents=True, exist_ok=True)
    for name in SUBDIRS:
        path = root / name
        path.mkdir(parents=True, exist_ok=True)
        dirs[name] = str(path)
    return dirs


def safe_join(base: str | Path, *parts: str | Path) -> str:
    """Join *parts* under *base*, refusing any path that escapes the base directory."""
    base_path = Path(base).resolve()
    target = base_path.joinpath(*(str(p) for p in parts)).resolve()
    if target != base_path and base_path not in target.parents:
        raise ValueError(f"path traversal blocked: {parts!r} escapes {base_path}")
    return str(target)


def save_upload(data: bytes, project_id: str, subdir: str = "frames", filename: str = "upload.bin") -> str:
    """Persist an uploaded payload inside the project workspace; returns the absolute path."""
    ws = workspace(project_id)
    directory = ws.get(subdir) or ws["root"]
    clean_name = Path(filename).name or "upload.bin"
    out_path = safe_join(directory, clean_name)
    Path(out_path).write_bytes(data)
    return out_path


def purge_project(project_id: str) -> bool:
    """Best-effort recursive delete of a project's files. Returns True if something was removed."""
    root = Path(get_settings().storage_root).expanduser() / "projects" / project_id
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
        return True
    return False


def file_size(path: str | Path) -> int:
    """Size in bytes, 0 when missing/unreadable."""
    try:
        return os.path.getsize(path)
    except OSError:
        return 0
