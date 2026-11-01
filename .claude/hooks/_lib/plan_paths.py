"""Shared PLAN filename and path matching for lifecycle consumers.

The filename grammar is the authoritative PLAN-SCHEMA.md §1.4 pattern.
Paths are normalized before matching so hooks receive the same result from
relative, absolute, POSIX, and Windows-style tool payloads.
"""

from __future__ import annotations

import re


PLAN_FILENAME_RE = re.compile(
    r"^PLAN-[0-9]{3}(-FOLLOWUP)?-[a-z0-9]+(-[a-z0-9]+)*\.md$"
)

def is_plan_path(file_path: str) -> bool:
    """Return whether ``file_path`` names a schema-valid plan file."""
    if not file_path:
        return False
    parent, _, filename = str(file_path).replace("\\", "/").rpartition("/")
    in_plans = parent == ".claude/plans" or parent.endswith("/.claude/plans")
    return in_plans and PLAN_FILENAME_RE.fullmatch(filename) is not None


def plan_id_from_path(file_path: str) -> str:
    """Return ``PLAN-NNN`` from a schema-valid path, otherwise ``""``."""
    if not file_path:
        return ""
    normalized = str(file_path).replace("\\", "/")
    filename = normalized.rsplit("/", 1)[-1]
    if not PLAN_FILENAME_RE.fullmatch(filename):
        return ""
    return filename[:8]


__all__ = ["PLAN_FILENAME_RE", "is_plan_path", "plan_id_from_path"]
