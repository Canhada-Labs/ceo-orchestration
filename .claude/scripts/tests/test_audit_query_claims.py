"""Tests for `audit-query.py claims` sub-command (PLAN-008 Phase 2, ADR-018)."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
_AQ_PATH = _SCRIPTS_DIR / "audit-query.py"
_spec = importlib.util.spec_from_file_location("audit_query", _AQ_PATH)
_aq = importlib.util.module_from_spec(_spec)
sys.modules["audit_query"] = _aq
_spec.loader.exec_module(_aq)


class TestCmdClaims(unittest.TestCase):
    def _args(self, **overrides):
        args = types.SimpleNamespace(kind=None, agent=None, failed_only=False)
        for k, v in overrides.items():
            setattr(args, k, v)
        return args

    def _make_entries(self):
        return [
            {
                "action": "confidence_gate",
                "ts": "2026-04-13T10:00:00Z",
                "claim_count": 5,
                "pass_count": 4,
                "fail_count": 1,
                "verifier_kind_counts": {"path_exists": 3, "function_exists": 2},
                "agent_name": "Staff Backend",
                "source": "stdin",
            },
            {
                "action": "confidence_gate",
                "ts": "2026-04-13T11:00:00Z",
                "claim_count": 3,
                "pass_count": 3,
                "fail_count": 0,
                "verifier_kind_counts": {"path_exists": 3},
                "agent_name": "VP Engineering",
                "source": "stdin",
            },
            # non-matching event
            {"action": "agent_spawn", "claim_count": 999},
        ]

    def test_aggregates_totals(self):
        out = _aq.cmd_claims(self._make_entries(), self._args())
        self.assertEqual(out["event_count"], 2)
        self.assertEqual(out["claim_count"], 8)
        self.assertEqual(out["pass_count"], 7)
        self.assertEqual(out["fail_count"], 1)
        self.assertAlmostEqual(out["failure_rate"], 1 / 8)

    def test_per_kind_aggregation(self):
        out = _aq.cmd_claims(self._make_entries(), self._args())
        self.assertEqual(out["per_kind"]["path_exists"]["total"], 6)
        self.assertEqual(out["per_kind"]["path_exists"]["events"], 2)
        self.assertEqual(out["per_kind"]["function_exists"]["total"], 2)

    def test_per_agent_aggregation(self):
        out = _aq.cmd_claims(self._make_entries(), self._args())
        self.assertEqual(out["per_agent"]["Staff Backend"]["events"], 1)
        self.assertEqual(out["per_agent"]["Staff Backend"]["fail"], 1)
        self.assertEqual(out["per_agent"]["VP Engineering"]["pass"], 3)

    def test_failed_only_filter(self):
        out = _aq.cmd_claims(self._make_entries(), self._args(failed_only=True))
        self.assertEqual(out["event_count"], 1)
        self.assertEqual(out["fail_count"], 1)

    def test_agent_filter(self):
        out = _aq.cmd_claims(self._make_entries(), self._args(agent="VP Engineering"))
        self.assertEqual(out["event_count"], 1)

    def test_kind_filter(self):
        out = _aq.cmd_claims(self._make_entries(), self._args(kind="function_exists"))
        self.assertEqual(out["event_count"], 1)

    def test_empty_log_returns_zero_but_no_division_error(self):
        out = _aq.cmd_claims([], self._args())
        self.assertEqual(out["event_count"], 0)
        self.assertIsNone(out["failure_rate"])


if __name__ == "__main__":
    unittest.main()
