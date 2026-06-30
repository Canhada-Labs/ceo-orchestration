---
id: ADR-133
title: Autonomous-loop opt-in capability doctrine
status: ACCEPTED
proposed_at: 2026-05-18
proposed_by: CEO (Session 142 PLAN-102 v1.36.0 ship-time draft; ACCEPT pending separate Codex R2 ceremony per PLAN-096/097/098 precedent)
related_plans: [PLAN-017, PLAN-102]
related_adrs: [ADR-064, ADR-115, ADR-121, ADR-124, ADR-125, ADR-126]
supersedes: []
refines: [ADR-125]
amends: []
authorization: PLAN-102 ceremony sentinel `.claude/plans/PLAN-102/architect/round-1/approved.md` + `.asc` (Owner GPG 0000000000000000000000000000000000000000)
tags: [opt-in-capability, autonomous-loop, cost-envelope, execution-context-hmac, six-layer-kill-switch, tier-c-default-off, not-directive-supersession]
accepted_at: 2026-05-20
accepting_session: S147
---

# ADR-133 — Autonomous-loop opt-in capability doctrine

## Status

ACCEPTED. (Drafted PROPOSED Session 142 (2026-05-18); promoted to ACCEPTED
in a SEPARATE post-ship Owner ceremony after the Codex R2 3-iter ACCEPT,
per the established PLAN-096 (`ADR-042-AMEND-1`) + PLAN-097
(`ADR-062-AMEND-1` + `ADR-128`) + PLAN-098 (`ADR-132`) precedent. The
capability shipped v1.36.0 with ADR-133 in PROPOSED state; the
autonomous-loop opt-in mechanism is governed by this doctrine from day one
regardless of promotion state (no behavior gate on the `ACCEPTED` flip).
Frontmatter `status:` is the source of truth — PLAN-113 W2 reconciled this
body marker to match.)

## Date

2026-05-18

## Deciders

CEO (Owner). Codex R2 cross-LLM verdict pending post-ship.

## Tags

opt-in-capability / autonomous-loop / cost-envelope / execution-context-hmac
/ six-layer-kill-switch / tier-c-default-off / not-directive-supersession

## Refines

- **ADR-125** (Risk-tiered defaulting A/B/C) — ADR-133 introduces a NEW
  CAPABILITY SURFACE under Tier C (`spendy-opt-in`, default-OFF), NOT a
  Tier-C→B promotion. ADR-125 §Tier C invariants are PRESERVED unchanged:
  cross-boundary autonomy + Owner physical consent mandatory + cost-envelope
  manifest required + NOT promotable to Tier B trivially.

## Related

- **PLAN-017** Phase 4 (S46 2026-04-22 — autonomous-loop parallelism shipped
  with Owner directive 2026-04-17 anti-goal #1 "default DESLIGADO forever").
  This ADR PRESERVES the anti-goal — the new capability ships INFRASTRUCTURE
  for opt-in autonomy, NOT a default flip. Any future "default-ON" attempt
  requires a NEW ADR superseding ADR-125 §Tier C invariant (higher bar than
  ADR-133's own promotion ceremony).
- **ADR-064** `dynamic-tier-policy-learned-dispatch` — cost-envelope rules
  per-class matrix; per-class cost-cap declared in
  `_lib/cost_envelope.py:_COST_CAP_MATRIX` (vibecoder $5/$25/$80/$3/1 loop,
  CTO $15/$75/$250/$10/2 loops, team $50/$250/$800/$30/4 loops; daily/weekly
  /monthly/per-plan/max-parallel).
- **ADR-115** §3 (instrumentation-without-policy-change) — covers shipping
  cost_envelope.py + check_cost_envelope.py + execution_context.py +
  swarm_circuit_breaker.py DEFAULT-OFF. The hook code is in-tree at v1.36.0;
  it activates ONLY when Owner per-class GPG sentinel + env flag are BOTH
  present.
- **ADR-121** (sentinel-signer-rotation) — referenced as DECLINED dependency:
  ADR-121 is still PROPOSED at v1.36.0 and PLAN-102 deliberately does NOT
  block on it. The execution_context HMAC pattern uses stdlib
  `hmac.new(key, msg, hashlib.sha256)` with `key` held as a
  coordinator-process-owned in-memory bytes (NOT a sentinel-signer-registry
  entry). Key lifecycle: regenerated at coordinator start; bounded to
  coordinator process; child spawns cannot read the key (process isolation).
- **ADR-124** §Part 2 (mechanical scope gate) — PLAN-102 `maps_to_roadmap_items`
  carries 3 F-A-* IDs bound to PLAN-084 canonical roadmap via
  approved-amendment-2026-05-18-plan-102-autonomous-loop-bind.md +
  findings-master.jsonl P0/P1 classification.
- **ADR-126** (governed sidecar capability model) — autonomous-loop opt-in
  is NOT a sidecar (it's an in-tree capability surface), but inherits the
  default-OFF + Owner-physical-consent discipline.

## Context

PLAN-017 (S46 2026-04-22) shipped autonomous-loop parallelism gated by
`CEO_SWARM=1` env flag (default absent → default-OFF) with Owner directive
2026-04-17 explicit "default DESLIGADO forever" as anti-goal #1.

Codex revalidation S115 (`019e2203-d588-72f2-aae3-877596e5cda9`) revisited
PLAN-017 with:

- **P1 REVISIT**: blanket "default DESLIGADO" stale; risk-tiered defaulting
  (ADR-125) governs — Tier C `spendy-opt-in` is the proper category, NOT
  a permanent prohibition.
- **P12 STILL-VALID**: autonomous-loop policy split into separate plan IS
  correct engineering IF that plan is concrete + immediate (NOT a perpetual
  deferral).
- **PLAN-102 = the concrete + immediate plan.**

S119 R1 identity-trust-architect VETO closure REFRAMED PLAN-102 from
"default-ON flip" to "opt-in capability". Rationale:

- Prior wording "default-ON" violated ADR-125 §Tier C invariant + Owner
  directive 2026-04-17 anti-goal #1.
- The plan SHIPS the cost-envelope hook + execution_context hooks +
  per-class cost matrix INFRASTRUCTURE, but autonomous-loop default
  remains OFF.
- Owner enables per-class via explicit Owner-physical opt-in (GPG sentinel
  `.claude/data/swarm/<class>-enabled.md.asc` + env flag
  `CEO_SWARM_<CLASS>_ENABLED=1`).
- PLAN-017 anti-goal #1 PRESERVED; ADR-125 §Tier C invariant respected.

S134 Codex R2 5-iter ACCEPT (`019e37d3-e6e3-7230-90e9-891c3afb5e0a`,
gpt-5.2; iter-1 BLOCK 3 P0 + 5 P1 → iter-5 ACCEPT) hardened the doctrine:

- P0 #1: Wave C "Default-ON flip" REMOVED — replaced with kill-switch
  chain verification (NO mode change to `_lib/persona_routing.py`).
- P0 #2: Wave 0 added for PLAN-084 canonical roadmap binding (3 F-A-*
  IDs + findings-master.jsonl P0/P1 classification).
- P0 #3: "directive amendment ceremony" phrase REPLACED with
  "NOT directive supersession" throughout the plan body + this ADR
  (§Decision §Part 2).
- P1 #1-5: test paths moved to `_lib/tests/` (pytest collection root) +
  audit taxonomy harmonized via reuse of `swarm_*` family (NOT parallel
  `autonomous_loop_*` namespace) + kill-switch env names harmonized with
  shipped `CEO_SWARM` family + execution_context HMAC uses stdlib pattern
  (NOT ADR-121 which is still PROPOSED).

## Decision

### Part 1 — Opt-in capability surface, not a directive supersession

PLAN-102 ships the following at v1.36.0:

1. **cost-envelope hook infrastructure** (`_lib/cost_envelope.py` +
   `check_cost_envelope.py`):
   - Tracks $X spent/day/week/month/per-plan per adopter via audit-log
     analysis (multi-window aggregation).
   - State file `~/.claude/projects/<project>/state/cost-envelope-<sha256[:32]>.json`
     where the sha256 input is `project_path || ":" || user_id || ":" || YYYY-MM-DD`.
     Each new date gets a NEW state file (cheap, no migration); cross-
     date isolation is implicit. Filelock'd via `_lib/filelock.FileLock`
     (5s acquire timeout; fail-OPEN on lock contention).
   - Tenant-iso composite key: `sha256(project_path || ":" || user_id || ":" || date)[:32]`.
   - Daily reset via date-keyed state files (implicit atomic rollover via
     key change at UTC midnight; no migration; no race window for
     double-spend). Cross-date consistency within a single operation
     enforced by the `_today_context()` NamedTuple snapshot helper
     (Codex R2 iter-2 P0 #1) — all derived paths/keys (state_path,
     lock_path, tenant_key) come from a SINGLE `_utc_today_iso()` call.
     Atomic check+add enforced by `check_and_record()` under a SINGLE
     FileLock acquisition (Codex R2 iter-2 P0 #2) — eliminates the
     TOCTOU window between `would_breach()` and `record_spend()` in the
     prior split-phase API; production callers MUST use
     `check_and_record()`.
   - Per-class cost-cap matrix (vibecoder/CTO/team × daily/weekly/monthly
     /per-plan/max-parallel) declared as module-level FROZEN dict in cents.
   - HARD CAP = IMMEDIATE STOP single-strike (`would_breach()` returns the
     breached window; caller MUST treat as IMMEDIATE STOP).
   - SOFT CAP = compound condition (>80% daily AND >70% weekly AND >60%
     monthly — AND, not OR — per R1 P1-6 to prevent single-window evasion).

2. **execution_context HMAC tamper-evidence** (`_lib/execution_context.py`):
   - Payload signed via stdlib `hmac.new(key, msg, hashlib.sha256)`.
   - `key` is coordinator-process-owned in-memory bytes (32 bytes via
     `secrets.token_bytes(32)`); NEVER persisted to disk; NEVER inherited
     by child spawns (process isolation).
   - **Key rotation lifecycle** (PLAN-109 amendment): the HMAC key carries
     `key_max_age_seconds: 3600` (1 hour). At or after this age, the coordinator
     MUST auto-rotate the key (new `secrets.token_bytes(32)`) and emit a new
     audit action `execution_context_key_rotated` with payload
     `{previous_key_age_seconds: <int>, rotation_reason: "scheduled" | "compromise_suspected"}`.
     This new action is SPEC-ONLY at PLAN-109 ship (does NOT add to
     `_KNOWN_ACTIONS` in this plan; future implementation plan registers + wires).
   - Replay protection: monotonic nonce + 60s freshness window via
     LRU(1000) replay-seen dict.
   - Constant-time signature comparison via `hmac.compare_digest`.
   - Canonical serialization: `json.dumps(payload, sort_keys=True,
     separators=(",", ":")).encode()` (deterministic; HMAC-stable).

3. **circuit-breaker rules** (`_lib/swarm_circuit_breaker.py`):
   - **Reverse-tripwire**: `swarm_iteration` count >1000/day without Owner-
     physical event in window → auto-disable + emit `swarm_runaway_suspected`.
   - **Weekend-burn detection**: any swarm-loop running >12h without Owner
     Read in audit-log → auto-pause + emit `swarm_paused_owner_absent`;
     requires Owner ack to resume.
   - **Recovery latency SLO**: kill-switch event-to-all-loops-halted ≤60s p99
     across N=20 trials (nearest-rank ceiling formula, NOT interpolated
     quantiles — matches Prometheus/Datadog p99 semantics).

4. **Six-layer kill-switch chain** (staged-capability honesty per
   Codex R2 iter-2 P0 #3 — see §6 below for the L3+L4 enforcement
   deferral; verification-only, NO default flip):
   1. `CEO_SWARM=0` (master kill — current shipped gate at
      `.claude/scripts/swarm/coordinator.py:186`)
   2. `CEO_AUTONOMOUS_LOOPS_DISABLE=1` (shipped secondary kill at
      `swarm/coordinator.py:190`)
   3. GPG enable sentinel (verified at runtime by
      `.claude/hooks/_lib/swarm_enable_gate.py:is_class_enabled`;
      sentinel path `.claude/data/swarm/<class>-enabled.md.asc` with
      detached signature against `.claude/sentinel-signers.txt`
      allowlist; per-class opt-in fail-CLOSED; coordinator
      integration deferred to PLAN-102-FOLLOWUP per ADR-104-AMEND-1
      staged-capability precedent — current ship plants the gate
      module as opt-in capability surface)
   4. Per-class env flag `CEO_SWARM_<CLASS_UPPER>_ENABLED=1` (EXACT
      match per S139 partial-match-non-interference doctrine; both
      `is_class_enabled` AND coordinator integration use exact "1";
      defense in depth after sentinel)
   5. SIGTERM→SIGKILL escalation (30s) via existing
      `.claude/scripts/swarm/kill_switch.py`
   6. cgroups/ulimit + supervisor watchdog + coordinator counter
      (existing PLAN-017 layers)

   **§Part 1 §6 — Staged-capability amendment (Codex R2 iter-2 P0 #3)**:
   Layers 1+2+5+6 are WIRED at runtime via shipped `swarm/coordinator.py`
   + `kill_switch.py` (each independently halts an active loop today).
   Layers 3+4 ship at v1.36.0 as a runtime PRIMITIVE
   (`.claude/hooks/_lib/swarm_enable_gate.py:is_class_enabled`) with
   REAL-behavior test coverage (sentinel detached-sig verify against
   `.claude/sentinel-signers.txt` + per-class env exact-match +
   partial-match non-interference + cross-class isolation). However,
   COORDINATOR-INTEGRATION (wiring the gate at dispatch entry in
   `.claude/scripts/swarm/coordinator.py`) is DEFERRED to
   PLAN-102-FOLLOWUP under the staged-capability precedent established
   by ADR-104-AMEND-1 §B (per-class promotion ceremony pattern). The
   6-layer claim at v1.36.0 is therefore `doctrine-shipped +
   primitive-shipped + enforcement-pending` for L3+L4, not
   `all-6-independently-halt-today`. PLAN-102-FOLLOWUP closes the
   integration gap when an explicit Owner ceremony promotes the L3+L4
   gate from `primitive-shipped` to `enforcement-wired` for the first
   class tier (mirrors S140 ADR-019-AMEND-2-CLASS-SHA_EXISTS pattern).

### Part 2 — NOT directive supersession

ADR-133 explicitly declares: **this is NOT a supersession of Owner directive
2026-04-17 anti-goal #1 ("default DESLIGADO forever").**

The directive remains in force. PLAN-102 ships INFRASTRUCTURE for opt-in
autonomy under Tier C; the default for ALL classes is OFF; Owner enables
per-class via BOTH (a) GPG sentinel AND (b) env flag (defense in depth).

Any future "default-ON" attempt requires a NEW ADR explicitly superseding
ADR-125 §Tier C invariant. That hypothetical ceremony has a higher bar
than ADR-133's own promotion ceremony:

- 5-archetype Wave-D-style R1 debate
- 3-iter Codex R2 ACCEPT
- Owner-physical GPG ceremony
- Plus: explicit prose declaring it supersedes Owner directive 2026-04-17

ADR-133 promotion ceremony covers ONLY the opt-in capability contract; it
does NOT carry directive-supersession authority.

### Part 3 — Audit taxonomy harmonization

PLAN-102 EXTENDS existing `swarm_*` taxonomy (5 new actions total under
the same kernel override):

- `cost_envelope_capped` (Wave A) — HARD CAP IMMEDIATE STOP fire
- `swarm_runaway_suspected` (Wave B reverse-tripwire) — REUSES existing
  `swarm_*` namespace; NOT a parallel `autonomous_loop_runaway_suspected`
- `swarm_paused_owner_absent` (Wave B weekend-burn) — REUSES existing
  namespace
- `execution_context_signed` (Wave B HMAC sign success)
- `execution_context_validation_failed` (Wave B HMAC reject — tamper,
  replay, stale nonce, missing field)

**Emit path**: all 5 actions emit via `emit_generic("<action>",
action="<action>", ...)` with a per-action `_scrub_ceo_boot_event`
dispatch branch enforcing the Sec MF-3 allowlist. **NO typed wrappers
are created** — this matches the `task_route_advised` precedent
(PLAN-101 S141 P1 #3 fold) and keeps `_EXPECTED_PUBLIC_SYMBOLS`
contract-gate byte-identical at v1.36.0 vs v1.35.0.

Plus: `swarm_iteration` schema EXTENDED with optional `cumulative_usd_cents`
field (Sec MF-3 allowlist entry; LLM06 side-channel guarded; cents int
caps precision at $0.01 to avoid float drift + bounds leakage).

Kernel override env: `CEO_KERNEL_OVERRIDE=PLAN-102-WAVE-A-AUDIT-EMIT-EXTENSION`
+ `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` per ADR-116. The single override
covers BOTH Wave A (3 actions) AND Wave B (2 actions) per atomic-ceremony
discipline (S141 PLAN-101 precedent).

## Consequences

### Positive

- **Tier-C capability surface available** — adopters who explicitly need
  autonomous-loop have a documented opt-in path with cost-envelope safety
  rails. Removes the prior "permanent prohibition" framing that made
  Tier-C autonomy unreachable.
- **Defense in depth** — 6-layer kill-switch chain (Layers 1+2+5+6 wired
  at runtime via shipped `swarm/coordinator.py` + `kill_switch.py`;
  Layers 3+4 ship as runtime PRIMITIVE `_lib/swarm_enable_gate.py` with
  REAL-behavior tests, coordinator integration deferred to
  PLAN-102-FOLLOWUP per staged-capability precedent ADR-104-AMEND-1
  and Codex R2 iter-2 P0 #3 fold) + execution_context HMAC
  tamper-evidence + reverse-tripwire + weekend-burn detection +
  recovery-latency SLO ≤60s p99. The 6-layer claim at v1.36.0 is
  `doctrine-shipped + primitive-shipped + enforcement-pending` for
  L3+L4, NOT `all-6-independently-halt-today`.
- **Cost predictability** — per-class cost-cap matrix forces explicit
  budget declaration; no unbounded autonomous spend possible.
- **PLAN-017 anti-goal #1 preserved** — the directive remains the
  authoritative default; ADR-133 adds a capability without overriding it.
- **Audit-emit taxonomy hygiene** — REUSES `swarm_*` family instead of
  inventing parallel `autonomous_loop_*`; SPEC v2.21 stays clean.

### Negative

- **Surface area expansion** — 4 new modules (`cost_envelope`,
  `execution_context`, `swarm_circuit_breaker`) + 2 hooks + 5 new audit
  actions add ~1000 LoC + 76 tests. Each is fail-OPEN on infra errors
  to avoid blocking sessions on bugs, but bug surface is now larger.
- **Operator complexity** — adopters must now reason about 5 distinct
  kill-switch layers; per-class enable requires BOTH sentinel AND env
  flag (intentional defense in depth, but cognitive load).
- **HMAC key lifecycle is coordinator-process-bound** — graceful
  coordinator restart invalidates all in-flight execution_context
  signatures; reconnecting child spawns must re-sign. Documented in
  module docstring + AC12.
- **NOT promotable to Tier B trivially** — locked-in non-promotion
  semantics protect against future drift but limit policy maneuver room.

### Neutral

- **Calendar-gate retraction** — original PLAN-102 external_wait was
  "30d-soak PLAN-096 MCP expansion"; retracted 2026-05-18 per ADR-095
  doctrine + Owner reaffirmation S139
  (`feedback_no_calendar_gates_ai_workflow.md`). Replaced with
  `regression-probe-pass` gate against `.claude/hooks/tests/test_mcp_*.py`.

## Compliance

- **ADR-115 §3** (instrumentation-without-policy-change) — covers the
  hook code shipping default-OFF at v1.36.0 with no behavior change for
  adopters who don't opt-in.
- **ADR-124 §Part 2** (mechanical scope gate) — closed via Wave 0
  PLAN-084 canonical roadmap binding (3 F-A-* IDs bound;
  findings-master.jsonl P0/P1 classification per Codex R2 P1c).
- **ADR-125 §Tier C invariant** — PRESERVED unchanged:
  cross-boundary autonomy + Owner physical consent (GPG sentinel + env
  flag) + cost-envelope manifest + NOT promotable to Tier B trivially.
- **PLAN-017 anti-goal #1** — PRESERVED unchanged (default DESLIGADO
  forever; ADR-133 is opt-in capability, NOT supersession).
- **Owner directive 2026-04-17** — PRESERVED unchanged.

## Codex MCP gate trail

S142 ceremony bundle review — Codex R2 5-iter ACCEPT (gpt-5.2).

`Codex R2 thread`: `019e3d1d-e0e5-7ff1-9020-96de51d1c7f3`
`iters_count`: 5
`verdict_summary`: iter-1 BLOCK (5 P0 + 2 P1 + 1 P2 — record_spend
missing, typed-wrapper mismatch, tenant-iso key mismatch, hook not
wired in settings.json, per-class enable runtime not implemented,
swarm-dispatch false-positive, phantom audit actions, calendar-gate
language in §8) → iter-2 ACCEPT-WITH-FIXES (3 P0 + 2 P2 — TOCTOU on
`_utc_today_iso()`, HARD CAP not atomic under concurrency, claims
drift after iter-1 folds, timeout snippet drift, `is_class_enabled`
ReDoS-safe confirmed informational) → iter-3 ACCEPT-WITH-FIXES (1 P0
+ 1 P2 — residual doc drift in canonical artifacts, AC5 dense-but-
acceptable splitting deferred) → iter-4 ACCEPT-WITH-FIXES (1 P0 +
1 P1 + 1 P2 — signed PLAN-084 evolution-roadmap stale cost-envelope
mechanics, ADR-133 gate trail placeholders, test docstring stale) →
iter-5 ACCEPT (no remaining Tier-C pre-ceremony blockers; only
self-correcting cosmetic header iter-count nit, fixed in same pass).
All folds applied in-session.

`patches_applied_at_ceremony`:
  - iter-1 P0 #1 — `check_cost_envelope.py:main` calls
    `env.record_spend(estimated_cents, plan_id)` on allow path
  - iter-1 P0 #2 — hook uses `audit_emit.emit_generic("cost_envelope_capped", ...)`
    + Sec MF-3 scrub gate (no typed wrapper); patcher Section 3
    rewritten to "0 typed wrappers"
  - iter-1 P0 #3 — date-keyed state file model
    `cost-envelope-<sha256[:32]>.json` with implicit cross-date
    isolation; removed dead `_composite_dated_key()` helper
  - iter-1 P0 #4 — `apply-patches.py` P_SETTINGS patch wires
    `check_cost_envelope.py` PreToolUse Bash hook in
    `.claude/settings.json` (idempotent JSON parse + append)
  - iter-1 P0 #5 — NEW `_lib/swarm_enable_gate.py` runtime gate
    primitive (Layer 3 GPG sentinel + Layer 4 env flag EXACT-match);
    coordinator integration deferred to PLAN-102-FOLLOWUP per
    ADR-104-AMEND-1 staged-capability precedent
  - iter-1 P1 #1 — `_looks_like_swarm_dispatch()` requires BOTH
    `CEO_SWARM=="1"` AND real swarm-coordinator command substring
    (eliminates false-positive)
  - iter-1 P1 #2 — `_OWNER_READ_ACTIONS = frozenset({"session_start"})`
    real action; reverse-tripwire + weekend-burn use real proxy
  - iter-1 P2 #1 — PLAN-102 §8 calendar-gate language replaced with
    regression-probe-pass per ADR-095 doctrine
  - iter-2 P0 #1 — `_TodayContext` NamedTuple + `_today_context()`
    helper; threaded `ctx` through all operations (one-shot
    `_utc_today_iso()` consumption)
  - iter-2 P0 #2 — `check_and_record()` atomic single-lock API;
    hook refactored to single call; split-phase eliminated
  - iter-2 P0 #3 — PLAN-102 AC5/AC6/AC13 + ADR-133 §Part 1 §1 +
    §Defense in depth + §Part 1 §6 amendment + approved.md items
    6+7+14+178 rewritten for staged-capability honesty
  - iter-2 P2 #1 — timeout snippet drift aligned to 5s
  - iter-3 P0 #1 — PLAN-102 §A.1/A.2/A.4 + §6 + §6b + ADR-133
    §Part 1 §1 + approved.md item 8 rewritten with iter-3 reality
    wording (date-keyed state file, `_today_context()`,
    `check_and_record()`, no `CEO_SWARM_*_USD` env knobs)
  - iter-4 P0 — PLAN-084 evolution-roadmap.md F-A-COST-ENVELOPE-HOOK-0002
    capability prose rewritten with iter-3 reality (date-keyed
    state file + `_today_context()` + `check_and_record()`)
  - iter-4 P1 — this gate trail populated in-session (was `<TBD>`
    placeholders); removed false "Phase A2 emits" claim
  - iter-4 P2 — `wave-a-test-cost-envelope.py:9` docstring stale
    "atomic CAS midnight rollover" wording aligned to date-keyed
    state file model

## Promotion to ACCEPTED

This ADR is PROPOSED at v1.36.0 ship. Promotion to ACCEPTED is a
SEPARATE post-ship Owner ceremony with:

1. R1 5-archetype debate (security-engineer + identity-trust-architect
   + qa-architect + performance-engineer + llm-finops-architect focus).
2. R2 Codex 3-iter ACCEPT on the full ADR text + ceremony bundle.
3. Owner-physical GPG ceremony for the promotion sentinel at
   `.claude/plans/PLAN-102/architect/round-1/approved-promotion.md.asc`
   (separate from the v1.36.0 ship sentinel — promotion is a distinct
   governance action per S133 ADR-132 + S140 ADR-019-AMEND-1 precedent).
4. ADR-133 frontmatter flips `status: PROPOSED → ACCEPTED` +
   `accepted_at: <YYYY-MM-DD>` + §Codex MCP gate trail populated.

The capability ships v1.36.0 with ADR-133 in PROPOSED state; the
autonomous-loop opt-in mechanism is governed by this doctrine from
day one regardless of promotion state (no behavior gate on `ACCEPTED`
flip).

<!-- PLAN-102-FOLLOWUP layer-3-4-stamp -->
Layer 3+4 enforcement wired at PLAN-102-FOLLOWUP ship v1.38.2 at `LoopRunner.step()` entry (`loop_runner.py:74`) as defense-in-depth. The `is_class_enabled` primitive runs at every iteration step before the iterate callable is invoked; gate-block emits `swarm_layer_3_4_blocked` (NEW action, SPEC v2.23). Coordinator-level wiring at `coordinator.main()` is deferred to PLAN-102-FOLLOWUP-NEXT once worktree orchestration ships (today `coordinator.main` is `refused: scaffold_only`).
