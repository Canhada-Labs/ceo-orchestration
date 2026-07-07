---
plan: PLAN-154
round: 1
archetype: qa-architect
skill: testing-strategy
verdict: ADJUST_PROCEED
created_at: 2026-07-06
---

## Verdict

ADJUST_PROCEED — the plan's governance skeleton (zero self-activation,
metadata-only v1, advisory-only dampening, injection-scanned pipeline) is the
right shape, and the stub correctly names `lessons.py` as canonical-guarded
(`check_canonical_edit.py:129` — the PLAN-153 draft error is fixed). But as
written, four of the seven items are **not testable as stated**: the decay
item builds on a file whose existing decay path reads the wall clock with no
seam (`lessons.py:353`), the distiller has no hermetic-CI story, "blocking
never dampened" has no tested classifier to make it falsifiable, and
"metadata-only" is a constraint sentence, not an assertable contract. All are
fixable in the plan/ADR text before execution; none require redesign. Fix the
must-fixes below and this moves to `reviewed` from the QA seat.

## Summary (≤ 3 bullets)

- **What it does:** imports ecc's observe→distill→candidate learning funnel
  under human gating: an opt-in metadata rail, an offline distiller into the
  existing `lessons.py` PENDING store, confidence decay, fenced `/ceo-boot`
  one-liners, advisory dampening, a deny-once ADVISORY→enforce gate, and
  `/lesson-evolve` → SP-NNN.
- **Strong:** every red line is stated as a testable-sounding invariant, and
  the base it extends is the *right* base — `_lib/tool_lifecycle.py` already
  models the exact QA discipline this plan needs (closed enums MF-SEC-1,
  injectable clock MF-QA-B "tests never time.sleep", fail-open emit).
- **Weak:** the plan inherits six binding constraints but zero fixtures. The
  Wave-E doctrine (behavioral positive-control certifies; static scan
  complements — PLAN-153:201-203) exists precisely so new guard surfaces ship
  with planted-violation fixtures; this plan must state, per item, what the
  planted violation is and what RED looks like. Today it doesn't.

## Risks

- **R-QA-01 — Nondeterministic clock in the exact path item 3 extends**
  Severity: **CRITICAL**
  Description: `lessons.py:346-357` `_recency_decay()` calls
  `datetime.now(timezone.utc)` inline; there is no injectable clock anywhere
  in the scoring path (`get_top_k` → `_recency_decay` at `:397`). Item 3
  ("confidence score with deterministic decay") and constraint 5's TTL
  (30d + 7d warning) are both time functions. If they copy the existing
  pattern, every test either mocks `datetime` globally (fragile under
  `pytest -n auto`) or flakes at day boundaries. The house pattern already
  exists in the very rail item 1 extends: `tool_lifecycle.py` MF-PERF-3/MF-QA-B
  — "orphan timeout with an INJECTABLE clock (`now_fn`) — tests never
  `time.sleep`".
  Mitigation: every new time-dependent function (confidence decay, TTL expiry,
  7d warning, any dampening window) takes `now_fn`/`now` as a parameter with
  the wall clock only as default; scoring becomes a pure function of
  (record, now) with golden-value tests at boundaries (day 0, half-life,
  TTL−1s, TTL+1s) plus a monotonicity property test. Refactor `_recency_decay`
  to accept `now` in the same SENT-F edit — it is already in scope.

- **R-QA-02 — Distiller has no hermetic CI story (model-in-the-loop)**
  Severity: **CRITICAL**
  Description: item 2 is "offline distiller (cheap model)". CI must never call
  a live model (the `/self-test` "$0 hermetic" precedent). Without a recorded
  or stubbed model mode, the distiller's tests are either CI-dark (the S254
  class — ~1377 tests were dark) or paid+flaky. Worse: constraint 2's
  injection scan over distiller *output* is unverifiable in CI if the output
  can't be produced deterministically.
  Mitigation: the distiller CLI ships a `--from-fixture` (recorded model
  output) mode as a first-class contract, and CI runs ONLY that mode. Schema
  validation of distiller output is fail-CLOSED (unparseable/over-schema
  output → no candidate written + breadcrumb), mirroring the `_e3`/C4
  precedent. Two mandatory fixtures: (a) planted hostile observation drawn
  from the existing injection corpus (`scan-injection.py`,
  `hooks/tests/test_injection_patterns_bypass.py` class) must be rejected
  before candidate stage; (b) a benign observation must survive to PENDING —
  the positive control proving the funnel is alive, per Wave-E doctrine.

- **R-QA-03 — "Blocking never dampened" is unfalsifiable without a tested classifier**
  Severity: **HIGH**
  Description: constraint 4 / item 5 promise a blocking guard's block reason
  NEVER loses legibility. That invariant needs a mechanical decision surface
  — an `is_blocking(output)` classification the dampening layer consults —
  and that classifier must itself be tested, or the invariant is prose. The
  original anti-pattern (attacker probes bash-safety, guard goes quiet —
  PLAN-153 R-VP5) regresses silently the first time an output is
  misclassified as advisory.
  Mitigation: (a) dampening consumes a schema field (decision=deny/block vs
  advisory), never a heuristic over message text; (b) property test: block
  reason at repeat N=1 is byte-identical (modulo timestamps) to N=100 — a
  planted repeated-block fixture replayed by CI, exactly the Wave-E
  positive-control shape (PLAN-153:205-216); (c) advisory condensation test
  asserts the ordinal + pointer survive condensation.

- **R-QA-04 — "Metadata-only" is a constraint, not an assertable contract**
  Severity: **HIGH**
  Description: constraint 1 says the rail is content-free, but nothing in the
  plan freezes what that means mechanically. `tool_lifecycle.py` shows the
  standard: four coarse fields, closed enums, "the raw
  `mcp__<server>__<tool>` string MUST NEVER reach the wire" (MF-SEC-1), raw
  `duration_ms` never emitted (MF-SEC-3). An extension that adds one
  free-form string field silently converts the rail into a content store —
  the exact healthcare/fintech failure constraint 1 forbids.
  Mitigation: three assertions, all cheap: (a) frozen closed-key schema
  fixture — a schema-hash test reds CI on ANY field addition until the
  fixture is consciously updated in review; (b) type gate — every value is a
  closed enum, bool, or bucketed numeric; no free-form strings pass the
  emitter; (c) canary-exfiltration test — run a synthetic tool call whose
  args/output carry `CANARY_SECRET_...`, then grep the ENTIRE observation
  store: zero hits. Plus the kill-switch negative control: env unset → zero
  filesystem delta (assert no observation file is even created).

- **R-QA-05 — ADVISORY→enforce flip (item 6) has no pre-registered exit criteria**
  Severity: **HIGH**
  Description: the only enforce-capable item in the plan describes a shadow
  posture ("ADVISORY→enforce path") but no numeric criteria for the flip. A
  vibes-based flip after an unmeasured shadow window is how false-positive
  storms ship; a fail-CLOSED citation gate with a high FP rate blocks real
  work and trains Owners to override.
  Mitigation: pre-register the flip gate in ADR-160: FP rate < X% over ≥ N
  events AND ≥ M calendar days of dogfood shadow telemetry (measured from the
  HMAC audit log), numbers chosen at this plan's Wave 0. The flip itself is a
  governance event recorded in the chain. Reuse — do not reinvent — the
  transcript-read-failure fixture class PLAN-153 Wave E item 5 ships
  (PLAN-153:234-239); add the fabricated-citation positive control: a
  citation that fails verification must BLOCK.

- **R-QA-06 — E↔F fixture coupling is an interface dependency, not just ordering**
  Severity: **MEDIUM**
  Description: constraint 6 requires the opt-in no-op hook to carry the
  Wave-E allowlist marker. But Wave E is authored/staged tonight and NOT yet
  visible on main from this worktree (no harness-config gate on disk at time
  of writing). If PLAN-154 authors its fixtures against a *guessed* marker
  syntax or fixture-registration API, we get two fixture dialects and the
  R-VP6 "fixtures proving both directions" promise quietly forks.
  Mitigation: hard precondition (add to the stub's gate list): pin the
  LANDED Wave-E marker syntax + positive-control fixture API before item 1 is
  authored. And extend "both directions" to three: (a) marked opt-in no-op
  passes the harness gate; (b) unmarked fail-open shim reds it; (c) **marker
  abuse** — a MARKED hook that is registered as a blocking guard must still
  be liveness-tracked, so the allowlist cannot be used to hide a dead rail.

- **R-QA-07 — CI-dark and env-drift regression surfaces (same-commit rule)**
  Severity: **MEDIUM**
  Description: `validate.yml` collects tests by directory —
  `.claude/scripts/tests/` + `.claude/scripts/optimizer/tests/` (line 318)
  and `.claude/hooks/tests/` (line 1093). Any NEW test directory (a distiller
  subpackage is the likely candidate) is CI-dark unless wired the same
  commit. Separately: the kill-switch env var (item 1) joins the steering-var
  family — the S218 footgun class (`env-inventory-check.py` exists for this)
  and the xdist env-leak lesson both apply. And test placement crosses the
  guard boundary: `hooks/tests/` is NOT canonical-guarded but
  `hooks/_lib/tests/` IS — if item 1 extends `_lib/tool_lifecycle.py`, its
  tests either land in the guarded dir (→ SENT-F scope must include them, or
  the wave stalls on `touched − SIGNED SCOPE ≠ ∅`) or in `hooks/tests/`.
  Mitigation: write into this plan's success criteria: new tests live in
  already-collected dirs OR validate.yml gains the path in the same commit;
  new env vars registered in `env-inventory.json` + the autouse reset fixture
  same-commit; test-placement/SENT-F-scope decision made at this plan's
  Wave 0, not mid-wave.

- **R-QA-08 — /lesson-evolve pipeline (item 7): no end-to-end path, clustering nondeterminism**
  Severity: **MEDIUM**
  Description: item 7 chains trigger-clustering → SP-NNN → `/skill-review` →
  7-day soak. Untested joints: does the generated proposal actually parse in
  `skill-patch-apply.py`? Is clustering deterministic (unstable sorts,
  unseeded tie-breaks → different SP candidates from the same store →
  unreviewable diffs)? Does the soak hold for machine-generated proposals?
  Mitigation: one seeded-store e2e fixture: N crafted lessons →
  `/lesson-evolve` → emits an SP proposal that `skill-patch-propose.py` /
  `skill-patch-apply.py` accept in shadow mode; soak asserted via the
  existing injectable-age seam (`skill-patch-apply.py:645-667`,
  `_SEVEN_DAYS_SECS` / `skip_soak` — test BOTH branches); determinism test:
  run twice on the same store, assert identical candidates; generated SP
  content passes the injection scan before the proposal file is written.

- **R-QA-09 — /ceo-boot injection (item 4): cap + fencing edge cases**
  Severity: **MEDIUM**
  Description: the ~1k-char cap and "fenced as untrusted data" both have
  sharp edges: multi-byte truncation (the PLAN-152 CEO_UNICODE_HARDBLOCK
  lesson class — chars vs bytes), a lesson whose advisory text contains
  fence-closing markdown, and the imperative-detector's own coverage.
  Mitigation: boundary tests at cap−1/cap/cap+1 including multi-byte;
  positive control: a lesson carrying a directive payload ("ignore previous
  instructions…") is flagged by the imperative-detector AND still renders
  fenced-as-data (fence-escape attempt fixture); extend the existing
  `test_ceo_boot*.py` suites rather than a new file family; boot is Tier-S —
  respect the perf gate (a separate CI job per the pre-push lesson; the
  overhead is a p95/p99 budget, not a vibe).

- **R-QA-10 — TTL vs existing pruning: two lifecycles on one store**
  Severity: **LOW**
  Description: constraint 5's TTL (30d + 7d warning) coexists with
  `prune-lessons.py --older-than-days` (ADR-017/ADR-020). Two independent
  expiry mechanisms on the same JSON files invite double-delete,
  warn-after-prune, or a pruned-then-approved zombie.
  Mitigation: fixture proving (a) the 7d warning fires exactly once per
  pending (idempotent, same contract as `/lesson-review --undo`'s
  `already_undone` no-op branch), (b) an expired pending cannot be approved,
  (c) prune and TTL agree on which clock and which field they read.

## Must-fix (blocking)

1. **Injectable clock seam for every time-dependent path** (R-QA-01): decay,
   TTL, warning, dampening windows all take `now_fn`; `_recency_decay`
   refactored under the same SENT-F; golden-value + monotonicity tests named
   in the plan's item 3 text.
2. **Hermetic distiller mode as a contract** (R-QA-02): `--from-fixture`
   recorded-output mode; CI never calls a live model; fail-CLOSED output
   schema; hostile-observation-rejected + benign-observation-survives
   fixtures listed as item-2 acceptance criteria.
3. **Tested blocking/advisory classifier + repeat-N property test**
   (R-QA-03): dampening keyed on a schema decision field; byte-identical
   block reason at N=1 vs N=100 replayed as a CI positive control.
4. **Metadata-only as three CI assertions** (R-QA-04): frozen schema-hash
   fixture, closed-type emitter gate, canary-exfiltration grep + kill-switch
   zero-delta negative control. Write these into constraint 1's text so the
   ADR inherits them.
5. **Pre-registered numeric flip criteria for item 6** (R-QA-05): FP
   threshold + minimum event count + minimum calendar days in ADR-160; flip
   recorded as an HMAC-chain governance event; fabricated-citation fixture
   BLOCKS.
6. **Pin the landed Wave-E fixture/marker API as a precondition** (R-QA-06)
   and extend the E↔F fixture set to the third direction (marker abuse
   cannot hide a dead blocking rail).
7. **Same-commit wiring rule in success criteria** (R-QA-07): CI test-path
   additions, `env-inventory.json`, autouse env-reset fixture; SENT-F
   test-placement decision (`_lib/tests/` guarded vs `hooks/tests/` not) made
   at Wave 0.
8. **Fix the ADR index in the stub** — the plan text gates execution on
   "ADR-174 drafted and accepted" (stub §Context) but the reserved
   learning-loop ADR is **ADR-160** (S261 index correction). Correct before
   the consensus inherits a dead ADR number into SENT-F and ceremony text.

## Nice-to-have (advisory)

1. E2E `/lesson-evolve` seeded-store fixture + twice-run determinism assert
   (R-QA-08) — advisory only because item 7 can land last.
2. TTL/prune interaction fixture (R-QA-10).
3. Unicode/cap boundary + fence-escape fixtures for item 4 (R-QA-09).
4. First release ships item 4 (boot injection) default-OFF behind the same
   kill-switch family as item 1 — one session of dogfood shadow before
   default-on; cheap because the env plumbing already exists.
5. A single `PLAN-154/fixtures/` README mapping item → planted violation →
   expected RED, so the Wave-E doctrine mapping survives context loss between
   the 2 budgeted sessions.

## Unseen by the original plan

1. **The determinism gap lives in the exact file the plan extends** —
   `lessons.py`'s own decay reads the wall clock inline; "deterministic
   decay" over a nondeterministic substrate is a category error the stub
   never mentions.
2. **No hermetic-model test story** for the distiller — the plan says "cheap
   model" but never says how CI exercises it for $0.
3. **Metadata-only has no freeze mechanism named** — without a schema-hash
   fixture, the contract erodes one "harmless" field at a time.
4. **Wave E is an interface dependency, not just a sequencing dependency** —
   the stub gates on "Wave E ships" but not on consuming its actual
   marker/fixture API.
5. **The kill-switch env var is a steering var** — env-inventory + xdist
   reset obligations (S218 class) are invisible in the plan.
6. **ADR-174 vs ADR-160 drift** in the stub's own gate list.
7. **TTL vs `prune-lessons.py`** — a second lifecycle on a store that already
   has one.

## What I would NOT change

- **Zero self-activation + PENDING → `/lesson-review` + SP-NNN + soak**
  (constraint 5) — the single most important invariant; also the most
  testable one, because every activation requires an approval event in the
  HMAC chain (the plan's stated success criterion is already an assertable
  oracle: "zero writes outside pending stores without an approval event").
  Preserve verbatim.
- **Extending `tool_lifecycle.py` rather than a new rail** (constraint 1) —
  it already carries the closed-enum, injectable-clock, fail-open-emit
  discipline this plan needs; extension inherits its test suite.
- **"The human gate is explicitly NOT the injection defense (mechanical
  scanning is)"** — this division of labor is what makes the pipeline
  testable at all: the machine's filter gets fixtures, the human's filter
  gets a UI. Keep exactly.
- **Advisory-only dampening redesign** (constraint 4) — correct response to
  R-VP5; my R-QA-03 hardens it, does not weaken it.
- **Stub-until-debate posture with SENT-F acknowledged as guarded** — the
  stub correctly states `lessons.py` IS canonical-guarded at
  `check_canonical_edit.py:129`, fixing the PLAN-153 draft's false claim.

## Per-item positive-control map (Wave-E doctrine applied)

| Item | Planted violation / fixture | Expected signal |
|---|---|---|
| 1 rail | canary secret in tool args; kill-switch unset | zero canary hits in store; zero filesystem delta |
| 1 rail (E↔F) | marked no-op hook / unmarked shim / marked-but-blocking hook | pass / RED / liveness-tracked |
| 2 distiller | hostile observation from injection corpus; malformed model output | rejected pre-candidate; fail-CLOSED no-write |
| 3 decay | frozen `now`, boundary timestamps | golden scores; monotonic; twice-run identical |
| 4 boot | directive payload in lesson text; cap±1 multi-byte | flagged + fenced; clean truncation |
| 5 dampening | same block repeated 100x | byte-identical block reason each time |
| 6 deny-once | fabricated citation; transcript-read failure | BLOCK; fail-CLOSED (audit-emit side fail-open) |
| 7 evolve | seeded lesson cluster; young shadow | valid SP accepted in shadow; soak refuses promote |
