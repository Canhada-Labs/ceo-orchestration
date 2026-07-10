# SENT-CX-B — PLAN-155 Wave 4 audit-actions sentinel (round-1 DRAFT)

Drafted S266 (2026-07-09, Wave 0 prep) by the CEO under the Owner's
delegation; **inert until the Owner fills the anchor and detach-signs**
(`approved.md.asc`, dual rail per ADR-121). Scope below is the EXACT
guarded target set of the Wave 4 staged overlay
`.claude/plans/PLAN-155/staged/wave-4/` (mirror layout = repo-relative
targets). The landing ceremony asserts `touched − SIGNED SCOPE = ∅` (S258
rule) before applying.

**KERNEL-class (pair-rail S265 F3):** `audit_log.py` and
`_lib/audit_emit.py` are in `_KERNEL_PATHS`
(`check_arbitration_kernel.py:200,90`). The apply env MUST carry
`CEO_KERNEL_OVERRIDE=PLAN-155-CODEX-AUDIT-ACTIONS` +
`CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` (audited per ADR-031 §kernel-override)
on top of this sentinel; the SENT-E/S261 Owner-shell apply route satisfies
the same requirement with this signed sentinel as the authorization record.

Landing order (binding): PLAN-154 SENT-F lands BEFORE every SENT-CX
(F-before-CX); within PLAN-155: SENT-CX-A → (Waves 2/3 unguarded) →
SENT-CX-E → **SENT-CX-B** → SENT-CX-C → SENT-CX-D. Anchor
(`__ANCHOR_SHA__`) taken on main after SENT-CX-E lands.

**Baseline-count note (binding):** the `_KNOWN_ACTIONS` count baseline
INHERITS PLAN-154 SENT-F's landing (F-before-CX order). The repo baseline
at drafting time is **303** (pin at
`test_audit_emit_api_contract.py:656-658`); if SENT-F itself registers new
actions, Wave 4's arithmetic starts from SENT-F's post-landing count, and
the rebaseline recorded here reads "+1 per Wave-4 action" (per-tool-call
append action, turn-ended backstop action → nominally 303→304/305 from
today's baseline), never a hardcoded absolute that races SENT-F.

Four-file coupling, ONE commit (S261 PLAN-153 Wave E 302→303 precedent):
(1) `_KNOWN_ACTIONS` registration + closed-enum field allowlist in
`_lib/audit_emit.py` (`:153`; `_write_event` rejects unregistered actions
at `:2475-2477`); (2) the SPEC Amends row below; (3) count+SHA256 pin
rebaseline in the unguarded companion test; (4) the emitter. The unguarded
`hooks/tests/` companion rides the same commit (not sentinel-blocked),
named here so the coupling is not discovered at execution time.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs 71a2ef5f8dc52aabe8ba2c848e65b7c6b895a5c1
Anchor-SHA: __ANCHOR_SHA__
Plans: PLAN-155
Kernel-Override: PLAN-155-CODEX-AUDIT-ACTIONS (+ CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT)
Scope:
  Wave 4 — audit chain under Codex (per-tool-call append action +
  turn-ended backstop action; debate A13 TestEnvContext replay +
  asserted-backstop coupling), landed as the complete staged overlay of
  PLAN-155/staged/wave-4/ (reconciled S265 against the on-disk overlay
  after the integrated-verify pass — MANIFEST-B §7 flagged the original
  4-file draft as SEVERELY under-scoped; this is the 11-file set):
  - .claude/hooks/audit_log.py
  - .claude/hooks/_lib/audit_emit.py
  - SPEC/v1/audit-log.schema.md
  - .claude/data/audit-registry.golden.txt
  - scripts/codex-exec-wrapper.sh
  - .claude/hooks/tests/test_audit_emit_api_contract.py
  - .claude/hooks/tests/test_codex_audit_chain.py
  - .claude/hooks/tests/test_codex_egress_proof_telemetry.py
  - .claude/hooks/tests/test_git_bypass_guard.py
  - .claude/hooks/tests/test_w5_scrub_enforcement.py
  - .claude/hooks/tests/fixtures/adapters/codex/session/codex_session_e2e.json
Amends: SPEC/v1/audit-log.schema.md — adds the Wave-4 action rows: the
  per-tool-call append action (Codex PostToolUse `*` path — audit_log.py
  today returns None for non-Agent tools at :566-567 and hardcodes
  agent_spawn at :642) and the turn-ended backstop action (distinct name
  so completeness analysis can tell per-tool vs turn-level appends apart),
  each with its closed-enum field allowlist, AND the matching
  version-summary-table row; required by the `_KNOWN_ACTIONS`
  registration landing in .claude/hooks/_lib/audit_emit.py under this same
  sentinel. **Baseline note (S265, corrected):** this wave lands AFTER
  PLAN-154 SENT-F (F-before-CX), whose overlay already carries
  `_KNOWN_ACTIONS` at 314; Wave-4 adds 2 codex actions → **314→316** (NOT
  the draft's stale 303→304/305). The four count-pin companions
  (test_audit_emit_api_contract.py, test_codex_egress_proof_telemetry.py,
  test_git_bypass_guard.py, test_w5_scrub_enforcement.py) + the
  audit-registry golden are ALSO in SENT-F scope at 314 — they are
  re-touched here to 316; both ceremonies list them, landing order
  (SENT-F@314 then this@316) keeps each intermediate state self-consistent.
  audit_emit.py additionally carries the `settings_tamper_codex_killswitch_missing`
  tamper-class mirror for wave-3b's new class (additive frozenset entry;
  does NOT change the `_KNOWN_ACTIONS` golden). The HMAC chain shape and
  `verify_chain()` are UNTOUCHED.
<!-- END SIGNED SCOPE -->
