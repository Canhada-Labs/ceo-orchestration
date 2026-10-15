# GitHub Actions — Pinned Versions Freeze Doc

PLAN-006 Phase 6a (Node 24 runner audit). This document is the
authoritative record of every GitHub Actions dependency used by the
framework's CI workflows, with version + SHA + runtime notes. Keep in
sync with workflow files.

## Pinning policy

- Every `uses:` line in `.github/workflows/*.yml` MUST be pinned to a
  SHA, NOT a floating tag (`@main`, `@v4`). SHA pins are a supply-chain
  security invariant (ADR-007 → release gate).
- Dependabot (`.github/dependabot.yml`) opens PRs to bump SHAs. Each
  PR runs through `validate.yml` + `coverage.yml` + `smoke-install.yml`
  before merge.
- The comment `# SHA-pinned: <action>@<tag>` ABOVE each `uses:` line
  records which tag that SHA corresponded to at pinning time.

## Current pins (as of Sprint 7 Dependabot bumps, 2026-04-13)

| Action | Pinned tag | SHA | Runtime | Deprecation watch |
|---|---|---|---|---|
| `actions/checkout` | `v6.0.2` | `de0fac2e4500dabe0009e67214ff5f5447ce83dd` | Node 24 | ✅ migrated |
| `actions/setup-python` | `v6.2.0` | `a309ff8b426b58ec0e2a45f0f869d46889d02405` | Node 24 | ✅ migrated |
| `actions/setup-node` | `v6.4.0` | `48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e` | Node 24 | ✅ migrated — row corrected 2026-10-02 (PLAN-194 W4): this SHA, the only setup-node pin (`npm-publish.yml`), resolves to tag `v6.4.0` (`runs.using: node24`); the `v4.1.0` / `39370e39…` this row used to carry was not the pin in the workflow |
| `actions/upload-artifact` | `v7.0.1` | `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` | Node 24 | ✅ migrated |

### Runtime version configuration (separate from action version)

| Workflow | Tool | Declared version |
|---|---|---|
| `npm-publish.yml` | Node + npm | Node **`24`** + npm **`11.20.0`** (exact) — the workflow-level `env` (`PUBLISH_NODE_MAJOR`, `PUBLISH_NPM_VERSION`), read by `publish` and `rc-toolchain-proof`; set by PLAN-194 W4 (2026-10-02). Until then the file declared Node `"20"` and `npm@^11.5.1` — the Sprint 6 bump below never landed |
| `coverage.yml` | Python | `3.11` |
| `release.yml` | Python | `3.11` |
| `smoke-install.yml` | Python | `3.11` |
| `benchmarks.yml` | Python | `3.12` |

## Sprint 6 Phase 6a scope

Per PLAN-006 debate R-DEV3, Sprint 6 Phase 6a is a **standalone phase**,
not closeout. Scope:

- ✅ Document current pins in this file
- ❌ Bump `npm-publish.yml` `node-version: 20 → 24` (runtime update) —
  NOT done in Sprint 6 (the file kept `node-version: "20"`); done by
  PLAN-194 W4 on 2026-10-02 (correction recorded then)
- ✅ Flag 2026-06-02 Node 20 deprecation deadline per action
- ✅ **Sprint 7 executed** (PLAN-007 Phase A): Dependabot opened PRs,
  mergeadas individualmente após CI verde:
  - ✅ PR #2: `actions/checkout@v4 → v6` (SHA `de0fac2e…`)
  - ✅ PR #3: `actions/setup-python@v5.4 → v6.2` (SHA `a309ff8b…`)
  - ✅ PR #1: `actions/upload-artifact@v4.6 → v7.0` (SHA `043fb46d…`)
- ~~**Pending Dependabot**: `actions/setup-node@v4 → v5`~~ — moot
  (2026-10-02): the setup-node pin is `v6.4.0` (see the table above)

### Migration log (Sprint 7, 2026-04-13)

Todas as 3 PRs passaram nos 4 status checks (Governance, Coverage
enforcing 86%, Smoke Install, Benchmarks). Nenhum schema break
detectado. Merge sequencial via `gh pr merge --squash`. Total 3
commits on main.

## Upgrade procedure (Sprint 7)

For each action requiring bump:

1. Wait for Dependabot PR (enabled in `.github/dependabot.yml`) OR
   manually create a PR with just that one action's SHA change.
2. Update the SHA + the `# SHA-pinned: <tag>` comment.
3. Let CI run — validate.yml + coverage.yml + smoke-install.yml all
   green.
4. If CI red: investigate (usually input-schema break); find compat
   path or hold bump until action releases a backward-compat version.
5. Merge — then update this doc with the new SHA.
6. Update `docs/BRANCH-PROTECTION.md` §Node deprecation if applicable.

## Deprecation tracking

Reference: [GitHub Actions runtime deprecation policy][github-rt-dep]

Current active deprecation: **Node 20 runtime** — deadline 2026-05-15.
After that date, actions built on Node 20 will fail with warnings,
eventually errors. All four actions listed in the pin table above run
on Node 24 (`runs.using` read from each pinned SHA's `action.yml`,
2026-10-02); the table does not list every action the workflows use.

[github-rt-dep]: https://github.blog/changelog/

## References

- ADR-007 — SPEC v1 + SemVer + RC policy (release gate)
- `.github/dependabot.yml` — PR automation for action bumps
- `docs/BRANCH-PROTECTION.md` — branch protection + Node 24 deadline
- PLAN-006 §Phase 6a
- PLAN-006/debate/round-1/devops-engineer.md §R-DEV3
