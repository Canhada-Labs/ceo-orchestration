# SENT-CX-C — PLAN-155 Wave 5 installer sentinel (round-1 DRAFT)

Drafted S266 (2026-07-09, Wave 0 prep) by the CEO under the Owner's
delegation; **inert until the Owner fills the anchor and detach-signs**
(`approved.md.asc`, dual rail per ADR-121). Scope below is the EXACT
guarded target set of the Wave 5 staged overlay
`.claude/plans/PLAN-155/staged/wave-5/` (mirror layout = repo-relative
targets). The landing ceremony asserts `touched − SIGNED SCOPE = ∅` (S258
rule) before applying. No kernel rows in this wave — sentinel-only
(canonical guard on `scripts/install.sh`).

**Anchor note (binding):** PLAN-153's install.sh waves (SENT-B lifecycle +
SENT-E deny-baseline) LANDED on main 2026-07-08 — the sequencing
precondition in PLAN-155 §Approach is SATISFIED. The anchor
(`__ANCHOR_SHA__`) is taken on **post-PLAN-153 main**, AND after PLAN-154
SENT-F lands (F-before-CX order) — if SENT-F also touches
`scripts/install.sh`, the Wave 5 staged copy MUST be rebased on the
SENT-F version before this sentinel applies (two signed sentinels racing
one guarded file is exactly what the S258 scope assert exists to trip).

Landing order (binding): PLAN-154 SENT-F → SENT-CX-A → (Waves 2/3
unguarded) → SENT-CX-E → SENT-CX-B → **SENT-CX-C** → SENT-CX-D. Wave 3b
(SENT-CX-E) MUST land before this wave ships the `.codex` kill-switch
paths via the installer, so the hooks the installer copies already carry
the protection.

Scope notes: `scripts/upgrade.sh` is CONDITIONAL — in scope only if the
`--harness` round-trip (debate A11 case 6) requires touching it; the
Owner strikes the line if not. The `scripts/tests/` companion is a NEW
unguarded file (named so the A11 nine-case matrix + its same-commit
validate.yml wiring are not discovered at execution time; the
validate.yml touch itself rides SENT-CX-D scope per the Wave 1/6
decision).

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs 71a2ef5f8dc52aabe8ba2c848e65b7c6b895a5c1
Anchor-SHA: __ANCHOR_SHA__
Plans: PLAN-155
Scope:
  Wave 5 — installer `--harness codex` (debate A7 arming verification,
  A9 lifecycle symmetry incl. the `.git/` pre-push third surface, A10
  collision policy, A11 nine-case matrix, A15 version-skew probe),
  landed as the complete staged overlay of PLAN-155/staged/wave-5/
  (reconciled S265 against the on-disk overlay — MANIFEST-B §7):
  - scripts/install.sh
  - scripts/upgrade.sh
  - scripts/_codex_harness.sh
  - scripts/tests/test-install-harness-codex.sh
  - scripts/tests/_case2_probe.py
Amends: none (no SPEC/v1 row; default `claude` path byte-identical when
  `--harness` is absent — `diff -r` regression case 1 of the A11 matrix).
Reconciliation note (S265): ADDED `scripts/_codex_harness.sh` (the sourced
  ~200-line helper) and `scripts/tests/_case2_probe.py`; corrected the
  test filename `test-install-codex-harness.sh` → `test-install-harness-codex.sh`.
  `scripts/upgrade.sh` IS staged (the `--harness` value round-trips
  through upgrade replay, A11 case 6). NONE of these is in `_KERNEL_PATHS`
  (install.sh/upgrade.sh are canonical-guarded, sentinel-only — no
  kernel-override needed). The wave-5 `validate-yml-installer-matrix.diff`
  rider does NOT land under this sentinel: validate.yml is KERNEL and this
  sentinel carries no override → that rider rides SENT-CX-D's
  PLAN-155-CODEX-PAIRRAIL-TEETH (MANIFEST-B §4).
<!-- END SIGNED SCOPE -->
