"""Unit tests for check_budget.py (PLAN-011 Phase 6, ADR-033).

Covers:
- decide() — under cap / over cap / bypass / rate limit / no plan
- plan resolution from frontmatter (zero / one / many active plans)
- audit-log rollup (null tokens_total, project scoping, plan_id scoping)
- bypass rate-limit window (24h rolling)
- end-to-end via main() with env isolation (TestEnvContext)
- fail-open on malformed stdin / missing audit-log / OS errors
- S5 contract: every test asserts at least one behavior beyond exit code.
"""

from __future__ import annotations

import io
import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

_HOOKS_DIR = Path(__file__).resolve().parent.parent

from _lib import contract as _contract  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402

import check_budget as hk  # noqa: E402


# ---------------------------------------------------------------------------
# decide() — pure function, no I/O
# ---------------------------------------------------------------------------


class TestDecidePure(unittest.TestCase):
    def _base(self, **overrides):
        base = dict(
            plan_id="PLAN-011",
            tokens_used=0,
            max_plan_tokens=1_000_000,
            bypass_requested=False,
            recent_bypass_count=0,
            bypass_max_per_day=10,
            caller_pid=1234,
            session_id="s1",
            project="/tmp/proj",
        )
        base.update(overrides)
        return base

    def test_no_active_plan_skips(self):
        d, effect = hk.decide(**self._base(plan_id=None))
        self.assertTrue(d.allow)
        self.assertIsNone(effect)
        self.assertIsNone(d.system_message)

    def test_under_cap_quiet_allow(self):
        d, effect = hk.decide(**self._base(tokens_used=500_000, max_plan_tokens=1_000_000))
        self.assertTrue(d.allow)
        self.assertIsNone(effect)
        self.assertIsNone(d.system_message)

    def test_at_cap_exact_no_warning(self):
        """Boundary: exactly at cap is still under the threshold."""
        d, effect = hk.decide(**self._base(tokens_used=1_000_000, max_plan_tokens=1_000_000))
        self.assertTrue(d.allow)
        self.assertIsNone(effect)

    def test_over_cap_emits_event_but_allows(self):
        d, effect = hk.decide(**self._base(tokens_used=1_500_000, max_plan_tokens=1_000_000))
        self.assertTrue(d.allow, "Sprint 11 State 0 ALWAYS allows")
        self.assertIsNotNone(effect)
        self.assertEqual(effect["emit"], "budget_exceeded")
        self.assertEqual(effect["tokens_used"], 1_500_000)
        self.assertEqual(effect["cap"], 1_000_000)
        self.assertEqual(effect["scope"], "plan")
        self.assertIn("BUDGET WARNING", d.system_message)
        self.assertIn("PLAN-011", d.system_message)
        self.assertIn("ADR-033", d.system_message)

    def test_bypass_consumes_budget(self):
        d, effect = hk.decide(**self._base(bypass_requested=True, recent_bypass_count=3))
        self.assertTrue(d.allow)
        self.assertEqual(effect["emit"], "budget_bypass_used")
        self.assertEqual(effect["plan_id"], "PLAN-011")
        self.assertEqual(effect["caller_pid"], 1234)
        self.assertIn("BUDGET BYPASS USED", d.system_message)
        self.assertIn("4/10", d.system_message)

    def test_bypass_rate_limit_exhausted_blocks_emit(self):
        """11th bypass in 24h → rate-limit exhausted → breadcrumb, no audit event."""
        d, effect = hk.decide(
            **self._base(
                bypass_requested=True,
                recent_bypass_count=10,  # already at cap
                bypass_max_per_day=10,
            )
        )
        self.assertTrue(d.allow, "State 0 still allows even when rate-limited")
        self.assertIsNotNone(effect)
        self.assertEqual(effect["emit"], "rate_limit_exceeded")
        self.assertIn("RATE LIMIT EXCEEDED", d.system_message)

    def test_bypass_over_limit_count(self):
        """21st bypass with cap=10 → still rate-limited."""
        d, effect = hk.decide(
            **self._base(
                bypass_requested=True,
                recent_bypass_count=20,
                bypass_max_per_day=10,
            )
        )
        self.assertEqual(effect["emit"], "rate_limit_exceeded")

    def test_bypass_ignores_over_cap_spend(self):
        """Bypass short-circuits the over-cap emit path."""
        d, effect = hk.decide(
            **self._base(
                bypass_requested=True,
                recent_bypass_count=0,
                tokens_used=5_000_000,
            )
        )
        self.assertEqual(effect["emit"], "budget_bypass_used")
        self.assertNotIn("WARNING", d.system_message)


# ---------------------------------------------------------------------------
# _env_int / _is_truthy — env var parsing
# ---------------------------------------------------------------------------


class TestEnvParse(unittest.TestCase):
    def test_env_int_default_when_unset(self):
        self.assertEqual(hk._env_int("CEO_X_TEST", 42, env={}), 42)

    def test_env_int_valid(self):
        self.assertEqual(hk._env_int("CEO_X_TEST", 42, env={"CEO_X_TEST": "99"}), 99)

    def test_env_int_rejects_negative(self):
        self.assertEqual(
            hk._env_int("CEO_X_TEST", 42, env={"CEO_X_TEST": "-5"}), 42
        )

    def test_env_int_rejects_nonnumeric(self):
        self.assertEqual(
            hk._env_int("CEO_X_TEST", 42, env={"CEO_X_TEST": "abc"}), 42
        )

    def test_env_int_accepts_zero(self):
        self.assertEqual(
            hk._env_int("CEO_X_TEST", 42, env={"CEO_X_TEST": "0"}), 0
        )

    def test_is_truthy_variants(self):
        for val in ("1", "true", "TRUE", "yes", "on"):
            self.assertTrue(hk._is_truthy("X", env={"X": val}), f"{val!r}")

    def test_is_falsy_variants(self):
        for val in ("", "0", "false", "no", "off", "maybe"):
            self.assertFalse(hk._is_truthy("X", env={"X": val}), f"{val!r}")


# ---------------------------------------------------------------------------
# _active_plan_id — frontmatter scanning
# ---------------------------------------------------------------------------


class TestActivePlanResolution(TestEnvContext):
    def _write_plan(self, name: str, plan_id: str, status: str) -> None:
        self.write_project_file(
            f".claude/plans/{name}",
            f"---\nid: {plan_id}\nstatus: {status}\nowner: CEO\n---\n\n# Body\n",
        )

    def test_single_executing_plan_matches(self):
        self._write_plan("PLAN-011-state-of-the-art.md", "PLAN-011", "executing")
        self.assertEqual(
            hk._active_plan_id(self.project_dir), "PLAN-011"
        )

    def test_single_reviewed_plan_matches(self):
        self._write_plan("PLAN-012-next.md", "PLAN-012", "reviewed")
        self.assertEqual(hk._active_plan_id(self.project_dir), "PLAN-012")

    def test_done_plan_excluded(self):
        self._write_plan("PLAN-010-finished.md", "PLAN-010", "done")
        self.assertIsNone(hk._active_plan_id(self.project_dir))

    def test_two_active_plans_indeterminate(self):
        self._write_plan("PLAN-011-a.md", "PLAN-011", "executing")
        self._write_plan("PLAN-012-b.md", "PLAN-012", "reviewed")
        self.assertIsNone(hk._active_plan_id(self.project_dir))

    def test_no_plans_dir(self):
        self.assertIsNone(hk._active_plan_id(self.project_dir))

    def test_ignores_schema_files(self):
        """PLAN-SCHEMA.md etc. must NOT be treated as plans."""
        self.write_project_file(
            ".claude/plans/PLAN-SCHEMA.md",
            "---\nid: PLAN-SCHEMA\nstatus: executing\n---\n",
        )
        self.assertIsNone(hk._active_plan_id(self.project_dir))

    def test_malformed_frontmatter_skipped(self):
        self.write_project_file(
            ".claude/plans/PLAN-099-broken.md", "no frontmatter at all\n"
        )
        self.assertIsNone(hk._active_plan_id(self.project_dir))

    # _resolve_active_plan — (path, count) drives breadcrumb gating
    def test_resolve_zero_active_returns_count_zero(self):
        self._write_plan("PLAN-010-finished.md", "PLAN-010", "done")
        path, count = hk._resolve_active_plan(self.project_dir)
        self.assertIsNone(path)
        self.assertEqual(count, 0)

    def test_resolve_single_active_returns_count_one(self):
        self._write_plan("PLAN-011-a.md", "PLAN-011", "executing")
        path, count = hk._resolve_active_plan(self.project_dir)
        self.assertIsNotNone(path)
        self.assertEqual(count, 1)

    def test_resolve_two_active_returns_count_two(self):
        self._write_plan("PLAN-011-a.md", "PLAN-011", "executing")
        self._write_plan("PLAN-012-b.md", "PLAN-012", "reviewed")
        path, count = hk._resolve_active_plan(self.project_dir)
        self.assertIsNone(path)
        self.assertEqual(count, 2)

    def test_resolve_no_plans_dir_returns_count_zero(self):
        path, count = hk._resolve_active_plan(self.project_dir)
        self.assertIsNone(path)
        self.assertEqual(count, 0)


# ---------------------------------------------------------------------------
# _plan_tokens_total — rollup from audit-log
# ---------------------------------------------------------------------------


class TestPlanTokensRollup(TestEnvContext):
    def _seed_log(self, lines: list) -> None:
        path = self.audit_dir / "audit-log.jsonl"
        with path.open("a", encoding="utf-8") as f:
            for obj in lines:
                f.write(json.dumps(obj) + "\n")

    def test_empty_log_is_zero(self):
        total, count = hk._plan_tokens_total(
            "PLAN-011", project_dir=str(self.project_dir)
        )
        self.assertEqual(total, 0)
        self.assertEqual(count, 0)

    def test_sums_matching_project(self):
        self._seed_log([
            {
                "action": "agent_spawn",
                "plan_id": "PLAN-011",
                "project": str(self.project_dir),
                "tokens_total": 1200,
            },
            {
                "action": "agent_spawn",
                "plan_id": "PLAN-011",
                "project": str(self.project_dir),
                "tokens_total": 800,
            },
        ])
        total, count = hk._plan_tokens_total(
            "PLAN-011", project_dir=str(self.project_dir)
        )
        self.assertEqual(total, 2000)
        self.assertEqual(count, 2)

    def test_null_tokens_skipped(self):
        self._seed_log([
            {
                "action": "agent_spawn",
                "plan_id": "PLAN-011",
                "project": str(self.project_dir),
                "tokens_total": None,
            },
            {
                "action": "agent_spawn",
                "plan_id": "PLAN-011",
                "project": str(self.project_dir),
                "tokens_total": 500,
            },
        ])
        total, count = hk._plan_tokens_total(
            "PLAN-011", project_dir=str(self.project_dir)
        )
        self.assertEqual(total, 500)
        self.assertEqual(count, 1)

    def test_other_plan_excluded(self):
        self._seed_log([
            {
                "action": "agent_spawn",
                "plan_id": "PLAN-010",
                "project": str(self.project_dir),
                "tokens_total": 9_999_999,
            },
            {
                "action": "agent_spawn",
                "plan_id": "PLAN-011",
                "project": str(self.project_dir),
                "tokens_total": 42,
            },
        ])
        total, count = hk._plan_tokens_total(
            "PLAN-011", project_dir=str(self.project_dir)
        )
        self.assertEqual(total, 42)

    def test_malformed_line_skipped(self):
        path = self.audit_dir / "audit-log.jsonl"
        path.write_text(
            '{"action":"agent_spawn","plan_id":"PLAN-011","tokens_total":100}\n'
            'NOT JSON\n'
            '{"action":"agent_spawn","plan_id":"PLAN-011","tokens_total":50}\n',
            encoding="utf-8",
        )
        total, count = hk._plan_tokens_total(
            "PLAN-011", project_dir=str(self.project_dir)
        )
        self.assertEqual(total, 150)
        self.assertEqual(count, 2)

    def test_legacy_no_plan_id_uses_project(self):
        """Pre-Sprint-11 events lack plan_id; fall back to project scope."""
        self._seed_log([
            {
                "action": "agent_spawn",
                "project": str(self.project_dir),
                "tokens_total": 77,
            },
        ])
        total, _ = hk._plan_tokens_total(
            "PLAN-011", project_dir=str(self.project_dir)
        )
        self.assertEqual(total, 77)


# ---------------------------------------------------------------------------
# _count_recent_bypasses — 24h rolling window
# ---------------------------------------------------------------------------


class TestBypassRateLimit(TestEnvContext):
    def _seed_bypass(self, plan_id: str, *, ts: datetime) -> None:
        path = self.audit_dir / "audit-log.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "action": "budget_bypass_used",
                "plan_id": plan_id,
                "ts": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "caller_pid": 100,
            }) + "\n")

    def test_counts_within_window(self):
        now = datetime.now(timezone.utc)
        for i in range(5):
            self._seed_bypass("PLAN-011", ts=now - timedelta(hours=i * 2))
        self.assertEqual(hk._count_recent_bypasses("PLAN-011"), 5)

    def test_excludes_outside_24h(self):
        now = datetime.now(timezone.utc)
        self._seed_bypass("PLAN-011", ts=now - timedelta(hours=25))
        self._seed_bypass("PLAN-011", ts=now - timedelta(hours=1))
        self.assertEqual(hk._count_recent_bypasses("PLAN-011"), 1)

    def test_different_plan_ignored(self):
        now = datetime.now(timezone.utc)
        self._seed_bypass("PLAN-010", ts=now - timedelta(hours=1))
        self.assertEqual(hk._count_recent_bypasses("PLAN-011"), 0)


# ---------------------------------------------------------------------------
# End-to-end via main() — stdin/stdout, full env isolation
# ---------------------------------------------------------------------------


class TestMainEndToEnd(TestEnvContext):
    def setUp(self) -> None:
        super().setUp()
        # Install one active plan by default.
        self.write_project_file(
            ".claude/plans/PLAN-011-x.md",
            "---\nid: PLAN-011\nstatus: executing\n---\n",
        )

    def _run(self, payload: dict) -> dict:
        stdin_text = json.dumps(payload)
        stdout_buf = io.StringIO()
        with patch.object(sys, "stdin", io.StringIO(stdin_text)):
            with patch.object(sys, "stdout", stdout_buf):
                hk.main()
        return json.loads(stdout_buf.getvalue().strip())

    def test_bad_stdin_allows_fail_open(self):
        stdout_buf = io.StringIO()
        with patch.object(sys, "stdin", io.StringIO("not json at all")):
            with patch.object(sys, "stdout", stdout_buf):
                hk.main()
        obj = json.loads(stdout_buf.getvalue().strip())
        self.assertEqual(obj.get("decision", "allow"), "allow")

    def test_empty_stdin_allows(self):
        stdout_buf = io.StringIO()
        with patch.object(sys, "stdin", io.StringIO("")):
            with patch.object(sys, "stdout", stdout_buf):
                hk.main()
        obj = json.loads(stdout_buf.getvalue().strip())
        self.assertEqual(obj.get("decision", "allow"), "allow")

    def test_non_agent_tool_allows(self):
        obj = self._run({
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        })
        self.assertEqual(obj.get("decision", "allow"), "allow")
        self.assertNotIn("systemMessage", obj)

    def test_under_cap_quiet_allow(self):
        os.environ["CEO_MAX_PLAN_TOKENS"] = "1000000"
        obj = self._run({
            "hook_event_name": "PreToolUse",
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "general-purpose",
                           "description": "test",
                           "prompt": "hi"},
        })
        self.assertEqual(obj.get("decision", "allow"), "allow")

    def test_over_cap_emits_warning(self):
        # Seed audit-log with spawns totaling > cap.
        path = self.audit_dir / "audit-log.jsonl"
        with path.open("w", encoding="utf-8") as f:
            f.write(json.dumps({
                "action": "agent_spawn",
                "plan_id": "PLAN-011",
                "project": str(self.project_dir.resolve()),
                "tokens_total": 500_000,
            }) + "\n")
            f.write(json.dumps({
                "action": "agent_spawn",
                "plan_id": "PLAN-011",
                "project": str(self.project_dir.resolve()),
                "tokens_total": 700_000,
            }) + "\n")
        os.environ["CEO_MAX_PLAN_TOKENS"] = "1000000"
        obj = self._run({
            "hook_event_name": "PreToolUse",
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "x", "description": "y", "prompt": "z"},
        })
        self.assertEqual(obj.get("decision", "allow"), "allow", "State 0 always allows")
        self.assertIn("systemMessage", obj)
        self.assertIn("BUDGET WARNING", obj["systemMessage"])

        # Audit event was emitted.
        audit_text = self.read_audit_log()
        self.assertIn("budget_exceeded", audit_text)

    def test_indeterminate_plan_skips(self):
        # Wipe the single plan; add two active plans.
        plan_file = self.project_dir / ".claude" / "plans" / "PLAN-011-x.md"
        plan_file.unlink()
        self.write_project_file(
            ".claude/plans/PLAN-011-a.md",
            "---\nid: PLAN-011\nstatus: executing\n---\n",
        )
        self.write_project_file(
            ".claude/plans/PLAN-012-b.md",
            "---\nid: PLAN-012\nstatus: reviewed\n---\n",
        )
        obj = self._run({
            "hook_event_name": "PreToolUse",
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "x", "description": "y", "prompt": "z"},
        })
        self.assertEqual(obj.get("decision", "allow"), "allow")
        # Breadcrumb mentions indeterminate AND the ambiguous count.
        errors = self.read_audit_errors()
        self.assertIn("indeterminate", errors)
        self.assertIn("2 active plans", errors)

    def test_no_active_plan_silent_skip(self):
        # Zero active plans is the normal maintenance-mode state (all
        # plans terminal). The hook must allow WITHOUT writing an
        # "indeterminate" breadcrumb — otherwise audit-log.errors floods
        # on every plan-less tool call (noise burndown).
        plan_file = self.project_dir / ".claude" / "plans" / "PLAN-011-x.md"
        plan_file.unlink()
        obj = self._run({
            "hook_event_name": "PreToolUse",
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "x", "description": "y", "prompt": "z"},
        })
        self.assertEqual(obj.get("decision", "allow"), "allow")
        errors = self.read_audit_errors()
        self.assertNotIn("indeterminate", errors)

    def test_bypass_emits_bypass_used(self):
        os.environ["CEO_BUDGET_BYPASS"] = "1"
        os.environ["CEO_MAX_PLAN_TOKENS"] = "1000"
        obj = self._run({
            "hook_event_name": "PreToolUse",
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "x", "description": "y", "prompt": "z"},
        })
        self.assertEqual(obj.get("decision", "allow"), "allow")
        self.assertIn("BUDGET BYPASS USED", obj["systemMessage"])
        audit_text = self.read_audit_log()
        self.assertIn("budget_bypass_used", audit_text)

    def test_bypass_rate_limit_exhausted_warns(self):
        """Seed 10 prior bypasses → 11th attempt logs breadcrumb instead."""
        now = datetime.now(timezone.utc)
        path = self.audit_dir / "audit-log.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for i in range(10):
                f.write(json.dumps({
                    "action": "budget_bypass_used",
                    "plan_id": "PLAN-011",
                    "ts": (now - timedelta(minutes=i * 5)).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                    "caller_pid": 1,
                }) + "\n")
        os.environ["CEO_BUDGET_BYPASS"] = "1"
        os.environ["CEO_BUDGET_BYPASS_MAX_PER_DAY"] = "10"
        obj = self._run({
            "hook_event_name": "PreToolUse",
            "tool_name": "Agent",
            "tool_input": {"subagent_type": "x", "description": "y", "prompt": "z"},
        })
        self.assertEqual(obj.get("decision", "allow"), "allow")
        self.assertIn("RATE LIMIT EXCEEDED", obj["systemMessage"])
        errors = self.read_audit_errors()
        self.assertIn("BYPASS RATE LIMIT", errors)

        # Critically: NO new budget_bypass_used emit for the 11th attempt.
        # Count existing ones stayed at 10.
        post = self.read_audit_log()
        self.assertEqual(post.count("budget_bypass_used"), 10)

    def test_empty_tool_name_still_checks(self):
        """Empty tool_name defaults to Agent path (harness variant)."""
        obj = self._run({
            "hook_event_name": "PreToolUse",
            "tool_name": "",
            "tool_input": {"subagent_type": "x"},
        })
        self.assertEqual(obj.get("decision", "allow"), "allow")


# ---------------------------------------------------------------------------
# Fail-open invariants
# ---------------------------------------------------------------------------


class TestFailOpen(TestEnvContext):
    def test_audit_log_missing_is_zero_spend(self):
        """No audit-log file → rollup returns 0 gracefully."""
        total, _ = hk._plan_tokens_total(
            "PLAN-011", project_dir=str(self.project_dir)
        )
        self.assertEqual(total, 0)


if __name__ == "__main__":
    unittest.main()
