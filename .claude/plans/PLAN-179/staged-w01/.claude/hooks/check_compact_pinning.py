#!/usr/bin/env python3
"""PLAN-179 W1-b [amendment r1-C3] — Constraint Pinning, PRIMARY channel.

After a compaction the harness starts a fresh session turn and fires
``SessionStart`` with ``source="compact"``. This hook re-states the pinned
governance constraints (``_lib/pinned_constraints.PINNED_CONSTRAINTS`` — a
CODE constant, amendment r1-C5) through
``hookSpecificOutput.additionalContext``.

## Why SessionStart is the PRIMARY channel and PostCompact the REINFORCEMENT

W0-1 of PLAN-179 still owes a verdict on whether ``PostCompact``'s
``additionalContext`` is actually CONSUMED (the S309 fires-proof showed the
event fires and delivers nothing useful — [[feedback-event-probe-is-not-channel-probe]]:
proving a hook fired does NOT prove its output is consumed). ``SessionStart``
``additionalContext`` has a positive local precedent — ``turbo_sessionstart.py``,
whose banner demonstrably reaches the model. Pinning therefore rides the
CHANNEL WITH EVIDENCE and stops being hostage to the W0 verdict;
``check_postcompact_reinject.py`` re-emits the same block as reinforcement.

## Contract

- Fires on ``SessionStart`` only, and is a NO-OP unless ``source`` is
  exactly ``"compact"``. The documented enum is
  ``[startup, resume, clear, compact, fork]``; any other value — including
  a value a future harness adds — is treated as "not a compaction" and
  yields ``{}``. Non-compact starts already read Gate-1 the normal way, so
  emitting there would only buy context tax.
- ADVISORY + fail-OPEN on everything (missing/broken stdin, import failure,
  unexpected shapes): breadcrumb to stderr + ``{}``. A SessionStart hook must
  never wedge a session.
- Emits NO audit event. ``pinned_constraints_emitted`` is NOT in
  ``_lib/audit_emit._KNOWN_ACTIONS`` and an unregistered action is silently
  DROPPED — registering it (allowlist + scrub branch + SPEC row) is the audit
  owner's ceremony, tracked as a PLAN-179 follow-up. Emitting into a void
  would be false telemetry, so this hook stays silent on the wire.
- Kill-switch: ``CEO_CONSTRAINT_PINNING=0`` (dedicated — see below).
- Stdlib only, Python >= 3.9.

## Kill-switch decoupling (PLAN-179 §8.8, decision taken here)

The deferred question was whether pinning shares ``CEO_COMPACTION_CONTINUITY=0``
with the snapshot machinery. DECISION: it does NOT. That switch is documented
as "turn off the continuity SNAPSHOT"; letting it also silently disarm the
governance floor would widen one narrowly-scoped operational decision into a
governance decision the operator never made. Pinning gets its own
``CEO_CONSTRAINT_PINNING=0``. Owner ratification is requested at land time.
(PLAN-179 — rail finding C: the previous wording called the snapshot switch an
operator's "throughput decision", which implies disabling it buys throughput.
This repo makes no speed claim anywhere; the wording is now neutral.)

## additionalContext shape

``{"hookSpecificOutput": {"hookEventName": "SessionStart",
  "additionalContext": "<pinned constraint block>"}}``
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

# Make the local `_lib` importable (matches the pattern of existing hooks).
_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

# PLAN-179 W1-b: the ONLY SessionStart source that means "the transcript was
# just collapsed". Kept as a single literal rather than the full enum — this
# hook needs to recognise one value, and listing the other four would invite
# the closed-set-from-memory error class
# ([[feedback-closed-sets-must-be-derived-not-recalled]]).
_COMPACT_SOURCE = "compact"


def _breadcrumb(msg: str) -> None:
    sys.stderr.write("# check_compact_pinning: %s\n" % msg[:160])


def gate(event: Dict[str, Any]) -> Dict[str, Any]:
    """Return the SessionStart hookSpecificOutput, or ``{}`` for a no-op.

    No-ops on: the dedicated kill-switch, a non-``compact`` source, an absent
    or non-string source, and an unavailable/empty pinned set."""
    if os.environ.get("CEO_CONSTRAINT_PINNING", "1") == "0":
        return {}
    source = event.get("source")
    # Fail-open on anything unexpected: a missing source, a non-string source,
    # or a source this hook does not recognise is NOT a compaction restart.
    if not isinstance(source, str) or source != _COMPACT_SOURCE:
        return {}
    try:
        from _lib import pinned_constraints  # noqa: E402
    except Exception as exc:  # pragma: no cover — import guard
        _breadcrumb("pinned_constraints import failed (%s)" % str(exc)[:80])
        return {}
    try:
        lines = pinned_constraints.render_pinned_block()
    except Exception as exc:  # pragma: no cover — belt-and-suspenders
        _breadcrumb("render_pinned_block failed (%s)" % str(exc)[:80])
        return {}
    if not lines:
        return {}
    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n".join(lines),
        }
    }


def main() -> None:
    try:
        hook_input = json.loads(sys.stdin.read() or "{}")
        if not isinstance(hook_input, dict):
            raise ValueError("hook input is not a JSON object")
    except Exception as exc:
        # PLAN-091 S116: parse error is infra → breadcrumb + schema-compliant allow.
        _breadcrumb("fail-open (stdin): %s" % str(exc)[:120])
        print("{}")
        return
    try:
        print(json.dumps(gate(hook_input)))
    except Exception as exc:
        _breadcrumb("fail-open: %s" % str(exc)[:120])
        print("{}")


if __name__ == "__main__":
    main()
