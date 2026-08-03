# PLAN-165 P1-corrected + P2 — Owner sentinel (S291)

Anchor-sha: 36696c5992bd983342f554c43116eba0ad91797a
Ceremony: consolidated posture-write surface + audit action

Scope:
- .claude/data/audit-registry.golden.txt
- .claude/hooks/_lib/audit_emit.py
- .claude/hooks/check_arbitration_kernel.py
- .claude/hooks/check_canonical_edit.py
- .claude/hooks/tests/test_audit_emit_api_contract.py
- .claude/hooks/tests/test_audit_emit_night_mode_toggled.py
- .claude/hooks/tests/test_audit_emit_plan163_lifecycle_actions.py
- .claude/settings.json
- SPEC/v1/audit-log.schema.md
- scripts/install.sh
- templates/settings/settings.base.json

Rationale: closes the escalation ladder the codex review (CX-1)
proved the original p1 left open — per-tool deny entries never see
the Bash rail, so the three posture paths also enter
_CANONICAL_GUARDS (which check_bash_safety keys off) and the two
state files enter _KERNEL_PATHS. Implements the Owner-ratified
OQ1-redo (2026-08-03): night-mode on/off become human actions.
P2 registers night_mode_toggled atomically with the contract tests
it turns red, so no commit ever has an unregistered emit.

Signed-by: Owner
