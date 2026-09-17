#!/usr/bin/env python3
"""PLAN-190 W1 — Workflow launch ledger + resume guard (PreToolUse/PostToolUse ``Workflow``).

Records every ``Workflow`` tool call BEFORE it is dispatched (script sha256 +
snapshot of the script bytes, literal ``args``, ``resumeFromRunId``, code
revision of ``cwd`` enriched afterwards within a strict budget) and, on the
PostToolUse half, binds the run id the runner returned. Library:
``_lib/launch_ledger.py`` (the contract, the guard rules and the binding rules
are documented there).

Contract
--------
- Fires for ``tool_name == "Workflow"`` only; anything else ⇒ ``{}``.
- PreToolUse: the guard decides a resume from this call and the recorded manifest,
  then this call's manifest + snapshot + index line are written (before any git
  enrichment). On a resume:
  args differ from the bound manifest ⇒ ``{"decision": "block", "reason": <counts-only>}``;
  script differs, args same ⇒ ``{"systemMessage": <advisory>}`` unless
  ``CEO_WORKFLOW_SCRIPT_GUARD=enforce``; args identical but a script hash unavailable ⇒ inconclusive,
  allowed; no bound manifest ⇒ allowed; a recorded manifest that fails its
  integrity check (``manifest_problem``) ⇒ inconclusive, allowed. A block
  needs a STRONG bind (by ``tool_use_id`` or manual): a heuristic bind never
  sustains one, args or script alike. ONE override path for every block, and
  it is carried by the call or the process, never by stored state:
  ``CEO_WORKFLOW_RESUME_FORCE=1`` in the process environment, or the call's own
  ``description`` starting with ``CEO_WORKFLOW_RESUME_FORCE:`` plus a non-empty
  reason — recorded as ``mismatch_forced`` and announced.
  ``CEO_WORKFLOW_RESUME_GUARD=0`` = advisory mode. An exception inside the
  guard is recorded as inconclusive (never a silent allow without a record).
- PostToolUse: binds ``wf_<id>`` by ``tool_use_id``, else by the single unbound
  launch of the session — a launch the guard blocked never ran and is never a
  candidate; an unknown tool_use_id or zero/several candidates is an ``orphan``
  line; a response with no run id, or with ambiguous ids, records nothing.
  Always ``{}``.
- Fail-OPEN on infrastructure (unreadable stdin, import failure, unwritable
  state dir): breadcrumb to stderr + ``{}``. This is a recovery instrument,
  not a security matcher — it must never wedge a session.
- Kill-switch: ``CEO_WORKFLOW_LEDGER=0``.
- The block reason never carries operator text (arg keys, values, an
  unvalidated run id): the channel to the model is counts-only by removal.
- Emits NO audit event (registering an audit action is the audit owner's
  ceremony — PLAN-190 follow-up); the ledger files are the record.
- Stdlib only, Python >= 3.9.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))


def _breadcrumb(msg: str) -> None:
    sys.stderr.write("# check_workflow_launch: %s\n" % msg[:200])


def gate(event: Dict[str, Any]) -> Dict[str, Any]:
    if os.environ.get("CEO_WORKFLOW_LEDGER", "1") == "0":
        return {}
    if event.get("tool_name") != "Workflow":
        return {}
    try:
        from _lib import launch_ledger  # noqa: E402
    except Exception as exc:  # pragma: no cover — import guard
        _breadcrumb("launch_ledger import failed (%s)" % str(exc)[:100])
        return {}
    try:
        d = launch_ledger.ledger_dir()
    except Exception as exc:
        _breadcrumb("ledger dir unavailable (%s)" % str(exc)[:100])
        return {}
    hook_event = event.get("hook_event_name")
    if not isinstance(hook_event, str) and "tool_response" in event:
        hook_event = "PostToolUse"  # older CLIs may omit the name; a response present means Post
    try:
        if hook_event == "PostToolUse":
            launch_ledger.decide_post(event, d)
            return {}
        decision, manifest = launch_ledger.decide_pre(event, d)
        if manifest.get("write_error"):
            _breadcrumb("ledger write failed (%s); decision kept" % str(manifest["write_error"])[:40])
        guard_error = (manifest.get("guard") or {}).get("error")
        if guard_error:
            _breadcrumb("guard inconclusive after %s (recorded)" % str(guard_error)[:60])
        return decision
    except Exception as exc:
        _breadcrumb("ledger write/guard failed (%s)" % str(exc)[:100])
        return {}


def main() -> None:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
        if not isinstance(event, dict):
            event = {}
    except Exception as exc:
        _breadcrumb("unreadable stdin (%s)" % str(exc)[:80])
        event = {}
    try:
        out = gate(event)
    except Exception as exc:  # pragma: no cover — belt-and-suspenders
        _breadcrumb("gate raised (%s)" % str(exc)[:80])
        out = {}
    sys.stdout.write(json.dumps(out) + "\n")


if __name__ == "__main__":
    main()
    sys.exit(0)
