# ADR-043: SOC2 Audit Trail Mapping

**Status:** ACCEPTED
**Date:** 2026-04-15 (stub reservation) / 2026-04-16 (full accept, Phase C.4)
**Sprint:** 13 (PLAN-013 Phase 0 reservation + Phase C.4 full decision)
**Related:** ADR-035 (OTEL export — audit event canonical source),
ADR-040 (Live Adapter Activation Contract — live call events are
SOC2-mapped), ADR-041 (Transition Log Convention — compliance state
changes tracked per-ADR), ADR-042 (MCP Server Contract — handler
denial events map to CC6.1 Logical Access), ADR-044 (Formal
Verification Pilot — proved invariants inform CC7.2 Change Management
scope).

## Context

PLAN-013 Phase C expands the threat model + SOC2 audit scope ahead
of Sprint 15 adopter-1 validation. The debate Round 1
consensus §C4 (HIGH, 3/5 agents — Security, VP Engineering, DevOps)
flagged two gaps in the original proposal:

1. **Threat model scope too narrow.** "≥3 scenarios per STRIDE
   category" = 18 total, below the 30-scenario floor for meaningful
   coverage of a framework with 41 ADRs, 12 hooks, and 48 skills.
   Per-ADR threat table missing; would become paste-in mapping
   without forcing function. Attacker capability model and
   trust-boundary diagram absent. Out-of-scope section missing.
2. **SOC2 Common Criteria scope too narrow.** Original 5 controls
   (CC6.1 / CC6.6 / CC7.1 / CC7.2 / CC8.1) miss CC5.1 (Risk
   Mitigation), CC6.2 (Logical Access Provisioning), CC6.3 (Logical
   Access Removal), CC7.4 (Incident Response). Framework touches
   all nine directly; 5-of-9 mapping = compliance theater, Staff
   Security vetoes.

This stub reserves the ADR number. Full decision content (scenario
catalog, per-ADR threat table, SOC2 9-control mapping,
evidence-to-code cross-reference, TOC with §C scenario pool pointer)
lands in Phase C.4 after Phase C.1 (threat model) + C.2 (SOC2
mapping) complete.

## Decision drivers

- **Scenario floor ≥30** (PLAN-013 consensus §C4): STRIDE × 6
  categories = 5 per category minimum, not 3.
- **Per-ADR threat table mandatory** (consensus §C4): every ADR
  gets a threat row in
  `docs/threat-model/per-adr-threat-matrix.md` (Phase C.1);
  cross-reference-only is not enough.
- **Attacker capability model required** (consensus §C4): explicit
  adversary profile (external network-remote, internal-network
  insider, compromised-skill-upgrade supply-chain, LLM-provider
  outage/compromise) with capability × goal × controls matrix.
- **Trust-boundary diagram required** (consensus §C4): system
  diagram distinguishing Claude-native invocation, MCP external
  invocation, hook mechanical enforcement boundaries, OTEL export
  to third-party destination, provider API surface. Phase C.1
  deliverable.
- **Out-of-scope section explicit** (consensus §C4): what the
  threat model deliberately does NOT cover (e.g. physical security,
  OS kernel attacks, compiler supply chain beyond our pins).
- **SOC2 9-control mapping** (consensus §C4): mapping is
  per-control with evidence pointer to code, audit event, or hook.
  No "see ADR-XXX" pointers without naming the specific control and
  specific evidence.
- **Conformance harness cross-reference** (ADR-044): formally-proved
  invariants contribute evidence for CC7.2 Change Management (proof
  artifact = change-control evidence).

## §Scope (Phase 0 — locked)

This ADR covers the following nine SOC2 Common Criteria controls,
mapped to framework audit events, hooks, and ADRs. Full evidence
column lands in Phase C.4.

| Control | Area | Framework surface (evidence pointer) |
|---|---|---|
| **CC5.1** | Risk Mitigation | Threat model catalog (`docs/threat-model/stride-catalog.md` Phase C.1) + ADR-044 formal-verification conformance tests |
| **CC6.1** | Logical Access — Authentication | ADR-042 §Auth (HMAC + default-deny + audit on denial) + `mcp_handler_denied` audit event |
| **CC6.2** | Logical Access — Provisioning | `.claude/settings.json` `mcp_client_registry` (ADR-042) + `live_adapter_allowlist` (ADR-040) + operator sign-off in `docs/rotation-log.md` |
| **CC6.3** | Logical Access — Removal | Credential rotation hard 90-day cap (ADR-040 §4) + `credential_rotation_due` audit event + revocation ledger (skill marketplace, ADR-039) |
| **CC6.6** | External System Boundary | ADR-040 §6 activation gate (per-provider flags default disabled) + ADR-042 §Auth.4 CORS default-deny + network-boundary documentation in `docs/threat-model/trust-boundaries.md` (Phase C.1) |
| **CC7.1** | Monitoring — Baseline | Audit-log schema (`SPEC/v1/audit-log.schema.md`) + `_lib/audit_emit.py` canonical export + OTEL export (ADR-035) |
| **CC7.2** | Monitoring — Change Management | `check_canonical_edit.py` hook (ADR-010) + branch protection (ADR-003) + CODEOWNERS + release gate 7-day RC hold (PLAN-013 Phase 0 item 0.3) + ADR-044 formal-verification proofs as change-control evidence |
| **CC7.4** | Incident Response | `docs/incident-response.md` (Phase C.2 deliverable) covering: kill-switch (`CEO_SOTA_DISABLE=1`), breaker open state (ADR-040 §2), rollback paths (PLAN-012 §Revert procedure), Owner escalation |
| **CC8.1** | Change Management — Authorization | PROTOCOL.md plan-debate-execute + ADR numbering (`.claude/adr/README.md`) + debate artifacts under `.claude/plans/PLAN-*/debate/` + 3-strike policy |

## Options considered

### Option A — 9 CC controls with evidence-to-code cross-reference (CHOSEN)

Every control names ≥1 concrete evidence pointer: a file path, an
audit event, a hook module, an ADR reference, or a workflow file. The
Phase C.5 CI check (`.claude/scripts/check-threat-model-coverage.py`)
mechanically asserts that every control has non-empty evidence rows
and every emitted audit event either has a non-empty
`supports_controls` list or an explicit `"N/A: not applicable to
SOC2 CC"` annotation.

**Pros:**

- **Adopter-defensible.** Sprint 15 adopter-1 / Sprint 16 adopter-2
  adopters can hand the mapping + evidence trail to their own
  security team for Type I readiness review without bespoke work.
- **Auditor-friendly.** A SOC2 Type I auditor can `grep`, `jq`, or
  `cat` every claim; zero interpretive prose between the control and
  the evidence. This is the closest a framework without an external
  auditor engagement can get to "audit-ready".
- **Cross-cuts the framework evenly.** 9 controls span risk
  mitigation (CC5.1), access management (CC6.1-6.6), monitoring
  (CC7.1-7.4), change management (CC8.1). Every major subsystem
  (hooks, live adapters, MCP server, squad marketplace, OTEL,
  chaos, skill patches) contributes evidence to at least one
  control.
- **CI-enforced.** The Phase C.5 script prevents silent drift; a
  new hook emitting a new audit event without SOC2 mapping fails
  the main-branch CI.
- **Additive upgrade path.** If Sprint 18+ goes Type II, the same
  mapping forms the skeleton — Type II just adds 12-month
  observation evidence rows, not a new schema.

**Cons:**

- **Maintenance burden.** Every new ADR that introduces an audit
  event or governance surface must update `docs/soc2-audit-
  mapping.md`. This is enforced by CI (fail-closed), so skipping is
  not an option — discipline cost is real.
- **Gap-list requires quarterly review.** 5 open gaps ship with
  1.0.0 (MCP handler events, formal verification conformance,
  incident-response doc, trust-boundary diagram, Type II
  readiness). Owner must cycle through them; the Phase C.5 script
  fails CI on unbounded deadlines, so gaps cannot drift to "TBD".
- **9 controls is not 100% SOC2 CC coverage.** The 2017 TSC has 33
  Common Criteria; we map 9. The un-mapped 24 are deliberately
  out-of-scope for a framework layer (e.g. CC2.1 internal
  communications, CC4.1 risk assessment process — adopter's
  responsibility). This distinction must be crystal-clear in the
  mapping doc to prevent false "SOC2 compliant" claims.

### Option B — 5 CC controls minimum (REJECTED per PLAN-013 consensus §C4)

Original Phase 0 scope per pre-debate PLAN-013 draft: map only CC6.1,
CC6.6, CC7.1, CC7.2, CC8.1 (authentication + external boundary +
monitoring baseline + change management + change authorization).

**Pros:**

- Less maintenance surface.
- Faster initial delivery (smaller mapping doc).
- Easier to keep aligned when ADRs churn.

**Cons:**

- **Debate consensus §C4 HIGH (3/5 agents — Security, VP Engineering,
  DevOps) flagged this as compliance theater.** Framework touches
  all 9 of the chosen controls directly — mapping only 5 creates a
  false impression of bounded coverage when the un-mapped 4 (CC5.1
  risk mitigation, CC6.2/6.3 provisioning/removal, CC7.4 incident
  response) have clear framework surfaces.
- **CC5.1 (risk mitigation) omission is the most damning.** We ship
  a threat model (Phase C.1) and formal verification (Phase D.1) —
  these are textbook CC5.1 evidence. Omitting them says "we don't
  mitigate risk" which contradicts ~40% of Sprint 11-12 effort.
- **CC6.2/6.3 (logical access provisioning/removal) gaps leak into
  Sprint 15 adopter-1 adoption.** `.claude/settings.json`
  `mcp_client_registry` + `squad_allowlist` + `live_adapter_
  allowlist` ARE the provisioning surface; credential rotation
  90-day cap IS the removal surface. Not mapping them forces the
  adopter to map them inline, defeating the "adopter-defensible"
  goal.
- **CC7.4 (incident response) omission blocks Type I readiness.**
  An auditor sees our `CEO_SOTA_DISABLE=1` kill-switch + breaker
  open state + rollback procedure + Owner escalation → that IS a
  response capability. Omitting it invites a finding.
- **Staff Security (debate §C4 contributor) explicitly vetoed.**

**Rejected** per debate outcome. The 4 added controls (CC5.1, CC6.2,
CC6.3, CC7.4) cost minimal additional mapping work since the
evidence already exists.

### Option C — Full SOC2 Type II readiness (DEFERRED to Sprint 18+)

Full Type II would require:

- 12-month continuous observation window with evidence sampling at
  regular intervals.
- External auditor engagement (CPA firm) with formal scoping
  agreement.
- Uptime SLA on the audit pipeline (`_lib/audit_emit.py` +
  `_lib/otel/` export path) with measured downtime.
- 12-month retention guarantee on `audit-log.jsonl` rotation chain
  (current ADR-035 rotates at 10MB / 30 days — insufficient for Type
  II).
- Per-control test procedures executed on a schedule with
  retained evidence.
- Management assertion letter + independent auditor's opinion.

**Pros:**

- True external credibility — "SOC2 Type II certified" is an
  enterprise procurement unlock.
- Forces discipline on long-running observability (uptime tracking,
  retention guarantees) that currently ship as best-effort.
- Aligns framework with enterprise adopter expectations (Sprint 18+
  Go-Public conditional).

**Cons:**

- **Auditor cost** typically $20k-$80k per audit cycle for a
  small-scope Type II (plus internal preparation time).
- **12-month window** means a Sprint 18 kickoff couldn't yield a
  signed report before Sprint 30+ at earliest.
- **Out of scope for PLAN-013** per Owner directive "fecha tudo aqui
  no máximo possível, estado da arte, antes de aplicar em adopter-1"
  — internal-first validation, NOT external audit.
- **Locks framework into audit schedule.** Once under Type II,
  breaking changes to audit event shape require auditor notification
  + re-test windows. This constrains Sprint 13-17 architectural
  freedom.

**Deferred.** PLAN-013 ships the **foundation** (9-control mapping +
evidence trail + gap list) that a future Sprint 18+ Type II
engagement would build on. No audit date is committed; the decision
to pursue Type II is re-opened after Owner's Sprint 18 Go-Public
gate.

## Decision

**Adopt Option A: publish a 9-control SOC2 Common Criteria mapping
(`docs/soc2-audit-mapping.md`) with evidence-to-code cross-reference
for CC5.1, CC6.1, CC6.2, CC6.3, CC6.6, CC7.1, CC7.2, CC7.4, CC8.1,
enforced by the Phase C.5 CI check against the canonical schema
`SPEC/v1/soc2-control-map.schema.md`.** The 9 controls cover every
framework subsystem that has security or change-management relevance;
the mapping is additive-only within SPEC v1 (deprecations annotated,
never deleted); and gaps are explicitly enumerated with Owner,
deadline, and remediation columns.

**Why Option A won on the decision drivers:**

- **Scenario floor ≥30 / per-ADR threat table** (§Decision drivers
  bullet 1-2) — 9-control scope dovetails with Phase C.1 threat
  model by giving each STRIDE category ≥1 CC control home for its
  compensating evidence. A 5-control scope would leave Tampering
  and Denial-of-Service scenarios without a CC mapping home.
- **Attacker capability model / trust-boundary diagram** (bullets
  3-4) — both are CC6.6 external boundary evidence; both are CC5.1
  risk mitigation evidence. Without CC5.1 and CC6.6 both in scope,
  the threat model artifact serves half its audit-readiness
  purpose.
- **Out-of-scope section** (bullet 5) — Option A's gap list (5
  entries including GAP-005 "Type II deferred Sprint 18+") is the
  out-of-scope section's mechanical counterpart. Option B had no
  structured gap discipline.
- **9-control SOC2 mapping** (bullet 6) — this IS bullet 6,
  resolved.
- **Conformance harness cross-reference** (bullet 7) — ADR-044
  formal verification proofs land as CC7.2 Change Management
  evidence (proof artifact = change-control evidence). Option B
  omitted CC7.2's full breadth by keeping it but without the
  conformance-harness bridge; Option A's CC7.2 row names ADR-044
  explicitly.

**Scope locked (non-negotiable within SPEC v1):**

| Control | Area |
|---|---|
| CC5.1 | Risk Mitigation |
| CC6.1 | Logical Access — Authentication |
| CC6.2 | Logical Access — Provisioning |
| CC6.3 | Logical Access — Removal |
| CC6.6 | External System Boundary |
| CC7.1 | Monitoring — Baseline |
| CC7.2 | Monitoring — Change Management |
| CC7.4 | Incident Response |
| CC8.1 | Change Management — Authorization |

Adding a 10th control is a future MINOR-bump of
`SPEC/v1/soc2-control-map.schema.md` + an ADR-043 amendment.
Removing any of these 9 is forbidden within SPEC v1 (MAJOR-bump
required; MAJOR bumps are forbidden within v1 per ADR-007).

## Consequences

### Positive

- **Adopter-defensible mapping.** Sprint 15 (adopter-1) + Sprint 16
  (adopter-2) adopters receive a grep-able, auditor-ready CC
  evidence trail instead of bespoke narrative text.
- **Framework passes internal SOC2 Type I readiness** for the
  mapped scope. "Readiness" here means: an independent reviewer
  using only `docs/soc2-audit-mapping.md` + `SPEC/v1/soc2-control-
  map.schema.md` + the framework tree can validate every evidence
  claim without interviews.
- **Mechanical CI prevents silent drift.** Phase C.5 script
  (`.claude/scripts/check-threat-model-coverage.py`) fails the
  main-branch build if a new audit event lacks a SOC2 mapping row
  OR an explicit `N/A` annotation. Sprint 14+ ADRs that add audit
  surface must update the mapping atomically.
- **Gap list forces Owner attention.** 5 gaps ship with 1.0.0,
  each with a Sprint-indexed deadline. The Phase C.5 script fails
  CI on unbounded deadlines, making "TBD" impossible. Quarterly
  review is enforced by the drift-checker's deadline parsing.
- **Forward compat into Sprint 18+.** If the Owner later opens the
  Type II question, the same 9-control skeleton becomes the Type
  II scope starter. No re-mapping needed — just add 12-month
  observation evidence rows.
- **Cross-ADR reinforcement.** ADR-040 (live adapters), ADR-042
  (MCP server), ADR-044 (formal verification) all provide CC
  evidence without changing their own scope. The mapping is a
  *view* over existing invariants, not a new surface.

### Negative

- **9-control scope is ongoing maintenance.** Every new ADR that
  introduces an audit event or governance surface must update
  `docs/soc2-audit-mapping.md`. Phase C.5 CI check enforces this
  (fail-closed) so the burden is real — Sprint 14+ plan estimates
  must include the mapping-update line item.
- **Gap list requires quarterly review.** Owner must close GAP-001
  (MCP handler events — Phase A) + GAP-002 (formal verification
  conformance — Phase D) + GAP-003 (incident-response doc — Phase
  C.2) + GAP-004 (trust-boundary diagram — Phase C.1) within
  Sprint 13. GAP-005 (Type II) is Sprint 18 conditional. The
  drift-checker fails CI if a gap deadline elapses without
  `resolved_in` or deadline extension.
- **False-compliance-claim risk.** An adopter misreading the
  9-control mapping as "SOC2 certified" would be wrong — we map
  only CC controls where the framework provides evidence, NOT all
  33 SOC2 CC criteria. `docs/soc2-audit-mapping.md` MUST include
  a prominent "what this is NOT" section (Phase C.2 deliverable)
  citing ADR-043 §Options-C explicitly.
- **No external audit opinion.** Type I readiness ≠ Type I audit
  report. Adopters needing a signed auditor opinion must procure
  one themselves; the framework provides the evidence trail, not
  the auditor engagement.
- **Retroactive ADR-043 amendments** required every time a mapped
  control's evidence set changes (e.g. Phase A.6 adds
  `mcp_handler_invoked` → GAP-001 closes → ADR-043 Transition Log
  row). Boilerplate tax.

### Neutral

- **Zero code behaviour change.** This ADR is documentation +
  evidence-pointer discipline + CI check. No hook ships new logic;
  no adapter changes shape; no user session experience differs.
- **Additive-only within SPEC v1.** The 9-control scope can GROW
  (new controls added MINOR bump) but cannot SHRINK (removal
  requires MAJOR, forbidden in v1). This mirrors ADR-005 event
  stream additivity.
- **Transition Log mandatory** per ADR-041 convention. State
  transitions on this ADR (PROPOSED → ACCEPTED → gap closures) all
  land as appended rows, never edits.
- **No Type II commitment.** The Sprint 18 Go-Public gate remains
  independent; this ADR does NOT pre-commit the framework to a
  Type II schedule.

## Blast radius

**L2** — documentation + CI check. Files produced:

### New files (Phase C.1 / C.2 / C.3 / C.4 / C.5)

- `docs/threat-model.md` (Phase C.1) — STRIDE catalog ≥30 scenarios.
- `docs/threat-model/stride-catalog.md` (Phase C.1) — per-category
  scenario detail.
- `docs/threat-model/per-adr-threat-matrix.md` (Phase C.1) —
  per-ADR threat table.
- `docs/threat-model/trust-boundaries.md` (Phase C.1) — trust
  boundary diagram.
- `docs/soc2-audit-mapping.md` (Phase C.2) — populated 9-control
  evidence trail.
- `docs/incident-response.md` (Phase C.2) — CC7.4 evidence doc.
- `SPEC/v1/soc2-control-map.schema.md` (Phase C.3) — canonical
  schema this ADR governs.
- `.claude/adr/ADR-043-soc2-audit-trail-mapping.md` (Phase C.4 —
  this file).
- `.claude/scripts/check-threat-model-coverage.py` (Phase C.5) —
  CI check enforcing the mapping invariants.
- `.claude/scripts/tests/test_check_threat_model_coverage.py`
  (Phase C.5) — TestEnvContext-isolated unit tests for the script.

### Workflow touched

- `.github/workflows/validate.yml` (Phase C.5) — adds Phase-C.5
  script to the CI job. Fail-closed: mapping drift blocks merge.

### Modified files

- None. This ADR and the new files are additive; no existing
  hook, adapter, script, or workflow is restructured. ADR-005
  (event stream v2) is referenced but not amended; new audit
  events in Phase A / D follow existing ADR-005 additive discipline
  and are mapped in this ADR's `audit_events[]` list as they ship.

### Zero code behaviour change

- No hook logic changes.
- No live adapter behavior changes.
- No audit event shape changes (only new events added by other
  Phase A / D deliverables, which this ADR then maps).
- No user-session surface changes.
- No release-gate logic changes (the 7-day RC hold added by Phase
  0 item 0.3 is ADR-007 precedent, not this ADR).

### Reversibility

**HIGH.** This ADR is pure governance overlay on existing invariants.
Removing the ADR + the three mapping docs + the CI check would revert
the framework to its pre-PLAN-013 state with zero behavior change
(the underlying hooks, adapters, and audit events continue to emit as
before). The mapping is a *view* over existing evidence — not a
*producer* of new evidence.

## Transition Log

*This appendix follows ADR-041 Transition Log Convention.*

| Date | From-State | To-State | Evidence-Link | PR-Ref | Signer |
|------|------------|----------|---------------|--------|--------|
| 2026-04-15 | (absent) | ADR stub reserved + 9-control scope locked | PLAN-013 Phase 0 item 0.1 | Phase 0 commit | CEO |
| 2026-04-16 | PROPOSED | ACCEPTED (Phase C.4 Options + Decision + Consequences + Blast radius populated; SPEC/v1/soc2-control-map.schema.md published as 1.0.0-rc.1) | PLAN-013 Phase C.4 deliverable | Phase C.4 commit | CEO |
| _(Phase C.1 threat model completion pending — will annotate GAP-004 closure)_ | | | | | |
| _(Phase C.2 mapping doc completion pending — will annotate GAP-003 closure)_ | | | | | |
| _(Phase A.6 MCP handler events registration pending — will annotate GAP-001 closure)_ | | | | | |
| _(Phase D.1 conformance harness completion pending — will annotate GAP-002 closure)_ | | | | | |
| _(Sprint 18+ Type II decision pending — will annotate GAP-005 resolution or explicit Sprint-deferral)_ | | | | | |

## References

### PLAN-013 scope

- PLAN-013 §Phase C (C.1 threat model, C.2 SOC2 mapping doc, C.3
  SPEC schema, C.4 this ADR, C.5 CI check) — full completion scope.
- PLAN-013 §Phase 0 item 0.1 — ADR stub reservation pre-debate.
- PLAN-013 §Phase 0 item 0.5 — ADR auth/cost scope locked pre-Phase-A.
- PLAN-013 §Phase D — ADR-044 conformance harness informs CC7.2
  evidence.
- PLAN-013 §Phase E — benchmarks reference threat model (CC5.1).
- PLAN-013 debate Round 1 consensus §C4 HIGH (scope floor + per-ADR
  mapping + attacker model + trust boundary).
- PLAN-013 debate Round 1 `.claude/plans/PLAN-013/debate/round-1/
  security-engineer.md` §CRITICAL-3 (18-scenario theater rejection).
- PLAN-013 debate Round 1 `.claude/plans/PLAN-013/debate/round-1/
  consensus.md` §C4 (3/5 agents flagged scope as theater).

### Related ADRs (cross-linked)

- ADR-005 — Event stream v2 (additive discipline; mapping follows
  same additivity contract).
- ADR-007 — SPEC v1 + SemVer + RC policy (governs
  `SPEC/v1/soc2-control-map.schema.md` versioning).
- ADR-010 — Canonical edit sentinel (CC7.2 change management
  evidence — protects canonical files from unsigned edits).
- ADR-035 — OTEL export (CC7.1 monitoring baseline; audit event
  source for `otel_export_dropped`).
- ADR-039 — Skill marketplace protocol (CC6.2 provisioning +
  CC6.3 revocation ledger evidence).
- ADR-040 — Live Adapter Activation Contract (CC6.2 provisioning
  via `live_adapter_allowlist` + CC6.3 credential 90-day cap +
  CC6.6 external boundary).
- ADR-041 — Transition Log appendix format (this ADR adopts the
  convention).
- ADR-042 — MCP Server Contract (CC6.1 authentication via HMAC +
  default-deny + per-handler ACL + CC6.6 external boundary via
  CORS default-deny; audit events `mcp_handler_invoked` /
  `mcp_handler_denied` = GAP-001).
- ADR-044 — Formal Verification Pilot (CC7.2 change-control
  evidence via proved invariants + conformance harness = GAP-002).

### SPEC references

- `SPEC/v1/audit-log.schema.md` — canonical audit event schema
  this mapping references under CC7.1.
- `SPEC/v1/soc2-control-map.schema.md` — companion SPEC published
  in Phase C.3 declaring the canonical document shape.
- `SPEC/v1/live-adapters-policy.schema.md` — credential lifecycle
  fields referenced under CC6.2/CC6.3.

### Deliverables referenced

- `docs/threat-model.md` — Phase C.1 deliverable (CC5.1, CC6.6).
- `docs/threat-model/stride-catalog.md` — Phase C.1 (CC5.1).
- `docs/threat-model/per-adr-threat-matrix.md` — Phase C.1 (CC5.1).
- `docs/threat-model/trust-boundaries.md` — Phase C.1 (CC6.6 =
  GAP-004).
- `docs/soc2-audit-mapping.md` — Phase C.2 deliverable (= GAP-003
  incident-response sibling).
- `docs/incident-response.md` — Phase C.2 (CC7.4 = GAP-003).
- `.claude/scripts/check-threat-model-coverage.py` — Phase C.5
  CI check enforcing the mapping invariants.
- `.claude/scripts/tests/test_check_threat_model_coverage.py` —
  Phase C.5 TestEnvContext-isolated unit tests.

### External (non-normative)

- AICPA 2017 Trust Services Criteria — source of CC5.1 / CC6.1-6.6
  / CC7.1-7.4 / CC8.1 control definitions referenced in this ADR
  and in `docs/soc2-audit-mapping.md`.
- ADR-007 precedent for RC policy and SemVer adopted by the
  companion SPEC.

## Enforcement commit

`78ae44b0bb8a` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
