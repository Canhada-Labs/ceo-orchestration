# SPEC v1 — soc2-control-map.schema

> **Normative source:** `docs/soc2-audit-mapping.md` (PLAN-013 Phase C.2 deliverable)
> **Spec version:** 1.0.0-rc.1 (PLAN-013 Phase C.3, Sprint 13)
> **Status:** PROPOSED (additive; promotes to ACCEPTED when Phase C.2
> `docs/soc2-audit-mapping.md` lands and CI check C.5 passes).
> **Related ADR:** ADR-043 — SOC2 Audit Trail Mapping.

---

## 1. Version

`1.0.0-rc.1` — SemVer `MAJOR.MINOR.PATCH[-rc.N]`.

- **MAJOR**: semantic break to the mapping contract (e.g. control IDs
  removed, evidence-shape change, retroactive deletion of an existing
  mapping within a MAJOR line). Forbidden within v1.
- **MINOR**: additive control mapping (new CC row), additive evidence
  row on an existing control, new audit event mapping, new gap entry.
- **PATCH**: clarification, typo fix, link repair, prose tightening.
  Never changes semantics.

Initial publication bumps from `1.0.0-rc.1` → `1.0.0` on Phase C.2
merge. Every subsequent amendment bumps MINOR (additive) or PATCH
(editorial) per ADR-007 SemVer + RC policy.

---

## 2. Status

`PROPOSED` — this document is a Phase 0-reserved schema. It promotes to
`ACCEPTED` when **all three** conditions hold:

1. `docs/soc2-audit-mapping.md` (Phase C.2) merges with all 9 CC
   controls populated per ADR-043 §Scope.
2. CI check `.claude/scripts/check-threat-model-coverage.py` (PLAN-013
   Phase C.5) passes on the main branch — asserting every
   `tags: [security]` ADR appears in the threat model and every CC
   control in this schema has ≥1 concrete evidence row.
3. ADR-043 `Status:` flips from `PROPOSED` to `ACCEPTED` via its own
   Transition Log row (ADR-041 convention) signed by the Owner.

Until all three are true, downstream consumers (Sprint 15 adopter-1
install, Sprint 18+ external-audit readiness) MUST treat this schema
as non-binding preview.

---

## 3. Overview

### Purpose

This schema declares the **canonical document shape** for expressing
SOC2 Common Criteria (CC) control-to-evidence mappings produced by the
framework. It is the machine-readable counterpart of
`docs/soc2-audit-mapping.md` (the human-readable narrative).

Consumers use this schema to:

- Verify every CC control the framework claims to support has concrete
  evidence (file path, audit event, hook, or ADR).
- Cross-reference audit events emitted by `_lib/audit_emit.py` against
  the control(s) they support.
- Enumerate open gaps with named remediation owners + deadlines.
- Enable mechanical CI assertion (PLAN-013 C.5) of mapping integrity
  without relying on prose drift detection.

### Non-goals

- **NOT** a SOC2 Type II audit deliverable. The framework's Type II
  readiness (12-month observation window + external auditor
  engagement) is explicitly deferred to Sprint 18+ per ADR-043
  §Options-C (rejected-for-now).
- **NOT** a runtime policy engine. This schema is a static mapping;
  policy-as-code (DSL-driven authorization decisions) remains out of
  scope until PLAN-014 reduced-scope (post-Sprint-15).
- **NOT** a substitute for ADR-035 (OTEL export) audit stream. The
  audit-log is the source of truth for event emission; this schema
  records *which events map to which controls*, not the events
  themselves.
- **NOT** a replacement for `docs/threat-model.md` (Phase C.1). The
  threat model enumerates adversaries + scenarios; this schema
  enumerates compensating controls against those threats.

### Normative requirements

Documents claiming conformance to this schema (currently only
`docs/soc2-audit-mapping.md`) MUST:

1. Include all three top-level arrays: `controls`, `audit_events`,
   `gaps`. Empty arrays are legal (e.g. zero known gaps).
2. Include every CC control from ADR-043 §Scope (currently 9: CC5.1,
   CC6.1, CC6.2, CC6.3, CC6.6, CC7.1, CC7.2, CC7.4, CC8.1). Adding a
   control requires a MINOR bump + ADR-043 amendment.
3. For every `controls[].evidence[]` row, populate `type` + `location`
   + `verification_method`. The `adr_ref` field is nullable.
4. For every `audit_events[]` row, populate `event` + `emitted_by` +
   `supports_controls` (non-empty list OR explicit
   `"supports_controls": ["N/A"]` flag documented in `gaps[]`).
5. Never silently remove an existing control or evidence row; see §7
   Revocation.

---

## 4. Invariants

These are enforced by PLAN-013 Phase C.5 script
`.claude/scripts/check-threat-model-coverage.py` (shared CI check that
also covers the threat model per its name):

### 4.1 Evidence integrity

**Every `controls[]` row MUST name at least one concrete evidence
artifact.** An evidence row is "concrete" iff:

- `type` ∈ `{"document", "audit_event", "adr", "hook", "script",
  "spec", "test", "workflow", "config"}`.
- `location` is a repo-relative path OR a full URL OR the canonical
  audit event name (for `type: "audit_event"`).
- `verification_method` is a non-empty imperative sentence describing
  how an auditor reproduces the check (e.g. `"grep '^action' in
  audit-log.jsonl"`, `"run .claude/scripts/check-threat-model-
  coverage.py"`, `"inspect .claude/hooks/check_agent_spawn.py
  §PERSONA check"`).

A control with zero evidence rows fails the CI check.

### 4.2 Audit event completeness

**Every event emitted by `_lib/audit_emit.py` MUST appear in
`audit_events[]`.** Sources of truth:

- Emitter list: `.claude/hooks/_lib/audit_emit.py::emit_*` functions.
- Registered schema: `SPEC/v1/audit-log.schema.md` §"Required fields
  per v2 action" table.

An event emitter that lacks an `audit_events[]` row with a non-empty
`supports_controls` list OR explicit `"N/A: not applicable to SOC2
CC"` annotation fails the CI check. This prevents silent drift where
a new hook ships emissions without SOC2 consideration.

### 4.3 Additive-only

**Existing mappings are NEVER removed within a MAJOR version.** A
control that is deprecated (e.g. replaced by a successor control in a
SOC2 revision) is annotated with a `superseded_by` field and remains
in the list. A MAJOR bump is required to delete rows; within SPEC v1,
MAJOR bumps are forbidden (ADR-007).

### 4.4 Cross-ADR reference resolvability

Every `controls[].evidence[].adr_ref` that is non-null MUST point to
an ADR file that exists under `.claude/adr/ADR-NNN-*.md`. The CI
check does `Path.exists()` on the reference.

### 4.5 Gap-list discipline

**Every `gaps[]` entry MUST have an `owner` + `deadline` + non-empty
`remediation` string.** Deadlines MUST be expressed as Sprint
identifiers (`"Sprint 15"`, `"Sprint 18"`) OR ISO dates
(`"2026-06-30"`). Unbounded deadlines (`"TBD"`, `"future"`) fail the
CI check.

---

## 5. Error model

### 5.1 CI check failures (Phase C.5 script)

The `.claude/scripts/check-threat-model-coverage.py` script
implements the invariants above. Failure modes:

| Failure | Exit code | Diagnostic |
|---|---|---|
| Control missing required evidence rows | 1 | `CONTROL_NO_EVIDENCE: CC{id} has 0 evidence entries` |
| Evidence row missing required field | 1 | `EVIDENCE_INCOMPLETE: CC{id}[{n}]: missing {field}` |
| Audit event not mapped | 1 | `EVENT_UNMAPPED: {event_name} emitted but absent from audit_events[]` |
| Audit event with empty controls + no N/A | 1 | `EVENT_SCOPE_MISSING: {event_name} supports_controls is empty and gaps[] has no N/A entry` |
| ADR reference path does not exist | 1 | `ADR_REF_BROKEN: CC{id}[{n}] adr_ref={path} not found` |
| Gap missing owner/deadline/remediation | 1 | `GAP_INCOMPLETE: gaps[{n}] missing {field}` |
| Gap deadline unbounded | 1 | `GAP_UNBOUNDED: gaps[{n}] deadline={value} is not a Sprint ID or ISO date` |
| Mapping file syntactically invalid | 2 | `PARSE_ERROR: {location}: {exception_type}` |

Exit code 0 = all invariants hold. Exit code ≥1 = CI red; the PR
adding the drift MUST fix the invariant before merge. Fail-closed
(per ADR-043 §Decision drivers — mapping integrity > observability;
contrast with audit emission which is fail-open per ADR-035).

### 5.2 No runtime failures

This schema has **zero runtime surface**. No hook reads it; no live
adapter consults it; no live audit emission depends on it. A broken
mapping can only fail CI (blocking merge) — it can never block a user
session or crash the framework.

---

## 6. Rate limit / quota

### 6.1 This schema

**N/A.** This is a static document; no rate limit applies to the
schema itself.

### 6.2 Audit-log ingestion rates it references

The audit events this schema maps ARE rate-governed per ADR-035 OTEL
Export §Rate limits:

- `_lib/otel/` bounded queue (1000 events) + 2s timeout.
- DROP_OLDEST on queue overflow → `otel_export_dropped` event fires
  (itself mapped in this schema under CC7.1 Monitoring).
- Double redaction applied at handler-parse + export boundaries
  (ADR-035 §6).

Cross-reference: `SPEC/v1/audit-log.schema.md` §Rotation (10MB or
30 days, whichever first) governs on-disk retention.

### 6.3 SOC2 Type I vs Type II

Type I (point-in-time) readiness — current scope — has no ingestion
rate requirement beyond "emit events exist + are retrievable". Type
II (12-month observation) would require uptime SLA on audit pipeline
+ retention guarantees; explicitly deferred Sprint 18+ per ADR-043
§Options-C.

---

## 7. Revocation

### 7.1 Deprecating a control mapping

When a SOC2 revision retires a control (e.g. the 2017 Trust Services
Criteria → 2024 revision consolidations) OR the framework decides a
mapping was incorrect:

1. **Annotate, do not delete.** Add `superseded_by: "CC{new_id}"` to
   the existing control row.
2. **Keep evidence rows intact.** An auditor reviewing historical
   Sprint 15 adopter state MUST still see the control that WAS in
   scope at that sprint.
3. **Append remediation to `gaps[]`.** If the supersession changed
   coverage (e.g. old control covered X, new control doesn't), file
   the delta as a gap with deadline.
4. **MINOR version bump.** Annotation is additive; no MAJOR required.

### 7.2 Deprecating an audit event mapping

When an event is renamed, retired, or loses SOC2 relevance:

1. Keep the old `audit_events[]` row with `superseded_by` annotation.
2. If the event emission itself is retired, cross-reference the ADR
   that retired it; add a `retired_in_adr` field.
3. Never remove the row — consumers running on historical audit logs
   must still resolve the control mapping for old events.

### 7.3 Revoking a gap (remediation complete)

A completed gap is NOT deleted from `gaps[]`:

1. Add `resolved_in` field with the merge commit SHA (or PR ref) that
   closed the gap.
2. Add `resolved_at` with ISO date.
3. Keep the original gap entry — auditor timeline requires evidence
   the gap existed AND was closed.

---

## 8. Deprecation

### 8.1 Deprecation window: 2 versions

Any field or row marked `superseded_by` remains readable for **two
MINOR versions** minimum before the earliest permissible MAJOR bump
that could remove it. Since MAJOR bumps are forbidden within SPEC v1,
deprecated rows in effect stay forever (until a hypothetical SPEC v2).

### 8.2 Consumer obligation

Consumers of this schema (currently the Phase C.5 CI check;
potentially a future audit-dashboard panel) MUST:

- Tolerate unknown top-level fields (forward-compat).
- Treat a `superseded_by` row as non-authoritative for NEW assertions
  but retain it for historical queries.
- Fail-closed when asked to assert `control X has evidence` on a
  superseded control — return `DEPRECATED` rather than silently
  switching to the successor.

### 8.3 Notification

Deprecations are announced via:

1. ADR-043 Transition Log row with From-State=`active` →
   To-State=`superseded by CC{new_id}` (ADR-041 convention).
2. CHANGELOG entry in CLAUDE.md session-close.
3. If the deprecation affects Sprint 15+ adopters (adopter-1, adopter-2), cross-post to `docs/adopters-notes.md` (Phase E.5
   deliverable).

---

## 9. Versioning

### 9.1 SemVer rules (binding)

| Change | Bump | Example |
|---|---|---|
| Add new control row (e.g. CC7.3 for Sprint 18+ Type II) | MINOR | `1.0.0 → 1.1.0` |
| Add evidence row to existing control | MINOR | `1.0.0 → 1.1.0` |
| Add new audit event mapping | MINOR | `1.1.0 → 1.2.0` |
| Add / resolve gap entry | MINOR | `1.2.0 → 1.3.0` |
| Annotate `superseded_by` on existing row | MINOR | `1.3.0 → 1.4.0` |
| Typo / clarification / link repair | PATCH | `1.4.0 → 1.4.1` |
| Remove any row | MAJOR | Forbidden in v1 |
| Rename a field | MAJOR | Forbidden in v1 |
| Change evidence-row required field set | MAJOR | Forbidden in v1 |

### 9.2 RC holds (per ADR-007)

- `1.0.0-rc.1` is the first publication shipping in PLAN-013 Phase
  C.3 (this document).
- `1.0.0` promotion happens when Phase C.2 merges the populated
  mapping AND the 24h RC hold elapses (per ADR-103, which reduced the original ADR-007 7-day window) AND ADR-043 is ACCEPTED.
- Each subsequent MINOR bump MAY use an RC cycle at the Owner's
  discretion (low-risk additive bumps typically skip RC).

### 9.3 Relationship to framework VERSION

The framework `VERSION=1.4.0-rc.1` and this schema `1.0.0-rc.1` are
**independent**. The framework can bump without this schema bumping;
this schema can bump (adding new gap annotations, for instance)
without the framework bumping.

---

## 10. History

| SPEC version | Date | Notes |
|---|---|---|
| 1.0.0-rc.1 | 2026-04-16 | Initial publication. PLAN-013 Phase C.3. 9-control scope per ADR-043. Mirrors 11-section structure of `adapters.schema.md` + `live-adapters-policy.schema.md`. No populated mappings (Phase C.2 ships those). |

---

## 11. Backward-compat guarantees + deprecation-window

### 11.1 Guarantees (binding within SPEC v1)

1. **Additive-only.** Every subsequent publication within
   `1.x.y` retains all rows present in `1.0.0` plus any additions.
2. **Field-stable.** The five field names on an `evidence` row
   (`type`, `location`, `verification_method`, `adr_ref`) and the
   four field names on a `gaps` row (`description`, `owner`,
   `deadline`, `remediation`) are stable through SPEC v1.
3. **Control ID stable.** CC identifiers never change spelling; a
   control is either present with its original ID OR
   `superseded_by`-annotated.
4. **Audit event name stability.** Event names in `audit_events[]`
   match byte-identically the `action` field emitted by
   `_lib/audit_emit.py`. Event renames require a MAJOR bump
   (forbidden in v1); in practice the framework never renames audit
   events — it adds new ones and deprecates old ones.

### 11.2 Deprecation window

- Deprecated rows (annotated `superseded_by`) remain readable for
  **at least 2 MINOR versions** before the earliest candidate MAJOR
  bump could remove them. Within SPEC v1 this is effectively forever.
- Deprecated rows are flagged in Phase C.5 CI output as `INFO`, not
  `WARN` or `ERROR` — they do not fail CI, but they appear in the
  Sprint-close report so Owner sees cumulative deprecation surface.

### 11.3 Consumer contract (forward-compat)

Consumers MUST:

- Tolerate unknown top-level fields on every row (future additive
  extensions).
- Treat the three top-level arrays (`controls`, `audit_events`,
  `gaps`) as authoritative — additional top-level keys MAY be
  ignored.
- Dereference `adr_ref` values lazily; a broken reference is a CI
  error, not a parse error (Phase C.5 script catches it).

### 11.4 SPEC v2 compatibility (future)

If a hypothetical SPEC v2 introduces breaking changes (e.g. a
control-shape restructure for SOC2 2024 revision), the v2 publication
MUST:

1. Ship a migration tool that converts v1 documents to v2.
2. Keep the v1 schema file as `soc2-control-map.schema.v1.md`
   readable for 6 months minimum after v2 publication.
3. Document the migration in ADR-043 (amendment) + a new ADR on the
   migration itself.

---

## Document structure (normative JSON shape)

The canonical shape a Phase C.2 populated mapping file MUST produce
when serialized (or expressed as markdown tables matching this
structure):

```json
{
  "version": "1.0.0",
  "generated_at": "2026-04-16T12:00:00Z",
  "generator": "docs/soc2-audit-mapping.md",
  "spec_schema": "SPEC/v1/soc2-control-map.schema.md",
  "controls": [
    {
      "id": "CC5.1",
      "area": "Risk Mitigation",
      "description": "The entity identifies, selects, and develops risk mitigation activities for risks arising from potential business disruptions.",
      "evidence": [
        {
          "type": "document",
          "location": "docs/threat-model.md",
          "verification_method": "grep '^## STRIDE' docs/threat-model.md && check-threat-model-coverage.py",
          "adr_ref": null
        },
        {
          "type": "adr",
          "location": ".claude/adr/ADR-044-formal-verification-pilot.md",
          "verification_method": "cat .claude/adr/ADR-044-*.md | grep -c '^## '",
          "adr_ref": ".claude/adr/ADR-044-formal-verification-pilot.md"
        }
      ],
      "superseded_by": null,
      "retired_in_adr": null
    },
    {
      "id": "CC6.1",
      "area": "Logical Access — Authentication",
      "description": "The entity implements logical access security software, infrastructure, and architectures over protected information assets.",
      "evidence": [
        {
          "type": "adr",
          "location": ".claude/adr/ADR-042-mcp-server-contract.md",
          "verification_method": "grep -A 5 '§Auth (Phase 0 — locked)' .claude/adr/ADR-042-*.md",
          "adr_ref": ".claude/adr/ADR-042-mcp-server-contract.md"
        },
        {
          "type": "audit_event",
          "location": "mcp_handler_denied",
          "verification_method": "audit-query.py --action mcp_handler_denied (Phase A post-deployment)",
          "adr_ref": ".claude/adr/ADR-042-mcp-server-contract.md"
        }
      ]
    },
    {
      "id": "CC6.2",
      "area": "Logical Access — Provisioning",
      "evidence": [
        {
          "type": "config",
          "location": ".claude/settings.json",
          "verification_method": "jq '.mcp_client_registry, .squad_allowlist, .live_adapter_allowlist' .claude/settings.json",
          "adr_ref": ".claude/adr/ADR-040-live-adapter-activation-contract.md"
        },
        {
          "type": "document",
          "location": "docs/rotation-log.md",
          "verification_method": "grep -c '^## ' docs/rotation-log.md",
          "adr_ref": null
        }
      ]
    },
    {
      "id": "CC6.3",
      "area": "Logical Access — Removal",
      "evidence": [
        {
          "type": "adr",
          "location": ".claude/adr/ADR-040-live-adapter-activation-contract.md",
          "verification_method": "grep -A 3 'credential_max_age_days' SPEC/v1/live-adapters-policy.schema.md",
          "adr_ref": ".claude/adr/ADR-040-live-adapter-activation-contract.md"
        },
        {
          "type": "document",
          "location": ".claude/squad-revocations.jsonl",
          "verification_method": "wc -l .claude/squad-revocations.jsonl (existence; entries are historical)",
          "adr_ref": ".claude/adr/ADR-039-skill-marketplace-protocol.md"
        }
      ]
    },
    {
      "id": "CC6.6",
      "area": "External System Boundary",
      "evidence": [
        {
          "type": "adr",
          "location": ".claude/adr/ADR-040-live-adapter-activation-contract.md",
          "verification_method": "grep -B 1 -A 10 '§6 activation gate' .claude/adr/ADR-040-*.md",
          "adr_ref": ".claude/adr/ADR-040-live-adapter-activation-contract.md"
        },
        {
          "type": "adr",
          "location": ".claude/adr/ADR-042-mcp-server-contract.md",
          "verification_method": "grep '§Auth.4 CORS' .claude/adr/ADR-042-*.md",
          "adr_ref": ".claude/adr/ADR-042-mcp-server-contract.md"
        },
        {
          "type": "document",
          "location": "docs/threat-model/trust-boundaries.md",
          "verification_method": "check-threat-model-coverage.py --boundaries",
          "adr_ref": null
        }
      ]
    },
    {
      "id": "CC7.1",
      "area": "Monitoring — Baseline",
      "evidence": [
        {
          "type": "spec",
          "location": "SPEC/v1/audit-log.schema.md",
          "verification_method": "diff <(jq -r 'keys[]' audit-log.jsonl | sort -u) <(grep '^| `' SPEC/v1/audit-log.schema.md | awk '{print $2}')",
          "adr_ref": ".claude/adr/ADR-005-event-stream-v2.md"
        },
        {
          "type": "hook",
          "location": ".claude/hooks/_lib/audit_emit.py",
          "verification_method": "grep '^def emit_' .claude/hooks/_lib/audit_emit.py",
          "adr_ref": ".claude/adr/ADR-005-event-stream-v2.md"
        },
        {
          "type": "adr",
          "location": ".claude/adr/ADR-035-otel-export.md",
          "verification_method": "grep 'double redact' .claude/adr/ADR-035-*.md",
          "adr_ref": ".claude/adr/ADR-035-otel-export.md"
        }
      ]
    },
    {
      "id": "CC7.2",
      "area": "Monitoring — Change Management",
      "evidence": [
        {
          "type": "hook",
          "location": ".claude/hooks/check_canonical_edit.py",
          "verification_method": "python -m pytest .claude/hooks/tests/test_check_canonical_edit.py",
          "adr_ref": ".claude/adr/ADR-010-canonical-edit-sentinel.md"
        },
        {
          "type": "workflow",
          "location": ".github/workflows/release.yml",
          "verification_method": "grep '7-day' .github/workflows/release.yml",
          "adr_ref": ".claude/adr/ADR-007-spec-v1-semver-rc-policy.md"
        },
        {
          "type": "adr",
          "location": ".claude/adr/ADR-044-formal-verification-pilot.md",
          "verification_method": "grep -c 'conformance' .claude/adr/ADR-044-*.md",
          "adr_ref": ".claude/adr/ADR-044-formal-verification-pilot.md"
        }
      ]
    },
    {
      "id": "CC7.4",
      "area": "Incident Response",
      "evidence": [
        {
          "type": "document",
          "location": "docs/incident-response.md",
          "verification_method": "grep -c '^## ' docs/incident-response.md",
          "adr_ref": null
        },
        {
          "type": "config",
          "location": "CEO_SOTA_DISABLE env var",
          "verification_method": "grep -rn 'CEO_SOTA_DISABLE' .claude/hooks/ .claude/scripts/ .github/workflows/",
          "adr_ref": null
        }
      ]
    },
    {
      "id": "CC8.1",
      "area": "Change Management — Authorization",
      "evidence": [
        {
          "type": "document",
          "location": "PROTOCOL.md",
          "verification_method": "grep '^## ' PROTOCOL.md | grep -E 'Plan|Debate|Execute'",
          "adr_ref": null
        },
        {
          "type": "document",
          "location": ".claude/adr/README.md",
          "verification_method": "cat .claude/adr/README.md",
          "adr_ref": null
        },
        {
          "type": "document",
          "location": ".claude/plans/PLAN-*/debate/",
          "verification_method": "find .claude/plans -type d -name debate | wc -l",
          "adr_ref": null
        }
      ]
    }
  ],
  "audit_events": [
    {
      "event": "agent_spawn",
      "emitted_by": ".claude/hooks/audit_log.py",
      "supports_controls": ["CC6.1", "CC8.1"],
      "description_hash_field": "desc_hash",
      "redaction_applied": true
    },
    {
      "event": "debate_event",
      "emitted_by": ".claude/scripts/debate-emit.py",
      "supports_controls": ["CC8.1"]
    },
    {
      "event": "plan_transition",
      "emitted_by": ".claude/hooks/check_plan_edit.py",
      "supports_controls": ["CC7.2", "CC8.1"]
    },
    {
      "event": "veto_triggered",
      "emitted_by": "any governance hook on block path",
      "supports_controls": ["CC6.1", "CC7.2", "CC8.1"]
    },
    {
      "event": "benchmark_run",
      "emitted_by": ".claude/scripts/run-skill-benchmark.py",
      "supports_controls": ["CC7.1"]
    },
    {
      "event": "lesson_write",
      "emitted_by": ".claude/scripts/lessons.py",
      "supports_controls": ["N/A: operational learning loop; no direct SOC2 mapping"]
    },
    {
      "event": "injection_flag",
      "emitted_by": ".claude/hooks/check_read_injection.py",
      "supports_controls": ["CC6.1", "CC6.6", "CC7.1"]
    },
    {
      "event": "confidence_gate",
      "emitted_by": ".claude/hooks/check_confidence_gate.py",
      "supports_controls": ["CC7.2"]
    },
    {
      "event": "lesson_read",
      "emitted_by": ".claude/scripts/lessons.py",
      "supports_controls": ["N/A: operational learning loop; no direct SOC2 mapping"]
    },
    {
      "event": "lesson_archived",
      "emitted_by": ".claude/scripts/prune-lessons.py",
      "supports_controls": ["N/A: lifecycle bookkeeping; no direct SOC2 mapping"]
    },
    {
      "event": "lesson_restored",
      "emitted_by": ".claude/scripts/lesson-restore.py",
      "supports_controls": ["N/A: lifecycle bookkeeping; no direct SOC2 mapping"]
    },
    {
      "event": "lesson_outcome",
      "emitted_by": ".claude/hooks/emit_architect_outcome.py",
      "supports_controls": ["N/A: architect learning loop; no direct SOC2 mapping"]
    },
    {
      "event": "lesson_outcome_undone",
      "emitted_by": ".claude/scripts/lessons.py",
      "supports_controls": ["N/A: admin override of learning loop; no direct SOC2 mapping"]
    },
    {
      "event": "state_store_write",
      "emitted_by": ".claude/hooks/_lib/state_store.py",
      "supports_controls": ["CC6.1", "CC7.1"]
    },
    {
      "event": "state_store_read",
      "emitted_by": ".claude/hooks/_lib/state_store.py",
      "supports_controls": ["CC7.1"]
    },
    {
      "event": "state_store_pruned",
      "emitted_by": ".claude/hooks/_lib/state_store.py",
      "supports_controls": ["CC6.3", "CC7.1"]
    },
    {
      "event": "budget_exceeded",
      "emitted_by": ".claude/hooks/check_budget.py",
      "supports_controls": ["CC6.6", "CC7.1", "CC7.4"]
    },
    {
      "event": "budget_bypass_used",
      "emitted_by": ".claude/hooks/check_budget.py",
      "supports_controls": ["CC6.1", "CC7.2"]
    },
    {
      "event": "otel_export_dropped",
      "emitted_by": ".claude/hooks/_lib/otel/",
      "supports_controls": ["CC7.1", "CC7.4"]
    },
    {
      "event": "output_safety_flag",
      "emitted_by": ".claude/hooks/check_output_safety.py",
      "supports_controls": ["CC6.1", "CC6.6", "CC7.1"]
    },
    {
      "event": "skill_patch_applied",
      "emitted_by": ".claude/scripts/skill-patch-apply.py",
      "supports_controls": ["CC7.2", "CC8.1"]
    },
    {
      "event": "squad_imported",
      "emitted_by": ".claude/scripts/squad-import.py",
      "supports_controls": ["CC6.2", "CC7.2", "CC8.1"]
    }
  ],
  "gaps": [
    {
      "id": "GAP-001",
      "description": "MCP handler audit events (mcp_handler_invoked, mcp_handler_denied) referenced by CC6.1 are Phase A deliverables; not yet emitted by _lib/audit_emit.py.",
      "owner": "CEO / Phase A owner",
      "deadline": "Sprint 13 (PLAN-013 Phase A.6)",
      "remediation": "Phase A.6 registers the events in SPEC/v1/audit-log.schema.md + adds emit_mcp_handler_invoked / emit_mcp_handler_denied to audit_emit.py; Phase C.5 CI check starts enforcing on first main-branch run thereafter.",
      "resolved_in": null,
      "resolved_at": null
    },
    {
      "id": "GAP-002",
      "description": "Formal verification conformance harness proofs (ADR-044) are Phase D deliverables; CC7.2 evidence is currently ADR text only, not executable properties.",
      "owner": "Phase D owner",
      "deadline": "Sprint 13 (PLAN-013 Phase D)",
      "remediation": "Phase D ships ≥3 safety + ≥1 liveness property with executable hypothesis + mutation-test gate per ADR-044.",
      "resolved_in": null,
      "resolved_at": null
    },
    {
      "id": "GAP-003",
      "description": "docs/incident-response.md referenced by CC7.4 is a Phase C.2 deliverable and does not yet exist.",
      "owner": "Phase C.2 owner",
      "deadline": "Sprint 13 (PLAN-013 Phase C.2)",
      "remediation": "Phase C.2 authors docs/incident-response.md covering kill-switch (CEO_SOTA_DISABLE=1), breaker open state (ADR-040 §2), rollback paths (PLAN-012 §Revert procedure), Owner escalation.",
      "resolved_in": null,
      "resolved_at": null
    },
    {
      "id": "GAP-004",
      "description": "docs/threat-model/trust-boundaries.md referenced by CC6.6 is a Phase C.1 deliverable.",
      "owner": "Phase C.1 owner",
      "deadline": "Sprint 13 (PLAN-013 Phase C.1)",
      "remediation": "Phase C.1 ships trust-boundary diagram as part of docs/threat-model.md tree.",
      "resolved_in": null,
      "resolved_at": null
    },
    {
      "id": "GAP-005",
      "description": "SOC2 Type II (12-month observation + external auditor engagement) is out of scope for PLAN-013 per ADR-043 §Options-C.",
      "owner": "CEO (decision holder)",
      "deadline": "Sprint 18 (conditional on Owner Go-Public decision)",
      "remediation": "Sprint 18+ plan MUST include: uptime SLA for audit pipeline; 12-month retention guarantee; external auditor procurement; retest of all CC controls against Type II criteria.",
      "resolved_in": null,
      "resolved_at": null
    }
  ]
}
```

**Note:** Phase C.2 MAY express the above as nine `## CCx.y` markdown
sections with tables, provided the information content is isomorphic.
The JSON shape above is the *authoritative semantic contract*; the
markdown is the authoritative human presentation. Phase C.5 CI check
parses the markdown and validates against this schema.

---

## Referenced by

- ADR-043 — SOC2 Audit Trail Mapping (authoritative decision record).
- `docs/soc2-audit-mapping.md` (Phase C.2) — populated mapping.
- `docs/threat-model.md` + `docs/threat-model/**` (Phase C.1) —
  threat-model artifacts referenced under CC5.1, CC6.6, CC7.4.
- `SPEC/v1/audit-log.schema.md` — canonical audit event schema
  referenced under CC7.1.
- `SPEC/v1/live-adapters-policy.schema.md` — referenced under CC6.2,
  CC6.3 (credential lifecycle).
- `.claude/scripts/check-threat-model-coverage.py` (Phase C.5) — CI
  check enforcing §4 invariants.

---

## Changelog

- **1.0.0-rc.1** (2026-04-16, PLAN-013 Phase C.3): initial
  publication. Declares 9-control scope (CC5.1, CC6.1, CC6.2, CC6.3,
  CC6.6, CC7.1, CC7.2, CC7.4, CC8.1), document structure, invariants
  (4), error model, revocation/deprecation discipline (additive-only
  within v1), and backward-compat guarantees. Mirrors 11-section
  structure of `adapters.schema.md` + `live-adapters-policy.schema.md`
  per consensus §S14.
