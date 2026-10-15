"""The ``cost_envelope_capped`` audit event of ``check_cost_envelope.py``.

``test_check_cost_envelope_block.py`` pins the hook's DECISION and leaves the
audit event out on purpose: ``_safe_emit_capped`` passed ``action`` twice to
``emit_generic(action, **kwargs)`` — positionally AND as ``action=`` — so the
call raised ``TypeError`` at argument binding, before ``emit_generic`` ran.
The hook's fail-open ``except`` swallowed it: the only trace was one line on
the hook's stderr, never a row in the log and never a breadcrumb in
``audit-log.errors`` (``audit_emit._breadcrumb`` is never reached). Every cap
the gate enforced left the audit trail silent.

This file is the event's control. It runs the hook the way the harness does
— a SUBPROCESS fed a PreToolUse payload, with the REAL emitter (no mock: a
mock of ``emit_generic`` would accept the duplicate keyword and hide the very
``TypeError`` this file exists to catch) writing into this test's isolated
audit dir — and asserts:

* an allowed dispatch writes NO ``cost_envelope_capped`` row (the event is
  not emitted unconditionally);
* a capped dispatch writes EXACTLY ONE row, with the window, class, cap and
  counter the decision names, the payload's session id and the project;
* the row is chain-covered (non-null ``hmac``) and ``verify_chain`` over the
  isolated log is intact;
* nothing outside the event's allowlist reached the row (no
  ``dropped forbidden field`` breadcrumb; no caller-side key such as
  ``project_path`` / ``user_id``; neither the user id nor the command text is
  in the raw line — Sec MF-3, ADR-133 §A);
* the hook's stderr carries no swallowed emit exception.

Red/green provenance (S363): against the hook at ``6ccde6b0`` (duplicate
``action=``) ``test_capped_dispatch_writes_exactly_one_event`` fails with
0 rows and stderr ``emit_generic cost_envelope_capped exception:
TypeError("emit_generic() got multiple values for argument 'action'")``;
green after the keyword is removed; red again when it is re-introduced
(mutant).

Known residual, inherited from ``test_check_cost_envelope_block.py``: the
daily counter lives in a UTC-date-keyed state file and the hook has no clock
seam, so the two dispatches of the test must fall on the same UTC date. A
pair that straddles 00:00 UTC starts a fresh daily counter between them, the
second dispatch is allowed and the test fails (a re-run clears it).

Env discipline: ``TestEnvContext`` isolation; the child env comes from
``subprocess_env`` (HOME + audit dir inside this test's tmp tree, HMAC kill
switch and per-file audit overrides cleared) and every steering variable the
hook reads is popped before being set. The HMAC key is read from the isolated
audit dir by an explicit path, never resolved from ambient env.

Stdlib-only, Python >= 3.9, ``from __future__ import annotations``.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from _lib import audit_hmac  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402

_HOOK = Path(__file__).resolve().parent.parent / "check_cost_envelope.py"

_ACTION = "cost_envelope_capped"
_SWARM_CMD = "python3 .claude/scripts/swarm/coordinator.py --dispatch"
_SESSION_ID = "cost-envelope-emit-session"
_USER_ID = "cost-envelope-emit-user"
# Caller-side inputs the allowlist must keep out of the row (audit_emit.py:1264).
_CALLER_SIDE_KEYS = ("project_path", "user_id", "user", "command")

_STEERING_VARS = (
    "CEO_SWARM",
    "CEO_SWARM_CLASS",
    "CEO_SWARM_ESTIMATED_SPAWN_CENTS",
    "CEO_SWARM_ESTIMATE_CENTS",
    "CEO_PLAN_ID",
    "CEO_USER_ID",
)

# vibecoder daily cap (cents); the matrix is pinned by
# test_cost_envelope.py::TestMatrix.
_VIBECODER_DAILY = 500


class CostEnvelopeCappedEmitTests(TestEnvContext):
    """The hook, as a subprocess, from payload to audit row."""

    def _dispatch(self, *, estimate: int, plan_id: str) -> Tuple[Dict[str, Any], str]:
        env = self.subprocess_env(CLAUDE_PROJECT_DIR=str(self.project_dir))
        for var in _STEERING_VARS:
            env.pop(var, None)
        env["CEO_SWARM"] = "1"
        env["CEO_USER_ID"] = _USER_ID
        env["CEO_PLAN_ID"] = plan_id
        env["CEO_SWARM_ESTIMATED_SPAWN_CENTS"] = str(estimate)
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": _SWARM_CMD},
            "session_id": _SESSION_ID,
        }
        proc = subprocess.run(
            [sys.executable, str(_HOOK)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        self.assertEqual(
            proc.returncode, 0,
            f"hook must exit 0; rc={proc.returncode} stderr={proc.stderr[:400]!r}",
        )
        lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 1, f"one decision line expected; got {proc.stdout!r}")
        return json.loads(lines[0]), proc.stderr

    def _log_path(self) -> Path:
        return self.audit_dir / "audit-log.jsonl"

    def _capped_rows(self) -> List[Tuple[str, Dict[str, Any]]]:
        log = self._log_path()
        if not log.is_file():
            return []
        rows = []
        for raw in log.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            row = json.loads(raw)
            if row.get("action") == _ACTION:
                rows.append((raw, row))
        return rows

    def test_capped_dispatch_writes_exactly_one_event(self) -> None:
        allowed, _ = self._dispatch(estimate=300, plan_id="PLAN-A")
        self.assertEqual(allowed, {}, "300 of 500 daily cents fits; must pass")
        self.assertEqual(
            self._capped_rows(), [],
            "an allowed dispatch must not write a cost_envelope_capped row",
        )

        blocked, stderr = self._dispatch(estimate=300, plan_id="PLAN-B")
        # Armed contrast: the decision IS a block, so a missing row below is
        # the emitter's failure, not a gate that never fired.
        self.assertEqual(blocked.get("decision"), "block", blocked)
        self.assertTrue(
            blocked.get("reason", "").startswith(
                "GOVERNANCE: cost_envelope_capped_at_daily: "
            ),
            blocked,
        )

        rows = self._capped_rows()
        self.assertEqual(
            len(rows), 1,
            f"exactly one {_ACTION} row expected; got {len(rows)} "
            f"(hook stderr={stderr[:400]!r})",
        )
        self.assertNotIn(
            "emit_generic cost_envelope_capped exception", stderr,
            "the emit raised and the fail-open except swallowed it",
        )
        raw, row = rows[0]
        self.assertEqual(row["class_tier"], "vibecoder")
        self.assertEqual(row["window_breached"], "daily")
        self.assertEqual(row["cap_cents"], _VIBECODER_DAILY)
        self.assertEqual(row["current_cents"], 300)
        self.assertEqual(row["session_id"], _SESSION_ID)
        # ``project`` is a per-row field that the CALLER fills: the hook
        # passes ``project=`` from ``_resolve_project_path()``
        # (CLAUDE_PROJECT_DIR, set by this test to its project dir), and
        # ``_write_event`` does not inject it. It is on the allowlist
        # (audit_emit.py:1267) and in the v2.27 field table
        # (SPEC/v1/audit-log.schema.md:398); the deny-by-default comment
        # (audit_emit.py:1264) names the caller-side key ``project_path``.
        # The SPEC prose at :1349-1352 ("raw project paths ... NEVER
        # persisted via this row") contradicts that table — declared
        # residual, 1.4.4.
        self.assertEqual(row["project"], str(self.project_dir))
        self.assertTrue(row.get("hmac"), "the row must be chain-covered")

        # Sec MF-3 — the allowlist kept everything the hook sends, and no
        # caller-side key nor the raw user id / command text reached the row.
        self.assertNotIn(f"{_ACTION} dropped forbidden field", self.read_audit_errors())
        for key in _CALLER_SIDE_KEYS:
            self.assertNotIn(key, row, f"caller-side key {key!r} persisted")
        self.assertNotIn(_USER_ID, raw)
        self.assertNotIn(_SWARM_CMD, raw)

        result = audit_hmac.verify_chain(
            self._log_path(),
            key_path_override=self.audit_dir / audit_hmac.KEY_FILENAME,
        )
        self.assertTrue(result.is_intact, result)
        self.assertGreaterEqual(result.verified_count, 1, result)


if __name__ == "__main__":  # pragma: no cover
    import unittest

    unittest.main()
