# ADR-100 — `trustedDependencies` allowlist re-affirm — SP-NNN sign chain documents the same discipline

**Status:** ACCEPTED
**Date:** 2026-05-02
**Enforcement commit:** n/a (documentation-only)
**Decision drivers:**
- External validation (helmor adopts allowlist-by-default) corroborates the SP-NNN approach
- Adopters reading the framework should see "supply-chain hygiene is a documented decision, not an emergent property"
- ADR-085 (Claude-only landscape) + ADR-051 (SKILL REFERENCE Format B) + this ADR-100 form the supply-chain narrative
- Pattern strength deserves explicit record: ADR-051 sign chain = trusted-dependencies analogue for skill content

## Context

Helmor analysis 2026-05-02 (PLAN-068 lesson L6) surfaced bun's
`trustedDependencies` allowlist as a supply-chain hygiene primitive:
helmor's `package.json` declares an explicit allowlist of dependencies
permitted to run install scripts; everything else is denied by default.
This is the strict-mode-with-allowlist posture for npm install
hooks — a meaningful improvement over the npm default that
runs install scripts for every transitive dep.

ceo-orchestration's existing **SP-NNN sign chain** is the structural
equivalent already in place since PLAN-020 ADR-051. Each imported
skill or canonical edit requires an Owner-physical GPG sentinel
signing a round-N approval document covering the canonical paths
touched. The sentinel format is `architect/round-N/approved.md.asc`
(see PLAN-044 Wave A+B+C ceremonies for shipped examples). Skill
patches landing through `/skill-review` are gated by SP-NNN approval
documents at `.claude/plans/PLAN-NNN/architect/round-N/approved.md`.

The discipline is allowlist-by-default: a canonical edit (skill,
hook, settings.json, plan body, ADR canonical promotion) is rejected
by `check_canonical_edit.py` unless the corresponding sentinel
exists and signs the path. Skill imports specifically run through the
SP-NNN curated import pipeline (ADR-060) — the framework refuses to
import unsigned skill content.

This is functionally identical to bun's `trustedDependencies`
posture: the framework refuses to consume skill content (and
canonical edits) unless explicitly allowlisted by Owner-physical
signature. ADR-100 documents the equivalence.

ZERO code change. ZERO new file beyond this ADR. The runtime
mechanism already exists (ADR-051 + ADR-060); this ADR provides the
supply-chain framing as a citable record for adopters and auditors.

## Decision drivers

- **External validation strengthens credibility.** Helmor's adoption of
  `trustedDependencies` shows the allowlist-by-default pattern has
  cross-ecosystem traction. ceo-orchestration's SP-NNN chain pre-dates
  this with the same posture; the ADR records the convergence.
- **Auditor / adopter discoverability.** Reading ADR-051 alone teaches
  the SKILL REFERENCE Format B mechanism but does not frame it as
  supply-chain hygiene. ADR-085 frames the Claude-only thesis but
  does not isolate the supply-chain dimension. ADR-100 fills the
  framing gap.
- **Cross-model auditor reference.** Per ADR-095 gate #6 (outside
  reviewer) + the Codex re-pass discipline (ADR-095 + Session 75
  closure pattern), cross-model auditors benefit from explicit
  supply-chain decision records over implicit-from-code reading.
- **ADR-093 60-day moratorium NA.** ADR-100 is documentation-only —
  not a refusal, not a new default, not a workflow change. PLAN-068
  §0.4 R11 confirms the moratorium does not apply.

## Options considered

### Option A — Adopt bun-style `trustedDependencies` JSON config (REJECTED)

Add a `trustedDependencies` allowlist to a Node `package.json` at
repo root.

- Pros: literal pattern reuse; tooling-supported.
- Cons: no Node/bun runtime in the framework (ADR-085 Claude-only
  thesis + PLAN-068 §0.4 R1 stdlib-only). Introducing one solely for
  config metadata contradicts the depth-over-breadth posture.

**Rejected** — wrong runtime ecosystem.

### Option B — Document existing SP-NNN as the equivalent (CHOSEN — docs ADR only)

Author this ADR-100 cross-referencing helmor as external precedent;
document SP-NNN sign chain as the allowlist-by-default discipline;
ZERO code change.

- Pros: leverages existing runtime mechanism; closes lesson L6 of
  helmor analysis as "already-implemented; precedent confirmed";
  ~50-120 LoC of doc only; PLAN-068 §0.4 R11 satisfied (ADDITIVE
  not new default).
- Cons: requires reader to follow cross-references to ADR-051 + ADR-060
  to reach the runtime artifact. Mitigated by explicit cross-ref
  list in §Cross-references.

**Chosen.**

### Option C — Migrate SP-NNN to a different signing scheme (REJECTED)

Replace the GPG-sentinel approval-document pattern with a JSON
allowlist or sigstore-based signing.

- Pros: closer to bun's mechanism in form.
- Cons: out of scope for PLAN-068; existing SP-NNN scheme works
  (8 GPG ceremonies in PLAN-044 Wave A+B+C alone, ADR-051 + ADR-060
  ACCEPTED, no observed failure mode). The discipline is not the
  bottleneck.

**Rejected** — premature migration of working mechanism.

### Option D — Skip the ADR; rely on ADR-051 alone (REJECTED)

ADR-051 already documents SKILL REFERENCE Format B + sign chain.
Could argue ADR-100 is redundant.

- Pros: zero new ADR-numbered slot consumed.
- Cons: ADR-051 is about REFERENCE FORMAT (Format B vs Format A
  expanded-trust-boundary); supply-chain framing is a distinct
  audience concern (auditors + adopters reading for hygiene posture,
  not API format). Cross-reference to helmor as external precedent
  also deserves its own record. Three separate ADRs (051 + 060 + 100)
  composing the supply-chain narrative is the cleaner factoring.

**Rejected** — framing is load-bearing for auditor discoverability.

## Decision

**Option B.** Document the existing SP-NNN sign chain (Owner-physical
GPG sentinels per `architect/round-N/approved.md.asc` covering
canonical paths) as ceo-orchestration's allowlist-by-default discipline
equivalent to helmor's `trustedDependencies`. Cross-reference helmor as
external precedent for the pattern.

The runtime mechanism is unchanged:

- `check_canonical_edit.py` (PreToolUse hook) — denies canonical edits
  to Gate-1 paths + ADR/plan canonical paths absent a matching sentinel
- `check_skill_patch_sentinel.py` (PostToolUse hook) — denies skill
  imports absent SP-NNN sentinel approval (ADR-060)
- `architect/round-N/approved.md` — the approval document; `.asc`
  detached signature carries the Owner GPG signature
- Owner key fingerprint `0000000000000000000000000000000000000000`

ZERO code change. ZERO new file beyond this ADR. The ADR is purely
narrative-documentary — it provides the supply-chain framing for an
existing runtime artifact.

## Consequences

**Positive (+):**
- Adopters and auditors find the supply-chain decision documented
  alongside ADR-051 + ADR-060 — the framework's hygiene posture is a
  citable record, not an inferred property.
- Cross-model auditors (per ADR-095 gate #6 + Codex re-pass discipline)
  have explicit reference for the discipline; reduces audit time spent
  reverse-engineering the intent of SP-NNN.
- External precedent (helmor's `trustedDependencies`) strengthens
  the pattern's credibility — convergent adoption across ecosystems
  signals the posture is non-idiosyncratic.
- Closes PLAN-068 lesson L6 ("re-affirm via ADR") with the minimum
  artifact required (~120 LoC, single ADR).

**Negative (-):**
- One additional ADR slot consumed (ADR-100); index gets a marginal
  entry. Mitigated by the slot being inexpensive and the cross-link
  value tangible.

**Neutral (~):**
- No runtime impact; documentation-only.
- ADR-051 remains the runtime artifact for SKILL REFERENCE Format B;
  ADR-060 remains the runtime artifact for the curated skill import
  pipeline; ADR-100 documents the supply-chain framing that subsumes
  both.

## Blast radius

**L1** — single ADR file; documentation-only. No runtime hooks, no
script changes, no workflow changes, no convention changes. The only
on-disk artifact is this ADR plus its index entry in `.claude/adr/README.md`
auto-generated index (regenerated by `generate-adr-index.py`).

## Compliance checklist

| Item | Verification |
|---|---|
| ADR file lands at canonical `.claude/adr/ADR-100-trusted-dependencies-re-affirm.md` | post-ceremony commit |
| Status is ACCEPTED post-ceremony | `grep "^**Status:** ACCEPTED" .claude/adr/ADR-100-*.md` |
| Enforcement commit field literally `n/a (documentation-only)` | grep field value |
| Cross-references to ADR-051 + ADR-060 + ADR-085 present | grep `ADR-051\|ADR-060\|ADR-085` in §Cross-references |
| Helmor external precedent cited | grep `helmor` in body |
| ADR-093 moratorium not violated | this ADR is documentation-only ADDITIVE; not a refusal |
| `.claude/adr/README.md` index regenerated | `generate-adr-index.py --write` post-ceremony |
| Zero code change | git diff post-ceremony shows only ADR + index regeneration |

## Cross-references

- PLAN-068 §11.2.2 (Track-1 scope — trustedDeps re-affirm docs ADR)
- PLAN-068 §0.4 R11 (moratorium NA for ADDITIVE conventions)
- ADR-051 — SKILL REFERENCE expanded trust boundary (the runtime
  artifact: Format B + SHA-256 binding + sign chain)
- ADR-060 — Curated skill import pipeline (SP-NNN chain — the
  per-skill allowlist primitive)
- ADR-085 — Framework landscape Claude-only positioning (basis for
  why the framework owns its own allowlist mechanism instead of
  importing one from another ecosystem)
- ADR-053 — Sentinel HMAC deferred (companion supply-chain decision —
  SHA-256 + CODEOWNERS sufficient under current threat model)
- Helmor `package.json#trustedDependencies` (external precedent for
  the allowlist-by-default discipline)
- Helmor analysis 2026-05-02 (lesson L6 — origin of the cross-reference)
