"""MCP handler: ``list_agents`` — enumerate backend + frontend archetypes.

Per ADR-042 §Auth.2 this is a ``readonly`` handler. Returns:

    {
      "archetypes": [
        {"tier": "backend" | "frontend" | "staff",
         "name": str,
         "skill_primary": str,
         "skill_secondary": str | ""},
        ...
      ]
    }

## Source of truth

``.claude/team.md`` for backend + staff archetypes; ``.claude/frontend-team.md``
for frontend archetypes. Also sweeps
``.claude/skills/domains/*/team-personas.md`` and
``.claude/skills/domains/*/frontend-team-personas.md`` when present
(domain-specific personas).

Parser is intentionally tolerant: the archetype tables are markdown
tables with known column headers. We extract bold-wrapped role names
and their ``skill_primary`` / ``skill_secondary`` cells. Non-table
content is skipped.

Fail-open: returns an empty list + ``warning`` field on parse error.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


_BOLD_ROLE_RE = re.compile(r"^\*\*(?P<name>[^*]+)\*\*$")
_BACKTICK_SKILL_RE = re.compile(r"^`(?P<slug>[a-z][a-z0-9_-]{0,62})`$")


def _parse_md_table(
    lines: List[str], header_predicate
) -> List[List[str]]:
    """Extract the first markdown table whose header matches ``header_predicate``.

    Returns a list of row-cell-lists (header and divider excluded).
    ``header_predicate`` receives a lowercased, stripped header string
    and returns True on match.
    """
    rows: List[List[str]] = []
    in_table = False
    seen_divider = False
    for line in lines:
        s = line.rstrip()
        if not in_table:
            if s.startswith("|") and header_predicate(s.lower()):
                in_table = True
                seen_divider = False
            continue
        if not seen_divider:
            if s.strip().startswith("|") and "---" in s:
                seen_divider = True
            continue
        if not s.startswith("|"):
            break  # end of table
        cells = [c.strip() for c in s.strip().strip("|").split("|")]
        rows.append(cells)
    return rows


def _normalize_skill(cell: str) -> str:
    """Strip backticks / whitespace from a skill cell; return '' if none."""
    if not cell:
        return ""
    stripped = cell.strip()
    if stripped in ("—", "-", "–"):
        return ""
    m = _BACKTICK_SKILL_RE.match(stripped)
    if m:
        return m.group("slug")
    # Fallback: if the cell is just a slug-ish word, pass through.
    if re.match(r"^[a-z][a-z0-9_-]{0,62}$", stripped):
        return stripped
    return ""


def _parse_role_name(cell: str) -> str:
    """Extract the displayed role name from a table cell.

    Accepts ``**Name**``, plain text, and ``Name (qualifier)`` forms.
    """
    if not cell:
        return ""
    s = cell.strip()
    m = _BOLD_ROLE_RE.match(s)
    if m:
        return m.group("name").strip()
    # Strip bold markers anywhere.
    s = re.sub(r"\*\*", "", s)
    # Strip trailing parentheticals like " (optional, per domain)".
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s)
    return s.strip()


def _extract_from_team_md(path: Path, default_tier: str) -> List[Dict[str, str]]:
    """Extract archetypes from a team.md-style file."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    lines = text.splitlines()
    out: List[Dict[str, str]] = []
    seen: set = set()

    # ICs table: `| Archetype | Reports to | Focus | Primary skill | Secondary |`
    ic_rows = _parse_md_table(
        lines, lambda h: "archetype" in h and "primary skill" in h
    )
    for row in ic_rows:
        if len(row) < 4:
            continue
        name = _parse_role_name(row[0])
        primary = _normalize_skill(row[3])
        secondary = _normalize_skill(row[4]) if len(row) > 4 else ""
        if not name:
            continue
        key = (default_tier, name.lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "tier": default_tier,
                "name": name,
                "skill_primary": primary,
                "skill_secondary": secondary,
            }
        )

    # VPs table: `| Role | Reports to | Area | Primary skill |`
    vp_rows = _parse_md_table(
        lines, lambda h: "role" in h and "primary skill" in h and "area" in h
    )
    for row in vp_rows:
        if len(row) < 4:
            continue
        name = _parse_role_name(row[0])
        primary = _normalize_skill(row[3])
        if not name:
            continue
        key = (default_tier, name.lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "tier": default_tier,
                "name": name,
                "skill_primary": primary,
                "skill_secondary": "",
            }
        )

    # Staff table: `| Role | Reports to | Authority | Primary skill |`
    staff_rows = _parse_md_table(
        lines, lambda h: "role" in h and "authority" in h
    )
    for row in staff_rows:
        if len(row) < 4:
            continue
        name = _parse_role_name(row[0])
        primary = _normalize_skill(row[3])
        if not name:
            continue
        key = ("staff", name.lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "tier": "staff",
                "name": name,
                "skill_primary": primary,
                "skill_secondary": "",
            }
        )

    return out


def handle(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """MCP handler entry point.

    Returns ``{"archetypes": [...]}`` dict. Fail-open: returns empty
    list + ``warning`` on parse error.
    """
    project_dir_raw = context.get("project_dir")
    if project_dir_raw is None:
        return {"archetypes": [], "warning": "project_dir_missing"}
    project_dir = Path(project_dir_raw)

    claude_dir = project_dir / ".claude"
    try:
        out: List[Dict[str, str]] = []
        backend = claude_dir / "team.md"
        if backend.is_file():
            out.extend(_extract_from_team_md(backend, "backend"))
        frontend = claude_dir / "frontend-team.md"
        if frontend.is_file():
            out.extend(_extract_from_team_md(frontend, "frontend"))
        # Domain personas — additive.
        domains_dir = claude_dir / "skills" / "domains"
        if domains_dir.is_dir():
            for domain_dir in sorted(domains_dir.iterdir()):
                if not domain_dir.is_dir():
                    continue
                dp = domain_dir / "team-personas.md"
                if dp.is_file():
                    for ent in _extract_from_team_md(dp, "backend"):
                        ent["domain"] = domain_dir.name
                        out.append(ent)
                fp = domain_dir / "frontend-team-personas.md"
                if fp.is_file():
                    for ent in _extract_from_team_md(fp, "frontend"):
                        ent["domain"] = domain_dir.name
                        out.append(ent)
        return {"archetypes": out, "total": len(out)}
    except Exception as e:  # pragma: no cover - defensive fail-open
        return {
            "archetypes": [],
            "warning": f"parse_failed:{type(e).__name__}",
        }


__all__ = ["handle"]
