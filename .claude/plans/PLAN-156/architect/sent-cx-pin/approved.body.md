# SENT-CX-PIN — PLAN-156 Wave 1 codex-cli 5.6 pin bump

Widen-upper-ONLY pin bump so codex-cli 0.144.1 (GPT-5.6 Sol/Terra/Luna
first-class) is in range. Lower bound UNCHANGED (>=0.128.0) — raising it
would drop an in-flight RC verdict out of range in release.yml step-15
(debate C10). Both pin files are _KERNEL_PATHS.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Anchor-SHA: __ANCHOR_SHA__
Plans: PLAN-156
Kernel-Override: PLAN-156-CODEX-PIN-BUMP (+ CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT)
Scope:
  - .claude/governance/codex-cli-pin.txt
  - .claude/governance/codex-cli-binary-sha256.txt
<!-- END SIGNED SCOPE -->
