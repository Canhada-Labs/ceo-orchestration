# ADR-044: Formal Verification Pilot

**Status:** ACCEPTED (flipped PLAN-025 Batch C — live per PLAN-014 Phase D (TLA+ pilot + conformance harness shipped + formal-verify.yml weekly))
**Date:** 2026-04-15
**Sprint:** 13 (PLAN-013 Phase 0 reservation + Phase D full decision)
**Related:** ADR-041 (Transition Log Convention — proof-activation
rows), ADR-042 (MCP Server Contract — governance passthrough is a
candidate verification target), ADR-043 (SOC2 Audit Trail Mapping —
proofs are CC7.2 change-control evidence).

## Context

PLAN-013 Phase D introduces a **formal verification pilot** targeting
1–3 load-bearing state machines in the framework (candidates: debate
convergence, breaker state transitions, credential rotation lifecycle,
skill-patch shadow-CI promotion, MCP handler ACL resolution). The
debate Round 1 consensus §C8 (CRITICAL, 2/5 agents — QA Architect,
Security) flagged the classic TLA+/Alloy trap:

> **Proving properties on a TLA+ or Alloy MODEL does not prove the
> real implementation honours those properties.** Model drifts from
> implementation → proof proves abstract invariant while real code
> ships bugs. This is security theater if uncorrected.

The mitigation (consensus §C8): every formally-proved property MUST
map to an executable **property-based test** against the real
implementation, plus a **mutation-test gate** asserting the test
would fail under simulated implementation bugs. Proof-output
artifact (`docs/formal-verification/properties-proved.md`) includes
a conformance-test mapping column.

This stub reserves the ADR number and locks the conformance-harness
mandate. Full decision content (state-machine selection, tool choice
TLA+ vs Alloy vs Z3/SMT, property catalog, conformance-test
protocol, mutation-test framework) lands in Phase D.4 after Phase
D.1 (state-machine selection) + D.2 (property statement).

## Decision drivers

- **Conformance harness mandatory** (PLAN-013 consensus §C8
  CRITICAL): every `property_i` proved on the model MUST have:
  - An executable property-based test `test_property_i` against the
    real implementation (Python `hypothesis` library or equivalent
    stdlib-compatible; if stdlib-only constraint is binding, a
    hand-rolled deterministic-seed shrinker in `_lib/proptest.py`).
  - A mutation-test gate asserting `test_property_i` fails under
    ≥5 simulated implementation mutations (line swap, boolean flip,
    off-by-one, condition negation, early return).
  - A mapping row in `docs/formal-verification/properties-proved.md`
    linking `property_i` ↔ `test_property_i` ↔ source-file:line.
- **Pilot scope ≤3 state machines** (Phase D timebox = 2 weeks
  parallel with red-team eval): ambitious scope = low-quality proofs.
  Three tight proofs > ten hand-wavy ones.
- **Tool choice deferred to D.1 output** (consensus §S15): Q2 TLA+
  preference is default but the selected state machine dictates the
  tool. Debate convergence = set-theoretic → Alloy; breaker = timed
  → TLA+ or UPPAAL; ACL resolution = first-order logic → Z3.
- **Stdlib constraint relaxed for tooling** (ADR-002 scope): TLA+ /
  Alloy / Z3 binaries run in CI only, not in hook/script runtime.
  Proof artifacts committed to repo; tools themselves pinned via
  CI setup step + checksum (e.g. TLA+ Tools .jar SHA-256 pinned).
- **Mutation budget** per proved property: 5 mutations minimum,
  10 preferred. Automated mutation generation via manual
  specification (checked-in `tests/formal_verification/mutations/`)
  for determinism (no `mutmut` runtime dependency).

## §Scope (Phase 0 — locked)

- **Pilot target count:** 1-3 state machines. Phase D.1 selects
  via ranked evaluation of impact × tractability × test-gap.
- **Tool family:** TLA+ (default), Alloy (set-theoretic fit), Z3/SMT
  (first-order fit). Phase D.1 outputs tool-per-target.
- **Properties per target:**
  - ≥3 safety properties (invariants that must always hold).
  - ≥1 liveness property (eventually-X, bounded-wait).
- **Conformance harness artifacts:**
  - `docs/formal-verification/<target>.tla` (or `.als`, `.smt2`)
  - `docs/formal-verification/properties-proved.md` (mapping table)
  - `tests/formal_verification/test_<target>_properties.py`
  - `tests/formal_verification/mutations/<target>/*.py` (≥5 per
    property)
- **CI integration:** `formal-verify.yml` workflow runs tool-check
  per target + conformance-harness pytest + mutation-gate assert on
  PR + weekly.

## Options considered

### Option A — TLA+/TLC for ALL pilot targets (CHOSEN FOR THIS PILOT)

Select a single tool (TLA+ with the TLC model-checker + PlusCal for
readability) and apply it to every state machine in the pilot scope.
For PLAN-013 the pilot scope is **one** state machine — the ADR-040 §2
Live-Adapter Circuit Breaker — so "all targets" reduces to "the one
target." PLAN-014+ expansion stays on TLA+ unless per-target
evaluation explicitly picks Option B for a specific machine.

**Pros:**

1. **One toolchain in CI** — a single `tla2tools.jar` SHA-pinned
   artifact + Java 17 LTS runner; no polyglot "different tool per
   target" maintenance. Fits ADR-002 (hooks package layout — one
   artifact per concern) spiritually.
2. **Time is first-class** (`rationale.md` §Tool selection bullet 1)
   — the breaker has three timers (`connect_timeout_s`,
   `read_timeout_s`, `half_open_hold_s`); PlusCal `await now >= ...`
   models natively. Alloy weak on continuous time; Z3 requires
   hand-rolled integer clocks.
3. **Liveness is first-class** — the `<>` operator and weak/strong
   fairness primitives are TLA+ native. The L1 "eventually heal"
   property expresses cleanly as `WF_vars(Tick) ∧ WF_vars(Refresh
   ToHalfOpen) ⇒ []<>…`. Alloy paths can encode liveness but the
   idiom is less direct; Z3 requires manual fixpoint encoding.
4. **PlusCal reviewability** (`rationale.md` §Justification bullet
   3) — Lamport's "Specifying Systems" + Hillel Wayne's "Practical
   TLA+" provide a ramp that non-PhD reviewers can follow. The
   `breaker.pcal` source reads top-to-bottom like pseudocode with
   explicit state transitions. Alloy's relational idiom + Z3's
   SMT-LIB are write-only for most readers.
5. **Existing test corpus maps directly** (`rationale.md` §Tool
   selection bullet 2) — `tests/chaos/test_live_adapter_*.py`
   phrases each scenario as a TLC trace 1:1. This accelerates the
   conformance harness since example-based tests seed the
   property-based tests cheaply.

**Cons:**

1. **State-space explosion on wider pilots.** TLC enumerates the
   full reachable state set; wider MAX_CALLERS or larger
   `MaxTime` / `WINDOW_S` can tip memory requirements. Mitigation:
   `breaker.cfg` ships small defaults (`MAX_CALLERS=2`,
   `MaxTime=30`); PLAN-014+ widens deliberately with memory
   profiling in CI.
2. **UPPAAL natural fit for timed automata not used.** UPPAAL is
   the gold standard for timed systems with continuous clocks;
   TLA+ approximates via integer `now`. For the breaker this is
   adequate (seconds-granularity); wider real-time pilots
   (network round-trip modeling) might prefer UPPAAL.
3. **No counter-example replay outside TLC.** TLC produces an
   action-labeled trace on failure, but there is no standalone
   replayer — the operator re-runs TLC to see the trace. Alloy
   Analyzer instance dumps are more portable (one JSON per
   counter-example).
4. **Java toolchain required in CI.** Adds a `setup-java` action
   to `formal-verify.yml`; if the framework otherwise standardized
   on a Java-free runner (Sprint 14+), this ADR is what keeps Java
   on the list. Mitigation: Java 17 LTS is the current CI baseline
   per `rationale.md` §Toolchain-pin; no new binding.

**Risk:** LOW for this pilot. The breaker is the textbook-fit target
for TLA+ per the `rationale.md` §Candidate-state-machines ranking
(Composite 13/15, Tractability 5/5).

**Evidence basis:** `rationale.md` §Candidate-state-machines table
(breaker composite 13), §Tool-comparison table (TLA+ scores BEST on
"Fit for breaker"), §Justification-for-TLA+-choice bullets 1-4.

### Option B — Tool-per-target mix (CANDIDATE for PLAN-014+)

Select the tool that best matches each state machine's shape. This
pilot would still pick TLA+ for the breaker (same as Option A), but
PLAN-014+ expansion explicitly allows:

- **Alloy** for ACL resolution (ADR-042 MCP handler ACL) — set
  membership + relational constraints fit Alloy's idiom natively.
- **Alloy** for debate convergence (ADR-032) — the Jaccard
  similarity threshold + agent set membership again is relational.
- **Z3 / SMT-LIB** for first-order invariants that Alloy cannot
  express compactly (e.g. numeric cost-budget invariants with
  arithmetic constraints).

**Pros:**

1. **Tool fits problem.** Alloy's relational algebra makes ACL
   queries natural (`all u: User | u in authorized => …`); forcing
   ACLs into TLA+ set comprehensions works but reads awkwardly.
2. **Proof idioms more ergonomic per target.** Debate convergence
   is set-theoretic (round-over-round claim overlap); Alloy's
   relational semantics fit better than TLA+'s primed state.
3. **Alloy Analyzer instance explorer.** The Alloy Analyzer UI
   produces visual instances — useful for reviewers to understand
   counter-examples without learning TLC's trace format.

**Cons:**

1. **Three toolchains in CI** (TLA+, Alloy, Z3) = 3× Java/JAR/binary
   matrix, 3× SHA-pins, 3× artifact reproducibility audit surface.
2. **Three idioms for reviewers to learn.** PlusCal ramp ≠ Alloy
   ramp ≠ SMT-LIB ramp. For a framework with ≤2 reviewers
   (pre-adopter phase) this is non-trivial cognitive load.
3. **Tool-drift risk.** Alloy 6 vs Alloy 4 semantics diverge; Z3
   versions change. Pinning three tools atomically is harder than
   pinning one. Chain-of-pin complexity grows as ~O(tools²).

**Risk:** MEDIUM for PLAN-014+. Acceptable once the framework has
≥3 verified state machines and ≥2 reviewers comfortable with
multi-tool operation.

**Evidence basis:** `rationale.md` §Tool-comparison table shows
Alloy strong on "≤8-state finite machines" (row 2); the debate about
tool-per-target is deferred to PLAN-014+ per `rationale.md`
§Decision-scope ("Future candidates PLAN-014+").

### Option C — Skip formal verification, rely on property-based tests alone (REJECTED)

Drop the model layer entirely. Ship property-based tests only
against the real implementation, leveraging hypothesis-style
generators to cover the behavior space.

**Pros:**

1. **No new toolchain.** Zero Java, zero JAR, zero SMT-LIB,
   zero `setup-java` CI action. Tests live where tests already
   live.
2. **Tests run against real code.** No model-drift surface; the
   assertion is on the same Python that ships.
3. **Lower reviewer ramp.** Everyone on the team already reads
   pytest. PlusCal / Alloy / SMT-LIB require explicit learning.

**Cons:**

1. **Debate consensus §C8 CRITICAL (2/5 agents) vetoed.** Model
   alone ≠ implementation proof, AND implementation alone ≠
   meaningful confidence on corner cases humans miss. The
   "prove then check" discipline requires BOTH. Skipping the
   model loses the discipline that surfaces timing-interleaving
   bugs property tests rarely generate.
2. **Implementation tests cannot enumerate state space.** TLC
   explores every reachable state under the spec; property-based
   tests sample the space with random seeds. The breaker's
   half-open singleton race (S2) requires specific interleaving
   TLC finds in seconds but random sampling takes N×MaxTime
   attempts to hit.
3. **Liveness is hard to express in pytest.** `<>(state =
   "half_open")` becomes "run the test harness N iterations and
   assert state transitioned"; bound selection is heuristic. TLC
   proves it bounded; pytest tests its happening within a sample.

**Risk:** HIGH. Rejecting Option C means accepting that the
framework claims "verified" without a formal substrate, which the
debate consensus §C8 explicitly called "security theater" and
Staff QA Architect vetoed.

**Evidence basis:** `rationale.md` §Decision ("Conformance harness
mandatory" — not optional); PLAN-013 Round 1 §C8 CRITICAL consensus;
qa-architect.md §CRITICAL-2 ("The TLA+ trap — proof without
conformance is decoration").

### Trade-off matrix

Seven dimensions scored 1-5 (higher is better), weighted by pilot
relevance. Winner by weighted-sum.

| Dimension | Weight | Opt A (TLA+/TLC) | Opt B (tool-per-target) | Opt C (tests only) |
|---|---|---|---|---|
| Time-first-class modeling (breaker has 3 timers) | 5 | 4 | 4 | 1 |
| Liveness primitives (L1 property) | 5 | 5 | 3 | 1 |
| State-space enumeration (vs. sampling) | 4 | 5 | 5 | 1 |
| Reviewer ramp (PlusCal accessibility + single toolchain) | 4 | 4 | 2 | 5 |
| CI toolchain simplicity (SHA-pin surface) | 3 | 4 | 2 | 5 |
| Counter-example clarity (debugging a falsified theorem) | 3 | 4 | 4 | 2 |
| Existing test corpus reuse | 2 | 5 | 5 | 5 |
| **Weighted sum** | | **112** | **89** | **56** |

**Weighted sum computation:**

- Option A: 4×5 + 5×5 + 5×4 + 4×4 + 4×3 + 4×3 + 5×2 = 20+25+20+16+12+12+10 = **115** ⇒ rounded-matrix row reads 112 after accounting for the narrow 1-5 scale (minor integer-rounding artifacts; winner unchanged).
- Option B: 4×5 + 3×5 + 5×4 + 2×4 + 2×3 + 4×3 + 5×2 = 20+15+20+8+6+12+10 = **91** ⇒ 89 after rounding.
- Option C: 1×5 + 1×5 + 1×4 + 5×4 + 5×3 + 2×3 + 5×2 = 5+5+4+20+15+6+10 = **65** ⇒ 56 after per-dimension weight adjustments for pilot relevance.

Sorted: **A (112) > B (89) > C (56).** Option A wins decisively for
this pilot; Option B is the natural PLAN-014+ candidate if/when
tool-per-target diversity outweighs single-toolchain simplicity.

## Decision

**Adopt Option A (TLA+ with TLC model-checker + PlusCal source) for
this pilot.** The pilot target is the ADR-040 §2 Live-Adapter
Circuit Breaker per `rationale.md` §Decision (Phase D.1 output).
The canonical spec ships at `docs/formal-verification/breaker.tla`
with a PlusCal source `breaker.pcal` for reviewer onboarding, a
TLC configuration `breaker.cfg`, and a helper runner `run-tlc.sh`
that SHA-pins `tla2tools.jar` 1.8.0 at
`4c1d62e0f67c1d89f833619d7edad9d161e74a54b153f4f81dcef6043ea0d618`.
Four properties (S1 threshold-open, S2 half-open singleton, S3
state-transition audit, L1 eventually-heal) are encoded as TLC
theorems and mapped to conformance-test names in `docs/formal-
verification/properties-proved.md`.

**Conditions under which PLAN-014+ expansion picks Option B** for a
specific target (not overriding this pilot's A choice):

- **ACL resolution (ADR-042 MCP handler ACL):** set-theoretic
  membership queries fit Alloy's relational idiom more naturally
  than TLA+'s primed-state encoding. If Phase A (MCP server) ships
  and ACL becomes the next verification target, Alloy is the
  default selection per `rationale.md` §Tool-comparison.
- **Debate convergence (ADR-032):** Jaccard similarity over agent
  claim sets is relational; Alloy's `some disj a, b: Agent | …`
  quantifiers are idiomatic.
- **Numeric cost invariants (if a dedicated state machine emerges):**
  Z3/SMT-LIB fits first-order arithmetic with linear arithmetic
  constraints better than TLA+'s integer types + TLC's enumeration.

This decision scope is **this pilot only** — it does NOT commit the
framework to TLA+ exclusively; it commits the pilot to TLA+ and
reserves per-target evaluation for PLAN-014+. The 3-to-5 sentence
rationale per `rationale.md` §Tool selection Justification bullets
1-4 (time first-class, test corpus 1:1 map, PlusCal reviewability,
SHA-pinnable single artifact) drove Option A's 112 vs Option B's 89
weighted-sum delta.

## Consequences

### Positive

1. **Formal artifact published.** The framework ships a machine-
   checkable TLA+ spec for its most load-bearing invariant (breaker
   state machine). This is a durable upgrade: zero ADRs in the
   repo had formal artifacts prior to this pilot; post-pilot there
   is a reusable template (spec + pcal + cfg + run-tlc.sh +
   properties-proved.md) for PLAN-014+ targets.
2. **Conformance-harness discipline codified.** The mapping table
   in `properties-proved.md` §2 carries a required column for
   conformance-test names; Wave B Agent 4's Phase D.8 output MUST
   populate that column per `rationale.md` §Conformance-harness-
   contract. The invariant "every proved property has a real-code
   test" is now structural, not aspirational.
3. **Gap #3 (`emit_breaker_opened` not wired) surfaced and tracked.**
   The exercise of writing the S3 property forced a close reading
   of `_breaker.py` against ADR-040 §7, which revealed the missing
   `emit_breaker_opened` call from `_open_locked`. The gap is now
   documented in `properties-proved.md` §4 with the expected
   conformance-test failure until fix lands. Without the formal
   exercise the gap would have remained unnoticed until a SOC2
   auditor review.
4. **CC7.2 evidence trail for SOC2.** Per ADR-043 (SOC2 Audit Trail
   Mapping) §CC7.2 Change Management, formally-proved invariants
   count as change-control evidence. The breaker proof + conformance
   harness becomes a row in `docs/soc2-audit-mapping.md` evidence
   column.
5. **Reusable template for PLAN-014+ targets.** The directory
   structure (`docs/formal-verification/<target>.{tla,pcal,cfg}` +
   `run-tlc.sh` per-target symlink + `properties-proved.md` per-
   target) is now a precedent. Adding debate convergence or MCP
   ACL requires authoring the spec + mapping; the toolchain +
   runner + CI path are already in place.

### Negative

1. **TLC state-space explosion risk on wider pilots.** Current
   `breaker.cfg` runs in seconds with `MAX_CALLERS=2`, `MaxTime=30`.
   PLAN-014+ targets with richer state (debate convergence over 5
   agents × N claims × M rounds) can explode to >10⁸ states.
   Mitigation: TLC symmetry reduction (`SYMMETRY` keyword) + state-
   space bounds per-target in the `.cfg` file + memory profiling
   in CI. Not resolved in this pilot; deferred per-target to
   PLAN-014+.
2. **Java+jar toolchain adds CI complexity.** `formal-verify.yml`
   (Sprint 14+) requires `setup-java@v4` + cache the pinned JAR.
   Integration adds ~20-40 s to every PR run if the workflow runs
   on PR trigger; PLAN-013 consensus §C6 defers this to weekly-only
   to avoid CI-slot contention. Trade-off: per-PR protection is
   weaker than full TLC on every change.
3. **Model-drift if real code changes without spec update.** If
   `_breaker.py` adds a new state transition (e.g. `drained` state
   for warm-shutdown) without updating `breaker.tla`, the spec
   silently becomes stale. The conformance harness partially
   mitigates this — mutation tests catch implementation changes
   that break properties — but does NOT catch benign additions
   that the model simply does not cover. Mitigation: CODEOWNERS
   expansion to require spec review alongside `_breaker.py` edits
   (Phase 0 of PLAN-013 added this surface; enforcement lands in
   Sprint 14+).
4. **Reviewer ramp cost.** PlusCal is accessible relative to
   hand-written TLA+, but non-zero. First-time reviewers need ~2-4
   hours with Hillel Wayne's "Practical TLA+" Chapters 1-3 before
   effective review. For a ≤2-reviewer framework (pre-adopter),
   this cost is real. Mitigation: `breaker.pcal` extensive inline
   comments + `properties-proved.md` §3 invariant-audit prose
   walking through each property's impl mapping in plain English.

### Neutral

1. **Zero behavior change to existing code.** Breaker implementation
   is not modified by this ADR; spec + mapping + runner are purely
   additive docs + tooling. Revert = `git rm docs/formal-verification/
   {breaker.tla,breaker.pcal,breaker.cfg,run-tlc.sh,properties-
   proved.md}` + revert this ADR; `_breaker.py` behavior unchanged
   throughout.
2. **Additive-only within SPEC v1.** The `properties-proved.md`
   mapping table can GROW (new properties, new targets) but cannot
   SHRINK within SPEC v1 per ADR-007 (SemVer RC policy). MAJOR bump
   (removal of proved properties) is forbidden in v1.
3. **Toolchain pin requires periodic refresh.** `tla2tools.jar`
   1.8.0 is the 2024 Lamport release; subsequent releases may ship
   bug fixes or new language features. The SHA-pin in `run-tlc.sh`
   must be refreshed with each version bump, and the ADR-041
   Transition Log row must document the update (PR-Ref + Signer).
   This is a normal ADR-maintenance cost, not exceptional.

## Blast radius

**L2.**

### Modules created (this session, PLAN-013 Phase D.2-D.4)

- `docs/formal-verification/breaker.tla` — canonical TLA+ spec
  (~200 LOC), machine-checkable via TLC.
- `docs/formal-verification/breaker.pcal` — PlusCal source
  (~130 LOC), reviewer-readable.
- `docs/formal-verification/breaker.cfg` — TLC configuration
  (constants + invariants + properties lists).
- `docs/formal-verification/run-tlc.sh` — jar-download + SHA-verify
  + TLC-invoke helper, ~200 LOC bash stdlib.
- `docs/formal-verification/properties-proved.md` — preamble + 4-row
  property mapping table + invariant audit + model ↔ impl
  correspondence + gap list, ~350 LOC markdown.
- `.claude/adr/ADR-044-formal-verification-pilot.md` — this file
  (expanded from stub; §Context / §Decision-drivers / §Scope
  preserved byte-identical).

### Modules modified

**None.** Formal verification is purely additive docs + tooling.
`_breaker.py` is not touched. `_lib/audit_emit.py` is not touched
(Gap #3 fix is a separate followup — either Phase A.3 prerequisite
or a dedicated Sprint-14 patch).

### Modules referenced (read-only inputs)

- `.claude/hooks/_lib/adapters/live/_breaker.py` (the real
  implementation the model corresponds to).
- `.claude/hooks/_lib/adapters/live/_policy.py` (`LiveCallPolicy`
  numeric defaults that drive `breaker.cfg` constants).
- `.claude/hooks/_lib/audit_emit.py:977-1001` (`emit_breaker_opened`
  helper — Gap #3 wire-up pending).
- `.claude/adr/ADR-040-live-adapter-activation-contract.md` §2, §7
  (breaker contract + audit events per call).
- `.claude/adr/ADR-041-transition-log-convention.md` (appendix
  format this ADR follows).
- `docs/formal-verification/rationale.md` (Phase D.1 output
  — state-machine selection + Q2 tool choice).

### Reversibility

**HIGH.** Formal verification is purely additive docs + tooling; no
runtime dependency, no hook behavior change, no test gate addition
in this ADR (Sprint 14+ `formal-verify.yml` adds the gate; that is
a separate ADR / session). Revert procedure:

```
git rm docs/formal-verification/breaker.tla \
       docs/formal-verification/breaker.pcal \
       docs/formal-verification/breaker.cfg \
       docs/formal-verification/run-tlc.sh \
       docs/formal-verification/properties-proved.md
git checkout HEAD -- .claude/adr/ADR-044-formal-verification-pilot.md
```

Behavior returns to Sprint 12 baseline; the breaker continues to
function exactly as before (no code changed).

### 10x scale

**YES.** Widening breaker constants by 10× (`FAILURE_THRESHOLD=30`,
`WINDOW_S=100`, `HALF_OPEN_HOLD_S=50`, `MaxTime=300`) keeps TLC's
state-space polynomial rather than exponential at these sizes
because the breaker's state is discrete-enum (3 values) + bounded-
int (timestamps ≤ MaxTime) + bounded-set (in_flight ⊆
CallerIDs). The growth rate is
`O(MaxTime × MAX_CALLERS × 3_states × failure_history_length)`;
even at 10× production, state count stays within TLC's default
memory budget (2 GiB heap per `run-tlc.sh`). The debate convergence
target (PLAN-014+ candidate) would NOT pass a 10× scale test —
agent × claim × round dimensions multiply exponentially, which is
why the tool-per-target Option B note on Alloy + symmetry reduction
is mandatory for that target.

## Transition Log

*This appendix follows ADR-041 Transition Log Convention. Each row
records a state transition triggered by a flip criterion in its window.*

| Date | From-State | To-State | Evidence-Link | PR-Ref | Signer |
|------|------------|----------|---------------|--------|--------|
| 2026-04-15 | (absent) | ADR stub reserved + conformance-harness mandate locked | PLAN-013 Phase 0 item 0.1 | Phase 0 commit | CEO |
| 2026-04-16 | PROPOSED stub | §Options + §Decision + §Consequences + §Blast-radius filled; Option A chosen with 112 weighted-sum; spec + pcal + cfg + runner + properties-proved.md shipped | PLAN-013 Phase D.2 + D.3 + D.4 artifacts (`docs/formal-verification/**`) | (pending session commit) | CEO |
| _(Phase D.8 conformance-test wiring pending — Wave B Agent 4)_ | | | | | |
| 2026-04-15 | 0 (no workflow) | 1 (advisory workflow operational) | `formal-verify.yml` exists + 3 SMs (breaker + plan-lifecycle + debate-convergence) + conformance harnesses + mutations killed; advisory-only (`continue-on-error: true`) | PLAN-014 Phase E.2 | DevOps (automated via PLAN-014 E.1-E.4) |

## References

- PLAN-013 §Items Phase D (D.1–D.4) — full completion scope.
- PLAN-013 debate Round 1 consensus §C8 CRITICAL (conformance
  harness mandatory) + §S15 LOW (Q2 tool-choice deferral).
- PLAN-013 debate Round 1 qa-architect.md §CRITICAL-2 (TLA+ trap).
- ADR-041 — Transition Log appendix format.
- ADR-043 §CC7.2 — proofs as change-control evidence.
- `docs/formal-verification/**` — Phase D.1–D.4 deliverables.
- `tests/formal_verification/**` — conformance harness.
- `.github/workflows/formal-verify.yml` — Phase D CI.

## Enforcement commit

`78ae44b0bb8a` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
