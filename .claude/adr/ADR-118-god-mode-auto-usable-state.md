---
id: ADR-118
title: Framework reaches god-mode AUTO-USABLE state on PLAN-088 close — capability_surface_delta=0 by mechanical SHA-pin
status: ACCEPTED
proposed_at: 2026-05-12
proposed_by: CEO (PLAN-088 Wave 4.3 — R1 5-archetype + R2 Codex MCP iter-4 ACCEPT 2026-05-12)
accepted_at: 2026-05-13
accepted_by: Owner (PLAN-088 closeout ceremony v1.22.0 S114-cont 2026-05-13)
related_plans: [PLAN-051, PLAN-058, PLAN-084, PLAN-085, PLAN-086, PLAN-087, PLAN-088]
related_adrs: [ADR-040, ADR-042, ADR-051, ADR-052, ADR-064, ADR-081, ADR-090, ADR-107, ADR-108, ADR-115, ADR-116]
amends: [ADR-115]
supersedes: []
veto_floor: ADR-052 (security-engineer + threat-detection-engineer + code-reviewer + qa-architect + performance-engineer)
codex_pair_rail: required (W4.3 SHA-pin Rationale verifier is the mechanical evidence surface)
tags: [governance, capability-gap, auto-activation, ac10-closure, god-mode, post-sota-maintenance, sha-pin-evidence]
authorization: PLAN-088 closeout ceremony (`OWNER-CEREMONY-PLAN-088-CLOSEOUT.sh`)
verifier: .claude/scripts/verify-adr-118-rationale.py
note: |
  PROPOSED at PLAN-088 W4.3 authoring (this commit). Flips to ACCEPTED
  at PLAN-088 closeout ceremony, gated by: (a) Codex MCP R2 ACCEPT;
  (b) `verify-adr-118-rationale.py` exit 0 against this file;
  (c) `verify-persona-coverage.py` reports thresholds met for all 4
  personas (vibecoder >=12/13, others >=11/13); (d) Owner GPG sentinel
  on closeout commit.
---

# ADR-118 — Framework reaches god-mode AUTO-USABLE state on PLAN-088 close

## §1. Context

PLAN-084 (SOTA-finalization audit, shipped `v1.18.0`, ADR-113/114/115
ACCEPTED) **falsified the "god-mode Claude+Codex" thesis at the
auto-activation layer**, while leaving the underlying capability
inventory **intact**. The five capability ACs that failed are:

| AC | Verdict | Falsification mechanism |
|---|---|---|
| AC10 auto-activation (4 personas × 13 axes = 52 cells) | FAIL ALL | vibecoder 53.85% / junior 30.77% / CTO 61.54% / team 30.77% |
| AC11a time-to-first-value | FAIL ALL | vibecoder ≤5min FAILS empirically (wizard not auto-spawned) |
| AC11b token efficiency 2/3 | FAIL | tier-policy 82% empty `model_recommended` → 55% mis-routing |
| AC11c multi-model routing | FAIL | 51% overall mis-route / 67% volume-weighted |
| AC12 estimation accuracy 2/4 | FAIL | AC12c data-driven pipeline absent; AC12d phase-refinement unregistered |

These failures are **not capability gaps** — they are **activation
gaps**: every primitive required to satisfy AC10/AC11a/AC11b/AC11c/AC12
is already shipped in the codebase. The failure mode is that each
primitive requires the user to know the right command, archetype name,
or env-var. Personas without that command-surface fluency (vibecoder /
junior / team member) cannot extract value from capability they
technically have.

PLAN-088 closes those activation gaps via **13 priority conversions**
(10 AUTO + 3 SEMI) sourced from
`.claude/plans/PLAN-084/automation-gap-roadmap.yaml`:

- 10 AUTO conversions: AUTO-01 through AUTO-10
- 3 SEMI conversions: SEMI-11 / SEMI-12 / SEMI-13

The closure target is **AUTO+SEMI ≥85% across all 4 personas, with
vibecoder ≥90%** (per AC1 in PLAN-088 §10):

| Persona | Pre-PLAN-088 | Target | Mechanism |
|---|---|---|---|
| vibecoder | 7/13 = 53.85% | ≥12/13 = ≥92.3% | AUTO-01..10 + SEMI-11/13 |
| junior_dev | 4/13 = 30.77% | ≥11/13 = ≥84.6% | AUTO-* across critical axes |
| skeptical_cto | 8/13 = 61.54% | ≥11/13 = ≥84.6% | AUTO-* + opt-out clarity |
| team_member | 4/13 = 30.77% | ≥11/13 = ≥84.6% | AUTO-* + advisory SEMI |

This ADR is **PROPOSED at PLAN-088 W4.3 authoring time** and **flips to
ACCEPTED at PLAN-088 closeout** once the verifier asserts the SHA-pin
Rationale table proves `capability_surface_delta=0` for every
conversion.

## §2. Decision

### §2.1 Declaration

Upon PLAN-088 closeout commit landing (gated by ceremony script
`OWNER-CEREMONY-PLAN-088-CLOSEOUT.sh`), the framework formally
declares the **god-mode AUTO-USABLE state**.

**Definition (god-mode AUTO-USABLE state):** the framework satisfies
all of:

1. **Per-persona AUTO+SEMI threshold** — vibecoder ≥12/13 (≥92.3%);
   junior_dev / skeptical_cto / team_member each ≥11/13 (≥84.6%),
   measured by `.claude/scripts/verify-persona-coverage.py` against the
   52-cell scenario suite `tests/fixtures/persona-scenario-suite.yaml`.
2. **AC10/AC11a/AC11b/AC11c/AC12 closure** — each capability AC from
   PLAN-084 §AC table moves from FAIL to PASS, mechanically verified by
   the per-AC scripts enumerated in PLAN-088 §10 closeout criteria.
3. **Opt-out preserved on every conversion** — every AUTO/SEMI ships
   with at least one kill-switch (per-conversion env-var; SEMI-13 is
   the documented graceful-degradation exception where opt-out would
   violate the failure-mode telemetry invariant).
4. **capability_surface_delta = 0** — proven mechanically by
   `verify-adr-118-rationale.py` against the §3 Rationale table
   below. No primitive is introduced; every conversion wires an
   existing primitive (shipped at an earlier commit-SHA) to a
   trigger signal.

If any one of the four conditions fails at closeout, this ADR remains
PROPOSED and PLAN-088 cannot transition `executing → done`.

### §2.2 Scope amendment to ADR-115 (maintenance-mode posture)

This ADR **amends ADR-115 §scope-amendment** by adding an explicit
in-scope category for "wiring activation of shipped capability"
(see §4 below). ADR-115 is **not re-debated**; it is **mechanically
respected** via the §3 SHA-pin Rationale table.

## §3. Rationale — MECHANICAL SHA-PIN TABLE (LOAD-BEARING)

> **This table is the load-bearing evidence surface** that proves
> `capability_surface_delta=0` for every conversion in the canonical
> 13 (10 AUTO + 3 SEMI). It is consumed by
> `.claude/scripts/verify-adr-118-rationale.py` per
> PLAN-088 W4.3 / M-27 / Sec-7 / handoff §9.4. Schema:
>
> - **Conversion** — canonical ID from `automation-gap-roadmap.yaml`
>   (`AUTO-01..AUTO-10` or `SEMI-11/12/13`); exactly 13 rows.
> - **Capability primitive** — the already-shipped primitive whose
>   activation surface PLAN-088 wires; described by file path or
>   skill/SDK name.
> - **First-shipped SHA** — git commit SHA (40 hex) when the
>   primitive first landed in the framework; if the primitive
>   pre-dates the PLAN-084 audit baseline and no atomic
>   "first-shipped" SHA can be cleanly attributed (because the
>   primitive evolved across many commits before becoming the
>   activation surface PLAN-088 wires), the marker
>   `ANCESTRAL-PRE-PLAN-084` is used. The verifier accepts both
>   the 40-hex form and the `ANCESTRAL-PRE-PLAN-084` marker.
> - **Trigger-wire LoC** — line-count of the NEW wiring code added
>   in PLAN-088 (this is the only net-new code surface for that
>   conversion); estimated per PLAN-088 §4 wave specs.
> - **Surface delta** — MUST equal `0` for every row; this is the
>   load-bearing claim of the ADR. If any conversion introduces a
>   primitive not already shipped (rather than wiring an existing
>   one), the row's surface_delta becomes 1, the verifier FAILS,
>   and ADR-118 cannot reach ACCEPTED.

| Conversion | Capability primitive | First-shipped SHA | Trigger-wire LoC | Surface delta |
|---|---|---|---|---|
| AUTO-01 | B.1 prompt caching — `cache_control` markers + Tier-A `check_tier_a_cache_hit_rate_24h.py` (advisory) — 98% empirical hit rate at PLAN-084 audit | ANCESTRAL-PRE-PLAN-084 | 40 | 0 |
| AUTO-02 | B.10 first-run-wizard primitive — `.claude/scripts/first-run-wizard.py` (PLAN-083 Wave 2) | aae27f1 | 60 | 0 |
| AUTO-03 | B.14 estimation infrastructure — `architect` skill + `estimate_refined` audit-emit register (PLAN-084 Wave 0.5) + calibration-baseline.yaml fixture surface | b15d68f | 150 | 0 |
| AUTO-04 | B.11 token efficiency — tier-policy advisor history in audit-log + ceo_boot Tier-A check infrastructure | ANCESTRAL-PRE-PLAN-084 | 120 | 0 |
| AUTO-05 | B.12 multi-model routing — `_ADR_052_ROLE_TO_MODEL` row table + PLAN-086 Wave B row-extension dependency | d76bb6b | 250 | 0 |
| AUTO-06 | B.6 MCP servers — connected MCP server set (Sentry / Stripe / Vercel / Supabase / Cloudflare / Gmail / Drive / Calendar / Ahrefs / Similarweb / LunarCrush / claude-in-chrome); contracts per ADR-042 | ANCESTRAL-PRE-PLAN-084 | 300 | 0 |
| AUTO-07 | B.4 Codex MCP surface — `.claude/hooks/check_pair_rail.py` + Pair-Rail Case A-F infrastructure (PLAN-081 Phase 3 / ADR-107/108) | 0747829 | 180 | 0 |
| AUTO-08 | B.5 batch / streaming / vision — Anthropic Message Batches API contract (external SDK surface; framework consumes via `_lib/adapters/live/claude.py`) | 205a73e | 250 | 0 |
| AUTO-09 | B.2 extended thinking — `thinking` kwarg infrastructure in `_lib/adapters/live/claude.py` (kwarg shape lands in PLAN-086 Wave A; W2.3 wires task-class dispatch on top) | 3514fbe | 80 | 0 |
| AUTO-10 | B.3 sub-agent dispatch — `check_agent_spawn.py` + `.claude/team.md` ROUTING TABLE | c1c426e | 90 | 0 |
| SEMI-11 | B.7 cookbook — Anthropic Cookbook 2026 reference set (external doc surface; PLAN-084 B.7 reviewed 2/9 ADOPTED, 4 PARTIAL, 2 DEFERRED, 1 N/A) | ANCESTRAL-PRE-PLAN-084 | 120 | 0 |
| SEMI-12 | B.8 SOTA research — Reflexion + ReAct (ADOPTED per PLAN-084 B.8); CoVe + Self-Consistency DEFERRED to PLAN-092 stub-row (PLAN-088 ships zero deferral spec content per M-26) | a8b4629 | 0 | 0 |
| SEMI-13 | B.13 graceful degradation — `audit_emit.py` register infrastructure (PLAN-004 Phase 1) + adapter exception envelopes (ANCESTRAL); 4 emit-action gaps closed by wire-only patches | a8b4629 | 80 | 0 |

**Total trigger-wire LoC across all 13 rows: ~1,720 LoC** (sum of
column 4; this is the gross NEW LoC PLAN-088 ships across W1-W4 to
wire existing capability to trigger signals — distinct from the
capability primitives themselves, which carry zero net-new LoC in
PLAN-088).

**Surface-delta sum: 0** (all 13 rows). This is the load-bearing
mechanical claim verified by `verify-adr-118-rationale.py`.

### §3.1 Anti-rationalization clause

If a reviewer reads §3 and observes a row where the "First-shipped
SHA" appears to refer to a commit that itself introduced significant
surface (not just the activation hook), the reviewer MUST flag the
row as a candidate `surface_delta=1` row. The verifier accepts the
SHA's plain text presence but **does not deeply audit the SHA's diff**;
that audit is the human reviewer's responsibility during PLAN-088
closeout debate, captured in the Codex MCP R2 thread of record.

### §3.2 Why `ANCESTRAL-PRE-PLAN-084` is acceptable as a SHA-pin

Five of the 13 rows mark `ANCESTRAL-PRE-PLAN-084` rather than a
40-hex commit SHA. The rationale:

- **AUTO-01 (prompt caching)** — the `cache_control` adoption +
  Tier-A cache-hit-rate observatory evolved across PLAN-073 /
  PLAN-083 / PLAN-086 with no atomic "this commit ships prompt
  caching" event. The PLAN-084 audit measured a stable 98% empirical
  hit rate, certifying that the primitive was in steady state at
  audit time.
- **AUTO-04 (tier-policy advisor)** — tier-policy advisory output
  exists in the audit-log surface (otherwise PLAN-084 could not
  have measured the 82% empty `model_recommended` rate); the
  primitive is a logging contract, not a single-file artifact.
- **AUTO-06 (MCP servers)** — the 12 MCP server connections were
  provisioned operationally outside the framework code (per
  ADR-042 contract); the framework consumes them via prose +
  fixture lookups.
- **SEMI-11 (Cookbook)** — Anthropic Cookbook references are an
  external doc surface; the framework consumes them via prose +
  fixture lookups.
- **SEMI-12 (SOTA research)** — the adopted Reflexion + ReAct
  primitives pre-date PLAN-084 (Reflexion landed at PLAN-006
  Phase 4); SEMI-12 ships zero deferral spec content in PLAN-088
  (per M-26 — deferred to PLAN-092). The `ANCESTRAL` marker here
  is the strongest evidence that PLAN-088 introduces nothing for SEMI-12.

All five `ANCESTRAL` rows have `capability_surface_delta=0` because
they map activation wiring onto primitives that were already
present at PLAN-084 audit time. The verifier explicitly accepts
the marker `ANCESTRAL-PRE-PLAN-084` as equivalent to a 40-hex SHA
for the purpose of the `capability_surface_delta=0` proof.

## §4. Scope amendment to ADR-115

ADR-115 §Decision (post-SOTA maintenance-mode) enumerated three
in-scope categories: bug fixes, roadmap items already debated, and
adopter-blocking install bugs. PLAN-088 adds a fourth via this ADR:

> **In-scope category #4 (ADR-118 amendment): wiring activation of
> already-shipped capability primitives.** A plan is permitted under
> maintenance-mode if every load-bearing change in the plan maps
> via SHA-pin to a capability primitive that was already present in
> the codebase at the PLAN-084 audit baseline, AND the SHA-pin
> Rationale table proves `capability_surface_delta=0` for every
> conversion.

The amendment is **narrowly scoped to PLAN-088 + future plans that
explicitly cite this ADR as authority**. PLAN-089 / PLAN-090 /
PLAN-091 / PLAN-092 do not inherit this scope category by default;
each such future plan must declare an in-scope match to this
category and ship its own ADR-118-equivalent SHA-pin Rationale if it
wishes to claim the same maintenance-mode posture.

## §5. Consequences

### §5.1 What changes upon ACCEPTED

- 13 new trigger-signal → dispatch wiring paths land in the codebase
  (PLAN-088 W1-W4 LoC, ~1,720 total).
- 13 audit-emit actions in the canonical-13 enter the registry
  (`cache_discipline_alerted` + `first_run_wizard_dispatched` +
  `estimate_calibrator_pipeline_run` + `subagent_findings_partial_drop`
  + `anthropic_429_observed` + `git_index_lock_retry` +
  `codex_invoke_dispatched` + `tier_policy_misrouting_advised` +
  `model_routing_advised` + `mcp_route_advised` +
  `cookbook_pattern_advised` + `pair_rail_phase_advanced` +
  `batch_dispatched`); each one carries ATLAS technique-ID metadata
  per PLAN-088 §1.5 canonical-13 enumeration.
- `KNOWN_ACTIONS` floor advances `BASELINE_PRE_PLAN_088 + 11` per
  reconciliation (2 of 13 already registered pre-PLAN-088:
  `model_routing_advised` from PLAN-078, `mcp_route_advised` from
  PLAN-086 Wave D).
- Vibecoder, junior, CTO, and team-member personas reach AUTO+SEMI
  thresholds per §2.1 above.
- AC10 / AC11a / AC11b / AC11c / AC12 close in PLAN-084 evolution
  ledger.

### §5.2 What does NOT change

- **Capability primitives themselves are unchanged.** Per §3 + §3.1,
  `capability_surface_delta=0` for every conversion. The framework
  ships no further entries beyond what already lives in
  `_lib/adapters/live/claude.py` or `_lib/adapters/live/codex.py`.
- **ADR-115 maintenance-mode posture is preserved.** The only
  amendment is the addition of in-scope category #4 (§4 above),
  which is itself narrowly scoped to this plan.
- **Kill-switches preserved per Sec-3 / M-12 invariants.** Every
  AUTO/SEMI conversion ships with at least one per-conversion
  env-var opt-out (SEMI-13 graceful-degradation telemetry is the
  documented exception, where opt-out would violate the failure-mode
  invariant).
- **No further surface for AC10 closure.** Vibecoder default posture
  (Phase C ACTIVE rollout) is DEFERRED-TO-PLAN-090 per R2 iter-1 C5
  fold; PLAN-088 ships SHADOW + DRY_RUN only.

### §5.3 Detection-decay monitor (per ADR-115 §Detection-decay)

Post-PLAN-088 closeout, the following emit actions are expected to
fire non-zero in the audit-log within 30 days of merge:

- `cache_discipline_alerted` — fires when SessionStart Tier-S cache
  check observes hit-rate below 0.7 floor; non-zero rate expected
  (existing capability already empirically at 98%, so most sessions
  pass — alerted state is for outliers).
- `first_run_wizard_dispatched` — expected to fire once per
  fresh install only.
- `model_routing_advised` — expected to fire on most agent_spawn
  events (typical multi-session rate >100/day).
- `mcp_route_advised` — expected to fire on MCP-eligible task
  classes.
- `pair_rail_phase_advanced` — fires on phase transition; expected
  to be sparse but non-zero in 30-day window.

If any of the above show **zero events 30 days post-merge**, the
detection-decay monitor flags the wiring as broken — trigger
PLAN-NNN investigation per ADR-115 Detection-decay clause.

### §5.4 What MUST be re-evaluated at v2.0 trigger

- Phase C ACTIVE rollout (per-persona default flip semantics) is
  PLAN-090 scope; the god-mode AUTO-USABLE declaration here is
  per-persona-default-OFF for the AUTO-* conversions (except those
  where SHADOW/DRY_RUN matches the user's expectation).
- SEMI-12 SOTA research deferral (CoVe + Self-Consistency) is
  PLAN-092 / v2.0-candidate; declaring god-mode now does not mark
  SEMI-12 as closed (the row is PRESENT in the §3 table only as
  evidence of `capability_surface_delta=0` for the Reflexion + ReAct
  primitives already adopted, not as a closure of the CoVe gap).

## §6. Related

- **PLAN-088** — Capability auto-activation — god-mode unlock; this
  ADR is authored by PLAN-088 W4.3.
- **PLAN-084** — SOTA-finalization audit; established the
  `automation-gap-roadmap.yaml` 13-conversion set this ADR closes.
- **ADR-051** — non-delegation principle; sub-agent dispatch
  patterns used in PLAN-088 wave authoring are read-only proposal
  + CEO-applied per this ADR.
- **ADR-052** — VETO-floor archetype routing; the 5-archetype R1
  debate that gated PLAN-088 PROPOSED → reviewed transition.
- **ADR-115** — Post-SOTA maintenance-mode declaration; this ADR
  AMENDS ADR-115 §scope-amendment.
- **ADR-116** — KERNEL HARD-DENY tier-0 extension; `_KERNEL_PATHS`
  baseline that PLAN-088 W5.1 `verify-persona-coverage.py`
  cross-links into.

## §7. Authorization

- PLAN-088 closeout ceremony script
  `OWNER-CEREMONY-PLAN-088-CLOSEOUT.sh` performs:
  1. Run `python3 .claude/scripts/verify-adr-118-rationale.py` →
     must exit 0.
  2. Run `python3 .claude/scripts/verify-persona-coverage.py` for
     each persona → all 4 must meet thresholds.
  3. Flip ADR-118 frontmatter `status: PROPOSED` → `status:
     ACCEPTED` + populate `accepted_at` + `accepted_by`.
  4. GPG-sign closeout commit + tag `v1.22.0`.
- Owner physical: GPG signing only (no manual edits to §3 SHA-pin
  table; ceremony script is read-only on this ADR body, write-only on
  frontmatter status fields).
