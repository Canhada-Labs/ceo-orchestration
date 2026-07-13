# SENT-ADV — PLAN-158 Wave 2 check_adversary SECRETS-only scan

Spec-conformance fix (debate upgraded from optional; OQ2 ratified by
Owner S270): the E1 §4 pre-exec Bash gate is docstring-scoped to LIVE
CREDENTIALS but scanned ALL_PATTERNS — checksum-valid numeric PII
collisions (S270 live incident: a benign GitHub run id passes the CPF
checksum; br_rg matches ANY bare 8-9 digit run) fail-CLOSED blocked
benign commands with no env escape. Fix: _command_carries_secret now
scans patterns=SECRETS (28 credential families); fallback to the full
catalog if SECRETS is absent (over-block, never under-block). VETO
guardrails (recorded, security critic): NO PII family deleted from the
shared catalog (egress-redaction keeps consuming them); the
unconditional credential fail-closed path untouched; no RC dist-tag npm
publish. Proven: 8/8 regression tests (neutral-layout clean proof) +
live positive control (the unpatched gate ASK-blocked the session's own
command carrying the colliding literal).

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Anchor-SHA: d6cad0b1874023277f1c2c93e11a9e6f1d23c2d8
Plans: PLAN-158
Kernel-Override: (none — no _KERNEL_PATHS in this scope)
Scope:
  - .claude/hooks/check_adversary.py
<!-- END SIGNED SCOPE -->
