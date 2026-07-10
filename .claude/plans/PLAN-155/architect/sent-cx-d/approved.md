# SENT-CX-D — PLAN-155 Wave 6 pair-rail-teeth sentinel (round-1 DRAFT)

Drafted S266 (2026-07-09, Wave 0 prep) by the CEO under the Owner's
delegation; **inert until the Owner fills the anchor and detach-signs**
(`approved.md.asc`, dual rail per ADR-121). Scope below is the EXACT
guarded target set of the Wave 6 staged overlay
`.claude/plans/PLAN-155/staged/wave-6/` (mirror layout = repo-relative
targets). The landing ceremony asserts `touched − SIGNED SCOPE = ∅` (S258
rule) before applying.

**KERNEL-class, CONDITIONAL (pair-rail S265 F5):** all three guarded
surfaces below are in `_KERNEL_PATHS`
(`check_arbitration_kernel.py:180,133,135` —
`check_pair_rail.py` / `.claude/dispatcher/**` / `validate.yml`). If Wave
6 touches ANY of them, the apply env MUST carry
`CEO_KERNEL_OVERRIDE=PLAN-155-CODEX-PAIRRAIL-TEETH` +
`CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` (audited per ADR-031 §kernel-override)
on top of this sentinel; the SENT-E/S261 Owner-shell apply route satisfies
the same requirement with this signed sentinel as the authorization
record. `validate.yml` is expected-touched (CI teeth + the Wave 1/5
pytest/matrix paths that were deferred to this wave's CI commit), so the
override is expected-required.

Landing order (binding): PLAN-154 SENT-F → SENT-CX-A → (Waves 2/3
unguarded) → SENT-CX-E → SENT-CX-B → SENT-CX-C → **SENT-CX-D** (last).
Anchor (`8c032dfdfbef63bd5a25a504d4bef659df68dbd2`) taken on main after SENT-CX-C lands.

Scope notes: `check_pair_rail.py` and `.claude/dispatcher/**` are
CONDITIONAL — in scope only if the inverted Stop-hook rail / routing
matrix requires touching them (decided at signing from the Wave 6 design;
the Owner strikes unused lines — a struck line narrows scope, never
widens it). The NEW unguarded companions (Stop-rail + pre-push + chain
-scan scripts and their tests) land under `.claude/scripts/`,
`scripts/tests/`, `.claude/hooks/tests/`, and `templates/codex/` — none
canonical-guarded, named here as a class so the S258 assert set is
understood at signing. The Wave 6 exit evidence (live Stop-block
transcript, debate A5) archives under `PLAN-155/artifacts/` (unguarded).

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs 71a2ef5f8dc52aabe8ba2c848e65b7c6b895a5c1
Anchor-SHA: 8c032dfdfbef63bd5a25a504d4bef659df68dbd2
Plans: PLAN-155
Kernel-Override: PLAN-155-CODEX-PAIRRAIL-TEETH (+ CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT; covers the KERNEL `.github/workflows/validate.yml` row — required because BOTH ceremony riders touch it)
Scope:
  Wave 6 — inverted pair-rail (Codex operates, `claude -p` reviews) +
  CI/pre-push teeth for the two ADVISORY rails (debate A2 RED-on-absence
  semantics; A5 Stop-block transcript gates the matrix row), landed as
  the complete staged overlay of PLAN-155/staged/wave-6/ (reconciled S265
  against the on-disk overlay — MANIFEST-B §7 flagged the original draft's
  file NAMES as divergent from the implementation, which added a NEW
  canonical hook rather than editing check_pair_rail.py; this is the
  ACTUAL staged set):
  - .claude/hooks/check_codex_stop_review.py
  - .claude/hooks/tests/test_codex_advisory_teeth.py
  - .claude/hooks/tests/test_codex_stop_review.py
  - scripts/codex-advisory-teeth.py
  - .claude/scripts/test-env-hygiene-allowlist.yaml
  - templates/codex/hooks.json
  - templates/codex/config.toml.hooks-example
  - templates/codex/pre-push-review-gate.sh
  - .github/workflows/validate.yml
Amends: none (no SPEC/v1 row; the ADVISORY rails stay ADVISORY — the
  teeth are documented as backstops, never as promotion to ENFORCED).
Rider note (MANIFEST-B §4, BINDING): `.github/workflows/validate.yml` is
  patched by TWO riders — wave-6/ceremony-riders/validate-yml-advisory-teeth.diff
  AND wave-5/ceremony-riders/validate-yml-installer-matrix.diff (the
  latter has NO override coverage under SENT-CX-C, so it rides THIS
  sentinel's PLAN-155-CODEX-PAIRRAIL-TEETH override). Both insert a new
  step at the SAME anchor (~validate.yml:341/342); naive sequential
  `git apply` FAILS (line-shift). Apply with `patch -p1 --fuzz=3 < R5`
  then `patch -p1 --fuzz=3 < R6`, verify YAML parses, both PLAN-155 steps
  land. `scripts/codex-advisory-teeth.py` and the two `check_*` files are
  canonical/unguarded (NONE in `_KERNEL_PATHS`); the override is solely
  for validate.yml. `test-env-hygiene-allowlist.yaml` base = PLAN-154
  SENT-F (this wave appends +2 file blocks) — double-touched, listed in
  both ceremonies.
<!-- END SIGNED SCOPE -->
