# ADR-042-AMEND-1 — Read-only MCP tools expansion (PLAN-096)

---
adr_id: ADR-042-AMEND-1
title: Read-only MCP tools expansion — audit-query + plan-status + debate-state + cost-budget
status: ACCEPTED
amends: ADR-042
proposed_at: 2026-05-17
proposed_by: CEO (PLAN-096 execute-session)
session_origin: S130
risk_tier: A
related_plans: [PLAN-096, PLAN-052, PLAN-070, PLAN-102]
target_tag: v1.29.0
accepted_at: 2026-05-20
accepting_session: S147
---

## §1 Scope

This amendment extends ADR-042 §Auth.2 (handler ACL inventory) and §Auth.3
(per-class rate-bucket table) to cover the **33 new read-only MCP
methods** shipped in v1.29.0 by PLAN-096. NO write-capable surface is
introduced; every new method inherits the `read_only=True` invariant
documented in §3 below.

Out of scope:

- Write-capable handlers (would require ADR-042-AMEND-2 with separate
  security-engineer + identity-trust-architect VETO per PLAN-099
  federation-contract precedent).
- HTTP-stream transport (stdio JSON-RPC remains the v1.29.0 baseline per
  AC-T-2; locked in `.claude/plans/PLAN-096/wave-a-mcp-subset.md` §4).
- Live cost-envelope data path (stub-mode until PLAN-102 lands).

## §2 Handler inventory delta

### §2.1 Wave A — audit-query namespace (27 methods)

All routed to the `audit_read` class (existing). One handler per source
sub-command from `audit-query.py`, EXCEPT `label` which is excluded per
`wave-a-mcp-subset.md` §3 because it appends to an HMAC-chained store.

Enumeration locked at execute-time; method-count contract enforced by
`tests/integration/test_mcp_audit_query.py::test_method_count_matches_source`.

### §2.2 Wave B — plan-status namespace (4 methods)

Class: `readonly` (existing, 60 rpm / burst 10).

- `list_plans(status=None)` — frontmatter summaries; optional status filter.
- `get_plan(plan_id)` — full frontmatter for one plan.
- `get_plan_acs(plan_id)` — parsed Acceptance Criteria list.
- `get_plan_dependencies(plan_id)` — depends_on + external_wait arrays.

Source of truth: `.claude/plans/PLAN-NNN-<slug>.md` frontmatter (lightweight
YAML-ish parser; no write surface).

### §2.3 Wave C — debate-state namespace (1 method)

Class: `debate_read` (NEW; 10 rpm / burst 3).

- `get_debate_state(plan_id)` — snapshot-only AFTER debate sentinel
  `.asc` lands (mid-debate vote-text body NEVER serialized; AC4).

The new `debate_read` class enforces a lower budget than `readonly`
because debate snapshots are immutable post-sentinel — caller polling
beyond a few times per minute is a misuse signal.

### §2.4 Wave D — cost-budget namespace (1 method)

Class: `cost_budget` (NEW; 30 rpm / burst 5).

- `get_cost_budget(scope='caller'|'aggregate', target_client_id=None)` —
  stub-mode pre-PLAN-102; returns `{"status":"unwired","plan_dep":"PLAN-102"}`.

Cross-tenant isolation invariant (AC-C-3): `scope=caller` with a
`target_client_id` differing from the caller's own client_id is denied
with reason `cross_tenant` (`-32002` ACL fault code).

## §3 Read-only invariant (AC-R-1)

Every new handler MUST:

1. **Reject forged-write params** at handler entry. The conservative
   denylist substrings are: `label`, `write`, `append`, `output_path`,
   `out_path`, `store`, `patch`. Any matching param routes to
   `read_only_violation` with `-32602` (InvalidParams).
2. **Emit `mcp_handler_denied`** via the existing
   `audit_emit.emit_mcp_handler_denied` path with `reason` ∈ the
   closed enum extended by this amendment:
   - `read_only_violation` (new, this amendment)
   - `cross_tenant` (new, this amendment)
3. **Make no disk write** beyond the existing audit-log append (which is
   not handler-driven; the audit subsystem appends after handler return).

Test enforcement: `tests/integration/test_mcp_readonly_invariant.py`
asserts disk SHA stability across every handler under 6 forged-write
param shapes.

## §4 ACL allowlist update (`.claude/settings.json`)

The `mcp_client_registry.<client_id>.handlers` array gains 33 new
entries. NO wildcard (`"*"`) is permitted — `auth.check_acl` continues
to fail-closed on any wildcard, per ADR-042 §Auth.2 normative.

Default registry seed (template for adopters):

```json
"mcp_client_registry": {
  "<client_id_hex16>": {
    "handlers": [
      "list_skills", "get_skill", "list_agents", "list_pitfalls",
      "get_audit_log", "spawn_agent", "server.capabilities",
      "list_plans", "get_plan", "get_plan_acs", "get_plan_dependencies",
      "get_debate_state", "get_cost_budget",
      "audit_query.summary", "audit_query.by_skill", "audit_query.compliance",
      "audit_query.by_day", "audit_query.search", "audit_query.since",
      "audit_query.errors", "audit_query.stats", "audit_query.export",
      "audit_query.debate", "audit_query.plans", "audit_query.vetoes",
      "audit_query.benchmarks", "audit_query.lessons", "audit_query.metrics",
      "audit_query.health", "audit_query.tokens", "audit_query.claims",
      "audit_query.prune_restore_ratio", "audit_query.architect_outcomes",
      "audit_query.lessons_effectiveness", "audit_query.weekly_summary",
      "audit_query.spawn_stats", "audit_query.by_domain", "audit_query.fp_rate",
      "audit_query.case_summary", "audit_query.codex_writeguard_summary"
    ]
  }
}
```

Total: 7 baseline + 33 new = **40 ACL entries**.

## §5 Rate-bucket table (§Auth.3 extension)

| Class | rpm | burst | Used by |
|---|---|---|---|
| readonly | 60 | 10 | list_skills, get_skill, list_agents, list_pitfalls, server.capabilities, list_plans, get_plan, get_plan_acs, get_plan_dependencies |
| audit_read | 30 | 5 | get_audit_log, audit_query.* (27 methods) |
| spawn | 6 | 2 | spawn_agent |
| **debate_read** | **10** | **3** | **get_debate_state** (NEW) |
| **cost_budget** | **30** | **5** | **get_cost_budget** (NEW) |

## §6 Audit-emit actions

### §6.1 Existing actions reused (AC6)

- `mcp_handler_invoked` — fires on every successful new-handler entry
  (Wave A/B/C/D unchanged from ADR-042 §Auth).
- `mcp_handler_denied` — fires on every denial path. The closed-enum
  `reason` field is extended with two values in §3 above.

### §6.2 New actions

| Action | Fields | Trigger |
|---|---|---|
| `mcp_cross_tenant_denied` | handler, caller_client_id_hash, target_client_id_hash, transport, session_id, project | `get_cost_budget` with `scope=caller` + `target_client_id != caller` |
| `mcp_soak_fpr_breach` | window_days, fpr_observed, threshold, top_deny_reason, session_id, project | 7-day rolling FPR > 1% (AC-F-4); fires once per breach day |

Both actions follow Sec MF-3 hygiene: caller-supplied opaque
identifiers are HASHED via `auth.hash_client_id` before serialization
into the audit log.

## §7 30d soak observability (AC6 + AC-F-4)

Counter source: `audit_query search 'mcp_handler_invoked|mcp_handler_denied'`.

Rolling-window computation (per `.claude/plans/PLAN-096/soak-report-template.md`):

- Window: 7 calendar days.
- Threshold: 1.00% FPR (mirrors PLAN-052 `soak_target_fpr: 0.01`).
- Breach action: emit `mcp_soak_fpr_breach`; file
  PLAN-096-FOLLOWUP-soak-breach.

Decision gate at 30d close determines whether PLAN-097/098/099 unblock
or whether ADR-042-AMEND-2 / rollback PR is filed.

## §8 Kill-switch

Adopters may disable the entire v1.29.0 handler expansion via
environment variable `CEO_MCP_READONLY_TOOLS_ENABLED=0`. The dispatcher
returns `method_not_found` (`-32601`) for every Wave A/B/C/D method
when the kill-switch is set. Baseline handlers from ADR-042 §Auth.2
remain operational.

This is the Tier-A reversal predicate per ADR-125 §criterion-3
(single env-var kill-switch).

## §9 Backwards compatibility

100% additive. No existing handler signature changes. No existing
audit-emit field changes. Baseline 7 handlers continue to operate
exactly as defined in ADR-042. The two new closed-enum `reason`
values are append-only — existing parsers that switch on a default
arm continue to handle them.

## §10 Ship gates (AC-S-6)

- 3-iter Codex R2 ACCEPT on this draft (sentinel
  `.claude/plans/PLAN-096/approved.md.asc` Owner-GPG-signed).
- Hook test suite passes (no new test failures).
- Tests/integration/test_mcp_*.py 55+ pass.
- Method count contract verified at CI time.

## §11 Rollback plan

Single-revert PR strategy:

1. Revert the `dispatch.py` HANDLERS entries (5-line patch).
2. Revert `rate_limit.py` HANDLER_CLASS additions.
3. Restore `settings.json` ACL allowlist to pre-AMEND-1 baseline.
4. Optional: leave handler files in place (dead code; harmless).

No data migration needed (stub-mode cost-budget; in-memory rate-limit
buckets reset on process restart).
