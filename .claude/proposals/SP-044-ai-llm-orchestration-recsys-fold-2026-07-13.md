---
id: SP-044
skill_slug: ai-llm-orchestration
archetype: none   # core-skill fold, CEO-proposed — SP-018/SP-042 precedent (no owning archetype)
proposed_at: 2026-07-13T23:06:00Z
source_lessons:
  - plan-157-w1-fold-recsys-pipeline-architect
scan_injection_pass: true
diff_size_added: 39
diff_size_removed: 1
sha256_of_diff: c5a309691533e99e88a9562f5c5b59647a0246e1509fc5eb7d44b484a3651ae6
sha256_of_staged: dded58b68b243e8e58fb273fb498e194b7107ddf1a471bdb44d471e8102fbe5b
claims_declared: false
status: proposed
shadow_mode: false
soak_waiver: owner-ratified-at-signing   # PLAN-157 OQ4 (Owner tie-break S270) via SP-042/S264-OQ4 precedent
proposal_type: fold-distill-append
patch_source: inline diff fence (below)
---

# SP-044 — fold `recsys-pipeline-architect` → `core/ai-llm-orchestration` (PLAN-157 W1)

**Target:** `.claude/skills/core/ai-llm-orchestration/SKILL.md`
**Source:** the architecture squad's `recsys-pipeline-architect` skill
(pre-fold source pin sha256
`8e39ef7f3d07325016f341bf30c58c7c6a7492441e248a287e7b214fc4929de7`),
sunset in the same W1 ceremony per OQ2 (git-history-only deletion +
pointer in the plan).
**Kind:** distilled append + one-line declared-budget bump.

## Rationale

PLAN-157 W1 honors the plan's own in-wave record: "`recsys-pipeline-
architect` does NOT fit `core/architecture-decisions`' token budget —
pick target in-wave." The picked target is `core/ai-llm-orchestration`:
the source is explicitly "the plumbing AROUND a scoring function",
including RAG retrieval reranking and LLM-judge scoring, and the target
already owns LLM pipeline/output doctrine (LLM Output Reliability
Patterns, Council Output Findings). Scope-mismatch runners-up
considered and rejected: `parallelization-by-default` (agent-dispatch
primitive, not data-serving) and `state-machines-and-invariants`
(state doctrine, not ranking-pipeline shape).

**What survives (the distill, ~566 est tokens):** the six-stage
Source→Hydrator→Filter→Scorer→Selector→SideEffect table (compressed) +
the why-order-is-fixed bullets; the three load-bearing trade-offs as
one-liners (single vs multi-action; isolated vs joint; online/offline/
hybrid); the hard rules — no invented benchmarks, surface every
trade-off, filter order load-bearing, side effects never block — and
the honest attribution / no-trademark rule.

**What is dropped, and why:** the 8-step interview workflow (process
scaffolding a CEO-context skill re-derives from the stage table); the
filter/scorer cookbook detail (worked-example depth, not doctrine);
activation/do-not-activate prose and the checklist bulk (redundant with
the compressed table + rules); the changelog + import attestation
(source-file bookkeeping).

## Budget evidence (repo-canonical chars/4 estimate)

- Distilled section: 2,266 B ≈ 566 tokens. Post-fold file: 32,434 B
  ≈ 8,108 tokens full-file; post-fold body est ≈ 7,628 tokens
  (pre-fold body_est 7,062 + 566) — the largest core candidate, still
  22,372 tokens under the 30,000 per-skill schema ceiling
  (`repo-profile-skill-binding.schema.json`).
- Declared `context_budget_tokens` bumped 1000 → 1150 (scout-measured
  recommendation; declared field = progressive-disclosure active-set
  contribution estimate, not body size).
- Live profile sum unaffected today: trading-readonly
  `context_total_tokens: 10200` vs cap 30,000 (19,800 live headroom);
  this target is not in the current active set.
- Tier-boundary safety: appended prose carries no
  `domains/<x>/skills/<y>` or `../../domains/` reference (asserted at
  build time with the `_DOMAIN_REF_RE` pattern); no core file added —
  `check-tier-boundaries.py` stays 92-files clean.

## Ceremony caution — stale shadow artifact

The target dir carries `SKILL.md.shadow.md` (5,862 B vs 30,167 B main
— a frontmatter-era artifact, not a live soak; verified on disk
2026-07-13). Reconcile/remove it in the SAME W1 ceremony so the shadow
diff does not false-flag the fold. `sha256_of_staged` above pins
`SKILL.md` only.

## Soak waiver

WAIVED per the Owner's OQ4 ratification (S270 structured tie-break,
SP-042/S264-OQ4 precedent): content in-tree and import-attested since
2026-07-08; the fold adds zero new doctrine. Owner ratifies by
detach-signing this proposal. `sha256_of_staged` pins the exact
post-apply file.

## Apply route

The appended-section hunk is pipeline-expressible (append-only); the
one-line `context_budget_tokens` bump is not (pipeline
`_apply_unified_diff` is append-only by design and cannot express a
removal — SP-042). Applied Owner-shell inside the W1 sentinel ceremony;
staged-file hash asserted before commit. Source-dir sunset + shadow-file
removal ride the same ceremony as separate Owner-shell steps.

## Diff

```diff
--- a/.claude/skills/core/ai-llm-orchestration/SKILL.md
+++ b/.claude/skills/core/ai-llm-orchestration/SKILL.md
@@ -22,7 +22,7 @@
 priority: 5
 risk_class: medium
 stack: [python, typescript]
-context_budget_tokens: 1000
+context_budget_tokens: 1150
 inactive_but_retained: false
 repo_profile_binding:
   frontend: {active: true, priority: 6}
@@ -618,3 +618,41 @@
 - **"The bill is fine, no need for the FinOps section"** — FinOps
   drift is the leading indicator for a regressed prompt. Skipping the
   section is skipping the leading indicator.
+
+## Ranking/Feed Pipeline Shape — folded from `recsys-pipeline-architect` (PLAN-157 W1)
+
+When the task is "pick the top K items for a (user, context)" — RAG retrieval
+reranking, notification/task prioritisation, feed or search ranking — the
+plumbing around the scoring function follows six composable stages, in fixed
+order (distilled from the sunset architecture squad's
+`recsys-pipeline-architect` skill; full text in git history):
+
+| # | Stage | Job | Concurrency |
+|---|---|---|---|
+| 1 | Source | retrieve candidates from one or more origins | parallel fan-out |
+| 2 | Hydrator | attach the metadata later stages need | parallel |
+| 3 | Filter | drop what must never be shown | sequential |
+| 4 | Scorer | score survivors — a chain, not one scorer | sequential |
+| 5 | Selector | sort by final score, take top K | single op |
+| 6 | SideEffect | cache served ids, log, emit events | async — never blocks |
+
+Why the order is fixed: source before hydrate (know the candidates before
+paying to enrich them); hydrate before filter (filters need attributes the
+source did not return); filter before score (scoring is the expensive stage);
+select after score (keeps scoring deterministic and cacheable); side effects
+last and async (bookkeeping never sits in the latency path).
+
+Trade-offs to surface explicitly — never default silently: **single relevance
+score vs multi-action prediction** (predict P(action) per action and combine
+with serving-time weights — re-tune without retraining; weights can be
+negative); **candidate isolation vs joint scoring** (isolated = deterministic
+and cacheable, the default; joint only with a specific reason such as
+batch-aware diversity); **online vs offline vs hybrid serving** (online
+~100-300 ms budget is the default; hybrid = retrieve offline, rank online).
+
+Hard rules: never invent benchmark numbers ("it depends; measure it");
+filter order is load-bearing — cheap/universal before expensive/personal;
+side effects are fire-and-forget; scaffolds must actually run, no pseudocode.
+Attribute the pattern honestly: the six-stage shape was popularised by the
+open-sourced "For You" ranking algorithm (Apache-2.0); no trademark or brand
+borrowing — use neutral names ("candidate pipeline", "ranking pipeline").
```

## Verification

- `sha256(SKILL.md post-apply) == sha256_of_staged` (asserted by the
  W1 landing script before commit).
- `python3 .claude/scripts/check-tier-boundaries.py` → clean, exit 0
  (92 files scanned; no core file added).
- `python3 .claude/scripts/smart-loading-resolver.py resolve --json` →
  `context_total_tokens` ≤ 30000 (10,200 today).
- `python3 .claude/scripts/lint-skills.py` → zero ERROR lines.
- `SKILL.md.shadow.md` removed in the same ceremony (stale-artifact
  reconcile); full PLAN-157 per-wave Check set rides the W1 commit.
