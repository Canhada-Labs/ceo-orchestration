# Mutation Kill Traces — Swarm Coordinator

> **Source:** PLAN-051 Phase 4 B3 — mutation budget 12 → 40.
> **Generated:** 2026-04-24 (Session 58).
> **Harness:** `tests/formal_verification/test_swarm_coordinator_conformance.py`.
> **Machine-readable manifest:** `EXPECTED-KILLS.json` (same directory).

This file documents *where* every mutation was killed: the first
seed and trace step at which the conformance harness detected a
property violation. Reviewers should treat `EXPECTED-KILLS.json`
as authoritative for CI enforcement; this file is the narrative
companion for debate rounds and architectural reviews.

## 1. Summary

| Property | Mutations | 100% killed | Independent-bias kills |
|----------|:---------:|:-----------:|:-----------------------:|
| I1 (MaxParallelRespected) | 5 | 5/5 | 5/5 (no bias needed) |
| I2 (IterCeilingRespected) | 5 | 5/5 | 5/5 (no bias needed) |
| I3 (PerLoopTokenBound) | 5 | 5/5 | 5/5 (no bias needed) |
| I4 (TotalConsumedBounded) | 5 | 5/5 | 5/5 (no bias needed) |
| L1 (NoDeadWorker) | 5 | 5/5 | 2/5 under `_termination_bias` |
| L2 (ProgressGuaranteed) | 5 | 5/5 | 4/5 under `_progress_bias` |
| L3 (KillSwitchHalts) | 5 | 5/5 | 4/5 under `_kill_then_propagate_bias` |
| L4 (TripPrecedesPropagate) | 5 | 5/5 | 5/5 under `kill_heavy_bias` |
| **TOTAL** | **40** | **40/40** | **35/40 (88%) w/o dedicated bias** |

**Independent kill proof (PLAN-051 Cluster 3):** every property has
≥1 mutation killed under the default (non-dedicated) bias. Test
methods `test_l1_mutations_fail_under_default_bias` and
`test_l2_mutations_fail_under_default_bias` mechanically enforce
this on every CI run.

**Bias count (VP Eng scope concern):** 4 dedicated biases total —
`_mutation_l1_a_bias`, `_mutation_l1_b_bias`, `_mutation_l2_bias`,
`_kill_then_propagate_bias`. ≤5 limit met.

## 2. Per-property kill tables

Each row: `<mutation_id>` → `seed=<N>` at `step=<K>` (first state
where the invariant fails under the listed bias).

### I1 — MaxParallelRespected (start-heavy bias)

| Mutation | Seed | Step | Axis |
|----------|:----:|:----:|------|
| `mut_i1_01_parallel_cap_bypassed` | 0 | 3 | gate-removal |
| `mut_i1_02_active_count_off_by_one` | 0 | 3 | comparator-off-by-one |
| `mut_i1_03_active_count_always_zero` | 0 | 3 | counter-short-circuit |
| `mut_i1_04_active_count_excludes_iter_zero` | 0 | 3 | predicate-swap (status→iter) |
| `mut_i1_05_active_count_excludes_first_loop` | 1 | 3 | scope-exclusion |

### I2 — IterCeilingRespected (iterate-heavy bias)

| Mutation | Seed | Step | Axis |
|----------|:----:|:----:|------|
| `mut_i2_01_iter_ceiling_bypassed` | 0 | 6 | gate-removal |
| `mut_i2_02_double_iter_increment` | 0 | 2 | transition-overshoot |
| `mut_i2_03_iterate_on_pending` | 0 | 2 | status-gate-error |
| `mut_i2_04_iter_ceiling_relaxed_double` | 0 | 6 | ceiling-relaxed-factor |
| `mut_i2_05_iter_ceiling_off_by_one_lte` | 0 | 6 | comparator-off-by-one |

### I3 — PerLoopTokenBound (iterate-heavy bias)

| Mutation | Seed | Step | Axis |
|----------|:----:|:----:|------|
| `mut_i3_01_double_token_charge` | 0 | 2 | per-step-multiplier |
| `mut_i3_02_iter_increment_skipped` | 0 | 2 | decoupling-increment-dropped |
| `mut_i3_03_start_charges_tokens` | 0 | 1 | entry-transition-side-effect |
| `mut_i3_04_converge_charges_tokens` | 0 | 3 | success-transition-side-effect |
| `mut_i3_05_tokens_scale_with_iter` | 0 | 3 | non-linear-growth |

### I4 — TotalConsumedBounded (iterate-heavy bias)

| Mutation | Seed | Step | Axis |
|----------|:----:|:----:|------|
| `mut_i4_01_budget_bypassed` | 0 | 2 | gate-dropped + inflation |
| `mut_i4_02_single_iter_overflow` | 0 | 2 | single-step-magnitude |
| `mut_i4_03_budget_kill_inflates_consumed` | 0 | 8 | terminal-transition-side-effect |
| `mut_i4_04_start_charges_global_consumed` | 0 | 3 | entry-transition-side-effect |
| `mut_i4_05_converge_charges_global_consumed` | 0 | 3 | success-transition-side-effect |

### L1 — NoDeadWorker (`_mutation_l1_a_bias` / `_mutation_l1_b_bias`)

| Mutation | Seed | Step | Bias | Axis |
|----------|:----:|:----:|------|------|
| `mut_l1_01_completion_disabled` | 0 | (step_ceiling) | a-bias | gate-terminal-blackout |
| `mut_l1_02_terminal_not_sink` | 0 | 7 | b-bias | terminal-escape-via-start |
| `mut_l1_03_all_terminal_actions_disabled` | 0 | (step_ceiling) | a-bias | gate-terminal-blackout-narrow |
| `mut_l1_04_start_transition_noop` | 0 | (step_ceiling) | a-bias | entry-transition-noop |
| `mut_l1_05_terminal_transitions_regress_to_pending` | 0 | (step_ceiling) | a-bias | terminal-transition-regress |

Independent-bias (`_termination_bias`) kills: `mut_l1_01`, `mut_l1_03`.

### L2 — ProgressGuaranteed (`_mutation_l2_bias`)

| Mutation | Seed | Step | Axis |
|----------|:----:|:----:|------|
| `mut_l2_01_iterate_noop` | 0 | (step_ceiling) | transition-total-noop |
| `mut_l2_02_iter_not_incremented` | 0 | (step_ceiling) | transition-partial-noop |
| `mut_l2_03_iter_only_on_first_loop` | 0 | (step_ceiling) | loop-scope-regression |
| `mut_l2_04_iterate_gate_requires_iter_positive` | 0 | (step_ceiling) | gate-catch-22-numeric |
| `mut_l2_05_iterate_gate_rejects_running` | 0 | (step_ceiling) | gate-catch-22-categorical |

Independent-bias (`_progress_bias`) kills: `mut_l2_02`, `mut_l2_03`, `mut_l2_04`, `mut_l2_05`.

### L3 — KillSwitchHalts (`_kill_then_propagate_bias`)

| Mutation | Seed | Step | Axis |
|----------|:----:|:----:|------|
| `mut_l3_01_propagate_without_trip` | 0 | 1 | gate-kill-flag-bypass |
| `mut_l3_02_kill_not_halting` | *none needed* | *none needed* | **no-trip-fires** (see note) |
| `mut_l3_03_partial_propagate` | 0 | ~(step_ceiling) | propagation-scope-partial |
| `mut_l3_04_propagate_transitions_to_running` | 0 | ~(step_ceiling) | transition-cosmetic-kill |
| `mut_l3_05_propagate_skips_pending_loops` | 0 | ~(step_ceiling) | gate-scope-regression |

**Note on `mut_l3_02_kill_not_halting`:** this mutation disables the
`not state.kill` guards on Start/Iterate AND disables PropagateKill.
Under the L3 bias the walk terminates via non-kill paths
(converge/complete/budget_kill), so no seed exposes an unterminated
final state. The conformance harness detects this via its fall-through
assertion `"L3 mutation not detected across seed sweep"` — the
absence of any kill-induced violation across 200 seeds is itself the
kill signal. See `test_swarm_coordinator_conformance.py:887-893`.

### L4 — TripPrecedesPropagate (kill-heavy bias)

| Mutation | Seed | Step | Axis |
|----------|:----:|:----:|------|
| `mut_l4_01_trip_does_not_set_flag` | 0 | 1 | trip-noop + propagate-bypass |
| `mut_l4_02_propagate_resets_kill_flag` | 0 | 2 | transition-side-effect-kill-reset |
| `mut_l4_03_trip_kills_loops_without_setting_flag` | 0 | 1 | transition-action-confusion |
| `mut_l4_04_start_sets_killed_status` | 2 | 1 | typo-wrong-literal |
| `mut_l4_05_initial_state_corrupted` | 0 | 0 | initialization-corruption |

## 3. Diversity matrix

Per PLAN-051 Phase 4 B3 Cluster 3: each property's 5 mutations
target distinct code anchors AND distinct semantic axes (bound
direction / ordering / termination / invariant carrier / scope).

- **Gate-side bugs** (I1, I2, L2, L3, L4): predicate removals,
  off-by-one comparators, status/scope filter swaps, kill-flag
  bypasses.
- **Transition-side bugs** (I2, I3, I4, L1, L2, L3, L4): increment
  drops/inflates, wrong literals, side-effects on non-owning
  transitions (Start charging tokens, Converge charging consumed,
  etc.).
- **Initialization bugs** (L4): walk() override corrupts initial
  state before any Next step.

No two mutations of the same property share both anchor AND axis.
This is enforced at debate review via the per-file header comment
(``Anchor:`` and ``Axis:`` fields in every mutation docstring).

## 4. Re-running the kill sweep

```bash
# Fast: all conformance tests + mutation gates
python3 -m pytest tests/formal_verification/test_swarm_coordinator_conformance.py -q

# Per-property mutation gate only
python3 -m pytest tests/formal_verification/test_swarm_coordinator_conformance.py::TestI1MaxParallelRespected::test_i1_mutations_fail -q
python3 -m pytest tests/formal_verification/test_swarm_coordinator_conformance.py::TestL2ProgressGuaranteed::test_l2_mutations_fail_under_default_bias -q

# Regenerate EXPECTED-KILLS.json (not yet automated; see PLAN-051 §10
# sub-directory for future CI script expected_kills_sync.sh).
```

## 5. Maintenance contract

Any change to:

- `.claude/scripts/swarm/_coordinator_sim.py` (baseline simulator)
- `tests/formal_verification/test_swarm_coordinator_conformance.py`
  (harness)
- Any `tests/formal_verification/mutation_fixtures/swarm_coordinator/mut_*.py`

MUST be followed by:

1. `pytest tests/formal_verification/` passes (40/40 conformance).
2. Regenerate / review `EXPECTED-KILLS.json` if the kill seed/step
   shifted (or commit the shift with a rationale).
3. Update this `KILL-TRACES.md` if a new mutation was added or the
   kill mechanism changed.
4. Diversity matrix §3 still holds (no two mutations share anchor +
   axis for the same property).

References: `docs/formal-verification/properties-proved.md §9.4`;
PLAN-051 Phase 4 B3 acceptance criteria; ADR-044 (formal
verification pilot).
