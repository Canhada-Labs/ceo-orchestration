"""PLAN-098 GOAP planner core tests (AC1, AC3, AC4, AC7, AC8, AC10, AC11, AC12, AC13, AC14).

Stdlib-only. Loads the canonical `.claude/scripts/goap-planner.py` via
importlib.util.spec_from_file_location (the file has a hyphen so it cannot
be imported by module name — same pattern as `.claude/scripts/audit-query.py`
loaded by PLAN-096 MCP handlers).

Canonical test path: .claude/hooks/_lib/tests/test_goap_planner.py

Tests:
- test_parse_goal_*  — AC13 deterministic parser + fall-through
- test_search_*      — AC3 + core A* correctness
- test_render_*      — AC4 markdown shape + cap at MAX_TREE_SIZE
- test_replan_*      — AC7 replan-on-failure + MAX_REPLAN_ATTEMPTS
- test_heuristic_admissibility  — AC8 >=200 random state pairs
- test_kill_switch_* — AC10 CEO_GOAP_ADVISORY_ENABLED=0 short-circuit
- test_latency_*     — AC11 p99 cold <= 800ms / warm <= 200ms
- test_cycle_*       — AC12 cyclic action library
- test_baseline_*    — AC14 action-cost-baseline.json path + schema
- test_no_auto_dispatch_in_planner — AC5 plain-text smoke
"""
from __future__ import annotations

import importlib.util
import json
import os
import random
import sys
import time
import unittest
from pathlib import Path

# Canonical test layout: .claude/hooks/_lib/tests/test_X.py -> parents[4] = repo root.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_GOAP_PLANNER_PATH = _REPO_ROOT / ".claude" / "scripts" / "goap-planner.py"


def _load_goap_planner():
    """Load .claude/scripts/goap-planner.py as a module (hyphen-in-filename pattern)."""
    spec = importlib.util.spec_from_file_location("goap_planner", _GOAP_PLANNER_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load goap-planner from {_GOAP_PLANNER_PATH}")
    mod = importlib.util.module_from_spec(spec)
    # Register in sys.modules BEFORE exec_module so dataclasses' frame
    # introspection (sys.modules[cls.__module__].__dict__) finds the
    # module — Python 3.9 dataclass + importlib.util quirk.
    sys.modules["goap_planner"] = mod
    spec.loader.exec_module(mod)
    return mod


goap_planner = _load_goap_planner()


class TestParseGoal(unittest.TestCase):
    """AC13 — deterministic goal parser + fall-through."""

    def test_ship_extracts_done_and_tagged(self):
        preds, status = goap_planner.parse_goal("ship v1.32.0")
        self.assertEqual(status, "ok")
        self.assertEqual(preds, frozenset({"plan_status=done", "tagged=true"}))

    def test_promote_extracts_adr_accepted(self):
        preds, status = goap_planner.parse_goal("promote ADR-132 to ACCEPTED")
        self.assertEqual(status, "ok")
        self.assertIn("adr_status=accepted", preds)

    def test_unknown_verb_returns_failed(self):
        preds, status = goap_planner.parse_goal("frobnicate the widget")
        self.assertEqual(status, "goal-parse-failed")
        self.assertEqual(preds, frozenset())

    def test_empty_returns_failed(self):
        preds, status = goap_planner.parse_goal("")
        self.assertEqual(status, "goal-parse-failed")

    def test_too_long_returns_failed(self):
        text = "ship " + ("x" * (goap_planner.MAX_GOAL_CHARS + 1))
        preds, status = goap_planner.parse_goal(text)
        self.assertEqual(status, "goal-too-long")
        self.assertEqual(preds, frozenset())

    def test_canonical_verbs_all_resolve(self):
        for verb in goap_planner._GOAL_VERBS.keys():
            preds, status = goap_planner.parse_goal(verb)
            self.assertEqual(status, "ok", verb)
            self.assertGreater(len(preds), 0, verb)


class TestSearch(unittest.TestCase):
    """AC3 — A* returns valid plan from start to goal."""

    def setUp(self):
        self.actions, _ = goap_planner.load_action_library()

    def test_search_ship_from_executing(self):
        start = goap_planner.State(predicates=frozenset({"plan_status=executing"}))
        goal = frozenset({"tagged=true"})
        result = goap_planner.search(start, goal, self.actions)
        self.assertEqual(result.status, "ok")
        self.assertGreater(len(result.plan), 0)
        action_ids = [a.id for a in result.plan]
        self.assertIn("tag_release", action_ids)

    def test_search_promote_adr_from_executing(self):
        start = goap_planner.State(predicates=frozenset({"plan_status=executing"}))
        goal = frozenset({"adr_status=accepted"})
        result = goap_planner.search(start, goal, self.actions)
        self.assertEqual(result.status, "ok")
        action_ids = [a.id for a in result.plan]
        self.assertIn("adr_propose", action_ids)
        self.assertIn("adr_promote_to_accepted", action_ids)

    def test_search_returns_no_plan_for_unreachable(self):
        start = goap_planner.State(predicates=frozenset({"plan_status=draft"}))
        goal = frozenset({"impossible_predicate=true"})
        result = goap_planner.search(start, goal, self.actions, max_nodes=20)
        self.assertIn(result.status, ("no_plan", "node_cap", "depth_exceeded"))
        self.assertEqual(len(result.plan), 0)

    def test_search_already_at_goal_returns_empty_plan(self):
        start = goap_planner.State(predicates=frozenset({"plan_status=done", "tagged=true"}))
        goal = frozenset({"tagged=true"})
        result = goap_planner.search(start, goal, self.actions)
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result.plan), 0)


class TestRenderTreeMarkdown(unittest.TestCase):
    """AC4 — tree visualization with pre-cond + effects per node; cap at MAX_TREE_SIZE."""

    def setUp(self):
        self.actions, _ = goap_planner.load_action_library()
        self.start = goap_planner.State(predicates=frozenset({"plan_status=executing"}))
        self.goal = frozenset({"tagged=true"})
        self.result = goap_planner.search(self.start, self.goal, self.actions)

    def test_markdown_has_advisory_banner(self):
        md = goap_planner.render_tree_markdown("ship v1.32.0", self.goal, self.result.plan, self.result)
        self.assertIn("ADVISORY ONLY", md)
        self.assertIn("ADR-132", md)
        self.assertIn("ADR-051", md)

    def test_markdown_has_preconditions_and_effects(self):
        md = goap_planner.render_tree_markdown("ship", self.goal, self.result.plan, self.result)
        self.assertIn("Pre-conditions", md)
        self.assertIn("Effects", md)

    def test_markdown_has_cost_annotations(self):
        md = goap_planner.render_tree_markdown("ship", self.goal, self.result.plan, self.result)
        self.assertIn("cumulative", md)
        self.assertIn("Tokens (k)", md)
        self.assertIn("GPG events", md)

    def test_markdown_truncates_at_max_tree_size(self):
        plan = [self.actions[0]] * (goap_planner.MAX_TREE_SIZE + 10)
        md = goap_planner.render_tree_markdown(
            "synthetic", self.goal, plan,
            goap_planner.SearchResult(status="ok", plan=plan),
        )
        self.assertIn("truncated", md)


class TestReplan(unittest.TestCase):
    """AC7 — replan-on-failure cap = MAX_REPLAN_ATTEMPTS."""

    def setUp(self):
        self.actions, _ = goap_planner.load_action_library()

    def test_replan_succeeds_within_cap(self):
        current = goap_planner.State(predicates=frozenset({
            "plan_status=executing", "code_review=passed",
        }))
        goal = frozenset({"tagged=true"})
        result = goap_planner.replan_from(current, goal, self.actions, attempt=1)
        self.assertEqual(result.status, "ok")

    def test_replan_exhausted_at_cap(self):
        current = goap_planner.State(predicates=frozenset({"plan_status=executing"}))
        goal = frozenset({"tagged=true"})
        result = goap_planner.replan_from(
            current, goal, self.actions, attempt=goap_planner.MAX_REPLAN_ATTEMPTS + 1,
        )
        self.assertEqual(result.status, "no_plan")
        self.assertEqual(result.terminus_reason, "replan_exhausted")

    def test_replan_produces_plan_from_failure_state(self):
        original_start = goap_planner.State(predicates=frozenset({"plan_status=executing"}))
        original_result = goap_planner.search(original_start, frozenset({"tagged=true"}), self.actions)
        self.assertEqual(original_result.status, "ok")
        failure_state = goap_planner.State(predicates=frozenset({
            "plan_status=executing", "research_complete=true",
        }))
        replan_result = goap_planner.replan_from(failure_state, frozenset({"tagged=true"}), self.actions)
        self.assertEqual(replan_result.status, "ok")


class TestHeuristicAdmissibility(unittest.TestCase):
    """AC8 — heuristic admissibility property test on >=200 random state pairs."""

    def test_heuristic_consistent_on_200_random_pairs(self):
        actions, _ = goap_planner.load_action_library()
        rng = random.Random(20260517)

        all_eff_preds = sorted({e for a in actions for e in a.eff if not e.startswith("!")})
        all_goal_pool = [
            frozenset({"tagged=true"}),
            frozenset({"adr_status=accepted"}),
            frozenset({"session_closed=true"}),
            frozenset({"plan_status=done"}),
            frozenset({"plan_status=reviewed"}),
            frozenset({"plan_status=done", "tagged=true"}),
        ]

        n_tested = 0
        for _ in range(500):
            seed_count = rng.randint(0, len(all_eff_preds))
            seed = frozenset(rng.sample(all_eff_preds, seed_count))
            s = goap_planner.State(predicates=seed)
            applicable = [a for a in actions if goap_planner._action_applicable(s, a)]
            if not applicable:
                continue
            a = rng.choice(applicable)
            s_prime = goap_planner._apply_action(s, a)
            goal = rng.choice(all_goal_pool)
            h_s = goap_planner.heuristic(s, goal, actions)
            h_s_prime = goap_planner.heuristic(s_prime, goal, actions)
            c = goap_planner._action_cost(a)
            self.assertLessEqual(
                h_s, c + h_s_prime,
                f"admissibility violated: h(s)={h_s} > c+h(s')={c}+{h_s_prime} on action={a.id}",
            )
            n_tested += 1
            if n_tested >= 200:
                break

        self.assertGreaterEqual(n_tested, 200, f"only {n_tested} valid pairs tested")


class TestKillSwitch(unittest.TestCase):
    """AC10 — CEO_GOAP_ADVISORY_ENABLED=0 short-circuits."""

    def test_disabled_returns_short_circuit(self):
        prior = os.environ.get("CEO_GOAP_ADVISORY_ENABLED")
        os.environ["CEO_GOAP_ADVISORY_ENABLED"] = "0"
        try:
            result = goap_planner.plan_for_goal("ship v1.32.0")
            self.assertEqual(result["status"], "disabled")
            self.assertEqual(result["plan_depth"], 0)
            self.assertIn("disabled", result["tree_markdown"])
        finally:
            if prior is None:
                del os.environ["CEO_GOAP_ADVISORY_ENABLED"]
            else:
                os.environ["CEO_GOAP_ADVISORY_ENABLED"] = prior

    def test_enabled_runs_search(self):
        prior = os.environ.get("CEO_GOAP_ADVISORY_ENABLED")
        os.environ["CEO_GOAP_ADVISORY_ENABLED"] = "1"
        try:
            result = goap_planner.plan_for_goal(
                "ship v1.32.0",
                start=goap_planner.State(predicates=frozenset({"plan_status=executing"})),
            )
            self.assertEqual(result["status"], "ok")
            self.assertGreater(result["plan_depth"], 0)
        finally:
            if prior is None:
                del os.environ["CEO_GOAP_ADVISORY_ENABLED"]
            else:
                os.environ["CEO_GOAP_ADVISORY_ENABLED"] = prior


class TestLatency(unittest.TestCase):
    """AC11 — p99 latency target: 800ms cold / 200ms warm."""

    def test_planner_latency_below_target(self):
        prior = os.environ.get("CEO_GOAP_ADVISORY_ENABLED")
        os.environ["CEO_GOAP_ADVISORY_ENABLED"] = "1"
        try:
            start_t = time.monotonic()
            result = goap_planner.plan_for_goal(
                "ship v1.32.0",
                start=goap_planner.State(predicates=frozenset({"plan_status=executing"})),
            )
            cold_ms = int((time.monotonic() - start_t) * 1000)
            self.assertEqual(result["status"], "ok")
            self.assertLess(cold_ms, 800, f"cold latency {cold_ms}ms > AC11 800ms")

            warm_t = time.monotonic()
            result = goap_planner.plan_for_goal(
                "ship v1.32.0",
                start=goap_planner.State(predicates=frozenset({"plan_status=executing"})),
            )
            warm_ms = int((time.monotonic() - warm_t) * 1000)
            self.assertEqual(result["status"], "ok")
            self.assertLess(warm_ms, 200, f"warm latency {warm_ms}ms > AC11 200ms")
        finally:
            if prior is None:
                del os.environ["CEO_GOAP_ADVISORY_ENABLED"]
            else:
                os.environ["CEO_GOAP_ADVISORY_ENABLED"] = prior


class TestCycleDetection(unittest.TestCase):
    """AC12 — adversarial cyclic action library terminates gracefully."""

    def test_cyclic_actions_terminate(self):
        cyclic = [
            goap_planner.Action(
                id="a_to_b",
                pre=frozenset({"x=a"}),
                eff=frozenset({"x=b"}),
                tokens_k=1, gpg_events=0, wall_clock_s=1,
            ),
            goap_planner.Action(
                id="b_to_a",
                pre=frozenset({"x=b"}),
                eff=frozenset({"x=a"}),
                tokens_k=1, gpg_events=0, wall_clock_s=1,
            ),
        ]
        start = goap_planner.State(predicates=frozenset({"x=a"}))
        goal = frozenset({"x=c"})

        started = time.monotonic()
        result = goap_planner.search(start, goal, cyclic, max_nodes=20, wall_clock_s=1.0)
        elapsed_s = time.monotonic() - started

        self.assertLess(elapsed_s, 2.0, "cyclic search did not terminate quickly")
        self.assertIn(result.status, ("no_plan", "node_cap", "depth_exceeded"))
        self.assertGreaterEqual(result.cycles_rejected, 1)


class TestActionCostBaseline(unittest.TestCase):
    """AC14 — action-cost-baseline.json at canonical path with required keys."""

    def test_baseline_file_exists_and_loads(self):
        path = _REPO_ROOT / ".claude" / "data" / "goap" / "action-cost-baseline.json"
        self.assertTrue(path.exists(), f"action-cost-baseline.json missing at {path}")
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        self.assertIn("actions", raw)
        for action_id in goap_planner._ACTION_SCHEMA:
            self.assertIn(action_id, raw["actions"], action_id)
            entry = raw["actions"][action_id]
            self.assertIn("tokens_k", entry)
            self.assertIn("gpg_events", entry)
            self.assertIn("wall_clock_s", entry)


class TestNoAutoDispatch(unittest.TestCase):
    """AC5 plain-text smoke — planner module does NOT import the Agent tool
    or any spawn machinery. Hook integration test covers full enforcement.
    """

    def test_planner_does_not_reference_spawn_paths(self):
        src = _GOAP_PLANNER_PATH.read_text(encoding="utf-8")
        forbidden = ["tools/Agent", "subprocess.Popen", "agent_spawn(", "/spawn "]
        for needle in forbidden:
            self.assertNotIn(
                needle, src,
                f"planner references {needle!r} — advisory invariant at risk",
            )


if __name__ == "__main__":
    unittest.main()
