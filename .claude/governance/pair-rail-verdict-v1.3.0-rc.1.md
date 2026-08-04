# Pair-Rail Verdict — v1.3.0-rc.1

```yaml
verdict: GO
generated_at: 2026-08-04T22:03:40Z
ttl_hours: 24
parent_sha: 4111a115190d375c39c90cc33ac1d9d5899c1cf2
release_tag: v1.3.0-rc.1
inputs_hash: 1c1d8f4404521de942451b7f7c25cba721eedaeb51d6a4f01d3dde20335ed10f
inputs_hash_paths_manifest_sha: b3ab0242a6ff4e12fdf2fd90c47cbc23649ab07226340c8b7aacbb0f9cc093e0
tool_versions:
  codex_cli: 0.144.6
  codex_target_triple: aarch64-apple-darwin
  codex_payload_sha256: 80a3933d11a9d13ef806aa24f7bb8afc9169cfe4e9b09d6da6a92922cbde9cff
  claude_code: claude-fable-5
  python: 3.9.6
transcript_hash: f7899f53aa844536a7dace9434a2d26d662f773e9891b39e83f5452b0a8d15e6
findings: [r4-P1-bump-idempotence-FIXED, r4-P2-checklist-coherence-FIXED]
gpg_signature: base64:LS0tLS1CRUdJTiBQR1AgU0lHTkFUVVJFLS0tLS0KCmlKRUVBQllLQURrV0lRU3VteU52MnZCR0tIUUdER3ZQejZ6d0F6WGNkQVVDYW5KaHZCc1VnQUFBQUFBRUFBNXQKWVc1MU1pd3lMalVyTVM0eE1pd3dMRE1BQ2drUXo4K3M4QU0xM0hRYUpBRC9aT2JYNEV2aVhNb3U0YVF5aXVQZApvN0lYeU5OSzlCck02bE5BcTdweXJnb0JBTHNXdW1lTXR0ZEd0T2ZZNDl0dlRKelczNFdsajBHWS9uSWRzMVlnCnRwMEsKPUx1OW0KLS0tLS1FTkQgUEdQIFNJR05BVFVSRS0tLS0tCg==
```

## Signature verification recipe

base64 -d of the value after `base64:` → detached .asc; verify against
`.claude/plans/PLAN-162/ga/verdict-fields-v1.3.0-rc.1.txt` (committed alongside). Signer CFCFACF00335DC74.

<!-- VERDICT: GO -->
## Review record — release-mechanics re-pass (advisory input to this verdict)

- **Reviewer:** codex-cli 0.144.6 (`codex exec --sandbox read-only`),
  prompt+diff routed through the ADR-114 redactor as ONE pipeline;
  ADR-182 payload pin verified byte-exact before invocation
  (`80a3933d…`, aarch64-apple-darwin).
- **Date:** 2026-08-04 (S293). **Rounds:** 4.
- **Scope:** release mechanics as the v1.2.0..HEAD unified diff (VERSION,
  npm/, pyproject, CHANGELOG, INSTALL, docs/ARCHITECTURE, README,
  SECURITY, VERSIONING, SBOM, release.yml, npm-publish.yml,
  release-checklist.md, verify-counts.sh, release driver).
- **Trajectory:** r1 NO-GO (5) → r2 NO-GO (6) → r3 NO-GO (5) → r4
  GO-WITH-CONDITIONS (2). **18 findings, 17 real and fixed, 1 refuted
  with a citation** (the SemVer-MAJOR claim: this repo's published
  `VERSIONING.md` §MAJOR is scoped to schema-consumer breakage; the
  sentinel-unlock provenance requirement is the literal §MINOR
  "new trust boundary" case, and it is called out in CHANGELOG
  §Security with the adopter action).
- **Both r4 conditions were closed BEFORE this verdict, not carried:**
  `bump` is idempotent (a no-op bump is success — the documented
  three-phase path stays executable on an already-prepared tree) and
  the checklist no longer claims the driver covers every site.
- **Found while closing them (self-caught, not by the rail):** the
  post-bump hint used `${STABLE:+…}`, which expands for `STABLE=0`
  and told the Owner to cut the STABLE tag during an RC run. Fixed
  and both branches exercised.
- **Material catches this round set:** a signed tag annotation still
  describing v1.2.0; `bump --dry-run` leaving debris (restore list
  shorter than the write list — the S273 class); three current-version
  declarations (SBOM/SECURITY/VERSIONING) stale AND unwatched; a
  support-window guard that watched only `Current MINOR`.
