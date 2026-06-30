"""Tests for `audit-query.py tokens` sub-command.

PLAN-006 Phase 5a (ADR-016).
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent

# Load audit-query.py as a module
_AQ_PATH = _SCRIPTS_DIR / "audit-query.py"
_spec = importlib.util.spec_from_file_location("audit_query", _AQ_PATH)
_aq = importlib.util.module_from_spec(_spec)
sys.modules["audit_query"] = _aq
_spec.loader.exec_module(_aq)


class TestCmdTokens(unittest.TestCase):
    def _make_entries(self):
        return [
            {
                "action": "agent_spawn",
                "ts": "2026-04-13T10:00:00Z",
                "skill": "architecture-decisions",
                "subagent_type": "general-purpose",
                "tokens_in": 1000,
                "tokens_out": 500,
            },
            {
                "action": "agent_spawn",
                "ts": "2026-04-13T12:00:00Z",
                "skill": "architecture-decisions",
                "subagent_type": "general-purpose",
                "tokens_in": 2000,
                "tokens_out": 800,
            },
            {
                "action": "agent_spawn",
                "ts": "2026-04-14T09:00:00Z",
                "skill": "public-api-design",
                "subagent_type": "general-purpose",
                "tokens_in": 500,
                "tokens_out": 300,
            },
            # No tokens fields (older emitter)
            {
                "action": "agent_spawn",
                "ts": "2026-04-12T15:00:00Z",
                "skill": "devops-ci-cd",
                "subagent_type": "general-purpose",
            },
            # Non-spawn event ignored
            {"action": "debate_event", "tokens_in": 99999, "tokens_out": 99999},
        ]

    def test_totals_sums_only_integer_values(self):
        result = _aq.cmd_tokens(self._make_entries(), args=None)
        t = result["totals"]
        self.assertEqual(t["tokens_in"], 3500)
        self.assertEqual(t["tokens_out"], 1600)
        self.assertEqual(t["tokens_total"], 5100)
        self.assertEqual(t["spawns_with_tokens"], 3)
        self.assertEqual(t["spawns_without_tokens"], 1)

    def test_per_skill_grouping(self):
        result = _aq.cmd_tokens(self._make_entries(), args=None)
        arch = result["per_skill"]["architecture-decisions"]
        self.assertEqual(arch["tokens_in"], 3000)
        self.assertEqual(arch["tokens_out"], 1300)
        self.assertEqual(arch["spawns"], 2)

    def test_per_day_grouping(self):
        result = _aq.cmd_tokens(self._make_entries(), args=None)
        self.assertEqual(result["per_day"]["2026-04-13"]["spawns"], 2)
        self.assertEqual(result["per_day"]["2026-04-14"]["spawns"], 1)
        self.assertEqual(result["per_day"]["2026-04-12"]["spawns"], 1)

    def test_non_spawn_events_ignored(self):
        """debate_event with tokens fields must not pollute totals."""
        result = _aq.cmd_tokens(self._make_entries(), args=None)
        self.assertLess(result["totals"]["tokens_in"], 90000)

    def test_empty_entries(self):
        result = _aq.cmd_tokens([], args=None)
        self.assertEqual(result["totals"]["tokens_in"], 0)
        self.assertEqual(result["totals"]["tokens_out"], 0)
        self.assertEqual(result["totals"]["spawns_with_tokens"], 0)
        self.assertEqual(result["totals"]["spawns_without_tokens"], 0)

    def test_null_tokens_counted_as_without(self):
        entries = [
            {"action": "agent_spawn", "ts": "2026-04-13T10:00:00Z",
             "tokens_in": None, "tokens_out": None},
        ]
        result = _aq.cmd_tokens(entries, args=None)
        self.assertEqual(result["totals"]["spawns_without_tokens"], 1)
        self.assertEqual(result["totals"]["spawns_with_tokens"], 0)


if __name__ == "__main__":
    unittest.main()
