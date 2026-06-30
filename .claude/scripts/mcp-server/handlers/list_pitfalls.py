"""MCP handler: ``list_pitfalls`` — enumerate universal + optional domain pitfalls.

Per ADR-042 §Auth.2 this is a ``readonly`` handler. Params:

- ``domain`` (optional): ``"fintech"`` | ``"lgpd-heavy-saas"`` |
  ``"trading-hft"`` | ``"edtech"`` | ``"government"``. Unknown domain
  yields empty list (not an error — the caller may enumerate before
  knowing what's installed).

Returns ``{"pitfalls": [{...}, ...], "total": int}``.

## Source of truth

- Universal: ``.claude/pitfalls-catalog.yaml``.
- Domain:    ``.claude/skills/domains/<domain>/pitfalls.yaml``.

The catalog uses a small subset of YAML. We don't import PyYAML
(stdlib discipline) — the file is hand-authored with a stable schema:

```
pitfalls:
  - id: IPC-001
    rule: "..."
    whenToUse: "..."
    agents: [PerformanceEngineer, RealTimeSystemsEngineer]
```

Our parser looks for the top-level ``pitfalls:`` key, then walks dash
items recognizing ``id:``, ``rule:``, ``whenToUse:``, ``agents:``
fields. Unknown fields are preserved as-is (key → raw value string).

Fail-open: empty list + ``warning`` on parse error; never raises.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional


_DOMAIN_SLUG_RE = re.compile(r"^[a-z][a-z0-9_-]{0,62}$")


def _parse_simple_list(value: str) -> List[str]:
    """Parse ``[a, b, c]`` → ``["a", "b", "c"]``. Tolerant of quotes."""
    v = value.strip()
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        if not inner:
            return []
        parts = [p.strip().strip('"').strip("'") for p in inner.split(",")]
        return [p for p in parts if p]
    # Single bare value
    return [v.strip().strip('"').strip("'")] if v else []


def _unquote(value: str) -> str:
    """Strip paired leading/trailing quote chars and whitespace."""
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
        v = v[1:-1]
    return v


def _parse_pitfalls_yaml(text: str) -> List[Dict[str, Any]]:
    """Very small subset parser tuned to the catalog schema.

    State machine:
    - Skip everything before the ``pitfalls:`` key.
    - On ``  - id: NNN`` start a new entry.
    - On indented ``    key: value`` add field to current entry.
    - On line with no leading whitespace beyond the original indent
      (and not a dash) → end of pitfalls section.
    """
    out: List[Dict[str, Any]] = []
    lines = text.splitlines()
    current: Optional[Dict[str, Any]] = None
    in_section = False
    section_indent: Optional[int] = None

    for raw in lines:
        # Strip trailing whitespace but preserve leading for indent.
        line = raw.rstrip()
        if not line:
            continue
        # Comment lines.
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        indent = len(line) - len(stripped)

        if not in_section:
            if stripped.startswith("pitfalls:"):
                in_section = True
                section_indent = indent
            continue

        # In section — detect end of section.
        if section_indent is not None and indent <= section_indent and not stripped.startswith("-"):
            break

        # Dash-item start.
        if stripped.startswith("- "):
            if current is not None:
                out.append(current)
            current = {}
            remainder = stripped[2:]
            if remainder.startswith("id:"):
                current["id"] = _unquote(remainder[len("id:"):])
            continue

        if current is None:
            continue

        # Key: value line.
        if ":" in stripped:
            key, _, rest = stripped.partition(":")
            key = key.strip()
            rest = rest.strip()
            if key == "agents":
                current[key] = _parse_simple_list(rest)
            else:
                current[key] = _unquote(rest)

    if current is not None:
        out.append(current)
    # Drop entries with no id (malformed)
    return [p for p in out if p.get("id")]


def _load_catalog(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return _parse_pitfalls_yaml(text)


def handle(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """MCP handler entry point.

    Params:
        domain (str, optional): domain slug. Unknown or malformed →
            treated as absent (universal-only listing).

    Returns:
        ``{"pitfalls": [...], "total": int, "domain": str?}``
    """
    project_dir_raw = context.get("project_dir")
    if project_dir_raw is None:
        return {"pitfalls": [], "warning": "project_dir_missing"}
    project_dir = Path(project_dir_raw)

    domain = ""
    if isinstance(params, dict):
        d = params.get("domain")
        if isinstance(d, str) and _DOMAIN_SLUG_RE.match(d):
            domain = d

    claude_dir = project_dir / ".claude"
    try:
        universal = _load_catalog(claude_dir / "pitfalls-catalog.yaml")
        domain_pitfalls: List[Dict[str, Any]] = []
        if domain:
            dpath = claude_dir / "skills" / "domains" / domain / "pitfalls.yaml"
            if dpath.is_file():
                domain_pitfalls = _load_catalog(dpath)
        # Tag each pitfall with its origin so consumers can filter.
        for p in universal:
            p["scope"] = "universal"
        for p in domain_pitfalls:
            p["scope"] = "domain"
            p["domain"] = domain
        combined = universal + domain_pitfalls
        out: Dict[str, Any] = {
            "pitfalls": combined,
            "total": len(combined),
        }
        if domain:
            out["domain"] = domain
        return out
    except Exception as e:  # pragma: no cover - defensive fail-open
        return {
            "pitfalls": [],
            "warning": f"parse_failed:{type(e).__name__}",
        }


__all__ = ["handle"]
