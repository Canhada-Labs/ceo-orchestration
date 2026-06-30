---
id: ADR-132
title: GOAP advisory-only planning doctrine
status: ACCEPTED
accepted_at: 2026-05-17
proposed_at: 2026-05-17
proposed_by: CEO (Session 132 PLAN-098 v1.31.0 ship-time draft; ACCEPT pending separate Codex R2 ceremony per PLAN-096/097 precedent)
related_plans: [PLAN-098]
related_adrs: [ADR-010, ADR-064, ADR-124, ADR-125, ADR-126, ADR-127]
supersedes: []
refines: [ADR-010]
amends: []
authorization: PLAN-098 ceremony sentinel `.claude/plans/PLAN-098/approved.md` + `.asc` (Owner GPG 0000000000000000000000000000000000000000)
tags: [advisory-only, goap, a-star, non-delegation-preserved, tier-a-default-on]
---

# ADR-132 — GOAP advisory-only planning doctrine

## Status

ACCEPTED. (Drafted PROPOSED Session 132 (2026-05-17); promoted to ACCEPTED
in a SEPARATE post-ship Owner ceremony after the Codex R2 3-iter ACCEPT,
per the established PLAN-096 (`ADR-042-AMEND-1`) and PLAN-097
(`ADR-062-AMEND-1` + `ADR-128`) precedent. The capability shipped v1.31.0
with ADR-132 in PROPOSED state; the GOAP planner is governed by this
doctrine from day one regardless of promotion state (no behavior gate on
the `ACCEPTED` flip). Frontmatter `status:` is the source of truth —
PLAN-113 W2 reconciled this body marker to match.)

## Date

2026-05-17

## Deciders

CEO (Owner). Codex R2 cross-LLM verdict pending post-ship.

## Tags

advisory-only / goap / a-star / non-delegation-preserved / tier-a-default-on

## Refines

- **ADR-010** (Canonical-edit sentinel + architect-recursion guard via
  `CEO_ARCHITECT_ACTIVE` env detection in `check_agent_spawn.py`. The
  framework enforces "architect role cannot be delegated to a subagent"
  mechanically — block reason code `architect_role_not_delegable` at
  `check_agent_spawn.py:1386`. GOAP planner offers *suggestions*, never
  delegated authority; ADR-132 preserves this invariant explicitly via
  §Decision Part 2.)

## Related

- ADR-064 `dynamic-tier-policy-learned-dispatch` — cost-envelope rules; N/A
  for GOAP advisory under Tier-A (no token spend in steady state)
- ADR-124 §Part 2 (post-audit-SOTA-execution-mode mechanical scope test —
  PLAN-098 `maps_to_roadmap_items` carries `F-A-SOTA-PLANNING-0001` +
  `F-A-SOTA-EDGE-OBSERVABILITY-0002` per the PLAN-092..PLAN-098 cohort
  field-presence convention; canonical PLAN-084 evolution-roadmap.md
  amendment is a planned separate followup `PLAN-084-AMEND-1`, NOT
  blocking ADR-132 promotion)
- ADR-125 §Tier A criteria (read-only / no token spend in steady state /
  single env kill-switch / reversal byte-identical except append-only audit)
- ADR-126 (Governed sidecar capability model — GOAP is NOT a sidecar; it lives
  in `.claude/scripts/goap-planner.py` core stdlib path. C-class authorization
  not required.)
- ADR-127 `Pair-Rail Case B procedural-block advisory promotion + Phase 4
  substantive-block pre-emptive advisory doctrine` — the analogue advisory→
  blocking promotion gate precedent (30d numeric soak gate + Owner amendment
  ADR required; numeric evidence necessary but NOT sufficient)
- PLAN-096 (`ADR-042-AMEND-1` PROPOSED-at-ship + post-ship Codex R2 3-iter
  ACCEPT promotion) and PLAN-097 (`ADR-062-AMEND-1` + `ADR-128` same pattern)
  — established the procedural precedent ADR-132 follows for PROPOSED-at-ship
  + post-ship promotion
- PLAN-098 (origin plan; defines waves A/B/C/D + 14 ACs + 9 audit actions)

## Context

S115 Codex P11 revalidation (thread `019e2203-d588-72f2-aae3-877596e5cda9`,
verdict LOCK 2026-05-13) refuted the prior "GOAP intrinsically incompatible
with framework governance" doctrine. The refutation rests on three premises:

1. **A* is pure-stdlib** (~250 LoC `heapq` + `dataclasses`). No C-class
   sidecar authorization required.
2. **Per-edge observability is feasible**: every explored edge can fire a
   `goap_edge_explored` audit event (with 1-in-N sampling for large
   searches + terminus aggregate).
3. **Advisory-only mode preserves the non-delegation invariant**: GOAP
   produces an action tree; Owner must physically confirm each action
   before any spawn / debate / closeout / tag dispatch.

A competing framework (`goal.ruv.io` "Ruflo") ships GOAP A* with autonomous
dispatch. ceo-orchestration's posture is fundamentally different — the
framework defers planning to Owner via `/debate` manual workflow plus
extensive observability. ADR-132 documents how GOAP fits within that
posture WITHOUT collapsing it.

## Decision

### Part 1 — Advisory-only invariant

**The GOAP planner output is ADVISORY.** The `/goap` slash command renders
a markdown action tree from a plain-English goal. The tree is presented
to the Owner verbatim. The Owner reviews the tree and physically initiates
any action the tree recommends. The model NEVER auto-dispatches based on
GOAP output.

Three mechanisms enforce this invariant:

1. **`/goap` slash command contract**: the command's procedure (`Step 3`
   in `.claude/commands/goap.md`) explicitly forbids the model from acting
   on the tree. The model surfaces the markdown and waits for Owner action.
2. **Owner-confirmation marker**: the spawn hook (Part 2 below) blocks any
   spawn that carries a `goap-plan-id` reference WITHOUT a `## GOAP CONFIRM`
   block AND a `CEO_GOAP_CONFIRMED=1` env var set by the Owner in the same
   shell. The env var is the physical-presence proof.
3. **Audit emit trail (event schema only in v1.31.0)**:
   `goap_recommendation_accepted` is REGISTERED in `_KNOWN_ACTIONS` with its
   `emit_*` function in `.claude/hooks/_lib/audit_emit.py` (Sec MF-3 caller
   field whitelist), but **the call site that fires this event on Owner-
   confirmed spawn is NOT WIRED in v1.31.0**. Wiring (e.g., in
   `check_agent_spawn.py` on the allow path for GOAP-tagged spawns) is a
   prerequisite for §Part 4 promotion-gate measurement and will land in a
   future PLAN-098 follow-up plan (no plan ID asserted by ADR-132 itself).

### Part 2 — Non-delegation invariant (ADR-010 recursion guard) preserved

ADR-010 establishes the architect-recursion guard: an active architect
session (signalled by env var `CEO_ARCHITECT_ACTIVE=1`) cannot spawn
another architect. The framework extends this mechanically into a broader
"architect role cannot be delegated to a subagent" doctrine via
`check_agent_spawn.py:1386` (block-reason code
`architect_role_not_delegable`), exercised by the `_probe_architect`
Phase 0 governance probe.

The GOAP planner does NOT function as a parallel architect — it is a
**search-result-renderer**. The distinction is mechanical:

| Architect (CEO) | GOAP planner |
|---|---|
| Authors plans (drafts) | Reads `.claude/plans/PLAN-098/action-cost-baseline.json` (static doctrinal action library) |
| Authorizes ADRs | Reads no ADR state |
| Initiates ceremonies | Renders ceremony candidates in markdown |
| Dispatches `/spawn` | NEVER dispatches |
| Sets `CEO_ARCHITECT_ACTIVE=1` | NEVER sets architect env |
| Owner physical presence | Mechanical state-space search |

The `check_agent_spawn.py` hook's ADR-010 recursion guard
(`CEO_ARCHITECT_ACTIVE=1` + architect-name detection + the
`architect_role_not_delegable` block path) continues to apply. GOAP cannot
bypass it because GOAP never spawns.

### Part 3 — Tier classification

GOAP advisory ships **Tier A** (observable-ON default) per ADR-125. All four
Tier-A criteria hold:

1. **Read-only**: GOAP outputs markdown action tree; does NOT dispatch, edit
   files, or mutate framework state.
2. **No token spend in steady state**: A* is local computation (stdlib only).
   Goal parsing is one-shot deterministic regex at `/goap` invocation
   (NOT continuous LLM polling). A future LLM-parser extension is documented
   in PLAN-098 as a v2.0-defer item but is NOT implemented or wired in
   v1.31.0; no symbol named `_llm_parse_goal` exists in `goap-planner.py`.
3. **Single env-var kill-switch**: `CEO_GOAP_ADVISORY_ENABLED=0` short-circuits
   the entire `/goap` path with `goap_disabled_by_env` emit + exit-0.
4. **Reversal byte-identical** except append-only `goap_*` audit emit (Tier-A
   exemption per ADR-125 §criterion-4 note).

### Part 4 — Advisory→blocking promotion gate (NEVER auto-applied)

Promotion of GOAP from Tier A (advisory) to Tier B (blocking — i.e., GOAP
recommendation becomes a hard pre-condition for `/spawn` dispatch) is gated
on FOUR cumulative thresholds. All MUST hold.

**Instrumentation prerequisites (currently UNFULFILLED in v1.31.0).** The
three numeric thresholds below are not measurable from the v1.31.0 audit
surface alone. The following instrumentation MUST land in a future PLAN-098
follow-up plan before any promotion-gate measurement is meaningful (no
specific plan ID asserted by ADR-132; the follow-up plan will be scaffolded
as part of the post-promotion measurement program):

- (a) `goap_recommendation_accepted` call-site emit wire-in at
  `check_agent_spawn.py` allow-path for GOAP-tagged spawns (numerator
  source for thresholds 1 and 2)
- (b) `goap_recommendation_rendered` NEW event — fires at `/goap`
  invocation with the count of rendered actions (denominator source for
  threshold 2 accept-rate)
- (c) `goap_recommendation_overridden` NEW event — fires when Owner
  rejects or substantively edits a rendered action before dispatch
  (needed to distinguish "ignored" from "overridden" in threshold 2)
- (d) `plan_id` correlation field added to `goap_replan_triggered` schema
  (needed for per-plan replan denominator in threshold 3 — currently the
  event has no plan binding)

**Thresholds (all MUST hold):**

1. **Dispatch volume**: ≥30 dispatched plans with `goap_recommendation_accepted=true`
   audit events. Requires prerequisite (a).
2. **Accept-rate**: ≥80% of GOAP recommendations physically confirmed by Owner
   (vs. ignored or overridden). Requires prerequisites (a) + (b) + (c).
3. **Replan stability**: `goap_replan_triggered` count ≤2× per-plan median
   (high replan rate indicates the heuristic is overconfident). Requires
   prerequisite (d).
4. **Owner amendment**: `ADR-132-AMEND-1` ACCEPTED via Codex R2 3-iter ACCEPT
   plus Owner GPG sentinel.

Default stance: **STAY advisory-only.** None of the three numeric thresholds
auto-promote; the amendment ADR is REQUIRED. This is the same governance
posture as ADR-127 (Pair-Rail Case B procedural-block advisory promotion
30d soak gate) and ADR-125 (risk-tiered defaulting): numeric evidence is
necessary but NOT sufficient for tier promotion.

### Part 5 — Heuristic admissibility obligation

The A* heuristic `h(state) = sum(cheapest action cost per unsatisfied goal
predicate, deduplicated)` is admissible by construction (each goal predicate
needs ≥1 producer action; minimum cost across producers; deduplicated across
shared producers cannot overcount). Admissibility is **property-tested**
(AC8) on ≥200 random `(s, s')` state pairs at every CI run. Test failure is
fail-CLOSED — the property test is part of the AC gate.

If a future action-library extension introduces a goal predicate with no
producer, the heuristic returns `0` contribution for that predicate (still
admissible — `h ≤ h*`). The search may then return `no_plan` / `frontier_exhausted`,
which is correct termination, not heuristic failure.

### Part 6 — Audit-surface (9 actions registered; 8 wired emit paths in v1.31.0)

The framework **registers 9 GOAP audit actions** in `_KNOWN_ACTIONS` and
provides 9 matching `emit_*` functions in `.claude/hooks/_lib/audit_emit.py`.
**8 actions have wired v1.31.0 emit paths; 1 (`goap_recommendation_accepted`)
is registered-only** pending the follow-up call-site wire-in (see §Part 4
prerequisite (a)).

| Action | Trigger | Sampling | v1.31.0 wired? |
|---|---|---|---|
| `goap_edge_explored` | A* explored edge | 1-in-N when frontier > 50; full otherwise | YES |
| `goap_search_aborted` | wall-clock / node-cap exceeded | always | YES |
| `goap_search_summary` | A* terminus (ok/no_plan/timeout/cap) | always (terminus aggregate) | YES |
| `goap_cycle_detected` | closed-set hit during A* | always (bounded by node-cap) | YES |
| `goap_depth_exceeded` | path length >= MAX_PLAN_DEPTH | always | YES |
| `goap_replan_triggered` | `replan_from()` invoked | always | YES (caller-invoked only) |
| `goap_replan_exhausted` | MAX_REPLAN_ATTEMPTS hit | always | YES |
| `goap_disabled_by_env` | kill-switch engaged at `/goap` entry | always | YES |
| `goap_recommendation_accepted` | Owner-confirmed spawn from GOAP plan | N/A until wired | **REGISTERED-ONLY** (call site deferred to a planned follow-up plan; see §Part 4 prerequisite (a)) |

All 9 actions are Sec MF-3 caller-field whitelisted at the `emit_*`
boundary in `.claude/hooks/_lib/audit_emit.py`. Goal text body is NEVER
persisted (privacy + LLM06 side-channel guard).

## Consequences

### Positive

- **Framework gains plain-English goal decomposition** without sacrificing
  the non-delegation invariant (ADR-010 recursion-guard preserved).
- **Replan-on-failure scaffolding exists** via `replan_from(state, attempt)`
  in `.claude/scripts/goap-planner.py`; v1.31.0 supports caller-invoked
  replan only. Automatic replan-on-action-failure (a failure-event listener
  that invokes `replan_from()` when a dispatched action's expected effect
  doesn't materialize) is a documented future capability, NOT shipped in
  v1.31.0.
- **Tier-A default-ON** + kill-switch posture matches PLAN-097 RAG routing
  precedent: capability defaults to useful, with single-env reversal.

### Negative

- **Action library bound to PLAN-098 baseline.** Adding a new action requires
  a plan amendment (cost baseline + pre/effect schema). This is intentional —
  schema drift is the cost of doctrinal action sets.
- **Goal parser is deterministic only.** Inputs outside the canonical verb set
  return `goal-parse-failed`. LLM enhancement is opt-in future work.
- **Heuristic admissibility property test must be maintained.** Any future
  heuristic refactor MUST keep the AC8 property test green or the change
  fails-CLOSED at CI.

### Neutral

- ADR-132 in PROPOSED state ships v1.31.0; promotion to ACCEPTED is a separate
  post-ship ceremony. The capability is governed by ADR-132 from day one
  regardless of promotion state.

## Compliance

- ADR-010 architect-recursion guard / non-delegation invariant: preserved
  via §Decision Part 2 (GOAP never spawns; the `architect_role_not_delegable`
  block path at `check_agent_spawn.py:1386` continues to apply).
- ADR-064 dynamic tier policy: N/A (Tier-A no token spend in steady state).
- ADR-124 §Part 2 mechanical scope test: PLAN-098 `maps_to_roadmap_items`
  carries `F-A-SOTA-PLANNING-0001` + `F-A-SOTA-EDGE-OBSERVABILITY-0002`
  per the PLAN-092..PLAN-098 cohort field-presence convention; canonical
  PLAN-084 evolution-roadmap.md amendment is a planned separate followup
  (`PLAN-084-AMEND-1`).
- ADR-125 Tier-A criteria: all four satisfied (§Decision Part 3).
- ADR-126 capability-class authorization: NOT required (GOAP is not a sidecar).
- ADR-127 advisory→blocking promotion gate precedent: §Decision Part 4
  follows the same pattern (30d soak + Owner amendment ADR; numeric
  evidence necessary but NOT sufficient).
- PLAN-096 + PLAN-097 precedent: PROPOSED-at-ship + post-ship Codex R2
  3-iter ACCEPT promotion ceremony; ADR-132 follows the same procedural
  cadence.


## Codex MCP gate trail

Codex R2 3-iter ACCEPT trail (PLAN-098 promotion ceremony, S133, thread `019e371f-55cf-70a0-9e33-6382fd28f352`, gpt-5.5):

- This ADR R2 iter-1 (S133, gpt-5.5): ACCEPT-WITH-FIXES — 3 P0 + 4 P1 + 1 P2 findings folded into draft:
  (P0) ADR-051 misreference replaced with ADR-010 architect-recursion guard across frontmatter/§Refines/§Decision Part 2/§Compliance/§References;
  (P0) `goap_recommendation_accepted` claim corrected from "fires on Owner-confirm" to "registered-only in v1.31.0; call site deferred to future PLAN-098 follow-up plan";
  (P0) §Decision Part 4 numeric thresholds annotated with explicit instrumentation prerequisites (a)–(d) currently UNFULFILLED;
  (P1) ADR-124 §Part 2 F-A-SOTA-* mapping softened to PLAN-092..PLAN-098 cohort field-presence convention + planned `PLAN-084-AMEND-1` followup;
  (P1) ADR-115 §exception #1 removed as wrong authority; PLAN-096/PLAN-097 procedural precedent cited instead;
  (P1) `_llm_parse_goal` claim corrected to "future v2.0-defer extension; no symbol exists in goap-planner.py";
  (P1) snapshot/replan claims softened — planner reads only `action-cost-baseline.json` (static); `replan_from()` is caller-invoked only;
  (P2) ADR-127 added to `related_adrs` with its exact title.
- This ADR R2 iter-2: NEEDS-REWRITE — 1 P0 regression + 2 P1 folded:
  (P0) §Decision Part 6 table contradicted §Part 1 by claiming 9 wired emit paths — rewritten as "9 registered; 8 wired emit paths in v1.31.0" with new "v1.31.0 wired?" column; `goap_recommendation_accepted` row marked REGISTERED-ONLY;
  (P1) nonexistent `PLAN-098-FOLLOWUP-emit-wireup` plan ID removed; reworded to "future PLAN-098 follow-up plan" without asserting an ID;
  (P1) `.claude/commands/goap.md` operator-facing doctrine updated to match draft (ADR-051→ADR-010, honest Step 4 emit description, promotion-gate instrumentation prerequisites added).
- This ADR R2 iter-3 (final): **ACCEPT** — disk cross-check verified Part 6 distinguishes 9 registered vs 8 wired; `goap_recommendation_accepted` consistently documented as registered-only; nonexistent plan ID removed; `.claude/commands/goap.md` no longer contradicts the ADR. Status flip PROPOSED → ACCEPTED authorized.

## References

- PLAN-098 — origin plan, full body
- ADR-010 — canonical-edit sentinel + architect-recursion guard
- ADR-125 — risk-tiered defaulting doctrine
- ADR-127 — Pair-Rail Case B procedural-block advisory promotion + Phase 4
  substantive-block pre-emptive advisory doctrine (advisory→blocking gate
  precedent)
- Codex thread `019e2203-d588-72f2-aae3-877596e5cda9` — P11 revalidation
  LOCK verdict (2026-05-13)
