# SENT-GRAD-JVM — PLAN-157 Wave 2: graduate jvm (full ADR-009 bundle)

Merges the machine-local staged bundle
(`.claude/plans/PLAN-157/staged/jvm/`, gitignored) additively into
`.claude/skills/domains/jvm/`: team-personas (5 personas + routing
table, 3 VETO holders), 18 pitfalls, 2 task-chains, 1 example, and ONE
new authored skill (`jvm-testing`). The two existing imported skills
(`java-coding-standards`, `springboot-patterns`) are NOT touched — the
merge is strictly additive; the land script dies on any collision.

Criterion (OQ1, Owner-ratified S270 structured tie-break):
reach/consumer-plausibility, telemetry as floor. Skill telemetry is
structurally blind to greenfield domain squads (uniform zero across
407,932 events for all 13 imports) — NO usage claim is made or implied.
Reach case: Java 17+ with Spring Boot/Quarkus is one of the largest
backend ecosystems adopters of this framework plausibly run.

Evidence: bundle staged S272 (2026-07-13); ADR-009 bundle validator
(`validate-squad-contract.py`) PASS on the merged tree (canonical 2
skills + staged bundle → 3 skill dirs, all minimums hold) — re-verified
2026-07-13 while authoring this body. The land script re-runs the same
validator against the canonical tree post-copy (gate 2/12), and
`validate-governance.sh` §5 re-asserts the contract at ERROR level once
jvm leaves the grandfather roster.

Roster/cap math (expected under the plan order W1 → jvm first; the land
script DERIVES every number from disk and aborts on drift):
`SQUAD_GRANDFATHER` 28 → 27 names; policy `current` 28 → 27;
`cap := 27` (OQ3 cap := current); `_EXPECTED_DOMAIN_CAP := 27` — all
three surfaces in this ONE commit. Catalog: 160 → 161 skills total,
110 → 111 domain; jvm skill dirs 2 → 3. Reconcile rides the same
commit across CLAUDE.md, README, INSTALL, ARCHITECTURE, GUIA twins,
verify-counts header, core SKILL.md literal + regenerated inventory
block, COMMAND-SKILL-HOOK-MAP.

Vehicle: `bash .claude/plans/PLAN-157/land-plan157-graduation.sh jvm`
— single signed commit tagged [SENT-GRAD-JVM]; push is a separate
Owner act after review.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Anchor-SHA: 60ceb634a0222f9881bcdb0895910db8ca7db058
Plans: PLAN-157
Kernel-Override: (none needed — Owner-shell apply route; NOTE: grandfather-cap.policy.yaml matches the _KERNEL_PATHS glob .claude/policies/*.yaml, but the arbitration kernel gates Claude tool calls, not the Owner shell — S261 precedent)
Scope:
  - .claude/skills/domains/jvm/
  - CLAUDE.md
  - README.md
  - INSTALL.md
  - docs/ARCHITECTURE.md
  - docs/GUIA-COMPLETO.md
  - docs/GUIA-COMPLETO.pt-BR.md
  - docs/COMMAND-SKILL-HOOK-MAP.md
  - .claude/policies/grandfather-cap.policy.yaml
  - .claude/scripts/validate-governance.sh
  - .claude/scripts/tests/test_squad_grandfather_cap.py
  - .claude/scripts/local/verify-counts.sh
  - .claude/skills/core/ceo-orchestration/SKILL.md
  - .claude/plans/PLAN-157/architect/grad-jvm/
Amends: jvm squad graduates off SQUAD_GRANDFATHER (roster 28→27, cap :=
  current per OQ3); +1 skill jvm-testing; count reconcile 160→161/110→111;
  derived surfaces regenerated. Existing jvm skills byte-identical.
<!-- END SIGNED SCOPE -->
