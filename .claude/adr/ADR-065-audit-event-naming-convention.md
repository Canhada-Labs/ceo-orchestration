---
id: ADR-065
title: Audit-event naming convention — `<surface>_<verb>[_modifier]` freeze
status: ACCEPTED
date: 2026-04-20
proposed_date: 2026-04-20
accepted_date: 2026-04-21
deciders: CEO + Owner
related_plans: [PLAN-045, PLAN-044]
related_adrs: [ADR-005, ADR-007, ADR-056, ADR-062, ADR-063, ADR-064]
blast_radius: L2-narrow
---

# ADR-065 — Audit-event naming convention

## Context

PLAN-044 finding F-07-08 surfaced an asymmetry in tier-policy event
names. Eight of nine `tier_policy_*` actions follow a
`<surface>_<verb>` pattern (e.g. `tier_policy_derived`,
`tier_policy_promote_applied`, `tier_policy_demote_requested`). One
entry, `tier_policy_promote_cost_gated`, reads as a parallel of
`promote_applied` — as if a "cost-gated" promote variant executed —
when the actual semantics are "promote rejected by the cost gate".

The finding recommends either renaming the outlier (SemVer-MINOR bump
+ kernel batch + backward-compat alias) or freezing the corpus as-is
with a naming-convention ADR.

Inspection of the full `_KNOWN_ACTIONS` registry (63 actions across
11 subsystems) shows that every name already decomposes into a
`surface_verb_modifier` triplet. Adopter-facing confusion from the
single outlier is low (log-diffing doesn't depend on name shape and
SPEC row defines semantics explicitly). The cost of renaming is
non-trivial: every consumer that filters on `action ==
"tier_policy_promote_cost_gated"` breaks silently on a rename, unless
an alias table is maintained indefinitely.

## Decision

**Freeze the current 63-action corpus as-is.** Codify the
`<surface>_<verb>[_modifier]` pattern as the naming rule for every
new action, starting from `event_schema` v2.11. The outlier
`tier_policy_promote_cost_gated` is kept verbatim with an inline
comment documenting the reading ambiguity.

Naming rule, applied to new actions only:

```
<surface>_<verb>[_<modifier>]

- surface:  subsystem slug (rag, tier_policy, tournament, session, skill_reference, ...)
- verb:     past-tense action (rejected, applied, triggered, complete, read, written, queried, ...)
- modifier: optional qualifier (cost_gated, mismatch, stale, never, ...)

Underscores separate parts; no camelCase; no double underscores.
```

Existing outliers are grandfathered. A new action that would need
renaming an existing one is a NO; pick a distinct name instead.

## Consequences

### Positive

- Zero backward-incompat risk: 63 existing names unchanged.
- SemVer-MINOR additions stay additive (ADR-007 contract preserved).
- Low-cost governance: one `check-audit-action-name-convention.py`
  advisory script enforces the rule on additions to `_KNOWN_ACTIONS`
  via a diff-only linter in CI (advisory in v1; MUST-pass in v2).

### Negative

- Documented inconsistency: the single outlier
  `tier_policy_promote_cost_gated` remains. Mitigated by an inline
  comment at the registry entry + the v2.9 SPEC table row
  documenting the actual semantics.
- A future rename would still require the full kernel-batch +
  backward-compat-alias migration dance. Freezing now trades short-
  term pragmatism for a deferred cost if a v2.x major rewrite lands.

### Neutral

- `_KNOWN_ACTIONS` byte-identity fixtures stay pinned (7 fixtures,
  no updates needed).
- SPEC/v1 contract stable.

## Scope

**In scope:**
- Additions to `_KNOWN_ACTIONS` from v2.11 onward.
- Convention enforcement via `check-audit-action-name-convention.py`
  (advisory).

**Out of scope:**
- Rename of existing actions (no).
- `tier_policy_promote_cost_gated` disambiguation (inline comment
  only; no rename).
- Any event name in external SPEC files that are NOT action literals
  (record types in `SPEC/v1/tournament-report.schema.md`,
  `SPEC/v1/rag-sidecar.schema.md`, etc. — those have their own
  naming conventions).

## Alternatives considered

### A. Rename `tier_policy_promote_cost_gated` to `tier_policy_promote_cost_gate_rejected`

- Pro: semantically clearer; aligns with the `_rejected` suffix used
  for `tier_policy_rejected` (the hold-action path).
- Con: MINOR SemVer bump + kernel batch (~2h Owner physical shell) +
  backward-compat alias table + test-fixture rewrite (7 fixtures).
  Consumer-facing breakage on downstream audit-query filters.
- Not chosen: cost > benefit given the documented semantics and the
  `event_schema` v2.9 SPEC row already explaining the gate.

### B. Adopt a stricter `surface.verb` dotted form

- Pro: Looks cleaner for log-viewers.
- Con: Dotted names break JSONPath-style consumer filters and most
  SIEM ingesters expect underscore-separated enum literals. A rename
  of all 63 actions is a MAJOR SemVer bump (forbidden within SPEC
  v1 per ADR-007).
- Not chosen: violates SemVer-MAJOR freeze.

### C. Do nothing — absorb the finding as design-decision

- Pro: zero work.
- Con: pattern drifts on the next action addition; no guardrail.
- Not chosen: ADR-007 requires every `_KNOWN_ACTIONS` addition ships
  with a new ADR; codifying the naming rule now is cheaper than
  relitigating on each addition.

## Enforcement

- **Advisory linter:** `.claude/scripts/check-audit-action-name-convention.py`
  shipped 2026-04-21. Imports `_KNOWN_ACTIONS` names (regex-extracted,
  no runtime import of audit_emit) and checks each against
  `^[a-z][a-z0-9]*(_[a-z0-9]+){1,3}$`. Findings are advisory; `--strict`
  flag raises exit code to 1 for CI-enforced mode (v2).
- **Allowlist seed (5 entries):**
  - `tier_policy_promote_cost_gated` — semantic-ambiguity outlier per
    original ADR-065 finding F-07-08
  - `mcp_server_disabled_by_kill_switch` — compound-surface outlier
    (6 segments total; surface = `mcp_server`)
  - `tier_policy_hmac_verify_failed` — compound-surface (5 segments)
  - `tier_policy_adopter_override_respected` — compound-surface
  - `tier_policy_dry_run_complete` — compound-surface
  
  Future exceptions require an ADR-065 amendment.
- **Regex slot-count rationale:** the documented `{1,3}` slot-count
  after surface matches single-word surfaces. When the surface is
  compound (`tier_policy`, `mcp_server`) the effective total reaches
  5-6 segments. The 4 additional grandfathered entries above are
  preserved as-is per the ADR's "freeze corpus" decision. v2 may
  amend the regex to `{1,5}` to cover compound-surface names without
  individual allowlist entries.
- **CI wiring:** `validate.yml` step "check-audit-action-name-
  convention" runs the linter; prints findings; does NOT fail the
  build in v1 (advisory). Promote to fail-on-finding in v2.
- **Usage:**
  ```bash
  # advisory (always exit 0 unless internal error)
  python3 .claude/scripts/check-audit-action-name-convention.py

  # strict mode (exit 1 on any non-grandfathered violation)
  python3 .claude/scripts/check-audit-action-name-convention.py --strict

  # audit mode — print all 75 names with status
  python3 .claude/scripts/check-audit-action-name-convention.py --audit
  ```

## Related

- **ADR-005** — audit event stream v2 (defines the registry contract).
- **ADR-007** — SPEC v1 SemVer + RC policy (action additions are
  MINOR bumps).
- **ADR-056/062/063/064** — each plan that introduced new action
  surfaces (hook lifecycle, RAG sidecar, tournament, tier_policy).
- **PLAN-044 F-07-08** — the finding that triggered this ADR.

## Enforcement commit

(populated on canonical flip — SHA of the commit registering
ADR-065 into `.claude/adr/README.md` index + wiring the advisory
linter into `validate.yml`).
