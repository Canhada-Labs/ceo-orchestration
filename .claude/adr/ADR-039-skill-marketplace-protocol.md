# ADR-039: Skill (squad) marketplace protocol

## Status: ACCEPTED (2026-04-14)

## Context

Sprints 1-10 shipped 5 squads (fintech, lgpd-heavy-saas, trading-hft,
edtech, government) inside this repo. PLAN-011 Phase 7a (Agent
Architect dogfood) and Phase 7b (second dogfood) proved the Architect
methodology converges to ~1h per squad. The next step is letting third
parties publish squads without modifying ceo-orchestration itself — a
**squad marketplace**.

Consensus round-1 §CR2 flagged this surface as **CRITICAL** before
shipping a single importer line:

- Tarballs parsed BEFORE signature verification = pre-auth RCE. Python
  `tarfile` has had CVEs in the parser itself (symlink traversal,
  malformed headers). Accepting untrusted archive bytes and parsing
  them is unsafe regardless of what we do after the parse.
- Self-signed with no trust policy = TOFU. Any squad imports itself on
  first contact. There is no revocation recourse.
- Path traversal via `..` in tarball names = filesystem-wide write.
  Even with signature verification, a signed malicious squad could
  overwrite `~/.ssh/authorized_keys`.

These three failure modes are the same attack surface as the npm /
PyPI incidents of the past decade. We design around them from day 1.

## Decision Drivers

- **Sig-before-parse.** NO tarball bytes are parsed (tarfile.open,
  manifest read, member enumeration) until `gpg --verify` returns 0
  on the raw tarball bytes with a detached signature.
- **Allowlist-first, not TOFU.** The default `squad_allowlist` is the
  empty list `[]`, which refuses every import. Operators add specific
  pin URIs (`github.com/acme/squad-edtech@v1`) with PR review.
- **Revocation mechanism.** A local JSONL ledger
  (`.claude/squad-revocations.jsonl`) lets operators banned a
  previously trusted squad without touching the allowlist.
- **Filesystem-safe extraction.** Every member is checked before
  extraction: no symlinks, no hardlinks, no absolute paths, no `..`.
  Resolved paths are asserted to stay under the destination root.
- **Size cap.** Default 5 MiB per archive protects against
  decompression bombs.
- **Manifest SHA-256 in audit.** The `squad_imported` event records
  the manifest hash + signer fingerprint + source URI. Tampering
  leaves an audit trail.
- **Contract validator post-extract.** `validate-squad-contract.py`
  (ADR-009 minimum counts) runs against the extracted squad. Failures
  trigger rollback.

## Options Considered

### Option A: Unsigned tarball + TOFU

- **Pros:** Zero friction to contribute; any URL installable.
- **Cons:** Pre-auth RCE on first malicious squad. No revocation
  recourse. Indistinguishable from `curl | bash`.

### Option B: Self-signed tarball + pin-allowlist + revocation (chosen)

- **Pros:** No key-infrastructure investment required. Operator-scoped
  trust: "I trust these specific squads." Revocation via local ledger.
- **Cons:** Keys aren't cross-verifiable without OOB (out-of-band)
  exchange. Accepted — see §Security rationale.

### Option C: PGP web-of-trust (WoT)

- **Pros:** Cross-organization trust. Keys signed by known signers
  inherit trust transitively.
- **Cons:** WoT is not widely adopted; setup burden high; trust graph
  hard to reason about. Overkill for a framework that runs inside a
  single org's repo.

### Option D: Trusted CA (TLS-style)

- **Pros:** Familiar model.
- **Cons:** Requires running a CA; no single vendor would host this.
  Enterprise-only and overkill.

## Decision

**Option B: self-signed tarball + pin-allowlist + revocation.**

TOFU is an explicit non-goal. The empty-default allowlist enforces
this: no allowlist entry = no imports. Matches how operators already
think about CODEOWNERS + branch protection.

## CR2 Mitigation Table (evidence-linked)

| Mitigation | Where enforced | Evidence path |
|---|---|---|
| Signature BEFORE open | `squad-import.py:395 _gpg_verify` → `squad-import.py:429 tarfile.open` (strict line order) | `test_squad_import.py::test_unsigned_rejected`, `test_signature_invalid_exit_2`, `test_sig_before_parse_order` |
| Detached sig only (no in-band) | `squad-import.py:395` passes raw bytes path | Same |
| Size cap | `squad-import.py:92 _read_bytes` stat check | `test_oversized_rejected` |
| Allowlist, empty default | `squad-import.py:158 _check_allowlist` | `test_not_in_allowlist_exit_2` |
| Revocation ledger | `squad-import.py:169 _check_revocation` | `test_revoked_exit_2` |
| Symlink refusal | `squad-import.py:194 _refuse_bad_members` | `test_symlink_refused` |
| Hardlink refusal | Same | `test_symlink_refused` (hardlink variant) |
| Absolute-path refusal | Same | `test_path_traversal_refused` |
| `..` entry refusal | Same | `test_path_traversal_refused` |
| Resolved-path containment | `squad-import.py:248 resolve()+relative_to()` | `test_path_traversal_refused` |
| Contract validator post-extract | `squad-import.py:273 _invoke_contract_validator` | `test_contract_fail_rollback` |
| Audit with SHA-256 | `emit_squad_imported(manifest_sha256=...)` | `test_audit_emitted` |

## Consequences

### Positive

- Squads become distributable without mutating ceo-orchestration.
- The attack surface is bounded by well-understood primitives
  (GPG detached sigs, JSON allowlist, path checks).
- Revocation is O(1) append to a local file.
- Audit trail ties every install to a fingerprint + source URI.
- CEO_SOTA_DISABLE=1 kill-switch gives operators a reversible
  emergency stop (debate S4).

### Negative

- GPG key lifecycle (rotation, expiration) is the operator's problem.
  Accepted: same as SSH keys, which this framework already relies on.
- The empty-default allowlist breaks the "install and go" flow — a
  PR must approve every new source. Accepted; explicit trust decision.
- A malicious signer IN the allowlist can still publish a bad squad;
  the contract validator catches ADR-009 violations, but not logic
  bugs. Detectable only post-install via audit + behavioral testing.

### Neutral

- The `manifest.yaml` human mirror is advisory; `manifest.json` is the
  machine authority. Eliminates dependency on PyYAML during import
  (stdlib-only constraint).

## Blast Radius

**L3** — touches the framework's installation surface. Adds a CLI
(`squad-import.py`) that writes to `.claude/skills/domains/`, which is
otherwise only written by `install.sh`. Reversibility: HIGH — any
installed squad can be removed with `rm -rf
.claude/skills/domains/<slug>/`.

## Open Questions (Sprint 12+)

- **Key rotation UX.** Operators currently must edit
  `squad_allowlist` manually to rotate a pinned version. A
  `--rotate` CLI flag that atomically updates the allowlist + re-runs
  import is Sprint-12 territory.
- **Multi-signer squads.** Some squads may be signed by an
  organizational threshold (k-of-n). `gpg --verify` handles detached
  sigs one at a time; threshold support would require a wrapper.
- **Marketplace discovery.** This ADR defines the IMPORT protocol, not
  the discovery mechanism. `docs/squad-marketplace.md` documents the
  URI format convention; a centralized index is out of scope.

## References

- PLAN-011 debate round-1 §CR2 (consensus CRITICAL)
- PLAN-011 consensus L5 (GPG keyring fixture shared with Phase 4)
- PLAN-011 consensus M8 (`/squad-install` slash command)
- PLAN-011 consensus S4 (`CEO_SOTA_DISABLE=1` kill-switch)
- PLAN-011 consensus S5 (behavior assertions per test)
- ADR-009 (squad bundle contract — validator invoked post-extract)
- ADR-031 (self-improving skills — parallel marketplace surface for
  skill patches; shares GPG keyring fixture)
- SPEC/v1/squad-manifest.schema.md

## Enforcement commit

`3455c4322b4d` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
