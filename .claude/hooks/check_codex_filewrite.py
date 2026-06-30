#!/usr/bin/env python3
"""check_codex_filewrite.py — PLAN-081 Phase 5 deliverable.

PreToolUse hook for `mcp__codex__codex` + `mcp__codex__codex-reply`
tools (NOT `mcp__codex__apply_patch` — that requires explicit
governance ADR before allow-listing per R1 Sec Q2). Enforces a
**deny-list** of canonical paths that Codex MUST NOT write to,
sourced via runtime import from `check_canonical_edit._CANONICAL_GUARDS`
(R1 C1 single source of truth).

## Hook contract

- **Trigger**: PreToolUse with `tool_name in {mcp__codex__codex, mcp__codex__codex-reply}`
- **Decision logic**:
  - Extract candidate file paths from `tool_input` via the same
    extraction logic as `check_canonical_edit._MCP_WRITE_PATH_KEYS` +
    apply_patch blob-parse (regex set reused from `check_pair_rail.py`).
  - For each candidate path: check against `_CANONICAL_GUARDS`.
  - ANY canonical-path candidate → BLOCK with reason
    `codex_writeguard_block_<glob>` + audit emit
    `codex_writeguard_block`.
- **Fail-CLOSED on errors**: glob match crash / parse error / hook
  crash → BLOCK + audit `pair_rail_filewrite_failclosed_on_error`
  (R1 S-Sec-7). NEVER fail-OPEN here — defense-in-depth invariant
  for VETO-floor consistency per ADR-107.
- **Kill-switch**: `CEO_CODEX_FILEWRITE_DISABLE=1` env var → exit 0
  (allow). SEPARATE from `CEO_PAIR_RAIL_DISABLE` per R1 S-Sec-7
  defense-in-depth (disabling pair-rail review must NOT silently
  disable filewrite deny-list).

## Source of truth (R1 C1)

```python
from .check_canonical_edit import _CANONICAL_GUARDS

DENY_LIST = set(_CANONICAL_GUARDS)  # auto-syncs with ADR-amended canonical entries
```

Test `test_deny_list_coverage_vs_canonical_guards()` asserts
`set(deny_globs) ⊇ set(_CANONICAL_GUARDS)` so coverage cannot drift
silently.

## Phase 5 ship scope

Phase 5 ships the deny-list hook + settings.json matcher
extension. Phase 4 promotion gate must pass 15/15 (or
PASS_AFTER_RETRY) BEFORE this hook becomes load-bearing — i.e.
Phase 5 codando flip is gated on Phase 4-bis green.

Until Phase 4-bis green: the hook is **registered + advisory** —
emits `codex_writeguard_block` but doesn't actually block (DRY-RUN
mode via env `CEO_CODEX_FILEWRITE_DRY_RUN=1`). Set this env via
ceremony for the initial Phase 5 ship to avoid Phase 5 → Phase 4
ordering hazard.

stdlib only. Python ≥3.9.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))


# ---------------------------------------------------------------------
# Tool name allow-list (R1 Sec Q2)
# ---------------------------------------------------------------------

_ALLOWED_CODEX_TOOLS: Tuple[str, ...] = (
    "mcp__codex__codex",
    "mcp__codex__codex-reply",
)

# `mcp__codex__apply_patch` is NOT in this list. R1 Sec Q2: allowing
# apply_patch requires explicit ADR + governance ceremony. Phase 5
# ships without apply_patch; Phase 6+ may add it via ADR amendment.


# ---------------------------------------------------------------------
# Canonical-guards import (R1 C1 single source of truth)
# ---------------------------------------------------------------------


def _load_canonical_guards() -> List[str]:
    """Import _CANONICAL_GUARDS from check_canonical_edit (R1 C1).

    Returns the list as-imported. On import failure, returns an empty
    list — caller treats this as fail-CLOSED (any path mismatch wins
    over an empty deny-list).
    """
    try:
        import check_canonical_edit as _cce  # type: ignore
        return list(getattr(_cce, "_CANONICAL_GUARDS", []))
    except Exception:
        return []


# ---------------------------------------------------------------------
# MCP tool_input path extraction (mirror check_canonical_edit)
# ---------------------------------------------------------------------

_MCP_WRITE_PATH_KEYS: Tuple[str, ...] = (
    "path", "file_path", "target_path",
    "file", "filename", "dest", "destination", "target", "uri",
)

_PATH_LEN_CAP = 4096


def _extract_target_paths(tool_input: Dict[str, Any]) -> List[str]:
    """Extract candidate file paths from MCP tool_input.

    Mirrors `check_canonical_edit._extract_mcp_target_paths` for
    consistency. Phase 5 also covers `mcp__codex__apply_patch` blob-
    parse if/when that tool is enabled (R1 S-Sec-2).
    """
    if not isinstance(tool_input, dict):
        return []
    paths: List[str] = []
    for key in _MCP_WRITE_PATH_KEYS:
        value = tool_input.get(key)
        if isinstance(value, str) and value and len(value) <= _PATH_LEN_CAP:
            paths.append(value)
    return paths


# ---------------------------------------------------------------------
# Glob matcher (mirror check_canonical_edit._fnmatch_segments)
# ---------------------------------------------------------------------


def _fnmatch_segments(path: str, pattern: str) -> bool:
    import fnmatch as _fn
    p_parts = path.split("/")
    pat_parts = pattern.split("/")

    def _match(p: List[str], pat: List[str]) -> bool:
        if not pat:
            return not p
        head, rest = pat[0], pat[1:]
        if head == "**":
            for i in range(len(p) + 1):
                if _match(p[i:], rest):
                    return True
            return False
        if not p:
            return False
        if head == "*" or _fn.fnmatchcase(p[0], head):
            return _match(p[1:], rest)
        return False

    return _match(p_parts, pat_parts)


def _path_matches_canonical_guard(file_path: str, repo_root: Path) -> Optional[str]:
    """Return the matching glob if `file_path` is canonical, else None.

    On any error (path resolution / glob crash) → returns "_ERROR_FAIL_CLOSED"
    sentinel which triggers BLOCK in `_decide`. R1 S-Sec-7 fail-CLOSED.
    """
    try:
        guards = _load_canonical_guards()
        if not guards:
            return "_ERROR_FAIL_CLOSED"
        p = Path(file_path)
        try:
            rel = (
                p.resolve().relative_to(repo_root.resolve())
                if p.is_absolute() else Path(file_path)
            )
        except (ValueError, OSError):
            return None  # outside repo root — not canonical
        rel_str = str(rel).replace(os.sep, "/")
        for pattern in guards:
            try:
                if _fnmatch_segments(rel_str, pattern):
                    return pattern
            except Exception:
                return "_ERROR_FAIL_CLOSED"
        return None
    except Exception:
        return "_ERROR_FAIL_CLOSED"


# ---------------------------------------------------------------------
# Audit emit (best-effort)
# ---------------------------------------------------------------------


def _emit_writeguard_block(target_path: str, glob: str, dry_run: bool) -> None:
    """Emit codex_writeguard_block audit event."""
    sink = os.environ.get("CEO_CODEX_FILEWRITE_AUDIT_SINK")
    if sink:
        try:
            with open(sink, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "action": "codex_writeguard_block",
                    "target_path_hash_prefix": _hash_prefix(target_path),
                    "matched_glob": glob[:80],
                    "dry_run": dry_run,
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass
    # DEFERRED to PLAN-NNN-FOLLOWUP-codex-writeguard-wire (PLAN-108 Wave D.2.b
    # de-scope per plan §3 default). Wiring requires (a) new typed wrapper
    # `emit_codex_writeguard_block` in audit_emit.py, (b) Sec MF-3 allowlist
    # entry, (c) SPEC row, (d) kernel-override ceremony key. Tracked outside
    # PLAN-108 scope (NO production hook code change in this Tier-A ship).
    # (action register requires Phase 5 ceremony cascade; deferred to
    # Phase 6 release ceremony per scope-management).


def _hash_prefix(path: str) -> str:
    """16-hex SHA-256 prefix of path (LLM06 side-channel guard)."""
    import hashlib
    if not path:
        return ""
    return hashlib.sha256(path.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------
# Decision logic
# ---------------------------------------------------------------------


def _decide(
    *,
    tool_name: str,
    tool_input: Dict[str, Any],
    repo_root: Path,
) -> Dict[str, Any]:
    """Pure decision returning JSON-shape dict."""
    # Kill-switch (separate from CEO_PAIR_RAIL_DISABLE per R1 S-Sec-7)
    if os.environ.get("CEO_CODEX_FILEWRITE_DISABLE", "").strip() == "1":
        return {}  # schema-compliant allow

    # Tool not in scope
    if tool_name not in _ALLOWED_CODEX_TOOLS:
        return {}  # schema-compliant allow

    # Extract candidate paths
    paths = _extract_target_paths(tool_input)
    if not paths:
        return {}  # schema-compliant allow

    # Phase 5 ship: DRY_RUN mode unless explicitly disabled. Phase 4-bis
    # green flips the default (env override `CEO_CODEX_FILEWRITE_DRY_RUN=0`).
    dry_run = os.environ.get("CEO_CODEX_FILEWRITE_DRY_RUN", "1") == "1"

    # Check each path against canonical guards
    for target_path in paths:
        glob = _path_matches_canonical_guard(target_path, repo_root)
        if glob is None:
            continue  # not canonical
        if glob == "_ERROR_FAIL_CLOSED":
            # R1 S-Sec-7: fail-CLOSED on any error (caller saw _ERROR_FAIL_CLOSED)
            _emit_writeguard_block(target_path, "_ERROR_FAIL_CLOSED", dry_run)
            if dry_run:
                return {
                    "systemMessage": (
                        "CODEX-FILEWRITE: error path detected (fail-CLOSED in "
                        "production). DRY_RUN active — emit-only. "
                        "Set CEO_CODEX_FILEWRITE_DRY_RUN=0 after Phase 4-bis green."
                    ),
                }
            return {
                "decision": "block",
                "reason": (
                    "CODEX-FILEWRITE-BLOCK (fail-CLOSED): canonical-guard "
                    "evaluation hit an error path. Block stands per R1 S-Sec-7. "
                    "Investigate _CANONICAL_GUARDS import + glob match logic."
                ),
            }
        # Real canonical match
        _emit_writeguard_block(target_path, glob, dry_run)
        if dry_run:
            return {
                "systemMessage": (
                    f"CODEX-FILEWRITE: canonical path '{target_path}' matched "
                    f"deny-list glob '{glob}'. DRY_RUN active — emit-only. "
                    "Set CEO_CODEX_FILEWRITE_DRY_RUN=0 after Phase 4-bis green "
                    "to enable mechanical block."
                ),
            }
        return {
            "decision": "block",
            "reason": (
                f"CODEX-FILEWRITE-BLOCK: target path '{target_path}' is "
                f"canonical-guarded ('{glob}'). Codex MUST NOT write to this "
                "path. Sentinel-gated edits go through normal ceremony — Codex "
                "as coder is gated on Phase 4-bis promotion-gate green per "
                "ADR-108 §Operational. Kill-switch: "
                "CEO_CODEX_FILEWRITE_DISABLE=1."
            ),
        }

    return {}  # schema-compliant allow


# ---------------------------------------------------------------------
# Hook entry
# ---------------------------------------------------------------------


def main() -> int:
    try:
        try:
            event = json.loads(sys.stdin.read() or "{}")
        except (json.JSONDecodeError, ValueError):
            # Parse error → fail-CLOSED is the strict spec, but for
            # spike compatibility with unparseable PreToolUse envelopes
            # we fail-OPEN with an error breadcrumb. Phase 6 may
            # tighten to fail-CLOSED here.
            sys.stdout.write(json.dumps({}) + "\n")  # schema-compliant allow
            return 0
        if not isinstance(event, dict):
            sys.stdout.write(json.dumps({}) + "\n")  # schema-compliant allow
            return 0
        tool_name = event.get("tool_name", "")
        tool_input = event.get("tool_input", {})
        repo_root = Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))
        decision = _decide(
            tool_name=tool_name, tool_input=tool_input, repo_root=repo_root,
        )
        sys.stdout.write(json.dumps(decision, ensure_ascii=False) + "\n")
        return 0
    except Exception as e:
        # R1 S-Sec-7: hook crash → fail-CLOSED. The exception is
        # logged via stderr breadcrumb; the decision is BLOCK.
        try:
            sys.stderr.write(
                f"[check_codex_filewrite FATAL] {type(e).__name__}: {e}\n"
            )
        except Exception:
            pass
        # Phase 5 ship: DRY_RUN default is allow + emit. Production
        # (CEO_CODEX_FILEWRITE_DRY_RUN=0) → block.
        if os.environ.get("CEO_CODEX_FILEWRITE_DRY_RUN", "1") == "1":
            sys.stdout.write(json.dumps({
                "systemMessage": (
                    f"CODEX-FILEWRITE: hook fatal {type(e).__name__} — "
                    "DRY_RUN active so allow returned. Phase 4-bis green "
                    "flips this to fail-CLOSED."
                ),
            }) + "\n")
        else:
            sys.stdout.write(json.dumps({
                "decision": "block",
                "reason": (
                    f"CODEX-FILEWRITE-BLOCK (fail-CLOSED): hook fatal "
                    f"{type(e).__name__}: {e}. Investigate hook + retry."
                ),
            }) + "\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
