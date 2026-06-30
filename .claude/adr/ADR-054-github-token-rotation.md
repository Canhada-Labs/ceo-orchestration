# ADR-054: GitHub Token Rotation Cadence

**Status:** ACCEPTED
**Date:** 2026-04-18 (PLAN-025 Batch G)
**Deciders:** CEO, DevOps & Platform Engineer, Principal Security
**Blast radius:** L2 (procedural; no code change)
**Supersedes:** none
**Superseded by:** none

## Context

The framework uses GitHub tokens in 4 contexts:

1. **`GITHUB_TOKEN`** (workflow-scoped): automatic per-workflow token
   provided by GitHub Actions. No rotation needed; scoped + ephemeral.

2. **`ANTHROPIC_API_KEY`** (repo secret): Claude API credential used
   by `adapter-live.yml` + any dogfooding session. Rotation tracked
   in `docs/rotation-log.md` (shared secret in org secret vault).

3. **Personal Access Tokens (PATs)** — used by Owner for local dev +
   CI access when `gh` CLI operates against the repo. These are
   long-lived by default and need explicit rotation.

4. **NPM publish token** (OIDC-provenanced, workflow-scoped):
   `npm-publish.yml` exchanges GitHub OIDC for a short-lived NPM
   token. No long-lived secret stored.

PLAN-024 F-wf-001 flagged that the framework documents SHA-pinned
actions + fork-safe triggers + least-privilege permissions, but had
no explicit policy for GitHub PAT rotation. SOC2 auditors and
adopter operators both need a documented cadence to audit against.

## Decision drivers

1. **GitHub's own recommendation** — rotate PATs at least every 90
   days; fine-grained tokens with explicit expiration are preferred
   over classic PATs.
2. **Adopter audit readiness** — SOC2 Type II + ISO 27001 both
   expect a documented rotation cadence with evidence of execution.
3. **Dogfood reality** — the framework Owner uses `gh` daily via a
   classic PAT; forcing overly-short rotation creates friction that
   leads to rotation-skipping.
4. **Blast radius** — a leaked PAT has write access to the repo;
   the `CEO_SOTA_DISABLE=1` + CODEOWNERS chain limits damage but
   doesn't revoke write access. Rotation + token-scoping are
   complementary.

## Decision

**Adopt the following rotation schedule:**

| Token class | Cadence | Target scope | Evidence |
|-------------|---------|--------------|----------|
| Fine-grained PAT (preferred) | 90 days | repo-only, Contents:read, Actions:read/write | `docs/rotation-log.md` entry per rotation |
| Classic PAT (legacy) | 60 days | `repo` + `workflow` | `docs/rotation-log.md` entry per rotation |
| `ANTHROPIC_API_KEY` | 90 days | API-key vault only | `docs/rotation-log.md` §ANTHROPIC |
| `GITHUB_TOKEN` | N/A (auto per-run) | workflow-scoped | GitHub Actions log |
| NPM publish (OIDC) | N/A (exchanged per-run) | workflow-scoped | `npm-publish.yml` provenance |

**Key procedural rules:**

- Every rotation writes a one-line entry to `docs/rotation-log.md` with:
  date (UTC ISO-8601), token class, old-fingerprint (last 4 chars),
  new-fingerprint (last 4 chars), rotator handle.
- The old token is REVOKED within 24h of the new one taking effect.
- On rotation-skip (365 days without rotation): the Owner reviews
  and either rotates or documents a justified exception in the
  rotation log under `### Known-long-lived`.
- Fine-grained PATs are PREFERRED over classic PATs. New tokens MUST
  be fine-grained unless a workflow requires classic-PAT scopes.

## Consequences

### Positive (+)

- Explicit cadence that adopter auditors can verify.
- Rotation-log entries enable forensic reconstruction of "which
  token signed commit X" post-incident.
- Fine-grained preference narrows blast radius per-token.

### Negative (−)

- 60-90 day rotation cadence adds ~5-10 min of Owner overhead per
  quarter. Acceptable for a one-Owner project.
- Rotation-log is markdown, not a signed ledger; a Tier-2 insider
  with repo write could falsify entries. Documented as residual per
  threat-model §RR-1.

### Neutral (~)

- No code change. Pure procedural/policy documentation.
- Existing `docs/rotation-log.md` format unchanged.

## Revisit trigger

- First rotation-skip incident reveals the cadence is unrealistic
- SOC2 Type II auditor requests tighter cadence (e.g. 30 days)
- GitHub deprecates classic PATs entirely

## References

- `docs/rotation-log.md` — rotation history (append-only)
- `SECURITY.md` §Known residuals — token rotation policy link
- `docs/threat-model.md` §RR-1 — workstation compromise scenario
- PLAN-024 F-wf-001 — originating finding
- `.github/workflows/shadow-ci.yml` — token-rotation-aware workflow

## Enforcement commit

`1ae10b63b783` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
