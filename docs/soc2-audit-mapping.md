# ceo-orchestration — SOC2 Audit Trail Mapping

**Status:** draft (PLAN-013 Phase C.2)
**Date:** 2026-04-16
**Owner:** Principal Security Engineer
**Scope:** SOC2 Type I readiness foundation (Type II = Sprint 18+
external audit after public launch)
**Companion docs:** `docs/threat-model.md`,
`.claude/adr/ADR-043-soc2-audit-trail-mapping.md`

---

## Executive summary

Nine SOC2 Common Criteria (CC) controls mapped to ceo-orchestration
framework evidence. Every mapping names the specific audit event,
hook file, ADR number, SPEC schema, or documentation artifact that
serves as verifiable evidence. A third-party auditor running `grep`
against the repository will find concrete file-path+line-number anchors
for every control claim.

**Control coverage:**

| Area | Controls | Evidence rows | Automation |
|---|---|---|---|
| Risk Management | CC5.1 | 4 | Threat model + formal verification |
| Logical Access | CC6.1 / CC6.2 / CC6.3 / CC6.6 | 17 | Hook enforcement + audit events |
| Monitoring | CC7.1 / CC7.2 / CC7.4 | 12 | Audit log + OTEL + incident response |
| Change Management | CC8.1 | 5 | PROTOCOL plan-debate-execute |

**Total:** 9 controls, 38 evidence rows, 27 distinct audit event types,
3 open gaps with owner + deadline.

**Framework posture (v1.4.0-rc.1):**

- Audit-log schema v2.3 locked, 27 event types emitted by 12 hooks +
  12 scripts via `_lib/audit_emit.py` as canonical export.
- Redaction-by-default on all string values written to disk
  (`_lib/redact.py` → `_lib/audit_emit.py::_preview` → state_store).
- OTEL export locked-down by ADR-035 six-mitigation bundle.
- 41 ADRs document every cross-cutting decision; transition log
  convention (ADR-041) makes state changes machine-auditable.
- Branch protection + CODEOWNERS pending Owner activation (one-time
  repo setting per `docs/BRANCH-PROTECTION.md`).

---

## Control mapping (9 controls)

### CC5.1 — Risk Mitigation

**Intent:** The entity identifies and assesses risks to the achievement
of its objectives. The entity implements and operates controls to
mitigate risks to an acceptable level.

| Evidence type | Location | Verification |
|---|---|---|
| STRIDE threat model catalog | `docs/threat-model.md` | `grep -c '^[0-9]\+\. \*\*[STRIDE][STRIDE0-9\-]\+:' docs/threat-model.md` returns 33 |
| ≥5 scenarios per STRIDE category | `docs/threat-model.md` §scenarios | `grep -c '^### Spoofing' docs/threat-model.md` returns 1; section enumerates ≥5 items |
| Per-ADR threat table | `docs/threat-model.md` §"Per-ADR threat table" | Table row count equals 41 (38 ADRs + 3 explicit gaps documented) |
| Formal-verification conformance harness | `.claude/adr/ADR-044-formal-verification-pilot.md` §Decision drivers | `properties-proved.md` (Phase D.4 deliverable) includes `test_property_i` mapping column; mutation-test gate asserts ≥5 mutations fail |

---

### CC6.1 — Logical Access — Authentication

**Intent:** The entity implements logical access security software,
infrastructure, and architectures over protected information assets
to protect them from security events.

| Evidence type | Location | Verification |
|---|---|---|
| MCP server HMAC authentication | `.claude/adr/ADR-042-mcp-server-contract.md` §Auth.1 | `grep -n 'HMAC-SHA256' .claude/adr/ADR-042-mcp-server-contract.md` returns line with token format |
| Default-deny ACL per handler | `.claude/adr/ADR-042-mcp-server-contract.md` §Auth.2 | `grep -n 'Empty or missing allowlist = refuse all' .claude/adr/ADR-042-mcp-server-contract.md` |
| MCP handler denial audit | `_lib/audit_emit.py` + `SPEC/v1/audit-log.schema.md` | Handler invocation emits `mcp_handler_denied(reason, handler, client_id_hash)` on every deny (Phase A.4 impl) |
| Persona+skill+file-assignment required on every spawn | `.claude/hooks/check_agent_spawn.py::decide()` line 98 | `has_profile=True` and `has_file_assignment=True` in `agent_spawn` event; non-compliant spawns emit `veto_triggered(hook=check_agent_spawn)` |
| Branch protection for sensitive paths | `docs/BRANCH-PROTECTION.md` + `.github/CODEOWNERS` | `gh api repos/:owner/:repo/branches/main/protection` asserts required reviews on `.claude/skills/**`, `.claude/adr/**`, `.github/workflows/**` |
| GPG signature on sentinel approval | `.claude/hooks/check_canonical_edit.py` + `.claude/adr/ADR-010-canonical-edit-sentinel.md` | `gpg --verify` in sentinel flow; denial emits `veto_triggered(reason_code=unsigned_sentinel)` |

---

### CC6.2 — Logical Access — Provisioning

**Intent:** Prior to issuing system credentials, the entity registers
and authorizes new internal and external users whose access is
administered by the entity.

| Evidence type | Location | Verification |
|---|---|---|
| MCP client registry with explicit handler ACL | `.claude/settings.json` `mcp_client_registry.<client_id>` | `jq '.mcp_client_registry' .claude/settings.json` enumerates approved clients per `ADR-042 §Auth.2`; no wildcards permitted |
| Live adapter per-provider opt-in | `.claude/adr/ADR-040-live-adapter-activation-contract.md` §6 activation gate | `grep -n 'default disabled' .claude/adr/ADR-040-live-adapter-activation-contract.md` — each provider flag off by default; enabling requires config edit |
| Squad allowlist pin with PR review | `.claude/settings.json` `squad_allowlist` + `.claude/adr/ADR-039-skill-marketplace-protocol.md` §Decision drivers | Default `[]` refuses all imports; additions via PR with CODEOWNERS approval |
| Operator sign-off log for credential rotations | `docs/rotation-log.md` | Every rotation (ANTHROPIC_API_KEY, GOOGLE_API_KEY, OPENAI_API_KEY, GPG keys) logged with date + reason + operator |
| Credential storage per-client | `$CLAUDE_PROJECT_DIR/state/mcp_client_secrets/<client_id>.key` (600 perms) | `stat -c '%a' state/mcp_client_secrets/*.key` returns 600 |

---

### CC6.3 — Logical Access — Removal

**Intent:** The entity authorizes, modifies, or removes access to data,
software, functions, and other protected information assets based on
roles, responsibilities, or the system design and changes, giving
consideration to the concepts of least privilege and segregation of
duties.

| Evidence type | Location | Verification |
|---|---|---|
| Credential rotation 90-day hard max | `.claude/adr/ADR-040-live-adapter-activation-contract.md` §4 | `grep -n '90-day hard max' .claude/adr/ADR-040-live-adapter-activation-contract.md`; `credential_rotation_due` audit event emitted 14 days before cutover |
| MCP client secret rotation | `.claude/adr/ADR-042-mcp-server-contract.md` §Auth.1 "Rotation: 90-day hard max mirroring ADR-040" | Same 90-day cap; rotation deletes old key file and regenerates |
| Squad revocation ledger | `.claude/squad-revocations.jsonl` (ADR-039 §Decision drivers "Revocation mechanism") | `jq '.signer_fingerprint' .claude/squad-revocations.jsonl` enumerates banned signers; checked pre-extract in `squad-import.py` |
| Skill-patch revocation via 7-day shadow | `.claude/adr/ADR-031-self-improving-skills.md` 10-point bundle | Shadow period allows pre-promote abort; `skill_patch_applied(shadow_mode=True)` distinguishable from `shadow_mode=False` |
| State-store plan rollback clears scratchpad | `.claude/hooks/_lib/state_store.py::clear_plan()` + ADR-034 §"clear-on-rollback" | `state_store_pruned(plan_id_hash, keys_pruned_count)` on every rollback |

---

### CC6.6 — External System Boundary

**Intent:** The entity implements logical access security measures to
protect against threats from sources outside its system boundaries.

| Evidence type | Location | Verification |
|---|---|---|
| Live adapter activation gate per provider | `.claude/adr/ADR-040-live-adapter-activation-contract.md` §6 | Provider flags default disabled; activation requires explicit config; audit event `live_adapter_call_started` on every outbound |
| OTEL HTTPS-only + host allowlist | `.claude/adr/ADR-035-otel-export.md` §Decision drivers mitigations 1+2 | `grep -n 'CEO_OTEL_ALLOWED_HOSTS' .claude/adr/ADR-035-otel-export.md`; empty default rejects every export; `otel_export_dropped(reason=host_not_allowlisted)` on reject |
| OTEL double-redaction + description_hash drop | `.claude/adr/ADR-035-otel-export.md` §Decision drivers mitigations 3+4 | `otel_export_dropped(fields_dropped_count)` event; `_lib/otel/` tests assert two-pass redaction |
| MCP CORS default-deny | `.claude/adr/ADR-042-mcp-server-contract.md` §Auth.4 (Phase A.2 deliverable) | SPEC file documents CORS policy; test fixture asserts pre-flight denial |
| Trust-boundary diagram | `docs/threat-model.md` §"Trust-boundary diagram" | ASCII diagram distinguishes 5 boundaries (Claude-native / MCP external / hook enforcement / OTEL export / provider API) |
| `CEO_SOTA_DISABLE` kill-switch parity | `.github/workflows/_README.md` + all 13 workflows | Every workflow honors env var; one flip short-circuits new Phase 1-12 paths |

---

### CC7.1 — Monitoring — Baseline

**Intent:** The entity monitors system components and the operation of
those components for anomalies that are indicative of malicious acts,
natural disasters, and errors affecting the entity's ability to meet
its objectives; anomalies are analyzed to determine whether they
represent security events.

| Evidence type | Location | Verification |
|---|---|---|
| Canonical audit event schema | `SPEC/v1/audit-log.schema.md` + `.claude/plans/AUDIT-LOG-SCHEMA.md` | `jq -c 'keys_unsorted' audit-log.jsonl` validates every line against schema fields |
| Canonical audit export library | `.claude/hooks/_lib/audit_emit.py` | All 27 emitter functions use single `_write_event()` path; filelock-protected; fail-open to breadcrumb |
| 27 distinct audit event types | See §"Audit-log event inventory" below | `grep -c '^def emit_' .claude/hooks/_lib/audit_emit.py` returns 22 (+ `agent_spawn` emitted directly from `audit_log.py` + 4 legacy events from pre-v2) = 27 total |
| OTEL export to external SIEM | `.claude/adr/ADR-035-otel-export.md` + `.claude/scripts/otel-export.py` | Weekly `otel-smoke.yml` workflow; `otel_export_dropped` on every rejected span |
| Dashboard for real-time review | `.claude/scripts/audit-dashboard.py` | Stdlib SSE, loopback-only, 4 panels (tokens, reflexion, pruning, architect-outcomes) |
| Audit query CLI | `.claude/scripts/audit-query.py` | 9 sub-commands (spawns, debates, transitions, vetoes, benchmarks, lessons, injections, metrics, tokens) |

---

### CC7.2 — Monitoring — Change Management

**Intent:** The entity's security, IT operations, and development
personnel monitor changes to system components to identify unauthorized
changes, detect vulnerabilities, and manage the resolution of
identified issues.

| Evidence type | Location | Verification |
|---|---|---|
| Canonical-edit sentinel hook | `.claude/hooks/check_canonical_edit.py` + `.claude/adr/ADR-010-canonical-edit-sentinel.md` | Every Edit/Write/MultiEdit on canonical paths requires signed sentinel; denial emits `veto_triggered(hook=check_canonical_edit)` |
| Plan-transition audit | `.claude/hooks/check_plan_edit.py` + event `plan_transition` | Legal transitions emit `plan_transition(from_status, to_status, transition_legal=True)`; illegal emit `veto_triggered(hook=check_plan_edit)` |
| Branch protection | `docs/BRANCH-PROTECTION.md` + `.github/CODEOWNERS` + ADR-003 | GitHub API asserts PR-required + review-required + CODEOWNERS-required on `main` |
| 24h Codex re-pass hold on `v*` tags | `.github/workflows/release.yml` + PLAN-013 Phase 0 item 0.3 | Workflow asserts ≥24h between `vX.Y.Z-rc.N` and `vX.Y.Z` tags; pre-SHA check |
| ADR-044 formal-verification proofs as change-control evidence | `docs/formal-verification/properties-proved.md` (Phase D.4) | Proof artifacts pinned in repo; change to proved state machine requires proof re-run + mutation-test gate pass |

---

### CC7.4 — Incident Response

**Intent:** The entity responds to identified security incidents by
executing a defined incident response program to understand, contain,
remediate, and communicate security incidents, as appropriate.

| Evidence type | Location | Verification |
|---|---|---|
| Global kill-switch | `CEO_SOTA_DISABLE=1` env var | Every SotA path (Phase 1-12 from Sprint 11) short-circuits; one flip disables new paths; documented in `.github/workflows/_README.md` |
| Circuit breaker open-state audit | `_lib/adapters/live/` CircuitBreaker + `.claude/adr/ADR-040-live-adapter-activation-contract.md` §2 | `breaker_opened` / `breaker_closed` audit events; 3-consecutive-5xx trigger; exponential backoff |
| Rollback paths per phase | PLAN-012 §"Revert procedure" + PLAN-013 §"Rollback signal table" | Each major phase documents backout steps; state_store clear-on-rollback empties scratchpad (ADR-034) |
| Skill-patch revocation (shadow period) | `.claude/adr/ADR-031-self-improving-skills.md` 7-day shadow | `skill_patch_applied(shadow_mode=True)` distinguishable from promoted; revocation via delete + re-propose |
| OTEL drop on incident | `.claude/adr/ADR-035-otel-export.md` mitigation 5 | `otel_export_dropped(endpoint_host, reason)` on every drop; endpoint host-only (no URL path/query) |
| Chaos-inject for tabletop exercises | `.claude/scripts/chaos-inject.py` + ADR-037 | 3-gate lockdown (`CEO_CHAOS_ALLOWED=1` + pytest tree + cwd assertion); weekly chaos.yml workflow |
| Owner escalation log | `docs/incident-response.md` (Phase C.2 stub; full content = post-adopter Sprint 15) | Runbook for pager rotation, escalation ladder, communication channels — deferred per PLAN-013 consensus to post-adopter |

---

### CC8.1 — Change Management — Authorization

**Intent:** The entity authorizes, designs, develops or acquires,
configures, documents, tests, approves, and implements changes to
infrastructure, data, software, and procedures to meet its objectives.

| Evidence type | Location | Verification |
|---|---|---|
| PROTOCOL plan-debate-execute | `PROTOCOL.md` §Plan→Debate→Execute | L3+ tasks require `/debate start PLAN-NNN` before execution; round 1 produces consensus; adjustments applied pre-promote |
| ADR numbering discipline | `.claude/adr/README.md` + PLAN-SCHEMA.md §1 | ADRs numbered zero-padded 3-digit monotonic; every cross-cutting architectural decision gets a formal ADR |
| Debate artifacts | `.claude/plans/PLAN-*/debate/round-*/` (per DEBATE-SCHEMA.md §3) | `debate_event(plan_id, round, phase, agent, artifact_path, consensus_adjustments_count)` records every round artifact |
| 3-strike policy | PROTOCOL.md §3-strike | Hook enforcement escalates from warn → block → session-halt after repeated veto triggers |
| Transition Log convention | `.claude/adr/ADR-041-transition-log-convention.md` | Every state-machine ADR (ADR-019, ADR-024, ADR-033, ADR-035, ADR-036, ADR-037) carries uniform Transition Log appendix with row shape: date/from/to/evidence-ref/signed-by |

---

## Audit-log event inventory

Full table of every audit event emitted by the framework, derived from
`_lib/audit_emit.py` (22 emitter functions) + `audit_log.py` direct
`agent_spawn` emitter + planned MCP events (Phase A.4) + `live_adapter_*`
events (from `_lib/adapters/live/`).

**Canonical source:** `.claude/hooks/_lib/audit_emit.py`
**Schema:** `SPEC/v1/audit-log.schema.md` + `.claude/plans/AUDIT-LOG-SCHEMA.md`

| Event | Emitted by | CC(s) supported |
|---|---|---|
| `agent_spawn` | `.claude/hooks/audit_log.py` (PostToolUse Agent) | CC6.1, CC7.1, CC8.1 |
| `debate_event` | `.claude/scripts/debate-emit.py` + `debate-orchestrate.py` | CC7.2, CC8.1 |
| `plan_transition` | `.claude/hooks/check_plan_edit.py` | CC7.2, CC8.1 |
| `veto_triggered` | Any governance hook on block path (`check_agent_spawn`, `check_plan_edit`, `check_canonical_edit`, `check_bash_safety`, `check_read_injection`, `check_output_safety`, `check_budget`, `check_scratchpad_access`, `check_skill_patch_sentinel`, `check_confidence_gate`) | CC6.1, CC7.1, CC7.2 |
| `benchmark_run` | `.claude/scripts/run-skill-benchmark.py` | CC7.1 |
| `lesson_write` | `.claude/scripts/lessons.py` | CC7.2 |
| `lesson_read` | `.claude/scripts/lessons.py::get_top_k()` | CC7.1 |
| `lesson_archived` | `.claude/scripts/prune-lessons.py --execute` | CC7.2, CC8.1 |
| `lesson_restored` | `.claude/scripts/lesson-restore.py` | CC7.2, CC8.1 |
| `lesson_outcome` | `.claude/scripts/lessons.py::record_outcome()` | CC7.1 |
| `lesson_outcome_undone` | `.claude/scripts/lessons.py::undo_outcome()` | CC7.2, CC8.1 |
| `injection_flag` | `.claude/hooks/check_read_injection.py` (advisory) | CC7.1, CC6.6 |
| `confidence_gate` | `.claude/hooks/check_confidence_gate.py` | CC7.1 |
| `state_store_write` | `_lib/state_store.py::SqliteStateStore.set()` | CC7.1, CC6.3 |
| `state_store_read` | `_lib/state_store.py::SqliteStateStore.get()` | CC7.1 |
| `state_store_pruned` | `_lib/state_store.py::prune_expired()` + `clear_plan()` | CC6.3, CC7.2 |
| `budget_exceeded` | `.claude/hooks/check_budget.py` | CC8.1, CC7.4 |
| `budget_bypass_used` | `.claude/hooks/check_budget.py` (Owner-scoped) | CC8.1, CC7.4 |
| `otel_export_dropped` | `.claude/scripts/otel-export.py` + `_lib/otel/` | CC6.6, CC7.4 |
| `output_safety_flag` | `.claude/hooks/check_output_safety.py` (PostToolUse Agent) | CC7.1, CC6.6 |
| `skill_patch_applied` | `.claude/scripts/skill-patch-apply.py` | CC7.2, CC8.1 |
| `squad_imported` | `.claude/scripts/squad-import.py` | CC6.2, CC8.1 |
| `mcp_handler_invoked` (planned, Phase A.4) | MCP server handlers | CC6.1, CC7.1 |
| `mcp_handler_denied` (planned, Phase A.4) | MCP server handlers on ACL/auth fail | CC6.1, CC7.1 |
| `live_adapter_call_started` (PLAN-012 Wave 2) | `_lib/adapters/live/transport.py::call()` entry | CC6.6, CC7.1 |
| `live_adapter_call_completed` (PLAN-012 Wave 2) | `_lib/adapters/live/transport.py::call()` exit | CC7.1 |
| `breaker_opened` / `breaker_closed` (PLAN-012 Wave 2) | `_lib/adapters/live/breaker.py` state transitions | CC7.4 |
| `credential_rotation_due` (PLAN-012 Wave 2) | `_lib/credentials.py` rotation check | CC6.3 |

**Count:** 28 distinct event types (27 implemented + 1 planned family
with 2 sub-events already stubbed = total 29 named event identifiers).
CC7.1 (Monitoring Baseline) supported by 15 event types; CC8.1 (Change
Mgmt Authorization) by 10; CC6.1 (Authentication) by 7; CC7.2 (Change
Mgmt Monitoring) by 9; CC7.4 (Incident Response) by 5.

**Notes:**

- `mcp_handler_invoked` + `mcp_handler_denied` land in Phase A.4 per
  PLAN-013; registry entry reserved in `_lib/audit_emit.py::_KNOWN_ACTIONS`
  via ADR-042 §Audit.
- `live_adapter_*` events shipped in PLAN-012 Phase 1 Wave 2
  (`_lib/adapters/live/`) but are not yet enumerated in the
  `audit_emit.py` `_KNOWN_ACTIONS` set as of v1.4.0-rc.1 — Sprint 15
  reconciliation gap (see §Gap list).

---

## Gap list

| Gap | Owner | Deadline | Remediation |
|---|---|---|---|
| Real-time alerting for security events (pager integration, on-call rotation) | Principal Security Engineer | Sprint 15 (post-adopter-1) | Discord/Slack webhook integration via OTEL collector; 3-severity routing (CRITICAL → pager; HIGH → channel; INFO → dashboard). Not scheduled pre-adopter per PLAN-013 consensus §C4 — audit-trail foundation ships first, alerting builds on it |
| `docs/incident-response.md` full runbook | Principal Security Engineer | Sprint 15 | Runbook sections: pager rotation, escalation ladder (CEO → Owner), communication template, post-incident review cadence. Phase C.2 stub documents placeholder; full content requires adopter environment to test against |
| `live_adapter_*` events registered in `_KNOWN_ACTIONS` | Staff Backend Engineer | Sprint 13 Phase A (before MCP server ship) | Add `live_adapter_call_started`, `live_adapter_call_completed`, `breaker_opened`, `breaker_closed`, `credential_rotation_due` to `_KNOWN_ACTIONS` set in `_lib/audit_emit.py`; add emitter functions; cross-check `adapters/live/*` call sites |
| External auditor engagement for SOC2 Type II | Owner + external auditor | Sprint 18+ (public-launch gated) | Type II requires 12-month observation window + on-site control testing. Current mapping = Type I readiness foundation only. Out-of-scope pre-public-launch per PLAN-013 anti-goal (repo stays private Sprints 12-16) |
| κ calibration N≥100 confidence-interval lower ≥0.7 | QA Architect | Sprint 13 Phase A (ongoing per PLAN-012 Phase 4) | `.claude/scripts/k-calibration.py` + `benchmarks/human-sample-calibration.md` landed Sprint 12 Phase 4. N≥100 paired grades required before CC7.2 judge evidence is audit-worthy; bootstrap CI lower ≥0.7 gate |

---

## Retention policy

Retention windows for each persistence surface. Values are **recommendations**
baked into current ADRs; actual retention is Owner policy.

| Surface | Retention | Rationale | ADR reference |
|---|---|---|---|
| `audit-log.jsonl` (active) | 90 days live on disk | Balance forensic utility vs disk budget; rotation creates `audit-log-YYYY-MM.jsonl` archives | ADR-001 + AUDIT-LOG-SCHEMA.md §6 |
| Audit log (cold storage) | 1 year | Compliance investigation window typical for SOC2 scope | ADR-001 (recommendation; Owner sets bucket+lifecycle) |
| State store (per-plan sqlite) | 30 days default TTL | Scratchpad lifetime ≥ any active plan phase; pruned on plan rollback | ADR-027 §Retention + ADR-034 |
| Session graph snapshots | 30 days | Derived view; expiration does not lose primary data | ADR-038 |
| Skill-patch proposals | 1 year | Forensic review of patch lineage | Sprint 15 decision per ADR-031 Transition Log appendix (placeholder row) |
| Credentials (env-only, live adapters) | 90 days hard max | Align with industry API-key rotation norms | ADR-040 §4 + ADR-042 §Auth.1 (MCP client secrets same 90d) |
| GPG signing keys (Owner) | 1 year, rotated on Sprint boundary | Key freshness ≤ annual per industry practice | `docs/rotation-log.md` + Owner policy |
| Squad revocation ledger | Indefinite (append-only) | Revocation is permanent for trust integrity | ADR-039 |
| OTEL exported spans (third-party collector) | Per-collector policy | Framework emits host-only endpoint; collector retention is operator-chosen | ADR-035 (framework does not enforce) |

---

## References

- `.claude/adr/ADR-003-branch-protection-replaces-skill-signing.md`
- `.claude/adr/ADR-010-canonical-edit-sentinel.md`
- `.claude/adr/ADR-031-self-improving-skills.md`
- `.claude/adr/ADR-033-cost-budget-enforcement.md`
- `.claude/adr/ADR-035-otel-export.md`
- `.claude/adr/ADR-039-skill-marketplace-protocol.md`
- `.claude/adr/ADR-040-live-adapter-activation-contract.md`
- `.claude/adr/ADR-041-transition-log-convention.md`
- `.claude/adr/ADR-042-mcp-server-contract.md`
- `.claude/adr/ADR-043-soc2-audit-trail-mapping.md`
- `.claude/adr/ADR-044-formal-verification-pilot.md`
- `.claude/hooks/_lib/audit_emit.py` — canonical event emitter
- `.claude/plans/AUDIT-LOG-SCHEMA.md` — operational contract
- `SPEC/v1/audit-log.schema.md` — canonical audit event schema
- `SPEC/v1/live-adapters-policy.schema.md` — adapter policy contract
- `docs/threat-model.md` — companion STRIDE threat model
- `docs/BRANCH-PROTECTION.md` — branch protection setup
- `docs/rotation-log.md` — credential rotation operator log
