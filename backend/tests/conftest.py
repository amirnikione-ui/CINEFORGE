"""Shared fixtures — isolated DB + storage per test run."""

from __future__ import annotations

import os
import sys
import tempfile

# Make `app` importable when pytest runs from repo root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_backend.db")
os.environ.setdefault("STORAGE_ROOT", tempfile.mkdtemp(prefix="cineforge-backend-test-"))
os.environ.setdefault("FONT_FILE", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
os.environ.setdefault("LLM_PROVIDER", "mock")
