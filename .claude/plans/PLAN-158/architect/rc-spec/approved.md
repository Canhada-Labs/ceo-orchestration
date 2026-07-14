# SENT-RC-SPEC — PLAN-158 Wave 3 rider: npm-shim stale cross-reference fix

Pair-rail RC round 1 (codex-cli 0.144.1, 2026-07-13 S272) returned
GO-WITH-CONDITIONS with a single P2: `SPEC/v1/npm-shim.md` §Cross-reference
ADR-012 line still claimed the OIDC trusted publisher was "not yet
configured", contradicting the §Publishing section amended by SENT-OIDC
(`d6cad0b`) — the Wave 1 patcher amended §Publishing + version history but
missed the cross-reference parenthetical (stale-claim class, same family as
the GOVERNANCE-MAP workflow_dispatch claim caught in the W1/W2 round 1).

Fix (doc-only, zero contract change): cross-reference now reads "Trusted
Publishing live since spec 1.1.0 — see §Publishing"; the 1.1.0
version-history row gains a post-amendment-sweep note. Codex round 2
re-reviewed the staged diff: APPROVE (net 16/16 APPROVE, OVERALL GO).

Applied at ceremony via
`.claude/plans/PLAN-158/staged/rc/spec-npm-shim-oidc-xref.patch`
(staged full copy: `.claude/plans/PLAN-158/staged/rc/npm-shim.md`;
apply = copy staged over canonical, verify with git diff --stat = 1 file).

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Anchor-SHA: f259eb273112dc70bc5f8c20d6fe06a679dc69ed
Plans: PLAN-158
Kernel-Override: (none — no _KERNEL_PATHS in this scope)
Scope:
  - SPEC/v1/npm-shim.md
Amends: SPEC/v1/npm-shim.md — §Cross-reference ADR-012 parenthetical +
  version-history 1.1.0 row sweep note (doc-only; shim contract unchanged).
<!-- END SIGNED SCOPE -->
