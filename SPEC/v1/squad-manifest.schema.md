# SPEC v1 — squad-manifest.schema

> **Spec version:** 1.0.0-rc.1
> **Status:** normative
> **Applies to:** ADR-039 (Skill marketplace protocol — self-signed
> tarballs with allowlist + revocation).

A squad marketplace tarball MUST contain a `manifest.json` at the root
of the single top-level `<slug>/` directory. A mirror `manifest.yaml`
MAY be included for human publication but is advisory only — the
machine-readable authority is `manifest.json`.

## 1. Filesystem shape inside the tarball

```
<slug>/
    manifest.json            (MANDATORY — programmatic)
    manifest.yaml            (OPTIONAL — human mirror)
    team-personas.md         (MANDATORY per ADR-009)
    pitfalls.yaml            (MANDATORY per ADR-009)
    task-chains.yaml         (MANDATORY per ADR-009)
    skills/<skill-id>/SKILL.md   (≥ 3 skills per ADR-009)
    examples/PLAN-EXAMPLE.md (OPTIONAL per ADR-009)
```

The top-level directory name MUST equal the `squad_name` field in the
manifest. `squad-import.py` refuses a tarball where these diverge.

## 2. manifest.json fields

```json
{
  "squad_name": "edtech",
  "version": "1.0.0",
  "created_at": "2026-04-14T12:00:00Z",
  "squad_contract": "v1",
  "files": [
    "edtech/team-personas.md",
    "edtech/pitfalls.yaml",
    "..."
  ],
  "files_sha256": {
    "edtech/team-personas.md": "<64-hex>",
    "...": "..."
  }
}
```

### Required fields

| Field            | Type          | Notes |
|------------------|---------------|-------|
| `squad_name`     | string        | Matches `<slug>/` directory prefix; kebab-case. |
| `version`        | string        | SemVer. `1.0.0` is the initial stable shape. |
| `created_at`     | ISO-8601 UTC  | Second-precision, `Z` suffix. |
| `squad_contract` | string        | MUST equal `"v1"` for ADR-009 compatibility. |
| `files`          | array[string] | Sorted list of `<slug>/path` entries in the tar. |
| `files_sha256`   | object        | `{relative_path: <64-hex>}`. One entry per file. |

### Reserved / optional fields

Future extensions (e.g. `signer_uid`, `license`, `requires_skills`) MUST
be additive and tolerated by `squad-import.py`. Consumers ignore unknown
fields.

## 3. Hash format

All hashes are lowercase hex SHA-256 digests of the raw file bytes. The
manifest's SHA-256 (used for revocation lookups) is computed over the
manifest.json bytes themselves as stored in the tarball.

## 4. Validation order (CRITICAL — security contract)

The `squad-import.py` pipeline MUST perform these checks in this order;
reordering is a security regression and requires an ADR amendment:

1. **Signature verification** — `gpg --verify <sig> <tarball>` on the
   raw tarball bytes. NOTHING in the archive is parsed until this
   passes. This is the sig-before-parse guarantee (consensus CR2).
2. **Size cap** — reject archives > `CEO_SQUAD_MAX_BYTES` (default
   5 MiB). Prevents resource-exhaustion via decompression bombs.
3. **Allowlist** — `--source <URI>` must appear in
   `.claude/settings.json` `squad_allowlist`. Empty list = import
   refused.
4. **Revocation** — manifest SHA-256 must not appear in
   `.claude/squad-revocations.jsonl`.
5. **Path-traversal refusal** — iterate tarfile members BEFORE
   extraction; refuse symlinks, hardlinks, absolute paths, or any
   name containing `..`.
6. **Extraction** — to a tmpdir first, atomic rename on success.
7. **Contract validation** — subprocess invoke
   `validate-squad-contract.py`. On failure, rollback (restore backup
   on `--force` collision, otherwise delete).
8. **Audit** — emit `squad_imported` event with `manifest_sha256`,
   `signer_fingerprint`, and `source`.

## 5. Security rationale

### Why sig-before-parse?

Historically, archive formats (zip, tar) have had CVEs in the parser
itself (path-traversal via `../`, infinite-loop via malformed headers,
symlink attacks). Parsing an UNTRUSTED tarball is a pre-auth RCE
surface. By demanding a valid detached signature on the raw bytes
BEFORE we open the tarball, we constrain the attack surface to:
"adversary controls signed archive bytes." This is equivalent to
standard TLS-terminated download + cert pin.

### Why self-signed + allowlist (not PGP web-of-trust)?

PGP WoT assumes a cross-organization key ecosystem. ceo-orchestration
is installed into repos one at a time, each with its own trust policy.
A pin-allowlist matches how operators already think about
dependencies: "I trust `github.com/acme/squad-edtech@v1` specifically."
Rotation = edit `.claude/settings.json` with PR review. Revocation =
append to `.claude/squad-revocations.jsonl`.

### Why TOFU is an EXPLICIT non-goal

TOFU (trust-on-first-use) would let any squad import itself on first
contact. That is unacceptable: the framework must NOT accept unknown
sources silently. The empty-default allowlist enforces this:
`squad_allowlist: []` means NO sources importable until the Owner adds
entries. This mirrors CODEOWNERS for branch protection.

## 6. Example manifest.yaml (human mirror)

```yaml
squad_name: edtech
version: 1.0.0
created_at: "2026-04-14T12:00:00Z"
squad_contract: v1
files:
  - edtech/team-personas.md
  - edtech/pitfalls.yaml
  - edtech/task-chains.yaml
  - edtech/skills/student-data-privacy/SKILL.md
files_sha256:
  "edtech/team-personas.md": "<64-hex>"
```

Format is best-effort; `squad-import.py` never reads `manifest.yaml`.
The ground truth is `manifest.json`.

## 7. Parser tolerance

- Additional fields MUST NOT cause parse failures.
- `manifest.yaml` MAY be absent (auto-generated, human-only).
- `squad_contract: v1` is the only value honored by Sprint 11
  `squad-import.py`. Future `v2` would require a matching import
  path update + ADR.

## 8. Version history

| SPEC version | Notes |
|---|---|
| 1.0.0-rc.1 | Initial contract — ADR-039, PLAN-011 Phase 12. |
