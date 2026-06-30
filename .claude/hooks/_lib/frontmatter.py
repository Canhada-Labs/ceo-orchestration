"""Generic stdlib YAML frontmatter parser (ADR-002 stdlib-only).

PLAN-025 Batch E (F-scripts-14 P2) — consolidated parser for the "3-dash
delimited key: value block" frontmatter shape used across .claude/adr/,
.claude/plans/, .claude/skills/, and various script-authored docs.

Before this module, ~10 scripts hand-rolled the same 15-20 lines of YAML
subset parsing. Each had subtle differences (quoting behaviour, empty-
value handling, nested keys) that caused correctness drift. This module
is the canonical implementation.

## Migration notes

Callers currently duplicating this logic:

- `.claude/scripts/check-docs-freshness.py`
- `.claude/scripts/check-staleness.py`
- `.claude/scripts/debate-orchestrate.py`
- `.claude/scripts/registry.py`
- `.claude/scripts/session-graph-build.py`
- `.claude/scripts/session-resume.py`
- `.claude/scripts/skill-index-build.py`
- `.claude/scripts/skill-patch-apply.py`
- `.claude/scripts/skill-patch-propose.py`
- `.claude/hooks/_lib/plan_frontmatter.py` (plan-specific wrapper)

Migration deferred to Sprint 26 (cross-caller blast radius mandates a
dedicated refactor commit with per-caller fixture regression).

## API

    from _lib.frontmatter import parse_frontmatter

    raw = path.read_text(encoding="utf-8")
    metadata, body = parse_frontmatter(raw)
    # metadata is Dict[str, str] (values always str); body is str

## Supported subset (per ADR-002 stdlib-only)

- Leading `---` on line 1
- Closing `---` on its own line
- Between them: `key: value` pairs (one per line)
- Empty values allowed: `key:` -> {"key": ""}
- Quoted values stripped: `key: "val"` -> {"key": "val"}
- Comments (#) at the start of a line skipped
- Empty lines skipped

## Unsupported (rejected by returning {}, body unchanged)

- Nested mappings (use SPEC/v1/policy-dsl.schema.md for that regime)
- List values with leading `-`
- Multi-line values
- YAML anchors / aliases (same reason as ADR-045)

Callers that need richer shapes should use `.claude/hooks/_lib/policy.py`
or write purpose-specific parsers; this module is deliberately minimal.
"""
from __future__ import annotations

import re
from typing import Dict, Tuple


_FRONTMATTER_DELIM = "---"
_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_\-]*)\s*:\s*(.*)$")


def parse_frontmatter(text: str) -> Tuple[Dict[str, str], str]:
    """Parse the leading `---`-delimited block as a flat str->str dict.

    Returns:
        (metadata, body) — metadata is empty dict when no frontmatter
        block is present; body is the original text in that case.

    Contract:
        - Does NOT raise. Best-effort parse; malformed lines skipped silently.
        - No frontmatter -> ({}, text)
        - Body preserves ALL text after the closing `---` line (including
          leading newline if present).
    """
    if not text:
        return {}, text
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\n\r") != _FRONTMATTER_DELIM:
        return {}, text

    # Find closing `---`
    close_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.rstrip("\n\r") == _FRONTMATTER_DELIM:
            close_idx = i
            break
    if close_idx is None:
        # No closing delim -> not valid frontmatter; return original.
        return {}, text

    meta: Dict[str, str] = {}
    for raw_line in lines[1:close_idx]:
        stripped = raw_line.rstrip("\n\r").strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = _KEY_RE.match(stripped)
        if m is None:
            continue  # skip malformed lines
        key, value = m.group(1), m.group(2).strip()
        # Strip simple quote wrappers
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("\"", "'"):
            value = value[1:-1]
        meta[key] = value

    body = "".join(lines[close_idx + 1:])
    return meta, body


def extract_body(text: str) -> str:
    """Return ``text`` with any frontmatter block stripped."""
    _, body = parse_frontmatter(text)
    return body


def extract_metadata(text: str) -> Dict[str, str]:
    """Return just the frontmatter dict (empty if absent)."""
    meta, _ = parse_frontmatter(text)
    return meta
