# ADR-089 — PLAN-059 Phase 1 SEC-P0 cluster disposition (Session 67)

## Status

ACCEPTED — Wave A re-ceremony 2026-04-27 — round-21 sentinel — Owner key 0000000000000000000000000000000000000000

## Context

PLAN-059 Round 2 v3 (Session 61 cont, 2026-04-24) introduced 4 SEC-P0
items as security-engineer's CONDITIONAL VETO requirements. These
were tracked but unfilled until Session 67. Owner directive 27/04
(close all by 2026-05-01) requires individual disposition for each.

## Per-SEC-P0 disposition

### SEC-P0-01 — `_lib/spec_context_sanitizer.py` — SHIPPED

**Disposition:** code SHIPPED (staged at
`.claude/plans/PLAN-059/staged-code/_lib/spec_context_sanitizer.py`,
22 unit tests passing).

**Coverage:**
- NFKC normalization (12 test cases including fullwidth → ASCII)
- Control-char strip (NUL + bidi RTL + ZWJ + BOM tested)
- Sentinel violation detection (`<<<SPEC-CONTEXT-BEGIN>>>` /
  `<<<SPEC-CONTEXT-END>>>` reserved)
- Markdown header-escape advisory count
- 8 KiB byte cap with truncate semantics
- SHA-256 deterministic hash (matches downstream HMAC chain
  contract per ADR-055)
- Fail-closed-to-empty-result on any internal exception (never raises)

**Pending mega-sentinel ceremony to git mv staged-code →
canonical `.claude/hooks/_lib/spec_context_sanitizer.py`.**

### SEC-P0-02 — memory-scratchpad role allowlist + hardening — REFUSED

**Disposition:** REFUSED via this ADR with reason `(b) cost-exceeds-benefit`
per refused-ADR taxonomy (PLAN-051 §3.1).

**Reason:**
- Owner-directive deadline 2026-05-01 budget does not accommodate
  1 dev-dia for new lib + canonical-guard expansion + auto-purge
  logic + 8 acceptance tests.
- Current memory-scratchpad usage in framework dogfood (Sessions
  60-67) shows zero observed cross-role contamination incidents.
- Existing skill-level controls + Owner-signed sentinel discipline
  for canonical paths cover the dominant attack surface.
- If a real cross-role scratchpad incident emerges in adopter
  telemetry, this ADR can be reopened with empirical evidence.

**Compensating controls:**
- `_lib/spec_context_sanitizer.py` (SEC-P0-01) covers the
  cross-context payload-injection vector at the dominant surface
  (spawn prompts).
- Owner-signed canonical-edit sentinel (ADR-010 / ADR-031) covers
  canonical paths.
- Audit-log emission on every memory-scratchpad write (existing
  via memory-scratchpad skill) provides forensic trail.

### SEC-P0-03 — GOVERNANCE.md §"What CANNOT be turned off" + frozen invariants test — SHIPPING IN PHASE 3

**Disposition:** doc-side SHIPPING D4 as part of PLAN-059 Phase 3
GOVERNANCE.md deliverable.

**Scope reduction:**
- The original spec proposed a `test_frozen_invariants_env_immutable.py`
  asserting 4 invariants (VETO floor + canonical-edit + HMAC + pre-
  redaction) cannot be disabled by env vars. Empirical reality:
  `CEO_AUDIT_HMAC_DISABLE=1` DOES disable HMAC chain (already known
  in C-P0-06; covered by salt addition in Round-23). Therefore
  "HMAC frozen" is currently false; making it true requires
  removing the kill-switch (breaking change for adopters in
  emergency rollback).
- D4 GOVERNANCE.md §"What CANNOT be turned off" lists ONLY the
  invariants that ARE genuinely frozen:
  - VETO floor (ADR-052) — hardcoded in `team.md` + `inject-agent-
    context.sh` template; no env-var override
  - Canonical-edit sentinel (ADR-031 / ADR-010) — sentinel discipline
    is structural; no kill-switch (intentional)
  - Kernel-override audit emit (ADR-031 §kernel-override) — even
    when override fires, the `veto_triggered` event is emitted
    (cannot be silenced)
- Documents kill-switches that EXIST + their rollback semantics
  (`CEO_AUDIT_HMAC_DISABLE`, `CEO_MITIGATION_DISABLE`,
  `CEO_MCP_SCANNER_DISABLE`, `CEO_OUTPUT_SAFETY_MODE`, etc.)

**Deferred from spec:** the `test_frozen_invariants_env_immutable.py`
unit test. Reason: empirical state mismatch; doc-only honesty
shipped instead of test-with-known-failures.

### SEC-P0-04 — `/audit-tokens` SessionEnd content-ban — DONE

**Disposition:** DONE (PLAN-060 Phase B, Session 62 cont, commit 54f8d74).

- `_AUDIT_TOKENS_ALLOWLIST` enforced via `scrub_audit_tokens_event()`
- 3 emitters (`audit_tokens_emitted`, `audit_tokens_timeout`,
  `audit_tokens_key_dropped`) registered in `_KNOWN_ACTIONS`
- 50ms wall budget at SessionEnd hook with timeout fallback
- 24 unit tests passing (Session 62 cont)
- Schema rows added to `SPEC/v1/audit-log.schema.md` (Session 67
  D1 drift cleanup commit `d077ce3`)

No further action.

## Bundled disposition matrix

| SEC-P0 | Disposition | Artifact |
|---|---|---|
| 01 spec-context sanitizer | **SHIPPED** | `_lib/spec_context_sanitizer.py` + 22 tests (pending mega-sentinel) |
| 02 memory-scratchpad allowlist | **REFUSED** (b) | this ADR |
| 03 frozen invariants doc | **SHIPPING in Phase 3 D4** | `docs/GOVERNANCE.md` |
| 04 audit-tokens content-ban | **DONE** (PLAN-060 Phase B) | commit 54f8d74 |

Net: **2 of 4 closed via code (01 + 04); 1 of 4 closed via doc (03);
1 of 4 refused via ADR (02)**. Refused-ADR cap (≤2/5) preserved
within PLAN-059 sprint budget per PLAN-051 §3.1.

## Consequences

### Positive

- 4 of 4 SEC-P0 items have explicit final disposition. No "TBD"
  outstanding before deadline.
- Refused-ADR taxonomy reason cited (cost-vs-benefit) with concrete
  compensating controls listed.
- D5 closeout v1.11.0 GA tag is unblocked from SEC-P0 cluster.

### Negative

- Memory-scratchpad cross-role attack surface remains as documented
  hypothetical. Empirical telemetry is absent today; this ADR can
  be reopened.
- Frozen-invariants test is doc-only; no machine-checkable assertion
  that VETO floor / canonical-edit / kernel-override emit are
  unconditionally on. Operators must read GOVERNANCE.md.

### Neutral

- SEC-P0-01 sanitizer ships as standalone library. Integration into
  `inject-agent-context.sh` Format B reference mode is Phase 2 of
  this ADR (not blocking D5 closeout).

## Alternatives considered

### A. Ship all 4 SEC-P0 in full per Round-2 spec (REJECTED)

Estimated 3-4 dev-dias. Rejected: deadline override; Owner directive
takes precedence over original Round-2 timeline.

### B. Refuse all 4 SEC-P0 via ADR (REJECTED)

Would push PLAN-059 Phase 1 closure to "all-refused". Rejected:
SEC-P0-01 sanitizer is genuinely shippable in 1 dev-dia + tests
(staged 22 passing); refusing it leaves the dominant attack surface
(spawn prompt context injection) un-mitigated. Refusing SEC-P0-04
would invalidate work already shipped (PLAN-060 Phase B). Both
unacceptable.

### C. Ship 1 + refuse 3 (REJECTED)

Refusing SEC-P0-04 doesn't make sense (already DONE). Refusing
SEC-P0-03 would skip the GOVERNANCE.md doc which is the closeout
artifact (PLAN-059 Phase 3 D4 deliverable). Hybrid 2-shipped /
1-doc-only / 1-refused is the cleanest disposition.

## Enforcement commit

To be filled in at Session 67 D5 closeout (this ADR's promotion +
sanitizer canonical promotion + GOVERNANCE.md land in mega-sentinel
ceremony commit batch).

## References

- PLAN-059 v3 (post Round-2) — sec-cluster origin
- ADR-085 — Framework landscape Claude-only (context for Phase 1
  scope reduction)
- PLAN-051 §3.1 — Refused-ADR taxonomy (reason `b` used)
- ADR-082 — L7c default-on (sister Session 67 deliverable)
- `_lib/spec_context_sanitizer.py` (staged) + 22 tests
- `docs/GOVERNANCE.md` — D4 Phase 3 deliverable (ships frozen
  invariants doc-side per SEC-P0-03 scope reduction)
