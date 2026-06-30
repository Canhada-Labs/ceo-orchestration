---


id: SP-007
skill_slug: ai-llm-orchestration
archetype: ai-orchestration-engineer
proposed_at: 2026-04-20T21:40:00Z
source_lessons:
  - plan-044-p0-12-ai-llm-orchestration
scan_injection_pass: true
diff_size_added: 21
diff_size_removed: 0
sha256_of_diff: 62b649aea9f905e0c4bb7bf6f3521cf47dfe12725fc89413e60a59de65ad4387
claims_declared: false
status: promoted
approved_by: 0000000000000000000000000000000000000000
applied_at: 2026-04-20T15:58:37Z
promoted_at: 2026-04-21T13:37:10Z
shadow_mode: false
---
# SP-007 — skill patch proposal

**Target:** `.claude/skills/core/ai-llm-orchestration/SKILL.md`
**Archetype:** ai-orchestration-engineer
**Kind:** PLAN-044 P0-12 SKILL.md adopter-note append (append-only)

## Rationale

PLAN-044 P0-12 closure. `ai-llm-orchestration/SKILL.md` carries hard-coded originating-project metrics (`src/ai/`, `18 files, ~9.3K lines`) in its YAML description field and finance-specific examples throughout. This proposal appends a generalisation note — the stale metric and domain framing are preserved for worked-example value while the note redirects the adopter to the archetype-level reading. Pure-addition keeps the frontmatter description (which is load-bearing for skill auto-trigger via `claude-code` description matcher) untouched. Frontmatter rewrite is flagged separately for CEO (see SUMMARY).

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
--- a/.claude/skills/core/ai-llm-orchestration/SKILL.md
+++ b/.claude/skills/core/ai-llm-orchestration/SKILL.md
@@ -98,3 +98,24 @@
 3. Output format must be parseable JSON schema
 4. Temperature should be low (0.1-0.3) for financial analysis
 5. Never ask LLM to "be creative" with market data
+## Adopter Note — Stale Metric + Domain Framing (PLAN-044 P0-12)
+
+The frontmatter description names `src/ai/` and `18 files,
+~9.3K lines` — both are originating-project metrics from the
+`ceo-orchestration` dogfood corpus circa 2025-Q1 and should not
+be treated as normative for your adopter codebase.
+
+Likewise, the Fail-Fast Rule's mention of `proprietary market
+data` and the final-section mention of `financial analysis` /
+`market data` bias the rubric toward fintech. The **patterns**
+(multi-model council, snapshot minimisation, injection guard,
+usage-limiter short-circuit, prompt templates kept out of the
+deploy path, confidence-threshold gating) apply to any LLM-in-
+the-loop system regardless of domain.
+
+If your project is not finance-adjacent, replace
+"market data" / "signal" with your own domain nouns when
+spawning an archetype that loads this skill. File-count and
+line-count figures are nominal; what matters is that the seven
+responsibilities in §Key modules each live in a dedicated
+module, not the absolute count.
```
