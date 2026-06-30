# Mutation fixtures — Conformance-Harness Quality Gate (PLAN-013 Phase D.8)

> **Note:** this directory was named ``mutations/`` until PLAN-019
> Phase 1 (P0-04). It was renamed to ``mutation_fixtures/`` so the
> Python package name stops colliding with
> ``.claude/hooks/tests/mutations/`` under pytest whole-tree collection.

Each formally-proved property in `docs/formal-verification/properties-
proved.md` has a paired mutation set. A mutation is a one-purpose bug
injected into the real `CircuitBreaker` via subclassing/method-override.
The paired conformance test runs its core assertion against the mutated
class and MUST fail — otherwise the assertion is decoration.

## Contract (every `mut_<prop>_<NN>_<slug>.py` must declare)

- `PROPERTY: str` — one of `"S1"`, `"S2"`, `"S3"`, `"L1"`.
- `DESCRIPTION: str` — one-sentence plain-English summary.
- `apply(cb_cls: type) -> type` — returns a NEW subclass of `cb_cls`
  with exactly one bug injected via a method override (or data-field
  tweak). The subclass must be instantiable with the same constructor
  signature as the original (no new required args). The override is
  the bug; nothing else.

## Naming

`mut_<property>_<NN>_<one-line-slug>.py` where `NN` starts at `01` and
zero-pads to 2 digits. Slug describes the bug surface:

- `threshold_off_by_one`, `window_size_change`, `counter_reset_missing`
- `race_window_widen`, `lock_omission`, `double_probe_swap`
- `audit_skipped`, `emit_before_state_update`, `action_string_mismatch`
- `timer_stop`, `transition_skip`, `terminal_state`, `clock_regression`

## Budget (per ADR-044 §Decision-drivers)

- S1: ≥6
- S2: ≥5
- S3: ≥5
- L1: ≥5

Total for breaker pilot: **21**.

## Adding a new mutation

1. Create `mutation_fixtures/breaker/mut_<prop>_<NN>_<slug>.py`
   following the contract above.
2. The mutation should model a single real-world regression:
   off-by-one, missing-reset, boolean-flip, early-return, race-window
   widen, lock-omission, wrong-action-string, wrong-emit-order,
   terminal-state introduction, clock-regression.
3. Verify manually that the mutation **does** break the corresponding
   conformance test:

```bash
python3 -m pytest tests/formal_verification/test_breaker_conformance.py::Test<Property> -v
```

4. Extend `docs/formal-verification/properties-proved.md` mutation
   count if the minimum budget rises. Extend
   `.claude/scripts/check-conformance-harness-mapping.py`
   `MIN_MUTATIONS` map if budget changes for an existing property.

## Why subclass + override (not AST patching)

- **Readable diff.** Each mutation is one method override in a
  self-contained Python file; the bug is literally visible.
- **Stdlib-only.** No `mutmut`, no external dep, no `ast.NodeTransformer`
  boilerplate, no source-patch string brittleness.
- **Deterministic.** Mutations are pinned at import time; no
  mid-process rewriting.
- **Robust under import paths.** The live `_breaker.py` module is
  imported once; mutations act on copies of the class object.

## Non-patching invariants

- **Never edit `.claude/hooks/_lib/adapters/live/_breaker.py`.** The
  harness tests ARE the enforcement — if you need to change behavior,
  change the real source and a mutation elsewhere (not the pilot one).
- **Never import from `tests/formal_verification/mutation_fixtures/`
  outside the harness.** Mutations are test-only fixtures.
- **Never run a mutation against production traffic.** All mutants are
  instantiated only in the test harness under TestEnvContext.

## References

- `docs/formal-verification/rationale.md` §Conformance harness rules.
- `docs/formal-verification/properties-proved.md` §2 mapping.
- `.claude/adr/ADR-044-formal-verification-pilot.md` §Decision-drivers.
- `PLAN-013` debate Round 1 consensus §C8 CRITICAL (conformance
  harness MANDATORY; model alone = theater).
