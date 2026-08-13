# NPM shim integrity manifest

> **Integrity contract for the `ceo-orchestration` npm shim.** This file
> states **no** version of its own: `VERSION` at the repo root is the single
> authority, mirrored into `npm/package.json` by the release bump driver
> (`.claude/scripts/local/_release_bump_sites.py`) — a second copy here would
> be a literal no oracle watches, which is exactly how it went stale before.
> Publishing stays gated — `npm-publish.yml` holds all `v*-rc.*` tags and
> requires manual approval on GA tags via `environment: production-npm`.
> **Which controls run, and where, is stated in exactly one place: the
> Contract table below.** This prose deliberately makes no mechanism claim of
> its own — a claim written here would be answerable to nothing, which is how
> this file came to advertise a tarball checksum that no workflow ever
> produced. The table's `Status` column and its machine-checked
> `Where enforced` cells are the answer; §Not yet automated names the gaps.
> In summary, and stated as absences: there is **no** per-tarball SHA-256
> manifest anywhere in the publish pipeline (no workflow materialises the
> `.tgz` — the packlist gate runs `npm pack --dry-run`, which writes nothing
> — so nothing hashes it), and neither the GPG detached signature nor the
> reproducible build is automated.

## Contract

The rows below are the contract for every release tarball.

`Status` is a **closed set** — `enforced`, `deferred`, `operator`. Anything
else is a test failure, so a row cannot acquire a comfortable new adjective.
`Where enforced` is **machine-checked** for `enforced` rows
(`test_integrity_contract_rows_name_a_live_step` in
`.claude/scripts/tests/test_release_bump_sites.py`): the cell must name a
workflow in backticks that exists, followed by `step "<name>"` matching a
`- name:` in that YAML by **exact equality** — never substring. A row that
claims enforcement without a live step is the failure mode this table
shipped with, and it now goes red.

| Control | Value / mechanism | Status | Where enforced |
|---|---|---|---|
| Zero runtime dependencies | `Object.keys(dependencies).length === 0` | enforced | `.github/workflows/npm-publish.yml` step "Verify zero runtime dependencies" |
| VERSION parity | `VERSION` == `npm/package.json.version` == tag `v<version>` | enforced | `.github/workflows/npm-publish.yml` step "Verify VERSION matches tag" + `.github/workflows/npm-publish.yml` step "Verify npm/package.json version matches VERSION" |
| Packlist hygiene | no tests, fixtures, eval corpora or plan material inside the tarball | enforced | `.github/workflows/npm-publish.yml` step "Packlist gate (PLAN-152 tarball-02)" + `.github/workflows/validate.yml` step "npm packlist gate (no tests/fixtures/eval/red-team-corpus/PLAN-N)" |
| `install.sh` self-SHA trailer | `# CEO-INSTALL-SHA256:` stamped over the staged installer; the installer re-hashes its own body at install time and fails closed on mismatch | enforced | `.github/workflows/npm-publish.yml` step "Populate install.sh self-SHA trailer (P0-15, PLAN-045)" |
| Tag/SHA binding at publish | the remote tag must still point at the SHA this run built | enforced | `.github/workflows/npm-publish.yml` step "Assert remote tag still points at this run's SHA" |
| SLSA Level-2 provenance | `npm publish --provenance` (Sigstore-attested via OIDC) | enforced | `.github/workflows/npm-publish.yml` step "Publish (Trusted Publishing — OIDC)" |
| SHA-256 tarball manifest | `sha256sum` over the published `.tgz`, plus a detached `<tarball>.sha256` | deferred | nothing — see §Not yet automated |
| Reproducible build | `SOURCE_DATE_EPOCH` pinned to the VERSION tag commit date | deferred | nothing — see §Not yet automated |
| GPG detached signature | RFC 4880 signature over tarball | operator | a human, by hand, if at all — see §Not yet automated |

## SHA-256 tarball manifest — what actually exists

`npm/SHA256SUMS.txt` is in the tree, and it is easy to read it as a shipped
guarantee. It is not one:

- It is written by **`scripts/install-npm.sh`**, a local build helper a
  maintainer runs on a workstation. No workflow invokes it, and no workflow
  appends to the file on tag push.
- It therefore records whatever tarball was last built locally, which lags
  the published package.
- It does **not** travel inside the package: `SHA256SUMS.txt` is absent from
  the `files:` array in `npm/package.json`, so it is not in the tarball a
  consumer installs.

Earlier revisions of this document published a consumer recipe that ran
`sha256sum -c` over that manifest from inside the installed package. The
recipe has been **removed, not annotated**: it could never run, for any
version, because the file it reads is not in the package. A caveated
impossible recipe is still an impossible recipe, and it is not reproduced
here — a reader who finds a command in a doc will run it.

What a consumer can actually verify is the provenance attestation — see
§SLSA Level-2 provenance below. For the bash install path, the
`install.sh.sha256` release asset is the checksum that exists; `SECURITY.md`
§How to verify what you install states its scope and its limits.

## Signing keys

The Owner's public key is committed in-repo at `.claude/trust/owner.asc`.
What it signs today is **release tags**. That gate lives outside this
contract and is documented — with its exact scope — in `SECURITY.md`
§How to verify what you install, which is its authority; this file does not
restate it. Verify locally with
`gpg --import .claude/trust/owner.asc && git tag --verify vX.Y.Z`.

There is **no** separate npm signing key. Two distribution points were
claimed here and neither exists: a fingerprint in `docs/rotation-log.md`
(that log covers API-key rotation — its NPM entry records the retirement of
`NPM_TOKEN` in favour of OIDC, and it publishes no key material), and a
public key served under a `.well-known/` path (this project serves no such
path at all). The detached-signature row above is `operator` for that reason:
nothing signs a tarball today.

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

**Status: specification only — no workflow implements any part of it.**
Inputs:
- `SOURCE_DATE_EPOCH = <VERSION tag creator-date, unix-epoch>`
- Node 20.x (`npm-publish.yml` step "Setup Node 20")
- No `npm install` for the bundle itself (zero runtime deps)

Intended output: byte-identical tarball across any ubuntu-latest GitHub
Actions runner with the same inputs. No workflow performs the rebuild or the
comparison, and no workflow sets `SOURCE_DATE_EPOCH` at all, so a deviation
would go unnoticed.

## CI verification (what the packlist gate does, and does not, prove)

Both `npm-publish.yml` and `validate.yml` run a packlist gate over
`npm pack --dry-run --json`, and its subject is the **file list** the tarball
would contain (no tests, fixtures, eval corpora or plan material). `--dry-run`
writes no archive, so the gate proves nothing about tarball **bytes** — no
checksum, no signature, no reproducibility. Tarball hashing and signing are
the un-automated controls above; provenance is the one byte-level attestation
that ships.

## Not yet automated (release-operator or out of scope)

- **SHA-256 tarball manifest** — no workflow materialises the `.tgz`, so
  none can hash it; `npm/SHA256SUMS.txt` is a local-build artefact and is not
  shipped inside the package.
- **GPG detached signature** would be a manual release-operator step (sign
  the tarball locally; attach the `.asc` to the GitHub Release). It is not a
  CI gate, there is no published npm signing key, and no release has shipped
  one.
- **Reproducible build** (`SOURCE_DATE_EPOCH`-pinned `npm pack`) is specified
  above but not yet asserted byte-for-byte in CI.
- **SLSA Level-3** (hermetic build + two-party review) is out of scope; the
  shipped provenance is SLSA Level-2 (`--provenance`).

## References

- PLAN-013 Phase E.7 (this ADR source)
- PLAN-013 Phase 0 item 0.2 — `npm-publish.yml` RC + manual-approval gates
- PLAN-177 W0 item 3 — the stale enforcement claim corrected to the
  mechanism, and the whole-file sweep that followed it
- ADR-040 §4 — credential lifecycle (90-day rotation applies to project keys)
- `.github/workflows/npm-publish.yml` — publish pipeline (gated)
- `.github/workflows/validate.yml` — packlist gate on `npm pack --dry-run`
- `scripts/install-npm.sh` — local tarball build + `SHA256SUMS.txt` writer
- `.claude/trust/owner.asc` — the Owner public key used for release-tag
  verification (scope documented in `SECURITY.md`, not here)
- `SECURITY.md` §How to verify what you install — the honest-limits statement
  this file now mirrors
- Sigstore + SLSA: <https://slsa.dev/spec/v1.0/levels>
- npm provenance: <https://docs.npmjs.com/generating-provenance-statements>
