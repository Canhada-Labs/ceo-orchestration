# SENT-CX-E — PLAN-155 Wave 3b kill-switch guard-extension sentinel (round-1 DRAFT)

Drafted S266 (2026-07-09, Wave 0 prep) by the CEO under the Owner's
delegation; **inert until the Owner fills the anchor and detach-signs**
(`approved.md.asc`, dual rail per ADR-121). Scope below is the EXACT
guarded target set of the Wave 3b staged overlay
`.claude/plans/PLAN-155/staged/wave-3b/` (mirror layout = repo-relative
targets). The landing ceremony asserts `touched − SIGNED SCOPE = ∅` (S258
rule) before applying.

**KERNEL-class — the override covers BOTH kernel rows of this wave:**
(1) `check_canonical_edit.py` is in `_KERNEL_PATHS`
(`check_arbitration_kernel.py:79`) and the `_CANONICAL_GUARDS` guard-list
extension is the double-gated edit class of PLAN-080-PHASE-0B /
PLAN-081-PHASE-2 (`check_canonical_edit.py:149-152` +
`check_arbitration_kernel.py:302-304`); (2) `SessionStart.py` IS in
`_KERNEL_PATHS` (`check_arbitration_kernel.py:201`, PLAN-153 landing's
kernel-extension — pair-rail S265 F2 corrected the earlier
"sentinel-only" claim). The apply env MUST carry
`CEO_KERNEL_OVERRIDE=PLAN-155-CODEX-KILLSWITCH-GUARD-EXTENSION` +
`CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` (audited per ADR-031 §kernel-override)
on top of this sentinel, covering both rows; `_lib/effective_config.py`
is canonical-guarded, sentinel-only (not kernel). The SENT-E/S261
Owner-shell apply route satisfies the same requirement with this signed
sentinel as the authorization record.

Landing order (binding): PLAN-154 SENT-F → SENT-CX-A → (Waves 2/3
templates, unguarded — they FIX the kill-switch path set this wave
protects) → **SENT-CX-E** → SENT-CX-B → SENT-CX-C → SENT-CX-D. SENT-CX-E
MUST land before SENT-CX-C ships the `.codex` kill-switch paths via the
installer. `check_canonical_edit.py` is touched by BOTH SENT-CX-A (seam
migration) and this sentinel (guard-list extension): the anchor
(`fdb182215c4fce8041ec6b70d99b16a6ca5da970`) is taken on main AFTER SENT-CX-A lands, and the Wave
3b staged copy is rebased on the post-A file.

Guarded-surface effect (what this sentinel authorizes): extend
`_CANONICAL_GUARDS` (`check_canonical_edit.py:137-142` region) to cover
the Codex kill-switch surface — `.codex/hooks.json`,
`.codex/config.toml`, `.codex/rules/ceo.rules`, `requirements.toml`,
operator `AGENTS.md`; extend the SessionStart boot-time hash re-check
beyond `_GATE_1_FILES` (`SessionStart.py:48-54,:79`) to re-hash that
surface, defined RED when a kill-switch file is missing or mutated
(debate A2 RED-on-absence — a silent fail-open here recreates the S254
dead-gate class); extend the `effective_config.py` disk census
(`effective_config.py:192-199`) so a deregistered kill-switch
registration surfaces as a tamper class. The three `hooks/tests/`
pin-test companions are unguarded, ride the same commit, and are named so
the coupling is not discovered at execution time.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs 71a2ef5f8dc52aabe8ba2c848e65b7c6b895a5c1
Anchor-SHA: fdb182215c4fce8041ec6b70d99b16a6ca5da970
Plans: PLAN-155
Kernel-Override: PLAN-155-CODEX-KILLSWITCH-GUARD-EXTENSION (+ CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT; covers BOTH kernel rows: check_canonical_edit.py AND SessionStart.py)
Scope:
  Wave 3b — kill-switch guard extension (debate A8: guard list + boot
  tripwire + census; closes the circular-disarm gap; flips the
  capability-matrix config/kill-switch row from ABSENT), landed as the
  complete staged overlay of PLAN-155/staged/wave-3b/ (reconciled S265
  against the on-disk overlay — MANIFEST-B §7):
  - .claude/hooks/check_canonical_edit.py
  - .claude/hooks/SessionStart.py
  - .claude/hooks/_lib/effective_config.py
  - .claude/hooks/tests/test_check_canonical_edit.py
  - .claude/hooks/tests/test_session_start.py
  - .claude/hooks/tests/test_effective_config.py
  - .claude/hooks/tests/test_codex_killswitch_teeth.py
Amends: none (no SPEC/v1 row; ADR-161 — landed under SENT-CX-A — records
  the guard-extension override alongside the PLAN-080/PLAN-081
  precedents when the matrix row flips).
Reconciliation note (S265): ADDED `test_codex_killswitch_teeth.py` (the
  behavioral positive-control — 5 kill-switch paths replayed as
  subprocesses on the shipped hooks.json command line → deny; copied
  marker still reddens; sentinel-gated grant). `test_session_start.py`
  additionally carries the S265 suite-isolation fix (per-test
  CEO_PROJECT_STATE_DIR via patch.dict) so the killswitch baseline no
  longer leaks across the in-process suite.
<!-- END SIGNED SCOPE -->
