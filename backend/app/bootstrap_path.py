"""Path bootstrap for the CINEFORGE monorepo.

The repo contains hyphenated package directories (``packages/ai-providers``,
``packages/video-engine``, ``packages/ai-agent``) whose importable inner
packages are ``ai_providers``, ``video_engine`` and ``ai_agent``. This module
resolves the repository root and inserts every required directory on
``sys.path`` so entrypoints (``app.main``, ``workers/*``, ``tests/conftest.py``,
``scripts/demo_e2e.py``) can simply ``import`` them.

Every entrypoint must import this module FIRST, before touching
``ai_providers`` / ``video_engine`` / ``ai_agent``.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Marker that unambiguously identifies the repository root.
_REPO_MARKER = Path("packages") / "ai-providers" / "ai_providers" / "__init__.py"


def find_repo_root(start: Path | None = None) -> Path:
    """Walk upwards from *start* (default: this file) until the repo root is found."""
    p = Path(start if start is not None else __file__).resolve()
    for candidate in (p, *p.parents):
        if (candidate / _REPO_MARKER).exists() and (candidate / "backend" / "app").is_dir():
            return candidate
    # Fallback to the structural convention: backend/app/bootstrap_path.py -> parents[2]
    return Path(__file__).resolve().parents[2]


REPO_ROOT: Path = find_repo_root()

_EXTRA_PATHS: tuple[Path, ...] = (
    REPO_ROOT,
    REPO_ROOT / "packages" / "ai-providers",
    REPO_ROOT / "packages" / "video-engine",
    REPO_ROOT / "packages" / "ai-agent",
    REPO_ROOT / "backend",
)

_bootstrapped = False


def bootstrap() -> Path:
    """Insert the repo root and the inner-package roots on ``sys.path`` (idempotent)."""
    global _bootstrapped
    if not _bootstrapped:
        for path in _EXTRA_PATHS:
            if path.is_dir() and str(path) not in sys.path:
                sys.path.append(str(path))
        _bootstrapped = True
    return REPO_ROOT


# Import side effect: importing this module is enough to bootstrap.
bootstrap()
