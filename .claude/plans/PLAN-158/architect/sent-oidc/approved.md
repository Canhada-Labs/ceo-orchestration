# SENT-OIDC — PLAN-158 Wave 1 npm Trusted Publishing (OIDC)

Flips npm-publish.yml registry auth from the granular NPM_TOKEN (expires
~2026-09-28) to npm Trusted Publishing: npm CLI >=11.5.1 upgrade step
(Node 20 bundles npm 10.x — without it GA dies ENEEDAUTH) + tokenless
publish step. RC-exclusion, production-npm gate, already_published guard
and --provenance are UNCHANGED (pins asserted). Carries the PLAN-152
§Deferred doc cascade assigned to this flip: SPEC/v1/npm-shim.md
§Publishing (via spec patcher under this sentinel), GOVERNANCE-MAP.md
secret row + workflow row, install-npm.sh auth wording. Rollback diff is
PRE-STAGED and PRE-AUTHORIZED by this sentinel
(staged/wave1/rollback-oidc-to-token.patch — Recovery B of the playbook):
applying EXACTLY that diff to npm-publish.yml needs no fresh sentinel.
Old token REVOKED after first OIDC GA publish (Owner console + rotation
log). OQ1 ratified by Owner S270 ("OIDC nesta release").

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Anchor-SHA: 01b01f3ab06be00a7d978b6bbf5cab00eb2375bd
Plans: PLAN-158
Kernel-Override: (none — no _KERNEL_PATHS in this scope)
Scope:
  - .github/workflows/npm-publish.yml
  - SPEC/v1/npm-shim.md
  - .github/workflows/GOVERNANCE-MAP.md
  - scripts/install-npm.sh
Amends: SPEC/v1/npm-shim.md — §Publishing auth mechanism + version-history
  row 1.1.0 (documentation-of-mechanism; shim contract unchanged). Applied
  via .claude/plans/PLAN-158/staged/spec-patches/apply-spec-npm-shim.py.
<!-- END SIGNED SCOPE -->
