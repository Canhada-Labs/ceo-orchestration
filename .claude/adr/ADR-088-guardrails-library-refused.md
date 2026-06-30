# ADR-088 — Guardrails-library standalone export REFUSED — depth-over-breadth thesis

## Status

ACCEPTED — Wave A re-ceremony 2026-04-27 — round-21 sentinel — Owner key 0000000000000000000000000000000000000000

## Context

PLAN-056 Phase 1 originally proposed 2-3 dev-dias to repackage the
framework's existing 6 token-economy detectors + 6 governance hooks
+ 19 secret families + OWASP LLM output_scan patterns as a
**standalone exportable skill** named `guardrails-library`. Trigger
was Session 60 landscape audit identifying the OpenAI Agents SDK
"Guardrails primitive" as a feature in core; ceo-orchestration has
the equivalent functionality but not packaged for standalone import
by adopters who don't want the full framework.

Owner directive Session 67 (Claude-only depth-over-breadth) reframes
this as **anti-thesis**: a standalone guardrails-library invites
adopters to consume framework guardrails *without* the framework's
governance, hooks, sentinels, and protocol. That undermines the
positioning of "deepest Claude-stack governance integration".

## Why standalone export is wrong shape

The framework's 6 detectors + 6 hooks + 19 secret families are
**load-bearing because they sit inside the protocol**, not despite it:

1. **`check_agent_spawn.py`** depends on `team.md` SKILL MAP +
   `ceo-orchestration` skill being loaded — extracting this to a
   standalone consumer would require duplicating the persona +
   spawn-protocol contract.
2. **`audit_log.py`** depends on `_lib/audit_emit.py` action registry +
   HMAC chain key + canonical-paths layout — extracting this to a
   standalone consumer requires the consumer to recreate the
   `_KNOWN_ACTIONS` registry + key management.
3. **`check_canonical_edit.py`** depends on Owner-signed sentinel
   pattern + canonical paths list — meaningless outside our governance.
4. **Token-economy detectors** depend on `audit-log.jsonl` schema —
   consumer must emit compatible events.
5. **Secret families catalog** is the ONLY component that is truly
   portable as a regex library — but pip already has `detect-secrets`
   and similar tools covering this surface.
6. **OWASP LLM output_scan patterns** are likewise covered by
   external libraries (e.g. `llm-guard`).

A `guardrails-library` skill export would either:

- (a) Drop the protocol context (becoming a pile of regexes
  duplicating what already exists in OSS), OR
- (b) Carry the protocol context (requiring full framework adoption,
  defeating the purpose of standalone export).

## Decision

**REFUSE PLAN-056 Phase 1 (guardrails-library standalone export)**
with reason `(b) cost-exceeds-benefit` per refused-ADR taxonomy.

Specifically:

1. No new `guardrails-library` skill.
2. No `docs/GUARDRAILS-LIBRARY.md` adopter import guide.
3. No skill inventory entry.
4. Reaffirm framework guardrails as **first-class internal**, not
   external library.
5. Document existing guardrails in `docs/GOVERNANCE.md` (ships under
   PLAN-059 Phase 3) explaining what each does and how it interacts
   with the protocol.

## Consequences

### Positive

- 2-3 dev-dias removed from roadmap permanently.
- No skill maintenance burden (frontmatter pin, SHA verification,
  update propagation across adopter projects).
- Avoids YAGNI-shaped abstraction (export-without-consumer-request).
- Reinforces depth-over-breadth thesis (ADR-085) — framework
  guardrails are first-class IN the framework, not standalone.

### Negative

- Adopters who want detector regexes without governance must use
  external OSS (`detect-secrets`, `llm-guard`). Acceptable: they
  have those tools.
- OpenAI Agents SDK comparison column shows this gap remaining.
  Counter: the SDK guardrails are paired with their orchestration;
  ours are paired with ours. Comparison is apples-to-apples in
  context.

### Neutral

- Existing guardrails (`_lib/output_scan.py`, `_lib/secret_patterns.py`,
  `_lib/injection_patterns.py`, `audit-tokens` detectors, hooks)
  remain unchanged. They are first-class internal.

## Alternatives considered

### A. Ship guardrails-library skill as proposed (REJECTED)

See decision rationale above. Cost-vs-benefit + thesis dilution.

### B. Ship just the secret_patterns regex catalog (REJECTED)

Already covered by `detect-secrets` and similar OSS. No marginal
uplift.

### C. Document existing guardrails in GOVERNANCE.md (CHOSEN)

`docs/GOVERNANCE.md` (ships under PLAN-059 Phase 3) lists each
guardrail + its kill-switch + its interaction with the protocol.
Adopters who want guardrails adopt the framework. Adopters who want
standalone regexes use OSS.

## Enforcement commit

To be filled in at Session 67 D5 closeout (this ADR's promotion +
`docs/GOVERNANCE.md` reference land in same commit batch).

## References

- ADR-085 — Framework landscape Claude-only (this ADR is part of
  the closeout)
- PLAN-056 Phase 1 — original proposal (refused via this ADR)
- PLAN-059 Phase 3 — `docs/GOVERNANCE.md` (companion deliverable)
- `_lib/output_scan.py`, `_lib/secret_patterns.py`,
  `_lib/injection_patterns.py` — existing guardrails (internal,
  not exported)
