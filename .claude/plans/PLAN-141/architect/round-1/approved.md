# PLAN-141 — Architect Sentinel (round 1)

Authorizes the single behaviour-preserving edit in PLAN-141: making the
mcp-smoke `ruff check` step fail-soft when the vestigial PLAN-070 staging tree
is absent (lint only files that exist). Path matches `.github/workflows/*.yml`
(canonical-guarded, ADR-010); not an arbitration-kernel path, so no
`CEO_KERNEL_OVERRIDE` is required.

Anchor commit 771194bc497796606cbdfae12dc2dad936bccde1 is the repo HEAD this
sentinel was signed against.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs 771194bc497796606cbdfae12dc2dad936bccde1
Plans: PLAN-141
Scope:
  - .github/workflows/mcp-smoke.yml
<!-- END SIGNED SCOPE -->

Authorization: Owner-signed GPG detached signature (approved.md.asc), signer
fingerprint D7227DFE7614477282A64BFE61C1C798ED8EE279, verified against both
signer rails (.claude/sentinel-signers.txt + the ADR-121 YAML registry) — the
rails were already bootstrapped in commit e0335fa (PLAN-140), so this ceremony
needs only the signature.

Rationale: the ruff step lints a pre-promotion copy of code that now lives,
evolved, at .claude/hooks/_lib/mcp/canonical_guard.py + .claude/hooks/tests/.
Making the lint fail-soft removes no real coverage and reintroduces no stale
duplicate. See PLAN-141 §2.
