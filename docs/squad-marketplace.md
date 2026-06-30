# Squad Marketplace — Discovery & Trust Model

> Status: rc.1 (PLAN-011 Phase 12). See ADR-039 for the normative
> security contract and SPEC/v1/squad-manifest.schema.md for the
> manifest format.

The squad marketplace is how third parties publish squads (domain
bundles: personas + pitfalls + task-chains + skills) that operators
can install into a ceo-orchestration-powered repo without modifying
the framework itself.

## 1. Trust model in one paragraph

ceo-orchestration's squad marketplace uses **self-signed tarballs +
pin-allowlist + revocation ledger**. Every squad install requires a
detached GPG signature on the tarball bytes AND a matching entry in
`.claude/settings.json` `squad_allowlist` AND no match in
`.claude/squad-revocations.jsonl`. **TOFU (trust-on-first-use) is
deliberately impossible** — the default allowlist is `[]`, refusing
every import until the Owner adds a specific pin.

This is the same pattern operators already use for CODEOWNERS +
branch protection. The PR that edits `squad_allowlist` is the
trust decision record.

## 2. Allowlist mechanics

`.claude/settings.json` carries one top-level key:

```json
{
  "squad_allowlist": [
    "github.com/acme/squad-edtech@v1",
    "github.com/acme/squad-fintech@v2"
  ]
}
```

Rules:

- Empty list (or missing key) = nothing importable. Secure default.
- Entries are opaque URIs to `squad-import.py` — they are matched
  **literally** against the `--source` flag. Rotating a pinned
  version (e.g. `@v1` → `@v2`) requires editing the allowlist.
- Each entry represents "this specific version of this specific squad
  from this specific source is trusted." A wildcard at any level is
  a loss of trust specificity and therefore **not supported**.

### Adding an entry (operator workflow)

1. Publisher hands you the tarball + detached `.sig` + the source URI.
2. You verify the tarball locally:

   ```bash
   gpg --verify squad-edtech-v1.tar.gz.sig squad-edtech-v1.tar.gz
   ```

3. You import the publisher's GPG key into your local keyring (or a
   dedicated keyring for marketplace squads).
4. You open a PR adding the URI to `squad_allowlist`. Reviewer confirms
   fingerprint + source out-of-band.
5. Merge → `/squad-install --tarball … --signature … --source …`.

## 3. Revocation process

`.claude/squad-revocations.jsonl` is a local append-only ledger. Each
line is one JSON object:

```json
{"squad_name": "edtech", "manifest_sha256": "<64-hex>", "revoked_at": "2026-04-14T12:00:00Z"}
```

When `squad-import.py` computes a manifest's SHA-256 and the hash
matches a revocation entry, the import is refused with exit code 2 and
reason code `revoked`.

Revocation scenarios:

- **Publisher key compromised** — revoke every `manifest_sha256` you
  already imported from that publisher AND remove their allowlist
  entry. Rotate by importing a freshly signed tarball under a new key.
- **Squad bug that's too bad to ship a patch** — revoke the affected
  manifest SHA and install a replacement.
- **Policy change** — if an industry regulator obsoletes a compliance
  pattern mid-quarter, you can revoke mid-flight without waiting for
  the publisher to issue a new version.

Revocation is operator-scoped — editing this file is a local action.
For centralized revocation across an org, commit the ledger to the
repo that ships ceo-orchestration and propagate through `install.sh`.

## 4. Conflict resolution: existing squad, same slug

If `.claude/skills/domains/<slug>/` already exists, `squad-import.py`
refuses the import with exit code 1 ("collision"). To proceed, pass
`--force`:

```bash
/squad-install --tarball … --signature … --source … --force
```

Force semantics:

1. The existing squad tree is moved to a tempdir (preserved).
2. The new tarball is extracted in its place.
3. `validate-squad-contract.py` runs on the new tree.
4. On validator failure, the backup is restored and the import exits
   with code 3.
5. On success, the backup is discarded.

The `squad_imported` audit event is emitted regardless so your audit
log captures the overwrite.

## 5. How to publish a squad (publisher workflow)

### Step 1 — Develop the squad

Follow ADR-009 (squad bundle contract) — minimum:

- `team-personas.md` with ≥ 5 personas and ≥ 2 VETO holders with
  distinct scopes.
- `pitfalls.yaml` with ≥ 12 entries under `pitfalls:`.
- `task-chains.yaml` with ≥ 2 chains.
- `skills/<skill-id>/SKILL.md` × ≥ 3.
- `examples/PLAN-EXAMPLE.md` (optional but recommended).

Verify your squad passes `validate-squad-contract.py` locally:

```bash
python3 .claude/scripts/validate-squad-contract.py \
    --squad .claude/skills/domains/<slug>/
```

### Step 2 — Export to tarball

```bash
python3 .claude/scripts/squad-export.py \
    --squad <slug> \
    --version 1.0.0 \
    --output ./squad-<slug>-v1.0.0.tar.gz
```

This writes a deterministic tarball (mtime=0, mode=0o600 per entry)
with `<slug>/manifest.json` + `<slug>/manifest.yaml` at the root.

### Step 3 — Sign it

```bash
python3 .claude/scripts/squad-export.py \
    --squad <slug> \
    --version 1.0.0 \
    --sign-with <your-gpg-fingerprint> \
    --output ./squad-<slug>-v1.0.0.tar.gz
```

Output: `./squad-<slug>-v1.0.0.tar.gz` + `.sig` (detached, armored).

### Step 4 — Publish

Host the tarball + sig at a stable URI. Consumers need BOTH files.
Recommended: GitHub release, stable download URLs, ssh-authenticated
endpoint. Consumers import your public key out-of-band into a
keyring they control.

## 6. How to verify a squad before importing (consumer workflow)

```bash
# 1. Import publisher key into a dedicated keyring (not your personal one).
export GNUPGHOME=~/.ceo-marketplace-keyring
mkdir -p $GNUPGHOME && chmod 700 $GNUPGHOME
gpg --import publisher-public-key.asc

# 2. Verify the detached signature.
gpg --verify squad-edtech-v1.tar.gz.sig squad-edtech-v1.tar.gz

# 3. Compute the manifest SHA-256 out-of-band (read the tarball without
#    extracting; compare to what the publisher advertised).
python3 -c "
import hashlib, tarfile, sys
with tarfile.open('squad-edtech-v1.tar.gz', 'r:gz') as t:
    for m in t.getmembers():
        if m.name.endswith('/manifest.json'):
            print(hashlib.sha256(t.extractfile(m).read()).hexdigest())
            break
"
```

If all three match expectations, open the PR to add the source to
`squad_allowlist`, then run `/squad-install`.

## 7. Kill-switch: `CEO_SOTA_DISABLE=1`

If you need to halt all squad imports framework-wide (security
incident, policy change, etc.), set:

```bash
export CEO_SOTA_DISABLE=1
```

Both `squad-import.py` and `squad-export.py` exit 0 with a "disabled"
message and make no filesystem changes. The kill-switch is
deliberately blunt — no per-source granularity — so the operator can
reach for it without thinking through edge cases.

## 8. What the marketplace is NOT

- **Not a package manager.** No transitive dependency resolution, no
  lockfile, no version solver. One squad, one install, one pin.
- **Not a registry.** No centralized index. Operators maintain their
  own list in `settings.json`.
- **Not a sandbox.** Squads are installed into the framework exactly
  as if they were authored in-repo. Trust the publisher.
- **Not a replacement for CODEOWNERS.** The allowlist entry is the
  trust decision; who-can-edit-`settings.json` is still enforced by
  branch protection.

## 9. FAQ

**Q: Can I import a squad from an HTTPS URL directly?**
A: No. The import CLI takes local paths. Download the tarball + sig
separately, verify OOB, then run `/squad-install`. This is by design —
network fetch is a larger attack surface than filesystem read.

**Q: What if the publisher rotates their key?**
A: Revoke the old allowlist entry (or all old manifest SHAs via the
revocation ledger), import the new key, add a new allowlist entry for
the re-signed tarball, import.

**Q: Can a squad install be partial / dry-run?**
A: `squad-import.py` has no `--dry-run` today. Contributions welcome.

**Q: How does this interact with skill-patch-apply (ADR-031)?**
A: Both surfaces share the same `GpgKeyringFixture` and the same
sig-before-parse discipline. They differ in scope: skill-patches
propose in-repo mutations to existing skills; marketplace squads
install entirely new squads. A consumer can gate both behind the
same GPG signing policy.
