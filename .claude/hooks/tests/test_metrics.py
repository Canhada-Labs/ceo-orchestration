"""Unit tests for _lib/metrics.py — event stream-derived metrics."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


from _lib import metrics  # noqa: E402


def _events(*evs):
    def _fn():
        return iter(evs)
    return _fn


class TestCompute(unittest.TestCase):
    def test_empty_stream(self):
        s = metrics.compute(_events())
        self.assertEqual(s["spawn_total"], 0)
        self.assertEqual(s["events_total"], 0)
        self.assertEqual(s["veto_by_reason_code"], {})

    def test_counts_spawn(self):
        s = metrics.compute(_events(
            {"action": "agent_spawn", "skill": "security-and-auth", "has_profile": True, "has_file_assignment": True, "hook_duration_ms": 12},
            {"action": "agent_spawn", "skill": "security-and-auth", "has_profile": True, "has_file_assignment": True, "hook_duration_ms": 15},
            {"action": "agent_spawn", "skill": "testing-strategy", "has_profile": False, "has_file_assignment": True, "hook_duration_ms": 9},
        ))
        self.assertEqual(s["spawn_total"], 3)
        self.assertEqual(s["spawn_by_skill"]["security-and-auth"], 2)
        self.assertEqual(s["spawn_by_skill"]["testing-strategy"], 1)
        self.assertEqual(s["spawn_compliance_breakdown"]["compliant"], 2)
        self.assertEqual(s["spawn_compliance_breakdown"]["missing_profile"], 1)
        self.assertAlmostEqual(s["spawn_compliance_rate"], 2/3, places=3)

    def test_counts_vetoes_by_reason(self):
        s = metrics.compute(_events(
            {"action": "veto_triggered", "hook": "check_agent_spawn", "reason_code": "missing_skill_content"},
            {"action": "veto_triggered", "hook": "check_agent_spawn", "reason_code": "missing_skill_content"},
            {"action": "veto_triggered", "hook": "check_bash_safety", "reason_code": "dangerous_rm"},
        ))
        self.assertEqual(s["veto_total"], 3)
        self.assertEqual(s["veto_by_hook"]["check_agent_spawn"], 2)
        self.assertEqual(s["veto_by_reason_code"]["missing_skill_content"], 2)
        self.assertEqual(s["veto_by_reason_code"]["dangerous_rm"], 1)

    def test_debate_plan_benchmark_lesson(self):
        s = metrics.compute(_events(
            {"action": "debate_event", "plan_id": "PLAN-004", "round": 1, "agent": "vp-engineering"},
            {"action": "plan_transition", "from_status": "draft", "to_status": "reviewed"},
            {"action": "plan_transition", "from_status": "reviewed", "to_status": "executing"},
            {"action": "benchmark_run", "skill": "security-and-auth", "pass_rate": 0.9},
            {"action": "benchmark_run", "skill": "security-and-auth", "pass_rate": 0.7},
            {"action": "lesson_write", "archetype": "security-engineer", "trigger": "benchmark_fail"},
        ))
        self.assertEqual(s["debate_event_total"], 1)
        self.assertEqual(s["plan_transition_total"], 2)
        self.assertEqual(s["plan_transitions_by_status"]["draft→reviewed"], 1)
        self.assertEqual(s["plan_transitions_by_status"]["reviewed→executing"], 1)
        self.assertEqual(s["benchmark_run_total"], 2)
        self.assertAlmostEqual(s["benchmark_pass_rate_mean"], 0.8, places=3)
        self.assertAlmostEqual(s["benchmark_pass_rate_min"], 0.7, places=3)
        self.assertEqual(s["lesson_write_total"], 1)
        self.assertEqual(s["lesson_by_archetype"]["security-engineer"], 1)

    def test_p95_latency(self):
        # 20 durations; p95 ≈ 19th (0-indexed 18) sorted
        durations = list(range(1, 21))
        events = [{"action": "agent_spawn", "skill": "x", "has_profile": True, "has_file_assignment": True, "hook_duration_ms": d} for d in durations]
        s = metrics.compute(_events(*events))
        self.assertEqual(s["hook_duration_ms_p95"], 19)

    def test_unknown_action_ignored(self):
        s = metrics.compute(_events({"action": "xyz_totally_unknown"}))
        self.assertEqual(s["spawn_total"], 0)
        self.assertEqual(s["events_total"], 1)


class TestHealth(unittest.TestCase):
    def test_healthy_when_no_findings(self):
        snap = metrics.compute(_events())
        h = metrics.health_from_snapshot(snap)
        self.assertEqual(h["status"], "healthy")
        self.assertEqual(h["findings"], [])

    def test_unhealthy_on_low_compliance(self):
        snap = metrics.compute(_events(
            *[{"action": "agent_spawn", "skill": "x", "has_profile": False, "has_file_assignment": False} for _ in range(20)],
            *[{"action": "agent_spawn", "skill": "x", "has_profile": True, "has_file_assignment": True} for _ in range(2)],
        ))
        h = metrics.health_from_snapshot(snap)
        self.assertEqual(h["status"], "unhealthy")
        self.assertTrue(any(f["name"] == "spawn_compliance_rate_low" for f in h["findings"]))

    def test_degraded_on_slow_hooks(self):
        snap = metrics.compute(_events(
            *[{"action": "agent_spawn", "skill": "x", "has_profile": True, "has_file_assignment": True, "hook_duration_ms": 100} for _ in range(30)],
        ))
        h = metrics.health_from_snapshot(snap)
        self.assertEqual(h["status"], "degraded")
        self.assertTrue(any(f["name"] == "hook_duration_p95_high" for f in h["findings"]))

    def test_unhealthy_on_benchmark_below_floor(self):
        snap = metrics.compute(_events(
            {"action": "benchmark_run", "skill": "x", "pass_rate": 0.4},
        ))
        h = metrics.health_from_snapshot(snap)
        self.assertEqual(h["status"], "unhealthy")


if __name__ == "__main__":
    unittest.main()
