---
id: ADR-115
title: Framework enters post-SOTA maintenance mode after PLAN-084
status: ACCEPTED-AMENDED
amended_by: [ADR-124]
proposed_at: 2026-05-12
proposed_by: CEO (PLAN-084 AC8 + R1 CR-P1-9 ADR pinning + QA-P2 timing)
related_plans: [PLAN-051, PLAN-058, PLAN-084]
related_adrs: [ADR-093]
supersedes: []
authorization: PLAN-084 Phase E sentinel
note: |
  Pre-allocated at Wave 0; populated at Phase E closeout with final
  numbers + 3 canonical artifact pointers. PRE-WAVE-0 frontmatter
  documented; Phase E synthesis fills body.
---

# ADR-115 — Framework enters post-SOTA maintenance mode after PLAN-084

## Exception-#2-retirement-notice (PLAN-103 FASE 0, 2026-05-13)

**§exception #2 ("Roadmap items in PLAN-085+ burn-down — already-
debated; small focused plans")** is **RETIRED** as of 2026-05-13 by
[ADR-124](ADR-124-post-audit-sota-execution-mode.md). The
roadmap-item burn-down scope is now governed by ADR-124 §Part 2
"Scope test (mechanical)" which requires:

1. Plan deliverable maps to a numbered TIER 1-7 item in
   `.claude/plans/PLAN-084/canonical/PLAN-084-evolution-roadmap.md`,
   OR an `AUTO-*` / `SEMI-*` item in
   `.claude/plans/PLAN-084/automation-gap-roadmap.yaml`, OR a
   finding ID in
   `.claude/plans/PLAN-084/canonical/PLAN-084-findings-master.jsonl`
   (P0/P1 only); AND
2. Plan frontmatter declares `maps_to_roadmap_items:` listing the
   concrete mapped IDs (status flip `draft → reviewed` BLOCKED
   without this field).

**§exception #1 (P0 security hotfix), §exception #3 (adopter-
blocking install bug), §exception #4 (v2.0 trigger) REMAIN IN
FORCE.** The §Detection-decay monitor section likewise remains
in force unchanged.

At ADR-124 sunset (per ADR-124 §Part 3), §exception #2 may be
reinstated by a successor ADR OR allowed to lapse permanently.

See ADR-124 §Part 4 for the full relationship spec.

## Context (pre-allocated at Wave 0; finalized at Phase E)

PLAN-084 (SOTA-finalization audit) is the final big plan of framework's
evolution phase. Its 3 canonical artifacts answer:

1. **Does it work correctly?** → `findings-master.jsonl` (bugs + smells + drift)
2. **Is it using Claude+Codex at 100%?** → `capability-gap-report.md`
3. **What remains to reach SOTA god-mode?** → `evolution-roadmap.md`

After PLAN-084 ships, framework formally transitions to **post-SOTA
maintenance mode**:

- Bug fixes only via PLAN-085+ burn-down
- Roadmap items already-debated (zero new design debate)
- No new feature creep, no new evolution debates
- No new audit of comparable scope for ≥12 months
- v2.0 only after Owner produces ≥10 concrete friction findings from
  5-repo real-world usage (per PLAN-083 §8 v1.1 trigger doctrine, extended)

## Decision (pre-allocated; populated at Phase E)

**Status: PROPOSED → ACCEPTED at Phase E closeout 2026-05-12.**

### Final numbers (post Wave D.1+D.2+D.3)

- Total unique findings: 236 (25 P0 + 30 P1 + 14 P2 + 4 P3 + 163 unclassified)
- Codex-adjudicated: 73 (53 CONFIRM + 12 REFUTE + 7 DEBATE + 1 BLINDSPOT-FLAG)
- Veto-case tagged: 26 (B=10, D=6, C=5, F=4, E=1)
- Capability axes audited: 12 mandatory + 2 optional = 14 total
- Evolution-roadmap items: 45 across 7 tiers
- Automation gap conversions: 13 priority (AUTO-01..AUTO-10 + SEMI-11/12/13)

### 3 canonical artifact SHA-pins (post-ceremony)

- findings-master.jsonl: SHA pinned at commit ceremony
- capability-gap-report.md: SHA pinned at commit ceremony
- evolution-roadmap.md: SHA pinned at commit ceremony

(Exact SHAs land in commit message; this ADR survives the commit so
in-document SHA would create circular self-reference.)

### Exception clauses for maintenance-mode boundaries

Per PLAN-051 §3 doctrine + PLAN-083 §8 v1.1 trigger doctrine extension,
exceptions allowed only for:

1. **P0 security findings** — burn-down via PLAN-085 + critical hotfix patches.
2. **Roadmap items in PLAN-085+ burn-down** — already-debated; small focused plans.
3. **Adopter-blocking install bugs** — vibecoder TTV ≤5min must hold; cap-table
   ship + first-run-wizard auto-spawn fixes are TIER-1.
4. **v2.0 trigger:** ≥10 concrete Owner-friction findings from 5-repo real-world
   usage (PLAN-083 §8 extended).

### Detection-decay monitor (per R1 TDE-P2-6)

**Expected-silent audit actions** (Wave 0.5+0.8 newly registered; should fire
only at expected ceremony points):

- canonical_edit_attempted / canonical_edit_blocked: fire at adopter canonical
  attempts; expected non-zero per maintenance-mode ceremony.
- sentinel_created / sentinel_verified: fire at every sentinel ceremony.
- gpg_signed / gpg_verified: fire at every GPG ceremony.
- wave_artifact_written: NO LONGER FIRES post-PLAN-084 (Wave 0.10 staging
  artifact integrity model was PLAN-084-specific; defer to PLAN-NNN audits).
- pair_rail_outgoing_redaction_applied: should fire on EVERY Codex egress
  (codex_invoke.py + check_pair_rail.py wired). Zero firings = telemetry
  regression.
- estimate_refined: should fire when CEO updates plan estimate post-phase
  milestone (Bayesian-style). Zero firings post-PLAN-085 = AC12d regression.

**Unexpected-silent**: if pair_rail_outgoing_redaction_applied stays at 0
emissions for 7+ days, ADR-114 enforcement is broken — trigger PLAN-NNN
investigation.

### What's NEXT (PLAN-085+)

See `.claude/plans/PLAN-084/canonical/PLAN-084-evolution-roadmap.md` for
full 45-item TIER 1-7 breakdown. PLAN-085 (immediate Q3 sprint) covers TIER
1 audit P0 burn-down (12 items, ~$50-100 / 8-12h CEO / 1-2 GPG).

### Authorization

PLAN-084 Phase E sentinel `phase-e-approved.md` + .asc detached signature
(Owner GPG) + 3 detached .asc on canonical artifacts.

Body will include:
- Total findings count (P0/P1/P2/P3 breakdown)
- Total capability axes audited (12 mandatory + 2 optional)
- Total evolution-roadmap items (HIGH/MEDIUM/LOW leverage)
- 3 canonical artifact SHA-pin
- Exception clauses for maintenance-mode boundaries
- §Detection-decay monitor per R1 TDE-P2-6

## Consequences (preview)

- PLAN-085+ are smaller, focused bug-fix plans
- Architect skill / `architect` slash command may be feature-frozen
  pending evolution-roadmap items completion
- No new ADRs except those mandated by PLAN-085+ burn-down

## Authorization

PLAN-084 Phase E sentinel `approved.md` (single sentinel covering all
3 canonical artifacts + this ADR per AC7 atomic commit).
