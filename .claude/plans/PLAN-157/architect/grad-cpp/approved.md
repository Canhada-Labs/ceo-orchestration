# SENT-GRAD-CPP — PLAN-157 Wave 2: graduate cpp (full ADR-009 bundle)

Merges the machine-local staged bundle
(`.claude/plans/PLAN-157/staged/cpp/`, gitignored) additively into
`.claude/skills/domains/cpp/`: team-personas (5 personas + routing
table, VETO holders with stated scopes), 15 pitfalls, 2 task-chains,
1 example, and ONE new authored skill (`cpp-build-systems`). The two
existing imported skills (`cpp-coding-standards`, `cpp-testing`) are
NOT touched — the merge is strictly additive; the land script dies on
any collision.

Criterion (OQ1, Owner-ratified S270 structured tie-break):
reach/consumer-plausibility, telemetry as floor. Skill telemetry is
structurally blind to greenfield domain squads (uniform zero across
407,932 events for all 13 imports) — NO usage claim is made or implied.
Reach case: C++ systems/performance work (CMake-era build-and-test
toolchains) is a high-plausibility adopter domain, and the two existing
skills already carry expert-depth content worth routing personas at.

Evidence: bundle staged S272 (2026-07-13); ADR-009 bundle validator
(`validate-squad-contract.py`) PASS on the merged tree (canonical 2
skills + staged bundle → 3 skill dirs, all minimums hold) — re-verified
2026-07-13 while authoring this body. The land script re-runs the same
validator against the canonical tree post-copy (gate 2/12), and
`validate-governance.sh` §5 re-asserts the contract at ERROR level once
cpp leaves the grandfather roster.

Roster/cap math (expected under the plan order W1 → jvm → cpp; the land
script DERIVES every number from disk and aborts on drift):
`SQUAD_GRANDFATHER` 27 → 26 names; policy `current` 27 → 26;
`cap := 26` (OQ3 cap := current); `_EXPECTED_DOMAIN_CAP := 26` — all
three surfaces in this ONE commit. Catalog: 161 → 162 skills total,
111 → 112 domain; cpp skill dirs 2 → 3. Reconcile rides the same
commit across CLAUDE.md, README, INSTALL, ARCHITECTURE, GUIA twins,
verify-counts header, core SKILL.md literal + regenerated inventory
block, COMMAND-SKILL-HOOK-MAP.

Vehicle: `bash .claude/plans/PLAN-157/land-plan157-graduation.sh cpp`
— single signed commit tagged [SENT-GRAD-CPP]; push is a separate
Owner act after review.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Anchor-SHA: 251998b3708ad355fc70c8acdfa157a27089bfa0
Plans: PLAN-157
Kernel-Override: (none needed — Owner-shell apply route; NOTE: grandfather-cap.policy.yaml matches the _KERNEL_PATHS glob .claude/policies/*.yaml, but the arbitration kernel gates Claude tool calls, not the Owner shell — S261 precedent)
Scope:
  - .claude/skills/domains/cpp/
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
  - .claude/plans/PLAN-157/architect/grad-cpp/
Amends: cpp squad graduates off SQUAD_GRANDFATHER (roster 27→26, cap :=
  current per OQ3); +1 skill cpp-build-systems; count reconcile
  161→162/111→112; derived surfaces regenerated. Existing cpp skills
  byte-identical.
<!-- END SIGNED SCOPE -->
