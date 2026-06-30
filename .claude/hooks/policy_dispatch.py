#!/usr/bin/env python3
"""policy_dispatch — dispatcher for policy-as-code hooks (PLAN-014 A.3).

Loads a YAML policy via :func:`_lib.policy.load` and evaluates against a
tool-call event on stdin. Output is a single JSON decision line on stdout
per the hook-io contract.

Fail-mode follows SPEC/v1/policy-dsl.schema.md §7 + ADR-045 §Fail-mode:

- ``CEO_POLICY_ENGINE_DISABLE=1`` → short-circuit to allow + breadcrumb
  via ``policy_error(disabled_by_env)`` (logged but tolerated since it is
  not in the SPEC §5 closed enum → falls back to ``parse_error`` in the
  emitter). Optionally delegates to a legacy ``.py`` hook at
  ``$CEO_POLICY_LEGACY_HOOK_PATH`` if set.
- Load failure → emit ``policy_error(error_kind)``; delegate to
  ``$CEO_POLICY_LEGACY_HOOK_PATH`` if set (dual-path window). Otherwise
  fail-CLOSED for security-surface hooks (block with
  ``policy_engine_unavailable``).

Invocation::

    policy_dispatch.py --policy bash-safety

The policy file is resolved as::

    $CLAUDE_PROJECT_DIR/.claude/policies/<name>.policy.yaml

or overridden by ``$CEO_POLICY_FILE`` (absolute path).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _lib import policy as _policy  # noqa: E402
except Exception as e:  # pragma: no cover
    _policy = None  # type: ignore
    _IMPORT_EXC = e
else:
    _IMPORT_EXC = None

try:
    from _lib import audit_emit as _audit_emit  # noqa: E402
except Exception:  # pragma: no cover
    _audit_emit = None  # type: ignore


def _emit_error(policy_id: str, error_kind: str, detail: str) -> None:
    if _audit_emit is None:
        return
    try:
        _audit_emit.emit_policy_error(
            policy_id=policy_id,
            error_kind=error_kind,
            detail=detail,
        )
    except Exception:  # pragma: no cover
        pass


def _resolve_policy_path(name: str) -> Path:
    override = os.environ.get("CEO_POLICY_FILE")
    if override:
        return Path(override)
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(project_dir) / ".claude" / "policies" / f"{name}.policy.yaml"


def _delegate_to_legacy(event_text: str) -> int:
    """Re-invoke the legacy Python hook if available. Returns exit code."""
    legacy = os.environ.get("CEO_POLICY_LEGACY_HOOK_PATH")
    if not legacy:
        return -1
    legacy_path = Path(legacy)
    if not legacy_path.is_file():
        return -1
    try:
        proc = subprocess.run(
            [sys.executable, str(legacy_path)],
            input=event_text,
            capture_output=True,
            text=True,
            timeout=5.0,
        )
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        return proc.returncode
    except Exception:
        return -1


def _fail_closed(policy_id: str, reason: str) -> None:
    sys.stdout.write(json.dumps({
        "decision": "block",
        "reason": reason,
    }, ensure_ascii=False) + "\n")


def _allow() -> None:
    sys.stdout.write(json.dumps({"decision": "allow"},
                                ensure_ascii=False) + "\n")


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(prog="policy_dispatch")
    parser.add_argument("--policy", required=True,
                        help="Policy slug (filename base without .policy.yaml)")
    args = parser.parse_args(argv)

    event_text = sys.stdin.read() or "{}"
    try:
        event: Dict[str, Any] = json.loads(event_text)
    except json.JSONDecodeError:
        event = {}

    # Kill-switch escape hatch (SPEC §7.4).
    if os.environ.get("CEO_POLICY_ENGINE_DISABLE") == "1":
        _emit_error(args.policy, "parse_error", "disabled_by_env")
        rc = _delegate_to_legacy(event_text)
        if rc >= 0:
            return rc
        _allow()
        return 0

    if _policy is None:
        _emit_error(args.policy, "import_failure", str(_IMPORT_EXC))
        rc = _delegate_to_legacy(event_text)
        if rc >= 0:
            return rc
        _fail_closed(args.policy, "policy_engine_unavailable")
        return 0

    policy_path = _resolve_policy_path(args.policy)
    try:
        policy_obj = _policy.load(policy_path)
    except _policy.PolicyLoadError as e:
        _emit_error(e.policy_id or args.policy, e.error_kind, e.detail)
        rc = _delegate_to_legacy(event_text)
        if rc >= 0:
            return rc
        _fail_closed(args.policy, "policy_engine_unavailable")
        return 0
    except Exception as e:  # pragma: no cover
        _emit_error(args.policy, "parse_error", f"unexpected: {e}")
        rc = _delegate_to_legacy(event_text)
        if rc >= 0:
            return rc
        _fail_closed(args.policy, "policy_engine_unavailable")
        return 0

    decision = policy_obj.decide(event)
    sys.stdout.write(json.dumps(decision, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
