# SPEC v1 — npm-shim

> **Spec version:** 1.0.1-rc.1 (amended PLAN-152 §Deferred `spec-npm-shim-oidc-wording` — §Publishing corrected to the shipped auth mechanism; no behavioral change)
> **Status:** normative
> **Canonical source:** `npm/bin/ceo-orch-init.js`

The npm package `ceo-orchestration` is a **pass-through shim** around
`scripts/install.sh`. This file locks the contract so adopters can
rely on uniform behavior between `bash install.sh` and `npx ceo-orchestration`.

## Pass-through invariants (locked in v1)

1. **Argument forwarding.** Every `process.argv[2..]` argument is
   forwarded unchanged, in order, to the spawned `bash install.sh`
   process. The shim does **not** add, remove, reorder, or rewrite
   arguments.
2. **Exit code passthrough.** The shim exits with the exact exit code
   of the spawned bash process. If the process is killed by signal,
   the shim exits 1.
3. **Stdio inheritance.** stdin, stdout, and stderr are inherited.
   The user sees install.sh's progress live, not buffered.
4. **`__dirname`-relative install location.** The shim resolves
   `install.sh` as `path.join(__dirname, '..', 'scripts', 'install.sh')`.
   It **never** consults `PATH`, environment variables, or working
   directory for installer location.
5. **Zero runtime dependencies.** `package.json`'s `dependencies`
   field is empty (length === 0). CI asserts this on every PR via
   `.github/workflows/smoke-install.yml`.

## Bundle contents (locked in v1)

The published tarball contains exactly:

- `bin/ceo-orch-init.js` (the shim itself)
- `scripts/` (entire framework script directory, incl. `install.sh`)
- `templates/` (template tree shipped to adopters)
- `.claude/` (skills, hooks, plans schema, commands)
- `SPEC/` (this directory)
- `VERSION`, `LICENSE`, `README.md`, `PROTOCOL.md`

`.npmignore` excludes:
- `node_modules/`, `.git/`, `.github/`, `*.log`, `.DS_Store`
- All `tests/` directories (adopters don't need them)
- `docs/`, `NOTES.md`

## Versioning

The shim's version follows the framework's `VERSION` file 1:1. They
are bumped together. There is no separate semver track for the npm
package; if `VERSION=1.2.3`, the npm package is `1.2.3`.

## Publishing

`ceo-orchestration` is published from CI on tag push (`v*`) via
`.github/workflows/npm-publish.yml`. Manual `npm publish` is not
used; tags are the only entry point. RC tags (`-rc.*`) are excluded
at the job level; only GA tags publish.

Registry authentication is a repo-scoped npm **granular token**
(`secrets.NPM_TOKEN`), gated behind the `production-npm` GitHub
environment (manual approval before any publish step). The per-run
GitHub OIDC JWT (`id-token: write`) is consumed ONLY by the Sigstore
`--provenance` attestation — it is **not** registry authentication.
npm **Trusted Publishing** (OIDC registry auth, replacing the
long-lived token) is NOT configured; it is a tracked v1.0.2
follow-up with an Owner web-console prerequisite (PLAN-152 §Deferred
`backlog-oidc`; NPM_TOKEN expires ~2026-09-28 and must be
regenerated before any later release until Trusted Publishing lands).

The publish workflow:
1. Verifies `npm/package.json` `version` matches `VERSION`.
2. Verifies the bundle includes `scripts/install.sh`.
3. Asserts `dependencies` is empty.
4. Publishes with `--provenance` (npm provenance via Sigstore).

## Exit codes

| Code | Meaning |
|---|---|
| 0..N | Whatever `install.sh` returned (passthrough) |
| 1 | Spawn killed by signal (no exit code captured) |
| 2 | `install.sh` missing from bundle (packaging bug, not user error) |

## Deprecation

No flags or behaviors deprecated in v1.0.0-rc.1.

Future deprecation requires:
- `deprecated_in: "1.X.0"` in this file
- `removed_in: "2.0.0"` in this file
- stdout warning when the deprecated behavior is observed
- 90-day window before removal

## Cross-reference

- `SPEC/v1/install-cli.md` — the install.sh flag contract this shim
  forwards to.
- `.github/workflows/smoke-install.yml` — pre-merge gate that runs
  `bash install.sh` AND (when the npm/ subtree changes) checks the
  npm shim's contract.
- ADR-012 — cross-adapter golden fixtures + OIDC trusted-publisher
  rationale (target end-state; not yet configured — see §Publishing).

## Version history

| SPEC version | Changes |
|---|---|
| 1.0.0-rc.1 | Initial formal contract; pass-through shim with zero deps |
| 1.0.1-rc.1 | §Publishing corrected: publish auth is a repo-scoped npm granular token + Sigstore `--provenance` attestation; the "OIDC trusted publisher" claim removed (never configured — same false-claim class as the npm-publish.yml header fixed by PLAN-152 tarball-01). Trusted Publishing tracked for v1.0.2 (PLAN-152 §Deferred `backlog-oidc`). Documentation correction only; no contract or behavioral change. |
