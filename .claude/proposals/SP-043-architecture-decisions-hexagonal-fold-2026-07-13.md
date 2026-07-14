---
id: SP-043
skill_slug: architecture-decisions
archetype: none   # core-skill fold, CEO-proposed — SP-018/SP-042 precedent (no owning archetype)
proposed_at: 2026-07-13T23:05:00Z
source_lessons:
  - plan-157-w1-fold-hexagonal-architecture
scan_injection_pass: true
diff_size_added: 53
diff_size_removed: 1
sha256_of_diff: a7759d0db41be597bcbc3908c4300a37869b8f5df3d99f5f3bc50556a04575c0
sha256_of_staged: f568c8f783525c710e9bef11029d73408c254f10fa69f91b9bad48d9e3a7a79c
claims_declared: false
status: proposed
shadow_mode: false
soak_waiver: owner-ratified-at-signing   # PLAN-157 OQ4 (Owner tie-break S270) via SP-042/S264-OQ4 precedent
proposal_type: fold-distill-append
patch_source: inline diff fence (below)
---

# SP-043 — fold `hexagonal-architecture` → `core/architecture-decisions` (PLAN-157 W1)

**Target:** `.claude/skills/core/architecture-decisions/SKILL.md`
**Source:** the architecture squad's `hexagonal-architecture` skill
(pre-fold source pin sha256
`8df04532a5a6e078e01b655c32a632661105df43e961b239f744b14234a59d70`),
sunset in the same W1 ceremony per OQ2 (git-history-only deletion +
pointer in the plan — never a path pointer in core prose).
**Kind:** distilled append + one-line declared-budget bump.

## Rationale

PLAN-157 W1 (ratified shape, Owner OQ1-OQ4 tie-break S270): the
`architecture` squad folds via SP-NNN with named, tier-checked targets,
then the scaffold sunsets, decrementing the grandfather roster. The
target's existing scope — "system boundary identification", the System
Boundaries layout, the DDD reference, When to Refactor vs Rewrite — is
exactly where Ports & Adapters boundary doctrine belongs.

**What survives (the distill, ~748 est tokens):** the one rule
(dependencies point inward), the six pieces compressed to prose, the
6-step build recipe, the per-boundary test list, the 5 anti-patterns,
and checklist essentials, plus a handoff line routing strangler
migration to `core/incremental-refactoring`.

**What is dropped, and why:** the 60-line Python worked example and the
composition-root code (worked code belongs in a domain skill, not a
core decision framework); the cross-language mapping (TS/Java/Kotlin/Go
wiring styles — syntax, not doctrine); the module-layout tree and ASCII
dependency diagram (rederivable from the pieces table); the changelog +
import attestation (source-file bookkeeping); and the strangler
migration playbook — already covered by `core/incremental-refactoring`'s
Migration Playbook + Working with Legacy Code sections (named runner-up
if the Owner wants the strangler bullets kept: a ~3-bullet rider there).

## Budget evidence (repo-canonical chars/4 estimate)

- Distilled section: 2,993 B ≈ 748 tokens. Post-fold file: 18,874 B
  ≈ 4,718 tokens full-file; post-fold body est ≈ 3,962 tokens
  (pre-fold body_est 3,214 + 748).
- Per-skill schema ceiling 30,000 (`repo-profile-skill-binding.schema.json`
  `context_budget_tokens` maximum) — 26,038 tokens of headroom remain.
- Declared `context_budget_tokens` bumped 900 → 1100 (scout-measured
  recommendation; the declared field is the progressive-disclosure
  active-set contribution estimate, not the body size).
- Live profile sum unaffected today: resolver shows trading-readonly
  `context_total_tokens: 10200` vs cap 30,000 (19,800 live headroom);
  this target is not in the current active set.
- Tier-boundary safety: the appended prose contains no
  `domains/<x>/skills/<y>` or `../../domains/` reference (asserted at
  build time with the same regex as `_DOMAIN_REF_RE`); the fold adds no
  file under core/, so `check-tier-boundaries.py` stays 92-files clean.

## Soak waiver

The 7-day shadow soak is WAIVED per the Owner's OQ4 ratification
(S270 structured tie-break, SP-042/S264-OQ4 precedent): the folded
content has been in-tree, import-attested, since 2026-07-08; this SP
compresses it into an existing core skill with zero new doctrine.
Owner ratifies the waiver by detach-signing this proposal.
`sha256_of_staged` above pins the exact post-apply file.

## Apply route

The appended-section hunk is pipeline-expressible (append-only). The
one-line `context_budget_tokens` bump is NOT — pipeline
`_apply_unified_diff` is append-only by design and cannot express a
removal (SP-042) — so this SP is applied Owner-shell inside the W1
sentinel ceremony (the `land-plan156.sh` batching pattern), with the
staged-file hash asserted before commit. The source-dir sunset is a
separate Owner-shell step in the same ceremony.

## Diff

```diff
--- a/.claude/skills/core/architecture-decisions/SKILL.md
+++ b/.claude/skills/core/architecture-decisions/SKILL.md
@@ -25,7 +25,7 @@
 priority: 4
 risk_class: medium
 stack: []
-context_budget_tokens: 900
+context_budget_tokens: 1100
 inactive_but_retained: false
 repo_profile_binding:
   frontend: {active: true, priority: 5}
@@ -362,3 +362,55 @@
 - **Treating the default package manager choice as a decision.** Transitive
   dependencies require the same reversibility classification as direct ones
   when they own a data format or protocol surface.
+
+## Hexagonal Boundaries (Ports & Adapters) — folded from `hexagonal-architecture` (PLAN-157 W1)
+
+Boundary doctrine for keeping business logic independent of frameworks,
+transport, and persistence — distilled from the sunset architecture squad's
+`hexagonal-architecture` skill (full text in git history; fold ratified
+PLAN-157 OQ1-OQ4, S270).
+
+**The one rule: dependencies point inward.** The core — domain rules plus the
+use cases that orchestrate them — never imports a framework, driver, transport
+type, or concrete client; it depends only on abstractions it owns (ports). An
+entity or use case that imports an ORM row, a web `Request`, or a vendor SDK
+has already broken the architecture.
+
+**The pieces:** domain model (entities, value objects, invariants — knows
+nothing external); use case (orchestrates one intent — knows ports only);
+inbound port (what the application can do); outbound port (what the
+application needs: repository, gateway, publisher, clock, id-generator);
+adapter (concrete edge — HTTP controller, DB repository, queue consumer, SDK
+wrapper — knows frameworks); composition root (the single place that
+instantiates adapters and injects them into use cases — knows everything, by
+design). Outbound port interfaces belong to the application layer; their
+implementations live in infrastructure.
+
+**Build recipe:** (1) draw one use-case boundary with explicit input/output
+DTOs — no transport wrappers cross the line; (2) name every side effect as an
+outbound port first — model capabilities (`StockRepository`), never
+technologies (`PostgresStockTable`); (3) write the use case as pure
+orchestration over injected ports; (4) build adapters at the edge — mapping
+lives there and never leaks inward; (5) wire everything in one auditable
+composition root; (6) test per boundary.
+
+**Testing, by boundary:** domain tests as pure rules (no mocks); use-case unit
+tests with in-memory fakes for every port; one shared contract suite per
+outbound port, run against every adapter implementing it; inbound adapter
+tests for protocol mapping in both directions; adapter integration tests
+against real infrastructure; end-to-end on the critical journeys;
+characterization tests before any extraction.
+
+**Anti-patterns:** domain entities importing ORM/web/SDK types; use cases
+reading `req`/`res` or queue metadata; use cases returning raw database rows;
+adapters calling each other instead of flowing through use-case ports; wiring
+scattered behind hidden global singletons.
+
+**Checklist:** validation at both boundaries (inbound adapter AND use-case
+invariants); transformations return new values, never mutate shared state;
+errors translated across boundaries (infra error → application/domain error);
+use cases runnable under simple in-memory fakes for every port.
+
+For migrating a tangled service slice-by-slice, use
+`core/incremental-refactoring` — its Migration Playbook and legacy-code
+sections cover the strangler path the source skill described.
```

## Verification

- `sha256(SKILL.md post-apply) == sha256_of_staged` (asserted by the
  W1 landing script before commit).
- `python3 .claude/scripts/check-tier-boundaries.py` → clean, exit 0
  (92 files scanned; no core file added).
- `python3 .claude/scripts/smart-loading-resolver.py resolve --json` →
  `context_total_tokens` ≤ 30000 (10,200 today).
- `python3 .claude/scripts/lint-skills.py` → zero ERROR lines.
- Full PLAN-157 per-wave Check set rides the W1 ceremony commit
  (claims, verify-counts, map regen, inventory block, install-profiles,
  docs-freshness).
