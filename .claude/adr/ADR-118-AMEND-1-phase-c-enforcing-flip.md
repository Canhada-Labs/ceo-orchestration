---
id: ADR-118-AMEND-1
title: Phase C — flip 4-persona AUTO defaults from advisory to enforcing
status: ACCEPTED
proposed_at: 2026-05-13
proposed_by: CEO (PLAN-090 Wave A — R1 6-archetype + R2 Codex MCP iter-3 ACCEPT 2026-05-13)
accepted_at: 2026-05-13
accepted_by: Owner @Canhada-Labs (0000000000000000000000000000000000000000) — PLAN-090 closeout ceremony S118 (v1.24.0)
parent_adr: ADR-118
amends: [ADR-118]
related_plans: [PLAN-088, PLAN-090, PLAN-091, PLAN-100]
related_adrs: [ADR-040, ADR-042, ADR-052, ADR-064, ADR-115, ADR-117, ADR-118, ADR-122, ADR-123, ADR-124, ADR-125]
veto_floor: ADR-052 (security-engineer + threat-detection-engineer + code-reviewer + qa-architect + performance-engineer + identity-trust-architect)
codex_pair_rail: required (PLAN-090 R2 Codex MCP iter-3 ACCEPT 2026-05-13 thread 019e212f-f85f-7fd2-a73a-29713ea9cc1f)
tags: [governance, capability-rollout, enforcing-flip, phase-c, god-mode, post-sota-maintenance]
authorization: PLAN-090 closeout ceremony (`OWNER-CEREMONY-PLAN-090-CLOSEOUT.sh`)
naming_precedent: ADR-040-AMEND-2 (S109) + ADR-116-AMEND-1 (PLAN-089)
---

# ADR-118-AMEND-1 — Phase C: advisory → enforcing flip for AUTO primitives

## §1. Context

ADR-118 (ACCEPTED 2026-05-13, PLAN-088 closeout) declared the framework
`god-mode AUTO-USABLE` with `capability_surface_delta=0` across 13
canonical conversions (AUTO-01..AUTO-10 + SEMI-11/12/13). PLAN-088
shipped the INFRASTRUCTURE for auto-activation: typed `emit_*` wrappers,
ATLAS bindings, 52-cell coverage harness.

PLAN-091 (v1.22.1, 2026-05-13) shipped the production CALLSITE wires:
16th Tier-S `tier_policy_misrouting_24h` check, `/effort` thinking
budget auto-inject in the live adapter, `mcp_routing` and
`specialization_promoted` spawn-hook wires, and `AC15.5
EXPECTED_CALLSITES` structural test. **Every AUTO primitive now has at
least one production callsite invoking the matching `emit_*` wrapper.**

What PLAN-088+PLAN-091 did NOT do: flip the DEFAULTS from `advisory`
(observe + emit audit, no behavior change) to `enforcing` (block
deviation, require explicit opt-out). That flip is Phase C of the
PLAN-088 god-mode trajectory and the subject of this amendment.

This ADR amends ADR-118 §3 (`Behaviour contract`) — it does NOT
supersede ADR-118 §2 (`capability_surface_delta=0` evidence) or §4
(`SHA-pin verifier`).

## §2. Decision

Effective at the `v1.24.0` tag (PLAN-090 closeout):

| Primitive class | Pre-AMEND-1 default | Post-AMEND-1 default | Rationale |
|---|---|---|---|
| `AUTO-01` ... `AUTO-10` | advisory (observe + emit) | **enforcing** (block deviation; opt-out via env) | 10 primitives have ≥1 wired callsite per `EXPECTED_CALLSITES`; advisory phase has surfaced 0 false-positive escalations since `v1.22.0` |
| `SEMI-11` ... `SEMI-13` | advisory | **advisory** (unchanged) | SEMI = user-confirm class; flipping would invert the "semi-automatic" contract |

Behaviour-change scope:

- A spawn-hook decision that contradicts an AUTO recommendation
  (e.g., dispatcher attempts model `claude-opus-4-7` for a task the
  router classified as `claude-haiku-4-5`) is REJECTED with a
  block decision and an `audit emit` of `persona_auto_decision_emitted`.
- The corresponding non-AUTO path is taken silently (no Owner prompt)
  unless `CEO_GODMODE_ENFORCING=0` is set in the parent shell.

> **§2.4 STATUS CORRECTION (PLAN-120 / S185, finding E2-F1) — the
> `AUTO-05` persona-routing / model-tier `block` decision above was
> NEVER implemented and is DEFERRED to a future `ADR-118-AMEND-2`.**
> The decision table (`AUTO-01..AUTO-10 -> enforcing (block deviation)`)
> and the §2 behaviour-change scope ("REJECTED with a block decision")
> describe the *intended* Phase-C contract. For the model-tier case the
> wired consult is **TELEMETRY-ONLY**: `check_agent_spawn.py`
> (`_consult_model_routing_mode`, the "W3 — DEFERRED BLOCK + FLIP
> DOCTRINE" comment block) consults all three `persona_routing` APIs and
> emits **`model_routing_enforced`** with `decision ∈ {enforce_telemetry,
> advisory, eval_error}` — there is **NO `block` value** and
> `persona_auto_decision_emitted` is not on this path. The block is
> deferred *by construction*: the PreToolUse Agent hook payload exposes
> only `description/prompt/subagent_type/run_in_background`
> (`SPEC/v1/hook-io.schema.md`) and carries no spawn-*requested* model to
> compare against authoritative frontmatter, so "a block would be
> theater". Lifecycle/enforcement classification of AUTO-05 persona
> routing = **ACTIVE-DEFAULT-OFF × TELEMETRY-ONLY**. Do NOT cite this ADR
> as evidence that persona/model-tier routing blocks at spawn time. The
> future flip is governed by observed-violation volume + a
> false-positive-rate threshold (ADR-095), NOT calendar days, and lands
> with `ADR-118-AMEND-2`. (Other AUTO primitives with a real wired
> block predicate are unaffected by this correction.)

## §3. Opt-out — `CEO_GODMODE_ENFORCING=0` kill-switch

**Truthiness footgun discipline** (R1 security-engineer P0 fold +
PLAN-090 §4 A.2 §3 inline):

The kill-switch fires **ONLY on EXACT MATCH** `CEO_GODMODE_ENFORCING=0`.

| Env value | Effect |
|---|---|
| `CEO_GODMODE_ENFORCING=0` | kill-switch ARMED — fall back to ADVISORY |
| `CEO_GODMODE_ENFORCING=false` | ignored — ENFORCING stays active |
| `CEO_GODMODE_ENFORCING=no` | ignored — ENFORCING stays active |
| `CEO_GODMODE_ENFORCING=FALSE` | ignored — ENFORCING stays active |
| `CEO_GODMODE_ENFORCING=""` | ignored — ENFORCING stays active |
| `CEO_GODMODE_ENFORCING=` | ignored — ENFORCING stays active |
| unset | ENFORCING stays active |
| `CEO_GODMODE_ENFORCING=1` | ignored — ENFORCING stays active |

Acceptance via `parent-shell only` (S110 pattern):
- never accepted via stdin or tool-param
- sub-agent prompts cannot activate the kill-switch via a Bash hook
- documented in
  `.claude/hooks/tests/test_kill_switch_godmode_enforcing.py` with an
  explicit truthiness matrix.

Every kill-switch trigger emits a `kill_switch_invoked` audit event
(FPR rate-budget tracking — if Owner invokes >X/week, ENFORCING is
effectively disabled and Wave D verification surfaces the drift).

## §4. Migration — one-time `phase_c_advisory` audit event

On the FIRST session after `v1.24.0` install (i.e., the first
`SessionStart` hook firing with `state/phase_c_seen.marker` absent):

1. Emit `phase_c_enforcing_flipped` with `migration_phase=first_session`
   (one-shot per session; idempotent on second session via
   marker-file existence check; pre-flip emit — crash mid-flip
   preserves the audit trail).
2. Write the marker `$HOME/.claude/projects/<project>/state/phase_c_seen.marker`
   with mtime = first-flip timestamp.
3. Print to stderr (advisory banner, never blocks):
   ```
   [INFO] Phase C enforcing enabled — see ADR-118-AMEND-1 for opt-out.
   ```

No CHANGELOG-only-migration is required — the version bump from
`v1.22.x` to `v1.24.0` is itself sufficient signal.

## §5. Verification

| Check | Mechanical |
|---|---|
| 52-cell persona × primitive matrix test | `pytest test_persona_routing_enforcing.py` GREEN |
| Kill-switch truthiness matrix | `pytest test_kill_switch_godmode_enforcing.py` GREEN |
| Idempotent phase-C emit | `pytest test_phase_c_advisory_audit.py` GREEN |
| `phase_c_enforcing_flipped` registered | grep `phase_c_enforcing_flipped` in `.claude/hooks/_lib/audit_emit.py` |
| `persona_auto_decision_emitted` registered + rate-capped | grep `persona_auto_decision_emitted` in `.claude/hooks/_lib/audit_emit.py` + token-bucket test PASS |
| `kill_switch_invoked` registered | grep `kill_switch_invoked` in `.claude/hooks/_lib/audit_emit.py` |
| `persona_auto_rate_capped` summary emit | grep `persona_auto_rate_capped` in `.claude/hooks/_lib/audit_emit.py` |
| Spawn-hook perf within budget | `ratio_p95 ≤ 1.05` AND `ratio_p99 ≤ 1.10` AND `ratio_max ≤ 1.20` |

## §6. PLAN-090 AMENDMENT-1 — confidence-gate empirical baseline

This AMEND-1 cites
`.claude/plans/PLAN-090/wave-a10-confidence-baseline.md` as the
upstream measurement source for any future PLAN-100 promotion of
`check_confidence_gate.py` from advisory to per-class BLOCK_MODE.
PLAN-100 will consume the baseline-report to decide per-class FPR
thresholds; until then, `check_confidence_gate.py` retains its
existing ADVISORY-only invariant.

## §7. Sunset trigger

This AMEND-1 is automatically subsumed when ADR-118 itself is
superseded by ADR-130+ (RESERVED per ADR-126 §Part 7 — first sidecar
plan or 30-day deferral) or when v2.0 lands (per ADR-124 §Part 3
mechanical sunset).

If Owner invokes `CEO_GODMODE_ENFORCING=0` more than 5 times per week
across 2 consecutive weeks, ENFORCING is treated as effectively
disabled and Wave D verification emits a `phase_c_killswitch_overuse`
advisory in `/ceo-boot`.

## §8. Risks + mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Wire-gap masking — missing PLAN-091 callsite amplifies into false negative | HIGH | `external_wait: PLAN-091-callsite-wires-shipped` blocks Wave A; AC15.5 `EXPECTED_CALLSITES` PASS on origin/main confirmed (commit `c0608e9` / tag `v1.22.1`) |
| Adopter surprise — default behavior change without re-install | MED | one-shot `phase_c_advisory` advisory banner + ADR-118-AMEND-1 §4 migration doc + kill-switch |
| Kill-switch leaks via prompt-injection | HIGH | parent-shell env only (S110 pattern); never accepted via stdin or tool-param |
| Per-decision audit event volume floods audit-log | MED | token-bucket rate-cap: 10 burst + 5/min sustained per persona; aggregate ceiling 20/min |
| Bootstrap paradox — A.5 test run fires ENFORCING and blocks ceremony commit | MED | A.3b is LAST sub-wave (§9 ordering invariant) + ceremony commit runs with `CEO_GODMODE_ENFORCING=0` (S110 pattern) |

## §9. Cost

- Implementation: ~150 LoC `_lib/persona_routing.py` + ~80 LoC audit
  emit additions + ~250 LoC test files = ~480 LoC net-new.
- Test suite: 52-cell matrix + 8-row truthiness matrix + idempotency
  test = ~70 NEW tests.
- Sub-agent dispatches: 0 (CEO solo via `general-purpose` mitigated
  rail; no persona-archetype review needed since R1 6-archetype
  completed S114-post 2026-05-13).
- Owner-physical: 1 GPG (sentinel `.asc` on policy-flip commit) +
  closeout tag.
