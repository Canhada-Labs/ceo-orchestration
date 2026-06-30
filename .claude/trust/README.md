# `.claude/trust/` — Owner GPG public key trust anchor

PLAN-044 audit-v2 C2-P0-02 staging directory for the Owner GPG public
key referenced by:

- `.github/workflows/release.yml` step **"Verify tag GPG signature"**
  (`gpg --import .claude/trust/owner.asc` + `git tag --verify`)
- Future SBOM cosign / sigstore envelope steps (audit-v2 P1)

## What ships here

- **`owner.asc`** — armored public key of the project Owner. Committed
  to the repo so the release.yml workflow can verify Owner-signed tags
  WITHOUT pulling from a keyserver at release time (offline-verifiable
  supply-chain attestation per PLAN-045 F-14).

## How to populate

The Owner runs ONCE per Owner-key rotation, locally (substitute the
project's repo root path and the Owner's actual GPG fingerprint —
look up via `gpg --list-keys --with-colons` if unknown):

```bash
cd "$(git rev-parse --show-toplevel)"
gpg --armor --export "<OWNER-GPG-FINGERPRINT>" \
  > .claude/trust/owner.asc

# Sanity check the export looks like an ASCII-armored public key block:
head -1 .claude/trust/owner.asc   # → -----BEGIN PGP PUBLIC KEY BLOCK-----
gpg --show-keys .claude/trust/owner.asc
```

After commit, the file becomes visible to every CI run; `release.yml`
step **"Verify tag GPG signature"** will auto-import + verify on the
next tag push.

## Rotation

If the Owner ever rotates the GPG key (new fingerprint), the new key
must:

1. Be exported here with `gpg --armor --export <NEW-FPR> > owner.asc`
2. Be added to `.claude/sentinel-signers.txt` (allowlist for Owner
   sentinel `.asc` signatures, per PLAN-045 Wave 1 P0-01 dual-tier
   verification).
3. Have its fingerprint referenced in any `OWNER-*-CEREMONY.sh`
   scripts that hardcode `--local-user <FPR>`.

Do **not** delete prior owner.asc rotations — append a comment trail
to `docs/rotation-log.md` for forensic continuity.

## Why this is committed (not gitignored)

Public keys are designed to be public. The supply-chain assertion is
that **only the holder of the matching PRIVATE key can sign a tag
that this PUBLIC key verifies**. A reviewer downloading the repo at
any tag can verify Owner authenticity locally:

```bash
git clone <repo> && cd <repo>
git checkout v1.11.0
gpg --import .claude/trust/owner.asc
git tag --verify v1.11.0   # → Good signature from "..."
```

This is the core of audit-v2 §"What honestly works well" — supply-
chain trust grounded in offline-verifiable signatures, not a TLS
session to GitHub.

## Cross-reference

- `release.yml:408` — verification step that depends on this file
- `.claude/sentinel-signers.txt` — the matching fingerprint allowlist
  for Owner sentinel `.asc` signatures
- ADR-031 — sentinel-signing-as-canonical-edit-grant
- PLAN-045 F-14 — supply-chain attestation roadmap
- PLAN-044 audit-v2 C2-P0-02 — finding that flagged the SBOM gate as
  staged-and-never-activated

## What does NOT live here

- The **private** key. Never commit private GPG material to a repo.
  Owner private key lives in `~/.gnupg/` + 1Password backup per
  memory `project_gpg_setup.md`.
- Other contributors' public keys. The single Owner-pubkey mode is
  intentional under bus-factor-1 (audit-v2 C7-DB-01); when a co-
  maintainer is recruited, the rotation path above adds a second
  `.asc` and updates `release.yml` to verify against ANY of an
  allowlist.
