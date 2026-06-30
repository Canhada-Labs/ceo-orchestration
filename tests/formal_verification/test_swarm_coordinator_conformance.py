"""Conformance tests for swarm-coordinator TLA+ spec — PLAN-050 Phase 7.

Per ``docs/formal-verification/swarm-coordinator.tla`` + §9 of
``docs/formal-verification/properties-proved.md``, every formally-
specified invariant MUST map to an executable property-based test
against the real Python implementation. This harness mirrors the
breaker / plan-lifecycle / debate-convergence pattern established by
PLAN-013 Phase D.8 and PLAN-014 Phase B.3.

## Eight property tests (4 C4-mandated + 4 support)

Safety invariants (state-wise, `[]`-quantified):

- **I1** ``test_i1_max_parallel_respected`` — ``Cardinality(ActiveLoops)
  <= MaxParallel`` holds over every reachable state.
- **I2** ``test_i2_iter_ceiling_respected`` — ``\\A i : loops[i].iter
  <= MaxIter`` — no loop exceeds its iteration ceiling.
- **I3** ``test_i3_per_loop_token_bound`` — ``\\A i : loops[i].tokens
  <= loops[i].iter`` — per-loop token accounting monotonic.
- **I4** ``test_i4_total_consumed_bounded`` — ``consumed <= N *
  MaxIter`` — global budget envelope cannot be exceeded.

Liveness properties (temporal, ``<>``-quantified, bounded):

- **L1** ``test_l1_no_dead_worker`` — every loop reaches a terminal
  status in bounded steps.
- **L2** ``test_l2_progress_guaranteed`` — running loops either
  iterate (monotonic tokens/iter) or transition to a terminal.
- **L3** ``test_l3_kill_switch_halts`` — once the kill switch trips,
  every running/pending loop reaches a terminal state in bounded
  steps. Layer-1 (env var CEO_SWARM=0) + layer-2 (sentinel file) +
  layer-3 (iteration ceiling) each exercised.
- **L4** ``test_l4_kill_precedes_propagate`` — TripKill precedes
  PropagateKill per-loop (kill propagation is observable only after
  the switch is set).

## Harness rules

1. Subclass ``TestEnvContext`` — env isolation per PLAN-013 ADJ-022.
2. Deterministic seeds — every random walk starts from an explicit
   ``random.seed(n)``; zero wall-clock dependency (monotonic clock
   is faked via injected start timestamps).
3. No ``time.sleep`` — the simulator advances the monotonic clock
   via a mutable box.
4. No live filesystem outside TestEnvContext-owned tmpdir — the
   kill-sentinel path is always under the per-test tmpdir.
5. No real subprocess / git worktree / signal delivery — those paths
   are covered by the modules' own unit tests; this harness asserts
   the TLA+ specification's state invariants against the pure-
   function surface (``coordinator.py`` + ``kill_switch.evaluate_kill_switch``).

The simulator class ``_SwarmSimulator`` deliberately re-implements
the TLA+ Next-state relation in pure Python so that random walks can
exhaustively explore the bounded state space at the conformance-test
tractability horizon (N <= 4, MaxIter <= 6, Budget <= N*MaxIter).
Larger configurations live in the TLC spec, not here.
"""

from __future__ import annotations

import importlib
import pkgutil
import random
import sys
import unittest
from pathlib import Path
from types import ModuleType
from typing import Callable, Dict, List, Optional, Tuple

# Path bootstrap — conftest.py handles this for pytest, but
# ``python3 -m unittest`` may skip the conftest, so we repeat.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
_SCRIPTS_DIR = _REPO_ROOT / ".claude" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

# The swarm package ships as `.claude/scripts/swarm/` — importable as
# `swarm.*` once `_SCRIPTS_DIR` is on sys.path.
from swarm.coordinator import (  # noqa: E402
    LoopState,
    MAX_PARALLEL_CEILING,
    SwarmConfig,
    budget_exceeded,
    detect_convergence,
    enumerate_active_loops,
    env_kill_switch_tripped,
    sentinel_file_kill_switch_tripped,
    summarize,
)
from swarm.kill_switch import (  # noqa: E402
    DECISION_CONTINUE,
    DECISION_HALT,
    DECISION_PAUSE,
    KillSwitchState,
    evaluate_kill_switch,
)

# Reference simulator + TLA+ Next-state relation — shared with the
# mutation fixtures under tests/formal_verification/mutation_fixtures/
# swarm_coordinator/ so bugs can be injected via subclass overrides.
from swarm._coordinator_sim import (  # noqa: E402
    SimConfig as _SimConfig,
    SimState as _SimState,
    SwarmSimulator as _SwarmSimulator,
    TERMINAL_STATUSES as _TERMINAL,
    init_state as _init_state,
    summarize_sim_state as _summarize_sim_state,
)


# ------------------------------------------------------------------
# Simulator — imported from swarm._coordinator_sim (see module docstring)
# ------------------------------------------------------------------
# The simulator, its config dataclasses, and the Next-state relation
# live in ``.claude/scripts/swarm/_coordinator_sim.py`` so they can be
# shared with ``mutation_fixtures/swarm_coordinator/``. See that
# module's docstring for the contract and separation rationale.


# ------------------------------------------------------------------
# Mutation fixture loader
# ------------------------------------------------------------------


def _load_mutations(property_id: str) -> List[ModuleType]:
    """Discover mutations under mutation_fixtures/swarm_coordinator/ tagged ``PROPERTY``.

    Returns modules sorted by filename for deterministic iteration
    (and deterministic failure order). Handles both pytest (package
    discovery) and ``python3 -m unittest`` (explicit re-import).
    """
    try:
        from mutation_fixtures import swarm_coordinator as mut_pkg  # type: ignore
    except ImportError:
        import mutation_fixtures.swarm_coordinator as mut_pkg  # type: ignore

    mods: List[ModuleType] = []
    pkg_path = Path(mut_pkg.__file__).resolve().parent  # type: ignore[arg-type]
    for info in pkgutil.iter_modules([str(pkg_path)]):
        if not info.name.startswith("mut_"):
            continue
        mod = importlib.import_module(
            f"mutation_fixtures.swarm_coordinator.{info.name}"
        )
        if getattr(mod, "PROPERTY", None) == property_id:
            mods.append(mod)
    mods.sort(key=lambda m: m.__name__)
    return mods


# ------------------------------------------------------------------
# Shared base — deterministic seed sweep + invariant assertions
# ------------------------------------------------------------------


class _SwarmConformanceBase(TestEnvContext):
    """Shared base for property tests.

    Subclasses override ``PROPERTY_ID`` + implement ``_invariant_holds``.
    ``_property_sweep`` drives N random walks under seeds [0, N) and
    calls ``_invariant_holds`` on every visited state. Mutation tests
    override ``SIM_CLS`` so the same sweep runs against a buggy
    simulator subclass and asserts the invariant fails.
    """

    # Number of random walks per property sweep. Kept modest (200) so
    # full test run stays well under 10s even on cold CI caches.
    SEED_SWEEP_N = 200

    #: Default simulator configuration — small-model tractable.
    CFG = _SimConfig(n=3, max_parallel=2, max_iter=4, budget=6)

    # Override in subclass. Example: "I1"
    PROPERTY_ID = "BASE"

    # Simulator class under test. Mutation tests temporarily swap this
    # for a mutated subclass; see ``_run_mutation_gate``.
    SIM_CLS = _SwarmSimulator

    def _invariant_holds(self, state: _SimState) -> Optional[str]:
        """Return None when invariant holds; violation reason otherwise."""
        raise NotImplementedError

    def _property_sweep(
        self,
        cfg: Optional[_SimConfig] = None,
        action_bias: Optional[Callable[[str, Optional[str]], float]] = None,
        seed_count: Optional[int] = None,
        sim_cls: Optional[type] = None,
    ) -> None:
        cfg = cfg or self.CFG
        n_seeds = seed_count if seed_count is not None else self.SEED_SWEEP_N
        cls = sim_cls or self.SIM_CLS
        for seed in range(n_seeds):
            rng = random.Random(seed)
            sim = cls(cfg=cfg, rng=rng, action_bias=action_bias)
            trace = sim.walk()
            self._assert_trace_holds(trace, seed)

    def _assert_trace_holds(self, trace: List[_SimState], seed: int) -> None:
        for step, state in enumerate(trace):
            reason = self._invariant_holds(state)
            if reason is not None:
                raise AssertionError(
                    f"[{self.PROPERTY_ID}] seed={seed} step={step}: {reason}. "
                    f"state={_summarize_sim_state(state)}"
                )

    def _run_mutation_gate(
        self,
        *,
        min_mutations: int,
        core_runner: Callable[[type], None],
    ) -> None:
        """Assert every mutation tagged ``self.PROPERTY_ID`` causes ``core_runner`` to fail.

        ``core_runner(sim_cls)`` must raise ``AssertionError`` when the
        given simulator class has been mutated to break the property.
        The unmutated baseline (``_SwarmSimulator``) has already been
        exercised by the corresponding ``test_<prop>_*`` methods, so we
        only verify that the mutant kills it.
        """
        mutations = _load_mutations(self.PROPERTY_ID)
        self.assertGreaterEqual(
            len(mutations),
            min_mutations,
            msg=(
                f"{self.PROPERTY_ID} mutation budget is {min_mutations}; "
                f"discovered {len(mutations)}"
            ),
        )
        survived: List[str] = []
        for mut_mod in mutations:
            cls_mutant = mut_mod.apply(_SwarmSimulator)
            try:
                core_runner(cls_mutant)
            except AssertionError:
                continue
            survived.append(mut_mod.__name__)
        self.assertEqual(
            survived,
            [],
            msg=(
                f"{self.PROPERTY_ID}: mutations did NOT raise AssertionError: "
                f"{survived}. These are surviving mutations — either the "
                f"property is under-specified or the mutations are wrong."
            ),
        )


# ------------------------------------------------------------------
# I1 — MaxParallelRespected (safety)
# ------------------------------------------------------------------


class TestI1MaxParallelRespected(_SwarmConformanceBase):
    """I1: |active loops| <= MaxParallel in every reachable state.

    Maps to TLA+ ``MaxParallelRespected`` and Python
    ``MAX_PARALLEL_CEILING = 8`` (coordinator.py:38) +
    ``SwarmConfig.n_loops`` clamping (coordinator.py:__post_init__).
    """

    PROPERTY_ID = "I1"

    def _invariant_holds(self, state: _SimState) -> Optional[str]:
        active = [lid for lid, s in state.loops.items() if s.status == "running"]
        if len(active) > self.CFG.max_parallel:
            return (
                f"I1 violated: active={len(active)} > MaxParallel="
                f"{self.CFG.max_parallel}; active_loops={active}"
            )
        return None

    def test_i1_random_walks(self) -> None:
        self._property_sweep()

    def test_i1_bias_toward_start(self) -> None:
        """Biased exploration: aggressively prefer StartLoop, stress the cap."""
        self._property_sweep(
            action_bias=lambda a, lid: 10.0 if a == "start" else 1.0
        )

    def test_i1_enumerate_active_loops_matches_simulator(self) -> None:
        """coordinator.enumerate_active_loops agrees with the simulator's running-set."""
        cfg = self.CFG
        rng = random.Random(1234)
        sim = _SwarmSimulator(cfg=cfg, rng=rng)
        for state in sim.walk():
            helper_active = enumerate_active_loops(state.loops)
            sim_active = sorted(
                lid for lid, s in state.loops.items() if s.status == "running"
            )
            self.assertEqual(sorted(helper_active), sim_active)

    def test_i1_config_clamp_to_ceiling(self) -> None:
        """SwarmConfig clamps ``n_loops`` at MAX_PARALLEL_CEILING (doesn't raise)."""
        cfg = SwarmConfig(
            n_loops=MAX_PARALLEL_CEILING + 5,
            budget_tokens=100,
            goal="x",
        )
        self.assertEqual(cfg.n_loops, MAX_PARALLEL_CEILING)

    def test_i1_config_rejects_non_positive(self) -> None:
        """SwarmConfig rejects n_loops < 1 per __post_init__ guard."""
        with self.assertRaises(ValueError):
            SwarmConfig(n_loops=0, budget_tokens=100, goal="x")

    def test_i1_mutations_fail(self) -> None:
        """Every I1 mutation causes the property sweep to raise AssertionError."""

        def runner(sim_cls: type) -> None:
            self._property_sweep(
                sim_cls=sim_cls,
                action_bias=lambda a, lid: 10.0 if a == "start" else 1.0,
            )

        self._run_mutation_gate(min_mutations=5, core_runner=runner)


# ------------------------------------------------------------------
# I2 — IterCeilingRespected (safety)
# ------------------------------------------------------------------


class TestI2IterCeilingRespected(_SwarmConformanceBase):
    """I2: no loop's iteration count ever exceeds MaxIter.

    Maps to TLA+ ``IterCeilingRespected`` and
    ``DEFAULT_MAX_ITERATIONS = 20`` (coordinator.py:46) +
    ``SwarmConfig.max_iterations`` guard.
    """

    PROPERTY_ID = "I2"

    def _invariant_holds(self, state: _SimState) -> Optional[str]:
        for lid, s in state.loops.items():
            if s.iteration > self.CFG.max_iter:
                return (
                    f"I2 violated: {lid}.iter={s.iteration} "
                    f"> MaxIter={self.CFG.max_iter}"
                )
        return None

    def test_i2_random_walks(self) -> None:
        self._property_sweep()

    def test_i2_bias_toward_iterate(self) -> None:
        """Biased exploration: always prefer Iterate when enabled."""
        self._property_sweep(
            action_bias=lambda a, lid: 10.0 if a == "iterate" else 1.0
        )

    def test_i2_config_rejects_non_positive_max_iter(self) -> None:
        with self.assertRaises(ValueError):
            SwarmConfig(
                n_loops=1, budget_tokens=10, goal="x", max_iterations=0
            )

    def test_i2_mutations_fail(self) -> None:
        def runner(sim_cls: type) -> None:
            self._property_sweep(
                sim_cls=sim_cls,
                action_bias=lambda a, lid: 10.0 if a == "iterate" else 1.0,
            )

        self._run_mutation_gate(min_mutations=5, core_runner=runner)


# ------------------------------------------------------------------
# I3 — PerLoopTokenBound (safety)
# ------------------------------------------------------------------


class TestI3PerLoopTokenBound(_SwarmConformanceBase):
    """I3: per-loop tokens_consumed never exceeds its iteration count.

    Maps to TLA+ ``PerLoopTokenBound`` — ensures the abstraction
    "1 token per iteration" is preserved. Real loop_runner.py may
    accumulate tokens faster, but the monotonicity relation
    ``tokens >= iter`` held by the simulator mirrors the TLA+ bound.
    """

    PROPERTY_ID = "I3"

    def _invariant_holds(self, state: _SimState) -> Optional[str]:
        for lid, s in state.loops.items():
            if s.tokens_consumed > s.iteration:
                return (
                    f"I3 violated: {lid}.tokens={s.tokens_consumed} "
                    f"> iter={s.iteration}"
                )
        return None

    def test_i3_random_walks(self) -> None:
        self._property_sweep()

    def test_i3_bias_toward_iterate(self) -> None:
        self._property_sweep(
            action_bias=lambda a, lid: 10.0 if a == "iterate" else 1.0
        )

    def test_i3_mutations_fail(self) -> None:
        def runner(sim_cls: type) -> None:
            self._property_sweep(
                sim_cls=sim_cls,
                action_bias=lambda a, lid: 10.0 if a == "iterate" else 1.0,
            )

        self._run_mutation_gate(min_mutations=5, core_runner=runner)


# ------------------------------------------------------------------
# I4 — TotalConsumedBounded (safety)
# ------------------------------------------------------------------


class TestI4TotalConsumedBounded(_SwarmConformanceBase):
    """I4: total ``consumed`` never exceeds N * MaxIter.

    Maps to TLA+ ``TotalConsumedBounded`` and the budget envelope
    logic in ``budget_exceeded`` (coordinator.py:166-172) +
    ``evaluate_kill_switch`` CB #1.
    """

    PROPERTY_ID = "I4"

    def _invariant_holds(self, state: _SimState) -> Optional[str]:
        ceiling = self.CFG.n * self.CFG.max_iter
        if state.consumed > ceiling:
            return (
                f"I4 violated: consumed={state.consumed} > N*MaxIter="
                f"{ceiling}"
            )
        return None

    def test_i4_random_walks(self) -> None:
        self._property_sweep()

    def test_i4_budget_exceeded_agrees_with_simulator(self) -> None:
        """``budget_exceeded`` returns True iff simulated consumed > budget."""
        cfg = self.CFG
        rng = random.Random(777)
        sim = _SwarmSimulator(cfg=cfg, rng=rng)
        for state in sim.walk():
            if not state.loops:
                continue
            # Simulator's ``consumed`` is the sum of per-loop tokens —
            # the same invariant budget_exceeded checks.
            expected = (
                sum(s.tokens_consumed for s in state.loops.values())
                > cfg.budget
            )
            actual = budget_exceeded(state.loops, cfg.budget)
            self.assertEqual(
                actual,
                expected,
                f"budget_exceeded disagreed with simulator at "
                f"{_summarize_sim_state(state)}",
            )

    def test_i4_budget_exceeded_rejects_non_positive(self) -> None:
        with self.assertRaises(ValueError):
            budget_exceeded({}, 0)

    def test_i4_mutations_fail(self) -> None:
        def runner(sim_cls: type) -> None:
            self._property_sweep(
                sim_cls=sim_cls,
                action_bias=lambda a, lid: 10.0 if a == "iterate" else 1.0,
            )

        self._run_mutation_gate(min_mutations=5, core_runner=runner)


# ------------------------------------------------------------------
# L1 — NoDeadWorker (liveness, bounded)
# ------------------------------------------------------------------


class TestL1NoDeadWorker(_SwarmConformanceBase):
    """L1: every loop reaches a terminal status in bounded steps.

    Maps to TLA+ ``NoDeadWorker`` (``<>(status \\in Terminal)``).
    We force termination by driving the simulator under an
    always-prefer-terminal bias. The bounded equivalent: within
    ``step_ceiling`` steps, either all loops terminated or the walk
    exhausted enabled actions. Both outcomes satisfy L1 in the
    small-model bound.
    """

    PROPERTY_ID = "L1"

    def _invariant_holds(self, state: _SimState) -> Optional[str]:
        # Stateless invariant — L1 is a liveness property enforced at
        # end-of-walk. See test_l1_* methods.
        return None

    def test_l1_every_walk_terminates(self) -> None:
        """Under a termination-biased policy, every walk reaches all-terminal."""
        bias = _termination_bias
        cfg = self.CFG
        for seed in range(self.SEED_SWEEP_N):
            rng = random.Random(seed)
            sim = _SwarmSimulator(cfg=cfg, rng=rng, action_bias=bias)
            trace = sim.walk()
            final = trace[-1]
            unterminated = [
                lid
                for lid, s in final.loops.items()
                if s.status not in _TERMINAL
            ]
            self.assertEqual(
                unterminated,
                [],
                f"L1 violated seed={seed}: unterminated loops={unterminated} "
                f"at final state {_summarize_sim_state(final)}",
            )

    def test_l1_mutations_fail_under_default_bias(self) -> None:
        """Independent kill proof (PLAN-051 Phase 4 B3 Cluster 3).

        Runs the L1 mutation set under the default ``_termination_bias``
        (the same policy driving ``test_l1_every_walk_terminates``)
        and asserts at least one mutation is killed. This proves the
        harness itself — not a dedicated mutation-test bias — has
        sufficient discrimination to detect at least one L1 bug.
        """
        bias = _termination_bias
        mutations = _load_mutations(self.PROPERTY_ID)
        self.assertGreaterEqual(len(mutations), 1)
        killed: List[str] = []
        for mut_mod in mutations:
            cls_mutant = mut_mod.apply(_SwarmSimulator)
            killed_here = False
            for seed in range(self.SEED_SWEEP_N):
                rng = random.Random(seed)
                sim = cls_mutant(cfg=self.CFG, rng=rng, action_bias=bias)
                trace = sim.walk()
                final = trace[-1]
                if any(s.status not in _TERMINAL for s in final.loops.values()):
                    killed_here = True
                    break
                # Terminal-escape check.
                first_terminal: Dict[str, Tuple[int, str]] = {}
                escaped = False
                for step, state in enumerate(trace):
                    for lid, s in state.loops.items():
                        if s.status in _TERMINAL:
                            first_terminal.setdefault(lid, (step, s.status))
                        elif lid in first_terminal:
                            escaped = True
                            break
                    if escaped:
                        break
                if escaped:
                    killed_here = True
                    break
            if killed_here:
                killed.append(mut_mod.__name__)
        self.assertGreaterEqual(
            len(killed),
            1,
            msg=(
                f"{self.PROPERTY_ID}: no mutation killed under "
                f"default _termination_bias — harness lacks "
                f"independent discrimination"
            ),
        )

    def test_l1_mutations_fail(self) -> None:
        """Every L1 mutation causes an L1 assertion to fail.

        Two mutations with distinct scenarios:
        - mut_l1_01 (all terminal paths disabled): detected via final-
          state un-termination. Any bias that lets the walk run to
          step_ceiling without escaping through kill works.
        - mut_l1_02 (terminal not a sink): detected via a loop
          transitioning out of Terminal. Needs a bias that stresses
          Start (re-start after completion) — high start weight with
          trip_kill zeroed so the walk doesn't short-circuit.
        """

        def runner(sim_cls: type) -> None:
            for seed in range(self.SEED_SWEEP_N):
                for bias in (_mutation_l1_a_bias, _mutation_l1_b_bias):
                    rng = random.Random(seed)
                    sim = sim_cls(cfg=self.CFG, rng=rng, action_bias=bias)
                    trace = sim.walk()
                    final = trace[-1]
                    unterminated = [
                        lid
                        for lid, s in final.loops.items()
                        if s.status not in _TERMINAL
                    ]
                    # Un-termination check (mut_l1_02 trigger).
                    first_terminal: Dict[str, Tuple[int, str]] = {}
                    for step, state in enumerate(trace):
                        for lid, s in state.loops.items():
                            if s.status in _TERMINAL:
                                if lid not in first_terminal:
                                    first_terminal[lid] = (step, s.status)
                            else:
                                prior = first_terminal.get(lid)
                                if prior is not None:
                                    raise AssertionError(
                                        f"L1 violated seed={seed}: "
                                        f"{lid} left terminal "
                                        f"{prior[1]} at step {step}"
                                    )
                    if unterminated:
                        raise AssertionError(
                            f"L1 violated seed={seed} bias={bias.__name__}: "
                            f"unterminated={unterminated}"
                        )

        self._run_mutation_gate(min_mutations=5, core_runner=runner)

    def test_l1_terminal_statuses_are_sink(self) -> None:
        """No transition out of terminal — once terminal, always terminal."""
        cfg = self.CFG
        rng = random.Random(42)
        sim = _SwarmSimulator(cfg=cfg, rng=rng, action_bias=_termination_bias)
        trace = sim.walk()
        # Walk the trace checking each loop's status is monotonic wrt
        # terminal: once a loop is in _TERMINAL at step k, it remains
        # in _TERMINAL at every step > k (and the specific terminal
        # identity doesn't change).
        first_terminal: Dict[str, Tuple[int, str]] = {}
        for step, state in enumerate(trace):
            for lid, s in state.loops.items():
                if s.status in _TERMINAL:
                    prior = first_terminal.get(lid)
                    if prior is None:
                        first_terminal[lid] = (step, s.status)
                    else:
                        first_step, first_status = prior
                        self.assertEqual(
                            s.status,
                            first_status,
                            f"L1 violated: {lid} changed terminal "
                            f"{first_status} (step {first_step}) -> "
                            f"{s.status} (step {step})",
                        )


# ------------------------------------------------------------------
# L2 — ProgressGuaranteed (liveness, bounded)
# ------------------------------------------------------------------


class TestL2ProgressGuaranteed(_SwarmConformanceBase):
    """L2: running loops either iterate OR transition to terminal.

    Maps to TLA+ ``ProgressGuaranteed``:
    ``(status = "running") ~> (iter > 0 \\/ status \\in Terminal)``.
    """

    PROPERTY_ID = "L2"

    def _invariant_holds(self, state: _SimState) -> Optional[str]:
        return None  # trace-level property; see methods below

    def test_l2_running_loops_eventually_progress_or_terminate(self) -> None:
        cfg = self.CFG
        for seed in range(self.SEED_SWEEP_N):
            rng = random.Random(seed)
            sim = _SwarmSimulator(
                cfg=cfg, rng=rng, action_bias=_progress_bias
            )
            trace = sim.walk()
            # Track "moment of running" per loop.
            first_running: Dict[str, int] = {}
            for step, state in enumerate(trace):
                for lid, s in state.loops.items():
                    if s.status == "running" and lid not in first_running:
                        first_running[lid] = step
            # For each loop that was ever running, assert eventual progress.
            for lid, first_step in first_running.items():
                # Find the first state after first_step where either
                # iter > 0 or status is terminal.
                satisfied = False
                for state in trace[first_step:]:
                    s = state.loops[lid]
                    if s.iteration > 0 or s.status in _TERMINAL:
                        satisfied = True
                        break
                self.assertTrue(
                    satisfied,
                    f"L2 violated: {lid} was running at step {first_step} "
                    f"but never iterated or terminated within {len(trace)} "
                    f"steps",
                )

    def test_l2_mutations_fail_under_default_bias(self) -> None:
        """Independent kill proof (PLAN-051 Phase 4 B3 Cluster 3).

        Runs the L2 mutation set under the default ``_progress_bias``
        (the policy driving
        ``test_l2_running_loops_eventually_progress_or_terminate``)
        and asserts at least one mutation is killed. Proves the L2
        invariant check itself has discrimination independent of the
        dedicated ``_mutation_l2_bias``.
        """
        bias = _progress_bias
        mutations = _load_mutations(self.PROPERTY_ID)
        self.assertGreaterEqual(len(mutations), 1)
        killed: List[str] = []
        for mut_mod in mutations:
            cls_mutant = mut_mod.apply(_SwarmSimulator)
            killed_here = False
            for seed in range(self.SEED_SWEEP_N):
                rng = random.Random(seed)
                sim = cls_mutant(cfg=self.CFG, rng=rng, action_bias=bias)
                trace = sim.walk()
                first_running: Dict[str, int] = {}
                for step, state in enumerate(trace):
                    for lid, s in state.loops.items():
                        if s.status == "running" and lid not in first_running:
                            first_running[lid] = step
                for lid, first_step in first_running.items():
                    satisfied = False
                    for state in trace[first_step:]:
                        s = state.loops[lid]
                        if s.iteration > 0 or s.status in _TERMINAL:
                            satisfied = True
                            break
                    if not satisfied:
                        killed_here = True
                        break
                if killed_here:
                    break
            if killed_here:
                killed.append(mut_mod.__name__)
        self.assertGreaterEqual(
            len(killed),
            1,
            msg=(
                f"{self.PROPERTY_ID}: no mutation killed under "
                f"default _progress_bias — harness lacks "
                f"independent discrimination"
            ),
        )

    def test_l2_mutations_fail(self) -> None:
        """L2-01 (iterate no-op) causes the progress/monotonicity check to fail.

        Uses a start-heavy + kill-zeroed bias so the walk runs all 3
        loops to running + iterate repeatedly without short-circuiting
        via TripKill → PropagateKill (which would terminate everything
        without requiring any iteration).
        """

        def runner(sim_cls: type) -> None:
            cfg = self.CFG
            for seed in range(self.SEED_SWEEP_N):
                rng = random.Random(seed)
                sim = sim_cls(
                    cfg=cfg, rng=rng, action_bias=_mutation_l2_bias
                )
                trace = sim.walk()
                # Detect no-op Iterate: a running loop that never
                # advances `iteration` before terminating.
                first_running: Dict[str, int] = {}
                ever_iterated: Dict[str, bool] = {}
                for step, state in enumerate(trace):
                    for lid, s in state.loops.items():
                        if s.status == "running" and lid not in first_running:
                            first_running[lid] = step
                        if s.iteration > 0:
                            ever_iterated[lid] = True
                # Loop that was running but reached step_ceiling or end
                # without iterating AND is still running in the final
                # state → L2 violated (no progress).
                final = trace[-1]
                for lid, first_step in first_running.items():
                    if (
                        not ever_iterated.get(lid, False)
                        and final.loops[lid].status == "running"
                    ):
                        raise AssertionError(
                            f"L2 violated seed={seed}: {lid} was running "
                            f"from step {first_step} but never iterated"
                        )

        self._run_mutation_gate(min_mutations=5, core_runner=runner)

    def test_l2_iteration_is_monotonic(self) -> None:
        """iter counter only increases; tokens only increase; no regression."""
        cfg = self.CFG
        rng = random.Random(31337)
        sim = _SwarmSimulator(cfg=cfg, rng=rng)
        trace = sim.walk()
        prev: Dict[str, Tuple[int, int]] = {}
        for step, state in enumerate(trace):
            for lid, s in state.loops.items():
                p_iter, p_tokens = prev.get(lid, (0, 0))
                self.assertGreaterEqual(
                    s.iteration,
                    p_iter,
                    f"L2 violated: {lid} iter regressed "
                    f"{p_iter}->{s.iteration} at step {step}",
                )
                self.assertGreaterEqual(
                    s.tokens_consumed,
                    p_tokens,
                    f"L2 violated: {lid} tokens regressed "
                    f"{p_tokens}->{s.tokens_consumed} at step {step}",
                )
                prev[lid] = (s.iteration, s.tokens_consumed)


# ------------------------------------------------------------------
# L3 — KillSwitchHalts (liveness, bounded) — 3-layer coverage
# ------------------------------------------------------------------


class TestL3KillSwitchHalts(_SwarmConformanceBase):
    """L3: once kill trips, every running/pending loop reaches terminal.

    Maps to TLA+ ``KillSwitchHalts``. We exercise the Python
    implementation's 3 in-process layers:
      - Layer 1: ``CEO_SWARM=0`` env var
      - Layer 2: sentinel file presence
      - Layer 3: per-loop iteration ceiling

    Plus the simulator's ``TripKill`` + ``PropagateKill`` abstraction
    to validate the temporal property directly.
    """

    PROPERTY_ID = "L3"

    def _invariant_holds(self, state: _SimState) -> Optional[str]:
        return None

    def test_l3_simulated_trip_eventually_halts_all(self) -> None:
        """Simulator-level: after TripKill fires, every loop terminates."""
        cfg = self.CFG
        for seed in range(self.SEED_SWEEP_N):
            rng = random.Random(seed)
            bias = _kill_then_propagate_bias
            sim = _SwarmSimulator(cfg=cfg, rng=rng, action_bias=bias)
            trace = sim.walk()
            kill_step: Optional[int] = None
            for step, state in enumerate(trace):
                if state.kill:
                    kill_step = step
                    break
            if kill_step is None:
                # Walk finished without ever tripping kill — vacuously
                # satisfies L3. Record skip rate in an implicit
                # subscribed seed set — not a violation.
                continue
            final = trace[-1]
            unterminated = [
                lid
                for lid, s in final.loops.items()
                if s.status not in _TERMINAL
            ]
            self.assertEqual(
                unterminated,
                [],
                f"L3 violated seed={seed}: kill tripped at step "
                f"{kill_step} but loops {unterminated} remained active "
                f"at final {_summarize_sim_state(final)}",
            )

    def test_l3_layer_1_env_var_halts(self) -> None:
        """Layer 1: CEO_SWARM=0 (or missing) trips the in-process kill switch."""
        # Default env (no CEO_SWARM set) → tripped.
        self.assertTrue(env_kill_switch_tripped({}))
        self.assertTrue(env_kill_switch_tripped({"CEO_SWARM": "0"}))
        # Explicit opt-in → not tripped.
        self.assertFalse(env_kill_switch_tripped({"CEO_SWARM": "1"}))
        # Layer-1 disable flag overrides opt-in.
        self.assertTrue(
            env_kill_switch_tripped(
                {"CEO_SWARM": "1", "CEO_AUTONOMOUS_LOOPS_DISABLE": "1"}
            )
        )

    def test_l3_layer_1_evaluate_produces_halt(self) -> None:
        """evaluate_kill_switch escalates to DECISION_HALT with layer-1 reason."""
        # env={} passes explicit empty dict → CEO_SWARM absent → halt
        result = evaluate_kill_switch(loops={}, budget_tokens=100, env={})
        self.assertEqual(result.decision, DECISION_HALT)
        self.assertTrue(
            any("kill_layer_1_env" in r for r in result.reasons),
            f"expected layer_1 reason, got {result.reasons}",
        )

    def test_l3_layer_2_sentinel_halts(self) -> None:
        """Layer 2: sentinel file presence trips the switch."""
        tmp = self._tmp_root / "swarm-kill"
        self.assertFalse(sentinel_file_kill_switch_tripped(tmp))
        tmp.write_text("")
        self.assertTrue(sentinel_file_kill_switch_tripped(tmp))

    def test_l3_layer_2_evaluate_halts_when_sentinel_present(self) -> None:
        tmp = self._tmp_root / "swarm-kill"
        tmp.write_text("")
        result = evaluate_kill_switch(
            loops={},
            budget_tokens=100,
            sentinel_path=tmp,
            env={"CEO_SWARM": "1"},
        )
        self.assertEqual(result.decision, DECISION_HALT)
        self.assertTrue(
            any("kill_layer_2_sentinel" in r for r in result.reasons),
            f"expected layer_2 reason, got {result.reasons}",
        )

    def test_l3_layer_3_iteration_ceiling_pauses(self) -> None:
        """Layer 3: a loop at iteration_limit escalates to at least PAUSE."""
        loops = {
            "L0": LoopState(loop_id="L0", iteration=5, status="running"),
            "L1": LoopState(loop_id="L1", iteration=1, status="running"),
        }
        result = evaluate_kill_switch(
            loops=loops,
            budget_tokens=100,
            iteration_limit=5,
            env={"CEO_SWARM": "1"},
        )
        # Pause OR halt — anything non-continue signals the switch.
        self.assertIn(result.decision, {DECISION_PAUSE, DECISION_HALT})
        self.assertTrue(
            any("kill_layer_3_iteration_ceiling" in r for r in result.reasons),
            f"expected layer_3 reason, got {result.reasons}",
        )

    def test_l3_mutations_fail(self) -> None:
        """Every L3 mutation causes the simulator-level KillSwitchHalts to fail.

        Uses the same kill-then-propagate bias as
        ``test_l3_simulated_trip_eventually_halts_all``: once TripKill
        fires, every running/pending loop MUST reach a terminal in
        bounded steps. Mutations that decouple kill from propagation
        or from iterate/start guards leave loops active after kill.
        """

        def runner(sim_cls: type) -> None:
            cfg = self.CFG
            detected_seed: Optional[int] = None
            for seed in range(self.SEED_SWEEP_N):
                rng = random.Random(seed)
                sim = sim_cls(
                    cfg=cfg, rng=rng, action_bias=_kill_then_propagate_bias
                )
                trace = sim.walk()
                kill_step: Optional[int] = None
                for step, state in enumerate(trace):
                    if state.kill:
                        kill_step = step
                        break
                # Check L4 ordering too: status=killed with kill=False.
                for state in trace:
                    for lid, s in state.loops.items():
                        if s.status == "killed" and not state.kill:
                            raise AssertionError(
                                f"L3/L4 violated seed={seed}: "
                                f"{lid} killed without kill flag"
                            )
                if kill_step is None:
                    continue
                final = trace[-1]
                unterminated = [
                    lid
                    for lid, s in final.loops.items()
                    if s.status not in _TERMINAL
                ]
                if unterminated:
                    detected_seed = seed
                    raise AssertionError(
                        f"L3 violated seed={seed}: kill tripped at step "
                        f"{kill_step} but {unterminated} still active "
                        f"in final state"
                    )
            # If every seed reached all-terminal, the mutation survived.
            if detected_seed is None:
                raise AssertionError(
                    "L3 mutation not detected across seed sweep"
                )

        self._run_mutation_gate(min_mutations=5, core_runner=runner)

    def test_l3_continue_when_no_trigger(self) -> None:
        """Sanity: evaluate returns CONTINUE when no layer/CB triggers."""
        loops = {
            "L0": LoopState(loop_id="L0", iteration=1, status="running"),
        }
        result = evaluate_kill_switch(
            loops=loops,
            budget_tokens=1000,
            env={"CEO_SWARM": "1"},
        )
        self.assertEqual(result.decision, DECISION_CONTINUE)
        self.assertEqual(result.reasons, [])



# ------------------------------------------------------------------
# L4 — TripKill precedes PropagateKill (ordering)
# ------------------------------------------------------------------


class TestL4KillPrecedesPropagate(_SwarmConformanceBase):
    """L4 (implicit from TLA+ action enabling): TripKill precedes any
    PropagateKill in every trace.

    This is not a numbered invariant in the TLA+ spec but follows
    directly from the ``PropagateKill(i)`` guard ``/\\ kill`` in
    swarm-coordinator.tla:108. We assert it here as a conformance
    property to guard against a future simulator refactor that
    accidentally allows propagate without trip.
    """

    PROPERTY_ID = "L4"

    def _invariant_holds(self, state: _SimState) -> Optional[str]:
        # State-level check: if ANY loop has status=="killed", kill
        # must be True. ("killed" results ONLY from PropagateKill.)
        for lid, s in state.loops.items():
            if s.status == "killed" and not state.kill:
                return (
                    f"L4 violated: {lid}.status=killed but kill=False "
                    f"— propagate fired before trip"
                )
        return None

    def test_l4_random_walks(self) -> None:
        self._property_sweep()

    def test_l4_bias_toward_kill(self) -> None:
        self._property_sweep(
            action_bias=lambda a, lid: 10.0
            if a in {"trip_kill", "propagate_kill"}
            else 1.0
        )

    def test_l4_mutations_fail(self) -> None:
        def runner(sim_cls: type) -> None:
            self._property_sweep(
                sim_cls=sim_cls,
                action_bias=lambda a, lid: 10.0
                if a in {"trip_kill", "propagate_kill"}
                else 1.0,
            )

        self._run_mutation_gate(min_mutations=5, core_runner=runner)


# ------------------------------------------------------------------
# Pure-function sanity — coordinator helpers reflect spec faithfully
# ------------------------------------------------------------------


class TestCoordinatorHelpersReflectSpec(TestEnvContext):
    """Unit-level sanity that the helpers we rely on in the simulator
    produce results consistent with the TLA+ semantics we're asserting
    (orthogonal to the property tests but cheap to pin)."""

    def test_summarize_counts_match_raw_state(self) -> None:
        loops = {
            "L0": LoopState(loop_id="L0", iteration=3, tokens_consumed=3,
                            status="completed"),
            "L1": LoopState(loop_id="L1", iteration=2, tokens_consumed=2,
                            status="running"),
            "L2": LoopState(loop_id="L2", iteration=1, tokens_consumed=1,
                            status="killed"),
        }
        summary = summarize(loops)
        self.assertEqual(summary["n_loops"], 3)
        self.assertEqual(summary["total_tokens_consumed"], 6)
        self.assertEqual(summary["total_iterations"], 6)
        # ``active`` reflects only status==running
        self.assertEqual(summary["active"], ["L1"])

    def test_detect_convergence_is_deterministic(self) -> None:
        """Convergence ids returned in stable insertion order."""
        loops = {
            "A": LoopState(
                loop_id="A", iteration=1, status="running",
                files_touched=["x.py", "y.py"],
            ),
            "B": LoopState(
                loop_id="B", iteration=1, status="running",
                files_touched=["x.py", "y.py"],
            ),
            "C": LoopState(
                loop_id="C", iteration=1, status="running",
                files_touched=["x.py", "y.py"],
            ),
        }
        # A keeps running; B, C are losers in deterministic order.
        self.assertEqual(detect_convergence(loops, threshold=0.5), ["B", "C"])

    def test_detect_convergence_threshold_bounds(self) -> None:
        loops = {"L0": LoopState(loop_id="L0", status="running")}
        with self.assertRaises(ValueError):
            detect_convergence(loops, threshold=-0.1)
        with self.assertRaises(ValueError):
            detect_convergence(loops, threshold=1.1)

    def test_evaluate_kill_switch_continue_empty_loops(self) -> None:
        """Empty loops + CEO_SWARM=1 + no triggers => CONTINUE."""
        result = evaluate_kill_switch(
            loops={}, budget_tokens=100, env={"CEO_SWARM": "1"}
        )
        self.assertIsInstance(result, KillSwitchState)
        self.assertEqual(result.decision, DECISION_CONTINUE)
        self.assertEqual(result.loops_to_kill, [])


# ------------------------------------------------------------------
# Action-bias heuristics — guide random walks into the scenarios the
# temporal-logic property is actually about.
# ------------------------------------------------------------------


def _termination_bias(action: str, _loop_id: Optional[str]) -> float:
    """Favor actions that move loops toward terminal statuses."""
    if action in {"converge", "complete", "budget_kill", "propagate_kill"}:
        return 10.0
    if action == "trip_kill":
        return 3.0
    # Starting/iterating is still allowed — we need loops to have
    # entered running state before they can converge/complete.
    return 1.0


def _progress_bias(action: str, _loop_id: Optional[str]) -> float:
    """Favor actions that produce monotonic progress (iterate > start)."""
    if action == "iterate":
        return 8.0
    if action == "start":
        return 3.0
    if action in {"converge", "complete"}:
        return 2.0
    return 1.0


def _kill_then_propagate_bias(
    action: str, _loop_id: Optional[str]
) -> float:
    """Favor TripKill early, then PropagateKill to drive KillSwitchHalts."""
    if action == "trip_kill":
        return 15.0
    if action == "propagate_kill":
        return 10.0
    if action in {"start", "iterate"}:
        return 2.0
    return 1.0


# ------------------------------------------------------------------
# Mutation-runner biases
# ------------------------------------------------------------------


def _mutation_l1_a_bias(action: str, _loop_id: Optional[str]) -> float:
    """Trigger mut_l1_01: kill-free walk so stuck loops never escape.

    Zero weights on kill-trigger actions; prefer Start + Iterate so
    loops enter running state and fail to terminate if Complete /
    Converge / BudgetKill paths are absent.
    """
    if action in {"trip_kill", "propagate_kill"}:
        return 0.0
    if action == "start":
        return 5.0
    if action == "iterate":
        return 3.0
    # Leave complete / converge / budget_kill nominal so the
    # un-mutated sim still can terminate via them.
    return 1.0


def _mutation_l1_b_bias(action: str, _loop_id: Optional[str]) -> float:
    """Trigger mut_l1_02: Start-heavy so completed loops get re-started.

    High weight on Start, moderate on Iterate + Complete, zero on kill.
    Under this bias, a loop that completes has a high chance of being
    re-started before the other loops also complete — triggering the
    "terminal left" assertion.
    """
    if action in {"trip_kill", "propagate_kill"}:
        return 0.0
    if action == "start":
        return 20.0
    if action == "iterate":
        return 5.0
    if action == "complete":
        return 3.0
    return 1.0


def _mutation_l2_bias(action: str, _loop_id: Optional[str]) -> float:
    """Trigger mut_l2_01: walk where Iterate can fire but kill cannot.

    Kill paths zeroed; Start moderate (enter running); Iterate high
    (so the no-op accumulates). Terminal-producing actions kept off
    so the scenario "running + never iterated" is observable.
    """
    if action in {"trip_kill", "propagate_kill"}:
        return 0.0
    if action == "start":
        return 5.0
    if action == "iterate":
        return 20.0
    if action in {"converge", "complete", "budget_kill"}:
        return 0.0
    return 1.0


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
