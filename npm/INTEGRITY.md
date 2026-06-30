# NPM shim integrity manifest

> **Integrity contract for the `ceo-orchestration` npm shim.** The package is
> built and versioned (`VERSION` / `package.json`, currently 1.0.0).
> Publishing stays gated — `npm-publish.yml` holds all `v*-rc.*` tags and
> requires manual approval on GA tags via `environment: production-npm`.
> The integrity controls enforced **today** are: (1) an `install.sh`
> self-SHA tamper trailer (`# CEO-INSTALL-SHA256:`) that re-hashes the
> installer at install time and **fails closed** on mismatch; (2) build
> provenance via `npm publish --provenance` (`publishConfig.provenance:
> true`, a Sigstore / SLSA-Level-2 attestation); and (3) a per-tarball
> SHA-256 manifest (`npm/SHA256SUMS.txt` plus a detached `<tarball>.sha256`)
> recorded by `npm-publish.yml` at tag cut. The sections below detail each
> control and the items that remain release-operator steps (GPG detached
> signature, reproducible build) rather than automated gates.

## Contract

Every release tarball (`npm pack --dry-run` output) MUST satisfy:

| Control | Value / mechanism | Where enforced |
|---|---|---|
| SHA-256 manifest per file | `sha256sum` over every file in `files:` array | `.github/workflows/validate.yml` (to-add) + manifest committed to `npm/SHA256SUMS.txt` during release prep |
| GPG detached signature | RFC 4880 signature over tarball | Release operator signs locally with project key; signature attached to GitHub Release as `ceo-orchestration-<version>.tgz.asc` |
| SLSA Level-2 provenance | `npm publish --provenance` (Sigstore-attested via OIDC) | `.github/workflows/npm-publish.yml` already passes `--provenance`; requires `id-token: write` permission (already set) |
| Reproducible build | `SOURCE_DATE_EPOCH` set to VERSION tag commit date | Release script (Sprint 17 scope) sets env var before `npm pack` |
| Zero runtime dependencies | `Object.keys(dependencies).length === 0` | `.github/workflows/npm-publish.yml` step "Verify zero runtime dependencies" (existing) |
| VERSION parity | `VERSION` file == `npm/package.json.version` == tag `v<version>` | `.github/workflows/npm-publish.yml` step "Verify VERSION matches tag" (existing) |

## File-layer SHA-256 manifest (example)

Generated during release prep, committed to `npm/SHA256SUMS.txt` adjacent to
`package.json`:

```
<sha256>  bin/ceo-orch-init.js
<sha256>  package.json
<sha256>  scripts/install.sh
<sha256>  templates/CLAUDE.md
...
```

Consumers verify with:

```bash
cd $(npm root -g)/ceo-orchestration
sha256sum -c SHA256SUMS.txt
```

## GPG key

Project signing key fingerprint published in `docs/rotation-log.md` §NPM.
Rotation: same 90-day maximum as other project credentials (ADR-040 §4).
Public key distributed via GitHub Release notes + `.well-known/gpg.asc`.

## SLSA Level-2 provenance

`npm publish --provenance` attaches a Sigstore-signed attestation declaring:
- Source repository (git URL)
- Commit SHA
- Workflow file that built the tarball
- Builder (GitHub Actions runner identity)

Consumers inspect via:

```bash
npm audit signatures ceo-orchestration
```

## Reproducible-build spec

Inputs:
- `SOURCE_DATE_EPOCH = <VERSION tag creator-date, unix-epoch>`
- Node 20.x (SHA-pinned in `npm-publish.yml`)
- No `npm install` for the bundle itself (zero runtime deps)

Expected output: byte-identical tarball across any ubuntu-latest GitHub
Actions runner with the same inputs. Deviation = rebuild failure.

## CI verification (npm pack --dry-run assertion)

A new step in `validate.yml` asserts:

```yaml
- name: Assert npm pack produces expected bundle
  run: |
    cd npm
    SOURCE_DATE_EPOCH=$(git log -1 --format=%ct) npm pack --dry-run > /tmp/pack-out.txt
    grep -q "^filename:" /tmp/pack-out.txt || { echo "::error::npm pack did not report filename"; exit 1; }
```

The `--dry-run` variant does not publish; it only asserts the pack step would
succeed. Full tarball signing + provenance is the release-operator workflow.

## Not yet automated (release-operator or out of scope)

- **GPG detached signature** is a manual release-operator step (sign the
  tarball locally; attach the `.asc` to the GitHub Release), not a CI gate.
- **Reproducible build** (`SOURCE_DATE_EPOCH`-pinned `npm pack`) is specified
  above but not yet asserted byte-for-byte in CI.
- **SLSA Level-3** (hermetic build + two-party review) is out of scope; the
  shipped provenance is SLSA Level-2 (`--provenance`).

## References

- PLAN-013 Phase E.7 (this ADR source)
- PLAN-013 Phase 0 item 0.2 — `npm-publish.yml` RC + manual-approval gates
- ADR-040 §4 — credential lifecycle (90-day rotation applies to GPG key)
- `.github/workflows/npm-publish.yml` — existing publish pipeline (gated)
- `.github/workflows/validate.yml` — `npm pack --dry-run` assertion site
- Sigstore + SLSA: <https://slsa.dev/spec/v1.0/levels>
- npm provenance: <https://docs.npmjs.com/generating-provenance-statements>
