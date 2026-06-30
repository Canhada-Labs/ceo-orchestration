"""Swarm-coordinator mutation set — PLAN-050 Phase 7 final tranche.

Each mutation module is self-contained and exposes:

- ``PROPERTY``: one of ``"I1" | "I2" | "I3" | "I4" | "L1" | "L2" | "L3" | "L4"``
  — matches the 4 C4-mandated safety + 4 support invariants mapped in
  ``docs/formal-verification/properties-proved.md`` §9.1.
- ``DESCRIPTION``: plain-English summary of what the mutation changes.
- ``apply(sim_cls)``: takes the unmutated ``_SwarmSimulator`` class and
  returns a *new* mutated subclass with exactly one bug injected. The
  conformance test runs its seed sweep against the returned class and
  asserts the property assertion fails (raises ``AssertionError``) for
  the mutation to count as killed.

## Apply-a-subclass pattern

Every mutation returns a subclass of ``_SwarmSimulator`` that overrides
``_apply_action`` or ``_enabled_actions`` (or both) to inject the bug.
This is simpler and more reviewable than AST patching: the mutation
diff is one method override, the test harness needs no source loader,
and each mutation is plain deterministic Python.

## Budget

Expanded tranche ships **40 mutations** covering all 8 invariants (5
per property) per PLAN-051 Phase 4 B3:

| Property | Count | Axes covered |
|----------|-------|--------------|
| I1 | 5 | gate-removal, comparator-off-by-one, counter-short-circuit, predicate-swap, scope-exclusion |
| I2 | 5 | gate-removal, transition-overshoot, status-gate-error, ceiling-relaxed-factor, comparator-off-by-one |
| I3 | 5 | per-step-multiplier, decoupling, 2× wrong-transition-side-effect, non-linear-growth |
| I4 | 5 | gate+inflation, single-step-magnitude, 3× transition-side-effect (budget/start/converge) |
| L1 | 5 | gate blackout (wide+narrow), terminal-escape-via-start, entry-noop, terminal-regress |
| L2 | 5 | transition-total-noop, partial-noop, loop-scope, gate-catch-22 (numeric+categorical) |
| L3 | 5 | kill-flag-bypass, gate-ignores-kill, scope-partial, cosmetic-kill, gate-scope-regression |
| L4 | 5 | trip-noop+bypass, kill-reset, action-confusion, typo-literal, init-corruption |

See `KILL-TRACES.md` for per-mutation seed/step evidence and
`EXPECTED-KILLS.json` for the CI-enforced manifest. Diversity matrix
verified: no two mutations of the same property share both anchor
and axis.

Independent kill proof (PLAN-051 Cluster 3): every property has ≥1
mutation killed under the default (non-dedicated) bias; see
`test_l1_mutations_fail_under_default_bias` and
`test_l2_mutations_fail_under_default_bias` for the mechanical
enforcement.
"""

from __future__ import annotations
