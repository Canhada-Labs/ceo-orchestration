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
delta_allowlist:  # PLAN-166 W0 — ENFORCED by tag() (_release_tag_guard.py delta) and by the release.yml fail-closed step. CLOSED set: every path allowed to differ between parent_sha and the tag commit. Literal repo-relative paths, NO glob metacharacters. MUST include this verdict file itself, the tag's verdict-fields file at the plan dir's canonical path (verdict-fields-<TAG>.md — basename elsewhere is rejected), and the re-pass evidence files of THIS tag only.
  - .claude/governance/pair-rail-verdict-<release-tag>.md
  - .claude/plans/PLAN-<NNN>/verdict-fields-<release-tag>.md
  - .claude/plans/PLAN-<NNN>/repass-<N>/<each evidence file, named one by one>
delta_manifest: <repo-relative path of the re-pass evidence MANIFEST.sha256 — the allowlist closes by CONTENT, not just by name: the guard runs `shasum -a 256 -c` on it>
delta_manifest_sha256: <64-hex sha256 OF the MANIFEST.sha256 file itself — pins the pin>
tool_versions:
  codex_cli: <version, must match codex-cli-pin.txt range>
  codex_target_triple: <targetTriple of the run that generated this verdict, e.g. aarch64-apple-darwin (ADR-182 wire-shape)>
  codex_payload_sha256: <64-hex; sha256 of the NATIVE codex payload for that triple — must equal codex-cli-pin-manifest.json payloads.<triple>.sha256. Compute via `python3 .claude/hooks/check_pair_rail.py --verify-codex-pin` (the `sha256` field). NOT the hash of `which codex` (that is the npm JS launcher).>
  # codex_cli_binary_sha256: <DEPRECATED (ADR-182) — launcher-hash pin, pre-ADR-182 tags only. The pin file is now a comment-only tombstone; do not declare this field in new verdicts.>
  claude_code: <version>
  python: <e.g. 3.9.6>
transcript_hash: <SHA-256 of session transcript that produced this verdict>
findings: []  # List of P0/P1/P2/P3 with file:line if any
gpg_signature: <armored GPG signature of the above fields>
```

## tag() guard semantics (PLAN-166 W0 — local AND server-side)

- `delta_allowlist` / `delta_manifest` / `delta_manifest_sha256` are
  REQUIRED for every new verdict (RC and stable). `tag()` refuses to
  sign when `git diff <parent_sha>..HEAD --name-only` contains any path
  outside the allowlist, when the allowlist carries a glob
  metacharacter or another tag's artifacts, when the parent_sha is not
  an ancestor of HEAD (E_PARENT_NOT_ANCESTOR=12), or when
  `shasum -a 256 -c <delta_manifest>` fails. The same asserts run
  server-side in release.yml, independent of
  CEO_PAIR_RAIL_VERDICT_OPTIONAL (fail-closed step).

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
- `--codex-pin-manifest-file`: assert
  `tool_versions.codex_payload_sha256` equals
  `payloads[tool_versions.codex_target_triple].sha256` in
  `codex-cli-pin-manifest.json` (ADR-182 payload pin). Missing
  fields, triple absent from the manifest, or sha mismatch → exit
  `VERDICT_INVALID` (3), fail-CLOSED.
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
