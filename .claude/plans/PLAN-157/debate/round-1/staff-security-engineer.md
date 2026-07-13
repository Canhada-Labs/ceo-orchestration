---
round: 1
archetype: Staff Security Engineer
skill: security-and-auth
agent_persona: Staff Security (staff tier, VETO on governance-enforcement surfaces per team.md)
generated_at: 2026-07-13T00:00:00Z
---

## Verdict

ADJUST

## Summary (≤ 3 bullets)

- The plan drains the 8 PLAN-153 Wave D squads out of `SQUAD_GRANDFATHER`
  (validate-governance.sh:284) and the policy roster
  (grandfather-cap.policy.yaml:47-83), returning `current: 32→24`. From an
  enforcement standpoint this is strictly *tightening*: every removal
  converts that squad name from WARNING-tier to ERROR-tier under the
  ADR-009 bundle gate. Direction of travel is correct and welcome.
- Strong: the plan never proposes weakening a guard, its success criteria
  demand "ERROR-free on bundle validation (not WARNING-suppressed)", and
  the policy YAML it must edit is the best-protected artifact in the
  touch set — canonical-sentinel-gated (`_CANONICAL_GUARDS`
  `.claude/policies/*.yaml`, check_canonical_edit.py:144) AND
  kernel HARD-DENY with no sentinel escape
  (check_arbitration_kernel.py:93-95, requires `CEO_KERNEL_OVERRIDE` +
  `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT`, Owner-only, audit-logged).
- Weak: the plan's mechanics section is wrong about *which* pipeline each
  guarded write rides (SP-NNN only covers patches to EXISTING SKILL.md;
  new files ride the separate `CEO_SKILL_BOOTSTRAP` two-factor gate;
  guarded-file DELETION rides neither), and it inherits — without
  noticing — a real tamper gap: the roster cross-check between the
  unguarded bash array and the kernel-guarded policy members is
  count-only, not identity-based (test_squad_grandfather_cap.py:407-433).

## Risks

1. **R-SEC1 — HIGH — Guarded-pipeline mapping is mechanically wrong,
   inviting mid-execution improvisation around guards.**
   Wave 2 says "New SKILL.md files ride the SP-NNN pipeline where
   required". Ground truth (check_skill_patch_sentinel.py): the SP-NNN
   gate requires a proposal with matching `skill_slug` in status
   shadow/promoted + `CEO_SKILL_PATCH_SHA` — it structurally cannot cover
   a SKILL.md that does not exist yet. Brand-new files (all +5 graduation
   skills, any relocated skill at its new path) ride the bootstrap
   bypass: `CEO_SKILL_BOOTSTRAP=<slug>` + `CEO_SKILL_BOOTSTRAP_ACK=I-ACCEPT`,
   target-must-not-exist, scope-checked, audit-emitted
   (check_skill_patch_sentinel.py:200-259) — on top of the canonical
   sentinel. Conversely, Wave 1's folds edit EXISTING core SKILL.md files
   (`core/architecture-decisions` etc.) — that is exactly the SP-NNN +
   7-day-soak surface (ADR-031; cf. SP-034 soak precedent), yet Wave 1
   never mentions SP-NNN at all. A plan that mislabels its own gates is
   how an autonomous session ends up "creatively" routing around one.
   *Mitigation:* rewrite the mechanics paragraph + per-wave checklists
   with the correct gate per operation class (see Must-fix 1).
2. **R-SEC2 — HIGH — Roster cross-check is count-only; a name-swap in the
   unguarded bash array passes CI green.**
   `validate-governance.sh` is NOT in `_CANONICAL_GUARDS` (verified: only
   lessons scripts under `.claude/scripts/` are listed;
   check_canonical_edit.py:129-132) and never reads the policy YAML. The
   compensating control, test_squad_grandfather_cap.py, asserts only
   `len(array) <= cap` and `len(array) == current` — never membership
   identity. So: remove `jvm`, add `evil-squad` to `SQUAD_GRANDFATHER`
   (count unchanged) → all tests pass, and any
   `.claude/skills/domains/evil-squad/` directory is evaluated at
   WARNING-tier instead of ERROR-tier, while the kernel-guarded members
   list silently disagrees. This is the exact "count ≠ identity" test
   defect class this repo has already paid for elsewhere. PLAN-157 edits
   both surfaces and this test's expectations anyway — cheapest possible
   moment to close the gap.
   *Mitigation:* add a set-equality assertion
   `set(SQUAD_GRANDFATHER) == set(policy members)` to the test in Wave 0
   or Wave 1 (test file is unguarded; one-commit change).
3. **R-SEC3 — MEDIUM — Non-atomic per-squad transitions create either a
   dormant-allowlist window or CI-red thrash.**
   Two orderings go wrong: (i) squad dir removed (sunset) while its
   `SQUAD_GRANDFATHER`/members entries linger → a stale allowlist entry;
   anyone who later recreates a dir with that name (e.g. `desktop`)
   inherits WARNING-tier treatment instead of the ERROR-tier a new squad
   must face. (ii) roster entry removed before the graduation bundle is
   complete → instant ERROR (fail-closed, but burns a red Validate run
   and pressures for a "temporary" re-grandfather — a ratchet reversal).
   The plan implies both-lists removal but never states atomicity.
   *Mitigation:* per-squad atomic commit rule — bundle-complete (or
   dir-removed) + `SQUAD_GRANDFATHER` removal + policy `members`/`current`
   decrement land in ONE commit; per-wave check asserts none of the
   drained names remain in either list and (for sunsets) the dir is gone.
4. **R-SEC4 — MEDIUM — Transitional headroom: `cap: 32` while `current`
   drains to 24 re-opens the "silent re-import" slot the S262 note
   explicitly closed.**
   The mechanical gate is `len(array) <= cap`. From Wave 1 to closeout
   there are up to 8 free slots in which an addition to both surfaces
   passes the cap test without any cap-raise ceremony. The policy side is
   kernel-gated (Owner-only env pair), so the practical residual is
   Owner-env hygiene and process drift during the plan's own
   kernel-override ceremonies — but "NO headroom left on purpose"
   (policy.yaml:36) is a stated invariant and it is false for the entire
   execution window. This also answers OQ3: lowering the literal is a
   REAL control, not cosmetic — with `cap == current`, any re-import
   fails the mechanical gate and forces a conscious Owner-gated raise.
   *Mitigation:* ratify OQ3 = yes, and prefer `cap := current` at every
   wave boundary (it rides the same kernel-override ceremony as the
   `current:` edit; the test's `_EXPECTED_DOMAIN_CAP` is in an unguarded
   file and pins cap in BOTH directions, so each lowering is a one-line
   test edit in the same commit). At minimum, document the accepted
   headroom window and the `unset CEO_KERNEL_OVERRIDE*` discipline at the
   end of each ceremony script.
5. **R-SEC5 — MEDIUM — Sunset/archive can leave a half-dead skill live in
   the catalog, or lose provenance without record.**
   If "archive" keeps content anywhere under `.claude/skills/`, the
   catalog/loader and `activation_triggers` frontmatter can still
   activate a skill that will never again receive security review — a
   classic unmaintained-but-reachable surface. Separately, the imported
   skills carry MIT provenance (`inspired_by:` blocks,
   `Skill-Import-Attestation` trailers); an archive that strips these
   loses the licensing/attestation record. `csharp-testing` and
   `windows-desktop-e2e` carry no auth/crypto content (testing-domain
   skills), so the loss risk is provenance/record, not a security-content
   hole — but the control should be stated generically. Note the reopen
   gate (sunset_reopen_window_days: 14) only watches spawn hints for 14
   days; it is not a content-preservation control.
   *Mitigation:* archive destination OUTSIDE `.claude/skills/` (e.g.
   `.claude/plans/PLAN-157/archive/` or docs/), provenance trailers
   preserved verbatim, and the already-required "pointer" names the
   archive path + removal commit.
6. **R-SEC6 — LOW — Test-expectation sync is an unstated edit target.**
   OQ3 (and per-wave cap lowering, if adopted) requires editing
   `_EXPECTED_DOMAIN_CAP = 32` (test_squad_grandfather_cap.py:207); the
   plan lists the test only as a Check command, not as a file it must
   change. Also `_EXPECTED_DOMAIN_CURRENT = 25` is a dead, stale constant
   (no equality assertion uses it) — misleading to the next editor.
   *Mitigation:* name the test file in the Wave that changes `cap:`;
   delete or repair the dead constant in passing.

## Must-fix (blocking)

1. **Correct the guarded-pipeline mapping and enumerate the Owner-gated
   operations per wave.** For each operation class, state the actual
   gate: (a) policy YAML `current`/`members`/`cap` edits → canonical
   sentinel + arbitration-kernel override pair (Owner-only, once per
   wave, audit event `kernel_override_used`); (b) NEW SKILL.md (graduation
   skills, relocations) → canonical sentinel + `CEO_SKILL_BOOTSTRAP` +
   `_ACK` two-factor, one slug at a time; (c) edits to EXISTING SKILL.md
   (Wave 1 folds into core) → canonical sentinel + SP-NNN
   (shadow/promoted) + `CEO_SKILL_PATCH_SHA`, with the ADR-031 soak
   window acknowledged in the schedule; (d) DELETION of guarded files
   (sunset scaffolds) → not covered by any Edit/Write hook; route through
   the established Owner-run land-script pattern under the plan sentinel.
   The plan must not leave an autonomous session to discover (and
   improvise around) these gates mid-wave.
2. **Close the roster identity gap while touching this surface (R-SEC2):**
   add `set(SQUAD_GRANDFATHER) == set(domain_bundles.members)` to
   test_squad_grandfather_cap.py in Wave 0/1. Without it, the unguarded
   bash array can be name-swapped CI-green against the kernel-guarded
   policy, and this plan's own 8 removals are exactly the churn that
   could mask such a swap.
3. **State per-squad atomicity (R-SEC3):** one commit per squad carrying
   dir change + `SQUAD_GRANDFATHER` removal + policy decrement; per-wave
   assertion that drained names appear in neither list and sunset dirs
   are gone. No transitional commits where the two rosters disagree.
4. **Resolve OQ3 as a security decision, not cosmetics (R-SEC4):** ratify
   yes; adopt `cap := current` at each wave boundary (preferred) or
   explicitly accept and document the ≤8-slot headroom window for the
   plan's duration, including kernel-override env unset discipline in
   every ceremony script.

## Nice-to-have (advisory)

1. Archive hygiene bundle (R-SEC5): destination outside
   `.claude/skills/`, provenance trailers preserved, pointer includes
   archive path + commit. Supports the CEO default of archive-over-
   relocate — from an attack-surface view, archiving beats moving a
   zero-signal skill into a live domain.
2. Delete/repair the dead `_EXPECTED_DOMAIN_CURRENT = 25` constant while
   editing the test (R-SEC6).
3. Schedule note for Wave 1: SP-NNN soak (7d parallel-shadow precedent,
   SP-034) does not fit inside a single session; sequence folds so soak
   runs while Waves 2-3 execute.
4. Consider (in a FUTURE kernel-extension plan, not this one) guarding
   domain-level `task-chains.yaml` for parity with `team-personas.md` +
   `pitfalls.yaml`, and/or adding `validate-governance.sh` to
   `_CANONICAL_GUARDS`. Both require the KERNEL-HARD-DENY double-gate to
   extend the guard list; the Must-fix 2 identity test is the cheap
   compensating control in the meantime.

## Unseen by the original plan

1. The count-only roster cross-check (R-SEC2). The plan cites
   `test_squad_grandfather_cap.py:207` as its enforcement anchor without
   noticing the test never compares membership identity, and that
   `validate-governance.sh` is entirely outside `_CANONICAL_GUARDS`.
2. The `CEO_SKILL_BOOTSTRAP` two-factor gate. "SP-NNN where required"
   does not describe how any NEW SKILL.md actually lands; the SP gate
   cannot cover nonexistent targets by design (bootstrap-only-if-absent,
   check_skill_patch_sentinel.py:225-230).
3. Guarded-file deletion has no defined path. Sunset removes canonical
   files (SKILL.md under `domains/**`); Edit/Write hooks never fire on
   `git rm`, and bash-safety independently flags canonical-path-touching
   commands — the plan is silent on the ceremony vehicle.
4. The transitional headroom window (R-SEC4): `cap: 32` is only
   scheduled to move at closeout, so "no headroom by design" is untrue
   for the whole execution period.
5. The kernel HARD-DENY on the policy YAML means every `current:`
   decrement is an Owner-present operation — a spawned sub-agent cannot
   set the override env pair by design. The 3-session budget implicitly
   assumes Owner ceremony availability per wave; the plan never says so.
6. Graduation creates 4 new domain `task-chains.yaml` + `examples/`
   files that are NOT canonical-guarded (guard list covers only
   `team-personas.md` + `pitfalls.yaml` at domain level) — new
   governance-adjacent surface landing unguarded, worth a recorded
   accept-or-defer.

## What I would NOT change

- The drain itself and its direction: every removal from
  `SQUAD_GRANDFATHER` strengthens enforcement (WARNING→ERROR). No part of
  this plan weakens a guard, and pressure-test (a) confirms removal
  creates no fail-open window — the residual windows are ordering
  (R-SEC3) and the pre-existing identity gap (R-SEC2), not the removals.
- Success criterion "CI ERROR-free on bundle validation (not
  WARNING-suppressed)" — exactly the right posture; do not soften it to
  warnings-allowed to make graduations cheaper.
- Keeping policy YAML edits inside the sentinel + kernel-override double
  gate. Nobody should "streamline" this by exempting
  `grandfather-cap.policy.yaml` from `_KERNEL_PATHS` for the plan's
  convenience — the ceremony friction IS the control (answer to
  pressure-test (e): the YAML is tamper-guarded twice, and it must stay
  that way).
- Sunsets-before-graduations ordering (Wave 1 first): it shrinks the
  WARNING-tier surface fastest and takes the cheap risk reductions before
  the expensive authoring.
- Wave 0 baseline snapshot of roster membership — a tamper-evident
  starting point for exactly the identity-drift class flagged above.
- The OQ1 honesty: refusing to fabricate a telemetry ranking from an
  instrument that is structurally blind, and flagging the criterion
  substitution for Owner ratification instead of burying it.
