---
id: ADR-062-AMEND-1
title: RAG conditional default-ON via repo-profile LARGE — supersedes §default-OFF clause for LARGE profile only
status: ACCEPTED
accepted_at: 2026-05-17
date: 2026-05-17
proposed_at: 2026-05-17
proposed_by: CEO (PLAN-097 Wave 0 — S131 execution, post-PLAN-096 v1.29.0 ship)
amends: ADR-062
related_plans: [PLAN-041, PLAN-062, PLAN-093, PLAN-096, PLAN-097]
related_adrs: [ADR-062, ADR-125, ADR-126, ADR-128]
blast_radius: moderate
authorization: PLAN-097 sentinel `.claude/plans/PLAN-097/approved.md` + `.asc` (Owner GPG 0000000000000000000000000000000000000000) — TO BE COLLECTED AT CEREMONY
---

# ADR-062-AMEND-1 — RAG conditional default-ON via repo-profile LARGE

## Status

ACCEPTED. (Drafted PROPOSED Session 131 (2026-05-17) under PLAN-097 Wave 0
per PLAN-097 §3 Wave 0 + §5 ADRs-proposed; promoted PROPOSED → ACCEPTED at
the Owner ceremony after the Codex R2 3-iter ACCEPT cycle. Frontmatter
`status:` is the source of truth — PLAN-113 W2 reconciled this body marker
to match.)

## Date

2026-05-17

## Amendment summary

This amendment **narrows** ADR-062 §Decision §Invariants-preserved
`Opt-in default: CEO_RAG_SIDECAR=0` clause to apply to SMALL/MEDIUM
repo profiles only. For LARGE repo profiles (LoC ≥ 200,000 per
`detect-repo-profile.py` §LARGE classifier), the framework routes
retrieval queries to an Owner-instantiated sidecar process when one
is detected running. The amendment does NOT auto-start the sidecar
daemon and does NOT auto-install the sidecar; both remain Owner-
gated per ADR-126 §Part 3 C2 Tier-C install + ADR-128 §governance.

## Scope (what changes / what does not)

| ADR-062 clause | Pre-amendment | Post-amendment (LARGE only) | Unchanged (SMALL/MEDIUM) |
|---|---|---|---|
| §Decision §Opt-in default | `CEO_RAG_SIDECAR=0` everywhere | LARGE: framework AUTO-WIRES routing when sidecar is running | `CEO_RAG_SIDECAR=0` default |
| §Sidecar lifecycle §Auto-start | "explicitly NOT" auto-started | UNCHANGED — daemon never auto-started | UNCHANGED |
| §Auth (0600 socket) | UNCHANGED | UNCHANGED | UNCHANGED |
| §Kill-switches | `CEO_RAG_SIDECAR=0` wins | `CEO_RAG_SIDECAR=0` STILL wins (legacy alias); `CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED=0` ALSO wins (new positive-form class kill per ADR-128) | UNCHANGED |
| §Storage layout | UNCHANGED | UNCHANGED | UNCHANGED |
| §Fail-open | UNCHANGED — CAG fallback when sidecar unavailable | UNCHANGED | UNCHANGED |

## Decision

ADR-062 §Decision §Invariants-preserved bullet 8 reads:

> ✅ **Opt-in default:** `CEO_RAG_SIDECAR=0` is the default —
> adopters must explicitly enable. Zero overhead when off.

Replace with:

> ✅ **Tiered default per repo profile (amended by ADR-062-AMEND-1):**
>
> - **SMALL** (LoC < 50,000) and **MEDIUM** (50,000 ≤ LoC < 200,000):
>   `CEO_RAG_SIDECAR=0` opt-in default unchanged. Zero overhead.
> - **LARGE** (LoC ≥ 200,000): when `detect-repo-profile.py` emits
>   LARGE AND the sidecar process is detected running on the
>   `~/.ceo-orchestration/rag/sidecar.sock` Unix socket, the framework
>   **AUTO-WIRES** retrieval routing to it. The framework still does
>   NOT auto-start the daemon and does NOT auto-install the sidecar
>   — both remain Owner-gated (interactive prompt in `install.sh`
>   per PLAN-097 Wave C.2). When the sidecar is not running, the
>   framework emits `rag_auto_wire_skipped_sidecar_down` and falls
>   through to CAG-only retrieval (no behaviour change vs SMALL/MEDIUM).
> - **Migration**: existing adopters with `CEO_RAG_SIDECAR=0`
>   explicitly set are **unaffected** — the kill-switch always wins
>   per the precedence rule below.

### Kill-switch precedence (clarification)

Order of evaluation (highest priority wins):

1. `CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED=0` (positive-form class
   kill per ADR-128 §3) → ROUTING DISABLED regardless of profile.
2. `CEO_RAG_SIDECAR=0` (legacy alias preserved by routing layer)
   → ROUTING DISABLED regardless of profile.
3. `repo_profile == LARGE AND sidecar_installed AND sidecar_running`
   → ROUTING ENABLED. This is the canonical 3-clause predicate per
   ADR-128 §3 `governance.activation_predicate`; the health-probe
   socket connect is the implementation of `sidecar_running` (the
   routing layer probes the Unix socket and treats `connect()`
   success as the sub-clause evaluating true).
4. Default (SMALL/MEDIUM, or LARGE without running sidecar) →
   ROUTING DISABLED, CAG fallback used.

Both legacy `CEO_RAG_SIDECAR=0` and new
`CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED=0` MUST disable routing
when either is set. The routing layer reads both env vars; the
class kill-switch (ADR-128) is the canonical form going forward.
The legacy alias is preserved at v1.30.0 ship for backward
compatibility; **re-evaluation milestone**: the alias remains in
place until ADR-062-AMEND-2 promotes Tier B → Tier A (sustained
AC10 < 1% + AC11 ≥ 60% over 30d, per PLAN-097 §6b). The amendment
landing B → A is the natural moment to consider deprecation.

## Decision drivers

- **ADR-125 risk-tiered defaulting**: this amendment classifies
  RAG-routing-to-installed-sidecar as **Tier B (conditional default-ON
  via predicate evaluation)** per ADR-125 line 187-192. Tier B
  authorizes default-ON when predicate evaluates true at init —
  predicate here is `repo_profile == LARGE AND sidecar_socket_present
  AND sidecar_health_probe_succeeds`. Sidecar **install** remains
  **Tier C (Owner physical consent)** — interactive prompt in
  install.sh; no change to Tier-C semantics.
- **ADR-126 capability classes**: ADR-128 (this amendment's sibling
  ADR proposed in same PLAN-097) declares the C2 vector-memory
  capability class authorizing this sidecar. ADR-062 §Decision is
  refined by ADR-128 §scope for LARGE-profile behaviour.
- **PLAN-097 §6b default block**: explicit Tier B (routing) +
  Tier C (install) split. Promotion B → A requires sustained <1%
  false-LARGE classification + ≥60% hit-rate over 30d (AC10 + AC11)
  via subsequent ADR-062-AMEND-2 (NOT in scope this amendment).
- **TTV preservation (ADR-115 §exception #3)**: adopters with
  SMALL/MEDIUM repos see zero install-time overhead and zero new
  Tier-S checks. LARGE adopters see the interactive sidecar-install
  prompt during `install.sh` — TTV impact ≤30s when declined.

## Migration & backward compatibility

- **Existing `CEO_RAG_SIDECAR=0` adopters**: zero behavioural change.
  Kill-switch wins per precedence rule §1-2 above.
- **Existing `CEO_RAG_SIDECAR=1` adopters**: zero behavioural change
  on SMALL/MEDIUM. On LARGE repos, framework now auto-wires routing
  to their already-running sidecar (previously they had to invoke
  query tools explicitly).
- **Adopters without `CEO_RAG_SIDECAR` set on LARGE repos**: NEW
  behaviour — framework prompts to install sidecar at `install.sh`
  run; if installed and running, routing auto-wires. Skipping the
  prompt leaves the adopter in pre-amendment state (CAG-only).
- **No silent state mutation**: routing AUTO-WIRE is observable via
  `rag_query_routed` audit emit per query (AC14 wave). Adopters
  can audit-log-query for routing decisions.

## Consequences

**Positive (+):**

- LARGE-repo adopters get retrieval-augmented query routing without
  manual `CEO_RAG_SIDECAR=1` flag-flipping.
- SMALL/MEDIUM adopters unchanged — zero overhead, zero new env vars
  required.
- Kill-switch dual-form (legacy + class) preserves opt-out for any
  adopter regardless of profile, without ambiguity.
- Conditional default-ON pattern (Tier B per ADR-125) becomes
  repeatable for future capability classes that benefit from
  predicate-gated activation.

**Negative (-):**

- LARGE-classification false-positives (FP) auto-wire routing in
  repos that don't benefit from RAG. Mitigation: AC10 `<1% false-LARGE
  rate over 30d rolling window` measured on N≥30 reference corpus
  (PLAN-097 Wave A.7); >1% sustained 7d demotes routing predicate
  to OFF via `rag_false_large_demoted` audit emit.
- Hit-rate degradation (sidecar returns junk results) silently
  routes through to Claude context. Mitigation: AC11 `≥60% hit-rate
  on golden-query set over 30d`; <60% sustained 7d demotes via
  `rag_hit_rate_degraded`.
- Dual kill-switch (legacy + class) requires routing layer to read
  both env vars and OR them. Implementation cost: ~20 LoC in
  `.claude/hooks/_lib/rag_router.py` (PLAN-097 Wave C.3).

**Neutral (~):**

- ADR-062 §Architecture diagram (stdlib-only core + isolated sidecar
  venv) unchanged.
- ADR-062 §Storage layout (`~/.ceo-orchestration/rag/`) unchanged.
- ADR-062 §Interface (3 MCP tools) unchanged.

## Compliance checklist

| Item | Verification |
|---|---|
| `detect-repo-profile.py` emits `size_class == "LARGE"` for ≥200k LoC | `python3 .claude/scripts/detect-repo-profile.py detect --target <large-fixture> --json` returns `.size_class == "LARGE"`. Reference fixtures under `.claude/scripts/fixtures/corpus-expansion/` per PLAN-097 Wave A.7. |
| Routing layer reads BOTH env vars | grep for `CEO_RAG_SIDECAR` + `CEO_SIDECAR_C2_VECTOR_MEMORY_ENABLED` in `.claude/hooks/_lib/rag_router.py` |
| Legacy `CEO_RAG_SIDECAR=0` precedence preserved | unit test `test_kill_switch_legacy_alias_wins` |
| Sidecar daemon never auto-started by framework | code-review of routing layer + install.sh — no `nohup` / `systemd-run` / `launchctl` invocations |
| Profile-LARGE predicate honors sidecar-running check | unit test `test_profile_large_sidecar_down` |
| All 5 RAG audit emits registered | `grep -E 'rag_profile_recommended\|rag_auto_wire_skipped_sidecar_down\|rag_query_routed\|rag_false_large_demoted\|rag_hit_rate_degraded' .claude/hooks/_lib/audit_emit.py` (≥10 matches: 5 in `_KNOWN_ACTIONS` + 5 emit_* defs) |
| ADR-128 (C2 class) status post-Codex-R2 | `.claude/adr/ADR-128-c2-vector-memory-capability-class.md` status: ACCEPTED |
| Demotion mechanism is observability-only at v1.30.0 | `rag_false_large_demoted` + `rag_hit_rate_degraded` emit on AC10/AC11 thresholds; ACTUAL routing demotion to OFF requires Owner intervention (set kill-switch). Auto-demote is OUT OF SCOPE for v1.30.0 — see PLAN-097 §6b for promotion B→A criteria; PLAN-097-FOLLOWUP may add auto-demote in-process flag. |

## Related decisions

- **ADR-062** — amended by this amendment. Original §Opt-in default
  clause superseded for LARGE-profile only.
- **ADR-125** — risk-tiered defaulting doctrine. Tier B authorizes
  predicate-gated default-ON (routing); Tier C governs install.
- **ADR-126** — governed sidecar capability model. C2 vector-memory
  class is the home for RAG sidecar (ADR-128 authorizing).
- **ADR-128** — C2 vector-memory authorizing ADR (PLAN-097 sibling).
  This amendment cross-references ADR-128 §governance.kill_switch_env
  for the canonical class kill-switch.
- **PLAN-041** — original RAG sidecar implementation plan.
- **PLAN-062** — CAG/RAG adopter docs (CAG fallback always available
  per ADR-005).
- **PLAN-093** — ships detect-repo-profile.py fixtures (4 SEED at
  `.claude/scripts/fixtures/`); PLAN-097 Wave A.7 expands to N≥30
  reference corpus.
- **PLAN-097** — this amendment's proposing plan. Wave C wires
  routing per the amended semantics.

## Codex MCP gate trail

Codex R2 3-iter ACCEPT trail (PLAN-097 promotion ceremony, S131):

- This ADR R2 iter-1: ACCEPT-WITH-FIXES at PLAN-097 Wave 0.3 execution (S131) — 4 findings folded inline pre-ship: predicate canonical 3-clause, compliance row 1 size_class binding, legacy alias re-evaluation milestone, all 5 RAG audit emits enumerated, single-sentinel-covers-both note.
- This ADR R2 iter-2: ACCEPT — canonical state cross-checked vs ADR-128 §3 governance.activation_predicate, manifest.json, rag_router.py evaluate_predicate, audit_emit.py 5 _KNOWN_ACTIONS + 5 emit_* defs.
- This ADR R2 iter-3 (final): **ACCEPT** — all cross-checks pass; status flip PROPOSED → ACCEPTED authorized.

## Authorization

PLAN-097 sentinel `.claude/plans/PLAN-097/approved.md` + detached
`.asc` signature (Owner GPG
0000000000000000000000000000000000000000) collected at PLAN-097
Owner ceremony (v1.30.0 ship).

**Single-sentinel-covers-both** — per ADR-126 §Part 7 (single ADR
ceremony pattern), one Owner-signed sentinel at
`.claude/plans/PLAN-097/approved.md` covers ADR-128 + ADR-062-AMEND-1
same-ceremony scope. The `approved.md` §Scope block enumerates both
canonical paths explicitly.
