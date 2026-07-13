# SENT-GK-A — PLAN-156 Wave 0b+2 grok host adapter + kernel + shim

Creates the grok host adapter and enrolls it + the grok pins in the
arbitration kernel, adds the decision→exit-2 + block→deny chokepoint to
the shared shim (grok-gated per lacuna (h): exit-2 is an ACTIVE deny on
codex, so Claude/Codex stay byte-identical), reroutes check_codex_filewrite
through the shim in both settings surfaces, and amends the SPEC hook-io
exit ABI (grok-scoped, via Bash under this sentinel). KNOWN_ADAPTERS +=
grok. Kernel-class: adapter seam + shim + settings + kernel guard.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Anchor-SHA: daf9a5c36915c9bb938afa7cd5c095ac2d315b6e
Plans: PLAN-156
Kernel-Override: PLAN-156-GROK-HOST-ADAPTER (+ CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT)
Scope:
  - .claude/governance/grok-cli-pin.txt
  - .claude/governance/grok-cli-binary-sha256.txt
  - .claude/hooks/_lib/adapters/grok.py
  - .claude/hooks/_lib/adapters/__init__.py
  - .claude/hooks/_lib/contract.py
  - .claude/hooks/check_arbitration_kernel.py
  - .claude/hooks/_python-hook.sh
  - .claude/settings.json
  - templates/settings/settings.base.json
  - SPEC/v1/hook-io.schema.md
Amends: SPEC/v1/hook-io.schema.md — grok-scoped exit ABI addendum (block→deny
  rewrite + emitted-deny→exit-2 under CEO_HOOK_ADAPTER=grok; Claude/Codex
  unchanged). Applied via .claude/plans/PLAN-156/staged/spec-patches/apply-spec-hook-io.py.
<!-- END SIGNED SCOPE -->
