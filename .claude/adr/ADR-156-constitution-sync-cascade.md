# ADR-156: Constitution sync-cascade — advisory dependent-set re-verify + Sync Impact Report

**Status:** ACCEPTED (S241, 2026-06-17 — shipped + CI green in PLAN-138 Wave D)
**Date:** 2026-06-17
**Enforcement commit:** `bbe279ea` (PLAN-138 Wave D — sync-cascade hook: dependent-set re-verify + Sync Impact Report, additionalContext-only fail-open; CI green)
**Decision drivers:** the downstream-sync half of spec-kit's constitution cascade is genuinely absent; a PROTOCOL.md edit currently re-verifies nothing downstream

## Context

`github/spec-kit` (baseline pin **v0.11.0**, 2026-06-16; round-1 studied
v0.8.11) ships a *constitution cascade*: editing the constitution triggers
a Sync Impact Report that re-checks every downstream artifact the
constitution governs. PLAN-110 Wave D ported the **upstream** half — the
advisory hook `check_protocol_semver_cascade.py` warns when `PROTOCOL.md`
is edited without a paired `ADR-NNN-AMEND-M`. The **downstream** half — a
re-verification that the artifacts PROTOCOL.md governs are still
structurally present after a protocol edit — was never ported. Today a
PROTOCOL.md edit re-verifies *nothing* downstream; `docs/PROTOCOL-SEMVER.md`
documents the intended dependent-set (CLAUDE.md §Critical Rules, the
schemas, the SKILL.md) only as prose the author is trusted to honour by
hand.

This ADR closes that gap with the **minimum viable, advisory** mechanism:
a small explicit dependent-set re-verified on any PROTOCOL.md edit, surfaced
as a Sync Impact Report. It deliberately does NOT attempt spec-kit's full
numbered-Core-Principles model or any blocking enforcement.

## Decision drivers

- The downstream-sync half of the constitution cascade is genuinely absent
  (PLAN-110 ported only the upstream paired-amend warning).
- The well-behaved common case (PROTOCOL.md edited WITH a paired amend)
  currently returns a bare `{}` — it ships **no** Sync Impact Report at all,
  exactly when the author most wants the downstream cross-check.
- A drift detector must be **falsifiable** (a removed dependent must show as
  `MISSING/DRIFT`), not a tautology that always reports green.
- Governance moat: the mechanism must NOT weaken `check_canonical_edit.py`'s
  GPG gate, must NOT add a new audit action (that would require a
  kernel-override ceremony — ADR-055/S136 lesson), and must NOT introduce a
  blocking path on the Owner's signed PROTOCOL.md edit.
- A disk-sourced report is an injection surface (Codex S228 P0): rendered
  fragments must be sanitized.

## Options considered

### Option A: shell out to full `validate-governance.sh` on each PROTOCOL.md edit
Re-runs the authoritative governance suite. **Cons:** seconds-scale latency
on every protocol edit; can ERROR / non-zero exit, which a PreToolUse hook
must never propagate into a block; re-derives far more than the dependent-set;
fragile to load. Rejected — too heavy, fail-open-hostile.

### Option B: emit a new typed audit action recording the dependent-set state
Persists the cascade result to the audit chain. **Cons:** a new audit action
requires extending `_KNOWN_ACTIONS` + the SPEC under a GPG kernel-override
ceremony (S136); over-engineered for an advisory cross-check. Rejected for
this round.

### Option C: advisory in-process dependent-set probe + `additionalContext` report
Re-verify a small explicit dependent-set with targeted in-process reads
(no shell-out), render the result as a Sync Impact Report through
`additionalContext` only — booleans/counts, never echoed file text. No new
audit action; no new hook; fail-open always. **Chosen.**

## Decision

Adopt **Option C**. Widen `check_protocol_semver_cascade.py` so that on ANY
PROTOCOL.md edit it re-verifies a small, explicit dependent-set and emits a
**Sync Impact Report via `additionalContext` ONLY** — on **both** the
paired-amend path and the no-amend path (the no-amend path additionally
carries the legacy missing-amend WARN as an extra line). Properties:

- **`additionalContext`-only.** NO `permissionDecision`, ever. NO new audit
  action → NO kernel-override ceremony. The hook always exits 0.
- **fail-open ALWAYS.** A missing/binary/unreadable dependent file is
  `INDETERMINATE`, never an error; a blown deadline, a parse failure, or any
  exception degrades to today's behavior (no report).
- **Dependent-set keyed on STRUCTURAL anchors**, not byte/line counts, so
  Wave A's PLAN-SCHEMA §14 addition and legitimate renumbers do not cry
  wolf: [1] CLAUDE.md §Critical Rules present; [2] PLAN-SCHEMA.md §5
  required-body-sections heading present; [3] ceo-orchestration SKILL.md
  frontmatter valid (LINT-FM-04/05 surrogate); [4] DEBATE-SCHEMA.md present;
  [5] validate-governance.sh still references PLAN-SCHEMA. Reported as
  `PRESENT` / `MISSING/DRIFT` / `INDETERMINATE` — **falsifiable**, not a
  tautology.
- **booleans/counts only.** Matched file text is never echoed; every rendered
  fragment is sanitized to printable ASCII + length-clamped (`_sanitize_path`)
  so a dependent file with control chars cannot forge an extra report line
  (Codex S228 injection defense).
- **Kill-switch `CEO_PROTOCOL_SYNC_CASCADE=0`** suppresses the machine report
  (the legacy missing-amend WARN still ships).
- **Sub-2s deadline** (`TIME_BUDGET_S`, checked in every probe loop) +
  per-file read cap; the non-PROTOCOL hot path short-circuits with **zero**
  dependent-set file reads.

**Out of scope (explicit):** the numbered-Core-Principles refactor of
PROTOCOL.md (spec-kit models each principle as an addressable node) is NOT
adopted this round — it is a large structural rewrite with no advisory
payoff. No blocking enforcement. No signed/persisted cascade record.

## Consequences

- (+) Closes the documented-but-unverified downstream dependent-set gap; the
  paired-amend common case now ships a Sync Impact Report instead of `{}`.
- (+) Zero new escalation surface: `additionalContext`-only, fail-open,
  no new audit action, GPG gate untouched.
- (+) Cheap and bounded (sub-2s, per-file cap, zero reads on the hot path).
- (~) The dependent-set is small and hand-curated; it cross-checks structural
  presence, not semantic correctness — a present-but-wrong CLAUDE.md still
  reads `PRESENT`. This is an advisory cross-check, not a verifier.
- (~) Structural anchors can drift if a section is legitimately renamed; the
  report then reads `MISSING/DRIFT` until the anchor list is updated (a cheap
  doc edit). Booleans-only keeps the false-positive cost to a one-line nudge.
- (-) Adds ~120 lines to a previously tiny hook; mitigated by full fail-open
  coverage + a dedicated falsifiable test (PLAN-138 D.5).

## Blast radius

**L3.** Touches one governance hook (`check_protocol_semver_cascade.py`) on
the PreToolUse chain + its operator doc (`docs/PROTOCOL-SEMVER.md`) + a new
test. The hook is advisory/fail-open, so the runtime blast radius is bounded
to an `additionalContext` string; the L3 rating reflects that it sits on a
governance-critical hook and reads multiple canonical artifacts.
