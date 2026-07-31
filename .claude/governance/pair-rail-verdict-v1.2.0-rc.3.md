# Pair-Rail Verdict — v1.2.0-rc.3

```yaml
verdict: GO
generated_at: 2026-07-31T12:24:51Z
ttl_hours: 24
parent_sha: ad0c1dbcbb3ed9df43e1bc1d8e9d06d43df96806
release_tag: v1.2.0-rc.3
inputs_hash: 4cac9ac85ae02d246d5ab9c45d26aa5fdf3474008636e1001fd33a75f06e6d70
inputs_hash_paths_manifest_sha: b3ab0242a6ff4e12fdf2fd90c47cbc23649ab07226340c8b7aacbb0f9cc093e0
tool_versions:
  codex_cli: 0.144.6
  codex_target_triple: aarch64-apple-darwin
  codex_payload_sha256: 80a3933d11a9d13ef806aa24f7bb8afc9169cfe4e9b09d6da6a92922cbde9cff
  claude_code: claude-opus-5
  python: 3.9.6
transcript_hash: 1e12b08399e906a0af7998a8a68fe9dde2bed44b8574c8c6d346428ebdd4522c
findings: [RC3-F7-upgrade-backup-P2-open]
gpg_signature: base64:LS0tLS1CRUdJTiBQR1AgU0lHTkFUVVJFLS0tLS0KCmlKRUVBQllLQURrV0lRU3VteU52MnZCR0tIUUdER3ZQejZ6d0F6WGNkQVVDYW15VUV4c1VnQUFBQUFBRUFBNXQKWVc1MU1pd3lMalVyTVM0eE1pd3dMRE1BQ2drUXo4K3M4QU0xM0hRNWRBRUF6cy9TQUJTUUtTK2hZMXBVanBITApPY241QncvZzJhaDRYbjl0MGhNMHdMWUErZ01UTGNIeWhjTFhpYXo2TnNKV2VKTlBlbjN6bGU1bjliV2EvMTl4Cjdjd0kKPUlSOGEKLS0tLS1FTkQgUEdQIFNJR05BVFVSRS0tLS0tCg==
```

## Signature verification recipe

base64 -d of the value after `base64:` → detached .asc; verify against
`.claude/plans/PLAN-163/rc/verdict-fields-v1.2.0-rc.3.txt` (committed
alongside). Signer AE9B236FDAF0462874060C6BCFCFACF00335DC74.

<!-- VERDICT: GO -->
## Review record — pair-rail RC re-pass (advisory input to this verdict)

- **Reviewer:** codex-cli 0.144.6 (`codex exec --sandbox read-only`, prompt
  piped through the ADR-114 redactor as ONE pipeline; native payload sha
  verified against `.claude/governance/codex-cli-pin-manifest.json`
  (ADR-182) before invocation — `80a3933d…` exact match,
  aarch64-apple-darwin).
- **Date:** 2026-07-31 (S287).
- **Input scope:** release-mechanics surfaces as the v1.1.0..HEAD unified
  diff (VERSION, npm/package.json + npm/README.md, pyproject.toml,
  CHANGELOG.md, INSTALL.md, docs/ARCHITECTURE.md, SECURITY.md,
  VERSIONING.md, SBOM.md, release.yml, npm-publish.yml,
  install/upgrade/build-plugin scripts, .claude-plugin manifests,
  SPEC/v1/npm-shim.md). Per-plan content diffs were pair-rail-reviewed at
  their own landing ceremonies (PLAN-160/161/163/164 records).
- **Advisory only** — decision is the CEO's; the Owner authorizes via the
  GPG-signed envelope above. Train context: rc.1 died on the
  plugin-manifest version gate (fixed via `build-plugin.py
  --write-manifests`, `15aff41`); rc.2 died on the canonical-doc-freshness
  gate (fixed via a real content review + re-stamp of
  SECURITY/VERSIONING/SBOM, `3627d12`). This re-pass reviewed the tree
  containing both fixes.

## Round 1 (verbatim) — 8/15 APPROVE, 7 REJECT, OVERALL NO-GO

Full verbatim output in the committed transcript
(`.claude/plans/PLAN-163/rc/verdict-transcripts-v1.2.0-rc.3.txt`,
sha256 = `transcript_hash` above). Finding disposition after first-hand
verification (C4: claims, not reports — every finding re-checked against
the tree before acting):

| # | Sev | File | Verified? | Disposition |
|---|-----|------|-----------|-------------|
| F1 | P1 | release.yml / ADR-182 | CONFIRMED — `status: PROPOSED`, `enforcement_commit` placeholder, while the step-15 gate enforces ADR-182 | **Remediated in THIS ceremony** (record flip to ACCEPTED + `enforcement_commit: a4371c7fe0cfb09cf0fee22c2e8bedd5a143215e`, the Owner-signed `[SENT-PLAN163-PIN]` GATE-PIN commit that landed the enforcement; the ADR itself said "to be ACCEPTED at the PLAN-163 GATE-PIN ceremony" — the flip was planned and missed) |
| F2 | P2 | CHANGELOG.md | CONFIRMED — "60 → 150 registry entries" was false (it is the pair-rail registration-timeout cap in seconds) | Fixed `ad0c1db`, re-approved R2 |
| F3 | P2 | INSTALL.md | CONFIRMED — settings.json listed as "NOT touched" while upgrade.sh migrates it | Fixed `ad0c1db`, re-approved R2 |
| F4 | P1 | SBOM.md | CONFIRMED — egress attestation omitted the pair-rail itself (default-on vendor egress) | Fixed `ad0c1db`, re-approved R2 |
| F5 | P2 | VERSIONING.md | CONFIRMED — "durable pin" not implemented (one-shot) | Fixed `ad0c1db`, re-approved R2 |
| F6 | P2 | docs/ARCHITECTURE.md | CONFIRMED — 182 vs 184 ADRs | Fixed `ad0c1db`, re-approved R2 |
| F7 | P2 | scripts/upgrade.sh:1776 | CONFIRMED — settings backup `cp … 2>/dev/null \|\| true` then unconditional "BACKED UP" | **OPEN** — canonical-guarded code path; deferred to the next sentinel ceremony (candidate PLAN-162/165 scope). Carried in `findings:` above |

## Round 2 (verbatim) — fold re-review, 5/5 APPROVE, OVERALL GO

```text
FILE: CHANGELOG.md — APPROVE — The 60 → 150 change is correctly identified as the pair-rail registration-timeout cap, not registry cardinality.
FILE: INSTALL.md — APPROVE — The settings baseline migration, operator-value preservation, and pre-migration backup are now documented.
FILE: SBOM.md — APPROVE — The default pair-rail vendor egress and its redaction, pin verification, and kill switch are now disclosed.
FILE: VERSIONING.md — APPROVE — The documentation now accurately describes --pin as one-shot rather than durable.
FILE: docs/ARCHITECTURE.md — APPROVE — The stated count of 184 ADRs exactly matches the files on disk.
OVERALL: GO — All five Round-1 documentation findings are corrected within this re-review scope.
```

## Net result

R1: 7 REJECTs, all verified first-hand; 5 fixed and re-approved (R2 GO),
F1 remediated inside this ceremony (record-only flip of an
already-Owner-authorized enforcement), F7 carried OPEN as a P2 with a
named remediation path. Release mechanics themselves: 15/15 surfaces now
APPROVE or remediated → **GO** with one open non-blocking finding.

<!-- FINDINGS-YAML
findings:
  - id: RC3-F7
    severity: P2
    path: scripts/upgrade.sh:1776
    claim: settings backup failure is suppressed (cp 2>/dev/null || true) while "BACKED UP" prints unconditionally
    disposition: open-deferred (canonical-guarded; next sentinel ceremony)
FINDINGS-YAML -->
