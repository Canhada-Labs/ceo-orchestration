---


id: SP-017
skill_slug: chaos-and-resilience
archetype: chaos-engineer
proposed_at: 2026-04-28T00:00:00Z
source_lessons:
  - plan-045-session-46-f-15-05-supplement
scan_injection_pass: true
diff_size_added: 24
diff_size_removed: 0
sha256_of_diff: PENDING_ON_OWNER_SIGN
claims_declared: false
status: promoted
approved_by: 0000000000000000000000000000000000000000
applied_at: 2026-04-21T12:41:05Z
promoted_at: 2026-04-21T13:37:10Z
shadow_mode: false
---
# SP-017 — chaos-and-resilience adopter note supplement

**Target:** `.claude/skills/core/chaos-and-resilience/SKILL.md`
**Archetype:** chaos-engineer
**Kind:** adopter cross-link supplement (addition — no rewrites)
**Depends-on:** SP-006 promote (2026-04-27); SP-017 signs 2026-04-28+

## Rationale

SP-006 (shadow-applied 2026-04-20) carries the adopter note that
PLAN-045 Session 45 F-15-05 rewrite was BLOCKED by ADR-031 defense-
in-depth. That blockage was correct; the rewrite would have been
redundant with SP-006.

PLAN-045 Session 46 Phase 6 re-audit (when run) surfaces a second-
order gap: the chaos-and-resilience skill body does NOT yet cross-
link to the PLAN-045 F-15 chaos-scenarios catalog staged in
`.claude/plans/PLAN-045/re-audit/chaos-scenarios.md` (Session 44
phase 6 artifact). Adopter-facing adoption-test failures should
point here.

This SP adds that cross-link. Pure addition; SP-006 carries the
primary rewrite and this SP carries the adopter-observability
follow-on. Dependency: SP-006 must promote first (2026-04-27)
before SP-017 can sign (2026-04-28+).

## Provenance note

Draft authored Session 46 by CEO autonomously per PLAN-045
NEXT-TERMINAL-PROMPT-100.md Fase 2.2. Unsigned (Owner signs at
Session 47 ceremony 2026-04-28+ after SP-006 promote). Diff is a
pure addition (append-only) and applies via `skill-patch-apply.py`.

## Proposed diff

```diff
--- a/.claude/skills/core/chaos-and-resilience/SKILL.md
+++ b/.claude/skills/core/chaos-and-resilience/SKILL.md
@@ -462,0 +462,24 @@
+
+### Adopter observability cross-link (PLAN-045 F-15-05 supplement)
+
+When evaluating a framework installation's resilience posture,
+ground the assessment in the PLAN-045 chaos-scenarios catalog:
+`.claude/plans/PLAN-045/re-audit/chaos-scenarios.md` (if present
+— staged Session 44 phase 6). The catalog enumerates:
+
+- 12 shipped invariants (hook fail-open, filelock timeout, audit-
+  log sidecar rotation, kill-switch precedence, ...)
+- 8 observed-but-not-tested scenarios (rotation-window file
+  deletion, concurrent sigchain append, ...)
+- 3 explicit ADR-055 §Out-of-scope gaps (key theft, rollback
+  restore, tail truncation)
+
+Adopter recipe when the skill is spawned for a resilience review:
+
+1. Read the shipped-invariants list; match against the adopter's
+   target project's documented invariants (if any).
+2. Flag gaps in the observed-but-not-tested list as P1 work for
+   the adopter's hardening sprint (not a ship blocker).
+3. Explicitly call out the 3 ADR-055 gaps if the adopter has
+   regulatory requirements for tamper-evidence beyond the per-
+   file chain.
+
+Cross-ref: SP-006 (primary adopter note) + `docs/HONEST-
+LIMITATIONS.md` §residual risks.
```
