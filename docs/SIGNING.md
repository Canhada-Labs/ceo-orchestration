# Signing & sentinel-key custody (adopter guide)

> **Audience:** a team installing the ceo-orchestration framework into their
> own repository. This doc surfaces the GPG-sentinel half of the
> *compensating-control* model (`ADR-003-AMEND-1`) so adopters inherit a
> written key-custody policy, not just the code that enforces it.
>
> For the branch-protection / CODEOWNERS half — and the API-key rotation
> log — see **`docs/BRANCH-PROTECTION.md`** and **`docs/rotation-log.md`**.

## 1. Why signing exists here

Canonical-path edits (hooks, ADRs, SPEC, skills, workflows, the installer,
`tier-policy.json`, …) are gated by `check_canonical_edit.py`. The gate is
satisfied by an **Owner-signed sentinel**: a detached GPG signature over an
approval file at `.claude/plans/PLAN-NNN/architect/round-N/approved.md.asc`.
No valid sentinel → the edit is blocked. This is a **review** gate (force a
human signature on every weakening change), not a secrecy mechanism.

## 2. Key types — hot vs cold

The signer model (`.claude/hooks/_lib/sentinel_signers.py`) recognises two
key types:

| Type   | Signs                                              | Custody |
|--------|----------------------------------------------------|---------|
| `hot`  | ordinary canonical-edit sentinels (day-to-day)     | online — the working signing key |
| `cold` | **registry mutations + emergency recovery only**   | offline — air-gapped / hardware-token |

Cold-key actions (adding/removing a signer, rotating the registry) require a
**quorum**: `quorum_verify()` enforces an `M-of-N` threshold of *distinct*
valid `cold`-key signatures (typically **2-of-3**). A single key can never
mutate the signer registry by itself.

## 3. The signer registry

Two allowlist files govern who may sign what:

- **`.claude/sentinel-signers.txt`** — one full **40-hex uppercase** GPG
  fingerprint per non-comment line; the set permitted to sign canonical-edit
  sentinels. **An empty file is FAIL-CLOSED** — no sentinel is accepted, so a
  functional deployment MUST list at least one fingerprint.
- **`.claude/skill-patch-signers.txt`** — same format, scoped to skill-patch
  proposals.

**To add a signer:** append the new fingerprint (uppercase, 40 hex) on its
own line, then have the existing cold-key quorum sign the registry mutation.
Never hand-edit the registry on `main` without the quorum signature — that
is exactly the action the cold-key threshold exists to gate.

## 4. Revocation

Revocations are recorded in **`.claude/gpg-revocations.jsonl`** (JSONL; one
revocation record per line, comment lines begin with `#`). A revoked
fingerprint is rejected even if still present in the signer allowlist —
revocation takes precedence. To revoke: append the revocation record, then
remove the fingerprint from `sentinel-signers.txt` under the cold-key quorum.

## 5. Rotation cadence

- **Hot key:** rotate on suspected exposure or per your org policy (e.g.
  annually). Add the new fingerprint, quorum-sign, then revoke the old.
- **Cold keys:** rotate only via the quorum ceremony; keep ≥ `N` custodians so
  losing one key never drops you below the `M` threshold.
- **ANTHROPIC_API_KEY / other secrets:** logged separately in
  `docs/rotation-log.md` — that is the API-credential trail, distinct from
  the GPG-sentinel keys described here.

## 6. What an adopter MUST vs MAY sign

- **MUST sign** (canonical paths gated by `check_canonical_edit.py`): hooks,
  `_lib/`, ADRs + ADR README, SPEC, skill `SKILL.md`, workflows,
  `scripts/install.sh` / `upgrade.sh`, `CODEOWNERS`, `tier-policy.json`,
  `PROTOCOL.md`, governance files.
- **MAY sign** (informational): docs, plans prose, CHANGELOG — these are not
  canonical-gated, though branch-protection + CODEOWNERS still require a
  reviewed PR.

## 7. Relationship to branch protection

The GPG-sentinel layer and GitHub branch protection are **two halves of one
compensating control** (`ADR-003-AMEND-1`): the sentinel forces a signature
at *commit* time, CODEOWNERS + branch protection force review at *merge*
time. On a free-tier private repo where server-side branch protection is not
available (GitHub-Pro-gated — see `docs/BRANCH-PROTECTION.md`), the GPG
sentinel + the local hooks + the Codex pair-rail are the active enforcement.
Keep both halves: neither alone is sufficient.
