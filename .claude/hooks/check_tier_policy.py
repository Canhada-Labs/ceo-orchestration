#!/usr/bin/env python3
"""PLAN-043 Phase 4 — STAGED PreToolUse hook for VETO-floor structural defense.

**STAGED LOCATION NOTE**

This file is staged under ``.claude/scripts/tier_policy_cli/`` (renamed from ``tier_policy/`` per PLAN-076 fork (f), S89) (non-canonical
path) because the current Owner sentinel at
``.claude/plans/PLAN-043/architect/round-1/approved.md`` uses a documentation
format (``## Scope`` heading + ``Author:``) rather than the canonical-edit
hook's required format (``Scope:`` block with ``-`` bullets + ``Approved-By:
@handle <sha>`` regex per ``check_canonical_edit.py:138``).

**Phase 5 Owner action required:** either

(a) Reformat ``.claude/plans/PLAN-043/architect/round-1/approved.md`` to the
    ``Scope:`` + ``Approved-By:`` format (replace ``## Scope (canonical ...``
    with ``Scope:`` followed by the bullets unchanged; add
    ``Approved-By: @Canhada-Labs <current-HEAD-commit-sha>`` line), OR

(b) Apply the Phase 5 kernel batch ``/tmp/plan_043_promote_check_hook.py``
    (Owner physical shell + CEO_KERNEL_OVERRIDE) which copies this file to
    ``.claude/hooks/check_tier_policy.py`` + registers it in
    ``.claude/settings.json`` PreToolUse matcher.

Once promoted, the hook blocks any ``Edit``/``Write``/``MultiEdit`` on
``.claude/agents/code-reviewer.md`` or ``.claude/agents/security-engineer.md``
whose diff modifies the ``model:`` field, unless an Owner-signed sentinel
explicitly authorizes that specific change. This is the THIRD layer of
VETO-floor defense per Round 1 closure C-P0-3 (module-load SHA256
assertion + independent literal + structural hook-level block).

**Hook semantics (post-promotion):**

- tool_name ``Edit`` / ``Write`` / ``MultiEdit`` with ``file_path``
  matching ``.claude/agents/{code-reviewer,security-engineer}.md``:
  block unless:
  - An ``.claude/plans/PLAN-*/architect/round-*/approved.md`` sentinel
    contains BOTH the ``Approved-By:`` signature AND the specific
    agent file in a ``Scope:`` block (separate from the PLAN-043
    sentinel — a new per-change sentinel must be issued for each
    VETO-role tier change), AND
  - The sentinel's Scope bullet explicitly names this file.
- Other tools / non-VETO files: allow.
- Fail-open on parse errors per ADR-005 (emit breadcrumb, allow).

stdlib-only (ADR-002). Python >= 3.9.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import List, Optional


VETO_AGENT_FILES = frozenset({
    ".claude/agents/code-reviewer.md",
    ".claude/agents/security-engineer.md",
})

_APPROVED_BY_RE = re.compile(
    r"^\s*Approved-By:\s*@[\w\-]+\s+\S+", flags=re.MULTILINE
)

# Tool surface this hook monitors.
_WATCHED_TOOLS = frozenset({"Edit", "Write", "MultiEdit"})


def _emit_allow() -> str:
    # Allow: emit empty JSON. Top-level {"decision":"allow"} fails Claude
    # Code hook schema (enum is "approve"|"block").
    return json.dumps({}, ensure_ascii=False)


def _emit_block(reason: str) -> str:
    return json.dumps(
        {"decision": "block", "reason": reason}, ensure_ascii=False
    )


def _find_sentinels(repo_root: Path) -> List[Path]:
    base = repo_root / ".claude" / "plans"
    if not base.is_dir():
        return []
    return sorted(base.glob("PLAN-*/architect/round-*/approved.md"))


def _sentinel_grants_veto_edit(
    sentinel_path: Path, target_rel: str
) -> bool:
    """Check whether sentinel grants a VETO-role edit.

    Same ``Approved-By:`` + ``Scope:`` format as
    ``check_canonical_edit.py``. Additionally requires the sentinel
    to explicitly include a ``VETO-CHANGE:`` marker confirming Owner
    intentionally authorizes a VETO-floor tier change (belt-and-
    suspenders against accidental inclusion of VETO file paths in
    routine canonical-edit sentinels).
    """
    try:
        text = sentinel_path.read_text(encoding="utf-8")
    except OSError:
        return False

    if not _APPROVED_BY_RE.search(text):
        return False

    # Require explicit VETO-CHANGE marker.
    if "VETO-CHANGE:" not in text:
        return False

    scope_match = re.search(
        r"^Scope:\s*\n((?:\s*-\s*\S+.*\n?)+)",
        text,
        flags=re.MULTILINE,
    )
    if not scope_match:
        return False

    scope_block = scope_match.group(1)
    for line in scope_block.splitlines():
        m = re.match(r"\s*-\s*(\S+)", line)
        if not m:
            continue
        raw = m.group(1)
        if any(ord(c) < 0x20 for c in raw):
            continue
        normalized = os.path.normpath(raw).replace(os.sep, "/")
        if normalized == target_rel:
            return True
    return False


def decide(
    *,
    tool_name: str,
    file_path: str,
    repo_root: Path,
) -> str:
    """Pure decision function.

    Args:
        tool_name: The tool being invoked (Edit/Write/MultiEdit/...).
        file_path: The target file path (absolute or relative).
        repo_root: Repo root path for sentinel discovery.

    Returns:
        JSON payload for stdout (block or allow).
    """
    if tool_name not in _WATCHED_TOOLS:
        return _emit_allow()
    if not file_path:
        return _emit_allow()
    # Normalize to repo-relative form.
    try:
        p = Path(file_path)
        rel = str(
            p.resolve().relative_to(repo_root.resolve())
        ).replace(os.sep, "/")
    except (ValueError, OSError):
        return _emit_allow()
    if rel not in VETO_AGENT_FILES:
        return _emit_allow()

    # VETO file touched; require sentinel.
    sentinels = _find_sentinels(repo_root)
    for sentinel in sentinels:
        if _sentinel_grants_veto_edit(sentinel, rel):
            return _emit_allow()
    return _emit_block(
        reason=(
            "VETO-FLOOR-BLOCKED: '{f}' is a VETO-class agent (per "
            "ADR-052 + ADR-064 VETO_HARDCODE). Edits to the `model:` "
            "field require an Owner-signed sentinel at "
            ".claude/plans/PLAN-*/architect/round-*/approved.md with "
            "BOTH (a) the file path in the `Scope:` block AND (b) a "
            "`VETO-CHANGE:` marker confirming Owner intent. See "
            "ADR-064 §Decision 2 defense-in-depth."
        ).format(f=rel)
    )


def main() -> int:
    """Hook entry point — reads Claude Code JSON event from stdin."""
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        # Fail-open: corrupt event = allow + breadcrumb.
        sys.stdout.write(_emit_allow())
        return 0
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input") or {}
    file_path = tool_input.get("file_path", "")
    repo_root = Path(
        os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    )
    payload = decide(
        tool_name=tool_name,
        file_path=file_path,
        repo_root=repo_root,
    )
    sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
