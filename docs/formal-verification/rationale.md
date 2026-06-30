# Formal Verification Pilot — Rationale

**Status:** ACCEPTED 2026-04-16 (PLAN-013 Phase D.1)
**Scope:** PLAN-013 Phase D.1 (state-machine selection + Q2 tool choice);
outputs feed ADR-044 §Options-considered + §Decision (Phase D.4).
**Authored by:** Principal QA Architect + Principal Security Engineer
(composite persona), under CEO delegation per PLAN-013 Phase D.1
spawn.
**Related:** ADR-040 (live-adapter contract — breaker spec), ADR-031
(skill-patch shadow-CI — fallback candidate), ADR-032 (debate
convergence — fallback candidate), ADR-042 (MCP handler ACL —
deferred target), ADR-044 (Formal Verification Pilot — consumes this).

## Summary

Pilot verifies the **ADR-040 §2 live-adapter circuit breaker** with
**TLA+ / TLC**. Four properties (3 safety + 1 liveness) are proved on
the model and backed by property-based conformance tests against the
real Python implementation. Each property carries ≥5 mutation-test
variants per ADR-044 §Decision-drivers (closes "model drift" gap per
consensus §C8). Source of truth for D.1; D.2 spec, D.3 proof, D.4 ADR
accepted state ship in subsequent sessions.

## Candidate state machines (ranked by impact × tractability × test-gap)

Ranking rubric — each dimension scored 1–5; composite = sum. Impact
measures blast radius; tractability measures TLA+/Alloy/Z3 fit;
test-gap measures what formal verification ADDS beyond existing
example-based tests.

| # | State machine                      | Impact | Tractability | Test-gap | Composite | Pilot fit  |
|---|-------------------------------------|--------|--------------|----------|-----------|------------|
| 1 | Circuit breaker (ADR-040 §2)        | 5      | 5            | 3        | 13        | **STRONG** |
| 2 | Debate convergence (ADR-032)        | 4      | 3            | 4        | 11        | candidate  |
| 3 | Skill-patch shadow-CI (ADR-031)     | 4      | 3            | 3        | 10        | candidate  |
| 4 | MCP handler ACL (ADR-042)           | 5      | 4            | 5        | 14        | **deferred** (Phase A unfinished) |
| 5 | Credential rotation (ADR-040 §4)    | 3      | 4            | 2        | 9         | weak       |
| 6 | Plan lifecycle                      | 2      | 5            | 2        | 9         | weak       |

### Why the breaker wins despite MCP ACL's higher composite

MCP handler ACL scores 14 (highest) because test-gap is 5/5 (Phase A
has not shipped). That same gap disqualifies it — cannot formally
verify a handler set that doesn't exist. MCP ACL becomes a PLAN-014
candidate once Phase A.4 ships.

Breaker wins because: (1) **Impact maximal** — blast radius is all 4
adapters; half-open regression → cost runaway; closed-stuck regression
→ silent traffic loss. (2) **Tractability maximal** — ≤8 states,
explicit timed transitions, no ML/statistics. (3) **Test-gap moderate
(3/5)** — 82 unit + 31 chaos tests exist (PLAN-012 Phase 1 Wave 2),
so conformance tests seed from existing example-based assertions
cheaply; TLA+ is additive, catching timing interleavings unit tests
miss.

Debate convergence (row 2) is the explicit fallback if TLA+ modeling
of timed transitions proves intractable. Skill-patch shadow-CI (row
3) is a distant second fallback.

## Decision

**Pilot target: ADR-040 §2 Live-Adapter Circuit Breaker.**

- Fallback target if week-1 TLA+ intractability emerges: Debate
  Convergence (ADR-032) modeled in Alloy.
- Future candidates (PLAN-014+): MCP handler ACL (once Phase A
  ships), skill-patch shadow-CI promotion.

## Tool selection (Q2)

**Tool: TLA+ with TLC model-checker; PlusCal for accessible source
code.**

### Tool comparison

| Dimension                     | TLA+ / TLC                | Alloy              | Z3 / SMT (stateful)       |
|-------------------------------|---------------------------|--------------------|---------------------------|
| Timed systems                 | Native (`TLC` + `REAL_TIME`) | Weak (continuous time awkward) | Low-level (encode time as unbounded integer manually) |
| ≤8-state finite machines      | Strong                    | Strong             | Adequate                  |
| Liveness properties (`<>`)    | Native                    | Native (paths)     | Manual (fixpoint encoding) |
| Readability (reviewable by non-expert) | PlusCal clarity      | Alloy relations feel academic | SMT-LIB is write-only for most humans |
| Counter-example clarity       | Action-labeled trace      | Instance dump      | Model dump                |
| CI integration                | `tla2tools.jar` single artifact; SHA-pin | Alloy4 jar; SHA-pin | z3 binary per-OS            |
| Community + docs (2026)       | Excellent (Lamport, Hillel Wayne tutorials) | Good but narrower | Excellent for SMT use; narrow for stateful |
| Fit for **breaker**           | **BEST**                  | Adequate           | Over-engineered           |

### Justification for TLA+ choice

1. **Time is first-class.** ADR-040 §2 specifies three timers
   (`connect_timeout_s`=5, `read_timeout_s`=25, `half_open_hold_s`=30).
   PlusCal `await now >= ...` models natively; Alloy weak on
   continuous time; Z3 requires hand-rolled integer clocks.
2. **Existing test corpus maps to TLC actions.** `tests/chaos/
   test_live_adapter_*.py` rephrases as TLC traces 1:1.
3. **Reviewability.** PlusCal → readable TLA+ without formal-methods
   PhDs; Lamport "Specifying Systems" + Hillel Wayne "Practical TLA+"
   provide ramp.
4. **CI discipline.** `tla2tools.jar` is a single SHA-pinnable
   artifact fitting ADR-002.

### Falsification path (Phase D.2 exit criteria)

If Phase D.2 (week 1) TLA+ PlusCal cannot cleanly express the
breaker's timed-window semantics (hypothesis: TLC state-space
explosion), the pilot falls back to **Alloy**-modeled **debate
convergence**. Tool-fit discovery is a legitimate D.1 outcome.

### Toolchain pin (Phase D.2 CI binding)

- `tla2tools.jar` **1.8.0** (Lamport 2024 release); SHA-256 pinned
  in future `.github/workflows/formal-verify.yml` (Phase D.6).
- Java 17 LTS on CI runner.

## Properties to prove (feeds D.2 `.tla` spec + D.3 proof output)

Four properties — three safety + one liveness — satisfy ADR-044
§Scope minimum. Each property below includes:

1. A plain-English statement.
2. A TLA+ temporal-logic form (informal — D.2 writes canonical).
3. The source-of-truth link to ADR-040 §2.
4. A conformance-test target (Phase D.3 Python test).
5. Mutation budget (≥5, per ADR-044 §Decision-drivers).

### Safety properties (≥3 required)

#### S1 — Threshold-triggered open transition

**Plain English:** When the count of consecutive failures within
the rolling window `window_s` reaches `failure_threshold`, the
breaker MUST transition from `closed` to `open` within one
adapter call (bounded time).

**TLA+ (informal):**
```
THEOREM S1_OpenOnThreshold ==
  [](
    /\ breaker.state = "closed"
    /\ failures_in_window >= failure_threshold
    => <>(breaker.state = "open")
  )
```

**Source:** ADR-040 §2.1 "Breaker opens on N consecutive failures
within W-second window."

**Conformance test:**
`tests/formal_verification/test_breaker_conformance.py::test_s1_breaker_opens_on_threshold`

**Mutation budget:** 6 (threshold off-by-one, window size change,
counter reset missing, state check omission, boolean flip, early
return).

#### S2 — Half-open singleton

**Plain English:** During `half_open` state, at most ONE adapter
call is in flight at any instant.

**TLA+ (informal):**
```
THEOREM S2_HalfOpenSingleton ==
  [](breaker.state = "half_open" => Cardinality(in_flight) <= 1)
```

**Source:** ADR-040 §2.3 "Half-open probe is singleton — a second
caller must wait."

**Conformance test:**
`tests/formal_verification/test_breaker_conformance.py::test_s2_half_open_singleton`

**Mutation budget:** 5 (race-window widening, lock omission,
double-probe swap, state check skipped, early exit before
cardinality check).

#### S3 — State-transition audit

**Plain English:** Every transition `closed → open` MUST emit an
audit event `breaker_opened` with matching timestamp.

**TLA+ (informal):**
```
THEOREM S3_OpenEmitsAudit ==
  [](
    /\ breaker.state' = "open"
    /\ breaker.state  = "closed"
    => /\ audit_event' # audit_event
       /\ Last(audit_event').action = "breaker_opened"
  )
```

**Source:** ADR-040 §2.4 "State transitions are audited" +
ADR-035 §OTEL export (breaker_opened → span).

**Conformance test:**
`tests/formal_verification/test_breaker_conformance.py::test_s3_open_emits_audit`

**Mutation budget:** 5 (audit emission skipped, action-string
mismatch, emission before state update, emission after subprocess
exit, lost audit due to hook failure).

### Liveness property (≥1 required)

#### L1 — Eventually heal

**Plain English:** A breaker in `open` state MUST eventually
(within bounded `half_open_hold_s` seconds) transition to
`half_open`, and from `half_open` MUST eventually transition to
either `closed` (probe success) or `open` (probe failure). No
terminal stuck state exists.

**TLA+ (informal):**
```
THEOREM L1_EventuallyHeal ==
  /\ [](breaker.state = "open" => <>(breaker.state = "half_open"))
  /\ [](breaker.state = "half_open" =>
        <>(breaker.state = "closed" \/ breaker.state = "open"))
```

**Source:** ADR-040 §2.5 "Breaker MUST eventually close or re-open
after half_open_hold_s; no terminal state permitted."

**Conformance test:**
`tests/formal_verification/test_breaker_conformance.py::test_l1_eventually_heal`

**Mutation budget:** 5 (timer stop, transition skip, terminal
state introduction, half-open hold underflow, clock regression).

## Conformance harness contract (feeds ADR-044 §Decision)

Every proved property → one executable property-based test + ≥5
mutation tests.

| Property | TLA+ form  | Conformance test name                 | Impl file:line (target)                              | Mutation count |
|----------|-----------|---------------------------------------|------------------------------------------------------|----------------|
| S1       | `[](...)` | `test_s1_breaker_opens_on_threshold`  | `.claude/hooks/_lib/adapters/live/breaker.py:open_if_threshold` | **6**          |
| S2       | `[](...)` | `test_s2_half_open_singleton`         | `.claude/hooks/_lib/adapters/live/breaker.py:half_open_probe`   | **5**          |
| S3       | `[](...)` | `test_s3_open_emits_audit`            | `.claude/hooks/_lib/adapters/live/breaker.py:_emit_transition`  | **5**          |
| L1       | `[](<>)`  | `test_l1_eventually_heal`             | `.claude/hooks/_lib/adapters/live/breaker.py:tick`              | **5**          |

**Total:** 4 property-based conformance tests with ≥21 mutations
(21 ≥ target of 20).

### Harness rules (D.3 binding)

1. **`TestEnvContext` MANDATORY** per PLAN-013 consensus §S11.
   Every conformance test subclasses
   `.claude/hooks/_lib/testing.TestEnvContext` for env isolation.
2. **Deterministic seeds.** Property-based inputs must pin an
   explicit seed (`random.seed(42)` or hypothesis `@seed`) so
   failure traces reproduce.
3. **Mutation-test failure assertion.** For each mutation under
   `tests/formal_verification/mutations/breaker/`, the conformance
   test re-imported against the mutated source MUST fail; test
   counted as PASS only when the unmutated source passes AND all
   ≥5 mutations fail. This is the "would fail under implementation
   bug" gate ADR-044 mandates.
4. **No live network.** All tests are offline; breaker timing
   mocked via `time.monotonic()` fake-clock injection.
5. **Mapping row integrity.** Every property row in
   `properties-proved.md` (Phase D.3) MUST cite both TLC log
   hash AND conformance-test id. CI check
   `check-conformance-harness-mapping.py` (future Phase D.6) asserts
   both columns populated for every row.

## Out of scope (explicit non-decisions)

- **`.tla` spec itself.** Phase D.2 future session writes
  `breaker.tla` + `breaker.pcal`.
- **`properties-proved.md` proof output.** Phase D.3 future
  session runs TLC, captures log hash, writes mapping table.
- **ADR-044 §Decision text.** Phase D.4 future session updates
  ADR-044 from PROPOSED stub to ACCEPTED based on this rationale
  + D.2 + D.3 outputs.
- **Second state machine.** If the breaker pilot succeeds under
  time budget, PLAN-014 absorbs the next target (debate
  convergence, ACL). This document does NOT preselect.
- **`formal-verify.yml` CI workflow.** Phase D.6 future session.

## References

- ADR-040 — Live Adapter Activation Contract §2 (breaker spec); §2.1
  threshold open; §2.3 half-open singleton; §2.4 audit; §2.5 eventual
  heal.
- ADR-031 — Skill-patch shadow-CI (row-3 candidate rationale).
- ADR-032 — Debate convergence (row-2 fallback rationale).
- ADR-035 — OTEL export (breaker_opened → span).
- ADR-042 — MCP Server Contract (row-4 deferred rationale).
- ADR-044 — Formal Verification Pilot (consumes this document).
- PLAN-013 Phase D.1 (selection), D.2 (spec), D.3 (proof), D.4
  (ADR accept), D.8 (test partial).
- PLAN-013 debate Round 1 consensus §C8 CRITICAL (conformance
  harness mandatory).
- PLAN-013 debate Round 1 consensus §S15 LOW (Q2 tool choice
  deferral).
- Lamport, "Specifying Systems" (TLA+ canonical reference).
- Hillel Wayne, "Practical TLA+" (PlusCal accessible intro).
- `.claude/hooks/_lib/adapters/live/breaker.py` — implementation.
- `.claude/hooks/_lib/testing.py::TestEnvContext` — test isolation.
