#!/usr/bin/env python3
"""PostToolUse Bash canonical-edit forensic audit (PLAN-085 Wave E.4).

Advisory PostToolUse hook (NEVER blocks). Emits
``canonical_edit_completed`` breadcrumb events when a Bash command's
write-shape operators reference a canonical governance path.

Composition with E.3 (PreToolUse): E.3 BLOCKS the write at intent time;
E.4 records the forensic trail at completion time for any write that
slipped through (e.g. via a Bash subcommand the E.3 heuristic missed).

v1 implementation — no `git status -s` subprocess; pure command-string
heuristic. Latency: p99 < 1ms by construction (regex scan only).

Discipline: stdlib-only, Python >= 3.9, fail-OPEN per CLAUDE.md §5.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import List, Optional

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _lib import audit_emit as _audit_emit  # type: ignore
except Exception:  # pragma: no cover
    _audit_emit = None  # type: ignore

try:
    from _lib.adapters import claude as _claude_adapter
    from _lib import contract as _contract
except Exception:  # pragma: no cover
    _claude_adapter = None  # type: ignore
    _contract = None  # type: ignore


# Write-shape patterns. v1 lighter than E.3 to keep p99 < 1ms.
_WRITE_PATTERNS = (
    re.compile(r"(?:^|\s)>\s*([^\s|;&<>]+)"),
    re.compile(r"(?:^|\s)>>\s*([^\s|;&<>]+)"),
    re.compile(r"(?:^|\s)tee\s+(?:-a\s+)?([^\s|;&<>]+)"),
    re.compile(r"(?:^|\s)sed\s+-i\b.*?\s([^\s|;&<>]+)\s*$"),
)


def _scan_command_targets(command: str) -> List[str]:
    """Extract write-shape target paths from a Bash command string."""
    targets: List[str] = []
    for pat in _WRITE_PATTERNS:
        for m in pat.finditer(command or ""):
            target = m.group(1).strip("'\"")
            if target:
                targets.append(target)
    return targets


def _is_canonical(path: str, repo_root: Path) -> bool:
    """Cross-reference against check_canonical_edit._CANONICAL_GUARDS."""
    try:
        from check_canonical_edit import _is_canonical as _is_can
        return _is_can(path, repo_root)
    except Exception:  # pragma: no cover
        return False


def _emit_canonical_edit_completed(path: str, sentinel_hint: str) -> None:
    """Best-effort emit of canonical_edit_completed breadcrumb."""
    if _audit_emit is None:
        return
    try:
        emit = getattr(_audit_emit, "emit_generic", None)
        if emit is None:
            return
        # Use generic emit since this is a new action; the dispatch gate
        # will breadcrumb if action not yet in _KNOWN_ACTIONS.
        emit(
            "canonical_edit_completed",
            path=path[:200],
            sentinel_hint=sentinel_hint,
        )
    except Exception:
        pass


def _emit_bash_canonical_bypass(target: str, command_prefix: str) -> None:
    """Emit bash_canonical_bypass_invoked when Bash writes to canonical path.

    PLAN-113 WIRE-AUDIT: fires from the PostToolUse forensic hook when
    a canonical-path write completes and the command started with the
    owner-bypass prefix. Sec MF-3: token_hash_prefix is 8-hex of
    sha256(cmd_prefix[:32]); target_path_hash is the first 12 hex chars of
    sha256(normalized_target) — no raw filesystem path is persisted (P1 fix).
    """
    if _audit_emit is None:
        return
    try:
        import hashlib as _hl
        token_hash_prefix = _hl.sha256(
            command_prefix[:32].encode("utf-8", errors="replace")
        ).hexdigest()[:8]
        # Sec MF-3 — hash the target path; never write raw path to audit log.
        normalized = target.strip().lower()
        target_path_hash = _hl.sha256(
            normalized.encode("utf-8", errors="replace")
        ).hexdigest()[:12]
        emit_fn = getattr(_audit_emit, "emit_bash_canonical_bypass_invoked", None)
        if emit_fn is not None:
            emit_fn(
                token_hash_prefix=token_hash_prefix,
                target_path_hash=target_path_hash,
                ticket_expires_in_s=0,
            )
    except Exception:  # pragma: no cover
        pass


def decide(*, command: str, repo_root: Path) -> "Optional[object]":
    """Pure decision (advisory only — always allow).

    Side-effect: emits canonical_edit_completed + bash_canonical_bypass_invoked
    for each write-shape target that resolves to a canonical guarded path.
    Returns the contract-layer allow decision.
    """
    targets = _scan_command_targets(command)
    # Detect owner-bypass prefix:  or bare  — the syntax Claude
    # Code uses to run a Bash command as Owner (bypasses PreToolUse hooks).
    cmd_stripped = (command or "").lstrip()
    is_bypass = cmd_stripped.startswith("! ") or cmd_stripped.startswith("!bash")
    for target in targets:
        if _is_canonical(target, repo_root):
            # Heuristic: if any sentinel under round-*/approved.md is
            # active during this session, mark hint accordingly; else
            # mark unsigned.
            hint = "unsigned"
            try:
                from check_canonical_edit import _find_sentinels
                sentinels = _find_sentinels(repo_root)
                if sentinels:
                    hint = f"sentinel-active:{len(sentinels)}"
            except Exception:
                pass
            _emit_canonical_edit_completed(target, hint)
            # Emit bash_canonical_bypass_invoked when the owner-bypass
            # prefix was used to write to a canonical path.
            if is_bypass:
                _emit_bash_canonical_bypass(target, cmd_stripped[:32])
    if _contract is not None:
        return _contract.allow()
    return None


def main() -> int:
    """Entry point — PostToolUse hook, always allow."""
    if _claude_adapter is None or _contract is None:
        return 0
    try:
        event = _claude_adapter.read_event(phase="PostToolUse")
        if event.parse_error:
            _claude_adapter.emit_decision(_contract.allow())
            return 0
        command = event.command or ""
        if not command and isinstance(event.tool_input, dict):
            command = str(event.tool_input.get("command") or "")
        repo_root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
        decide(command=command, repo_root=repo_root)
        _claude_adapter.emit_decision(_contract.allow())
        return 0
    except Exception:  # pragma: no cover
        _claude_adapter.emit_decision(_contract.allow())
        return 0


if __name__ == "__main__":
    sys.exit(main())
