# `.claude/security/` — sentinel signers registry

> **PLAN-089 Wave C.3 — NEW canonical source for sentinel signer trust.**
> See [`ADR-121`](../plans/PLAN-089/wave-c1-adr-121-draft.md) for full policy.

## Purpose

`sentinel-signers-registry.yaml` is the canonical signer trust file
for canonical-edit + registry-mutation sentinels. It supersedes the
flat-text `.claude/sentinel-signers.txt` as the source of truth (the
text file is retained as a GENERATED artifact for backwards
compatibility during the transition — ADR-121 §5).

The registry is parsed by `.claude/hooks/_lib/sentinel_signers.py`
via a stdlib-only YAML-subset parser (`_parse_minimal_yaml`).
No PyYAML, no external dependencies. ADR-002 stdlib-only invariant
preserved.

## Schema fields

Top-level scalars:

| field | type | purpose |
|---|---|---|
| `version` | string | semver for the registry schema itself |
| `created` | ISO-8601 datetime | when the registry file was first written |
| `plan` | string | originating plan id (PLAN-089) |
| `adr` | string | governing ADR id (ADR-121) |
| `bootstrap_sha256` | string | 64-hex SHA256 of GENESIS YAML; baked into `check_canonical_edit.py` as `_BOOTSTRAP_REGISTRY_SHA256`. Filled at Wave C.6 ceremony. |

`signers:` list of mappings:

| field | type | required | purpose |
|---|---|---|---|
| `key_id` | 40-hex uppercase | yes | GPG primary-key fingerprint |
| `key_type` | `"hot"` or `"cold"` | yes | hot signs daily canonical-edit sentinels; cold signs registry mutations only |
| `created_at` | ISO-8601 UTC | yes | when the key was registered |
| `expires_at` | ISO-8601 UTC | yes | policy expiry (12mo hot / 60mo cold max per ADR-121 §2) |
| `revoked_at` | ISO-8601 UTC or `null` | no (defaults `null`) | revocation channel (precedence over expiry) |
| `notes` | string | no | free-form audit note |

Validity (per `is_valid_signer`): `revoked_at IS NULL AND expires_at > now()`.

## Verifying the YAML parses

```bash
python3 -c "import sys; sys.path.insert(0,'.claude/hooks'); from _lib.sentinel_signers import load_registry; from pathlib import Path; print(load_registry(Path('.claude/security/sentinel-signers-registry.yaml')))"
```

Expected: `dict` with 4 entries keyed by 40-hex fingerprint, each
mapped to a `SignerRecord`. Non-zero exit indicates a parser-side
schema violation (malformed datetime, invalid `key_id`, missing
required field, duplicate signer).

Strict assertion form (used in Wave C.3 validation):

```bash
python3 -c "import sys; sys.path.insert(0,'.claude/hooks'); from _lib.sentinel_signers import load_registry; from pathlib import Path; r=load_registry(Path('.claude/security/sentinel-signers-registry.yaml')); assert len(r) == 4, f'expected 4 got {len(r)}'; print('OK', len(r))"
```

## Wave C.6 placeholder detector

The cold-key entries in the GENESIS registry use a sentinel
placeholder fingerprint pattern: 16-hex prefix `DEADBEEFDEADBEEF`
followed by zero-padding and an 8-hex cold-key-index suffix
(`00000001` / `00000002` / `00000003`). The Wave C.6 ceremony script
**MUST refuse to commit** while any `signers[*].key_id` matches the
regex `^DEADBEEFDEADBEEF` (case-insensitive). Detector pseudocode:

```python
import re, yaml  # at ceremony time we may use PyYAML out-of-band
text = open('.claude/security/sentinel-signers-registry.yaml').read()
if re.search(r'(?im)^\s*key_id:\s*["\']?DEADBEEFDEADBEEF', text):
    sys.exit('PLACEHOLDER detected — refuse to commit; replace cold-key fingerprints first')
```

The same detector also guards `bootstrap_sha256`: while the literal
string `PLACEHOLDER-RECOMPUTED-AT-WAVE-C6-CEREMONY` is present, the
ceremony script refuses to commit.

## Wave C.6 GENESIS ceremony (joint hot + cold-key #1 signature)

ADR-121 §5 requires the first commit that creates the canonical
registry to carry **two** detached `.asc` files: one from the
existing hot-key, one from cold-key #1. Both must verify the same
YAML bytes. Single-key first-write is REJECTED by `check_canonical_edit.py`
with `reason_code=genesis_requires_joint_signature`.

Step-by-step (Owner-physical):

1. **Generate cold-key #1 offline.** On the air-gapped workstation:
   ```bash
   gpg --full-generate-key   # 4096-bit RSA, no passphrase prompt suppression
   gpg --list-keys --with-colons "<uid>" | awk -F: '/^fpr/{print $10; exit}'
   ```
   Record the 40-hex fingerprint on paper. Repeat for cold-key #2 + #3
   at the appropriate Site B / Site C physical locations.

2. **Edit `sentinel-signers-registry.yaml`.** Replace the three
   `DEADBEEFDEADBEEF…` placeholders with the real fingerprints.
   Recompute `bootstrap_sha256`:
   ```bash
   sha256sum .claude/security/sentinel-signers-registry.yaml
   # paste the digest into bootstrap_sha256, save, re-sha256, repeat
   # until digest stabilises (digest covers the YAML INCLUDING the
   # digest line — fixed-point iteration; usually 2 rounds).
   ```
   ALTERNATIVE: the ceremony script computes the digest with the
   `bootstrap_sha256` field replaced by a canonical sentinel value
   (e.g. all-zeros) and writes the result back — single-pass, no
   fixed-point. See `.claude/scripts/local/historical/` for the
   exact ceremony script if it has been authored.

3. **Hot-key signs the YAML.**
   ```bash
   gpg --detach-sign --armor \
       --default-key 0000000000000000000000000000000000000000 \
       .claude/security/sentinel-signers-registry.yaml
   mv .claude/security/sentinel-signers-registry.yaml.asc \
      .claude/security/sentinel-signers-registry.yaml.hot.asc
   ```

4. **Cold-key #1 signs the YAML (separate detached signature).**
   Import cold-key #1 secret material from the offline media
   (paper-keys via `paperkey --pubring … --secrets …` or HSM):
   ```bash
   gpg --import-secret-keys cold-key-1-secret.gpg
   gpg --detach-sign --armor \
       --default-key <cold-key-1-fpr> \
       .claude/security/sentinel-signers-registry.yaml
   mv .claude/security/sentinel-signers-registry.yaml.asc \
      .claude/security/sentinel-signers-registry.yaml.cold1.asc
   # IMMEDIATELY: gpg --delete-secret-keys <cold-key-1-fpr>
   ```
   Both `.asc` files must verify the byte-identical YAML; the
   hook checks both.

5. **Commit + tag.** Single GPG-signed commit (`git commit -S`)
   containing the YAML + both `.asc` files. The bootstrap SHA256
   constant in `check_canonical_edit.py` is updated in the SAME
   commit (kernel ceremony unlock under
   `CEO_SENTINEL_UNLOCK=PLAN-089-wave-c6-genesis`).

## Rotation ceremony (post-GENESIS)

Subsequent edits (annual hot-key rotation, cold-key replacement,
revocation) require **cold-key 2-of-3 quorum sentinel**. Three
detached `.asc` files at the commit; at least two must verify
against distinct VALID cold-key signers per `quorum_verify`.

Example: rotate the hot-key (expiry approaching):

1. Edit the YAML — bump hot-key `expires_at`, append a new hot-key
   entry, or set `revoked_at` on the outgoing hot-key.
2. Travel to Site A + Site B (or any 2 of 3 sites). Import each
   cold-key, sign, immediately delete secret material.
3. Three detached `.asc` files in the commit (two real + one
   absent/placeholder is acceptable per quorum semantics). The hook
   counts distinct valid cold-key sigs; >=2 distinct passes.

Audit emit (Wave C.5): `sentinel_signer_rotated` fires on successful
mutation.

## Recovery ceremony (incident response)

Cold-key compromise of 1 of 3 sites:

1. Travel to the two surviving sites.
2. Edit YAML: set `revoked_at` + `revoked_reason="compromise"` on
   the compromised cold-key. Append a new cold-key entry generated
   at a FRESH geographic site (distinct from the breached one).
3. Sign with the two surviving cold-keys. Quorum met.
4. Audit emit: `sentinel_signer_revoked` (compromised key) +
   `sentinel_signer_rotated` (replacement key).

Quorum cold-key compromise (2 of 3): see ADR-121 §4 — no in-band
recovery; Owner rebuilds via forked repo with hand-distributed
trust. This is intentionally out-of-scope for the framework.

## ATT&CK references

- **T1556 — Modify Authentication Process.** Direct edit of
  `sentinel-signers.txt` or the YAML registry is the canonical
  T1556 surface. Mitigated by kernel HARD-DENY of the YAML path
  (ADR-116-AMEND-1) + cold-key quorum requirement for mutations
  (ADR-121 §2).
- **T1584 — Compromise Infrastructure.** Hot-key compromise on the
  Owner workstation falls under T1584.005 (compromised credentials).
  Mitigated by limited hot-key authority (signs daily sentinels only,
  cannot mutate the registry) and revocation propagation = T+0ms
  (`load_registry` re-parses on every hook fire; no cache in v1.x —
  ADR-121 §6).
- **T1565.001 — Stored Data Manipulation.** Tampering with the
  on-disk YAML to swap a hot-key fingerprint pre-hook-invocation is
  the cold-start integrity surface. Mitigated by
  `_BOOTSTRAP_REGISTRY_SHA256` module-level constant baked into the
  hook source (ADR-121 §5); on-disk hash mismatch → fail-CLOSED with
  `reason_code=bootstrap_sha_mismatch`.

See ADR-121 §7 + PLAN-089 wave-c1 for full threat model.
