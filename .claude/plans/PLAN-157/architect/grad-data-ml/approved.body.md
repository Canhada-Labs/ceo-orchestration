# SENT-GRAD-DATA-ML — PLAN-157 Wave 3: graduate data-ml (ML-only, full ADR-009 bundle) + SP-047 prisma move

> ⚠ OWNER ACK REQUIRED (read before signing — signing this sentinel
> RECORDS the ack): the ratified OQ5 wording (S270) says data-ml
> graduates ML-only with "+1 authored ML skill". With `prisma-patterns`
> moved out, +1 would leave data-ml at 2 skill dirs — RED against the
> ADR-009 ≥3 minimum the moment it leaves the grandfather roster. The
> staged bundle therefore ships **+2** new skills (`ml-evaluation-patterns`,
> `ml-serving-patterns`) — the minimum satisfying the contract. Your
> signature on this sentinel is the explicit ack of that +2-vs-wording
> delta (flag raised in the staged bundle's rationale and in SP-047).

Two moves, one ceremony (SP-047 may also land earlier — the land script
verifies the precondition either way):

1. **SP-047 (OQ5 resolution, precondition):** `prisma-patterns` (a
   TypeScript ORM skill mis-paired with `pytorch-patterns`) moves
   VERBATIM to `.claude/skills/domains/saas-platforms/skills/` via
   `git mv` + a one-line frontmatter edit (`domain: data-ml` →
   `saas-platforms`); post-move file pinned by the SP's
   `sha256_of_staged`. Soak WAIVED per OQ4 (SP-042 precedent) — the
   Owner ratifies by detach-signing the SP itself. saas-platforms
   absorbs +1 (3 → 4 skill dirs; its own ADR-009 minimums verified to
   hold, and it remains grandfathered regardless). Net-zero on the
   skill catalog. data-ml graduation is BLOCKED by the land script
   until this move is on disk (`--apply-sp047` applies it in-ceremony).

2. **Graduation:** merges the machine-local staged bundle
   (`.claude/plans/PLAN-157/staged/data-ml/`, gitignored) additively
   into `.claude/skills/domains/data-ml/`: team-personas (5 personas +
   routing table; VETO holders on evaluation integrity and serving
   safety), 17 pitfalls, 2 task-chains, 1 example, and the TWO new
   authored skills. `pytorch-patterns` is NOT touched. End state:
   data-ml = pytorch-patterns + ml-evaluation-patterns +
   ml-serving-patterns — train → evaluate → serve, ML-only.

Criterion (OQ1, Owner-ratified S270 structured tie-break):
reach/consumer-plausibility, telemetry as floor. Skill telemetry is
structurally blind to greenfield domain squads (uniform zero across
407,932 events for all 13 imports) — NO usage claim is made or implied.
Reach case: PyTorch/ML engineering is among the highest-plausibility
adopter domains; the graduated bundle covers the lifecycle an ML change
actually moves through.

Evidence: bundle staged S272 (2026-07-13); ADR-009 bundle validator
(`validate-squad-contract.py`) PASS on the merged tree (prisma moved
out + staged bundle → 3 skill dirs, all minimums hold) AND on
saas-platforms with prisma absorbed — re-verified 2026-07-13 while
authoring this body. The land script re-runs the validator against the
canonical tree post-copy (gate 2/12), and `validate-governance.sh` §5
re-asserts the contract at ERROR level once data-ml leaves the roster.

Roster/cap math (expected under the plan order — data-ml LAST; the land
script DERIVES every number from disk and aborts on drift):
`SQUAD_GRANDFATHER` 25 → 24 names; policy `current` 25 → 24;
`cap := 24` (OQ3 cap := current) — **the PLAN-157 goal state
(current: 24, cap: 24)**; `_EXPECTED_DOMAIN_CAP := 24` — all three
surfaces in this ONE commit. Catalog: 164 → 166 skills total,
114 → 116 domain (SP-047 move is net-zero); data-ml skill dirs
2 → 1 (prisma out) → 3 (+2 authored); saas-platforms 3 → 4. Reconcile
rides the same commit across CLAUDE.md, README, INSTALL, ARCHITECTURE,
GUIA twins, verify-counts header, core SKILL.md literal + regenerated
inventory block, COMMAND-SKILL-HOOK-MAP; SP-047 + .asc registered in
`.claude/proposals/`.

Vehicle:
`bash .claude/plans/PLAN-157/land-plan157-graduation.sh data-ml --apply-sp047`
— single signed commit tagged [SENT-GRAD-DATA-ML]; push is a separate
Owner act after review. After push + Validate green: PLAN-157 goal
reached; plan closeout (executing → done) next session.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Anchor-SHA: __ANCHOR_SHA__
Plans: PLAN-157
Kernel-Override: (none needed — Owner-shell apply route; NOTE: grandfather-cap.policy.yaml matches the _KERNEL_PATHS glob .claude/policies/*.yaml, but the arbitration kernel gates Claude tool calls, not the Owner shell — S261 precedent)
Scope:
  - .claude/skills/domains/data-ml/
  - .claude/skills/domains/saas-platforms/skills/prisma-patterns/
  - .claude/proposals/SP-047-prisma-patterns-saas-platforms-move-2026-07-13.md
  - .claude/proposals/SP-047-prisma-patterns-saas-platforms-move-2026-07-13.md.asc
  - CLAUDE.md
  - README.md
  - INSTALL.md
  - docs/ARCHITECTURE.md
  - docs/GUIA-COMPLETO.md
  - docs/GUIA-COMPLETO.pt-BR.md
  - docs/COMMAND-SKILL-HOOK-MAP.md
  - docs/docs-freshness-allowlist.txt
  - .claude/policies/grandfather-cap.policy.yaml
  - .claude/scripts/validate-governance.sh
  - .claude/scripts/tests/test_squad_grandfather_cap.py
  - .claude/scripts/local/verify-counts.sh
  - .claude/skills/core/ceo-orchestration/SKILL.md
  - .claude/plans/PLAN-157/architect/grad-data-ml/
Amends: data-ml graduates ML-only off SQUAD_GRANDFATHER (roster 25→24 =
  plan goal, cap := current per OQ3); SP-047 prisma-patterns → saas-platforms
  (verbatim move, one frontmatter line); +2 skills ml-evaluation-patterns +
  ml-serving-patterns (Owner-acked vs OQ5 "+1" wording); count reconcile
  164→166/114→116; derived surfaces regenerated. pytorch-patterns
  byte-identical; docs-freshness-allowlist touched only if the move
  newly breaks a link (expected: none).
<!-- END SIGNED SCOPE -->
