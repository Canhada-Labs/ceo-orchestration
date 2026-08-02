# Pair-Rail Verdict — v1.2.0 GA

```yaml
verdict: GO
generated_at: 2026-08-02T15:00:41Z
ttl_hours: 24
parent_sha: fc22242344e50e93340b2bcfccda087ee014ee1c
release_tag: v1.2.0
inputs_hash: 4cac9ac85ae02d246d5ab9c45d26aa5fdf3474008636e1001fd33a75f06e6d70
inputs_hash_paths_manifest_sha: b3ab0242a6ff4e12fdf2fd90c47cbc23649ab07226340c8b7aacbb0f9cc093e0
tool_versions:
  codex_cli: 0.144.6
  codex_target_triple: aarch64-apple-darwin
  codex_payload_sha256: 80a3933d11a9d13ef806aa24f7bb8afc9169cfe4e9b09d6da6a92922cbde9cff
  claude_code: claude-fable-5
  python: 3.9.6
transcript_hash: ac717ccf0d862d8a3a10f04857193a6a5fd21875934357a1687f72300bc735af
findings: [RC3-F7-upgrade-backup-P2-open, GA-F3-npm-readme-staging-P2-open]
gpg_signature: base64:LS0tLS1CRUdJTiBQR1AgU0lHTkFUVVJFLS0tLS0KCmlKRUVBQllLQURrV0lRU3VteU52MnZCR0tIUUdER3ZQejZ6d0F6WGNkQVVDYW05Ym1oc1VnQUFBQUFBRUFBNXQKWVc1MU1pd3lMalVyTVM0eE1pd3dMRE1BQ2drUXo4K3M4QU0xM0hTbmpRRUF2MW41VmM5bW4vMGo1V2k5UDgzcApTSXBLc1JEVDNJTVVRcGtrMCt4L1ZSWUJBSitlQXFqM2FzSmdPZXo1R1J6dFNnSzk0UUlpZGV5cGVqRlRNZmNtCkQrVUQKPVdkcG4KLS0tLS1FTkQgUEdQIFNJR05BVFVSRS0tLS0tCg==
```

## Signature verification recipe

base64 -d of the value after `base64:` → detached .asc; verify against
`.claude/plans/PLAN-163/ga/verdict-fields-v1.2.0.txt` (committed
alongside). Signer AE9B236FDAF0462874060C6BCFCFACF00335DC74.

<!-- VERDICT: GO -->
## Review record — pair-rail GA re-pass (advisory input to this verdict)

- **Reviewer:** codex-cli 0.144.6 (`codex exec --sandbox read-only`, prompt
  piped through the ADR-114 redactor as ONE pipeline; native payload sha
  verified against `.claude/governance/codex-cli-pin-manifest.json`
  (ADR-182) before invocation — `80a3933d…` exact match,
  aarch64-apple-darwin).
- **Date:** 2026-08-02 (S288).
- **Input scope:** release-mechanics surfaces as the v1.1.0..HEAD unified
  diff (VERSION, npm/package.json + npm/README.md, pyproject.toml,
  CHANGELOG.md, INSTALL.md, docs/ARCHITECTURE.md, README.md, SECURITY.md,
  VERSIONING.md, SBOM.md, release.yml, npm-publish.yml,
  install/upgrade/build-plugin scripts, .claude-plugin manifests,
  SPEC/v1/npm-shim.md). Root README.md is NEW in scope vs the rc.3
  re-pass — it is what npm staging actually publishes (see GA-F3).
- **Advisory only** — decision is the CEO's; the Owner authorizes via the
  GPG-signed envelope above. Train context: rc.3 shipped FULL GREEN on
  2026-07-31 with verdict GO and one open P2 (RC3-F7); the post-RC delta
  reviewed here is the rc.3 verdict-landing commit plus the two GA
  documentation-fix commits produced by this re-pass itself.

## Round 1 (verbatim) — 13/16 APPROVE, 3 REJECT, OVERALL NO-GO

Full verbatim output in the committed transcript
(`.claude/plans/PLAN-163/ga/verdict-transcripts-v1.2.0.txt`,
sha256 = `transcript_hash` above). Finding disposition after first-hand
verification (C4: claims, not reports — every finding re-checked against
the tree before acting):

| # | Sev | File | Verified? | Disposition |
|---|-----|------|-----------|-------------|
| GA-F1 | P2 | README.md:3 | CONFIRMED — last-reviewed marker read `2026-06-22 v1.0.0`, two MINORs stale, and root README is what npm staging publishes | Fixed `1241e93` — full content re-read, every count claim verified live (166 skills; 57/46/48 hooks; 68 _lib; 26 commands; 184 ADRs; SPEC 32/28); stale test figures corrected (~12,000 → ~13,000; live 13,462, FLOOR); re-stamped `2026-08-02 v1.2.0`. Re-approved R3 (after GA-F4 fold) |
| GA-F2 | P2 | docs/ARCHITECTURE.md:76,84 | CONFIRMED — hook-gap prose said 53/44 vs 57 on disk / 46 wired; test prose said ~660 files vs 729 tracked | Fixed `1241e93` (57/46 + ~720/~13k; adjacent table was already correct). Re-approved R2 |
| GA-F3 | P2 | .github/workflows/npm-publish.yml:163 | CONFIRMED — the GA staging loop rsyncs root `README.md` into `npm/`, overwriting the reviewed `npm/README.md` before packing (v1.1.0 published under the identical behavior) | **OPEN** — canonical-guarded workflow path; carried in `findings:` with a named remediation: the next Owner sentinel ceremony fixes GA-F3 together with RC3-F7. Content risk neutralized for this GA by the GA-F1 re-stamp (what ships is now freshly reviewed). Carry-open disposition ACCEPTED by codex R2 |

## Round 2 (verbatim) — fold re-review, 1 new REJECT, OVERALL NO-GO

docs/ARCHITECTURE.md APPROVE; GA-F3 carry-open disposition ACCEPT;
README.md REJECT with a NEW finding the marker-focused Round 1 missed:

| # | Sev | File | Verified? | Disposition |
|---|-----|------|-----------|-------------|
| GA-F4 | P2 | README.md:148 | CONFIRMED — prose said "run under two harnesses" while the section documents three (claude, codex, grok) | Fixed `fc22242`. Re-approved R3 |

## Round 3 (verbatim) — fold re-review, OVERALL GO

```text
FILE: README.md - APPROVE - GA-F4 is resolved: the prose now correctly matches the three documented harnesses.
OVERALL: GO - The scoped Round 3 remediation is complete with no remaining finding.
```

## Net result

R1: 3 REJECTs, all verified first-hand; GA-F1/GA-F2 fixed and
re-approved, GA-F4 (found by the R2 fold) fixed and re-approved R3,
GA-F3 carried OPEN as a P2 with a named remediation path and an
explicit codex ACCEPT of the carry. Release mechanics: 16/16 surfaces
APPROVE or dispositioned → **GO** with two open non-blocking findings
(RC3-F7, GA-F3) headed to the same sentinel ceremony.

<!-- FINDINGS-YAML
findings:
  - id: RC3-F7
    severity: P2
    path: scripts/upgrade.sh:1776
    claim: settings backup failure is suppressed (cp 2>/dev/null || true) while "BACKED UP" prints unconditionally
    disposition: open-deferred (canonical-guarded; next sentinel ceremony)
  - id: GA-F3
    severity: P2
    path: .github/workflows/npm-publish.yml:163
    claim: GA staging rsync overwrites the reviewed npm/README.md with root README.md before packing
    disposition: open-deferred (canonical-guarded; next sentinel ceremony, paired with RC3-F7)
FINDINGS-YAML -->
