# Pair-Rail Verdict — TEMPLATE (Phase 6)

Owner authors a verdict file at
`.claude/governance/pair-rail-verdict-<release-tag>.md` BEFORE
each `git tag <release-tag>` push. The release.yml step 15
(`validate-pair-rail-verdict.py`) reads this file + asserts the
verdict was signed against the same release_tag + inputs_hash the
release run is computing.

## Required fields (validator parses YAML frontmatter)

```yaml
verdict: GO | NO-GO | GO-WITH-CONDITIONS
generated_at: <ISO 8601 UTC>
ttl_hours: 24
parent_sha: <40-char SHA — the commit the verdict was generated AGAINST (parent of the verdict-file commit). Resolves the v1.16.0 self-reference bug per S104 redesign. Compute via `git rev-parse HEAD` BEFORE creating the verdict commit.>
# commit_sha: <DEPRECATED — kept for v1.16.0-era backward-compat. Use parent_sha for new verdicts.>
release_tag: <e.g. v1.16.0-rc.1>
inputs_hash: <SHA256 of canonical_json envelope of git-hash-object SHAs for ALL paths in pair-rail-inputs-hash-manifest.txt>
inputs_hash_paths_manifest_sha: <SHA-256 of pair-rail-inputs-hash-manifest.txt itself>
tool_versions:
  codex_cli: <version, must match codex-cli-pin.txt range>
  codex_cli_binary_sha256: <hex; matches codex-cli-binary-sha256.txt>
  claude_code: <version>
  python: <e.g. 3.9.6>
transcript_hash: <SHA-256 of session transcript that produced this verdict>
findings: []  # List of P0/P1/P2/P3 with file:line if any
gpg_signature: <armored GPG signature of the above fields>
```

## Validator semantics

- `--parent-sha $PARENT_SHA` arg MUST equal the verdict's
  `parent_sha` (S104 redesign — replaces the unsolvable
  `commit_sha` self-reference). The release.yml step 15
  resolves PARENT_SHA via `git log -n1 --format=%H -- <verdict-file>^`.
  Mismatch → exit `VERDICT_INVALID` (3).
- `--release-tag $RELEASE_TAG` arg MUST equal the verdict's
  `release_tag` (R1 S-Sec-3 replay defense — exit non-zero on
  mismatch).
- `--max-age-hours 24`: assert `now - generated_at < ttl_hours`.
  Beyond TTL → distinct exit code `VERDICT_EXPIRED` (NOT infra
  error; release.yml routes appropriately per R1 S-QA-Unseen-2).
- `--codex-cli-pin-file`: assert `tool_versions.codex_cli` in pin
  range (R1 C5 enforcement).
- `--inputs-hash-paths-file`: read manifest + recompute
  `inputs_hash` via git hash-object + canonical_json (R1 S-Sec-4).
  Mismatch → exit non-zero.

## Phase 6 ship scope

The TEMPLATE is shipped. Per-release verdict instances are authored
by Owner BEFORE each tag push. The release.yml step 15 is wired
with `continue-on-error: true` only when
`CEO_PAIR_RAIL_VERDICT_OPTIONAL=1` (transition mode for v1.16.0-rc.1).

For v1.16.0 GA tag, `CEO_PAIR_RAIL_VERDICT_OPTIONAL` is unset →
verdict file MUST be present + valid.
