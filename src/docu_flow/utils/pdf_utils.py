"""Small helpers for PDF handling."""

from __future__ import annotations

import hashlib
from pathlib import Path


def pdf_sha256(pdf_path: Path) -> str:
    """Return hex SHA-256 of the file — used as a stable protocol ID."""
    h = hashlib.sha256()
    with pdf_path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_filename(name: str) -> str:
    """Strip dangerous characters from an upload filename."""
    return "".join(c for c in name if c.isalnum() or c in "._- ").strip()
