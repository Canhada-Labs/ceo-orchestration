# SENT-GK-E — PLAN-156 Wave 3+6 canonical guard extension

check_canonical_edit.py: adds the grok kill-switch surface (.grok/hooks/**,
.grok/config.toml, .grok/sandbox.toml, .grok/rules/*.md) + templates/settings
+ the council egress surface (.claude/workflows/council-audit.js,
.claude/commands/council.md) to _CANONICAL_GUARDS, AND their first-segment
prefixes (.grok, templates) to _CANONICAL_PREFIXES (else the globs are
INERT — the dead-guard class). check_canonical_edit.py is _KERNEL_PATHS.
The templates/grok/** operator surface (unguarded) rides this commit.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Anchor-SHA: __ANCHOR_SHA__
Plans: PLAN-156
Kernel-Override: PLAN-156-GROK-KILLSWITCH-GUARD-EXTENSION (+ CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT)
Scope:
  - .claude/hooks/check_canonical_edit.py
<!-- END SIGNED SCOPE -->
