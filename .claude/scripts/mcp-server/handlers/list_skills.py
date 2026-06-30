"""MCP handler: ``list_skills`` — enumerate the 48 skills.

Per ADR-042 §Auth.2 this is a ``readonly`` handler. No params. Returns
``{"skills": [{"tier": str, "slug": str, "description": str}, ...]}``.

## Source of truth

Walks ``.claude/skills/<tier>/<slug>/SKILL.md`` where ``tier`` is one
of ``core`` / ``frontend`` / ``domain`` (domain skills live under
``domains/<domain>/skills/<slug>/``; the tier reported is ``"domain"``
with a ``domain`` field added).

Description is the first non-blank paragraph of the frontmatter
``description`` field (YAML-ish parse; we don't import yaml). If no
description is available, we return an empty string — never raise.

## Cache

Module-level cache with a 60s TTL per ADR-042 (docstring target).
Tests reset via :func:`_reset_cache`. The cache scope is the
``project_dir`` — different project roots get different cache entries
so a test fixture root does not poison production.

Fail-open: any walk/parse exception degrades to an empty list and
records a structured error in the return payload
(``{"skills": [], "warning": "..."}``) — the handler never raises.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# Cache: (project_dir_str) -> (expires_at, skills_list)
_CACHE: Dict[str, Tuple[float, List[Dict[str, str]]]] = {}
_CACHE_LOCK = threading.Lock()
_CACHE_TTL_S = 60.0


def _reset_cache() -> None:
    """Test helper — drop the module cache."""
    with _CACHE_LOCK:
        _CACHE.clear()


def _parse_frontmatter_description(skill_md: Path) -> str:
    """Extract the ``description`` field from SKILL.md frontmatter.

    Lightweight YAML-ish parser: looks for the first ``---`` fence,
    scans lines until the next ``---`` for a ``description:`` key
    (possibly continued across indented wrap lines). Returns empty
    string on any parse failure.
    """
    try:
        text = skill_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    # Find the closing fence.
    end_idx: Optional[int] = None
    for i in range(1, min(len(lines), 200)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return ""
    body_lines = lines[1:end_idx]
    # Look for the description key + any continuation (wrapped YAML).
    desc_parts: List[str] = []
    in_desc = False
    for raw in body_lines:
        stripped = raw.rstrip()
        if stripped.startswith("description:"):
            value = stripped[len("description:"):].strip()
            # Strip leading/trailing quotes if single-line quoted.
            if value.startswith('"') and value.endswith('"') and len(value) >= 2:
                value = value[1:-1]
            desc_parts.append(value)
            in_desc = True
            continue
        if in_desc:
            # Continuation: indented (starts with space) and no ``key:``.
            if raw.startswith(" ") and ":" not in raw.split("  ", 1)[0]:
                desc_parts.append(stripped.strip())
                continue
            if raw.startswith(" ") and not raw.lstrip().split(" ", 1)[0].endswith(":"):
                desc_parts.append(stripped.strip())
                continue
            # Next top-level key terminates description.
            break
    description = " ".join(d for d in desc_parts if d).strip()
    # Collapse whitespace.
    return " ".join(description.split())


def _walk_skills(project_dir: Path) -> List[Dict[str, str]]:
    """Walk the skill tree once, returning the flat list.

    Structure:
    - ``.claude/skills/core/<slug>/SKILL.md`` → tier=core
    - ``.claude/skills/frontend/<slug>/SKILL.md`` → tier=frontend
    - ``.claude/skills/domains/<domain>/skills/<slug>/SKILL.md`` → tier=domain, domain=<domain>
    """
    out: List[Dict[str, str]] = []
    skills_root = project_dir / ".claude" / "skills"
    if not skills_root.is_dir():
        return out

    # Core + frontend: flat layout.
    for tier in ("core", "frontend"):
        tier_dir = skills_root / tier
        if not tier_dir.is_dir():
            continue
        for skill_dir in sorted(tier_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.is_file():
                continue
            entry: Dict[str, str] = {
                "tier": tier,
                "slug": skill_dir.name,
                "description": _parse_frontmatter_description(skill_md),
            }
            out.append(entry)

    # Domains: nested layout.
    domains_dir = skills_root / "domains"
    if domains_dir.is_dir():
        for domain_dir in sorted(domains_dir.iterdir()):
            if not domain_dir.is_dir():
                continue
            inner = domain_dir / "skills"
            if not inner.is_dir():
                continue
            for skill_dir in sorted(inner.iterdir()):
                if not skill_dir.is_dir():
                    continue
                skill_md = skill_dir / "SKILL.md"
                if not skill_md.is_file():
                    continue
                entry = {
                    "tier": "domain",
                    "domain": domain_dir.name,
                    "slug": skill_dir.name,
                    "description": _parse_frontmatter_description(skill_md),
                }
                out.append(entry)

    return out


def _cached_skills(project_dir: Path, *, now: Optional[float] = None) -> List[Dict[str, str]]:
    """Return cached skills, walking if stale."""
    key = str(project_dir.resolve())
    now_ts = float(now) if now is not None else time.monotonic()
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if entry is not None and entry[0] > now_ts:
            # Return a shallow copy so callers can't mutate the cache.
            return [dict(s) for s in entry[1]]
    # Walk outside the lock (I/O can be slow).
    fresh = _walk_skills(project_dir)
    with _CACHE_LOCK:
        _CACHE[key] = (now_ts + _CACHE_TTL_S, fresh)
    return [dict(s) for s in fresh]


def handle(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """MCP handler entry point.

    Args:
        params: JSON-RPC 2.0 params dict. Ignored (handler takes no args).
        context: runtime context with ``project_dir`` (pathlib.Path) key.

    Returns:
        ``{"skills": [...]}`` dict suitable as a JSON-RPC 2.0 ``result``.
        Fail-open: returns an empty list with a ``warning`` field on any
        walk error.
    """
    project_dir_raw = context.get("project_dir")
    if project_dir_raw is None:
        return {"skills": [], "warning": "project_dir_missing"}
    project_dir = Path(project_dir_raw)
    try:
        skills = _cached_skills(project_dir)
    except Exception as e:  # pragma: no cover - defensive fail-open
        return {"skills": [], "warning": f"walk_failed:{type(e).__name__}"}
    return {"skills": skills, "total": len(skills)}


__all__ = ["handle"]
