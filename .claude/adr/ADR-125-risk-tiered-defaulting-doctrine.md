---
id: ADR-125
title: Risk-tiered defaulting doctrine for capability rollout
status: ACCEPTED
proposed_at: 2026-05-13
accepted_at: 2026-05-13
proposed_by: CEO (Session 117 FASE 0 doctrine cleanup; Codex revalidation S115-cont REVISIT #1)
related_plans: [PLAN-090, PLAN-096, PLAN-097, PLAN-098, PLAN-099, PLAN-100, PLAN-101, PLAN-102, PLAN-103]
related_adrs: [ADR-019, ADR-042, ADR-062, ADR-064, ADR-104, ADR-118, ADR-124, ADR-126]
supersedes: []
authorization: PLAN-103 sentinel `.claude/plans/PLAN-103/architect/round-1/approved.md` + `.asc` (Owner GPG 0000000000000000000000000000000000000000)
---

# ADR-125 — Risk-tiered defaulting doctrine for capability rollout

## Status

ACCEPTED — Session 117 FASE 0 doctrine cleanup 2026-05-13 — Codex R2 iter-2 ACCEPT thread `019e2252-6e41-7152-8db9-ef85854c14fe` — Owner GPG 0000000000000000000000000000000000000000 via PLAN-103 sentinel `.asc`.

## Date

2026-05-13

## Context

ADR-124 establishes post-audit-SOTA-execution-mode for FASE 1-4 plan
execution. FASE 4 introduces seven capability rollouts each requiring
a default-state decision:

| Plan | Capability | Without doctrine: what's the default? |
|---|---|---|
| PLAN-090 §AC18 | confidence-gate baseline measurement | ON (cheap) or OFF (telemetry-only)? |
| PLAN-096 | read-only MCP server expansion | ON (low risk) or OFF (opt-in)? |
| PLAN-097 | RAG installability + conditional | conditional (HW class) or always opt-in? |
| PLAN-098 | GOAP advisory planner | advisory-ON or opt-in? |
| PLAN-099 | federation stdlib SSL read-only MVP | ON or OFF? |
| PLAN-100 | confidence-gate FPR-class block-mode | OFF until empirical proof? |
| PLAN-101 | AEK Calibration C2-C4 | calibration-only or apply-default? |
| PLAN-102 | autonomous-loop default-ON | ON or OFF? (Codex P12 STILL-VALID flagged) |

Without doctrine, each plan re-debates from zero. Worse, defaults
drift inconsistently (e.g., PLAN-102 autonomous-loop default-ON was
S115-cont scope locked AS default-ON, but ADR-064 LLM-FinOps cost-
envelope discipline argues default-OFF for any token-spending feature).

Codex MCP revalidation S115-cont (thread `019e215c-cff5`) Premise P1
verdict REVISIT: *"risk-tiered defaulting needs doctrine, not ad-hoc
per-plan decisions."* Master plan validation thread `019e21ef-36d6`
ordered FASE 4 plans **observable-surfaces FIRST, spendy autonomy
LAST** — the operational intuition that this ADR formalizes.

Three concrete drift cases in already-shipped plans:

- **ADR-019** (confidence-gate) shipped 2026-04-08 with **advisory-
  ON** default; PLAN-100 will flip to block-mode default-OFF after
  empirical proof. Different ADRs, different tiers → consistent.
- **ADR-042** (MCP server contract) shipped 2026-04-15 with
  **opt-in** default for adopter install; PLAN-096 expansion stays
  opt-in. Consistent with conservative MCP tier.
- **ADR-064** (LLM-FinOps) shipped 2026-04-23 with **kill-switch
  default-OFF** for spendy operations; ADR-118 (god-mode AUTO-
  USABLE) shipped 2026-05-13 with default-ON for free wiring. Mixed
  signal.

This ADR provides the missing classification rule.

## Decision drivers

- **Default = trust gradient.** Defaults encode "we trust this
  enough to ship ON to every adopter". Trust must be earned per
  blast-radius tier, not assumed uniformly.
- **Cost-envelope discipline (ADR-064).** Any default that spends
  tokens autonomously crosses the cost-quality dimension; ADR-064
  governance requires explicit gate.
- **Adopter front-door TTV.** ADR-115 §exception #3 caps install
  TTV at 5 minutes. Defaults that require config to be useful break
  TTV. Tier-A defaults should "just work".
- **Reversibility.** Tier-A defaults can be flipped OFF without
  data loss. Tier-C defaults (autonomous-loop, RAG indexing,
  federation peering) leave state behind that is expensive to
  revert.
- **Mechanical classification.** Each plan's default decision should
  reduce to "which tier is this capability?" not "what should this
  plan's default be?"

## Options considered

### Option A — Per-plan ad-hoc defaults

Status quo. Each plan debates default-ON vs default-OFF in its
own §AC block.

**Rejected** — already produces drift (ADR-064 OFF vs ADR-118 ON
for similar wiring surfaces). Codex P1 REVISIT directive applies.

### Option B — Single default rule (everything default-OFF, opt-in)

Conservative. All FASE 4 capabilities ship default-OFF; adopters
flip ON per-feature via env or settings.

**Rejected** — breaks TTV for cheap, observable-surface capabilities
(read-only MCP, GOAP advisory). Defeats the purpose of evolution-
roadmap shipping.

### Option C — Three-tier risk-tiered defaulting doctrine (CHOSEN)

Classify each capability into Tier A/B/C by blast radius +
reversibility + cost-envelope cross. Tier dictates default.

**CHOSEN.**

### Option D — Adopter-profile-based defaults (vibecoder vs team vs enterprise)

Three profiles, each with own default matrix.

**Rejected** — ADR-096 §Option B explicitly rejected the profile
system 2026-04-29 ("~5 dev-day extra work without proven demand").
This ADR honors that prior decision.

## Decision

**Option C.** Three-tier risk-tiered defaulting doctrine:

### Classification rule (applies BEFORE Tier A/B/C below)

Classify each capability at the **smallest independently kill-
switched surface**. If one env var / settings flag bundles a
Tier-A read-only surface with a Tier-B/C write/spend surface, the
entire bundle is classified to the HIGHEST tier present (A < B < C
escalation) — adopters MUST split the kill switch into separate
flags OR accept the higher tier.

This rule prevents the slippery-slope failure mode "Tier-A default-
ON observable surface silently activates Tier-C autonomous spend".
A single env var that flips both is a Tier-C kill switch.

**Classification audit**: each plan claiming Tier A or B MUST
enumerate every side effect of its kill switch in §Default block.
If any enumerated side effect crosses Tier-C criteria, the plan is
reclassified or the kill switch is split before status flip
`draft → reviewed`.

### Tier A — Observable-surfaces (default-ON)

**Criteria** (all must hold):

1. Read-only OR additive-only (no destructive side effects).
2. No token spend in steady state (telemetry/log-emit OK; LLM
   invocation NOT OK).
3. Kill-switch via single env var or settings flag.
4. Reversal restores prior state byte-identically **EXCEPT** for
   append-only audit/telemetry emission. Audit-log entries
   (`audit-log.jsonl`) + metric counters (sessionStart/etc) remain
   after kill-switch flip OFF — by design (forensic trail per
   ADR-115 §Detection-decay monitor). Append-only telemetry/audit-
   emit is the SOLE exemption from byte-identical reversal; any
   other persisted state (config file write, cache file, vector
   store, lock file beyond session scope) disqualifies Tier A.

**Default**: ON for all installs.

**Plans in Tier A**:
- PLAN-090 §AC18 confidence-gate baseline measurement (telemetry-only)
- PLAN-096 read-only MCP server expansion (read-only governance surface)
- PLAN-098 GOAP advisory planner (advisory-ON; no autonomous spend)
- PLAN-099 federation stdlib SSL read-only MVP (read-only peer view)

**Kill-switch envelope**: each Tier-A capability MUST document a
single env var that flips it OFF. Example:
`CEO_GOAP_ADVISORY_ENABLED=0`.

### Tier B — Conditional/calibrated (default-conditional)

**Criteria** (any one):

1. Requires hardware-class check before usefulness (RAG needs
   embeddings infrastructure).
2. Requires calibration data accumulation before activation (AEK
   C2-C4 needs N≥30 dispatch samples).
3. Spends tokens conditionally based on policy (confidence-gate
   block-mode only when FPR class proven below threshold).

**Default**: conditional-ON via runtime detection or accumulated
calibration; falls back to OFF if condition unmet.

**Plans in Tier B**:
- PLAN-097 RAG installability — Tier B applies ONLY to retrieval
  routing once the C2 sidecar is already installed (read-only
  query path against a pre-built vector index). Sidecar install +
  index build + autostart fall under Tier C per the split table
  below (those operations create persisted state). RAG default
  flip (from opt-in to conditional-ON) REQUIRES ADR-062-AMEND-1
  ACCEPTED first.
- PLAN-100 confidence-gate FPR-class block-mode — default-OFF until
  empirical FPR proof from PLAN-090 §AC18 baseline. Flips default-
  ON via amendment ADR after N≥30 samples with FPR ≤ documented threshold.
- PLAN-101 AEK Calibration C2-C4 — calibration accumulates default-
  OFF; activation flips conditional-ON per AEK policy after
  calibration window.

**Promotion path**: Tier B → Tier A requires amendment ADR citing
empirical evidence (sample size + threshold + observation window).
**Strictest-existing-threshold rule**: if a predecessor ADR sets a
stricter promotion gate (e.g., ADR-019 `<1% FPR sustained for 30
consecutive days`), the amendment ADR MUST satisfy the strictest
existing threshold, NOT just the generic `N≥30 samples` baseline.
Generic samples-only promotions are insufficient where domain-
specific gates exist. The amendment ADR MUST cite the predecessor
threshold + demonstrate the higher bar is met before tier flip.

### Tier C — Spendy/destructive (default-OFF, opt-in only)

**Criteria** (any one):

1. Spends tokens autonomously without per-action user prompt
   (autonomous-loop, autonomous RAG re-indexing, autonomous
   federation gossip).
2. Mutates external state outside the framework's git repo
   (sidecar persists vector store, federation publishes to peers).
3. Per-invocation token cost exceeds adopter-default budget cap
   (ADR-064 LLM-FinOps gate).

**Default**: OFF. Opt-in via explicit env var AND explicit
acknowledgment of cost-envelope (ADR-064 cost-cap manifest entry).

**Plans in Tier C**:
- PLAN-102 autonomous-loop default-ON — paradoxically, the plan's
  *name* contains "default-ON" but doctrine REQUIRES this be opt-in
  per the autonomous-token-spend criterion. **PLAN-102 plan rename
  amendment required** before ship; or plan ships in Tier C with
  default-OFF and the ADR-133 (PLAN-102's own ADR) names the opt-in
  trigger explicitly.

**Cost-envelope manifest**: each Tier-C opt-in MUST declare in its
plan §Cost section: (a) per-invocation token estimate, (b) daily
burn cap, (c) cost-cap enforcement mechanism.

### Cross-ADR refinement table

| ADR (sub-surface) | Capability | Pre-this-ADR default | Post-this-ADR tier | Adjustment? |
|---|---|---|---|---|
| ADR-019 | confidence-gate advisory | advisory-ON | A | no change |
| ADR-019-AMEND-1 (PLAN-100) | block-mode | (proposed default-OFF) | B → A (after `<1% FPR 30d` proof per ADR-019 strictest threshold) | promotion path with strictest-threshold gate |
| ADR-042 (read-only handlers: `list_skills`, `get_session_state`, etc.) | MCP read-only surface | opt-in | A | flip default-ON in PLAN-096 read-only expansion |
| ADR-042 (write/cost handlers: `spawn_agent`, `dispatch_*`) | MCP write/spend surface | opt-in | C | remains explicit opt-in; default-deny ACLs enforced; per-handler cost-envelope manifest required |
| ADR-062 (route to running sidecar) | RAG retrieval (read-only query path) | opt-in (manual install) | B (conditional on C2 sidecar already installed + HW class) | conditional default-ON ONLY after ADR-062-AMEND-1 ACCEPTED |
| ADR-062 (install + index + autostart) | RAG install / index build / vector-store mutation | opt-in (manual install) | C (persisted state mutation) | remains explicit opt-in; sidecar install creates persisted state outside framework git |
| ADR-064 | LLM-FinOps cost-envelope | gate-required | C governance source | no change |
| ADR-104 | AEK advisory | advisory | B (calibration) | conditional activation |
| ADR-118 | god-mode AUTO-USABLE | default-ON (free wires) | A | confirms — capability_surface_delta=0 |

## Consequences

**Positive (+):**

- FASE 4 plans inherit doctrine instead of re-debating defaults.
- Mechanical tier-classification reduces plan-review friction.
- Cost-envelope discipline (ADR-064) wired into Tier-C gate.
- Adopter TTV preserved — Tier-A "just works" + Tier-C requires
  explicit opt-in.
- Reversibility guarantee for Tier-A defaults eliminates "we shipped
  default-ON and adopters can't go back" failure mode.

**Negative (-):**

- Adds tier-classification step to plan review.
- PLAN-102 plan title "autonomous-loop default-ON" becomes
  semantically misleading — requires title amendment OR plan
  rescope.
- Promotion path Tier B → Tier A requires amendment ADR per
  capability (added doctrinal overhead).

**Neutral (~):**

- ADR-118 god-mode AUTO-USABLE (default-ON wires) classified as
  Tier A retroactively; no behavior change.
- ADR-064 LLM-FinOps remains the governance source for Tier-C
  cost-cap enforcement.

## Blast radius

**L3+** — affects every FASE 4 plan default decision. Touches:

- This ADR (new).
- `.claude/plans/PLAN-090/AMENDMENT-1.md` — §AC18 tier-A classification.
- `.claude/plans/PLAN-09{6,7,8,9}.md` + `PLAN-10{0,1,2}.md` —
  §Default section per plan cites tier.
- `.claude/adr/ADR-019.md` + `ADR-042.md` + `ADR-062.md` +
  `ADR-104.md` — append §Tier classification line (deferred to per-
  ADR amendment plans; NOT in PLAN-103 scope).
- `CLAUDE.md` §Current Work — tier reference (closeout drift queued).

No `.claude/hooks/`, no `SPEC/`, no policy file changes.

## Compliance checklist

| Item | Verification |
|---|---|
| ADR file present | `test -f .claude/adr/ADR-125-risk-tiered-defaulting-doctrine.md` |
| Codex R2 3-iter ACCEPT logged | thread ref in §Codex MCP gate trail |
| Tier A/B/C criteria mechanically applicable | dry-run on 7 FASE 4 plans → unique tier |
| Each Tier-A capability has env kill-switch documented | grep `CEO_.*_ENABLED` in plan §Default |
| Each Tier-B capability has promotion-path amendment ADR slot reserved | ADR table updated |
| Each Tier-C capability has cost-envelope manifest entry | plan §Cost present |
| PLAN-102 tier alignment | rename OR rescope addressed in PLAN-102 §Tier |

## Related decisions

- ADR-019 — Confidence-gate (advisory-ON) — Tier A pre-existing
- ADR-019-AMEND-1 (PLAN-100) — block-mode promotion — Tier B with documented Tier-A path
- ADR-042 — MCP server contract — Tier A read-only surface
- ADR-062 — RAG installability — Tier B conditional
- ADR-064 — LLM-FinOps cost-envelope — Tier-C gate source
- ADR-104 — AEK advisory — Tier B calibration
- ADR-118 — God-mode AUTO-USABLE — Tier A confirmed
- ADR-124 — Post-audit-SOTA-execution-mode — operational scope source
- ADR-126 — Governed sidecar capability model — sidecar-class source for Tier-B/C HW gating
- PLAN-084 evolution-roadmap.md — 45-item source for tier classification

## Codex MCP gate trail

- Cross-LLM revalidation: thread `019e215c-cff5-7ed3-a7f1-87e4b8f94439` (S115-cont) — P1 REVISIT.
- Master plan FASE-4 ordering: thread `019e21ef-36d6-7083-82d6-d41b26b61a80` (S115-cont).
- This ADR R2 iter-1 NEEDS-FIXES (5 findings: 4 P1 + 1 P2): thread `019e2252-6e41-7152-8db9-ef85854c14fe` (Session 117 Wave 1) — all 5 folded inline 2026-05-13 (classification preamble + Tier-A audit exemption + ADR-042 split + ADR-062 split + strictest-threshold promotion rule).
- This ADR R2 iter-2 final **ACCEPT** (early-exit from 3-iter pattern): thread continuation `019e2252-6e41-7152-8db9-ef85854c14fe` — verdict 2026-05-13: "ACCEPT. The iter-1 blockers are materially folded: classification is now surface-scoped, mixed bundles escalate, audit-only persistence is bounded, ADR-042/062 are split correctly, and promotions inherit stricter predecessor gates."

## Authorization

PLAN-103 sentinel `.claude/plans/PLAN-103/architect/round-1/approved.md` +
detached `.asc` signature (Owner GPG 00000000).

## §Part 3: skill activation modes (PLAN-110 Wave H)

> **Added 2026-05-20 by PLAN-110 Wave H.** Binds Tier-A defensibility
> to explicit `activation_mode:` frontmatter discipline.

### Three modes

| Mode              | Tier-A allowed? | Tier-B allowed? | Tier-C allowed? |
|-------------------|-----------------|-----------------|-----------------|
| `manual-only`     | YES (canonical) | YES             | YES             |
| `event-driven`    | NO              | YES             | YES (with ADR)  |
| `default-on`      | NO              | YES (with ADR)  | YES (with ADR + kill-switch + sentinel) |

### Promotion ceremony

Mode promotion is L3+ doctrine change. See
`docs/SKILL-ACTIVATION-MODES.md` for the full 9-gate ceremony.

### Audit field

New skills MUST declare `activation_mode:` in frontmatter.
`.claude/scripts/check-skill-activation-mode.py` advisory CI emits
warning if absent (fail-OPEN).

