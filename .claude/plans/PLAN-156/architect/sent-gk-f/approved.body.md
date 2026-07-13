# SENT-GK-F — PLAN-156 Wave 6+7 council workflow + ADR-162

Lands the council-audit.js workflow (now guarded by SENT-GK-E) + the
/council command + ADR-162. council-audit.js OWNS live external egress
(ADR-114 redactor + budget hard-kill + no-CI fence) — guarded so a later
edit cannot strip those. ADR-162 is the normative grok capability record.
Docs (unguarded) + the council fixture test ride this commit.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Anchor-SHA: __ANCHOR_SHA__
Plans: PLAN-156
Kernel-Override: (none — no _KERNEL_PATHS in this scope)
Scope:
  - .claude/workflows/council-audit.js
  - .claude/commands/council.md
  - .claude/adr/ADR-162-grok-harness-capability-matrix.md
<!-- END SIGNED SCOPE -->
