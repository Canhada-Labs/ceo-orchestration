#!/usr/bin/env python3
"""PLAN-102 Wave A.2 — PreToolUse hook: cost-envelope gate.

STAGED for ceremony Phase A1 copy to
`.claude/hooks/check_cost_envelope.py`. The ceremony apply-patches.py
performs the copy with Owner-signed sentinel (approved.md.asc) covering
the canonical destination per ADR-010.

## Wire-up

Registered in `.claude/settings.json` PreToolUse Bash matcher with:

    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_cost_envelope.py",
          "timeout": 5,
          "statusMessage": "Checking cost envelope..."
        }
      ]
    }

## Decision logic

1. Master kill — if `CEO_SWARM` unset OR == "0" → schema-compliant
   allow `{}`. Capability is DEFAULT-OFF.
2. Read stdin PreToolUse payload (Bash tool_input).
3. If the dispatch is not a swarm-loop signature (P1 #1 fold —
   requires BOTH `CEO_SWARM=1` AND a real swarm coordinator substring
   in command body), allow `{}`.
4. Resolve class tier from `CEO_SWARM_CLASS` env (default `vibecoder`).
5. Build `CostEnvelope` for (project_path, user_id, class_tier).
6. Estimate spend per spawn: `CEO_SWARM_ESTIMATED_SPAWN_CENTS` env or
   2 cents default (~1300 tokens × $0.000015 input ≈ $0.0195 ≈ 2 cents
   bucketed).
7. Call `env.check_and_record(additional, plan_id)` (Codex R2 iter-2
   P0 #2 fold — atomic check+add under SINGLE FileLock acquisition;
   eliminates TOCTOU window between would_breach and record_spend).
   Returns `(breached_window_or_None, cap_cents_or_-1, current_cents)`.
8. On breach (truthy window) → emit `cost_envelope_capped` via
   `emit_generic` (P0 #2 fold — emit_generic pattern + Sec MF-3 scrub;
   matches `task_route_advised` precedent; keeps
   `_EXPECTED_PUBLIC_SYMBOLS` contract stable) + return
   `{"decision": "block", "reason": "GOVERNANCE: cost_envelope_capped_at_<window>: ..."}`.
9. On allow (window=None) → pass-through `{}` (record already done
   atomically under the same lock).

## Fail-OPEN contract

Per CLAUDE.md §5 fail-open invariant. Any infra error → emit `{}`
breadcrumb to stderr; NEVER block the user session on a parse error /
missing state file / lock contention. The HARD CAP single-strike
semantic applies ONLY when the cap arithmetic actually decides breach.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

_HOOK_DIR = Path(__file__).resolve().parent
if str(_HOOK_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOK_DIR))

try:
    from _lib.cost_envelope import (  # type: ignore[import-not-found]
        CostEnvelope,
        is_disabled,
        soft_cap_breached,
    )
except Exception:  # pragma: no cover — defensive import
    CostEnvelope = None  # type: ignore[assignment]

    def is_disabled() -> bool:  # type: ignore[no-redef]
        return True

    def soft_cap_breached(env) -> bool:  # type: ignore[no-redef]
        return False

try:
    from _lib import audit_emit as _audit_emit  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    _audit_emit = None  # type: ignore[assignment]


_DEFAULT_ESTIMATE_CENTS = 2
# P1 #1 fold — require BOTH CEO_SWARM=1 AND command body match a real
# swarm coordinator signature. Substring matches are cheap + ReDoS-safe.
_SWARM_COMMAND_SIGNATURES = (
    "swarm/coordinator.py",
    "scripts/swarm/",
    ".claude/scripts/swarm/dispatch",
    "swarm_dispatch",
)


def _read_stdin_json() -> Optional[Dict[str, Any]]:
    try:
        raw = sys.stdin.read()
    except Exception:
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _emit_decision(decision: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(decision, ensure_ascii=False) + "\n")


def _breadcrumb(msg: str) -> None:
    try:
        sys.stderr.write(f"[check_cost_envelope] {msg}\n")
    except Exception:
        pass


def _looks_like_swarm_dispatch(tool_input: Dict[str, Any]) -> bool:
    """P1 #1 fold — require BOTH CEO_SWARM=1 AND a real swarm signature
    in the command body. Either alone is NOT enough.

    Prevents false-positive enforcement on every Bash invocation in a
    session that happens to have CEO_SWARM=1 in env (e.g. `git status`).
    """
    if os.environ.get("CEO_SWARM") != "1":
        return False
    cmd = tool_input.get("command")
    if not isinstance(cmd, str) or not cmd:
        return False
    for sig in _SWARM_COMMAND_SIGNATURES:
        if sig in cmd:
            return True
    return False


def _resolve_estimate_cents() -> int:
    raw = os.environ.get("CEO_SWARM_ESTIMATED_SPAWN_CENTS")
    if raw is None:
        # P0 #1 fold — fallback to legacy var for back-compat.
        raw = os.environ.get("CEO_SWARM_ESTIMATE_CENTS")
    if raw is None:
        return _DEFAULT_ESTIMATE_CENTS
    try:
        n = int(raw.strip())
        return n if n > 0 else _DEFAULT_ESTIMATE_CENTS
    except (ValueError, AttributeError):
        return _DEFAULT_ESTIMATE_CENTS


def _resolve_class_tier() -> str:
    raw = (os.environ.get("CEO_SWARM_CLASS") or "vibecoder").strip()
    if raw in ("vibecoder", "CTO", "team"):
        return raw
    return "vibecoder"


def _resolve_user_id() -> str:
    for key in ("CEO_USER_ID", "USER", "LOGNAME"):
        v = os.environ.get(key)
        if v:
            return v
    return "default"


def _resolve_project_path() -> str:
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def _safe_emit_capped(
    *,
    class_tier: str,
    window: str,
    cap_cents: int,
    current_cents: int,
    session_id: str,
    project: str,
) -> None:
    """Emit cost_envelope_capped via emit_generic (P0 #2 fold — NO
    typed wrappers; matches task_route_advised precedent; keeps
    `_EXPECTED_PUBLIC_SYMBOLS` contract gate stable per S141 P1 #3)."""
    if _audit_emit is None:
        return
    if not hasattr(_audit_emit, "emit_generic"):
        return
    try:
        _audit_emit.emit_generic(
            "cost_envelope_capped",
            action="cost_envelope_capped",
            class_tier=str(class_tier),
            window_breached=str(window),
            cap_cents=int(cap_cents),
            current_cents=int(current_cents),
            session_id=session_id,
            project=project,
        )
    except Exception as e:  # pragma: no cover — fail-OPEN
        _breadcrumb(f"emit_generic cost_envelope_capped exception: {e!r}")


def main() -> int:
    t0 = time.monotonic()

    if is_disabled():
        _emit_decision({})
        return 0
    if CostEnvelope is None:
        _emit_decision({})
        return 0

    payload = _read_stdin_json()
    if payload is None:
        _emit_decision({})
        return 0

    tool_name = (payload.get("tool_name") or "").strip()
    tool_input = payload.get("tool_input") or {}
    session_id = (payload.get("session_id") or "").strip()
    if not isinstance(tool_input, dict):
        _emit_decision({})
        return 0

    if tool_name != "Bash" or not _looks_like_swarm_dispatch(tool_input):
        _emit_decision({})
        return 0

    try:
        class_tier = _resolve_class_tier()
        project_path = _resolve_project_path()
        user_id = _resolve_user_id()
        env = CostEnvelope(
            project_path=project_path,
            user_id=user_id,
            class_tier=class_tier,
        )
        estimate = _resolve_estimate_cents()
        plan_id = os.environ.get("CEO_PLAN_ID")
        # Codex R2 iter-2 P0 #2 fold — atomic check+add. Single FileLock
        # acquire covers read of current spend + breach decision +
        # conditional write. Eliminates the prior split-phase TOCTOU
        # window where two concurrent dispatches could both pass
        # would_breach() and then overshoot the cap on record_spend().
        breached, cap, current = env.check_and_record(int(estimate), plan_id=plan_id)
    except Exception as e:
        _breadcrumb(f"envelope eval exception (fail-OPEN): {e!r}")
        _emit_decision({})
        return 0

    if not breached:
        # Allow path — check_and_record has already persisted the spend
        # atomically under the same lock. Nothing more to do.
        _emit_decision({})
        return 0

    _safe_emit_capped(
        class_tier=class_tier,
        window=breached,
        cap_cents=cap,
        current_cents=current,
        session_id=session_id,
        project=str(project_path),
    )

    duration_ms = int((time.monotonic() - t0) * 1000)
    reason = (
        f"GOVERNANCE: cost_envelope_capped_at_{breached}: "
        f"class={class_tier} cap_cents={cap} current_cents={current} "
        f"check_ms={duration_ms}"
    )
    _emit_decision({"decision": "block", "reason": reason})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
