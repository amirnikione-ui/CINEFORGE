"""Repo-level sanity: coordination files + contract docs stay consistent."""

from __future__ import annotations

import json
import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def test_registry_files_are_valid_json():
    reg_dir = os.path.join(REPO_ROOT, "coordination", "registry")
    if not os.path.isdir(reg_dir):
        pytest.skip("no registry dir")
    for name in sorted(os.listdir(reg_dir)):
        if name.endswith(".json"):
            with open(os.path.join(reg_dir, name), encoding="utf-8") as fh:
                data = json.load(fh)
            assert data["id"], name
            assert data["codename"], name
            assert data["status"] in ("ACTIVE", "JOINING", "INACTIVE")


def test_roster_table_has_registry_rows():
    agents_md = open(os.path.join(REPO_ROOT, "coordination", "AGENTS.md"), encoding="utf-8").read()
    reg_dir = os.path.join(REPO_ROOT, "coordination", "registry")
    for name in sorted(os.listdir(reg_dir)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(reg_dir, name), encoding="utf-8") as fh:
            agent = json.load(fh)
        assert agent["id"] in agents_md, f"{agent['id']} missing from AGENTS.md roster"


def test_no_secrets_committed():
    """Cheap guard: no GitHub PAT-looking strings anywhere in tracked files."""
    pattern = re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")
    offenders = []
    for base, _dirs, files in os.walk(REPO_ROOT):
        if any(part in base for part in (".git", ".venv", "node_modules", "__pycache__")):
            continue
        for fname in files:
            path = os.path.join(base, fname)
            if os.path.splitext(fname)[1] not in (".md", ".py", ".yml", ".yaml", ".json", ".sh", ".ts", ".toml", ".example", ""):
                continue
            try:
                content = open(path, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            if pattern.search(content):
                offenders.append(os.path.relpath(path, REPO_ROOT))
    assert offenders == [], f"potential tokens in: {offenders}"
