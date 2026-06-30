"""PLAN-136 T2a — check-audit-hmac-null.py CI gate tests.

Covers the S234 regression-class guard (float-in-HMAC → hmac=null):

- A clean log (known actions with a valid hmac, healthy ``hmac_error: null``)
  exits 0.
- A log with one known-action line carrying ``hmac=null`` + a non-null
  ``hmac_error`` breadcrumb exits 1.
- A missing log fail-opens (exit 0).
- An unknown-action line with hmac=null is ignored (out of scope).
- A PRESENT log with one malformed (un-parseable) line FAILS (exit 1) — only
  the *absent* log is allowed to fail-open.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent.parent
_CLI = _REPO / ".claude" / "scripts" / "check-audit-hmac-null.py"

# Canonical env-isolation base so this test is hygiene-mandate-compliant
# (PLAN-136 / S221 — no bare unittest.TestCase). Fail-soft import fallback.
try:
    from _lib.testing import TestEnvContext  # type: ignore
except Exception:  # pragma: no cover - defensive import-fallback
    _HOOKS_DIR = _REPO / ".claude" / "hooks"
    if str(_HOOKS_DIR) not in sys.path:
        sys.path.insert(0, str(_HOOKS_DIR))
    from _lib.testing import TestEnvContext  # type: ignore


# Inline fixtures -----------------------------------------------------------

# A CLEAN log: two known-action entries with a populated hmac and a healthy
# (null) hmac_error breadcrumb — exactly the shape a healthy chain produces.
_CLEAN_LINES = [
    {
        "action": "agent_spawn",
        "ts": "2026-06-15T00:00:00Z",
        "hmac": "df924db6612154731fd99c2bc6142ec83c398bb7fb3aba5f37c8d76b74fc3c89",
        "hmac_error": None,
    },
    {
        "action": "plan_transition",
        "ts": "2026-06-15T00:00:01Z",
        "hmac": "fea3ab64c31eff6b79feea87edf4230abe54dc8118c44a648c39c3b88635ce23",
        "hmac_error": None,
    },
]

# A REGRESSION log: one known-action entry written with hmac=null and a
# non-null hmac_error breadcrumb — the S234 float-in-HMAC birth defect.
_REGRESSION_LINES = [
    {
        "action": "agent_spawn",
        "ts": "2026-06-15T00:00:00Z",
        "hmac": "df924db6612154731fd99c2bc6142ec83c398bb7fb3aba5f37c8d76b74fc3c89",
        "hmac_error": None,
    },
    {
        "action": "statusline_sidecar_write",
        "ts": "2026-06-15T00:00:02Z",
        "hmac": None,
        "hmac_error": "CanonicalJsonError: float not permitted in canonical JSON",
    },
]


def _write_log(path: Path, entries) -> None:
    with path.open("w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, separators=(",", ":")) + "\n")


def _write_raw_lines(path: Path, lines) -> None:
    """Write raw text lines verbatim (used to inject a malformed JSON line)."""
    with path.open("w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")


class CheckAuditHmacNullCliTest(TestEnvContext):

    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory(prefix="plan-136-t2a-")
        self.tmp = Path(self._tmp.name)
        self.log_path = self.tmp / "audit-log.jsonl"

    def tearDown(self):
        self._tmp.cleanup()
        super().tearDown()

    def _run(self, *extra_args):
        cmd = [sys.executable, str(_CLI), "--log", str(self.log_path)]
        cmd.extend(extra_args)
        return subprocess.run(cmd, capture_output=True, text=True)

    # -- core contract -----------------------------------------------------

    def test_clean_log_exits_0(self):
        _write_log(self.log_path, _CLEAN_LINES)
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_regression_log_exits_1(self):
        _write_log(self.log_path, _REGRESSION_LINES)
        r = self._run()
        self.assertEqual(r.returncode, 1, r.stderr)
        # The offending action surfaces in the human report.
        self.assertIn("statusline_sidecar_write", r.stderr)

    # -- supporting behaviours --------------------------------------------

    def test_missing_log_fail_opens(self):
        # log_path intentionally not created.
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_json_report_clean(self):
        _write_log(self.log_path, _CLEAN_LINES)
        r = self._run("--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["regression_count"], 0)

    def test_json_report_regression(self):
        _write_log(self.log_path, _REGRESSION_LINES)
        r = self._run("--json")
        self.assertEqual(r.returncode, 1, r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["regression_count"], 1)
        self.assertEqual(report["findings"][0]["action"], "statusline_sidecar_write")

    def test_unknown_action_with_null_hmac_ignored(self):
        # An action NOT in _KNOWN_ACTIONS must not trip the gate.
        _write_log(self.log_path, [
            {"action": "totally_not_a_real_action", "hmac": None, "hmac_error": "x"},
        ])
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stderr)

    # -- present-but-malformed log must FAIL (not fail-open) ----------------

    def test_present_log_with_malformed_line_exits_1(self):
        # One clean known-action line + one un-parseable JSON line. Even
        # though no OTHER line is bad, the malformed line in a PRESENT log
        # must FAIL the gate (fail-open is reserved for the ABSENT log only).
        # Without the fix this exits 0 (the malformed line is silently
        # skipped) → a corrupted/tampered log slips past the security gate.
        clean = json.dumps(_CLEAN_LINES[0], separators=(",", ":"))
        _write_raw_lines(self.log_path, [clean, "{not valid json"])
        r = self._run()
        self.assertEqual(r.returncode, 1, r.stderr)

    def test_present_log_with_malformed_line_json_report(self):
        clean = json.dumps(_CLEAN_LINES[0], separators=(",", ":"))
        _write_raw_lines(self.log_path, [clean, "{not valid json"])
        r = self._run("--json")
        self.assertEqual(r.returncode, 1, r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["regression_count"], 1)
        self.assertEqual(report["findings"][0]["reason"], "malformed_json")
        # The malformed line is line 2 in the fixture.
        self.assertEqual(report["findings"][0]["line"], 2)


if __name__ == "__main__":
    unittest.main()
