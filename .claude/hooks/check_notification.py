#!/usr/bin/env python3
"""PLAN-163 T3.2 — Notification lifecycle telemetry (pure observer).

Registered on the CC 2.1.220 ``Notification`` event (NEW in the 2.1.x
substrate; matcher matches on ``notification_type``). Input shape per the
extracted hook schema (``.claude/data/hook-schema-2.1.220.json``)::

    {message: str, title?: str, notification_type: str, session_id, ...}

The hook records ONE ``notification_lifecycle`` audit event per
notification via the typed emitter
``_lib.audit_emit.emit_notification_lifecycle`` — the durable record of
the agent-attention lifecycle (needs-input / completed /
permission-request) that /ceo-boot telemetry can pivot without a
transcript.

## Contract

- PURE OBSERVER: stdout is ALWAYS ``{}`` and exit is ALWAYS 0 — the
  Notification event's only output arm is ``additionalContext`` and this
  hook deliberately uses none of it. NEVER blocks, never injects.
- ADVISORY + fail-open on INFRASTRUCTURE (CLAUDE.md §4): stdin parse
  errors, import failures, emit failures → stderr breadcrumb + ``{}``
  exit 0. There is no security-matcher input here (nothing to
  fail-CLOSED on — the hook makes no decision).
- Kill-switch: ``CEO_NOTIFICATION_TELEMETRY=0`` → ``{}`` exit 0, no
  read, no emit.

## NO-VALUE-ECHO (Sec MF-3 / S172 doctrine)

The ONLY facts that persist:

- ``notification_type`` — normalized to the CLOSED vocabulary
  {agent_needs_input, agent_completed, permission_request, other}. The
  harness enum is OPEN, so any unrecognized wire value coerces to
  ``other`` and the raw string is NEVER persisted.
- ``has_title`` — bool presence signal only.
- ``message_sha256_prefix`` — 12-lowercase-hex sha256 prefix of the
  message body ("" when absent/empty). Hash, never content: a
  notification message can quote tool output, file paths, or secrets.
- ``session_id`` — threaded from the event (fallback
  ``CLAUDE_SESSION_ID`` env, then "").

``message`` and ``title`` TEXT never leave this process — not on stdout,
not on stderr breadcrumbs, not in the audit log. The typed emitter's
deny-by-default allowlist (``_NOTIFICATION_LIFECYCLE_ALLOWLIST``)
enforces the same boundary a second time (defense-in-depth).

Stdlib only, Python >= 3.9.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

# Make the local `_lib` importable (matches the pattern of existing hooks).
_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

# CLOSED normalization vocabulary (mirror of audit_emit._NOTIFICATION_TYPE_ENUM
# minus the coercion target). Kept as a local literal so the hook stays
# importable even if audit_emit is unavailable (fail-open half below).
_KNOWN_NOTIFICATION_TYPES = frozenset({
    "agent_needs_input", "agent_completed", "permission_request",
})


def _breadcrumb(msg: str) -> None:
    """Stderr breadcrumb. NEVER interpolates message/title content."""
    sys.stderr.write("# check_notification: %s\n" % msg[:160])


def _normalize_type(raw: Any) -> str:
    """Open harness enum -> closed vocabulary. Off-enum/off-type -> other.

    Exact byte match only — no case-folding, no echo of the raw value
    anywhere (an unrecognized value could be arbitrary free text).
    """
    if isinstance(raw, str) and raw in _KNOWN_NOTIFICATION_TYPES:
        return raw
    return "other"


def _message_prefix(raw: Any) -> str:
    """sha256(message)[:12] — hash prefix, never content. "" when absent."""
    if not isinstance(raw, str) or not raw:
        return ""
    return hashlib.sha256(
        raw.encode("utf-8", errors="replace")
    ).hexdigest()[:12]


def _session_id(event: Dict[str, Any]) -> str:
    val = event.get("session_id")
    if isinstance(val, str) and val:
        return val[:64]
    env_val = os.environ.get("CLAUDE_SESSION_ID", "")
    return env_val[:64] if isinstance(env_val, str) else ""


def _emit(event: Dict[str, Any]) -> None:
    """Emit ONE notification_lifecycle row via the typed emitter.

    Lazy import so an audit_emit infra problem degrades to a breadcrumb
    (fail-open), never a hook crash.
    """
    from _lib import audit_emit  # lazy: resolved at emit time

    title = event.get("title")
    # PLAN-182 W2 (S321): sem `project=` o evento nasce nao-atribuivel — o
    # default do emissor e "". Fail-open: falha na resolucao vira "".
    try:
        from _lib import runtime_paths as _rp

        _project = str(_rp.project_dir())
    except Exception:  # pragma: no cover - fail-open
        _project = ""
    audit_emit.emit_notification_lifecycle(
        notification_type=_normalize_type(event.get("notification_type")),
        has_title=bool(isinstance(title, str) and title),
        message_sha256_prefix=_message_prefix(event.get("message")),
        session_id=_session_id(event),
        project=_project,
    )


def main() -> int:
    """Hook entrypoint. Reads the Notification payload; always allows."""
    # Kill-switch first: no read, no emit.
    if os.environ.get("CEO_NOTIFICATION_TELEMETRY") == "0":
        print("{}")
        return 0
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw else {}
        if not isinstance(event, dict):
            raise ValueError("hook input is not a JSON object")
    except Exception as exc:
        # INFRASTRUCTURE fail-open — a telemetry observer never blocks the
        # session. (No security decision is made here, so there is no
        # fail-CLOSED input arm.)
        _breadcrumb("fail-open (stdin): %s" % str(exc)[:120])
        print("{}")
        return 0
    if not event:
        # Empty payload = nothing to record; a vacuous all-coerced row would
        # only be audit noise.
        _breadcrumb("empty payload — nothing to record")
        print("{}")
        return 0
    try:
        _emit(event)
    except Exception as exc:  # pragma: no cover — belt-and-suspenders
        _breadcrumb("fail-open (emit): %s" % type(exc).__name__)
    print("{}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
