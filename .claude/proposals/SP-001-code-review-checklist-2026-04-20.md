---

id: SP-001
skill_slug: code-review-checklist
archetype: code-reviewer
proposed_at: 2026-04-20T09:16:54Z
source_lessons:
  - session-38-cont-sp-001-code-review-checklist
scan_injection_pass: true
diff_size_added: 21
diff_size_removed: 0
sha256_of_diff: 8fef5a17b6e4f2f8e1613c25f3112816b187cb37de4470fd2977a9a4d5944a49
claims_declared: false
status: promoted
approved_by: 0000000000000000000000000000000000000000
applied_at: 2026-04-20T09:58:51Z
promoted_at: 2026-04-21T13:37:10Z
shadow_mode: false
---
# SP-001 — skill patch proposal

**Target:** `.claude/skills/core/code-review-checklist/SKILL.md`  
**Archetype:** code-reviewer  
**Kind:** manual cross-link closure (Session 38 continuation)

## Rationale

PLAN-038 Wave C Phase 2 cross-link reverse amendment. PROTOCOL.md + docs/HONEST-LIMITATIONS.md already reference this skill unidirectionally (commit e7c4c0a, 2026-04-19); this patch closes the loop so the inference path carries the fluency-bias rubric when the code-reviewer archetype is spawned. Ultimate-guide audit BORROW-4. Anthropic fluency research: 5.2 pp less scrutiny for polished outputs vs rough drafts.

## Provenance note

This proposal was hand-authored via `/tmp/gen_sp_proposals.py` as part of the Session 38 100%-closure sweep (Owner autorizou in-chat 2026-04-20). The diff is a pure addition — append-only — and applies cleanly via `skill-patch-apply.py` which collects `+`-prefixed lines from the ```diff fence below. No code execution / automated mutation; the amendment is a doc-only cross-link to already-shipped artifacts (PROTOCOL.md §Artifact Paradox, docs/OWASP-LLM-TOP-10.md + benchmark, reference/*.yaml under frontend skills).

## Proposed diff

```diff
--- a/.claude/skills/core/code-review-checklist/SKILL.md
+++ b/.claude/skills/core/code-review-checklist/SKILL.md
@@ -286,3 +286,24 @@
 - `.claude/skills/core/pre-plan-brainstorm/SKILL.md` — spec.md
   artifact that Pass 1 consumes
 
+### Artifact Paradox (PROTOCOL.md §Artifact Paradox)
+
+Adopt the Artifact Paradox mindset explicitly: polished, confident,
+well-formatted agent output receives ~5.2 pp **less** critical scrutiny
+than rough drafts (Anthropic fluency research, ultimate-guide audit
+BORROW-4). Same-LLM reviewers inherit the bias. When an agent returns
+a confident "all done, tests green" with clean prose — **treat that as
+a red flag for unreviewed gaps**, not as a signal of quality.
+
+Concretely, during review:
+
+- Focus review time on what's **absent** (missing edge-case tests,
+  unhandled null paths, skipped invariants) more than on what's
+  present.
+- Verify against code with **more** rigor when the agent output is
+  fluent, not less. Fluency suggests the author spent cycles on
+  polish instead of on gaps.
+- Do not let a well-written summary substitute for reading the diff
+  line-by-line.
+
+Cross-ref: `PROTOCOL.md` §Artifact Paradox + `docs/HONEST-LIMITATIONS.md` §4.
```

