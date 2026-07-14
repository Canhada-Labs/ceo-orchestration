---
id: SP-045
skill_slug: parallelization-by-default
archetype: none   # core-skill fold, CEO-proposed — SP-018/SP-042 precedent (no owning archetype)
proposed_at: 2026-07-13T23:07:00Z
source_lessons:
  - plan-157-w1-fold-dynamic-workflow-mode
scan_injection_pass: true
diff_size_added: 46
diff_size_removed: 0
sha256_of_diff: 1a140f1993b98441218098df6d436d33bbeb623022a0e32245e7955e56a66134
sha256_of_staged: 280470ba6f887663c7861b27819496d3f197f7ae86e3b113d37f8fa6fd3a4a78
claims_declared: false
status: proposed
shadow_mode: false
soak_waiver: owner-ratified-at-signing   # PLAN-157 OQ4 (Owner tie-break S270) via SP-042/S264-OQ4 precedent
proposal_type: fold-distill-append
patch_source: inline diff fence (below)
---

# SP-045 — fold `dynamic-workflow-mode` → `core/parallelization-by-default` (PLAN-157 W1)

**Target:** `.claude/skills/core/parallelization-by-default/SKILL.md`
**Source:** the agents-meta squad's `dynamic-workflow-mode` skill
(pre-fold source pin sha256
`ef29bc7cbe32473cb250f0cf305ef64ba27ce95371650629a4d1caa895a73f70`),
sunset in the same W1 ceremony per OQ2 (git-history-only deletion +
pointer in the plan).
**Kind:** distilled append — PURE ADDITION, zero frontmatter change
(the cleanest fold of the W1 set). Companion: SP-046 folds the second
agents-meta source into this same target, applied after this SP.

## Rationale

PLAN-157 W1 (Owner OQ1-OQ4 ratification, S270): the `agents-meta`
squad folds into a named core target, then the scaffold sunsets. The
target is the CEO framework-wide dispatch primitive (When to invoke /
Decomposition algorithm / When NOT to dispatch parallel); the source's
harness decision tree — one-shot inline vs task-local harness vs shared
skill — is the natural adjacent doctrine for when dispatch alone is not
the answer. Co-locating both agents-meta sources here preserves their
mutual cross-reference without any domain path (tier-check-safe).

**What survives (the distill, ~654 est tokens):** the 5-field core
contract (Objective/Inputs/Outputs/Eval/Handoff), the 5-branch decision
tree, the shared-skill promotion rule (at least 2 of 5 criteria), the
eval-gate table compressed to one line per work type, and the 5
anti-patterns.

**What is dropped, and why:** the fill-in harness markdown template
block (a form, rederivable from the 5-field contract); the
observable-checkpoints prose (the plan-lifecycle / scratchpad /
audit-log surfaces are already documented framework doctrine — kept as
a one-line parenthetical in branch 4); the output standard and the
changelog + import attestation (bookkeeping).

## Budget evidence (repo-canonical chars/4 estimate)

- Distilled section: 2,617 B ≈ 654 tokens. Post-fold body est
  ≈ 2,476 tokens (pre-fold body_est 1,822 + 654) — fits inside the
  ALREADY-DECLARED `context_budget_tokens: 2500` with zero frontmatter
  change; post-fold file 10,878 B ≈ 2,719 tokens full-file vs the
  30,000 per-skill schema ceiling.
- Live profile sum unaffected today: trading-readonly
  `context_total_tokens: 10200` vs cap 30,000 (19,800 live headroom).
- Tier-boundary safety: appended prose carries no
  `domains/<x>/skills/<y>` or `../../domains/` reference (asserted at
  build time with the `_DOMAIN_REF_RE` pattern); no core file added —
  `check-tier-boundaries.py` stays 92-files clean.

## Soak waiver

WAIVED per the Owner's OQ4 ratification (S270 structured tie-break,
SP-042/S264-OQ4 precedent): content in-tree and import-attested since
2026-07-08; zero new doctrine. Owner ratifies by detach-signing this
proposal. `sha256_of_staged` pins the exact post-apply file.

## Apply route

This diff is a pure append — pipeline-expressible via
`_apply_unified_diff`. It nonetheless rides the W1 sentinel ceremony
Owner-shell for commit-atomicity with its source-dir sunset and with
SP-046 (which applies on top of this SP's staged result). Ordering is
load-bearing: SP-045 before SP-046.

## Diff

```diff
--- a/.claude/skills/core/parallelization-by-default/SKILL.md
+++ b/.claude/skills/core/parallelization-by-default/SKILL.md
@@ -174,3 +174,49 @@
   speed up Wave 1-3" — anti-ceo-overhead hook is the mitigation
 - ADR-046 sub-agent dispatch protocol (file-assignment-per-agent + result-
   contract)
+
+## Task-Local Harness Discipline — folded from `dynamic-workflow-mode` (PLAN-157 W1)
+
+Dispatch answers "who does the work in parallel"; this section answers "does
+the work deserve a custom harness at all" — the case where an agent generates
+a small task-local loop, evaluator, crawler, fixture generator, or watcher
+instead of following a fixed command flow (distilled from the sunset
+agents-meta squad's `dynamic-workflow-mode` skill; full text in git history).
+
+**Decision tree — how much harness does this deserve?**
+
+1. One-shot task → keep it inline; do not invent a harness.
+2. Repeated task, changing inputs → task-local harness in a plan-local or
+   scratchpad working area — never a canonical path.
+3. Repeated task across teammates or repos → extract into a shared skill.
+4. Task with external state, queueing, or approvals → add observable
+   checkpoints (plan file, plan-scoped scratchpad, task board, audit log)
+   before adding more automation.
+5. Task with a safety risk → eval gate + human merge gate before anything
+   autonomous.
+
+**Core contract** — every harness declares five fields before any code:
+Objective (what it owns and what it explicitly does NOT own); Inputs (files,
+URLs, data sources, credentials policy); Outputs (commits, reports, status
+files, checkpoints); Eval (at least one pass/fail check tied to the task, not
+merely "it ran"); Handoff (what happened, what is blocked, how to resume).
+
+**Eval gate per work type:** code feature → focused test + lint + one
+integration path; UI/dashboard → browser smoke + screenshot + overflow/error
+check; agent workflow → fixture transcript or seeded work item with expected
+routing; research/content → claim checklist + publish-ready outline;
+integration → dry-run + config validation + no-secret scan. A workflow is not
+reusable until another teammate can rerun its eval.
+
+**Promote to a shared skill only when at least two of:** the same workflow
+recurs across sessions/repos/teams; it needs specific tool or safety
+sequencing; failures repeat because operators skip a gate; it has a stable
+input/output contract; it benefits from a shared status board or handoff. A
+new skill is canonical-guarded — it lands through the import gate and
+`/skill-review`, never by direct write.
+
+**Anti-patterns:** scripts that hide the real decision logic from the
+operator; treating "dynamic workflow" as permission to skip tests; one-off
+docs when a shared skill or status artifact is the real deliverable; multiple
+agents with no ownership, merge gate, or conflict policy; private data
+leaking into committed artifacts.
```

## Verification

- `sha256(SKILL.md post-apply) == sha256_of_staged` (asserted by the
  W1 landing script before commit; this is also SP-046's declared base).
- `python3 .claude/scripts/check-tier-boundaries.py` → clean, exit 0
  (92 files scanned; no core file added).
- `python3 .claude/scripts/smart-loading-resolver.py resolve --json` →
  `context_total_tokens` ≤ 30000 (10,200 today).
- `python3 .claude/scripts/lint-skills.py` → zero ERROR lines.
- Full PLAN-157 per-wave Check set rides the W1 ceremony commit.
