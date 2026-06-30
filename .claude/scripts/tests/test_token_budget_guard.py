"""tests/test_token_budget_guard.py — PLAN-083 sub-agent 0.4 deliverable.

Stdlib unittest. Verifies:
  - check command exit codes (under vs over threshold)
  - dedup: first emit fires, retry within window suppressed
  - volume cap: 11th emit in 1h suppressed (per AC5c)
  - missing estimate file: graceful default to "no estimate available, allow"
  - --json schema valid
  - Sec MF-3 sanitize_event() drops non-allowlisted keys
  - plan-id regex guard (no path traversal)
  - audit-emit field whitelisting (NEVER persist token TEXT, only counts)
  - auto-pause-hook mode always exit 0
  - integer basis-points conversion (no floats in audit event)

Test invocation:
  cd .claude/plans/PLAN-083/staging/wave-0a/sub-0-4-token-budget-guard
  python3 -m unittest tests.test_token_budget_guard
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock


# Locate token-budget-guard.py relative to this test file.
_HERE = Path(__file__).resolve().parent
_SCRIPT_PATH = _HERE.parent / "token-budget-guard.py"


def _load_module():
    """Import token-budget-guard.py as a module (hyphen-named file)."""
    spec = importlib.util.spec_from_file_location("token_budget_guard", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tbg = _load_module()


class _TBGTestBase(unittest.TestCase):
    """Shared setUp: isolated tmpdir for audit-log + state + estimates."""

    def setUp(self) -> None:
        # PLAN-107 Wave A.4: force sync mode for emit-read tests
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
        self.tmpdir = Path(tempfile.mkdtemp(prefix="tbg-test-"))
        self.audit_log = self.tmpdir / "audit-log.jsonl"
        self.state_dir = self.tmpdir / "state"
        self.estimate_dir = self.tmpdir / "estimates"
        self.estimate_dir.mkdir()

        self._env_backup = {
            "CEO_AUDIT_LOG_PATH": os.environ.get("CEO_AUDIT_LOG_PATH"),
            "CEO_BUDGET_GUARD_STATE_DIR": os.environ.get("CEO_BUDGET_GUARD_STATE_DIR"),
            "CEO_TOKEN_ESTIMATE_DIR": os.environ.get("CEO_TOKEN_ESTIMATE_DIR"),
            "CEO_AUDIT_SYNC_MODE": os.environ.get("CEO_AUDIT_SYNC_MODE"),
            "HOME": os.environ.get("HOME"),
            "CLAUDE_PROJECT_DIR": os.environ.get("CLAUDE_PROJECT_DIR"),
        }
        os.environ["CEO_AUDIT_LOG_PATH"] = str(self.audit_log)
        os.environ["CEO_BUDGET_GUARD_STATE_DIR"] = str(self.state_dir)
        os.environ["CEO_TOKEN_ESTIMATE_DIR"] = str(self.estimate_dir)
        # Force HOME away from real user home so fallback paths land in tmpdir.
        os.environ["HOME"] = str(self.tmpdir / "home")
        # Avoid CLAUDE_PROJECT_DIR leak from outer harness into module's
        # estimate-file search paths during tests.
        os.environ.pop("CLAUDE_PROJECT_DIR", None)

    def tearDown(self) -> None:
        for k, v in self._env_backup.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # ------- audit-log helpers -------

    def _write_audit_event(self, **fields: Any) -> None:
        fields.setdefault("action", "agent_spawn")
        fields.setdefault("ts", "2026-05-11T12:00:00Z")
        self.audit_log.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(fields, sort_keys=True) + "\n")

    def _read_audit_events(self) -> List[Dict[str, Any]]:
        if not self.audit_log.is_file():
            return []
        out: List[Dict[str, Any]] = []
        with self.audit_log.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out

    def _write_estimate(self, plan_id: str, tokens: int) -> None:
        path = self.estimate_dir / f"{plan_id}.tokens.estimate"
        with path.open("w", encoding="utf-8") as f:
            json.dump({"estimate_tokens": tokens}, f)


# ----------------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------------


class TestPlanIdValidation(_TBGTestBase):
    """Sec MF-3 + path-traversal guard for plan_id."""

    def test_valid_plan_id_accepted(self):
        self.assertEqual(tbg.validate_plan_id("PLAN-083"), "PLAN-083")

    def test_invalid_plan_id_rejected(self):
        bad_ids = [
            "plan-083",          # lowercase
            "PLAN-83",           # 2 digits
            "PLAN-0083",         # 4 digits
            "PLAN-083/etc",      # path traversal
            "../PLAN-083",       # traversal
            "PLAN-083;rm",       # shell metachar
            "",                  # empty
            "PLAN-ABC",          # non-numeric
        ]
        for bad in bad_ids:
            with self.assertRaises(ValueError, msg=f"should reject {bad!r}"):
                tbg.validate_plan_id(bad)


class TestEstimateReader(_TBGTestBase):
    """Estimate file resolution + degraded paths."""

    def test_read_estimate_from_env_dir(self):
        self._write_estimate("PLAN-083", 1_000_000)
        self.assertEqual(tbg.read_estimate("PLAN-083"), 1_000_000)

    def test_read_estimate_missing_returns_none(self):
        self.assertIsNone(tbg.read_estimate("PLAN-999"))

    def test_read_estimate_corrupt_returns_none(self):
        path = self.estimate_dir / "PLAN-083.tokens.estimate"
        path.write_text("{ not valid json", encoding="utf-8")
        # Capture stderr to ensure a warning is printed.
        with mock.patch.object(sys, "stderr", new_callable=StringIO) as stderr:
            self.assertIsNone(tbg.read_estimate("PLAN-083"))
        self.assertIn("unreadable", stderr.getvalue())

    def test_read_estimate_high_low_band_midpoint(self):
        path = self.estimate_dir / "PLAN-083.tokens.estimate"
        path.write_text(
            json.dumps({"estimate_tokens_low": 1000, "estimate_tokens_high": 3000}),
            encoding="utf-8",
        )
        self.assertEqual(tbg.read_estimate("PLAN-083"), 2000)


class TestActualTokensSum(_TBGTestBase):
    """audit-log.jsonl token aggregation by plan_id."""

    def test_sum_actual_tokens_filters_by_plan_id(self):
        self._write_audit_event(plan_id="PLAN-083", tokens_in=100, tokens_out=200)
        self._write_audit_event(plan_id="PLAN-083", tokens_in=50, tokens_out=None)
        self._write_audit_event(plan_id="PLAN-084", tokens_in=999, tokens_out=999)
        self._write_audit_event(plan_id=None, tokens_in=1, tokens_out=2)
        self.assertEqual(tbg.sum_actual_tokens("PLAN-083"), 350)

    def test_sum_actual_tokens_handles_missing_log(self):
        # Audit log does not yet exist.
        self.assertEqual(tbg.sum_actual_tokens("PLAN-083"), 0)

    def test_sum_actual_tokens_skips_malformed_lines(self):
        self.audit_log.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_log.open("a", encoding="utf-8") as f:
            f.write("not json\n")
            f.write(json.dumps({"action": "agent_spawn", "plan_id": "PLAN-083",
                                "tokens_in": 42, "tokens_out": 0}) + "\n")
            f.write("\n")  # blank line
        self.assertEqual(tbg.sum_actual_tokens("PLAN-083"), 42)


class TestEvaluateDecisions(_TBGTestBase):
    """Core evaluate() decision tree."""

    def test_under_threshold_continues(self):
        self._write_estimate("PLAN-083", 1000)
        self._write_audit_event(plan_id="PLAN-083", tokens_in=400, tokens_out=200)
        verdict = tbg.evaluate("PLAN-083", 0.80)
        self.assertEqual(verdict["decision"], "continue")
        self.assertEqual(verdict["reason"], "under_threshold")
        self.assertEqual(verdict["actual_tokens"], 600)
        self.assertEqual(verdict["ratio_basis_points"], 600)
        self.assertEqual(verdict["threshold_basis_points"], 800)
        self.assertFalse(verdict["emitted"])

    def test_over_threshold_pauses_and_emits(self):
        self._write_estimate("PLAN-083", 1000)
        self._write_audit_event(plan_id="PLAN-083", tokens_in=600, tokens_out=300)
        verdict = tbg.evaluate("PLAN-083", 0.80)
        self.assertEqual(verdict["decision"], "pause")
        self.assertEqual(verdict["reason"], "over_threshold")
        self.assertEqual(verdict["actual_tokens"], 900)
        self.assertEqual(verdict["ratio_basis_points"], 900)
        self.assertTrue(verdict["emitted"])

        # Verify audit event landed with ONLY allowed fields.
        events = self._read_audit_events()
        guard_events = [e for e in events if e.get("action") == tbg.ACTION_NAME]
        self.assertEqual(len(guard_events), 1)
        e = guard_events[0]
        self.assertEqual(e["plan_id"], "PLAN-083")
        self.assertEqual(e["estimate_tokens"], 1000)
        self.assertEqual(e["actual_tokens"], 900)
        self.assertEqual(e["ratio_basis_points"], 900)
        self.assertEqual(e["threshold_basis_points"], 800)

    def test_no_estimate_file_degrades_to_continue(self):
        # No estimate file written → no fallback subprocess → graceful continue.
        self._write_audit_event(plan_id="PLAN-083", tokens_in=99_999, tokens_out=0)
        # Capture stderr.
        with mock.patch.object(sys, "stderr", new_callable=StringIO) as stderr:
            verdict = tbg.evaluate("PLAN-083", 0.80)
        self.assertEqual(verdict["decision"], "continue")
        self.assertEqual(verdict["reason"], "no_estimate_available")
        self.assertIsNone(verdict["estimate_tokens"])
        self.assertIn("no estimate available", stderr.getvalue())


class TestDedupAndVolumeCap(_TBGTestBase):
    """Dedup window + AC5c volume cap (≤10/hr)."""

    def test_dedup_suppresses_second_emit_in_window(self):
        self._write_estimate("PLAN-083", 1000)
        self._write_audit_event(plan_id="PLAN-083", tokens_in=800, tokens_out=100)
        now = 1_000_000.0
        v1 = tbg.evaluate("PLAN-083", 0.80, now=now)
        self.assertTrue(v1["emitted"])
        # Retry 5 minutes later — within dedup window → suppressed.
        v2 = tbg.evaluate("PLAN-083", 0.80, now=now + 300.0)
        self.assertEqual(v2["decision"], "pause")  # still pause
        self.assertEqual(v2["reason"], "over_threshold_dedup_suppressed")
        self.assertFalse(v2["emitted"])
        events = [e for e in self._read_audit_events() if e.get("action") == tbg.ACTION_NAME]
        self.assertEqual(len(events), 1, "second emit must be suppressed")

    def test_dedup_window_expires_after_1h(self):
        self._write_estimate("PLAN-083", 1000)
        self._write_audit_event(plan_id="PLAN-083", tokens_in=900, tokens_out=0)
        now = 1_000_000.0
        v1 = tbg.evaluate("PLAN-083", 0.80, now=now)
        self.assertTrue(v1["emitted"])
        # Past the 1h window → new emit allowed.
        v2 = tbg.evaluate("PLAN-083", 0.80, now=now + 3601.0)
        self.assertTrue(v2["emitted"])

    def test_volume_cap_suppresses_11th_emit(self):
        # Pre-populate 10 unique plan_id emits within the window by directly
        # poking the state file (cheaper than 10 evaluate() roundtrips).
        now = 1_000_000.0
        tbg._state_dir().mkdir(parents=True, exist_ok=True)
        cap_file = tbg._volume_cap_file()
        with cap_file.open("w", encoding="utf-8") as f:
            json.dump(
                {"emit_timestamps": [now - i for i in range(10)]},
                f,
            )
        self._write_estimate("PLAN-083", 1000)
        self._write_audit_event(plan_id="PLAN-083", tokens_in=900, tokens_out=0)
        with mock.patch.object(sys, "stderr", new_callable=StringIO) as stderr:
            verdict = tbg.evaluate("PLAN-083", 0.80, now=now + 1.0)
        self.assertTrue(verdict["volume_cap_hit"])
        self.assertFalse(verdict["emitted"])
        self.assertEqual(verdict["reason"], "over_threshold_volume_cap_suppressed")
        self.assertIn("volume cap", stderr.getvalue())
        # And no new guard event landed in the log.
        guard_events = [e for e in self._read_audit_events()
                        if e.get("action") == tbg.ACTION_NAME]
        self.assertEqual(guard_events, [])


class TestSecMF3Sanitization(_TBGTestBase):
    """Sec MF-3 deny-by-default field whitelist."""

    def test_sanitize_event_drops_disallowed_keys(self):
        unsafe = {
            "plan_id": "PLAN-083",
            "estimate_tokens": 1000,
            "actual_tokens": 800,
            "ratio_basis_points": 800,
            "threshold_basis_points": 800,
            # Forbidden keys (per Sec MF-3):
            "prompt_text": "Run /spawn with these secrets...",
            "raw_audit_event": "tokens=foo",
            "file_path": "/etc/passwd",
            "owner_email": "owner@example.com",
            "env_vars": {"ANTHROPIC_API_KEY": "sk-ant-..."},
        }
        safe = tbg.sanitize_event(unsafe)
        self.assertEqual(set(safe.keys()), tbg.ALLOWED_FIELDS & set(safe.keys()))
        self.assertTrue(set(safe.keys()).issubset(tbg.ALLOWED_FIELDS))
        # Verify forbidden values are absent.
        joined = json.dumps(safe)
        self.assertNotIn("sk-ant-", joined)
        self.assertNotIn("/etc/passwd", joined)
        self.assertNotIn("owner@example.com", joined)
        self.assertNotIn("Run /spawn", joined)

    def test_emitted_event_only_has_allowed_caller_fields(self):
        """Direct-write fallback must persist ONLY whitelisted caller fields."""
        self._write_estimate("PLAN-083", 1000)
        self._write_audit_event(plan_id="PLAN-083", tokens_in=900, tokens_out=0)
        verdict = tbg.evaluate("PLAN-083", 0.80)
        self.assertTrue(verdict["emitted"])
        events = [e for e in self._read_audit_events()
                  if e.get("action") == tbg.ACTION_NAME]
        self.assertEqual(len(events), 1)
        e = events[0]
        # Verify NO token-text fields snuck in.
        forbidden = {"prompt", "prompt_text", "raw_input", "raw_output",
                     "file_path", "env", "skill_content"}
        leaked = forbidden.intersection(e.keys())
        self.assertEqual(leaked, set(), f"Forbidden fields leaked: {leaked}")
        # Caller-supplied fields must all be in the allowlist.
        caller_keys = set(e.keys()) - {
            "action", "ts", "session_id", "project", "event_schema",
            "tokens_in", "tokens_out", "tokens_total", "hmac", "hmac_error",
        }
        self.assertTrue(
            caller_keys.issubset(tbg.ALLOWED_FIELDS),
            f"caller_keys={caller_keys} not subset of allowlist={tbg.ALLOWED_FIELDS}",
        )


class TestCLIInterface(_TBGTestBase):
    """CLI exit codes + --json schema."""

    def test_check_under_threshold_exit_0(self):
        self._write_estimate("PLAN-083", 1000)
        self._write_audit_event(plan_id="PLAN-083", tokens_in=100, tokens_out=100)
        with mock.patch.object(sys, "stdout", new_callable=StringIO):
            rc = tbg.main(["check", "--plan-id", "PLAN-083"])
        self.assertEqual(rc, 0)

    def test_check_over_threshold_exit_1(self):
        self._write_estimate("PLAN-083", 1000)
        self._write_audit_event(plan_id="PLAN-083", tokens_in=900, tokens_out=100)
        with mock.patch.object(sys, "stdout", new_callable=StringIO):
            rc = tbg.main(["check", "--plan-id", "PLAN-083"])
        self.assertEqual(rc, 1)

    def test_check_json_schema(self):
        self._write_estimate("PLAN-083", 1000)
        self._write_audit_event(plan_id="PLAN-083", tokens_in=900, tokens_out=100)
        with mock.patch.object(sys, "stdout", new_callable=StringIO) as stdout:
            tbg.main(["check", "--plan-id", "PLAN-083", "--json"])
        payload = json.loads(stdout.getvalue())
        # All required keys present.
        for key in ("decision", "reason", "plan_id", "estimate_tokens",
                    "actual_tokens", "ratio_basis_points",
                    "threshold_basis_points", "emitted"):
            self.assertIn(key, payload, f"missing key: {key}")
        self.assertEqual(payload["plan_id"], "PLAN-083")
        self.assertIn(payload["decision"], ("pause", "continue"))
        # No floats in the JSON (canonical_json invariant for downstream consumers).
        self.assertIsInstance(payload["ratio_basis_points"], int)
        self.assertIsInstance(payload["threshold_basis_points"], int)

    def test_check_invalid_threshold_exit_2(self):
        with mock.patch.object(sys, "stderr", new_callable=StringIO):
            rc = tbg.main(["check", "--plan-id", "PLAN-083", "--threshold", "1.5"])
        self.assertEqual(rc, 2)

    def test_check_invalid_plan_id_exit_2(self):
        with mock.patch.object(sys, "stderr", new_callable=StringIO):
            rc = tbg.main(["check", "--plan-id", "../etc/passwd"])
        self.assertEqual(rc, 2)

    def test_auto_pause_hook_always_exits_0(self):
        """Hook fail-open contract: even when over threshold, exit 0; pause
        signaled via stdout JSON only."""
        self._write_estimate("PLAN-083", 1000)
        self._write_audit_event(plan_id="PLAN-083", tokens_in=900, tokens_out=100)
        with mock.patch.object(sys, "stdout", new_callable=StringIO) as stdout:
            rc = tbg.main(["auto-pause-hook", "--plan-id", "PLAN-083"])
        self.assertEqual(rc, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["decision"], "pause")


class TestRatioBasisPointsInteger(_TBGTestBase):
    """ratio_basis_points must be integer (canonical_json no-float invariant)."""

    def test_ratio_emitted_as_integer_basis_points(self):
        self._write_estimate("PLAN-083", 1000)
        self._write_audit_event(plan_id="PLAN-083", tokens_in=875, tokens_out=0)
        verdict = tbg.evaluate("PLAN-083", 0.80)
        self.assertEqual(verdict["ratio_basis_points"], 875)
        self.assertIsInstance(verdict["ratio_basis_points"], int)
        self.assertIsInstance(verdict["threshold_basis_points"], int)
        events = [e for e in self._read_audit_events()
                  if e.get("action") == tbg.ACTION_NAME]
        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0]["ratio_basis_points"], int)


if __name__ == "__main__":
    unittest.main()
