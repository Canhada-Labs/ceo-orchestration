# Pair-Rail Verdict — v1.1.0-rc.1

```yaml
verdict: GO
generated_at: 2026-07-14T11:58:14Z
ttl_hours: 24
parent_sha: 09f00401568ec77214fa7cf41d6e1c7d372438cc
release_tag: v1.1.0-rc.1
inputs_hash: 2b0095f56d7d7a36b5d9c5243cfb95a42c50016cebccfafeefc9917bb80e65f5
inputs_hash_paths_manifest_sha: b3ab0242a6ff4e12fdf2fd90c47cbc23649ab07226340c8b7aacbb0f9cc093e0
tool_versions:
  codex_cli: 0.144.1
  codex_cli_binary_sha256: 134063e133f0b4244fa3b251acf973d4fe4b4aeeacbdc135211bf480f59f1477
  claude_code: claude-fable-5
  python: 3.9.6
transcript_hash: d4ffad4e42b06ce1bbc7db5c893a3fd5d2dc65e82ba44259dc9b3a2b6fe87498
findings: []
gpg_signature: base64:LS0tLS1CRUdJTiBQR1AgU0lHTkFUVVJFLS0tLS0KCmlKRUVBQllLQURrV0lRU3VteU52MnZCR0tIUUdER3ZQejZ6d0F6WGNkQVVDYWxZa1Zoc1VnQUFBQUFBRUFBNXQKWVc1MU1pd3lMalVyTVM0eE1pd3dMRE1BQ2drUXo4K3M4QU0xM0hSRGp3RUF6cFZnOUJDZ2JsNno1bm0vODN4cwpGUVh6dVdreS9UK0xJMy9WcGZNK0lkTUJBSjdDeDJQNFErb3NMQjBPYnFveUxsRVBFM0hQSEN6NTNIQ3ZzeEVFCnZ3VUkKPU1vcjUKLS0tLS1FTkQgUEdQIFNJR05BVFVSRS0tLS0tCg==
```

## Signature verification recipe

base64 -d of the value after `base64:` → detached .asc; verify against
`.claude/plans/PLAN-158/architect/rc/verdict-fields-v1.1.0-rc.1.txt` (committed alongside). Signer AE9B236FDAF0462874060C6BCFCFACF00335DC74.

<!-- VERDICT: GO -->
## Review record — pair-rail RC rounds (advisory input to this verdict)

- **Reviewer:** codex-cli 0.144.1 (`codex exec --sandbox read-only`,
  diff pipe; binary sha verified against
  `.claude/governance/codex-cli-binary-sha256.txt` at review time)
- **Date:** 2026-07-13 (S272)
- **Input scope:** release-mechanics surfaces (VERSION, npm/package.json,
  CHANGELOG.md, npm-publish.yml, release.yml, install scripts,
  SPEC/v1/npm-shim.md, SBOM.md, GOVERNANCE-MAP.md) + the 18-path
  trust-chain manifest files, as the v1.0.1..HEAD unified diff, + the
  62-commit log triage. Per-plan content diffs were pair-rail-reviewed at
  their own landing ceremonies (PLAN-153/154/155/156/158 records).
- **Advisory only** — decision is the CEO's; the Owner authorizes via the
  GPG-signed envelope above ([[feedback-pair-rail-clean-round-not-proof]];
  stopping criterion: every file APPROVE, single-issue REJECTs folded and
  re-reviewed once).

## Round 1 (verbatim)

15/16 APPROVE; 1 REJECT:

```text
FILE: SPEC/v1/npm-shim.md — REJECT — Stale cross-reference contradicts the OIDC Trusted Publishing migration.
FINDINGS: P2 — SPEC/v1/npm-shim.md:107 — Cross-reference still says OIDC trusted publisher is "not yet configured," while §Publishing and npm-publish.yml state registry auth is now npm Trusted Publishing.
OVERALL: GO-WITH-CONDITIONS — Release mechanics look intact, but fix the stale normative SPEC line before tagging.
```

(Full R1 per-file table in the committed transcript.)

**Fold:** real stale-claim (Wave 1 patcher amended §Publishing but missed
the §Cross-reference parenthetical). Fix staged at
`.claude/plans/PLAN-158/staged/rc/` and applied by this ceremony under
SENT-RC-SPEC BEFORE the envelope above was computed — the tagged tree
contains the corrected SPEC.

## Round 2 — corrected file only (verbatim)

```text
FILE: SPEC/v1/npm-shim.md — APPROVE — Cross-reference now matches §Publishing, and the version-history note is doc-only with no new contract or speed claim.
OVERALL: APPROVE
```

## Net result

16/16 APPROVE → **GO**. The R1 P2 finding is remediated in the tagged
tree (SENT-RC-SPEC commit precedes the verdict commit), hence
`findings: []` in the envelope.

<!-- FINDINGS-YAML
findings: []
FINDINGS-YAML -->
