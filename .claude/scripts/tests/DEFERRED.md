# Deferred tests — red-team-eval.py (Phase D.8 full scope)

**Status:** DEFERRED to a future session where D.2 TLA+ spec and
D.3 proof output land.

## What this session shipped

- `.claude/scripts/tests/test_red_team_eval.py` — **SMOKE** tests
  only (framework self-test). Covers:
  1. Fixture loader (schema validation + error paths)
  2. Evaluator (pass / fail / skip-deferred paths for 4 targets)
  3. Byte-identity ledger (drift detection + correct-hash accept)
  4. Issue payload idempotence (same fingerprint ⇒ same title)
  5. Flake budget (threshold triggers quarantine)
  6. Fork-PR guard logic (3 event classes)
  7. CLI dry-run (counts + kill-switch + target filter)
  8. Minimal YAML parser (round-trip + list-of-mappings)
  9. JUnit XML output shape (3 outcomes)
  10. Behavior matcher (all 5 MUST_* codes)
  11. Quarantine-skip (pre-seeded ledger → runner skips fixture)

Total: 11 test classes, 25 test methods, all using
`TestEnvContext` from `_lib/testing.py` per PLAN-013 consensus §S11.

## What is deferred

PLAN-013 Phase D.8 acceptance criterion specifies "**+40 tests**
(raised from 20): ... property-based conformance assertions per
D.3 mapping." Those 40 tests require:

1. **D.1 output** (`docs/formal-verification/rationale.md`) —
   **DONE this session** (state machine selected = live-adapter
   circuit breaker; tool = TLA+).
2. **D.2 output** (`docs/formal-verification/breaker.tla`) —
   **PENDING** future session. TLA+ PlusCal spec of ADR-040 §2
   breaker state machine.
3. **D.3 output** (`docs/formal-verification/properties-proved.md`) —
   **PENDING** future session. TLC proof run log + property-to-test
   mapping table.
4. **Conformance harness directory** —
   `tests/formal_verification/test_breaker_conformance.py` —
   **PENDING**. Property-based Python tests asserting the real
   `.claude/hooks/_lib/adapters/live/breaker.py` honors the proved
   properties S1, S2, S3, L1.
5. **Mutation directory** —
   `tests/formal_verification/mutations/breaker/` — **PENDING**.
   ≥21 mutations across the four properties (≥5 per property +
   one extra on S1). Each mutation lives as a Python file that
   re-imports the breaker source with a targeted modification; the
   conformance test must FAIL against the mutated source (this is
   the "would fail under implementation bug" gate ADR-044
   mandates).

## Why deferred — scope honesty

`red-team-eval.py` and the fixture corpus are standalone
adversarial tooling. They can (and should) ship NOW regardless of
formal-verification progress. The 40 conformance tests, in
contrast, are coupled to Phase D.2 TLA+ output: you cannot write a
`test_s1_breaker_opens_on_threshold` without first having a `.tla`
spec that DEFINES S1. Running D.8 full scope in this session would
mean writing tests against properties that haven't been
formally stated yet — which would bake in the "model drift from
implementation" bug consensus §C8 identified.

PLAN-013 Phase D acceptance (§Goals) says formal verification is a
**pilot** with ≥3 safety + ≥1 liveness property. All four
properties (S1, S2, S3, L1) are STATED in
`docs/formal-verification/rationale.md` §Properties — but they are
stated informally. Canonical TLA+ form is D.2; proof is D.3;
conformance is D.4 + D.8.

## Acceptance criterion for a future session

When Phase D.2 + D.3 are done, that session's agent ships:

- `tests/formal_verification/__init__.py`
- `tests/formal_verification/test_breaker_conformance.py`
  - ≥4 top-level property tests mapping to S1/S2/S3/L1
  - TestEnvContext inheritance (§S11)
  - Deterministic seed pinning
  - Fake-clock injection (no real `time.sleep`)
- `tests/formal_verification/mutations/breaker/*.py` (≥21 mutations)
- `.claude/scripts/check-conformance-harness-mapping.py` — CI
  check: every property row in `properties-proved.md` MUST cite
  (a) TLC log hash AND (b) conformance-test id.

Total new test count expected: ≥30 (aiming for 40 per Phase D.8
target — 10 conformance pytest-param cases + 21 mutation cases =
31 at minimum; additional variant tests push to 40).

## References

- PLAN-013 Phase D.8 (full scope).
- PLAN-013 consensus §C8 CRITICAL (conformance harness mandatory).
- PLAN-013 consensus §S11 (`TestEnvContext` mandatory).
- ADR-044 §Decision-drivers (mutation budget ≥5 per property).
- `docs/formal-verification/rationale.md` §Properties to prove.
- `test_red_team_eval.py` (this session's smoke coverage).
