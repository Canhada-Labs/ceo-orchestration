---
description: GOAP A* advisory-only planner — plain-English goal → action tree. ADVISORY ONLY; Owner must confirm each action. Usage — /goap "<goal text>"
argument-hint: "\"<plain-English goal text, <=500 chars>\""
---

# /goap — Advisory-only A* state-space planner (PLAN-098 / ADR-132)

You are about to invoke the GOAP advisory planner. The output is **ADVISORY ONLY** —
the planner produces an action tree showing the cheapest A* path from the current
state to the goal, but it **NEVER** auto-dispatches `/spawn`, `/debate`, `/closeout`,
or any other action. The Owner (CEO) must explicitly confirm each action before any
hand-off happens.

This contract is enforced by:

1. **ADR-132** `goap-advisory-planning-doctrine` declares the advisory-only invariant.
2. **ADR-010** architect-recursion guard + canonical-edit sentinel: the framework
   blocks any spawn carrying delegated-architect intent via the
   `architect_role_not_delegable` block path; the GOAP planner offers
   *suggestions*, not delegated authority.
3. **`check_agent_spawn.py` hook (PLAN-098 Wave C.2)**: if a spawn carries a
   `goap-plan-id` reference without an explicit Owner-confirmation marker (`##
   GOAP CONFIRM` block AND `CEO_GOAP_CONFIRMED=1` env), the spawn is blocked with
   `GOVERNANCE: goap_advisory_without_owner_confirm`.

## Arguments received

The user invoked: `/goap $ARGUMENTS`

## Argument contract

- The full argument string is the **plain-English goal text** (max 500 chars).
- Examples:
  - `/goap ship v1.32.0` — goal: `plan_status=done` AND `tagged=true`
  - `/goap promote ADR-132 to ACCEPTED` — goal: `adr_status=accepted`
  - `/goap closeout session` — goal: `session_closed=true`
- Supported leading verbs (deterministic parser; LLM extension deferred):
  `ship`, `release`, `tag`, `promote`, `execute`, `review`, `close`, `closeout`.
- Unsupported verbs return `status: goal-parse-failed` advisory marker.

## Kill-switches

| Env var | Effect |
|---|---|
| `CEO_GOAP_ADVISORY_ENABLED=0` | Disables `/goap` entirely; emits `goap_disabled_by_env`. |
| `CEO_GOAP_CONFIRMED=1` | Owner-side env confirmation marker required when spawning from a GOAP-recommended plan. Set by Owner in the same shell as the `/spawn` call, NEVER by the model. |

## Procedure

### Step 1 — Run the planner

```bash
python3 .claude/scripts/goap-planner.py --goal "<goal text>" --format markdown
```

The script:

1. Honors `CEO_GOAP_ADVISORY_ENABLED=0` short-circuit (returns "disabled" markdown).
2. Parses goal text via deterministic verb-rule parser; failures return
   `goal-parse-failed` advisory output (AC13 fall-through).
3. Loads the action library + cost baseline from
   `.claude/plans/PLAN-098/action-cost-baseline.json` (AC14; rebaselined quarterly).
4. Runs A* with `MAX_PLAN_DEPTH=12`, `MAX_PLAN_NODES=100`, wall-clock 5s hard
   limit (AC11 latency target p99 ≤ 800ms cold / ≤ 200ms warm).
5. Emits per-edge audit events (`goap_edge_explored`, sampled 1-in-10 when
   frontier > 50) + terminus `goap_search_summary`.
6. Rejects revisits via `frozenset` closed-set on `state_hash`; emits
   `goap_cycle_detected` (AC12).
7. Renders markdown action tree, capped at 50 nodes (AC4 UX cap), with
   pre-conditions + effects + cost annotations per node, plus the
   `> ADVISORY ONLY` banner at the top.

### Step 2 — Surface the plan to the Owner

Print the planner's markdown output verbatim. Do NOT:

- summarize it in your own words
- act on any of the recommended actions
- spawn agents, edit files, or run commands based on the plan

### Step 3 — Wait for explicit Owner confirmation

The Owner reviews the action tree and decides which actions (if any) to
authorize. The CEO follows this protocol:

1. If the Owner approves a specific action, the Owner sets
   `CEO_GOAP_CONFIRMED=1` in their shell AND types the action manually
   (e.g. `/spawn Staff Code Reviewer review src/...`).
2. The framework's spawn hook validates the env marker before allowing
   any GOAP-tagged spawn to proceed.
3. The model NEVER sets `CEO_GOAP_CONFIRMED` itself — that env is the
   Owner's physical-presence proof per the ADR-010 architect-recursion
   guard (non-delegation invariant).

### Step 4 — Audit emit

The planner's terminus event `goap_search_summary` already fired during
Step 1. The `goap_recommendation_accepted` event is **registered** in
`_KNOWN_ACTIONS` with an `emit_*` function in
`.claude/hooks/_lib/audit_emit.py`, but **the call site that fires it on
Owner-confirmed spawn is NOT WIRED in v1.31.0**. Wiring will land in a
future PLAN-098 follow-up plan as a prerequisite for promotion-gate
measurement (see §Promotion gate below).

## Promotion gate (advisory → blocking)

`/goap` ships **Tier A** (observable-ON) per ADR-125. Promotion to Tier B
(blocking) requires ALL of:

- ≥30 dispatched plans with `goap_recommendation_accepted=true` audit events
- accept-rate ≥80% (rendered → accepted ratio)
- `goap_replan_triggered` count ≤2× per-plan median
- `ADR-132-AMEND-1` ACCEPTED via explicit Owner amendment ceremony

**Instrumentation prerequisites (currently UNFULFILLED in v1.31.0)** —
the three numeric thresholds above are not measurable from the v1.31.0
audit surface alone. A future PLAN-098 follow-up plan must add:

- (a) `goap_recommendation_accepted` call-site emit wire-in
- (b) `goap_recommendation_rendered` NEW event (denominator for accept-rate)
- (c) `goap_recommendation_overridden` NEW event (distinguishes ignored vs
  overridden recommendations)
- (d) `plan_id` correlation field on `goap_replan_triggered` (per-plan
  replan denominator)

Default stance: **STAY advisory-only**. No auto-promotion paths exist.

## Limitations (v1.31.0)

- **Goal parser is rule-based.** No LLM integration in steady state (Tier-A
  §6b criterion 2). Verbs outside the canonical set return
  `goal-parse-failed`. Future LLM extension via opt-in adapter is documented
  but not wired in v1.31.0.
- **Action library is small (15 actions).** Covers spawn / debate / plan-flip /
  ADR / closeout / tag / ceremony patterns. Domain-specific actions (e.g.
  Supabase migrations, Vercel deployments) require future plan amendments.
- **Cost baseline is approximate.** Values derived from S128..S131 observed
  ceremonies. Rebaseline cadence: quarterly. Stale baselines are advisory-only
  (no enforcement).

### Wave A — Owner spawn protocol (PLAN-105)

When you decide to dispatch a rendered action, your spawn prompt MUST
include BOTH markers so the override-detection hook can classify the
dispatch correctly:

```
goap-plan-id: PLAN-105
goap-action-id: spawn_code_reviewer

## GOAP CONFIRM
Owner approves this rendered action for dispatch.
```

The hook compares `goap-action-id` against the most-recent rendered
action set (≤5 min window) and emits:

- `goap_recommendation_accepted` — exact match (numerator for promotion gate)
- `goap_recommendation_overridden` — mismatch / missing marker / no recent render

Kill-switch: `CEO_GOAP_OVERRIDE_DETECTION_DISABLED=1` forces `_accepted`
unconditionally on allow-path (diagnostic only; never the steady-state
default).
