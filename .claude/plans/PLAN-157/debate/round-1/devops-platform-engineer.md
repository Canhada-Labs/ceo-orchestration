---
round: 1
archetype: DevOps & Platform Engineer
skill: devops-ci-cd
agent_persona: DevOps & Platform Engineer (CI/CD gates lens)
generated_at: 2026-07-13T19:00:05Z
---

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- The plan drains the 8 PLAN-153 Wave D squads (graduate 4 / fold 2 /
  sunset 2) back to `current: 24`, with per-wave Check commands and a
  counts reconcile in W1 and the W3 closeout. The disposition logic and
  sequencing are sound.
- Strong: sunsets-first ordering, explicit OQ ratification, honest
  telemetry-blindness framing, per-wave `test_squad_grandfather_cap.py`
  runs, "CI green throughout" as a stated goal.
- Weak: the declared per-wave Check commands do **not** run what CI
  runs (`--fast` execs `validate_governance_fast.py`, whose docstring
  explicitly excludes "domain bundle audits" and "doc drift counts" —
  the exact two families this plan exercises), and the W1 reconcile
  list covers 3 of at least 9 derived surfaces the catalog shrink
  touches. This is precisely the S270 failure class (2 missed derived
  surfaces → main red), at larger scale.

## Risks

1. **R-DEV1 — Severity: CRITICAL — per-wave Check ≠ CI.**
   `bash .claude/scripts/validate-governance.sh --fast` (declared as
   the Check for W1/W2/W3) execs
   `.claude/scripts/validate_governance_fast.py`, which self-documents
   its out-of-scope list as "Skill frontmatter … sweeps, ADR scans,
   doc drift counts, domain bundle audits" (docstring, lines 21-23).
   CI (`validate.yml:44-47`) runs the FULL `validate-governance.sh`,
   where de-grandfathered squads flip from WARN to ERROR on the
   ADR-009 bundle contract. A wave can pass every declared Check
   locally and land red on main.
   *Mitigation:* per-wave Check must be the full
   `bash .claude/scripts/validate-governance.sh` (no `--fast`) plus
   the wave-relevant validate.yml step commands (enumerated in
   Must-fix 1).

2. **R-DEV2 — Severity: HIGH — W1 reconcile list is incomplete.**
   The plan lists `verify-counts.sh`, `check-claude-md-claims.py`,
   and "skill-inventory regen". The catalog shrink also trips, as
   hard CI gates: (a) `gen-command-skill-hook-map.py --check`
   (validate.yml:288 — `docs/COMMAND-SKILL-HOOK-MAP.md` is derived
   from `skills/**/SKILL.md`; its own totals line cites
   "166 — … domain 116 (across 36 domains)"); (b) the skill-inventory
   idempotency diff (validate.yml:801) against the committed block in
   `.claude/skills/core/ceo-orchestration/SKILL.md`; (c)
   `check-install-profiles.py` (validate.yml:875) — its domain-dir ↔
   profile bijection runs BOTH ways and `scripts/profiles/profiles.json`
   references **all 8** imported squads today, with a static
   cross-parse of `scripts/install.sh`; (d)
   `check-docs-freshness.py` (blocking, ADR-023 State 2) — it scans
   `.claude/plans/PLAN-*`, and PLAN-153's plan/debate/artifacts files
   reference `skills/domains/desktop|dotnet/...` paths that sunsets
   delete; (e) `check-tier-boundaries.py` for anything folded into
   core that still references `domains/`; (f)
   `check-doc-skill-paths.sh` for skill-path literals in
   INSTALL/README/CLAUDE.md; (g) `docs/GUIA-COMPLETO.md` +
   `docs/GUIA-COMPLETO.pt-BR.md` (both reference the imported squads;
   gated by translations-drift.yml on path triggers).
   *Mitigation:* enumerate the full reconcile checklist in the plan
   (Must-fix 2) and run it per wave, not once.

3. **R-DEV3 — Severity: HIGH — W2 has no counts reconcile at all.**
   `check-claude-md-claims.py` (tolerance=0, every push) matches
   CLAUDE.md:52 "**166 skills** ready-made (42 core + …)";
   `verify-counts.sh --no-tests` (every push) additionally gates
   INSTALL.md:531 "166-skill inventory". W2 adds +2 SKILL.md files
   (jvm+1, cpp+1) and W3 adds +3; each graduation ALSO regenerates
   the map and the inventory block. Yet W2's Check block contains
   neither claims nor counts commands, and the plan defers "counts
   reconciled" to W1 and the W3 closeout. Any W2 commit that lands
   without a same-commit CLAUDE.md/INSTALL.md/map/inventory update is
   red on main.
   *Mitigation:* every wave that changes the catalog carries the full
   reconcile in the SAME commit (Must-fix 3).

4. **R-DEV4 — Severity: MEDIUM — OQ3 (cap 32→24) trips a pinned test
   constant.** `test_squad_grandfather_cap.py` line 207 pins
   `_EXPECTED_DOMAIN_CAP = 32` and `test_domain_cap_declared_correctly`
   does an exact `assertEqual` against the policy `cap:`. This test
   runs in the validate job ("Run Python script unit tests") AND 4×
   in `hook-tests-python-matrix` (which runs `.claude/hooks/tests/`
   + `.claude/scripts/tests/` + optimizer together on 3.9/3.10/3.11/
   3.12 — confirmed validate.yml:1307). Lowering `cap:` without the
   same-commit constant edit reds 5 jobs.
   *Mitigation:* OQ3 rider = edit the constant (and the stale policy
   header comments) in the same commit; `.claude/scripts/tests/` is
   not canonical-guarded, so this is a direct edit.

5. **R-DEV5 — Severity: MEDIUM — the `Ceo` runner is currently dead.**
   `validate`, `integration-tests`,
   `formal-verification-mutation-harness`, `hook-tests-dual-rail`,
   and `hook-tests-python-matrix` are all `runs-on: Ceo`, and as of
   S270 the org runner is not picking up jobs (Validate for `188d3ea`
   queued 2h30m+). "CI green throughout" and the success criterion
   "Full Validate workflow green on the closeout commit" are
   unverifiable until the Owner unblocks it.
   *Mitigation:* add a Wave 0 precondition: main Validate green on
   the current HEAD before any W1 commit lands.

6. **R-DEV6 — Severity: MEDIUM — roster edits are a synchronized
   triple, per decrement.**
   `test_squad_grandfather_matches_policy_current` asserts
   `len(SQUAD_GRANDFATHER)` (validate-governance.sh:318) ==
   policy `current:`, and `test_domain_members_count_matches_current`
   asserts `len(members)` == `current:`. Every intermediate state the
   plan names (30, 28, 27, 26, 25, 24) must be commit-atomic across
   bash array + policy `members` + policy `current` + the
   corresponding skill-tree change + all derived regens.
   *Mitigation:* one revertable commit per disposition step (or per
   wave); never split "delete skills" and "reconcile counts" across
   commits.

7. **R-DEV7 — Severity: MEDIUM — "archive" must live outside
   `.claude/skills/`.** Both counters glob the whole tree
   (`verify-counts.sh`: `find .claude/skills -name SKILL.md`;
   claims gate: `.claude/skills/**/SKILL.md`), and the canonical
   guard covers `.claude/skills/domains/**/SKILL.md`. An archive
   directory under `.claude/skills/` keeps archived skills in the
   counted catalog (and in the derived map/inventory).
   *Mitigation:* OQ2's "archive" default = git-history-only deletion
   with a pointer in the plan, or a location outside `.claude/skills/`.

8. **R-DEV8 — Severity: MEDIUM — ceremony surface per wave is large
   and partly a different pipeline.** Everything this plan touches is
   canonical-guarded: `domains/**/SKILL.md`, `domains/*/team-personas.md`,
   `domains/*/pitfalls.yaml`, `policies/*.yaml` (the grandfather
   policy itself), core SKILL.md (the inventory block), and
   `scripts/install.sh` (if profile logic changes). Each wave is
   therefore an Owner-GPG sentinel ceremony. Additionally, the W1
   folds EDIT existing core SKILL.md files — per the framework's own
   discipline that class rides the SP-NNN `/skill-review` pipeline
   (with soak, unless Owner-waived per the SP-042 precedent), which
   is a different and slower pipeline than the sunset/graduate
   mechanics.
   *Mitigation:* batch each wave's guarded edits into one signed
   wake-up script (land-plan155/156 pattern) and get the Owner's
   soak-waiver decision for the fold SPs ratified at OQ time.

## Must-fix (blocking)

1. **Replace `--fast` in every wave's Check with the real CI set.**
   Minimum per-wave Check block:
   `bash .claude/scripts/validate-governance.sh` (full) &&
   `python3 .claude/scripts/check-claude-md-claims.py` &&
   `bash .claude/scripts/local/verify-counts.sh --no-tests` &&
   `python3 .claude/scripts/gen-command-skill-hook-map.py --check` &&
   the skill-inventory idempotency diff (validate.yml:801-815 command)
   && `python3 .claude/scripts/check-install-profiles.py` &&
   `python3 .claude/scripts/check-docs-freshness.py --format=text` &&
   `python3 .claude/scripts/check-tier-boundaries.py` (fold waves),
   plus the full `.claude/hooks/tests/ + .claude/scripts/tests/ +
   .claude/scripts/optimizer/tests/` pytest run at least once
   pre-push (that is what `hook-tests-python-matrix` actually runs,
   together, on 3.9-3.12 — not the single cap test file).
2. **Write the complete derived-surface reconcile checklist into the
   plan** (it is the deliverable W1 exercises and W2/W3 reuse):
   CLAUDE.md:52 counts; INSTALL.md:531; README.md count literals;
   `docs/COMMAND-SKILL-HOOK-MAP.md` regen (`--write`);
   `ceo-orchestration/SKILL.md` inventory re-embed;
   `scripts/profiles/profiles.json` + `scripts/install.sh` profile
   logic (bijection both ways); docs-freshness allowlist entries for
   deleted paths referenced by PLAN-153 plan/debate/artifacts;
   `docs/GUIA-COMPLETO.md` + `.pt-BR` twin.
3. **Counts reconcile in EVERY wave, same commit as the catalog
   delta.** Add the reconcile items + claims/counts/map/inventory
   Check commands to W2 and to each W3 graduation step; require one
   revertable, fully-reconciled commit per disposition step (no
   intermediate red states between "skills changed" and "counts
   reconciled").
4. **OQ3 rider:** the cap literal change must carry the same-commit
   edit of `_EXPECTED_DOMAIN_CAP` in
   `.claude/scripts/tests/test_squad_grandfather_cap.py` (and refresh
   the stale policy header comments citing 25/22).
5. **Wave 0 precondition:** main Validate green on current HEAD
   (i.e. the `Ceo` runner unblocked and run `29248385951`-class
   backlog cleared) before any PLAN-157 commit lands.
6. **Pin the OQ2 archive location outside `.claude/skills/`**
   (default: git-history-only deletion + pointer), so archived skills
   drop out of every counter, the derived map, and the guard surface.

## Nice-to-have (advisory)

1. Fix the pre-existing stale literals as W1 riders: README.md:54/72/
   184 still say 151/101 (disk: 166/116) and slip BOTH mechanical
   gates today because their phrasing matches none of the gate
   regexes; docs/ARCHITECTURE.md:55 says "101 skills across 29 domain
   profiles"; docs/GUIA-COMPLETO.md:74 says "151 skills".
2. Update `verify-counts.sh`'s dead domain regexes — `(\d+) skills
   across 29 domain` and `DOMAINS\*\* \(29 profiles\) \| (\d+)`
   hardcode "29", which no doc says anymore (37 domain dirs on disk),
   so the domain-count rule has silently lost citation coverage since
   PLAN-153. Re-anchor them (and they will shift again when this plan
   removes 4-6 domain dirs).
3. Cite the roster by pattern, not line number: `SQUAD_GRANDFATHER`
   is at validate-governance.sh:318 today (the plan/test say :284);
   line pins rot.
4. Clean-clone proof (`git clone --local` into scratchpad + run the
   new/changed tests) before each wave's push — the S266
   gitignored-staged class applies especially to W2/W3 if bundles are
   staged under a gitignored `PLAN-157/staged/` per the PLAN-155/156
   pattern.
5. Budget: 4 `/architect` bundles ≈ 50+ authored files + 3-4 signed
   ceremonies + per-wave reconciles. 300-450k tokens / 3 sessions is
   the optimistic edge; plan for 4 (or pre-authorize splitting W3)
   rather than discovering it mid-wave with context_risk already
   high.
6. Batch each wave's guarded edits + sentinels into a single
   Owner-run landing script (the land-plan155/156 pattern) so the
   Gate-1 cache-stable files (CLAUDE.md, ceo-orchestration/SKILL.md)
   are only touched at closeout ceremonies.

## Unseen by the original plan

1. **README.md is already drifted and the gates cannot see it** —
   living proof that "run verify-counts + claims" is not the same as
   "counts reconciled". The plan needs an explicit manual
   literal-sweep item, not just the two checkers.
2. **The install-profiles bijection** (`check-install-profiles.py`,
   hard gate): `scripts/profiles/profiles.json` references all 8
   squads; removing a domain dir without updating profiles.json AND
   the mirrored `install.sh` logic fails CI. `install.sh` is
   canonical-guarded, so this widens the ceremony scope.
3. **The skill-inventory block lives inside a Gate-1 cache-stable,
   canonical-guarded file** (`ceo-orchestration/SKILL.md`) with its
   own byte-diff CI gate — every catalog change forces a guarded edit
   of a file the operating contract says to touch only at closeout.
4. **translations-drift**: `docs/GUIA-COMPLETO.md` and its `.pt-BR`
   twin both reference the imported squads and have their own drift
   workflow.
5. **docs-freshness on deleted paths**: PLAN-153's plan/debate/
   artifacts reference `skills/domains/desktop|dotnet/...`; sunsets
   break those refs under a BLOCKING gate — allowlist entries (not
   history rewrites) are the fix, and they need to be in the wave's
   commit.
6. **Folds are a different pipeline**: merging content into existing
   core SKILL.md files is the SP-NNN `/skill-review` class (soak
   discipline), not the same mechanics as sunset/graduate — W1's
   single-wave framing hides a potential multi-day dependency unless
   the Owner waives soak at ratification.

## What I would NOT change

- **Sunsets before graduations.** Cheapest wave first exercises the
  entire reconcile machinery on the smallest diff and produces the
  reusable checklist for W2/W3. Do not reorder.
- **Per-wave `test_squad_grandfather_cap.py` runs.** Right test; it
  is collected by both the validate job and the Python matrix, so
  green there is directly CI-relevant.
- **OQ3 as an explicit Owner question** rather than silently riding
  the closeout — cap changes are Owner-gated by the policy's own
  contract; keep it that way.
- **The honest evidence framing** (telemetry blind ≠ telemetry says
  kill) and flagging the criterion substitution for ratification —
  do not let round-2 "improve" this into a fake data-driven claim.
- **Wave 0 baseline snapshot** (`PLAN-157/baseline.md`) — cheap,
  makes every later diff auditable, keep it.
