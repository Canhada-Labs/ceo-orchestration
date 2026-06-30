"""MCP handler: ``get_skill`` — read a single SKILL.md by (tier, slug).

Per ADR-042 §Auth.2 this is a ``readonly`` handler. Params:

- ``tier``: ``"core" | "frontend" | "domain"``.
- ``slug``: the skill slug, e.g. ``"public-api-design"``.
- ``domain`` (REQUIRED when tier="domain"): ``"fintech"`` etc.

Returns ``{"tier", "slug", "domain?", "description", "content"}``.

## Path-traversal defense (CRITICAL)

Handler readers in MCP server face the same threat surface as any
network-reachable file server. We enforce:

1. ``tier`` MUST be in a small closed enum.
2. ``slug`` and ``domain`` MUST match ``^[a-z][a-z0-9_-]{0,62}$`` —
   no slashes, no dots, no parent traversal.
3. After constructing the target path, we ``Path.resolve()`` both
   the root (``.claude/skills/``) and the target, then verify the
   target is a descendant of the root via ``relative_to``. Any
   failure → ``-32602 skill_not_found``.
4. Symlinks are rejected (``os.path.islink`` check on each component
   up to the target). This is defense-in-depth against a developer
   accidentally symlinking secrets into the skills tree.
5. File size cap 1 MiB — oversized SKILL.md rejects.

Any mismatch returns the JSON-RPC-2.0 error code ``-32602`` with the
generic ``skill_not_found`` reason — no distinguishing between missing
tier, missing slug, traversal attempt, or symlink (no oracle).
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict


_SLUG_RE = re.compile(r"^[a-z][a-z0-9_-]{0,62}$")
_ALLOWED_TIERS = {"core", "frontend", "domain"}
_MAX_FILE_BYTES = 1 * 1024 * 1024  # 1 MiB


def _validate_slug(value: Any) -> bool:
    """Return True iff ``value`` is a safe lowercase slug."""
    if not isinstance(value, str):
        return False
    return bool(_SLUG_RE.match(value))


def _build_target(
    project_dir: Path, tier: str, slug: str, domain: str
) -> Path:
    """Build the absolute target path. Caller enforces validation first."""
    skills_root = project_dir / ".claude" / "skills"
    if tier == "core":
        return skills_root / "core" / slug / "SKILL.md"
    if tier == "frontend":
        return skills_root / "frontend" / slug / "SKILL.md"
    # tier == "domain"
    return skills_root / "domains" / domain / "skills" / slug / "SKILL.md"


def _resolve_safely(root: Path, target: Path) -> bool:
    """Return True iff ``target`` resolves under ``root`` with no symlinks.

    Walks the path components from the target back to the root and
    rejects any symlink on the way. Also verifies
    ``resolved_target.relative_to(resolved_root)`` — no ``..`` escape.
    """
    try:
        resolved_root = root.resolve(strict=True)
    except (OSError, RuntimeError):
        return False
    try:
        resolved_target = target.resolve(strict=True)
    except (OSError, RuntimeError):
        return False
    try:
        resolved_target.relative_to(resolved_root)
    except ValueError:
        return False
    # Reject symlinks anywhere on the path from root to target.
    current = resolved_target
    while True:
        if os.path.islink(str(current)):
            return False
        if current == resolved_root:
            break
        parent = current.parent
        if parent == current:
            # Walked past root without matching — should not happen
            # after relative_to succeeded, but fail closed.
            return False
        current = parent
    return True


def handle(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """MCP handler entry point.

    Returns a JSON-RPC 2.0 ``result`` dict on success, or a
    ``{"__error__": {"code": int, "message": str}}`` sentinel on
    failure. The server wraps the sentinel into a proper JSON-RPC
    error envelope.
    """
    project_dir_raw = context.get("project_dir")
    if project_dir_raw is None:
        return {"__error__": {"code": -32603, "message": "internal_error"}}
    project_dir = Path(project_dir_raw)

    if not isinstance(params, dict):
        return {"__error__": {"code": -32602, "message": "invalid_params"}}

    tier = params.get("tier")
    slug = params.get("slug")
    domain = params.get("domain", "")

    if tier not in _ALLOWED_TIERS:
        return {"__error__": {"code": -32602, "message": "skill_not_found"}}
    if not _validate_slug(slug):
        return {"__error__": {"code": -32602, "message": "skill_not_found"}}
    if tier == "domain":
        if not _validate_slug(domain):
            return {"__error__": {"code": -32602, "message": "skill_not_found"}}
    else:
        # domain ignored for core/frontend; coerce to empty string.
        domain = ""

    assert isinstance(tier, str) and isinstance(slug, str) and isinstance(domain, str)
    target = _build_target(project_dir, tier, slug, domain)
    skills_root = project_dir / ".claude" / "skills"

    if not target.is_file():
        return {"__error__": {"code": -32602, "message": "skill_not_found"}}
    if not _resolve_safely(skills_root, target):
        return {"__error__": {"code": -32602, "message": "skill_not_found"}}

    try:
        size = target.stat().st_size
    except OSError:
        return {"__error__": {"code": -32602, "message": "skill_not_found"}}
    if size > _MAX_FILE_BYTES:
        return {"__error__": {"code": -32603, "message": "skill_too_large"}}

    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"__error__": {"code": -32603, "message": "internal_error"}}

    # Description extraction (shared with list_skills logic, simplified inline
    # to keep handler modules independent).
    description = _extract_description(content)

    result: Dict[str, Any] = {
        "tier": tier,
        "slug": slug,
        "description": description,
        "content": content,
    }
    if tier == "domain":
        result["domain"] = domain
    return result


def _extract_description(text: str) -> str:
    """Minimal frontmatter-description extractor, mirroring list_skills."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    end_idx: int = -1
    for i in range(1, min(len(lines), 200)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx < 0:
        return ""
    body = lines[1:end_idx]
    desc_parts = []
    in_desc = False
    for raw in body:
        if raw.startswith("description:"):
            value = raw[len("description:"):].strip()
            if value.startswith('"') and value.endswith('"') and len(value) >= 2:
                value = value[1:-1]
            desc_parts.append(value)
            in_desc = True
            continue
        if in_desc:
            if raw.startswith(" "):
                desc_parts.append(raw.strip())
                continue
            break
    return " ".join(p for p in desc_parts if p).strip()


__all__ = ["handle"]
