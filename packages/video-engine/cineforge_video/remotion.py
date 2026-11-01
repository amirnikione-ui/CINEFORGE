"""Remotion integration (ADR-0006 path b): project builder + render runner.

`build_project` copies the bundled remotion-template into the project workspace
and injects the storyboard (public contract: `--props storyboard.json`).
`render_remotion` runs the pinned toolchain (`npx remotion render`) when Node is
available — requires `npm install` in the project (done lazily, timeout-guarded).
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "remotion-template"


def build_project(storyboard: dict[str, Any], dest: Path) -> Path:
    if not TEMPLATE_DIR.is_dir():
        raise RuntimeError(f"remotion template missing: {TEMPLATE_DIR}")
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(TEMPLATE_DIR, dest, ignore=shutil.ignore_patterns(
        "node_modules", ".remotion", "dist", "__pycache__"))
    (dest / "storyboard.json").write_text(
        json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")
    return dest


def _node_available() -> bool:
    return shutil.which("node") is not None and shutil.which("npx") is not None


def render_remotion(project_dir: str | Path, out_path: str | Path,
                    *, timeout_s: int = 1800) -> dict[str, Any]:
    if not _node_available():
        raise RuntimeError("node/npx not available — install Node 20 for the Remotion path")
    project_dir = Path(project_dir)
    if not (project_dir / "node_modules").exists():
        subprocess.run(["npm", "install", "--no-audit", "--no-fund"], cwd=project_dir,
                       capture_output=True, text=True, timeout=1200, check=False)
    cmd = ["npx", "remotion", "render", "src/index.ts", "CinematicPromo",
           str(out_path), "--props", str(project_dir / "storyboard.json")]
    res = subprocess.run(cmd, cwd=project_dir, capture_output=True, text=True,
                         timeout=timeout_s, check=False)
    if res.returncode != 0:
        raise RuntimeError(f"remotion render failed: {(res.stderr or '')[-500:]}")
    return {"output": str(out_path), "engine": "remotion", "composition": "CinematicPromo"}
