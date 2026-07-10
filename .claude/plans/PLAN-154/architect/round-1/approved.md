# SENT-F — PLAN-154 gated-learning-loop landing sentinel (round-1)

Drafted S265 (2026-07-10, autonomous overnight run) by the CEO under the
Owner's 2026-07-09 delegation; **inert until the Owner fills the anchor
and detach-signs** (`approved.md.asc`). Scope below is the EXACT staged
overlay file set of `.claude/plans/PLAN-154/staged/sent-f/` (mirror
layout = repo-relative targets; see `staged/MANIFEST.md` for per-file
class tags and apply order). The wake-up ceremony asserts
`touched − SIGNED SCOPE = ∅` before applying.

Application path (SENT-E/S258 precedent): the Owner's shell applies the
staged overlay via the S265 wake-up script — for the KERNEL /
SELF-MODIFICATION-class rows (`.claude/hooks/check_bash_safety.py`,
`.claude/hooks/_lib/audit_emit.py`, `SPEC/v1/audit-log.schema.md` under
`deny: Edit(SPEC/**)`) this Owner-shell copy IS the sanctioned patcher
route; the signed sentinel is the authorization record. Any
Claude-mediated edit to those rows instead requires
`CEO_KERNEL_OVERRIDE=PLAN-154-GATED-LEARNING-LOOP` +
`CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` (ADR-031 §kernel-override, audited).
`CLAUDE.md` additionally obeys Gate-1 cache discipline: its count-bump
row lands at the ceremony, which IS the session closeout event.
ADR-160 lands with this wave and flips PROPOSED→ACCEPTED in the landing
series (ADR-158/159 precedent).

**Landing order:** SENT-F lands BEFORE every PLAN-155 SENT-CX ceremony
(F-before-CX) — PLAN-155's Wave-1/Wave-4 overlays are BASED on this
overlay's `check_bash_safety.py` / `audit_emit.py` / SPEC (action
baseline 314 after this landing).

**Wave-0 ratification rider (Owner, at signing):** (1) item-6 numeric
flip criteria as pre-registered in ADR-160 §Decision (FP < 2% over ≥ 50
gate-candidate events + ≥ 14 calendar days + zero unresolved integrity
flags); (2) `CEO_FACT_GATE_SHADOW` ships default-ON (telemetry needed
for the flip criteria); (3) advisory A19 (candidate pruning) waived for
v1 — `prune-lessons.py` does not see `candidates/`; archive-never-delete
posture holds; follow-up recorded in the wave record.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs 71a2ef5f8dc52aabe8ba2c848e65b7c6b895a5c1
Anchor: 9096813e61c19d7aad3f0332b742c4bb04b55d17
Plans: PLAN-154
Scope:
  Gated learning loop (items 1-7 + ADR-160 + 4-file audit coupling
  303→314 + env registration + derived-golden regen + count bumps),
  landed as the complete staged overlay of PLAN-154/staged/sent-f/
  (42 files; reconciled S265 against the on-disk overlay after the
  pair-rail P2#4 fix + the 4-count-pin/3-golden-drift closure — the
  S258 `touched − SIGNED SCOPE = ∅` set):
  - .claude/hooks/check_bash_safety.py
  - .claude/hooks/_lib/audit_emit.py
  - .claude/hooks/_lib/tool_lifecycle.py
  - .claude/hooks/_lib/advisory_dampen.py
  - .claude/scripts/lessons.py
  - .claude/scripts/ceo-boot.py
  - .claude/scripts/distill-lessons.py
  - .claude/scripts/lesson_evolve.py
  - .claude/scripts/env-inventory.json
  - .claude/scripts/test-env-hygiene-allowlist.yaml
  - .claude/data/audit-registry.golden.txt
  - .claude/adr/ADR-160-gated-learning-loop.md
  - .claude/commands/ceo-boot.md
  - .claude/commands/lesson-evolve.md
  - SPEC/v1/audit-log.schema.md
  - .claude/hooks/tests/test_audit_emit_api_contract.py
  - .claude/hooks/tests/test_tool_lifecycle_observe.py
  - .claude/hooks/tests/test_advisory_dampen.py
  - .claude/hooks/tests/test_fact_gate_deny_once.py
  - .claude/hooks/tests/test_codex_egress_proof_telemetry.py
  - .claude/hooks/tests/test_git_bypass_guard.py
  - .claude/hooks/tests/test_w5_scrub_enforcement.py
  - .claude/scripts/tests/test_lessons_candidates.py
  - .claude/scripts/tests/test_lessons_verified_render.py
  - .claude/scripts/tests/test_ceo_boot_lessons.py
  - .claude/scripts/tests/test_distill_lessons.py
  - .claude/scripts/tests/test_lesson_evolve.py
  - .claude/scripts/tests/fixtures/distiller/README.md
  - .claude/scripts/tests/fixtures/distiller/benign_observations.jsonl
  - .claude/scripts/tests/fixtures/distiller/hostile_observations.jsonl
  - .claude/scripts/tests/fixtures/distiller/killswitch_always_on_audit_log.jsonl
  - .claude/scripts/tests/fixtures/distiller/model_output_benign.json
  - .claude/scripts/tests/fixtures/distiller/model_output_empty.json
  - .claude/scripts/tests/fixtures/distiller/model_output_hostile.json
  - .claude/scripts/tests/fixtures/distiller/model_output_malformed.json
  - .claude/scripts/tests/fixtures/distiller/model_output_over_schema.json
  - docs/CHEAT-SHEET.md
  - docs/COMMAND-SKILL-HOOK-MAP.md
  - docs/provider-pricing.md
  - CLAUDE.md
  - INSTALL.md
  - README.md
Amends: SPEC/v1/audit-log.schema.md — v2.48: adds the 11 PLAN-154
  learning-loop action rows (lesson_candidate_written, lesson_approved,
  lesson_quarantined, lesson_expired, lesson_integrity_flag,
  lesson_boot_render_dropped, learning_rail_disabled,
  fact_gate_activation_changed, advisory_dampened,
  distiller_run_completed, lesson_evolve_run — closed-enum
  deny-by-default allowlists, Sec MF-3) AND the matching version-history
  row; required by the _KNOWN_ACTIONS 303→314 registration landing in
  .claude/hooks/_lib/audit_emit.py under this same sentinel
  (contract-test pin: count 314, SHA 689e3094…, in
  test_audit_emit_api_contract.py in-scope above).
<!-- END SIGNED SCOPE -->
