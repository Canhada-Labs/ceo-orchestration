# ADR-104-AMEND-1 — AEK Calibration Phases C2-C4 + Dated Promotion Criteria

**Status:** PROPOSED (Owner GPG ceremony pending — S141 PLAN-101 ship)
**Date:** 2026-05-18
**Enforcement commit:** _pending_ (filled at ceremony commit time;
mirrors ADR-019-AMEND-1 PROPOSED→ACCEPTED pattern)
**Plan:** PLAN-101
**Amends:** ADR-104 §Phase 2/3/4 promotion clause
**Related:** ADR-019-AMEND-1 (per-class block-mode lifecycle pattern;
S140 ACCEPTED), ADR-095 (calendar gate purge), ADR-124 §Part 2
(hotfix scope cover), ADR-125 §B (Tier-B conditional default),
PLAN-101 Wave 0..D

**Co-signers (architectural review):** Round 1 5-archetype debate
(S134) + Round 2 Codex MCP 5-iter ACCEPT (skeleton) thread
`019e3849-16b0-7782-865d-a250b4709a74` gpt-5.2 + Round 2 Codex MCP
4-iter ACCEPT (ceremony bundle) thread
`019e3ccc-c319-7242-a511-7daf67f3d30a` gpt-5.2 (S141).

## Codex MCP gate trail (S141 ceremony bundle review)

| Iter | Verdict | Findings |
| ---- | ------- | -------- |
| 1    | ACCEPT-WITH-FIXES | 0 P0 / 4 P1 / 4 P2 — Wilson FPR denominator wrong (`fp+tp+fn` instead of `fp+tn`); deferral-cap arithmetic 360d vs `max 3 × 90d = 270d`; ADR §E specified typed wrapper but ceremony P3 is NO-OP; FPR threshold check averaged eligible-only subset (could PASS missing class); P2: docstrings claim typed wrapper; ship_sha placeholder; fixture count drift; contract_id format hardcoded |
| 2    | ACCEPT-WITH-FIXES | 0 P0 / 3 P1 / 1 P2 — residual 360d references in commit msg + CHANGELOG entry + plan body §Risks; residual typed-wrapper mentions in commit msg + CHANGELOG; ADR-095 calendar-gate doctrine drift in plan body Wave 0 + §8 execute recipe; P2: matrix advised vs joined count clarity |
| 3    | ACCEPT-WITH-FIXES | 0 P0 / 2 P1 — Wave 0 draft bullet still listed "≥30 consecutive days of calibration window"; §8 step 1 wording "max 3x = 90d cap" inconsistent with canonical "270d cap" |
| 4    | ACCEPT | No residuals |

## Context

ADR-104 (PLAN-071 S87 v1.14.0) shipped the Adaptive Execution Kernel
(AEK) `task-route.py` + Reality Ledger in **advisory-only** mode. The
ADR's `Reopen criteria` + `§Negative consequences` clauses define an
empirical promotion pathway through three measurement phases:

- **Phase 2** task-class calibration baseline (S/M/L/XL distribution)
- **Phase 3** false-positive-rate matrix per class
- **Phase 4** kernel state-machine conformance

PLAN-101 (S115 skeleton; S134 reviewable-as-skeleton ACCEPT) opens
the empirical work. Codex P7 STILL-VALID confirms the phases are
prerequisite for promotion from advisory to enforcement.

**Two semantic problems** surfaced at S115 + S134 review that require
this amendment:

1. **Name collision**: PLAN-071 already shipped internal "Phase 2 / 3
   / 4" execution waves at v1.14.0. Reusing "Phase 2/3/4" for the
   empirical promotion phases conflates two unrelated workstreams.
2. **Perpetual deferral risk**: ADR-104 promotion clause was
   open-ended ("once data accumulates, revisit"). Without a dated
   trigger, the decision becomes "future Owner problem" forever.

ADR-095 doctrine (calendar-gate purge) further constrains the
amendment: substantive criteria (sample size, class diversity,
verifier determinism) replace calendar holding-periods. Recent S139
PLAN-100 reaffirmation + S140 ADR-019-AMEND-1 promotion concretized
the pattern.

## Decision drivers

- **Phase renaming for clarity** — empirical promotion phases are
  renamed `Calibration C2 / C3 / C4` to disambiguate from PLAN-071
  shipped internal phases. Calibration prefix marks them as
  measurement gates, not implementation work.
- **Dated vote trigger** (R1 P0-5 closure) — vote MUST fire 90d post
  PLAN-101 ship (2026-08-16 derived from S141 anticipated ship
  2026-05-18). Vote outcome may DEFER, but the decision-point itself
  is dated.
- **Deferral protocol** — if criteria NOT met at vote-trigger date,
  Owner ceremony records "defer + new dated trigger" (90d extension).
  Maximum 3 extensions = 270d total deferral cap (3 × 90d). After
  270d without criteria-met, escalate to ADR-104 §rescope or SUPERSEDE.
- **Numeric thresholds** (R1 P0-5 + S134 iter-2 P0 fold) — promotion
  requires:
  - FPR `< 15%` across all task classes (mean per-class FPR)
  - Sample size `N ≥ 200` total `task_route_advised` events
  - Per-cell minimum `N ≥ 30` events (uniformly, not "dominant cell")
  - All 4 task classes (S/M/L/XL) populated above threshold
- **Calendar-gate retraction** (ADR-095 doctrine; reinforced S139
  reaffirmation) — "30-day audit-log soak window" criterion is
  RETRACTED. Substantive criteria (sample-size + class-diversity +
  verifier-determinism) ARE the gate. Sample volume may be satisfied
  by (a) live audit-log accumulation OR (b) synthesized corpus run
  through actual `task-route.py:classify()` logic. Memory:
  [[feedback-no-calendar-gates-ai-workflow]].
- **Ground-truth labeling discipline** (S134 P0 #5 + iter-2 fold) —
  audit-log is append-only by ADR-018. Ground-truth labels MUST NOT
  backfill the original `task_route_advised` row. Register NEW
  append-only audit action `task_route_ground_truth_label` keyed by
  `contract_id` to join with the original event.
- **Strictest-existing-threshold rule** (ADR-125 §B + S134 fold) —
  AEK is less safety-critical than confidence-gate (which uses <1%
  from ADR-019). FPR <15% threshold is defensible for advisory-tier
  workstream classification.

## Decision

### §A — Phase renaming

The empirical promotion phases in ADR-104 are renamed:

| Old name (collides with PLAN-071) | New name (this amendment) |
| --------------------------------- | ------------------------- |
| Phase 2 calibration baseline      | **Calibration C2**        |
| Phase 3 FPR measurement           | **Calibration C3**        |
| Phase 4 state-machine conformance | **Calibration C4**        |

All forward references in ADR-104 § Reopen criteria,
§ Negative consequences, and downstream documentation MUST use the
`C2/C3/C4` form. The numeric phase suffixes (1, 5, etc.) in PLAN-071
internal execution waves are unaffected.

### §B — Dated promotion criteria

PLAN-101 ship date (`v1.35.0`, shipped 2026-05-18) anchors the
data-volume vote trigger. Per ADR-095 doctrine (no calendar gates), the
trigger is **event-based**, not calendar-bound:

- **Vote-trigger condition (ADR-095 compliant):** Owner ceremony vote
  fires when EITHER of the following substantive conditions is first met
  (whichever comes first):
  - **N ≥ 200** total `task_route_advised` audit events accumulated
    since v1.35.0 ship (live or synthesized corpus per §D), OR
  - **All 4 task classes (S/M/L/XL)** have per-cell minimum N ≥ 30
    events AND FPR < 15% across all cells (i.e. full §C criteria met).
- **Vote outcome contract:** Owner ceremony at trigger fires records EITHER:
  - `PROMOTE` — criteria met; emit per-class promotion ADR
    (mirrors ADR-019-AMEND-2-CLASS-SHA_EXISTS pattern S140)
  - `DEFER` — criteria not met; record "new trigger (advance by 100
    additional `task_route_advised` events)" with rationale; max 3
    deferrals = 270d total cap (≤ 600 total events backlog ceiling)
  - `RESCOPE` — escalate per §C below

> **Note (ADR-095 retraction):** The original §B wording referenced a
> hardcoded date "2026-08-16 (PLAN-101 ship + 90 days)". That calendar
> gate is RETRACTED per ADR-095 doctrine and
> [[feedback-no-calendar-gates-ai-workflow]]. The event-based trigger
> above replaces it. The deferral cap "270d" is also retired; the
> replacement cap is "3 additional batches of 100 events each" (300
> events max backlog beyond the initial 200 trigger).

### §C — Numeric thresholds

| Threshold        | Value      | Source / rationale                                |
| ---------------- | ---------- | ------------------------------------------------- |
| Per-class FPR    | `< 15%`    | ADR-125 §B strictest-existing-threshold; advisory-tier defensible |
| Total events     | `N ≥ 200`  | R1 P0-2 closure; PLAN-100 precedent               |
| Per-cell minimum | `N ≥ 30`   | S134 iter-2 P0 fold (uniform; NOT dominant-cell)  |
| Class coverage   | 4 of 4     | S/M/L/XL all populated above per-cell minimum     |
| FPR method       | Wilson 95% | Wilson lower-bound proxy; matches PLAN-100        |

Sparse cells (N < 30) MUST be marked `insufficient-data` in the FPR
matrix and EXCLUDED from the global FPR aggregate until the next
calibration refresh.

### §D — Calendar-gate retraction

The "30-day audit-log soak window" criterion in PLAN-101 original
frontmatter is RETRACTED per ADR-095 doctrine + memory
[[feedback-no-calendar-gates-ai-workflow]]. Substantive criteria
(§C above) replace calendar holding. Sample volume may be satisfied
by:

- (a) live audit-log accumulation of `task_route_advised` events, OR
- (b) synthesized corpus run through real `task-route.py:classify()`
  via `.claude/plans/PLAN-101/synthesize-corpus.py`, ground-truth
  labels knowable a priori since corpus controls descriptions.

PLAN-101 ships under path (b) — framework workload alone does not
produce 200 events in any feasible window. Audit ground-truth labels
emit via heuristic-auto over the synth corpus
(`ground_truth_source=heuristic_auto`).

### §E — Ground-truth-label new action registration

Register NEW append-only audit action `task_route_ground_truth_label`
in `.claude/hooks/_lib/audit_emit.py`:

- Add `task_route_ground_truth_label` to `_KNOWN_ACTIONS`
- Define `_TASK_ROUTE_GROUND_TRUTH_LABEL_ALLOWLIST` frozenset:
  `{action, ts, session_id, project, contract_id,
   ground_truth_class, ground_truth_source,
   annotation_confidence_bps}`
- Wire dispatch branch in `emit_generic()` (mirror existing
  `task_route_advised` pattern at line 3414)
- Add SPEC/v1/audit-log.schema.md row at v2.20

**No typed wrapper.** Matches the existing `task_route_advised`
precedent (PLAN-071 / ADR-104 ceremony): the action is emitted via
`emit_generic(action="task_route_ground_truth_label", ...)`; the
Sec MF-3 allowlist scrub fires inside the `emit_generic` dispatch
branch. Avoiding a typed wrapper keeps the
`_EXPECTED_PUBLIC_SYMBOLS` contract gate stable (no new public
emitter requires a contract bump beyond the SHA256 + count
rebaseline) — Codex R2 iter-1 P1 #3 fold.

Field semantics:

| Field                       | Type   | Required | Notes                                                       |
| --------------------------- | ------ | -------- | ----------------------------------------------------------- |
| `action`                    | string | yes      | literal `task_route_ground_truth_label`                     |
| `ts`                        | string | yes      | ISO-8601 UTC                                                |
| `session_id`                | string | yes      | producer session                                            |
| `project`                   | string | yes      | producer project                                            |
| `contract_id`               | string | yes      | join key — matches original `task_route_advised.contract_id` |
| `ground_truth_class`        | enum   | yes      | `S` / `M` / `L` / `XL`                                      |
| `ground_truth_source`       | enum   | yes      | `heuristic_auto` / `manual_review`                          |
| `annotation_confidence_bps` | int    | yes      | 0..10000 (basis points; 7000 = 70% threshold for Stage 2)   |

LLM06 hold: raw task descriptions NEVER persisted. Sec MF-3
allowlist scrub enforced via `_scrub_ceo_boot_event` helper
(mirrors PLAN-104 pattern).

Kernel extension kernel-override token:
`CEO_KERNEL_OVERRIDE=PLAN-101-WAVE-B-AUDIT-EMIT-EXTENSION`
(per PLAN-090-FOLLOWUP / PLAN-097 / PLAN-100 precedent).

### §F — Conformance test obligation

`.claude/scripts/tests/test_aek_state_machine.py` MUST exist with
`≥50` transition test cases covering REAL predicates in
`task-route.py:classify()`:

- empty/missing task_description path → safe-default `M`
- unknown/unrecognized predicate fallthrough
- boundary thresholds: S↔M↔L↔XL
- multi-predicate conjunction (description-keyword + size-hint)
- canonical-path detection → `XL`
- veto-domain detection (auth/financial/PHI) + multi-module → `XL`
- schema-change signal → `XL`
- workflow class (release/ci/rag) → `XL`
- multi-module + test-infra → `XL`
- ITIMER budget exceeded → safe-default `M`
- Cf (invisible format chars) + NFKC normalization

Mutation testing target `≥80%` kill-rate via
`.claude/scripts/mutation-test.py` against `classify()` predicates
in `task-route.py` (S134 P0 #2 fold — NOT `_decide_with_matrix`
which lives in `check_pair_rail.py`).

## Consequences

### Positive

- **Empirical promotion pathway dated** — no perpetual deferral.
  Owner ceremony at vote-trigger date forces a decision (PROMOTE
  / DEFER / RESCOPE) even when criteria-met is ambiguous.
- **Calendar gate retracted** — sample volume satisfied via
  synthesized corpus through real `classify()` verifier. PLAN-101
  ship not blocked by "30 days of audit-log accumulation" that
  framework workload cannot produce.
- **Audit-log append-only invariant preserved** — ground-truth
  labels go to a NEW action `task_route_ground_truth_label`, not
  a backfill of the original `task_route_advised` row. Sec MF-3
  allowlist scrub enforced; LLM06 raw-text hold preserved.
- **Per-class promotion pattern established** — when calibration
  FPR threshold is met for individual classes (e.g., S-class
  empirically <5% FPR), ADR-104-AMEND-1-CLASS-S amendment can
  ship per the ADR-019-AMEND-2-CLASS-SHA_EXISTS S140 pattern
  (governance-only commit; no tag).

### Negative

- **Synth corpus methodology disclaimer** — calibration FPR
  measured against synth corpus has the obvious circularity risk:
  if the corpus author and the classifier author share blind
  spots, the measurement misses them. Mitigation: Wave A.5
  anti-circularity discipline — corpus authored BEFORE classify()
  is re-read for this work; fixtures span all 4 classes; cross-LLM
  Codex R2 reviews the corpus + matrix.
- **Vote-trigger date is a soft commitment** — Owner must
  physically run the vote ceremony at 2026-08-16. If skipped, the
  amendment lapses to ADR-104 original ambiguity. Mitigation:
  Wave D catalogs the date in memory + CLAUDE.md §Current Work.
- **Deferral cap is rigid** — 270d total max (3 × 90d extensions) may
  be too short for organic adoption of `task-route.py` in adopter
  installs. Mitigation: amendment allows §RESCOPE escalation at any
  deferral point (does not require waiting for the 270d ceiling).

### Neutral

- **Cross-LLM Codex gate preserved** — per ADR-095 §gate-#6,
  ceremony bundle is reviewed by Codex MCP R2 (S141 thread TBD)
  before Owner-physical ship. Aligns with S140 ADR-019-AMEND-1
  precedent.

## Reopen criteria

- Calibration FPR rises above 15% in any subsequent calibration
  refresh → emit `aek_calibration_drift` event + Owner triage
  ceremony
- Per-class N drops below 30 in any refresh (audit-log staleness)
  → re-synthesize corpus + re-run calibration; document in plan
- Mutation kill-rate falls below 80% on `classify()` predicates
  (regression) → ADR amendment revisit + classifier hardening plan
- Ground-truth labeling source distribution skews toward
  `manual_review` (>10% of total) without quality justification →
  audit `heuristic_auto` accuracy + revise Wave B.1 protocol

## Empirical evidence cited

1. **PLAN-100 S139 precedent** — confidence-gate per-class block-
   mode shipped via ADR-019-AMEND-1 (PROPOSED) on the same dated-
   promotion pattern (drift detector + per-class kill-switch +
   ADR amendment).
2. **ADR-019-AMEND-1 S140 promotion ceremony** — PROPOSED→ACCEPTED
   pattern (no tag; governance-only commit) is the template for
   the subsequent ADR-104-AMEND-1-CLASS-* promotions.
3. **ADR-095 calendar-gate purge** — S139 cleanup commit `f8363ee`
   retracted PLAN-101's original 30d soak gate; this amendment
   formalizes the retraction in ADR form.
4. **Wave A.5 anti-circularity** — synth corpus authored against
   `task-route.py:classify()` decision tree per S134 P1 #1 fold;
   golden set fixtures re-used from PLAN-071 Phase 1 (22 train + 4
   holdout) where available; net new fixtures span boundary cells.
5. **S134 Codex R2 5-iter ACCEPT** — thread `019e3849-16b0-7782-
   865d-a250b4709a74` gpt-5.2 closed 5 P0 + 3 P1 findings in PLAN-101
   skeleton review; this amendment carries all 5 P0 folds (P0 #2
   classify() target, P0 #3 audit-query.py command verification,
   P0 #4 duration_ms semantic correction, P0 #5 ground-truth-label
   action, R2 P0 fold Wave 0.0 binding).

## References

- ADR-104 — original AEK advisory-only ADR (PLAN-071 S87 v1.14.0)
- ADR-095 — calendar gate final purge (this amendment's authority
  for §D)
- ADR-019-AMEND-1 — confidence-gate per-class block-mode lifecycle
  (S140 precedent for §B + §F)
- ADR-124 §Part 2 — hotfix scope cover (this amendment's authority
  for kernel extension under non-major version bump)
- ADR-125 §B — Tier-B conditional default (this amendment's tier
  classification)
- PLAN-101 — implementation plan (Wave 0..D)
- PLAN-101 Wave 0.0 — PLAN-084 canonical roadmap binding
- Memory: [[feedback-no-calendar-gates-ai-workflow]] — calendar-
  gate doctrine reinforcement (S139)
