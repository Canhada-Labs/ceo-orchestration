# ADR-033: Cost/Budget enforcement lifecycle (advisory Sprint 11, gate conditional Sprint 12)

**Status:** ACCEPTED
**Date:** 2026-04-14
**Sprint:** 11 (PLAN-011 Phase 6)
**Related:** ADR-019 (confidence-gate three-state lifecycle — pattern parent),
ADR-024 (perf baseline measure-then-gate precedent),
ADR-016 (spawn token tracking — the data source),
ADR-017/020 (pruning policy — conversion-criterion precedent),
ADR-001 (audit-dir state convention)

## Context

Sprint 6 shipped `tokens_in` / `tokens_out` / `tokens_total` nullable
fields on every `agent_spawn` audit event (ADR-016). That gave us a
per-spawn cost signal but **zero enforcement**: a runaway loop (or an
Architect dogfood session with 200 spawns) is invisible until the
Owner checks the dashboard by hand. The DevOps skill MANTRA ("if CI is
advisory forever, CI is a vibe — set the conversion criterion the day
you add it") applies directly: we need a budget hook AND the plan to
flip it to enforcing.

ADR-019 (confidence gate) and ADR-024 (perf baseline) already set the
three-state precedent: measure-only → advisory-with-floor → blocking.
This ADR adopts the same shape for token budgets with the additional
wrinkle of an Owner-only **bypass** rate-limited to prevent abuse.

## Decision drivers

- **No thin-air thresholds.** `CEO_MAX_PLAN_TOKENS=1_000_000` is the
  *initial* advisory cap; the enforcing threshold comes from real FPR
  data collected in Sprint 11, not a guess.
- **Machinery without activation.** Sprint 11 ships the hook *and* the
  env gate machinery, but the hook always allows. Sprint 12 decides
  the flip based on measured false-positive rate.
- **Owner-only bypass + audit trail (H13).** `CEO_BUDGET_BYPASS=1`
  mirrors ADR-019's `CEO_CONFIDENCE_BYPASS`: Owner-scoped escape
  hatch. Every bypass emits `budget_bypass_used` with caller PID +
  session_id + timestamp. Rate-limited to N/24h per plan — exhaustion
  writes a breadcrumb instead of a bypass event (honest accounting).
- **Fail-open on infra.** Plan-id derivation, audit-log scan, and
  frontmatter parse all funnel through try/except → allow + breadcrumb.
- **Snapshot idempotency.** `/agent budget` is a read-only report
  (M7). Two identical invocations produce identical output.

## Decision

### 1. Three-state lifecycle

```
         Sprint 11 (this)        Sprint 12 (conditional)      Sprint 13+ (conditional)
┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐
│  State 0             │──▶│  State 1             │──▶│  State 2             │
│  advisory (log+warn) │   │  advisory-with-floor │   │  blocking-on-over    │
│                      │   │                      │   │                      │
│ - check_budget.py    │   │ - enforce on only    │   │ - enforce on all     │
│   ALWAYS allows      │   │   repeat offenders   │   │   over-cap spawns    │
│ - budget_exceeded    │   │ - first 3 over-cap   │   │ - Owner bypass hatch │
│   emitted on cap     │   │   in 24h → warn only │   │ - CI gate optional   │
│ - /agent budget      │   │ - 4th → block with   │   │                      │
│   rollup available   │   │   reason + stderr    │   │                      │
│ - FPR data collected │   │ - CEO_BUDGET_ENFORCE │   │                      │
│                      │   │   Owner-only flag    │   │                      │
└──────────────────────┘   └──────────────────────┘   └──────────────────────┘
```

### 2. Flip Criteria Table (H16)

Every state transition has a published **criterion / metric /
window / fallback** before the transition ships. This table is the
normative contract.

| Transition     | Criterion                                                                                               | Metric                                                    | Window      | Fallback (if fails)                                 |
|----------------|---------------------------------------------------------------------------------------------------------|-----------------------------------------------------------|-------------|-----------------------------------------------------|
| **0 → 1**      | `budget_exceeded` FPR < 5% of Agent spawns AND ≥ 30 over-cap events observed                            | `count(budget_exceeded where legitimate=true) / count(agent_spawn)` | 30 days     | Hold State 0; raise default cap or refine plan-scoping. |
| **1 → 2**      | Under State-1, no legitimate spawn blocked > 1× per month across 2 consecutive months                   | `count(block_reason=budget_exceeded where legitimate) per month` | 60 days     | Hold State 1; tune repeat-offender detector.        |
| **Any → N-1**  | > 1 legitimate spawn / day blocked OR any P0/P1 incident where budget gate wedged emergency fix         | rollback incident log                                     | immediate   | Revert `CEO_BUDGET_ENFORCE=0`; open `budget-fp` issue. |

**Legitimacy classification:** A `budget_exceeded` event is classified
*legitimate* (non-FP) when the Owner triages the event within 14 days
and marks it "intended spend" (large plan, architectural exploration).
Unclassified events default to FP after 14 days — we'd rather be
conservative about calling things "true positives". Triage CLI lands
in Sprint 12 alongside the flip ADR.

### 3. Env var surface (contract)

| Var                               | Sprint 11 default | Meaning                                                                                      |
|-----------------------------------|-------------------|----------------------------------------------------------------------------------------------|
| `CEO_MAX_SPAWN_TOKENS`            | `100_000`         | Per-spawn cap. **Sprint 11 logs only** — enforcement deferred to Sprint 12 IFF 0→1 transition. |
| `CEO_MAX_PLAN_TOKENS`             | `1_000_000`       | Per-plan cap. Emits `budget_exceeded` in State 0; enforces in State 2.                       |
| `CEO_BUDGET_ENFORCE`              | `0`               | Sprint 11 flag (unused). Sprint 12 flip criterion documented in row 1 of this table.         |
| `CEO_BUDGET_BYPASS`               | unset             | Owner-only. `1` → allow regardless of cap. Emits `budget_bypass_used` audit event.           |
| `CEO_BUDGET_BYPASS_MAX_PER_DAY`   | `10`              | Rate limit: at most N bypasses / 24h per plan_id. Over-limit → breadcrumb, no emit.          |

`CEO_BUDGET_ENFORCE=1` is documented in exactly two places (mirrors
ADR-019 §2):

1. **`RELEASE.md`** v1.2.0-rc.1 — under "Owner-only knobs".
2. **`docs/FOR-EMPLOYEES.md`** — under "Flags not to touch".

NOT documented in `QUICKSTART.md`, `TROUBLESHOOTING.md`, or `README.md`.
Sprint 12 may elevate once FPR proves acceptable.

### 4. Rate limiting (H13)

10 bypasses per plan per rolling 24h window (configurable, `default=10`).
Rationale: an Architect dogfood session with 200 spawns across 3 plans
should never consume more than 30 bypass slots in a day; legitimate
emergency debugging should never exceed 2-3 in a 24h window. `10`
is conservative — the cap is not the point, the **audit trail** is.

**Over-limit behavior (State 0):** the hook ALLOWS (advisory-only),
emits a `systemMessage` warning to the user, writes a breadcrumb to
`audit-log.errors`, and deliberately skips the `budget_bypass_used`
emit. That last bit is the honest accounting: we don't want to count
"tried to bypass but was denied" as "used a bypass".

**Over-limit behavior (State 2, future):** same breadcrumb + skipped
emit, plus the spawn is blocked with a block reason pointing the user
at either (a) wait for the 24h window to roll, (b) flip
`CEO_BUDGET_BYPASS_MAX_PER_DAY` higher (Owner only), or (c) raise
the plan cap.

### 5. Rollback signal

Revert State 1 → State 0 (or 2 → 1) if ANY of:

- **> 1 legitimate spawn/day blocked** over 7 consecutive days.
- **Any P0/P1 incident where the budget hook blocked an emergency fix.**
  Escape hatch (`CEO_BUDGET_BYPASS=1`) must unblock within 5 seconds;
  if it doesn't, the hook is broken — revert immediately.
- **Repeated flakes on audit-log parse** (> 3 breadcrumbs/day in
  `audit-log.errors` tagged `check_budget:`). Indicates log corruption
  or parse drift — revert and triage.

Post-rollback: open issue tagged `budget-fp` with the blocked event +
`budget_exceeded` event JSON + Owner triage decision.

### 6. Known bypasses (documented, not fixed)

- **Fail-open on missing plan_id.** A session with zero active plans
  (no `status: executing|reviewed|draft` file) skips the check. This
  is deliberate: the hook should not invent spend attribution.
- **Fail-open on ambiguous plan_id.** Two active plans → skip. A
  future `CEO_BUDGET_PLAN_ID=PLAN-NNN` override is reserved for
  Sprint 12 if multi-plan sessions become common.
- **Fail-open on audit-log read failure.** If the log is absent,
  permission-denied, or corrupt, the tally is 0 and no cap triggers.
  Mitigated by: audit-log write errors already surface via `audit-log.errors`
  breadcrumbs, so corruption is detected through a different channel.
- **Legacy event aliasing.** Pre-Sprint-11 `agent_spawn` events without
  `plan_id` fall back to project-dir matching. This over-counts for
  single-plan projects — acceptable approximation (and by Sprint 12
  all events carry plan_id).

### 7. Schema + audit events

SPEC/v1/audit-log.schema.md already lists `budget_exceeded` and
`budget_bypass_used` action slugs (pre-staged by CEO). Emitters:

- `emit_budget_exceeded(plan_id, spawn_id, tokens_used, cap, scope)`
- `emit_budget_bypass_used(plan_id, caller_pid, reason)`

Both are additive — no migration.

### 8. Pricing integration

`docs/provider-pricing.md` ships with this ADR as a per-model
`$/1k tokens` table. The budget hook does **not** consume pricing in
Sprint 11 (tokens-only logging); only `/agent budget` rollups surface
cost. Sprint 12 may push the rollup into the hook output itself if
Owner demand signals.

## Consequences

### Positive

- Three-state pattern matches ADR-019 + ADR-024 — legible, easy to
  audit, predictable transitions.
- Bypass rate limit is the **first** rate-limited Owner escape hatch
  in the framework. Sets precedent for future gates (output-safety,
  skill-patch).
- `/agent budget` is callable from CI, dashboards, and `/loop` —
  snapshot idempotency is load-bearing for those consumers.
- Pricing table is fully additive — no schema migration, and TBD
  rows are honest about unknown costs.
- Fail-open contract preserved throughout — infra errors never block
  legitimate spawns.

### Negative

- Sprint 11 produces **no regression signal** until 30 days of State
  0 data accumulate. A runaway 5M-token session that lands on
  2026-04-15 is invisible to the gate until ~2026-05-14. Mitigation:
  the advisory `systemMessage` surfaces immediately in-session, and
  the dashboard panel (Phase 4 of PLAN-010 already shipped) makes
  spend trend visible ahead of the formal transition.
- Bypass rate limit is a **per-plan** counter. An attacker with a
  crafted plan file could rotate plan_ids to evade the cap. Not in
  scope — this is a quality signal, not a security boundary.
- Legacy events (no plan_id) fall back to project-scope tally. In a
  repo running multiple projects concurrently, cross-contamination is
  possible. Acceptable approximation for single-repo use.

### Neutral

- No Owner-facing UI knobs beyond env vars. The dashboard already
  surfaces `budget_exceeded` events (Phase 4); no new widget required
  in Sprint 11.
- `CEO_MAX_SPAWN_TOKENS` is reserved but unused in Sprint 11.
  Logging it now would spam the audit-log without signal — deferred
  to Sprint 12.

## Explicit non-goals for Sprint 11

- No enforcement. `CEO_BUDGET_ENFORCE=1` is reserved but unwired.
- No per-spawn cap enforcement (reserved var only).
- No triage CLI for legitimacy classification — Sprint 12.
- No dashboard red-line at over-cap — the existing token panel is
  sufficient for Sprint 11.
- No cross-plan rollup alerts. `/agent budget --since 24h` covers the
  use case manually.
- No auto-promote schedule. All state transitions are Owner-signed.

## Blast radius

**L2** — one new hook (check_budget.py ~380 LOC), one new script
(budget-summary.py ~320 LOC), one slash command, this ADR, one
pricing doc, appended settings.json entry. No existing hooks
modified. Tests additive. No env-var knobs promoted to user-facing
docs. Reversibility: HIGH — delete the 5 new files + revert the
settings.json append.

## Transition timeline (target, not committed)

| State | Date (target)               | Trigger                                     |
|-------|-----------------------------|---------------------------------------------|
| 0 (advisory) | 2026-04-14 (Sprint 11 ship) | This ADR                                    |
| 0 → 1 decision | 2026-05-14 (30d of data)    | FPR test per §2 row 1                       |
| 1 (advisory-with-floor) | Sprint 12 IFF §2 passes  | New ADR amending this one                   |
| 1 → 2 decision | +60 days clean data       | §2 row 2                                    |
| 2 (blocking gate) | Sprint 13+ IFF stable      | New ADR amendment                           |

No date is committed — all are *earliest possible*.

## Transition Log

*This appendix follows ADR-041 Transition Log Convention. Each row records
a state transition triggered by a flip criterion in its window.*

| Date | From-State | To-State | Evidence-Link | PR-Ref | Signer |
|------|------------|----------|---------------|--------|--------|
| _(empty — first flip pending per PLAN-012)_ | | | | | |

## References

- PLAN-011 Phase 6 — ships the hook + CLI + this ADR + pricing doc.
- PLAN-011 consensus.md H13 — Owner-only bypass + audit trail.
- PLAN-011 consensus.md H16 — flip-criteria-table-per-ADR requirement.
- PLAN-011 consensus.md L3 — provider-pricing.md scope.
- PLAN-011 consensus.md M7 — `/agent budget` idempotency contract.
- PLAN-011 consensus.md M8 — command namespacing (`/agent-budget` file).
- ADR-019 — confidence-gate three-state lifecycle (pattern parent).
- ADR-024 — perf baseline policy (measure-then-gate sibling).
- ADR-016 — spawn token tracking (data source).
- ADR-017 / ADR-020 — pruning policy (conversion-criterion precedent).
- `.claude/hooks/check_budget.py` — the hook.
- `.claude/scripts/budget-summary.py` — the CLI rollup.
- `.claude/commands/agent-budget.md` — the slash command.
- `docs/provider-pricing.md` — the pricing table.

## Enforcement commit

`7009a47d19a9` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
