---
id: ADR-124
title: Post-audit-SOTA-execution-mode supersedes ADR-096 terminal verdict
status: ACCEPTED
proposed_at: 2026-05-13
accepted_at: 2026-05-13
proposed_by: CEO (Session 117 FASE 0 doctrine cleanup; Codex revalidation S115-cont P4 REFUTED)
related_plans: [PLAN-084, PLAN-085, PLAN-086, PLAN-087, PLAN-088, PLAN-089, PLAN-090, PLAN-092, PLAN-093, PLAN-094, PLAN-095, PLAN-096, PLAN-097, PLAN-098, PLAN-099, PLAN-100, PLAN-101, PLAN-102, PLAN-103]
related_adrs: [ADR-085, ADR-093, ADR-095, ADR-096, ADR-103, ADR-105, ADR-115]
supersedes: []
partially_supersedes: [ADR-096]
amends: [ADR-115]
authorization: PLAN-103 sentinel `.claude/plans/PLAN-103/architect/round-1/approved.md` + `.asc` (Owner GPG 0000000000000000000000000000000000000000)
---

# ADR-124 — Post-audit-SOTA-execution-mode supersedes ADR-096 terminal verdict

## Status

ACCEPTED — Session 117 FASE 0 doctrine cleanup 2026-05-13 — Codex R2 iter-3 final ACCEPT thread `019e2250-6e34-7b90-8440-75c429042118` verdict 2026-05-13: "ACCEPT — iter-2 fixes are folded; scope, sunset, cross-ref, and deferred blast-radius handling are now mechanically bounded enough for ADR-124 ACCEPTED." — pending Owner GPG ceremony commit (Wave 3) via PLAN-103 sentinel `.asc`.

## Date

2026-05-13

## Context

ADR-096 (2026-04-29) declared `MAINTENANCE-MODE-VIBECODER` as the
**terminal verdict** for this framework's operational identity. The
ADR's §Part 3 reads:

> Verdict transitions from `TRIAL-PENDING-SOAK` to
> `MAINTENANCE-MODE-VIBECODER`. MAINTENANCE-MODE-VIBECODER is the
> terminal verdict for this framework's identity.

ADR-115 (2026-05-12, PLAN-084 Phase E closeout) then declared
**post-SOTA maintenance mode** as the operational mode after audit
finalization, with four `§exception` clauses permitting:

1. P0 security findings via PLAN-085+ burn-down.
2. Roadmap items in PLAN-085+ burn-down — already-debated; small focused plans.
3. Adopter-blocking install bugs.
4. v2.0 trigger: ≥10 concrete Owner-friction findings from 5-repo real-world usage.

Since ADR-115 ACCEPTED, the framework shipped **six consecutive
substantive plans** under §exception clause #2:

| Plan | Tag | Surface | "Roadmap item" claim |
|---|---|---|---|
| PLAN-085 | v1.19.0 | Kernel hardening + 8 P0 security closures | ✓ TIER 1 P0 |
| PLAN-086 | v1.20.0 | P1 burn-down + Wave I.1 UNLOCK regex | ✓ TIER 1 P1 |
| PLAN-087 | v1.21.0 | P2/P3 perf burn-down | ✓ TIER 2 P2 |
| PLAN-088 | v1.22.0 | Capability auto-activation (god-mode AUTO-USABLE) | ⚠ feature, framed as wiring |
| PLAN-089 | v1.23.0 (reviewed) | Kernel + auth hardening | ✓ TIER 1 hardening |
| PLAN-090 | v1.24.0 (reviewed) | Capability rollout + v2.0 trigger | ❌ feature, no §exception cover |

**Codex MCP cross-LLM revalidation S115-cont (thread `019e215c-cff5`)**
flagged this pattern as Premise P4 — *"maintenance-mode fig leaf"* —
with verdict REFUTED. Codex thread `019e21fe-f2d2` then validated the
remediation: **supersede ADR-096's terminal-verdict claim honestly via
a new ADR rather than continue stretching §exception clauses.**

The lesson [`maintenance_mode_fig_leaf`](~/.claude/projects/-Users-devuser-ceo-orchestration/memory/lesson_session_115_maintenance_mode_fig_leaf.md)
codifies the rule:

> If §scope-extension clauses justify 3+ consecutive feature plans,
> supersede honestly via new ADR. ADR-096 maintenance-mode → ADR-124
> post-audit-SOTA-execution-mode.

PLAN-090 (capability rollout) cannot honestly claim §exception cover.
Either we accept feature work post-audit and rename the mode honestly,
or we freeze further plans. The framework's lived behavior is "execute
the 45-item evolution-roadmap from PLAN-084". This ADR names that mode.

## Decision drivers

- **Honest framing > fig leaf.** Six §exception invocations make the
  "terminal" verdict false. Per ADR-092 closure-honesty discipline,
  OWN the operational reality.
- **Doctrinal cover for PLAN-090+ feature plans.** Plans that ship
  evolution-roadmap items deserve explicit cover, not §exception
  contortions.
- **Preserve ADR-096 §Part 1+2.** Positioning claims (bus-factor 1,
  no SLA, vibecoder-only audience) remain valid and load-bearing for
  README §Risks. Only §Part 3 terminal-verdict claim is superseded.
- **Preserve ADR-115 §exception #4** (v2.0 trigger). v2.0 still
  requires ≥10 concrete Owner-friction findings from 5-repo usage.
- **Sunset built-in.** Post-audit-SOTA-execution-mode is bounded by
  the 45-item evolution-roadmap from PLAN-084. When roadmap closes
  (FASE 4 PLAN-102 ship) OR v2.0 trigger fires, this ADR retires.
- **Cross-LLM gate.** Codex MCP R2 3-iter ACCEPT is mandatory before
  ACCEPTED status flip (per ADR-105 multi-LLM coordinated supersede).

## Options considered

### Option A — Continue stretching ADR-115 §exception #2

Status quo. Each PLAN-NNN claims "roadmap item in burn-down" cover.
Has shipped 6 plans already, can ship N more.

**Rejected** — §exception #2 was scoped for "small focused bug-fix
plans", not for v1.24.0+ feature rollouts. Premise P4 REFUTED by
Codex S115-cont. Lesson `maintenance_mode_fig_leaf` codifies the
anti-pattern. Continued use trains the team to ignore doctrinal
boundaries.

### Option B — Freeze all post-PLAN-088 work until v2.0 trigger

Strict reading of ADR-096 "terminal verdict" + ADR-115 §exception
#4. PLAN-089/090/092..PLAN-102 all blocked.

**Rejected** — discards $2160-3410 of already-debated, already-
roadmap-locked work. v2.0 trigger requires real-world friction
findings that 5-repo usage hasn't generated yet. Freeze would
strand the framework mid-evolution.

### Option C — Supersede ADR-096 §Part 3 + name the actual mode (CHOSEN)

Surgical supersession. Keep §Part 1 (vibecoder-only positioning) +
§Part 2 (README §Risks expansion). Replace §Part 3 (terminal-verdict
claim) with this ADR's post-audit-SOTA-execution-mode declaration.

ADR-115 §exception #2 retires at this ADR's ACCEPTED date — replaced
by the evolution-roadmap scope test below. ADR-115 §exception #1, #3,
#4 remain in force.

**CHOSEN.**

### Option D — Full ADR-096 supersession + new positioning ADR

Replace ADR-096 wholesale with a fresh positioning ADR that bundles
vibecoder-only + post-audit-execution + §exception clauses in one
document.

**Rejected** — ADR-096 §Part 1+2 are correct as written; rewriting
to bundle creates churn without value. Lesson `adr_supersession_drift`
warns against unnecessary supersession scope creep. Surgical wins.

## Decision

**Option C.** Three-part rule:

### Part 1 — Operational mode rename

The framework's operational mode from this ADR's ACCEPTED date until
sunset condition fires is:

**`post-audit-SOTA-execution-mode`**

This mode permits shipping plans that execute the 45-item evolution-
roadmap from PLAN-084 (`.claude/plans/PLAN-084/canonical/PLAN-084-evolution-roadmap.md`)
in TIER 1-7 priority order.

### Part 2 — Scope test (mechanical)

A plan is in-scope under this ADR iff:

1. Its primary deliverable maps to a numbered TIER 1-7 item in
   `.claude/plans/PLAN-084/canonical/PLAN-084-evolution-roadmap.md`,
   **OR** an `AUTO-*` / `SEMI-*` item in
   `.claude/plans/PLAN-084/automation-gap-roadmap.yaml`,
   **OR** a finding ID present in
   `.claude/plans/PLAN-084/canonical/PLAN-084-findings-master.jsonl`
   (P0/P1 only), **OR**
2. It is a hotfix patch (point-release vNNNNN.X) for a bug surfaced
   in a shipped TIER 1-7 plan, **OR**
3. It is a doctrinal ADR (this one, ADR-125, ADR-126, or future
   capability-class ADRs gating roadmap items).

**Mapping discipline (mechanical)**: every PLAN-NNN claiming scope
test #1 cover MUST list its mapped roadmap item IDs in plan
frontmatter as:

```yaml
maps_to_roadmap_items:
  - TIER-N-item-X   # from PLAN-084-evolution-roadmap.md
  - AUTO-NN         # from automation-gap-roadmap.yaml
  - SEMI-NN         # from automation-gap-roadmap.yaml
  - F-A-XXX-NNN     # from findings-master.jsonl (P0/P1 only)
```

Plan status flip `draft → reviewed` is BLOCKED by absence of this
field (enforced via `check_plan_edit.py` after this ADR ACCEPTED).
The three PLAN-084 canonical artifacts are the authoritative ID
sources.

Plans NOT meeting scope test require either:
- Owner-debated proposal (PROTOCOL.md §Plan→Debate→Execute), OR
- Explicit §exception cover from ADR-115 §1/§3/§4.

### Part 3 — Sunset conditions (any one fires)

This ADR retires when one of the following fires:

1. **Roadmap-completion sunset**: PLAN-102 ships AND
   `python3 .claude/scripts/check-roadmap-closure.py` returns
   `closed=45/45 + AUTO/SEMI=13/13` against:
   - `.claude/plans/PLAN-084/canonical/PLAN-084-evolution-roadmap.md` (TIER 1-7)
   - `.claude/plans/PLAN-084/automation-gap-roadmap.yaml` (AUTO/SEMI)
   - `.claude/plans/PLAN-084/canonical/PLAN-084-findings-master.jsonl` (P0/P1 backlog)

   The script ships in PLAN-102 closeout OR PLAN-104 housekeeping
   plan (whichever lands first). **Until `check-roadmap-closure.py`
   exists in `origin/main` HEAD, this sunset trigger CANNOT FIRE.**
   No manual-memory fallback is permitted (mechanical-only sunset
   per ADR-115 §Detection-decay monitor discipline + iter-2 R2
   closure).
2. **v2.0 trigger sunset**: ADR-115 §exception #4 triggers when
   `docs/v2-friction-ledger.md` contains ≥10 entries, each with
   the YAML record shape:

   ```yaml
   - repo: <github-org-or-name>
     friction: <one-line description>
     date: <YYYY-MM-DD>
     finding_id: <optional F-* or AUTO-* if cross-ref>
   ```

   AND entries span ≥5 distinct `repo:` values. Ledger file is
   canonical-guarded; entries land via separate per-friction
   sentinels under `.claude/plans/PLAN-NNN/v2-friction/`.
3. **External-adopter trigger**: ≥3 distinct external GitHub
   orgs (NOT including the Owner's own orgs) open a tracked issue
   in `Canhada-Labs/ceo-orchestration` with label
   `adopter-intent` (label requires Owner manual application;
   self-applied labels do not count) AND Owner confirms intent in
   a session memory entry referencing this ADR. Sub-thresholds
   (1-2 orgs) DO NOT trigger; sunset requires committed-adopter
   signal across multiple parties.

At sunset, status flips ACCEPTED → SUPERSEDED-BY:<new-ADR> via a
fresh ADR drafted under the post-sunset successor doctrine. The
sunset transition is itself a doctrinal supersession event subject
to ADR-105 multi-LLM coordinated supersede (Codex R2 ACCEPT
required).

### Part 4 — Relationship with ADR-115

- ADR-115 §exception #2 (roadmap-item burn-down) **retires** at this
  ADR's ACCEPTED date. Roadmap-item scope is now governed by Part 2
  above.
- ADR-115 §exception #1 (P0 security hotfix), #3 (adopter-blocking
  install bug), #4 (v2.0 trigger) **remain in force**.
- ADR-115 §Detection-decay monitor remains in force unchanged.

### Part 5 — Relationship with ADR-096

- ADR-096 §Part 1 (vibecoder-only positioning declaration) **remains
  in force**. Single-Owner audience, no SLA, no support.
- ADR-096 §Part 2 (README §Risks expansion) **remains in force**.
  Adopter front-door messaging unchanged.
- ADR-096 §Part 3 (terminal-verdict claim
  `MAINTENANCE-MODE-VIBECODER`) is **partially superseded** by this
  ADR. The framework's operational mode is post-audit-SOTA-execution
  for the duration of this ADR.
- `docs/READINESS-STATUS.md` verdict transitions from
  `MAINTENANCE-MODE-VIBECODER` to
  `POST-AUDIT-SOTA-EXECUTION (roadmap 45-item burn)` —
  **DEFERRED** to PLAN-104 housekeeping plan (or any earlier
  `docs/` touch plan) per §Blast radius scoping. Verdict returns
  to `MAINTENANCE-MODE-VIBECODER` at sunset (also DEFERRED to a
  separate `docs/` touch plan). Doc state is INFORMATIONAL — this
  ADR is the canonical source of operational-mode truth from its
  ACCEPTED date forward regardless of `docs/READINESS-STATUS.md`
  staleness.

## Consequences

**Positive (+):**

- Closes lesson `maintenance_mode_fig_leaf` reincidence risk.
- PLAN-089/090 + FASE 3 (PLAN-092..095) + FASE 4 (PLAN-096..102) ship
  under honest doctrinal cover.
- Mechanical scope test prevents §exception-clause stretching for
  future plans (anti-fig-leaf guardrail).
- Sunset conditions are explicit + mechanically checkable, preventing
  this ADR from itself becoming a fig leaf.
- Preserves all positioning + risk disclosure already in ADR-096
  §Part 1+2 + README §Risks.

**Negative (-):**

- Introduces a new operational-mode name into the vocabulary
  (post-audit-SOTA-execution-mode). Documentation + CLAUDE.md drift
  cost.
- Cross-references ADR-096 + ADR-115 + ADR-085 + ADR-103 (the
  doctrine triangle becomes a quadrilateral). Adopters reading
  governance must traverse one more node.
- 12-18 sessions / 90-180 calendar days estimated lifetime — non-
  trivial doctrinal commitment.

**Neutral (~):**

- ADR-093 (60d refused-ADR moratorium) was already superseded by
  ADR-103 2026-05-03 — unaffected by this ADR.
- ADR-085 (Claude-only thesis) — unaffected.
- v2.0 trigger criteria (ADR-115 §exception #4) — unaffected.

## Blast radius

**L3+** — doctrinal scope; affects all future plan reviews + status
flips. Touches:

- This ADR (new).
- `.claude/adr/ADR-096-vibecoder-only-by-design.md` — append
  §Partial-supersession-notice block at top (link to ADR-124).
- `.claude/adr/ADR-115-post-sota-maintenance-mode.md` — append
  §Exception-#2-retirement-notice block.
- `docs/READINESS-STATUS.md` — verdict update **DEFERRED**: out of
  PLAN-103 sentinel scope (sentinel covers only `.claude/adr/**`).
  Tracked as follow-up housekeeping under PLAN-104 (or any earlier
  plan that touches `docs/`); NOT a blocking AC for ADR-124
  ACCEPTED status flip.
- `CLAUDE.md` §Current Work — operational-mode reference **DEFERRED**
  to next closeout (cache discipline — see lesson
  `gate_1_cache_discipline`); out of PLAN-103 sentinel scope.
- `CHANGELOG.md` — ADR-124 entry **in PLAN-103 ceremony commit
  body** (commit message references this ADR; no separate file edit
  in PLAN-103).

No `.claude/policies/`, no `.claude/hooks/`, no `SPEC/`, no workflow
file changes — purely doctrinal.

## Compliance checklist

| Item | Verification |
|---|---|
| ADR file present at canonical path | `test -f .claude/adr/ADR-124-post-audit-sota-execution-mode.md` |
| Status ACCEPTED | `grep '^status: ACCEPTED$' .claude/adr/ADR-124-*.md` |
| Codex R2 3-iter ACCEPT logged | thread ref recorded in §Related decisions |
| ADR-096 §Partial-supersession-notice present | `grep -l 'partially_supersedes.*ADR-096' .claude/adr/ADR-124*.md` |
| ADR-115 §Exception-#2-retirement-notice present | inverse cross-ref test |
| READINESS-STATUS.md verdict updated | **DEFERRED** — tracked as follow-up under PLAN-104 housekeeping OR any earlier `docs/` touch plan; NOT a blocking AC for ADR-124 ACCEPTED status flip |
| Scope test §Part 2 mechanically applicable | dry-run on PLAN-089/090/092 maps to TIER ≥1 OR AUTO-NN OR SEMI-NN; `maps_to_roadmap_items` frontmatter present |
| Sunset conditions §Part 3 mechanically checkable | each of 3 triggers names a canonical artifact + check command OR concrete threshold |
| `check-roadmap-closure.py` ledger of trigger #1 | `test -f .claude/scripts/check-roadmap-closure.py` OR PLAN-104 tracking entry |
| `docs/v2-friction-ledger.md` schema of trigger #2 | grep YAML record shape `- repo:` + `friction:` + `date:` |

## Related decisions

- ADR-096 — Vibecoder-only by design — **partially superseded** by this ADR (§Part 3 only)
- ADR-115 — Post-SOTA maintenance mode — **§exception #2 retired** by this ADR
- ADR-085 — Claude-only thesis (Session 67) — unaffected
- ADR-093 — 60d refused-ADR moratorium — already superseded by ADR-103
- ADR-103 — Calendar-gate final purge — supersedes ADR-093
- ADR-105 — Multi-LLM coordinated supersede (Codex R2 governance source)
- PLAN-084 evolution-roadmap.md — scope source (45 items, TIER 1-7)
- lesson `maintenance_mode_fig_leaf` — codifies the anti-pattern this ADR closes
- lesson `adr_supersession_drift` — governs supersession-scope discipline

## Codex MCP gate trail

- Cross-LLM revalidation: thread `019e215c-cff5-7ed3-a7f1-87e4b8f94439` (S115-cont) — P4 REFUTED.
- Master plan validation: thread `019e21ef-36d6-7083-82d6-d41b26b61a80` (S115-cont).
- This ADR R2 iter-1 NEEDS-FIXES (4 findings: 2 P1 + 2 P2): thread `019e2250-6e34-7b90-8440-75c429042118` (Session 117 Wave 1) — all 4 folded inline 2026-05-13.
- This ADR R2 iter-2 NEEDS-FIXES (4 findings: 1 P1 + 3 P2): thread continuation `019e2250-6e34-7b90-8440-75c429042118` — all 4 folded inline 2026-05-13 (scope-source path corrections + docs/READINESS-STATUS.md §Part 5 deferral + iter-3 pre-claim removal + roadmap sunset mechanical-only no-fallback).
- This ADR R2 iter-3 final **ACCEPT**: thread continuation `019e2250-6e34-7b90-8440-75c429042118` — verdict 2026-05-13: "ACCEPT — iter-2 fixes are folded; scope, sunset, cross-ref, and deferred blast-radius handling are now mechanically bounded enough for ADR-124 ACCEPTED."

## Authorization

PLAN-103 sentinel `.claude/plans/PLAN-103/architect/round-1/approved.md` +
detached `.asc` signature (Owner GPG 00000000).
