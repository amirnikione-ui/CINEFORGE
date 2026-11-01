"""Local-disk storage under STORAGE_ROOT (S3 adapter tracked as CF-062)."""

from __future__ import annotations

import os
import re
import shutil

from .core.config import get_settings

_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")


def sanitize(name: str) -> str:
    return _SAFE.sub("_", name)[:120] or "file"


class Storage:
    def __init__(self, root: str | None = None) -> None:
        self.root = os.path.abspath(root or get_settings().storage_root)

    def project_dir(self, pid: str, subdir: str = "") -> str:
        path = os.path.join(self.root, pid, subdir) if subdir else os.path.join(self.root, pid)
        os.makedirs(path, exist_ok=True)
        return path

    def new_path(self, pid: str, subdir: str, filename: str) -> str:
        return os.path.join(self.project_dir(pid, subdir), sanitize(filename))

    def write(self, pid: str, subdir: str, filename: str, data: bytes) -> str:
        path = self.new_path(pid, subdir, filename)
        with open(path, "wb") as fh:
            fh.write(data)
        return path

    def copy_in(self, pid: str, subdir: str, src: str, filename: str) -> str:
        dst = self.new_path(pid, subdir, filename)
        if os.path.abspath(src) != os.path.abspath(dst):
            shutil.copy2(src, dst)
        return dst

    def abs(self, stored_path: str) -> str:
        return stored_path  # contract stores absolute-ish paths (/data/storage in docker)


storage = Storage()


def content_type_for(kind: str, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    return {
        "mp4": "video/mp4", "png": "image/png", "jpg": "image/jpeg",
        "wav": "audio/wav", "mp3": "audio/mpeg", "json": "application/json",
        "tsx": "text/plain", "ts": "text/plain", "zip": "application/zip",
    }.get(ext, "application/octet-stream") if kind != "storyboard" else "application/json"
