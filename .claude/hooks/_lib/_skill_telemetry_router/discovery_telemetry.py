"""Identify a real skill by its canonical SKILL.md location, without I/O writes."""

from __future__ import annotations

from pathlib import Path
import re


_SLUG = re.compile(r"[a-z0-9][a-z0-9-]*\Z")


def resolve_skill_slug_from_path(path: str) -> str:
    """Return a verified skill directory name or ``unknown``.

    Valid layouts mirror the skill inventory: core, frontend and domain skills.
    Symlink aliases resolve to the *target* skill, not their alias names.
    Relative paths are interpreted relative to the current working directory.
    """
    if not isinstance(path, str) or not path.strip() or "\x00" in path:
        return "unknown"

    candidate = Path(path)
    # Do not silently normalize a caller-supplied parent traversal.
    if ".." in candidate.parts:
        return "unknown"
    try:
        target = candidate.resolve(strict=True)
        if target.is_dir():
            target = (target / "SKILL.md").resolve(strict=True)
        if not target.is_file() or target.name != "SKILL.md":
            return "unknown"
    except (OSError, RuntimeError, ValueError):
        return "unknown"

    parts = target.parts
    # Canonical target, not the link, must be below .claude/skills.
    for index in range(len(parts) - 2):
        if parts[index : index + 2] == (".claude", "skills"):
            remainder = parts[index + 2 :]
            if remainder[-1] != "SKILL.md":
                return "unknown"
            directories = remainder[:-1]
            if (len(directories) == 2 and directories[0] in ("core", "frontend")
                    or len(directories) == 3 and directories[0] == "domains"
                    or len(directories) == 4 and directories[0] == "domains"
                    and directories[2] == "skills"):
                if all(_SLUG.fullmatch(part) for part in directories):
                    return directories[-1]
            return "unknown"
    return "unknown"
