# SENT-CX-A — PLAN-155 Wave 1 host-adapter sentinel (round-1 DRAFT)

Drafted S266 (2026-07-09, Wave 0 prep) by the CEO under the Owner's
delegation; **inert until the Owner fills the anchor and detach-signs**
(`approved.md.asc`, dual rail per ADR-121 — key in BOTH
`sentinel-signers.txt` and the YAML registry). Scope below is the EXACT
guarded target set of the Wave 1 staged overlay
`.claude/plans/PLAN-155/staged/wave-1/` (mirror layout = repo-relative
targets), under debate-A1 **seam option (b)** — a single shared
`resolve()` seam in `_lib/adapters/__init__.py`, with ONLY the four
ENFORCED hooks migrated in Wave 1 — the CEO RECOMMENDATION in
`PLAN-155/artifacts/dispatch-surface-inventory-A1.md`, to be RATIFIED BY
THE OWNER AT THIS SIGNING. If the Owner ratifies option (a)
(per-entrypoint migration) instead, this draft is VOID and is re-drafted
enumerating the full ~23-file set — no execution-time widening either way.
The landing ceremony asserts `touched − SIGNED SCOPE = ∅` (S258 rule)
before applying.

**KERNEL-class (pair-rail S265 F1):** `_lib/adapters/codex.py`,
`_lib/adapters/__init__.py`, and `_lib/contract.py` are in `_KERNEL_PATHS`
(`check_arbitration_kernel.py:165,168,85`; ADR-116-AMEND-1
kernel-extension-v2 via the PLAN-153 landing). The apply env MUST carry
`CEO_KERNEL_OVERRIDE=PLAN-155-CODEX-HOST-ADAPTER` +
`CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` (audited per ADR-031 §kernel-override)
on top of this sentinel; the SENT-E/S261 Owner-shell apply route satisfies
the same requirement with this signed sentinel as the authorization record.

Landing order (binding): **PLAN-154 SENT-F lands BEFORE every SENT-CX**;
within PLAN-155 the order is SENT-CX-A → (Waves 2/3 templates, unguarded
L2, land direct) → SENT-CX-E → SENT-CX-B → SENT-CX-C → SENT-CX-D. Anchor
(`__ANCHOR_SHA__` below) is taken on main AFTER PLAN-154 SENT-F lands. If
SENT-F staged a `check_bash_safety.py` edit, the Wave 1 staged copy of that
file MUST be rebased on the SENT-F version before this sentinel applies.

Scope notes (bind the bullets below): `_lib/contract.py` is CONDITIONAL —
in scope only if registry constants move or the debate-A2 coherence gate
lands contract-side (decided at this signing; the Owner strikes the line
if adapter-side is chosen). `check_canonical_edit.py` here covers the
seam migration ONLY — its guard-list extension is SENT-CX-E's scope.
`ADR-161` (new file) rides this ceremony batch because `.claude/adr/` is
guarded including new files (S261 confirmation). The `hooks/tests/` +
fixture paths are unguarded same-commit companions, named so the coupling
is not discovered at execution time (not sentinel-blocked).

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs 71a2ef5f8dc52aabe8ba2c848e65b7c6b895a5c1
Anchor-SHA: __ANCHOR_SHA__
Plans: PLAN-155
Kernel-Override: PLAN-155-CODEX-HOST-ADAPTER (+ CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT)
Scope:
  Wave 1 — Codex host-adapter linchpin (debate A1 seam option (b), A2
  coherence gate, A3/A4 anti-vacuous controls, A14 characterization
  pre-gate), landed as the complete staged overlay of
  PLAN-155/staged/wave-1/:
  - .claude/hooks/_lib/adapters/codex.py
  - .claude/hooks/_lib/adapters/__init__.py
  - .claude/hooks/check_canonical_edit.py
  - .claude/hooks/check_bash_safety.py
  - .claude/hooks/check_plan_edit.py
  - .claude/hooks/check_arbitration_kernel.py
  - .claude/adr/ADR-161-codex-harness-capability-matrix.md
  - .claude/hooks/tests/test_adapter_golden.py
  - .claude/hooks/tests/test_adapter_drift_detector.py
  - .claude/hooks/tests/test_adapter_seam_dispatch.py
  - .claude/hooks/tests/test_codex_pair_rail_characterization.py
  - .claude/hooks/tests/test_codex_positive_controls.py
  - .claude/hooks/tests/fixtures/adapters/codex/**
Amends: none (no SPEC/v1 row in this wave; the pair-rail reviewer-egress
  helper surface of codex.py is contract-UNTOUCHED, locked by the A14
  characterization tests passing unchanged on both sides of the commit).
Reconciliation note (S265, MANIFEST-B §7): STRUCK from the original draft
  — `.claude/hooks/_lib/contract.py` (registry constants did not move; A2
  coherence gate landed adapter-side, not contract-side) and
  `.claude/hooks/tests/adapters/live/test_adapters.py` (not staged);
  RENAMED `test_codex_reviewer_egress_characterization.py` →
  `test_codex_pair_rail_characterization.py`; ADDED
  `test_adapter_seam_dispatch.py`. `check_canonical_edit.py` and
  `check_bash_safety.py` are ALSO touched by later ceremonies
  (SENT-CX-E re-extends check_canonical_edit.py; PLAN-154 SENT-F carries
  the check_bash_safety.py fact-gate base this wave's seam sits on) —
  landing order bases each re-touch on the prior. The 44 `fixtures/…/**`
  files are the recorded codex-cli 0.139.0 wire (`_meta.codex_cli_version`
  pinned).
<!-- END SIGNED SCOPE -->
