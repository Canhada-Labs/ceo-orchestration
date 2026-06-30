# Formal Verification Pilot — Index

**Scope:** PLAN-013 Phase D (2 weeks, parallel track with red-team
eval). Proves ≥3 safety properties + ≥1 liveness property on a
selected framework state machine, backed by an executable
conformance harness per ADR-044.

**Current state (2026-04-16):** Phase D.1 DONE — state machine
selected (circuit breaker), tool selected (TLA+/TLC). Phase D.2–D.4
scheduled.

## Artifacts (ownership + status)

| File                            | Phase   | Status   | Owner archetype           |
|---------------------------------|---------|----------|---------------------------|
| `rationale.md`                  | D.1     | DONE     | QA Architect + Security   |
| `breaker.tla` (+ `.pcal`)       | D.2     | pending  | Staff Backend + QA        |
| `properties-proved.md`          | D.3     | pending  | QA Architect              |
| `../../.claude/adr/ADR-044-*`   | D.4     | PROPOSED | CEO + VP Engineering      |
| `../../.github/workflows/formal-verify.yml` | D.6 | pending | DevOps                |

## Pilot target (from `rationale.md`)

- **State machine:** ADR-040 §2 Live-Adapter Circuit Breaker.
- **Tool:** TLA+ with TLC model-checker; PlusCal for readability.
- **Properties:** 3 safety (S1 threshold-open, S2 half-open
  singleton, S3 transition audit) + 1 liveness (L1 eventually
  heal).
- **Conformance harness:** 4 property-based tests under
  `tests/formal_verification/` with ≥21 mutations.
- **Fallback:** Alloy-modeled debate convergence (ADR-032) if week-1
  TLA+ modeling blocks.

## Reading order for reviewers

1. `rationale.md` — decision log + property statements.
2. ADR-044 — accepted decision (§Decision becomes non-empty in
   Phase D.4).
3. `breaker.tla` / `breaker.pcal` — formal spec (Phase D.2).
4. `properties-proved.md` — TLC proof output + conformance-test
   mapping (Phase D.3).
5. `tests/formal_verification/test_breaker_conformance.py` — real
   Python conformance harness (Phase D.3).

## Conformance harness contract (summary)

Every proved property MUST have:

1. An executable property-based test (`tests/formal_verification/`).
2. `TestEnvContext` env isolation (per PLAN-013 §S11).
3. A mutation budget of ≥5 (`tests/formal_verification/mutations/`).
4. A mapping row in `properties-proved.md` linking property →
   test → impl source line + TLC-log-hash.

See `rationale.md` §Conformance harness contract for binding
details. See ADR-044 §Decision-drivers for the TLA+-trap
mitigation rationale.

## Non-goals

- NOT end-to-end formal verification of the framework. Pilot is
  scoped to ≤3 state machines; PLAN-014+ may expand.
- NOT model-only proofs (rejected by consensus §C8 CRITICAL).
- NOT stdlib-violation for runtime — TLA+ tooling runs in CI only;
  hook/script runtime remains stdlib-only per ADR-002.

## References

- ADR-040 — Live Adapter Activation Contract §2 (breaker spec).
- ADR-044 — Formal Verification Pilot (ACCEPTED after Phase D.4).
- PLAN-013 Phase D (full scope).
- PLAN-013 debate Round 1 consensus §C8 (conformance harness
  mandatory).
- `rationale.md` (Phase D.1 output — this directory).
- `.claude/scripts/red-team-eval.py` (parallel Phase D.5 track —
  adversarial red-team eval; see sibling directory).
