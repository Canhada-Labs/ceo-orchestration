"""Policy-engine mutation harness — PLAN-014 Phase A.6.

Runs every mutation under ``tests/mutations/`` in-process and asserts:

1. for engine mutations: at least one of the listed TARGETS fails (the
   existing test corpus kills the mutation);
2. for policy mutations: replaying the fixture JSONL against the mutated
   YAML produces ≥1 ``(decision, reason)`` tuple that differs from the
   un-mutated baseline.

``TestMutationKillRateGate`` fails with the full list of surviving
mutations if kill-rate < 100 %.

Design notes
------------

* **In-process** — pytest-subprocess-per-mutation was too slow. The
  harness imports ``_lib.policy``, calls ``mutation.apply(policy_mod)``,
  runs the targets, then invokes the returned ``revert()``. Each
  mutation is fully isolated.
* **Engine tests are unittest.TestCase subclasses** — the harness
  instantiates a dynamic subclass, drives setUp/tearDown, captures the
  first failure per target.
* **Policy mutations** load the mutated YAML via ``_lib.policy.load``
  through a tmpfile and replay the matching ``.fixtures.jsonl`` corpus.
  Un-mutated baseline is loaded once per module load.
* **TestEnvContext** subclass for env isolation per ADJ-028.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List, Tuple

_HOOKS_DIR = Path(__file__).resolve().parent.parent

# Make .claude/hooks/tests/ importable so we can resolve target classes.
_TESTS_DIR = Path(__file__).resolve().parent

from _lib.testing import TestEnvContext  # noqa: E402
from _lib import policy as _policy  # noqa: E402


_REPO_ROOT = _HOOKS_DIR.parent.parent
_POLICIES_DIR = _REPO_ROOT / ".claude" / "policies"
_FIXTURES_DIR = _POLICIES_DIR / "fixtures"
_ENGINE_MUT_DIR = _TESTS_DIR / "mutations" / "engine_mutations"
_POLICY_MUT_DIR = _TESTS_DIR / "mutations" / "policy_mutations"


# ---------------------------------------------------------------------------
# Mutation discovery
# ---------------------------------------------------------------------------


def _discover(pkg_dir: Path) -> List[Tuple[str, Any]]:
    """Import every ``mutation_*.py`` in pkg_dir; return [(name, module)]."""
    out = []
    for path in sorted(pkg_dir.glob("mutation_*.py")):
        name = path.stem
        spec = importlib.util.spec_from_file_location(
            f"_mutations.{pkg_dir.name}.{name}", path
        )
        if spec is None or spec.loader is None:
            continue
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        out.append((name, mod))
    return out


_ENGINE_MUTATIONS = _discover(_ENGINE_MUT_DIR)
_POLICY_MUTATIONS = _discover(_POLICY_MUT_DIR)


# ---------------------------------------------------------------------------
# Target resolution — lazy import of test_policy_engine once
# ---------------------------------------------------------------------------


def _import_target_module() -> Any:
    # Re-import fresh so the class bodies pick up any module-level patches.
    if "test_policy_engine" in sys.modules:
        # Keep the already-imported module; its tests use ``_lib.policy`` via
        # the module binding ``P``, which we patch at module level.
        return sys.modules["test_policy_engine"]
    import test_policy_engine  # noqa: E402
    return test_policy_engine


def _resolve_target(node_id: str):
    """``test_policy_engine.py::Class::method`` -> (Class, method_name)."""
    # Accept both ``file::Class::method`` and ``Class::method``
    parts = node_id.split("::")
    if len(parts) == 3:
        _file, cls_name, meth_name = parts
    elif len(parts) == 2:
        cls_name, meth_name = parts
    else:
        raise ValueError(f"unparseable target: {node_id!r}")
    mod = _import_target_module()
    cls = getattr(mod, cls_name, None)
    if cls is None:
        raise AttributeError(f"class {cls_name} not found in test_policy_engine")
    return cls, meth_name


def _run_target(node_id: str) -> Tuple[bool, str]:
    """Instantiate + run a single unittest test method.

    Returns ``(passed, detail)``; ``passed=False`` means the mutation killed
    the test (either via AssertionError or unexpected exception).
    """
    try:
        cls, meth = _resolve_target(node_id)
    except Exception as e:
        return False, f"resolve-failed: {e}"
    inst = cls(meth)
    result = unittest.TestResult()
    try:
        inst.run(result)
    except Exception as e:
        return False, f"run-crash: {e}"
    if result.failures or result.errors:
        detail = ""
        if result.failures:
            detail = result.failures[0][1].splitlines()[-1] if result.failures[0][1] else "failure"
        elif result.errors:
            detail = result.errors[0][1].splitlines()[-1] if result.errors[0][1] else "error"
        return False, detail
    return True, "ok"


# ---------------------------------------------------------------------------
# Policy-mutation fixture runner
# ---------------------------------------------------------------------------


def _load_fixtures(fixture_file: str) -> List[Dict[str, Any]]:
    path = _FIXTURES_DIR / fixture_file
    entries = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entries.append(json.loads(line))
    return entries


def _baseline_decisions(policy_slug: str) -> List[Tuple[str, Any]]:
    """Run the un-mutated policy against its fixture corpus. Returns list of
    (decision, reason) tuples aligned with fixture order.
    """
    policy_path = _POLICIES_DIR / f"{policy_slug}.policy.yaml"
    pol = _policy.load(policy_path)
    fixture_file = f"{policy_slug}.fixtures.jsonl"
    out = []
    for entry in _load_fixtures(fixture_file):
        d = pol.decide(entry["input"])
        out.append((d["decision"], d.get("reason")))
    return out


_POLICY_BASELINES: Dict[str, List[Tuple[str, Any]]] = {
    "bash-safety": _baseline_decisions("bash-safety"),
    "plan-edit": _baseline_decisions("plan-edit"),
}


def _run_policy_mutation(mod: Any, project_dir: Path) -> Tuple[bool, str]:
    """Write POLICY_YAML to a tmpfile, load it, run fixtures, compare vs baseline.

    Returns ``(killed, detail)``: killed=True when ≥1 fixture differs.
    """
    slug = mod.MUTATION["policy"]
    fixture_file = mod.FIXTURE_FILE
    baseline = _POLICY_BASELINES[slug]
    path = project_dir / f"{slug}-mutant.policy.yaml"
    path.write_text(mod.POLICY_YAML, encoding="utf-8")
    try:
        pol = _policy.load(path)
    except _policy.PolicyLoadError as e:
        # Load failing in itself constitutes a kill — behavior diverges.
        return True, f"load-failed: {e.error_kind}"
    fixtures = _load_fixtures(fixture_file)
    if len(fixtures) != len(baseline):
        return True, "fixture-count mismatch (dev error)"
    for i, entry in enumerate(fixtures):
        d = pol.decide(entry["input"])
        got = (d["decision"], d.get("reason"))
        if got != baseline[i]:
            return True, (
                f"fixture #{i} baseline={baseline[i]} mutant={got}"
            )
    return False, "no differing fixture"


# ---------------------------------------------------------------------------
# Per-mutation test classes (generated dynamically)
# ---------------------------------------------------------------------------


class _MutationHarnessBase(TestEnvContext):
    """Common harness: apply mutation, drive target, revert, assert kill."""

    # PLAN-025 F-qa-007 — per-mutation wall-clock budget. A single mutation
    # running its targets for longer than this is flagged as "harness slow
    # path" (test design issue), not as a killed mutation. Prevents a single
    # pathological mutation from masking which of its targets actually
    # failed. Uses stdlib-only wall-clock assertion (no pytest-timeout dep
    # per ADR-002 stdlib-only invariant).
    _MUTATION_WALL_CLOCK_BUDGET_SECONDS = 10.0

    def _apply_engine_mutation(self, mod) -> None:
        revert = mod.apply(_policy)
        self.addCleanup(revert)

    def _assert_engine_mutation_killed(self, mod) -> None:
        import time as _t
        self._apply_engine_mutation(mod)
        killed_any = False
        details = []
        t0 = _t.monotonic()
        for tgt in mod.TARGETS:
            passed, detail = _run_target(tgt)
            details.append(f"  {tgt}: passed={passed} ({detail})")
            if not passed:
                killed_any = True
        elapsed = _t.monotonic() - t0
        # Soft-assert the wall-clock budget: emit warning via print (CI logs)
        # rather than failing the whole test, since slow mutations are a
        # harness-design signal, not a correctness regression. Fail only
        # when the slow path is > 2x the budget.
        if elapsed > self._MUTATION_WALL_CLOCK_BUDGET_SECONDS:
            print(
                f"\n[MUTATION-BUDGET-WARN] {mod.MUTATION['description']!r} "
                f"took {elapsed:.2f}s (budget {self._MUTATION_WALL_CLOCK_BUDGET_SECONDS}s)"
            )
        self.assertLess(
            elapsed,
            self._MUTATION_WALL_CLOCK_BUDGET_SECONDS * 2,
            f"MUTATION WALL-CLOCK EXCEEDED — {mod.MUTATION['description']!r} "
            f"took {elapsed:.2f}s (2x budget). Harness redesign needed.",
        )
        self.assertTrue(
            killed_any,
            f"MUTATION NOT KILLED — no target failed under mutation "
            f"{mod.MUTATION['description']!r}:\n" + "\n".join(details),
        )

    def _assert_policy_mutation_killed(self, mod) -> None:
        killed, detail = _run_policy_mutation(mod, self.project_dir)
        self.assertTrue(
            killed,
            f"MUTATION NOT KILLED — no fixture differs from baseline for "
            f"{mod.MUTATION['description']!r}: {detail}",
        )


def _make_engine_test(name: str, mod: Any):
    def body(self):
        self._assert_engine_mutation_killed(mod)
    body.__name__ = f"test_{name}"
    return body


def _make_policy_test(name: str, mod: Any):
    def body(self):
        self._assert_policy_mutation_killed(mod)
    body.__name__ = f"test_{name}"
    return body


class TestEngineMutationKills(_MutationHarnessBase):
    """One test per engine mutation — all must kill ≥1 target."""


for _name, _mod in _ENGINE_MUTATIONS:
    setattr(TestEngineMutationKills, f"test_{_name}", _make_engine_test(_name, _mod))


class TestPolicyMutationKills(_MutationHarnessBase):
    """One test per policy mutation — all must differ from baseline."""


for _name, _mod in _POLICY_MUTATIONS:
    setattr(TestPolicyMutationKills, f"test_{_name}", _make_policy_test(_name, _mod))


# ---------------------------------------------------------------------------
# Aggregate gate
# ---------------------------------------------------------------------------


class TestMutationKillRateGate(_MutationHarnessBase):
    """Global kill-rate gate — asserts 100 % and reports any survivors."""

    def test_floor_counts(self):
        self.assertGreaterEqual(
            len(_ENGINE_MUTATIONS), 25,
            f"engine-mutation floor is 25; got {len(_ENGINE_MUTATIONS)}",
        )
        self.assertGreaterEqual(
            len(_POLICY_MUTATIONS), 16,
            f"policy-mutation floor is 16; got {len(_POLICY_MUTATIONS)}",
        )
        self.assertGreaterEqual(
            len(_ENGINE_MUTATIONS) + len(_POLICY_MUTATIONS), 41,
            "aggregate mutation floor is 41",
        )

    def test_category_coverage_engine(self):
        cats: Dict[str, int] = {}
        for _, mod in _ENGINE_MUTATIONS:
            cats[mod.MUTATION["category"]] = cats.get(mod.MUTATION["category"], 0) + 1
        self.assertGreaterEqual(cats.get("parser", 0), 6,
                                f"parser mutations < 6: {cats}")
        self.assertGreaterEqual(cats.get("compiler", 0), 6,
                                f"compiler mutations < 6: {cats}")
        self.assertGreaterEqual(cats.get("evaluator", 0), 8,
                                f"evaluator mutations < 8: {cats}")
        self.assertGreaterEqual(cats.get("error-model", 0), 2,
                                f"error-model mutations < 2: {cats}")

    def test_kill_rate_100pct(self):
        survivors: List[str] = []
        for name, mod in _ENGINE_MUTATIONS:
            revert = mod.apply(_policy)
            try:
                killed_any = False
                for tgt in mod.TARGETS:
                    passed, _ = _run_target(tgt)
                    if not passed:
                        killed_any = True
                        break
                if not killed_any:
                    survivors.append(f"engine:{name} — {mod.MUTATION['description']!r}")
            finally:
                revert()
        for name, mod in _POLICY_MUTATIONS:
            killed, _detail = _run_policy_mutation(mod, self.project_dir)
            if not killed:
                survivors.append(f"policy:{name} — {mod.MUTATION['description']!r}")
        total = len(_ENGINE_MUTATIONS) + len(_POLICY_MUTATIONS)
        kill_rate = 100.0 * (total - len(survivors)) / total if total else 0.0
        self.assertEqual(
            survivors, [],
            f"kill-rate {kill_rate:.1f}% — survivors:\n  " + "\n  ".join(survivors),
        )


if __name__ == "__main__":
    unittest.main()
