<!--
generated: 2026-07-06 (S261)
by: list-materialization agent under PLAN-153 Wave G contract-materialization
source-of-truth: .claude/plans/PLAN-153/artifacts/ecc-skill-matrix.md (97 ADAPT rows)
  + .claude/plans/PLAN-153-ecc-comparative-uplift.md §Wave G + §Deferred
upstream: github.com/affaan-m/ecc @ 81af4076 (repo-level MIT; per-file license
  verified at clone time via the NOTICE ledger — no local clone at materialization)
status: contract materialized; NOT yet dispatched. Each row rides SP-NNN +
  /skill-review + the check-imported-skill.py import gate (Wave D/G rule).
-->

# PLAN-153 Wave G — materialized merge list (25 ADAPT enrichments)

## Why this file exists

PLAN-153 §Wave G says "~25 enrichments, no new files (full list in artifacts)"
but no discrete 25-row list existed — only 18 plan-named merges (in prose) and
the 97-row ADAPT pool in `ecc-skill-matrix.md`. A wave cannot be dispatched
against an unmaterialized contract: each agent needs an exact
`(upstream skill → target skill-on-disk)` pair, and the §Deferred bookkeeping
(`72 = 97 − 25`) must reconcile to zero drift. This file is that contract.

## Method (deterministic)

1. **Rows 1–18** are the plan-named merges, ratified by the round-1 debate,
   transcribed **verbatim** — never substituted.
2. **Rows 19–25** (the `+7`) selected from the remaining 79 ADAPT rows by the
   fixed doctrine: quality **q5 first, then q4**; overlap column names **exactly
   one** existing skill; no version-pinned rot-risk; no dependency on Wave C
   restructuring beyond the two already-sequenced files (`security-and-auth`,
   `testing-strategy`); **spread across distinct target skills** to avoid merge
   pile-ups. Final tiebreak among q4-equal candidates: **alphabetical by
   upstream name**, skipping any whose target skill is already used.
3. Every target path was verified present on disk (see `target skill (on disk)`
   column — all 25 resolve to an existing `SKILL.md`).
4. All 25 carry upstream third-party content → each enters via SP-NNN +
   `/skill-review` + `check-imported-skill.py` (injection-corpus scan +
   provenance + review-attestation). Injection-adjacent upstream sources (`ck`,
   `visa-doc-translate`) are SKIP upstream and are **not** in this list
   (verified: neither is even in the ADAPT pool).

## The 25 merges

Legend — **q**: matrix quality. **AFTER-C**: runs only after Wave C restructures
the target into `references/` (debate A NTH-4). Paths are relative to repo root.

| #  | upstream skill (ecc@81af4076) | upstream path | target skill (on disk) | q | merge intent |
|----|-------------------------------|---------------|------------------------|----|--------------|
| 1  | react-performance | `skills/react-performance/SKILL.md` | `.claude/skills/frontend/frontend-performance-optimization/SKILL.md` | q5 | 70+ prioritized React perf rules (Vercel-MIT base) folded into our perf skill |
| 2  | react-patterns | `skills/react-patterns/SKILL.md` | `.claude/skills/frontend/frontend-patterns/SKILL.md` | q4 | dense React 18–19 hooks/RSC/forms patterns enrich frontend-patterns |
| 3  | react-testing | `skills/react-testing/SKILL.md` | `.claude/skills/core/testing-strategy/SKILL.md` | q4 | RTL/MSW/axe + unit-vs-E2E boundary; real gap for the frontend team. **AFTER-C.** ⚠DELTA |
| 4  | database-migrations | `skills/database-migrations/SKILL.md` | `.claude/skills/core/data-schema-design/SKILL.md` | q5 | zero-downtime checklist + good/bad SQL per ORM, deeper than current coverage |
| 5  | postgres-patterns | `skills/postgres-patterns/SKILL.md` | `.claude/skills/core/data-schema-design/SKILL.md` | q4 | index/type/RLS cheat-sheets complement data-schema-design |
| 6  | mysql-patterns | `skills/mysql-patterns/SKILL.md` | `.claude/skills/core/data-schema-design/SKILL.md` | q4 | concrete SQL + MySQL/MariaDB divergences for our PG-only schema skill |
| 7  | intent-driven-development | `skills/intent-driven-development/SKILL.md` | `.claude/skills/core/spec-clarify/SKILL.md` | q5 | observable AC-NNN (must-not + verification + review) enriches spec-clarify. ⚠DELTA |
| 8  | search-first | `skills/search-first/SKILL.md` | `.claude/skills/core/code-review-checklist/SKILL.md` | q4 | anti-NIH adopt/extend/build matrix. ⚠DELTA |
| 9  | evm-token-decimals | `skills/evm-token-decimals/SKILL.md` | `.claude/skills/domains/fintech/skills/financial-correctness-and-math/SKILL.md` | q4 | sharp decimals-per-chain/bridge bug class folded into fintech |
| 10 | nodejs-keccak256 | `skills/nodejs-keccak256/SKILL.md` | `.claude/skills/domains/fintech/skills/blockchain-security-audit/SKILL.md` | q4 | real footgun (NIST SHA3-256 ≠ Keccak) with executable proof |
| 11 | llm-trading-agent-security | `skills/llm-trading-agent-security/SKILL.md` | `.claude/skills/domains/trading-hft/skills/kill-switches/SKILL.md` | q4 | injection-as-financial-attack, spend limits, simulation; strong fintech+governance fit |
| 12 | carrier-relationship-management | `skills/carrier-relationship-management/SKILL.md` | `.claude/skills/domains/supply-chain/skills/supply-chain-strategist/SKILL.md` | q5 | dense freight knowledge (RFP, scorecard, FMCSA) |
| 13 | customs-trade-compliance | `skills/customs-trade-compliance/SKILL.md` | `.claude/skills/domains/supply-chain/skills/supply-chain-strategist/SKILL.md` | q4 | GRI/HS, FTA, denied-party screening |
| 14 | logistics-exception-management | `skills/logistics-exception-management/SKILL.md` | `.claude/skills/domains/supply-chain/skills/supply-chain-strategist/SKILL.md` | q4 | detention/claims/exception windows |
| 15 | inventory-demand-planning | `skills/inventory-demand-planning/SKILL.md` | `.claude/skills/domains/supply-chain/skills/supply-chain-strategist/SKILL.md` | q4 | dense demand-planning knowledge |
| 16 | security-review | `skills/security-review/SKILL.md` | `.claude/skills/core/security-and-auth/SKILL.md` | q4 | dense FAIL/PASS web/TS checklist (+ cloud annex). **AFTER-C.** |
| 17 | security-bounty-hunter | `skills/security-bounty-hunter/SKILL.md` | `.claude/skills/core/security-and-auth/SKILL.md` | q4 | exploitable/payable lens + noise skip-list. **AFTER-C.** |
| 18 | tdd-workflow | `skills/tdd-workflow/SKILL.md` | `.claude/skills/core/testing-strategy/SKILL.md` | q4 | plan-handoff section treats `*.plan.md` as untrusted input (anti-injection). **AFTER-C.** |
| 19 | inherit-legacy-style | `skills/inherit-legacy-style/SKILL.md` | `.claude/skills/core/codebase-onboarding/SKILL.md` | q5 | anti style-drift: grilling protocol + enforcement hook; fits our governance |
| 20 | motion-foundations | `skills/motion-foundations/SKILL.md` | `.claude/skills/frontend/design-system-and-components/SKILL.md` | q5 | motion base (tokens, springs, a11y, SSR-safety) aligned to token governance. ⚠CROSS-WAVE |
| 21 | agent-harness-construction | `skills/agent-harness-construction/SKILL.md` | `.claude/skills/core/mcp-server-authoring/SKILL.md` | q4 | dense action-space/observation/tool-granularity rules complement mcp-authoring |
| 22 | android-clean-architecture | `skills/android-clean-architecture/SKILL.md` | `.claude/skills/domains/mobile/skills/mobile-app-builder/SKILL.md` | q4 | modules/DI/Room/Ktor real code; deepens mobile past the generic builder |
| 23 | benchmark-optimization-loop | `skills/benchmark-optimization-loop/SKILL.md` | `.claude/skills/core/performance-engineering/SKILL.md` | q4 | bounded measured loop (baseline + correctness gate + ledger) complements perf-engineering |
| 24 | brand-voice | `skills/brand-voice/SKILL.md` | `.claude/skills/domains/marketing-global/skills/content-creator/SKILL.md` | q4 | reusable voice profile from real sources; strip ECC refs on port |
| 25 | competitive-report-structure | `skills/competitive-report-structure/SKILL.md` | `.claude/skills/domains/business-support/skills/executive-summary/SKILL.md` | q4 | decision-grade report with white-space discipline |

### The `+7` selection rationale (rows 19–25)

Eligible q5 rows in the 79-row pool that pass **all** filters (single existing-skill
overlap, no rot, no extra Wave-C dependency) are exactly two — both taken first:

- **19. inherit-legacy-style → core/codebase-onboarding** (q5) — sole clean q5 with
  a single-target overlap into a non-Wave-C skill.
- **20. motion-foundations → frontend/design-system-and-components** (q5) — single
  target (token governance); the only other passing q5. See ⚠CROSS-WAVE flag.

Remaining five drawn from q4, **alphabetical by upstream name**, each into a
**distinct** target not already used by rows 1–20:

- **21. agent-harness-construction → core/mcp-server-authoring** (q4) — first
  alphabetically; overlap names exactly `core/mcp-server-authoring`.
- **22. android-clean-architecture → mobile/mobile-app-builder** (q4) — single
  mobile target; first mobile candidate alphabetically (dart-flutter,
  kotlin-*, react-native, swift* all pile on the same target and are skipped).
- **23. benchmark-optimization-loop → core/performance-engineering** (q4) — single
  target; alphabetically ahead of `redis-patterns` which would pile on the same skill.
- **24. brand-voice → marketing-global/content-creator** (q4) — single target;
  distinct squad.
- **25. competitive-report-structure → business-support/executive-summary** (q4) —
  single target; distinct squad. (`customer-billing-ops`, `gan-style-harness`,
  `iterative-retrieval`, `kubernetes-patterns`, `prompt-optimizer`,
  `regex-vs-llm-structured-text`, `returns-reverse-logistics` are the next
  eligible q4 rows and roll into §Deferred — the cut is at exactly 7.)

## Rows needing care (flags)

- **AFTER-C (rows 3, 16, 17, 18):** `testing-strategy` and `security-and-auth`
  merges run **only after Wave C** extracts those files into `references/`
  (debate A NTH-4). Dispatching these before Wave C completes will fight the
  restructure.
- **⚠DELTA row 3 (react-testing):** the plan prose loosely grouped react-testing
  under "frontend", but the **matrix overlap names `core/testing-strategy`** and
  that wins (per contract). Target is `core/testing-strategy`, not a frontend
  skill — and it therefore inherits the AFTER-C constraint.
- **⚠DELTA row 7 (intent-driven-development):** matrix overlap names **two**
  skills (`core/spec-clarify` + `core/requirement-quality-checklist`); the
  plan/debate resolved the merge target to **`core/spec-clarify`**. Recorded as
  named (rows 1–18 are verbatim); flagged because the overlap is not singular.
- **⚠DELTA row 8 (search-first):** matrix overlap is **`none`** — no existing
  skill was auto-matched. Target `core/code-review-checklist` is assigned by the
  **plan/debate**, not the matrix. Verified present on disk; carry the note into
  the SP-NNN so the reviewer knows the target is plan-directed.
- **⚠CROSS-WAVE row 20 (motion-foundations):** the matrix verdict is **ADAPT**
  (merge into `design-system-and-components`), but PLAN-153 Wave D **batch-2**
  prose groups a "motion trio" (foundations/patterns/advanced) as new skills.
  The matrix is ground truth (patterns=ADOPT, advanced=ADOPT, **foundations=ADAPT**,
  ui=SKIP), so foundations belongs here. **Reconciliation rule:** if Wave D pulls
  motion-foundations forward as a *new* skill, drop row 20 from Wave G and
  promote the next eligible distinct-target q4 (`customer-billing-ops →
  core/monetization-and-billing`); update the 72/25 arithmetic accordingly.
- **Pile-ups on named targets (accepted):** `data-schema-design` takes 3 merges
  (rows 4–6) and `supply-chain-strategist` takes 4 (rows 12–15). These are
  plan-named/debate-ratified; the spread rule constrains only the `+7`. Sequence
  the three DB merges and the four supply-chain merges as ordered sub-edits within
  one SP each to avoid self-conflicting patches.

## Compliance-harness pilot (Wave G tail)

Wave G closes by piloting a `skill-comply`-style compliance harness on **exactly
two** existing skills (not ecc ports — a dogfood of the harness itself):

- `.claude/skills/core/minimal-change-discipline/SKILL.md` (verified on disk)
- `.claude/skills/core/git-workflow-discipline/SKILL.md` (verified on disk)

Both are short, high-frequency behavioral skills with crisp PASS/FAIL surface —
ideal first subjects for a 3-prompt-level compliance measurement. The harness is
**advisory** (measures whether the skill is *followed*), separate from the import
gate. `skill-comply` itself stays in §Deferred as an ADAPT (row 60 below) until
the pilot proves the shape.

## Appendix — 72 deferred ADAPTs (arithmetic check)

Reconciliation: **97 ADAPT (matrix) − 25 selected (this file) = 72 deferred.**
Recorded here by name so nothing is silently dropped (success-criterion §Deferred).
Revisit after `/skill-health` exists (Wave C). List computed by set-difference
`comm -23 <all-97-ADAPT> <25-selected>`:

1. agent-architecture-audit
2. agent-introspection-debugging
3. agent-self-evaluation
4. ai-regression-testing
5. api-connector-builder
6. autonomous-loops
7. benchmark-methodology
8. brand-discovery
9. browser-qa
10. canary-watch
11. cisco-ios-patterns
12. click-path-audit
13. competitive-platform-analysis
14. config-gc
15. context-budget
16. continuous-learning-v2
17. customer-billing-ops
18. dart-flutter-patterns
19. documentation-lookup
20. eval-harness
21. flutter-dart-code-review
22. gan-style-harness
23. gateguard
24. github-ops
25. golang-testing
26. growth-log
27. healthcare-phi-compliance
28. hipaa-compliance
29. investor-materials
30. iterative-retrieval
31. jira-integration
32. jpa-patterns
33. kotlin-coroutines-flows
34. kotlin-exposed-patterns
35. kubernetes-patterns
36. lead-intelligence
37. liquid-glass-design
38. make-interfaces-feel-better
39. marketing-campaign
40. ml-adoption-playbook
41. mle-workflow
42. opensource-pipeline
43. product-capability
44. production-audit
45. prompt-optimizer
46. python-patterns
47. python-testing
48. quarkus-patterns
49. quarkus-security
50. quarkus-tdd
51. quarkus-verification
52. react-native-patterns
53. redis-patterns
54. regex-vs-llm-structured-text
55. returns-reverse-logistics
56. rules-distill
57. santa-method
58. scientific-thinking-literature-review
59. scientific-thinking-scholar-evaluation
60. skill-comply
61. skill-scout
62. skill-stocktake
63. social-graph-ranker
64. springboot-security
65. springboot-tdd
66. springboot-verification
67. strategic-compact
68. swift-concurrency-6-2
69. swiftui-patterns
70. vite-patterns
71. vue-patterns
72. workspace-surface-audit

**Count check: 72 names above + 25 in the merge table = 97 = the ADAPT total in
`ecc-skill-matrix.md`. Zero drift.**

Notes on the deferred pool:
- `continuous-learning-v2` (16), `config-gc` (14) and the learning-adjacent
  `growth-log` (26) trend toward **PLAN-154** (gated learning loop), not Wave G.
- `skill-comply` (60) is the compliance-harness source — piloted (above) but not
  merged as a skill in this wave.
- The JVM cluster (`jpa-patterns`, `kotlin-*`, `quarkus-*`, `springboot-*`) is
  correctly deferred: it depends on a Java/JVM squad that is Wave D territory.
- Version-pinned rot-risk rows correctly excluded from the `+7`:
  `liquid-glass-design` (iOS 26), `swift-concurrency-6-2`, `jira-integration`
  (MCP pin).
