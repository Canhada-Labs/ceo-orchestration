# ADR-019-AMEND-1: Confidence-gate per-class block-mode lifecycle

**Status:** ACCEPTED
**Accepted:** 2026-05-18
**Date:** 2026-05-18
**Plan:** PLAN-100 v1.34.0
**Amends:** ADR-019
**amended_by:** ADR-019-AMEND-2 (CLASS-SHA_EXISTS promote to HIGH_CONFIDENCE_BLOCK, 2026-05-18)
**Related:** ADR-018, ADR-124, ADR-125, ADR-095

## Context

ADR-019 introduced the 3-state confidence-gate lifecycle gated by broad
`CEO_CONFIDENCE_ENFORCE=1` env var. Enforcement granularity was left
unspecified.

PLAN-100 Wave 0.5 baseline (synthesized 2026-05-18) measured per-class
characteristics:

| Class | N | Severity | Verifier-fail rate (empirical) |
|---|---|---|---|
| `sha_exists` | 200 | critical | 5% (intentional fakes only) |
| `path_exists` | 200 | info | 5% (intentional fakes only) |
| `function_exists` | 195 | warn | 17.9% (AST coverage gaps) |
| `line_range` | 200 | info | 5% |
| `import_resolves` | 195 | warn | 100% (stdlib not in repo) |
| `test_passes` | 200 | critical | 87.5% (pytest env-flaky) |

Broad enforcement is empirically unworkable: `test_passes` would
generate ~87% false blocks while `sha_exists` would block only on
genuine FPs.

## Decision

### 1. Per-class enforcement granularity

`CEO_CONFIDENCE_ENFORCE=1` applies ONLY to HIGH_CONFIDENCE_BLOCK
classes per `.claude/data/confidence-gate-class-tiers.json`.

### 2. Class-tier config file

JSON at `.claude/data/confidence-gate-class-tiers.json`, fail-OPEN on
missing/malformed.

### 3. Per-class kill-switch

`CEO_CONFIDENCE_BLOCK_<CLASS>=0` EXACT match. No prefix matching.

`CEO_CONFIDENCE_BLOCK=0` (no `_<CLASS>` suffix) — IGNORED.

Implementation reads `os.environ.get(f"CEO_CONFIDENCE_BLOCK_{cls.upper()}", "")`
and treats `"0"`, `"false"`, `"no"`, `""` (absent) as off-signal.

### 4. Initial v1.34.0 tier assignment

- HIGH_CONFIDENCE_BLOCK: `sha_exists`
- MED_CONFIDENCE_ADVISORY: `path_exists`, `function_exists`,
  `line_range`, `import_resolves`
- LOW_CONFIDENCE_ADVISORY: `test_passes`

### 5. Legacy flag interaction

`CEO_CONFIDENCE_ENFORCE=1` post-amendment triggers block on
`sha_exists` failures only.

### 6. Drift detector

`confidence_gate_fp_drift_detected` emits when 7-day rolling FPR > 2%
for any HIGH_CONFIDENCE_BLOCK class. Auto-demote after 24h cooling.
Owner overrides via re-sentinel
`.claude/data/confidence-gate-drift-override-<CLASS>.asc`.

### 7. Per-class promotion ceremony

Future promotions: a subsequent ADR-019-AMEND-N-CLASS-<X>.md (the
first realized promotion is ADR-019-AMEND-2-CLASS-SHA_EXISTS) + Owner
GPG sentinel `.claude/data/confidence-gate-class-promote-<CLASS>.asc`
+ tier-config JSON edit + plan-flip or bundled ship.

### 8. Calendar-gate retraction (S139 2026-05-18)

Original "30 consecutive days at <1% FPR" retracted per ADR-095.
Substantive criterion: N >= 200 events per class AND measured
FPR < 1%.

### 9. Failure modes + reversal

- tier-config JSON missing/malformed: fail-OPEN, all advisory
- HIGH_CONFIDENCE_BLOCK class flakes: drift detector fires, auto-demote
- legitimate spawn blocked: `CEO_CONFIDENCE_BYPASS=1` for unblock

Byte-identical reversal: remove tier-config JSON.

## Consequences

Per-class observability via `confidence_gate_blocked` emit; per-class
kill-switch hygiene; drift-detector auto-demotion; future promotions
extensible via the ADR-019-AMEND-N-CLASS-<X> pattern.

Tradeoffs: tier-config JSON is one more canonical artifact; env grammar
adds cognitive load; drift-detector may briefly auto-demote healthy
classes.


## Codex MCP gate trail

Codex R2 3-iter ACCEPT trail (PLAN-100 promotion ceremony, S140, thread `019e3c8c-cb5f-7132-af79-87799903f55b`, gpt-5.2):

- This ADR R2 iter-1 (S140, gpt-5.2): ACCEPT-WITH-FIXES — 3 P0 + 2 P1 + 1 P2 findings folded inline:
  (P0 #1) placeholder guardrails added — ceremony Phase A hard-fails if Codex review marker strings (thread-ID slot + iter-verdict template) remain unsubstituted in approved.md; Phase C post-apply re-scans the canonical ADRs to catch any unsubstituted markers that survived the apply step;
  (P0 #2) commit signing pinned to OWNER fingerprint via `git commit -S$OWNER_GPG_FPR` (the `-S<fingerprint>` flag fails non-zero if Owner key is unavailable, caught by `set -euo pipefail`) + post-commit `git verify-commit HEAD` exit-status check + `git log --format='%G?'` good-signature flag (S135/S136 lessons; full 40-char fingerprint grep avoided because `git log --show-signature` commonly displays only the 16-char keyid — would false-fail correctly-signed commits);
  (P0 #3) ADR-019-AMEND-2-CLASS-SHA_EXISTS (renamed from AMEND-1 per PLAN-113 W2 chain-collision fix) body cites ship tag `v1.34.0` alongside commit SHA in §Authority;
  (P1 #1) Co-Authored-By: Claude Opus 4.7 retained — Claude is the orchestrator+executor of this ceremony; Codex MCP is gate-review only (precedent: S133 ADR-132 promotion commit attributed identically);
  (P1 #2) per-class ADR drift-detector wording softened — `check-confidence-gate-drift.py` emits `confidence_gate_fp_drift_detected` with `auto_demote_at` timestamp; downstream operator/runner performs actual tier-config demotion when wired;
  (P2 #1) `sandbox-sim.py` docstring trimmed — clarifies that the out-of-band bash-execute against /tmp clone (S132 lesson) runs outside both this python file and the ceremony preflight.
- This ADR R2 iter-2 (S140, gpt-5.2): ACCEPT-WITH-FIXES — 1 P0 folded:
  (P0) post-commit GPG verify was brittle — grepping full 40-char fingerprint on `git verify-commit` + `git log --show-signature` outputs would false-fail correctly-signed commits because those outputs commonly carry only a 16-char keyid. Replaced with `git verify-commit HEAD` exit-status check + `git log --format='%G?'` flag check (`G` = good signature with known key; `U` = good signature with unknown validity — both accepted; trust comes from `-S<fingerprint>` having succeeded earlier in the same Phase D).
- This ADR R2 iter-3 (S140, gpt-5.2): ACCEPT — 1 P2 cleanup only:
  (P2) comment drift in Phase D about `%G?` — comment said "returns 'G' for good signature with known key" but check explicitly accepts `'G'` OR `'U'`; comment aligned with check.
- This ADR R2 final: **ACCEPT** — disk cross-check verified all P0/P1/P2 findings resolved; promotion safe.

## Authority

- ADR-019 (granularity decision deferred to amendment)
- ADR-124 §Part 2 (amendments to existing ADRs in scope)
- ADR-125 §B (conditional default-ON Tier-B)
- ADR-095 (calendar-gate retraction)
- PLAN-100 v1.34.0
