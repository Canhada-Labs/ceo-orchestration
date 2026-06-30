---


id: SP-009
skill_slug: code-review-checklist
archetype: code-reviewer
proposed_at: 2026-04-20T21:40:00Z
source_lessons:
  - plan-044-p0-12-code-review-checklist
scan_injection_pass: true
diff_size_added: 21
diff_size_removed: 0
sha256_of_diff: a922cf8756e184ed3718ad39e7169a6d37fdd231170f4da9c84a9036398f13e7
claims_declared: false
status: promoted
approved_by: 0000000000000000000000000000000000000000
applied_at: 2026-04-20T15:58:37Z
promoted_at: 2026-04-21T13:37:10Z
shadow_mode: false
---
# SP-009 — skill patch proposal

**Target:** `.claude/skills/core/code-review-checklist/SKILL.md`
**Archetype:** code-reviewer
**Kind:** PLAN-044 P0-12 SKILL.md adopter-note append (append-only)

## Rationale

PLAN-044 P0-12 closure. The §Why (pre-PLAN-019 evidence) subsection cites an internal framework plan that a fresh-install adopter would not recognise. Rather than rewriting the citation in-place (which would shift line numbers and invalidate the validated position-stable hunk plus need a non-additive edit under ADR-031), this proposal appends a disclaimer pointing out the single internal residue and suggesting a reader-side substitution. The residue is one word (`pre-PLAN-019`) — a full non-additive rewrite is over-kill for the blast radius. The disclaimer also explicitly distinguishes load-bearing ADR references from leak-prone PLAN references, which answers a predictable adopter question.

## Provenance note

This proposal was hand-authored via `/tmp/gen_sp_006_015.py` as part of
the PLAN-044 Phase 5 / P0-12 SKILL.md generalisation sweep (PLAN-045
Wave 4 equivalent, Session 41 handoff). The diff is a **pure addition**
— append-only — and applies cleanly via `skill-patch-apply.py` which
collects `+`-prefixed lines from the ```diff fence below. No code
execution, no automated mutation; the amendment is a doc-only adopter-
note section appended to the end of the target `SKILL.md`. Stdlib-only
generator; no network; no third-party deps.

Rollback-safe: if promote fails, reverting removes ONLY the added
lines. No other file is touched. No state change. This is what shadow
mode guarantees per ADR-031.

## Proposed diff

```diff
--- a/.claude/skills/core/code-review-checklist/SKILL.md
+++ b/.claude/skills/core/code-review-checklist/SKILL.md
@@ -286,3 +286,24 @@
 - `.claude/skills/core/pre-plan-brainstorm/SKILL.md` — spec.md
   artifact that Pass 1 consumes
 
+## Adopter Note — Framework-Internal References (PLAN-044 P0-12)
+
+The §Why (pre-PLAN-019 evidence) subsection refers to
+`PLAN-019`, which is an internal `ceo-orchestration` framework
+plan (the Sprint-17 remediation wave) — **not** a plan in your
+adopter project. The historical point being made ("multiple
+incidents where a review pass accepted the implementer's self-
+report and a later CI failure surfaced the gap") generalises
+cleanly — but the PLAN-019 citation itself does not.
+
+When you read that line in an adopter context, substitute
+"before we introduced the two-pass adversarial review frame"
+or "prior to the audit that established the adversarial
+reviewer pattern" — the narrative survives; the PLAN-NNN label
+does not.
+
+Other internal references in this skill that are load-bearing
+for framework self-consistency (ADR-052, ADR-058, ADR-031,
+ADR-018/019) are INTENTIONAL — they point at first-class
+governance contracts shipped alongside the skill. The PLAN-019
+reference is the only residue that leaks adopter-trippingly.
```
