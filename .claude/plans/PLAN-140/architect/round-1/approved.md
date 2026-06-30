# PLAN-140 — Architect Sentinel (round 1)

Authorizes the two behaviour-preserving edits in PLAN-140: removing the
forbidden `hook_origin` kwarg from the two compaction `emit_generic`
callsites. Both paths match `.claude/hooks/*.py` (canonical-guarded, ADR-010);
neither is an arbitration-kernel path, so no `CEO_KERNEL_OVERRIDE` is required.

Anchor commit a01cbda5e7607bc44b24258bebb2153ad75a8c9a is the repo HEAD this
sentinel was signed against.

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs a01cbda5e7607bc44b24258bebb2153ad75a8c9a
Plans: PLAN-140
Scope:
  - .claude/hooks/check_precompact_continuity.py
  - .claude/hooks/check_postcompact_reinject.py
<!-- END SIGNED SCOPE -->

Authorization: Owner-signed GPG detached signature (approved.md.asc), signer
fingerprint D7227DFE7614477282A64BFE61C1C798ED8EE279, verified against both
signer rails (.claude/sentinel-signers.txt + the ADR-121 YAML registry).

Scope note (re: cross-model review P1): the signer-rail activation that makes
this `.asc` verifiable (registering the Owner hot-key in
.claude/sentinel-signers.txt + .claude/security/sentinel-signers-registry.yaml)
is INTENTIONALLY NOT in this Scope block. Registering the first real signer is
a trust-root bootstrap — it cannot be authorized by the very ceremony it
enables (that would be circular). It is committed separately as an explicit
Owner-authorized bootstrap (manual sed on the kernel-guarded .txt + GPG key
possession = the out-of-band authority). KNOWN DEBT: this is a partial GENESIS
(hot-key only); the ADR-121 cold-key 2-of-3 quorum is deferred — the registry
still carries DEADBEEF… cold-key placeholders. Full GENESIS (cold-key
provisioning + bootstrap_sha256 pin) is a separate ceremony, out of scope for
PLAN-140.

Rationale by path:
  - .claude/hooks/check_precompact_continuity.py — drop hook_origin kwarg at
    the compaction_continuity_snapshot emit_generic call (~line 285).
  - .claude/hooks/check_postcompact_reinject.py — drop hook_origin kwarg at
    the compaction_context_reinjected emit_generic call (~line 208).
