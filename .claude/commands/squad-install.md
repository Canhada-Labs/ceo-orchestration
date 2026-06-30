---
command: /squad-install
description: Import a squad from a signed tarball into .claude/skills/domains/
usage: "/squad-install --tarball <path> --signature <path> --source <URI>"
idempotent: false
allowed-tools: Bash, Read
---

# /squad-install — Install a signed squad bundle

Verifies a detached GPG signature on a tarball, checks the source URI
against ``.claude/settings.json`` ``squad_allowlist``, checks the
manifest SHA-256 against ``.claude/squad-revocations.jsonl``, refuses
symlink / path-traversal entries, extracts to
``.claude/skills/domains/<slug>/``, and runs
``validate-squad-contract.py`` against the result. On any validation
failure, NOTHING is written to disk.

## Arguments received

`/squad-install $ARGUMENTS`

`$ARGUMENTS` MUST provide three flags (order flexible):

- `--tarball <path>` — local path to the `.tar.gz` archive.
- `--signature <path>` — local path to the detached `.sig` file.
- `--source <URI>` — the pin-allowlist URI (e.g. `github.com/acme/squad-edtech@v1`).

Optional:

- `--force` — overwrite an existing squad with the same slug (the old
  tree is backed up to a tempdir first and restored if the contract
  validator rejects the new one).

## Procedure

### Step 1 — Refuse missing required args

Parse `$ARGUMENTS`. If any of `--tarball`, `--signature`, or `--source`
is missing, tell the user which one is missing and stop. Do NOT invent
defaults.

### Step 2 — Invoke the backing script

```bash
python3 .claude/scripts/squad-import.py \
    --tarball "$TARBALL" \
    --signature "$SIGNATURE" \
    --source "$SOURCE" \
    ${FORCE:+--force}
```

Do NOT pass `$ARGUMENTS` through a shell-interpolated string; pass
each parsed flag as a separate argv entry.

### Step 3 — Interpret exit code

- `0` → imported cleanly. Tell the user:
  - the slug installed
  - the `manifest_sha256` (short form, e.g. first 16 chars)
  - the `signer_fingerprint`
  - the installed path
  - "run `validate-squad-contract.py --squad <path>` if you want to re-verify"
- `1` → IO error (missing file, collision without `--force`). Surface
  stderr and stop.
- `2` → validation failure (signature / size / allowlist / revocation /
  path-traversal). Surface stderr and stop. The reason code in stderr
  tells you which gate fired.
- `3` → the tarball passed signature + allowlist + path checks but the
  extracted squad failed `validate-squad-contract.py`. Rollback was
  applied. Suggest the publisher fix their squad per ADR-009 minimum
  counts.

### Step 4 — Follow-up

If the import succeeded, remind the user:

- "The squad is installable via `install.sh --profile core,<slug>`."
- "Squad source is pinned to the allowlist entry you passed; rotating
  the allowlist happens manually in `.claude/settings.json`."
- "To revoke this squad later, append an entry to
  `.claude/squad-revocations.jsonl` with the `manifest_sha256` shown."

## Kill-switch

If `CEO_SOTA_DISABLE=1` is set, `squad-import.py` exits 0 with a
"disabled" message and no filesystem changes.

## Exit codes

- 0 — imported cleanly (or disabled)
- 1 — IO / collision error
- 2 — signature / size / allowlist / revocation / traversal refusal
- 3 — squad contract (ADR-009) failure after extraction, rollback applied
