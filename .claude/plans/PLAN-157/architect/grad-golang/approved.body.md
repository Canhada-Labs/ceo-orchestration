# SENT-GRAD-GOLANG — PLAN-157 Wave 3: graduate golang (full ADR-009 bundle)

Merges the machine-local staged bundle
(`.claude/plans/PLAN-157/staged/golang/`, gitignored) additively into
`.claude/skills/domains/golang/`: team-personas (5 personas + routing
table, VETO holders with stated scopes), 16 pitfalls, 2 task-chains
(`golang-ship-new-service`, `golang-race-or-leak-triage`), 1 example,
and TWO new authored skills (`golang-testing`, `golang-services`). The
existing imported skill (`golang-patterns`) is NOT touched — the merge
is strictly additive; the land script dies on any collision.

Criterion (OQ1, Owner-ratified S270 structured tie-break):
reach/consumer-plausibility, telemetry as floor. Skill telemetry is
structurally blind to greenfield domain squads (uniform zero across
407,932 events for all 13 imports) — NO usage claim is made or implied.
Reach case: Go is a dominant cloud-native/services language among
plausible adopters; the squad needs +2 skills (not +1) because it
imported with a single skill and ADR-009 requires ≥3 skill dirs.

Evidence: bundle staged S272 (2026-07-13); ADR-009 bundle validator
(`validate-squad-contract.py`) PASS on the merged tree (canonical 1
skill + staged bundle → 3 skill dirs, all minimums hold) — re-verified
2026-07-13 while authoring this body. The land script re-runs the same
validator against the canonical tree post-copy (gate 2/12), and
`validate-governance.sh` §5 re-asserts the contract at ERROR level once
golang leaves the grandfather roster.

Roster/cap math (expected under the plan order W1 → W2 → golang; the
land script DERIVES every number from disk and aborts on drift):
`SQUAD_GRANDFATHER` 26 → 25 names; policy `current` 26 → 25;
`cap := 25` (OQ3 cap := current); `_EXPECTED_DOMAIN_CAP := 25` — all
three surfaces in this ONE commit. Catalog: 162 → 164 skills total,
112 → 114 domain; golang skill dirs 1 → 3. Reconcile rides the same
commit across CLAUDE.md, README, INSTALL, ARCHITECTURE, GUIA twins,
verify-counts header, core SKILL.md literal + regenerated inventory
block, COMMAND-SKILL-HOOK-MAP.

Vehicle: `bash .claude/plans/PLAN-157/land-plan157-graduation.sh golang`
— single signed commit tagged [SENT-GRAD-GOLANG]; push is a separate
Owner act after review.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Anchor-SHA: __ANCHOR_SHA__
Plans: PLAN-157
Kernel-Override: (none needed — Owner-shell apply route; NOTE: grandfather-cap.policy.yaml matches the _KERNEL_PATHS glob .claude/policies/*.yaml, but the arbitration kernel gates Claude tool calls, not the Owner shell — S261 precedent)
Scope:
  - .claude/skills/domains/golang/
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
  - .claude/plans/PLAN-157/architect/grad-golang/
Amends: golang squad graduates off SQUAD_GRANDFATHER (roster 26→25,
  cap := current per OQ3); +2 skills golang-testing + golang-services;
  count reconcile 162→164/112→114; derived surfaces regenerated.
  Existing golang-patterns byte-identical.
<!-- END SIGNED SCOPE -->
