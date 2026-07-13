---
plan: PLAN-157
round: 1
created_at: 2026-07-13
verdicts: [ADJUST, ADJUST, ADJUST]
round_verdict: PROCEED
consensus_adjustments: 8
---

# PLAN-157 round-1 consensus

Three critiques, all ADJUST. No critic rejected the thesis: the 4/2/2
disposition and sunsets-first sequencing survive intact (all three
explicitly kept them). The blocking findings are about *mechanics* —
pipeline classification, guard surfaces, and CI-check fidelity. All
adjustments are directly applicable; verdict **PROCEED** (design-coherent
after adjustments; shipping still gated by the verification cascade).

## Consensus findings (2+ critics)

1. **Folds are the SP-NNN pipeline, not quick edits** (A, B, C). Merging
   content into existing core SKILL.md files rides `/skill-review` with
   soak (waivable by Owner, SP-042 precedent). Wave 1 must say so, and
   the soak-waiver decision joins the OQ ratification.
2. **Everything in the touch set is canonical-guarded** (A, B, C): the
   grandfather policy YAML (double-guarded: sentinel + arbitration-kernel
   HARD-DENY — keep it that way), `domains/**/SKILL.md`, team-personas,
   pitfalls, core SKILL.md inventory block, `scripts/install.sh` (via the
   profiles bijection). Every wave is an Owner-GPG sentinel ceremony;
   guarded-file *deletion* (sunset) rides the same sentinel vehicle.
   `validate-governance.sh` itself is NOT guarded → roster edits must be
   commit-atomic with the policy (see 5).
3. **OQ3 trips a pinned test constant** (A, B, C):
   `_EXPECTED_DOMAIN_CAP = 32` in `test_squad_grandfather_cap.py` (~:207)
   asserts EQUAL against policy `cap:`; it runs in validate + 4× in the
   python matrix. Same-commit constant edit required. Critic-B upgrades
   OQ3 from cosmetic to a real control: **`cap := current` at every wave
   boundary** (cap 32 with current draining re-opens up to 8 silent
   re-import slots).
4. **Per-wave Checks must be the REAL CI set** (A, C — Critic-C rated
   CRITICAL): `validate-governance.sh --fast` execs the fast profile
   which explicitly excludes domain-bundle audits and doc-drift counts —
   the exact families this plan exercises. Replace with the full script +
   claims + counts + map --check + inventory diff + install-profiles +
   docs-freshness + tier-boundaries (folds) + the full
   hooks/scripts/optimizer pytest set pre-push. Reconcile must land in
   the SAME commit as each catalog delta, in EVERY wave (W2 had none).
5. **Roster cross-check is count-only — pre-existing tamper gap** (A, B):
   a name-swap in `SQUAD_GRANDFATHER` passes CI green against the
   guarded policy. Add set-equality (names, not counts) to
   `test_squad_grandfather_cap.py` as a Wave 0 rider. Critic-A adds: the
   reopen gate watches `domain_bundles.members`, so sunset squads drop
   out of its view — note in the sunset checklist.

## Single-critic insights kept

- **Factual fix (A):** the 8 squads hold **13** skills, not 15
  (`frontend-slides`/`ui-demo` live in `domains/devrel/`, a legacy
  squad). Scope statements corrected.
- **data-ml gate (A):** graduating data-ml as-is enshrines the
  prisma(TS-ORM)+pytorch mis-pairing in a permanent bundle. Resolve
  prisma's home BEFORE the data-ml graduation (new OQ5).
- **Per-squad go/no-go (A):** ratify the criterion at W0, but each W2/W3
  graduation gets an Owner go/no-go at the wave boundary — kills the
  sunk-cost commitment shape.
- **Fold targets named (A):** `recsys-pipeline-architect` →
  `core/architecture-decisions` violates the core tier token budget;
  fold targets must be named and tier-checked in the wave, with
  `check-tier-boundaries.py` as the gate.
- **OQ2 default flipped (C):** "archive" must NOT live under
  `.claude/skills/` (counters glob the whole tree). Default becomes
  git-history-only deletion + pointer in the plan.
- **Budget honesty (C):** 4 `/architect` bundles ≈ 50+ authored files +
  3-4 ceremonies → budget raised to 4 sessions (or pre-authorized W3
  split).
- **Pre-existing drift riders (C):** README.md 151/101 literals slip
  both gates today; verify-counts domain regexes hardcode a dead "29".
  Adopted as W1 riders.
- **Line-pin hygiene (C):** cite `SQUAD_GRANDFATHER` by pattern (it is
  at :318 today, not :284).

## Single-critic insights rejected / deferred

- **Wave-0 CI-green precondition (C):** already satisfied — Validate on
  `9b09f7c` went green in S270 (the critic read pre-fix state). Kept as
  a standing precondition line, not a blocker.

## Plan adjustments applied (§ index)

1. §Waves W1: folds reclassified as SP-NNN pipeline + soak-waiver OQ;
   fold targets to be named + tier-checked; sunset deletion rides the
   sentinel ceremony.
2. §Waves all: per-wave Check blocks replaced with the real CI set;
   reconcile same-commit in every wave.
3. §New section: complete derived-surface reconcile checklist (9+
   surfaces).
4. §Waves W0: set-equality test rider; baseline check fixed (roster
   pattern, not dash-count).
5. §OQ3 rewritten: `cap := current` per wave + same-commit
   `_EXPECTED_DOMAIN_CAP` edit + stale header comments refresh.
6. §OQ2 default: git-history-only deletion.
7. §New OQ5 (prisma home) + per-squad go/no-go at W2/W3 boundaries.
8. §Context/frontmatter: 13 skills (not 15); budget_sessions 4; roster
   cited by pattern.
