"""README diff helpers — compare generated content against an existing file."""

from __future__ import annotations

import difflib
from pathlib import Path


def _split_lines(text: str) -> list[str]:
    return text.splitlines(keepends=True) if text else []


def render_diff(
    existing: str,
    generated: str,
    existing_label: str = "README.md (existing)",
    generated_label: str = "README.md (generated)",
) -> str:
    """Return a unified diff between existing and generated README content.

    Returns an empty string when both inputs are identical.
    """
    if existing == generated:
        return ""
    diff = difflib.unified_diff(
        _split_lines(existing),
        _split_lines(generated),
        fromfile=existing_label,
        tofile=generated_label,
        n=3,
    )
    return "".join(diff)


def read_existing(path: str | Path) -> str:
    """Read an existing README, returning '' if missing."""
    p = Path(path)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8", errors="ignore")


def is_in_sync(existing: str, generated: str) -> bool:
    """Whether existing matches the generated content exactly."""
    return existing == generated
