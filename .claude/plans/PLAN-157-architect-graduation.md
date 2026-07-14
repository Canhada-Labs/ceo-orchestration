---
id: PLAN-157
title: Architect Graduation — Drain the 8 Imported Squads (cap 32→24)
status: executing
created: 2026-07-13
reviewed_at: 2026-07-13
reviewed_by: "Owner (chat ratification, S270)"
owner: CEO
depends_on: [PLAN-153]
budget_tokens: 400-600k
budget_sessions: 4
context_risk: high
external_wait: none
tags: [skills, governance, squads]
---

# PLAN-157 — Architect Graduation: drain the 8 imported squads (cap 32→24)

> Debate round 1 (S270): 3×ADJUST → PROCEED with 8 consensus adjustments
> applied (`PLAN-157/debate/round-1/consensus.md`). Design-coherent;
> shipping still gated by the verification cascade V0-V3.

## Context

PLAN-153 Wave D imported ecc skills as 8 new domain scaffolds
(agents-meta, architecture, cpp, data-ml, desktop, dotnet, golang, jvm —
created in ceremony `9152295`, 2026-07-08; **13 skills** live in these 8
squads — `frontend-slides`/`ui-demo` belong to the legacy `devrel`
squad). To land them without full ADR-009 bundles, the grandfather
roster was raised 24→32 (`.claude/policies/grandfather-cap.policy.yaml`
`cap: 32`, `current: 32`, `target_cap: 15`; the policy is
**double-guarded**: sentinel + arbitration-kernel HARD-DENY). The gate
is the `SQUAD_GRANDFATHER` array in `validate-governance.sh` (cite by
pattern — line drifts) + the policy-matching tests in
`test_squad_grandfather_cap.py`. Deferred obligation (PLAN-153:425):
drain the 8 back out, returning `current` to 24.

**Exit mechanics:** **Graduate** = author the full ADR-009 bundle (≥5
personas + ≥3 skills + ≥10 pitfalls + ≥2 task-chains + ≥1 example) via
`/architect`, then remove from roster+policy. **Sunset** = retire the
scaffold (fold keep-worthy content or delete with pointer), then remove
from both. Either path decrements `current`. **Fold** content into an
existing core SKILL.md is the SP-NNN `/skill-review` pipeline (soak
7d, Owner-waivable per the SP-042 precedent) — a different, slower
pipeline than sunset/graduate mechanics.

**Evidence constraint (S270 telemetry dossier):** skill-health over
407,932 events shows zero invocations for all 13 imported skills — and
for 155 of 164 catalog skills. The instrument is structurally blind to
greenfield domain skills (they earn use in target repos;
`.claude/commands/skill-health.md:62-69`). Uniform zero cannot rank the
squads. Criterion substituted to **reach/consumer-plausibility** (the
axis PLAN-153:322-323 used to admit them), telemetry as floor; flagged
for Owner ratification (OQ1). Debate note: do NOT reframe this as
data-driven — the honesty is the point.

## Goal

`grandfather-cap.policy.yaml` reaches `current: 24` (with `cap` tracking
`current` per OQ3) — every imported squad graduated (full ADR-009
bundle) or sunset (content folded via SP pipeline or deleted with
pointer), CI green on every wave commit.

## Approach

Per-squad disposition (ratified shape; each graduation additionally gets
a per-squad Owner go/no-go at its wave boundary — no sunk-cost
commitment):

| Squad | Skills | Reach | Disposition |
|---|---|---|---|
| jvm | 2 | High | Graduate (+1 skill) — go/no-go at W2 |
| cpp | 2 | High | Graduate (+1 skill) — go/no-go at W2 |
| golang | 1 | High | Graduate (+2 skills) — go/no-go at W3 |
| data-ml | 2 | High, mis-paired | Graduate ONLY after OQ5 resolves prisma's home — go/no-go at W3 |
| architecture | 2 | Medium, overlaps core | Fold via SP-NNN (targets named + tier-checked in-wave) + sunset scaffold |
| agents-meta | 2 | Medium, overlaps core | Fold via SP-NNN (target named in-wave) + sunset scaffold |
| dotnet | 1 | Medium, thin | Sunset (OQ2 disposition for csharp-testing) |
| desktop | 1 | Low niche | Sunset |

Alternatives considered: sunset-all-8 (cheapest, discards PLAN-153's
adopt/adapt reasoning); graduate-all-8 (~2x authoring budget on
low-reach squads). Cost honesty: each graduation is real authoring
(~50+ files across 4 bundles); budget raised to 4 sessions after debate.

**Every wave is an Owner-GPG sentinel ceremony** — the touch set is
canonical-guarded end to end (policy YAML, domains/**/SKILL.md,
team-personas, pitfalls, core SKILL.md inventory block, install.sh via
profiles). Batch each wave's guarded edits into one signed landing
script (the `land-plan156.sh` pattern). Guarded-file deletion (sunset)
rides the same sentinel vehicle.

## Derived-surface reconcile checklist (run in the SAME commit as every catalog delta)

The S270 incident class (2 missed derived surfaces → main red), at
larger scale. Each wave commit that changes the catalog MUST reconcile:

1. `CLAUDE.md` count claims (`check-claude-md-claims.py`, tolerance=0)
2. `INSTALL.md` "166-skill inventory" literal (`verify-counts.sh --no-tests`)
3. `README.md` count literals — **manual sweep**: the 151/101 stale
   literals slip both mechanical gates today (phrasing matches no gate
   regex). Fix as W1 rider.
4. `docs/COMMAND-SKILL-HOOK-MAP.md` regen (`gen-command-skill-hook-map.py --write`)
5. `ceo-orchestration/SKILL.md` embedded skill-inventory block (guarded,
   own byte-diff CI gate; Gate-1 cache-stable — touch only inside the
   wave ceremony)
6. `scripts/profiles/profiles.json` + mirrored `scripts/install.sh`
   profile logic (`check-install-profiles.py` bijection runs BOTH ways;
   all 8 squads are referenced today; install.sh is guarded)
7. docs-freshness allowlist entries for deleted paths referenced by
   PLAN-153 plan/debate/artifacts (`check-docs-freshness.py`, blocking)
8. `docs/GUIA-COMPLETO.md` + `.pt-BR` twin (translations-drift workflow)
9. W1 riders: verify-counts dead domain regexes (hardcoded "29"), and
   `docs/ARCHITECTURE.md:55` stale "101 skills / 29 domains"

**Per-wave Check set (the REAL CI set — `--fast` excludes exactly the
families this plan exercises):**
`bash .claude/scripts/validate-governance.sh` (full) &&
`python3 .claude/scripts/check-claude-md-claims.py` &&
`bash .claude/scripts/local/verify-counts.sh --no-tests` &&
`python3 .claude/scripts/gen-command-skill-hook-map.py --check` &&
skill-inventory idempotency diff (validate.yml command) &&
`python3 .claude/scripts/check-install-profiles.py` &&
`python3 .claude/scripts/check-docs-freshness.py --format=text` &&
`python3 .claude/scripts/check-tier-boundaries.py` (fold waves) &&
full `python3 -m pytest .claude/hooks/tests/ .claude/scripts/tests/
.claude/scripts/optimizer/tests/` pre-push (what the python matrix
actually runs, together) && clean-clone proof for new/changed tests.

## Waves

### Wave 0 — ratification + baseline + roster-tamper rider — DONE S272 (2026-07-13)
Check: python3 -m pytest .claude/scripts/tests/test_squad_grandfather_cap.py -q && bash .claude/scripts/validate-governance.sh
- [x] Debate adjustments folded (this revision); Owner ratifies OQ1-OQ5
  at `draft → reviewed`, including the fold soak-waiver decision.
- [x] Baseline snapshot: roster membership + policy state →
  `PLAN-157/baseline.md`.
  Check: grep -c 'SQUAD_GRANDFATHER=' .claude/scripts/validate-governance.sh && grep -n 'current: 32' .claude/policies/grandfather-cap.policy.yaml
- [x] **Tamper-gap rider (debate consensus #5):** add set-equality
  (names, not counts) between `SQUAD_GRANDFATHER` and policy
  `domain_bundles.members` to `test_squad_grandfather_cap.py`
  (scripts/tests is unguarded — direct edit). Also note: the reopen
  gate watches `domain_bundles.members`; sunset squads leave its view.
  Check: python3 -m pytest .claude/scripts/tests/test_squad_grandfather_cap.py -q
- [x] Standing precondition: main Validate green on HEAD before W1
  lands (satisfied S270 at `9b09f7c`; re-verified S272 at `264a8c4`
  após rerun de perf-flake — success).
  Check: gh run list --branch main --workflow "Validate CEO Orchestration governance" --limit 1

### Wave 1 — sunsets + folds (desktop, dotnet, architecture, agents-meta) [SENTINEL CEREMONY + SP-NNN] — DONE S272 (2026-07-14), commit `c3bfa2e` (Owner-signed, GPG Good)
Check: the full per-wave Check set (§reconcile checklist above)
- [x] Sunset `desktop` + `dotnet` (+ `architecture`, `agents-meta` after
  their folds): OQ2 git-history-only deletion; recovery pointer at
  `.claude/plans/PLAN-157/w1-sunset-pointer.md` (moved OUT of the
  gitignored `staged/` after the verify pass caught that `git add`
  silently skips ignored paths — the pointer would never have landed).
  All four dropped from `SQUAD_GRANDFATHER` + policy `members` in ONE
  commit-atomic guarded step.
- [x] Fold `architecture` + `agents-meta` via SP-043..SP-046 (Owner
  detach-signed; OQ4 soak waived): hexagonal → `core/architecture-decisions`,
  recsys → `core/ai-llm-orchestration`, dynamic-workflow + loop-design →
  `core/parallelization-by-default` (SP-045→046 ordering binding). Each
  diff pinned by `sha256_of_diff` + `sha256_of_staged`; tier budgets
  checked. → `current: 28`, `cap: 28` (OQ3), `_EXPECTED_DOMAIN_CAP` edited
  in the same commit.
- [x] Full reconcile in the same commit: skills 166 → **160**, domain dirs
  29 → 25; CLAUDE.md / README / INSTALL / ARCHITECTURE / GUIA twins /
  verify-counts / profiles.json applied from sha256-pinned replicas;
  COMMAND-SKILL-HOOK-MAP + skill-inventory regenerated. All 9 gates green
  (10,865 tests); `touched − scope = ∅`; clean-clone proof 15/15.

### Wave 2 — graduate jvm + cpp [SENTINEL CEREMONY; per-squad Owner go/no-go]
Check: the full per-wave Check set (§reconcile checklist above)
- [ ] Owner go/no-go for jvm; if go: `/architect` bundle (≥5 personas,
  ≥3 skills, ≥10 pitfalls, ≥2 task-chains, ≥1 example); remove from
  roster+policy commit-atomically → `current: 27`; `cap := current`.
- [ ] Same for cpp → `current: 26`.
- [ ] Reconcile checklist in the SAME commit as each catalog delta
  (this wave adds +2 SKILL.md files — claims/counts/map/inventory all
  move).

### Wave 3 — graduate golang + data-ml [SENTINEL CEREMONY; per-squad Owner go/no-go]
Check: the full per-wave Check set (§reconcile checklist above)
- [ ] Owner go/no-go for golang; if go: bundle → `current: 25`;
  `cap := current`.
- [ ] data-ml ONLY after OQ5 (prisma home) is resolved; if go: bundle →
  `current: 24`; `cap := current`.
- [ ] Closeout: policy `current: 24` + `cap: 24`, full reconcile, plan
  `executing → done` with `completed_at` + `related_commits`.
  Check: python3 -m pytest .claude/scripts/tests/test_squad_grandfather_cap.py -q && python3 .claude/scripts/check-claude-md-claims.py

## Open questions

- **OQ1 (criterion substitution)** — telemetry proved blind for
  greenfield domains; ratify reach/consumer-plausibility, or direct
  sunset-all-8.
- **OQ2 (sunset disposition)** — default (debate-adjusted):
  git-history-only deletion + pointer in this plan. Alternative: fold
  `csharp-testing` into a testing-adjacent domain via SP.
- **OQ3 (cap discipline)** — debate-upgraded from cosmetic to control:
  `cap := current` at EVERY wave boundary (cap 32 with a draining
  current re-opens up to 8 silent re-import slots). Each cap edit
  carries the same-commit `_EXPECTED_DOMAIN_CAP` test edit + stale
  policy header comment refresh. CEO default: yes.
- **OQ4 (fold soak)** — folds ride SP-NNN with 7d soak; waive (SP-042
  precedent) or hold? CEO default: waive, given the content is already
  in-tree since 2026-07-08.
- **OQ5 (prisma home)** — `prisma-patterns` (TS ORM) does not belong
  with `pytorch-patterns` in a data-ml bundle. Options: move prisma to
  a web/backend-adjacent domain (SP), keep data-ml as ML-only (+1 ML
  skill), or defer data-ml graduation. Must resolve BEFORE the data-ml
  go/no-go.

## Clarifications

- 2026-07-13 (S270, Owner via structured tie-break): OQ1-OQ4 → selected
  **"Ratificar os 4 (Recomendado)"** — OQ1 reach/consumer-plausibility
  criterion ratified; OQ2 sunset = git-history-only deletion + pointer;
  OQ3 `cap := current` at every wave boundary; OQ4 fold soak WAIVED
  (SP-042 precedent, content in-tree since 2026-07-08).
- 2026-07-13 (S270, Owner): OQ5 → selected **"data-ml vira ML-only +
  prisma move (Recomendado)"** — `prisma-patterns` moves via SP to a
  web/backend-adjacent domain (e.g. saas-platforms); data-ml graduates
  ML-only with +1 authored ML skill.

## How to continue

Read this plan + `PLAN-157/debate/round-1/consensus.md` +
`PLAN-157/baseline.md` (when present). If `draft`: Owner ratification
is the gate. If `reviewed`: execute waves in order; every catalog
delta commits with its full reconcile (see §checklist); every wave is
a sentinel ceremony batched into one Owner landing script. Mechanics:
grandfather-cap.policy.yaml (guarded), `SQUAD_GRANDFATHER` in
validate-governance.sh (unguarded — commit-atomic with policy),
test_squad_grandfather_cap.py (unguarded).

## Success criteria

- [ ] Policy shows `current: 24` AND `cap: 24`; `SQUAD_GRANDFATHER`
  set-equal to policy members (new test green).
- [ ] Graduated squads carry complete ADR-009 bundles; bundle
  validation ERROR-free (not WARNING-suppressed).
- [ ] No orphan skills: all 13 imported skills graduated, folded (SP
  landed), or deleted with pointer.
- [ ] Every wave commit green on the FULL Validate workflow (not just
  local fast checks).
