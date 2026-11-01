"""Local-filesystem storage under CINEFORGE_STORAGE_ROOT (ADR-0003; S3 adapter = CF-062).

Layout: {root}/{project_id}/{storyboards|frames|audio|video|projects|analysis}/{filename}
Asset.path is stored relative to the root; every read is traversal-guarded.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from .config import STORAGE_ROOT

_SUBDIRS = {"storyboard": "storyboards", "frame": "frames", "audio": "audio",
            "video": "video", "analysis": "analysis", "project": "projects"}

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_filename(name: str) -> str:
    cleaned = _SAFE_NAME.sub("_", Path(name).name).strip("._")
    return cleaned[:150] or "file"


def project_dir(project_id: str) -> Path:
    p = STORAGE_ROOT / project_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def new_file_path(project_id: str, kind: str, filename: str) -> Path:
    sub = _SUBDIRS.get(kind)
    if sub is None:
        raise ValueError(f"unsupported asset kind: {kind}")
    d = project_dir(project_id) / sub
    d.mkdir(parents=True, exist_ok=True)
    return d / _safe_filename(filename)


def rel_to_root(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(STORAGE_ROOT.resolve()))
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError("path escapes storage root") from exc


def resolve_rel(rel_path: str) -> Path:
    """Resolve a stored relative path, refusing traversal outside the root."""
    root = STORAGE_ROOT.resolve()
    target = (root / rel_path).resolve()
    if root != target and root not in target.parents:
        raise ValueError("path escapes storage root")
    return target


def save_bytes(project_id: str, kind: str, filename: str, data: bytes) -> Path:
    dst = new_file_path(project_id, kind, filename)
    dst.write_bytes(data)
    return dst


def copy_tree(src: Path, project_id: str, kind: str, dirname: str) -> Path:
    dst = new_file_path(project_id, kind, dirname)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return dst


def url_for_file(asset_path_rel: str) -> str:
    from urllib.parse import quote

    return f"/api/assets/file?path={quote(asset_path_rel)}"


def purge_project(project_id: str) -> None:
    p = STORAGE_ROOT / project_id
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)
