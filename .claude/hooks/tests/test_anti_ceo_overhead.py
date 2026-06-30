#!/usr/bin/env python3
"""Tests for check_anti_ceo_overhead.py — PLAN-083 Wave 0a sub-0.5.

Coverage matrix:
  - Each adversarial fixture line individually (positive + negative)
  - Emit budget cap (21st block in 24h suppressed)
  - Override env var bypass + audit emit recorded separately
  - Fail-OPEN on corrupted state file
  - p95 latency bench (1000 events, target ≤50ms)
  - Sec MF-3 whitelist (audit event has ONLY allowed fields)
  - decide() pure-function contract
  - Predicate-priority resolution (P1 > P2 > ... > P5)

Run from repo root::

    python -m unittest .claude.plans.PLAN-083.staging.wave-0a.sub-0-5-anti-ceo-overhead.tests.test_anti_ceo_overhead

Or after canonical promotion to .claude/hooks/::

    cd .claude/hooks && python -m pytest tests/test_anti_ceo_overhead.py -v

Tests use TestEnvContext-equivalent isolation: tempdir for state + env vars.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest import mock

# Resolve the hook module — supports both staging path and canonical path.
_THIS = Path(__file__).resolve()
_STAGING_HOOK = _THIS.parent.parent / "check_anti_ceo_overhead.py"
_CANONICAL_HOOK = (
    _THIS.parent.parent.parent.parent.parent.parent
    / ".claude" / "hooks" / "check_anti_ceo_overhead.py"
)
_HOOK_PATH = _STAGING_HOOK if _STAGING_HOOK.is_file() else _CANONICAL_HOOK


def _load_hook():
    spec = importlib.util.spec_from_file_location(
        "check_anti_ceo_overhead", _HOOK_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_anti_ceo_overhead"] = mod
    spec.loader.exec_module(mod)
    return mod


hook = _load_hook()


# Repo-root location of fixtures (S107-cont-fix: path was `.parent.parent / "fixtures"`
# resolving to `.claude/hooks/fixtures/` which does not exist; fixtures live at
# `.claude/hooks/tests/fixtures/anti_ceo_overhead/` per S106 PLAN-083 Wave 0a layout).
_FIXTURE_DIR = _THIS.parent / "fixtures" / "anti_ceo_overhead"


def _load_fixtures(filename: str) -> List[Dict[str, Any]]:
    """Load ndjson fixture, skipping the header comment line."""
    path = _FIXTURE_DIR / filename
    out: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict) and "_comment_header" in obj:
                continue
            out.append(obj)
    return out


class _TempStateDir:
    """Redirect _project_state_dir() to a tmpdir for test isolation."""

    def __init__(self):
        self.td = tempfile.TemporaryDirectory()
        self.path = Path(self.td.name)

    def __enter__(self):
        self._patcher = mock.patch.object(
            hook, "_project_state_dir", return_value=self.path
        )
        self._patcher.start()
        return self.path

    def __exit__(self, exc_type, exc, tb):
        self._patcher.stop()
        self.td.cleanup()


def _replay_sequence(
    events: List[Dict[str, Any]],
    *,
    override_env: bool = False,
    budget_available: bool = True,
    base_ts: float = 1_000_000.0,
) -> Dict[str, Any]:
    """Replay an ndjson event sequence through decide().

    Returns the FINAL decision + hit. The state dict is threaded through.
    """
    state: Dict[str, Any] = {"events": []}
    final_decision: Dict[str, Any] = {"decision": "allow"}
    final_hit: Optional[Dict[str, Any]] = None
    for ev in events:
        ts = base_ts + float(ev.get("dt", 0))
        decision, state, hit = hook.decide(
            tool_name=ev.get("tool_name", ""),
            tool_input=ev.get("tool_input", {}) or {},
            state=state,
            now=ts,
            override_env=override_env,
            budget_available=budget_available,
        )
        final_decision = decision
        final_hit = hit
    return {"decision": final_decision, "hit": final_hit, "state": state}


# -----------------------------------------------------------------------------
# Adversarial fixture replay tests
# -----------------------------------------------------------------------------

class AdversarialFixturesTest(unittest.TestCase):
    """Each fixture sequence is individually exercised."""

    def test_positive_fixtures_all_block(self):
        fixtures = _load_fixtures("should-block-on-X.ndjson")
        self.assertGreaterEqual(len(fixtures), 8, "need ≥8 positive fixtures")
        for fx in fixtures:
            with self.subTest(name=fx["name"]):
                result = _replay_sequence(fx["events"])
                self.assertEqual(
                    result["decision"].get("decision", "allow"),
                    "block",
                    f"fixture {fx['name']!r} must block but didn't: {result['decision']}",
                )
                self.assertIsNotNone(result["hit"], "hit must not be None")
                self.assertEqual(
                    result["hit"]["anti_pattern_id"],
                    fx["expected_anti_pattern_id"],
                )

    def test_negative_fixtures_none_block(self):
        fixtures = _load_fixtures("should-NOT-block-on-Y.ndjson")
        self.assertGreaterEqual(len(fixtures), 12, "need ≥12 negative fixtures")
        for fx in fixtures:
            with self.subTest(name=fx["name"]):
                result = _replay_sequence(fx["events"])
                self.assertEqual(
                    result["decision"].get("decision", "allow"),
                    "allow",
                    f"fixture {fx['name']!r} must allow but blocked: {result['decision']}",
                )

    def test_positive_fixture_count_at_least_8(self):
        fixtures = _load_fixtures("should-block-on-X.ndjson")
        self.assertGreaterEqual(len(fixtures), 8)

    def test_negative_fixture_count_at_least_12(self):
        fixtures = _load_fixtures("should-NOT-block-on-Y.ndjson")
        self.assertGreaterEqual(len(fixtures), 12)


# -----------------------------------------------------------------------------
# Predicate-specific unit tests
# -----------------------------------------------------------------------------

class PredicateTest(unittest.TestCase):
    def test_P1_three_distinct_skill_reads_fires(self):
        evs = [
            {"dt": 0, "tool_name": "Read", "tool_input": {
                "file_path": "/r/.claude/skills/core/a/SKILL.md"}},
            {"dt": 10, "tool_name": "Read", "tool_input": {
                "file_path": "/r/.claude/skills/core/b/SKILL.md"}},
            {"dt": 20, "tool_name": "Read", "tool_input": {
                "file_path": "/r/.claude/skills/core/c/SKILL.md"}},
        ]
        r = _replay_sequence(evs)
        self.assertEqual(r["hit"]["anti_pattern_id"], "P1_sequential_skill_reads")

    def test_P1_same_skill_three_times_does_not_fire(self):
        evs = [
            {"dt": i, "tool_name": "Read", "tool_input": {
                "file_path": "/r/.claude/skills/core/a/SKILL.md"}}
            for i in (0, 5, 10)
        ]
        r = _replay_sequence(evs)
        self.assertEqual(r["decision"].get("decision", "allow"), "allow")

    def test_P2_three_unrelated_edits_fires(self):
        evs = [
            {"dt": 0, "tool_name": "Edit", "tool_input": {"file_path": "/r/foo/a.py"}},
            {"dt": 5, "tool_name": "Edit", "tool_input": {"file_path": "/r/bar/b.py"}},
            {"dt": 10, "tool_name": "Edit", "tool_input": {"file_path": "/r/baz/c.py"}},
        ]
        r = _replay_sequence(evs)
        self.assertEqual(r["hit"]["anti_pattern_id"], "P2_unrelated_file_edits")

    def test_P2_related_edits_do_not_fire(self):
        evs = [
            {"dt": i, "tool_name": "Edit", "tool_input": {
                "file_path": f"/r/src/foo/m{i}.py"}}
            for i in (0, 5, 10)
        ]
        r = _replay_sequence(evs)
        self.assertEqual(r["decision"].get("decision", "allow"), "allow")

    def test_P3_two_unrelated_configs_fires(self):
        evs = [
            {"dt": 0, "tool_name": "Write", "tool_input": {
                "file_path": "/r/.github/workflows/release.yaml"}},
            {"dt": 30, "tool_name": "Write", "tool_input": {
                "file_path": "/r/.claude/policies/cap-table.yaml"}},
        ]
        r = _replay_sequence(evs)
        self.assertEqual(r["hit"]["anti_pattern_id"], "P3_config_serial_authoring")

    def test_P4_four_distinct_grep_fires(self):
        evs = [
            {"dt": 0, "tool_name": "Bash", "tool_input": {"command": "grep foo a.py"}},
            {"dt": 5, "tool_name": "Bash", "tool_input": {"command": "find . -name x.yaml"}},
            {"dt": 10, "tool_name": "Bash", "tool_input": {"command": "rg async docs/"}},
            {"dt": 15, "tool_name": "Bash", "tool_input": {"command": "grep TODO README.md"}},
        ]
        r = _replay_sequence(evs)
        self.assertEqual(r["hit"]["anti_pattern_id"], "P4_independent_grep_find_spam")

    def test_P4_jaccard_dedupes_similar_greps(self):
        # 4 grep commands very similar -> jaccard ≥0.5 collapses them
        evs = [
            {"dt": 0, "tool_name": "Bash", "tool_input": {
                "command": "grep audit_emit register PLAN src/"}},
            {"dt": 5, "tool_name": "Bash", "tool_input": {
                "command": "grep audit_emit register PLAN-083 src/"}},
            {"dt": 10, "tool_name": "Bash", "tool_input": {
                "command": "grep audit_emit register PLAN-083 hook src/"}},
            {"dt": 15, "tool_name": "Bash", "tool_input": {
                "command": "grep audit_emit register PLAN-083 hook check src/"}},
        ]
        r = _replay_sequence(evs)
        self.assertEqual(r["decision"].get("decision", "allow"), "allow")

    def test_P5_three_cross_module_tests_fires(self):
        evs = [
            {"dt": 0, "tool_name": "Write", "tool_input": {
                "file_path": "/r/src/foo/test_foo.py"}},
            {"dt": 10, "tool_name": "Write", "tool_input": {
                "file_path": "/r/backend/tests/test_bar.py"}},
            {"dt": 20, "tool_name": "Write", "tool_input": {
                "file_path": "/r/frontend/components/button.test.tsx"}},
        ]
        r = _replay_sequence(evs)
        self.assertEqual(r["hit"]["anti_pattern_id"], "P5_cross_module_test_authoring")


# -----------------------------------------------------------------------------
# Window pruning + sliding semantics
# -----------------------------------------------------------------------------

class WindowTest(unittest.TestCase):
    def test_events_outside_5min_pruned(self):
        evs = [
            {"dt": 0, "tool_name": "Read", "tool_input": {
                "file_path": "/r/.claude/skills/core/a/SKILL.md"}},
            {"dt": 350, "tool_name": "Read", "tool_input": {
                "file_path": "/r/.claude/skills/core/b/SKILL.md"}},
            {"dt": 700, "tool_name": "Read", "tool_input": {
                "file_path": "/r/.claude/skills/core/c/SKILL.md"}},
        ]
        r = _replay_sequence(evs)
        self.assertEqual(r["decision"].get("decision", "allow"), "allow",
                         "events spaced >5min apart must NOT trigger predicates")

    def test_max_state_entries_bounded(self):
        state = {"events": []}
        now = 1_000_000.0
        for i in range(500):
            hook._record_event(
                state,
                {"kind": "edit_unrelated", "file_path": f"/r/foo/{i}.py",
                 "parent_2": f"r/foo-{i}", "ts": now + i * 0.1},
                now + i * 0.1,
            )
        self.assertLessEqual(len(state["events"]), hook.MAX_STATE_ENTRIES)


# -----------------------------------------------------------------------------
# Emit budget enforcement
# -----------------------------------------------------------------------------

class EmitBudgetTest(unittest.TestCase):
    def test_under_budget_block_returned(self):
        evs = [
            {"dt": 0, "tool_name": "Read", "tool_input": {
                "file_path": "/r/.claude/skills/core/a/SKILL.md"}},
            {"dt": 5, "tool_name": "Read", "tool_input": {
                "file_path": "/r/.claude/skills/core/b/SKILL.md"}},
            {"dt": 10, "tool_name": "Read", "tool_input": {
                "file_path": "/r/.claude/skills/core/c/SKILL.md"}},
        ]
        r = _replay_sequence(evs, budget_available=True)
        self.assertEqual(r["decision"].get("decision", "allow"), "block")

    def test_over_budget_degrades_to_advisory(self):
        evs = [
            {"dt": 0, "tool_name": "Read", "tool_input": {
                "file_path": "/r/.claude/skills/core/a/SKILL.md"}},
            {"dt": 5, "tool_name": "Read", "tool_input": {
                "file_path": "/r/.claude/skills/core/b/SKILL.md"}},
            {"dt": 10, "tool_name": "Read", "tool_input": {
                "file_path": "/r/.claude/skills/core/c/SKILL.md"}},
        ]
        r = _replay_sequence(evs, budget_available=False)
        self.assertEqual(r["decision"].get("decision", "allow"), "allow")
        self.assertIn("emit budget exhausted", r["decision"]["systemMessage"])

    def test_emit_budget_dry_check_returns_count(self):
        with _TempStateDir():
            now = time.time()
            ok, count = hook._check_emit_budget_dry(now)
            self.assertTrue(ok)
            self.assertEqual(count, 0)

    def test_emit_budget_caps_at_20(self):
        with _TempStateDir():
            now = time.time()
            # Pre-populate budget file with 20 timestamps within window
            for _ in range(20):
                hook._check_emit_budget(now)
            ok, count = hook._check_emit_budget_dry(now)
            self.assertFalse(ok)
            self.assertEqual(count, 20)

    def test_emit_budget_prunes_outside_24h(self):
        with _TempStateDir():
            now = time.time()
            # Stale entries (>24h ago) should be pruned
            stale_ts = now - (25 * 60 * 60)
            hook._save_emit_budget(hook._emit_budget_path(), [stale_ts] * 25)
            ok, count = hook._check_emit_budget_dry(now)
            self.assertTrue(ok)
            self.assertEqual(count, 0)


# -----------------------------------------------------------------------------
# Override env var
# -----------------------------------------------------------------------------

class OverrideTest(unittest.TestCase):
    def test_override_allows_with_advisory_message(self):
        evs = [
            {"dt": 0, "tool_name": "Read", "tool_input": {
                "file_path": "/r/.claude/skills/core/a/SKILL.md"}},
            {"dt": 5, "tool_name": "Read", "tool_input": {
                "file_path": "/r/.claude/skills/core/b/SKILL.md"}},
            {"dt": 10, "tool_name": "Read", "tool_input": {
                "file_path": "/r/.claude/skills/core/c/SKILL.md"}},
        ]
        r = _replay_sequence(evs, override_env=True)
        self.assertEqual(r["decision"].get("decision", "allow"), "allow")
        self.assertIn("override acked", r["decision"]["systemMessage"])
        self.assertIsNotNone(r["hit"])

    def test_override_main_emits_override_audit(self):
        """The main() path should emit anti_ceo_overhead_override_used (smoke)."""
        # Quick smoke without _AUDIT_EMIT_AVAILABLE — just verify the helper
        # is wired and tolerates missing audit_emit.
        with mock.patch.object(hook, "_AUDIT_EMIT_AVAILABLE", False):
            hook._safe_emit_override(
                anti_pattern_id="P1_sequential_skill_reads",
                session_id="s1",
            )  # must not raise


# -----------------------------------------------------------------------------
# Fail-OPEN on infra errors
# -----------------------------------------------------------------------------

class FailOpenTest(unittest.TestCase):
    def test_corrupted_state_file_falls_back_to_empty(self):
        with _TempStateDir() as td:
            bad = td / "ceo-overhead-window.json"
            bad.write_text("{not valid json", encoding="utf-8")
            state = hook._load_state(bad)
            self.assertEqual(state, {"events": []})

    def test_corrupted_budget_file_returns_empty_list(self):
        with _TempStateDir() as td:
            bad = td / "ceo-overhead-emit-budget.json"
            bad.write_text("{not valid json", encoding="utf-8")
            ts_list = hook._load_emit_budget(bad)
            self.assertEqual(ts_list, [])

    def test_decide_unknown_tool_returns_allow(self):
        state = {"events": []}
        decision, _, hit = hook.decide(
            tool_name="MysteryTool",
            tool_input={"foo": "bar"},
            state=state,
            now=time.time(),
        )
        self.assertEqual(decision.get("decision", "allow"), "allow")
        self.assertIsNone(hit)

    def test_decide_missing_file_path_returns_allow(self):
        state = {"events": []}
        decision, _, hit = hook.decide(
            tool_name="Read",
            tool_input={},
            state=state,
            now=time.time(),
        )
        self.assertEqual(decision.get("decision", "allow"), "allow")

    def test_kill_switch_env_short_circuits(self):
        # Smoke test the env-var pathway via main()
        with mock.patch.dict(os.environ, {"CEO_ANTI_OVERHEAD": "0"}, clear=False):
            with _TempStateDir():
                # Inject empty stdin
                with mock.patch.object(sys, "stdin", _make_stdin('{"tool_name":"Read"}')):
                    captured = _CaptureStdout()
                    with captured:
                        rc = hook.main()
                self.assertEqual(rc, 0)
                out = captured.text.strip()
                self.assertEqual(json.loads(out), {})


# -----------------------------------------------------------------------------
# Performance budget
# -----------------------------------------------------------------------------

class LatencyTest(unittest.TestCase):
    def test_p95_under_50ms_on_1000_events(self):
        """Bench: 1000 mixed events, p95 latency ≤50ms."""
        samples = []
        state = {"events": []}
        now = 1_000_000.0
        for i in range(1000):
            ts = now + i * 0.5
            tool_name = "Read" if i % 3 == 0 else "Edit"
            file_path = (
                f"/r/.claude/skills/core/skill_{i}/SKILL.md"
                if tool_name == "Read"
                else f"/r/src/mod_{i % 50}/file_{i}.py"
            )
            t0 = time.perf_counter_ns()
            _ = hook.decide(
                tool_name=tool_name,
                tool_input={"file_path": file_path},
                state=state,
                now=ts,
                override_env=False,
                budget_available=True,
            )
            elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
            samples.append(elapsed_ms)
        samples.sort()
        p95 = samples[int(0.95 * len(samples))]
        # Budget per Perf P0-3 = 50ms. Loose CI margin.
        self.assertLess(p95, 50.0, f"p95 latency {p95:.3f}ms exceeded 50ms budget")


# -----------------------------------------------------------------------------
# Sec MF-3 whitelist (audit event must NEVER contain tool input content)
# -----------------------------------------------------------------------------

class SecMF3WhitelistTest(unittest.TestCase):
    def test_emit_block_only_contains_whitelisted_fields(self):
        """Verify the helper passes ONLY {anti_pattern_id, count_in_window,
        override_recommended_subagent_type} as caller fields."""
        captured: Dict[str, Any] = {}

        def fake_emit_generic(action, **kwargs):
            captured["action"] = action
            captured.update(kwargs)

        with mock.patch.object(hook, "_AUDIT_EMIT_AVAILABLE", True):
            fake_mod = mock.MagicMock()
            fake_mod.emit_generic = fake_emit_generic
            with mock.patch.object(hook, "_audit_emit", fake_mod):
                hook._safe_emit_block(
                    anti_pattern_id="P1_sequential_skill_reads",
                    count_in_window=3,
                    override_recommended_subagent_type="general-purpose",
                    session_id="s1",
                )
        self.assertEqual(captured["action"], "anti_ceo_overhead_block")
        # Only forensic keys + session/project baseline
        allowed_keys = {
            "action",  # captured separately
            "session_id",
            "anti_pattern_id",
            "count_in_window",
            "override_recommended_subagent_type",
            "project",
        }
        leaked = set(captured.keys()) - allowed_keys
        self.assertFalse(leaked, f"caller leaked fields: {leaked}")
        # NEVER persist tool_input content
        self.assertNotIn("file_path", captured)
        self.assertNotIn("command", captured)
        self.assertNotIn("tool_input", captured)
        self.assertNotIn("prompt", captured)

    def test_emit_override_only_contains_whitelisted_fields(self):
        captured: Dict[str, Any] = {}

        def fake_emit_generic(action, **kwargs):
            captured["action"] = action
            captured.update(kwargs)

        with mock.patch.object(hook, "_AUDIT_EMIT_AVAILABLE", True):
            fake_mod = mock.MagicMock()
            fake_mod.emit_generic = fake_emit_generic
            with mock.patch.object(hook, "_audit_emit", fake_mod):
                hook._safe_emit_override(
                    anti_pattern_id="P2_unrelated_file_edits",
                    session_id="s2",
                )
        self.assertEqual(captured["action"], "anti_ceo_overhead_override_used")
        allowed_keys = {"action", "session_id", "anti_pattern_id", "project"}
        leaked = set(captured.keys()) - allowed_keys
        self.assertFalse(leaked, f"override emit leaked fields: {leaked}")


# -----------------------------------------------------------------------------
# Priority resolution
# -----------------------------------------------------------------------------

class PriorityTest(unittest.TestCase):
    def test_P1_fires_before_P2(self):
        # Mix: 3 skill reads (P1) + 3 unrelated edits (P2) in same window.
        evs = [
            {"dt": 0, "tool_name": "Read", "tool_input": {
                "file_path": "/r/.claude/skills/core/a/SKILL.md"}},
            {"dt": 1, "tool_name": "Edit", "tool_input": {"file_path": "/r/foo/a.py"}},
            {"dt": 2, "tool_name": "Read", "tool_input": {
                "file_path": "/r/.claude/skills/core/b/SKILL.md"}},
            {"dt": 3, "tool_name": "Edit", "tool_input": {"file_path": "/r/bar/b.py"}},
            {"dt": 4, "tool_name": "Read", "tool_input": {
                "file_path": "/r/.claude/skills/core/c/SKILL.md"}},
            {"dt": 5, "tool_name": "Edit", "tool_input": {"file_path": "/r/baz/c.py"}},
        ]
        r = _replay_sequence(evs)
        self.assertEqual(r["hit"]["anti_pattern_id"], "P1_sequential_skill_reads")


# -----------------------------------------------------------------------------
# Helper plumbing
# -----------------------------------------------------------------------------

class _CaptureStdout:
    def __init__(self):
        self._orig = None
        self._buf = None

    def __enter__(self):
        from io import StringIO
        self._orig = sys.stdout
        self._buf = StringIO()
        sys.stdout = self._buf
        return self

    def __exit__(self, exc_type, exc, tb):
        sys.stdout = self._orig

    @property
    def text(self) -> str:
        return self._buf.getvalue() if self._buf else ""


def _make_stdin(text: str):
    from io import StringIO
    return StringIO(text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
