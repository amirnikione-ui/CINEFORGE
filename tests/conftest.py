"""Pytest path bootstrap for both test roots (tests/ and backend/tests/)."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
for p in (
    REPO_ROOT / "backend",
    REPO_ROOT / "packages" / "ai-providers",
    REPO_ROOT / "packages" / "video-engine",
):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)
