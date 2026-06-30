# SPEC v1 — audit-log.schema

> **Normative source:** `.claude/plans/AUDIT-LOG-SCHEMA.md`
> **Spec version:** 1.0.0-rc.1

## Summary (normative)

Append-only JSONL event stream at (out-of-repo):

```
${CEO_AUDIT_LOG_PATH:-$HOME/.claude/projects/ceo-orchestration/audit-log.jsonl}
```

### Schema versions

- **v1:** one action `agent_spawn`. Emitted by `audit_log.py` PostToolUse
  Agent hook. No `event_schema` field (absence IS the v1 marker).
- **v2:** six known actions (`agent_spawn`, `debate_event`,
  `plan_transition`, `veto_triggered`, `benchmark_run`, `lesson_write`).
  All v2 events carry `event_schema: "v2"` + `ts` + nullable
  `tokens_in` / `tokens_out` / `tokens_total`.
- **v2.1:** adds one action `injection_flag` (advisory; ADR-011). The
  `event_schema` value remains `v2` — consumers tolerating unknown
  actions are unaffected.
- **v2.2 (PLAN-008, Sprint 8):** adds four actions — `confidence_gate`
  (ADR-018), `lesson_read`, `lesson_archived`, `lesson_restored`
  (ADR-017 amendment). Plus `lesson_outcome` (ADR-015, Sprint 6) is
  formally registered. `event_schema` value remains `v2` (additive).
- **v2.2.1 (PLAN-009 Phase 1 C1.0, Sprint 9):** additive fields on
  `confidence_gate` — `raw_claim_count` (int) and `truncated` (bool).
  Populated when the input exceeded `CEO_CONFIDENCE_MAX_CLAIMS` (default
  200). `event_schema` remains `v2` (MINOR bump within v1).
- **v2.2.2 (PLAN-009 Phase 3 P3.5, Sprint 9):** `lesson_outcome` gains
  closed-enum `consumer` field (`"benchmark" | "architect"`) plus
  `inference_mode`, `window_duration_seconds`, `session_end_reason`.
  Pre-Sprint-9 events missing `consumer` MUST be parsed as
  `"benchmark"` (A23 back-compat).
- **v2.3 (PLAN-009 Phase 3 P3.3, Sprint 9):** new action
  `lesson_outcome_undone` — admin-facing escape hatch for reversing a
  bad Architect attribution. `event_schema` remains `v2`.
- **v2.4 (PLAN-011 Phase 0, Sprint 11):** three new actions —
  `state_store_write`, `state_store_read`, `state_store_pruned`
  (ADR-027). `event_schema` remains `v2` (additive). See
  `SPEC/v1/state-stores.schema.md` for the unified state-backend
  envelope these events describe. **Consolidation policy (consensus
  H11):** all PLAN-011 audit additions (`state_store_*`,
  `budget_exceeded`, `budget_bypass_used`, `otel_export_dropped`,
  `output_safety_flag`, `skill_patch_applied`, `squad_imported`) land
  in a single v2.4 bump — this entry will be amended during Phase 13
  closeout to enumerate the final set.
- **v2.5 (PLAN-013 Phase A.0 + Phase A, Sprint 13):** ten new actions —
  **Six live-adapter / breaker / credential events** (Gap #3 fix per
  PLAN-013 progress-log.md Session 20 — events emitted by
  `_lib/adapters/live/_transport.py` on_audit callback + planned
  `_breaker.py` + `_credentials` wiring but not registered in
  `_KNOWN_ACTIONS`): `live_adapter_call_started`,
  `live_adapter_call_succeeded`, `live_adapter_call_failed`,
  `breaker_opened`, `breaker_closed`, `credential_rotation_due` (ADR-040
  §2/§4/§7). **Four MCP server events** (ADR-042): `mcp_handler_invoked`
  (§Auth — entry audit), `mcp_handler_denied` (§Auth.5 — deny-path
  audit), `mcp_server_started` (§Cost.4 — startup observability),
  `mcp_server_disabled_by_kill_switch` (§Cost.4 — CEO_SOTA_DISABLE
  short-circuit). `event_schema` remains `v2` (additive).
- **v2.9 (PLAN-023 Phase B, Sprint 23 — ADR-055):** two **additive**
  nullable fields for HMAC chain tamper detection:
  - `hmac` (string|null) — 64 hex chars (SHA-256). Null if chain
    disabled (`CEO_AUDIT_HMAC_DISABLE=1`), pre-v2.9 emitter, or
    key-read failure (in which case `hmac_error` is set).
  - `hmac_error` (string|null) — Python exception class name on
    compute failure; null otherwise.
  Chain formula: `hmac = hmac_sha256(key, prev_hmac ||
  canonical_json(entry_sans_hmac))` where canonical_json is
  `_lib/canonical_json.py::encode` (pinned kwargs, NFC strings, no
  floats). Sidecar `audit-log.last-hmac` holds the last digest
  (best-effort; reconstructible from log tail). Key at
  `~/.claude/projects/<slug>/audit-key` (0600, 32 random bytes,
  auto-generated). Transition-entry rule is one-way (hmac-less after
  hmac-bearing = tamper). Chain resets on log rotation (per-file).
  `event_schema` remains `v2` (additive). Verifier:
  `.claude/scripts/audit-verify-chain.py`; exit 0/1/2/3/4 contract.
  Defends: forgery / reorder / interior deletion / transition
  violation. Does NOT defend: tail truncation / key theft / rollback
  / log+key co-deletion. See ADR-055 §Threat Model §Out-of-scope for
  the complete residual list.
- **v2.6 (PLAN-014 Phase 0.6, Sprint 14):** twelve new actions per
  ADJ-010 (registered BEFORE Phase A/F spawns to prevent mid-flight
  agent divergence on event names):
  **Three policy-engine events** (ADR-045 + SPEC/v1/policy-dsl.schema.md):
  `policy_evaluated`, `policy_denied`, `policy_error`.
  **Three replay events** (ADR-046 + SPEC/v1/replay.schema.md):
  `replay_started`, `replay_completed`, `replay_diff_produced`.
  **One predict-budget event** (ADR-047 + SPEC/v1/predict-budget.schema.md):
  `prediction_queried`.
  **Three cross-plan-memory events** (ADR-048 + SPEC/v1/memory-shared.schema.md):
  `pattern_stored`, `pattern_queried`, `pattern_evicted`.
  **Two threat-model governance events**: `threat_model_promoted`,
  `threat_model_freshness_breach`. `event_schema` remains `v2` (additive).
- **v2.41 (PLAN-133, Goose-harvest):** nineteen new actions —
  `env_var_hijack_blocked`, `invisible_unicode_blocked`,
  `egress_destination_detected`, `quota_exhausted`, `eval_task_completed`,
  `context_auto_compacted`, `context_auto_compact_suppressed`,
  `context_middle_out_degraded`, `context_middle_out_degrade_failed`,
  `adversary_review_flagged`, `supply_chain_advisory_emitted`,
  `spawn_tool_scope_violation`, `spawn_depth_or_overlap_blocked`,
  `spawn_file_assignment_recorded`, `action_required_held`,
  `action_required_resumed`, `action_required_rejected`,
  `persistent_instructions_blocked`, `hint_provenance_recorded`. Each is a
  closed-enum / hash / bucketed-int breadcrumb routed through a dedicated
  deny-by-default per-action allowlist in `audit_emit.py` (NEVER
  `_EMIT_GENERIC_PASSTHROUGH`); an out-of-enum value is COERCED to a safe
  sentinel before emit (S172 doctrine, never echoed). `event_schema`
  remains `v2`. Additive per SPEC/v1 rules.
- **v2.42 (PLAN-135 W1 S3, anthropic-surface-harvest):** one new action —
  `settings_tamper_detected`, the `/ceo-boot` Tier-S settings/env
  tamper-tripwire breadcrumb (one emit per tamper class detected on the
  RESOLVED multi-layer settings + import-time env snapshot). Closed-enum
  `tamper_class` (mirrors `_lib/effective_config.TAMPER_CLASSES`) +
  closed-enum `layer` + clamped-int `finding_count`; dedicated
  deny-by-default allowlist `_SETTINGS_TAMPER_DETECTED_ALLOWLIST` (NEVER
  `_EMIT_GENERIC_PASSTHROUGH`); the finding detail / env values are never
  persisted. `event_schema` remains `v2`. Additive per SPEC/v1 rules.
- **v2.43 (PLAN-135 W2, anthropic-surface-harvest hook wave):** new actions
  for the W2 new-event hooks — H2 contributes the ConfigChange-guard pair
  `config_change_observed` + `config_change_forbidden_key`
  (`check_config_change.py`: audit + advisory-block of out-of-band
  settings edits, the S197 class; forbidden-keys single source =
  `_lib/effective_config.FORBIDDEN_KEYS`, shared with W1 S3). Closed-enum
  `layer` (settings file surfaces only: `user` / `project` / `local` /
  `managed` / `other`) on both; the forbidden-key event adds closed-enum
  `tamper_class` (mirrors `_lib/effective_config.TAMPER_CLASSES`) +
  clamped-int `finding_count`. Dedicated deny-by-default allowlists
  `_CONFIG_CHANGE_OBSERVED_ALLOWLIST` /
  `_CONFIG_CHANGE_FORBIDDEN_KEY_ALLOWLIST` (NEVER
  `_EMIT_GENERIC_PASSTHROUGH`); the changed file's path/body and any key
  VALUE are never persisted. H5 (ADR-154 single-rewriter) contributes
  `bash_input_rewritten` — `check_bash_safety.py` rewrote a `git push
  --force`/`-f` Bash input to `--force-with-lease` via the PreToolUse
  `updatedInput` channel (surfaced as an `ask`, never a silent allow); the
  ONLY caller fields are closed-enum `rewrite_class` + the before/after
  sha256 hash PAIR (TYPED wrapper `emit_bash_input_rewritten`, dedicated
  `_BASH_INPUT_REWRITTEN_ALLOWLIST`, NEVER `_EMIT_GENERIC_PASSTHROUGH`); the
  command bytes are never persisted (the hash pair proves audited-cmd ==
  executed-cmd). H1 (ADR-153) contributes the compaction-continuity pair
  `compaction_continuity_snapshot` + `compaction_context_reinjected`. H3
  contributes `subagent_lifecycle_observed` — emitted ONCE per returning
  sub-agent by `check_fluency_nudge.py` (the SubagentStop H3 extension) after
  consuming the SubagentStart sidecar (`check_subagent_start.py`) + the
  harness `agent_transcript_path`: per-agent wall-time + token + claim
  bracket (the S227 `modelUsage` forensic reconstruction becomes a live hook
  emit; feeds the persona-ledger). EVERY wire field is a closed enum or
  coarse bucket — `agent_archetype` (persona-ledger archetype) + `wall_bucket`
  + `wall_source` + `token_bucket` + `claim_bucket`; the RAW token counts, RAW
  wall seconds, transcript path/body, marker snippets and raw agent_id are
  never persisted (TYPED wrapper `emit_subagent_lifecycle_observed`, dedicated
  `_SUBAGENT_LIFECYCLE_OBSERVED_ALLOWLIST`, NEVER `_EMIT_GENERIC_PASSTHROUGH`).
  Sibling W2 units' actions fold into this same v2.43 bump at the
  arc-verify wave. `event_schema` remains `v2`. Additive per SPEC/v1 rules.
- **v2.44 (PLAN-135 ARC, anthropic-surface-harvest W5 ops fold):** three new
  actions for the W5 ops surfaces, consolidated in the arc layer — `admin_key_lifecycle_event`
  (o9; `.claude/scripts/key-hygiene.py` Anthropic Admin API key-lifecycle
  breadcrumb), `statusline_sidecar_write` (o4; `.claude/scripts/statusline-ceo.py`
  statusLine sidecar-write breadcrumb), `model_refusal_observed` (o7;
  `.claude/hooks/_lib/adapters/live/claude.py` `_on_response` model-refusal
  breadcrumb). All three are TRUSTED first-party / adapter-library producers
  that PRE-REDACT at the emit site: `key-hygiene.py` `_redact()`s free text + emits
  only ids/counts/closed-enums (NEVER key material); `statusline-ceo.py` emits
  only numbers + enum-ish ids + a 12-char digest (NEVER the raw statusLine
  stdin); `claude.py` forwards ONLY the closed `stop_details.category` vocabulary
  (≤64) + provider/model slugs + status/duration ints and DROPS
  `stop_details.explanation` (model free text) at the emit site. `event_schema`
  remains `v2`. Additive per SPEC/v1 rules.
  _(Hardened in v2.45 — see below: these three no longer rely on producer-side
  pre-redaction alone; each now routes through a dedicated `_scrub_*` branch.)_
- **v2.45 (PLAN-135-FOLLOWUP, Codex R5 P1-2/P1-3):** no new actions, no new
  fields, `event_schema` remains `v2`. (1) **P1-2:** the three W5 actions
  (`admin_key_lifecycle_event`, `statusline_sidecar_write`, `model_refusal_observed`)
  move OFF `_EMIT_GENERIC_PASSTHROUGH` into dedicated deny-by-default `_scrub_*`
  branches (`_ADMIN_KEY_LIFECYCLE_EVENT_ALLOWLIST` / `_STATUSLINE_SIDECAR_WRITE_ALLOWLIST`
  / `_MODEL_REFUSAL_OBSERVED_ALLOWLIST`) with field-allowlist + enum/int VALUE
  coercion, so the Sec MF-3 boundary holds against a direct/future `emit_generic`
  caller that bypasses the trusted producer — producer-side pre-redaction is now
  defense-in-depth, not the sole line. (2) **P1-3:** one new closed-enum
  tamper-class member `settings_tamper_sidecar_redirect` (added to
  `settings_tamper_detected` + `config_change_forbidden_key`, mirroring
  `_lib/effective_config.TAMPER_CLASSES`) — a settings-LAYER `env` block setting
  `CEO_STATUSLINE_SIDECAR` to steer the always-on statusLine sidecar writer out of
  the audit/state dir (output/exfil-path steer; detected only in settings layers,
  the Owner launch-env override is legitimate). Additive per SPEC/v1 rules.

### Required fields per v2 action

| action | required fields |
|---|---|
| `agent_spawn` (v1) | `ts`, `action`, `session_id`, `project`, `tool`, `subagent_type`, `desc_preview`, `desc_hash`, `skill`, `has_profile`, `has_file_assignment`, `prompt_len_bucket`, `response_kind`, `hook_duration_ms` |
| `debate_event` | `action`, `plan_id`, `round`, `phase`, `agent`, `event_schema`, `ts` |
| `plan_transition` | `action`, `plan_id`, `from_status`, `to_status`, `editor_tool`, `file_path`, `transition_legal`, `event_schema`, `ts` |
| `veto_triggered` | `action`, `hook`, `reason_code`, `reason_preview` (redacted ≤120 chars), `blocked_tool`, `session_id` (str, v2.14), `caller` (str, v2.14 — optional, populated for kernel events), `event_schema`, `ts` |
| `benchmark_run` | `action`, `benchmark_id`, `skill`, `pass_count`, `fail_count`, `pass_rate_bps` (int 0..1000 — pass_rate × 1000; canonical_json no-float), `median_score_bps` (int 0..1000 — median_score × 1000), `floor_bps` (int 0..1000 — floor × 1000), `cost_usd_cents` (int ≥0 — cost × 100), `duration_ms` (int ≥0 — duration_s × 1000), `event_schema`, `ts` |
| `lesson_write` | `action`, `lesson_id`, `archetype`, `scope_tags` (list), `trigger`, `source_event_id`, `event_schema`, `ts` |
| `injection_flag` (v2.1) | `action`, `source`, `family_counts` (object), `match_count`, `bytes_scanned`, `truncated`, `triggered_by_tool`, `event_schema`, `ts` |
| `lesson_outcome` (v2) | `action`, `lesson_id`, `archetype`, `hit` (bool), `hit_count`, `miss_count`, `consumer` (enum `{benchmark, architect}`, v2.2.2), `inference_mode` (str, v2.2.2), `window_duration_seconds` (int, v2.2.2), `session_end_reason` (str, v2.2.2), `event_schema`, `ts` |
| `lesson_outcome_undone` (v2.3) | `action`, `lesson_id`, `archetype`, `consumer`, `undone_kind` (enum `{hit, miss}`), `hit_count`, `miss_count`, `event_schema`, `ts` |
| `confidence_gate` (v2.2) | `action`, `claim_count`, `pass_count`, `fail_count`, `verifier_kind_counts` (object: kind→count), `agent_name`, `source`, `raw_claim_count` (int, v2.2.1), `truncated` (bool, v2.2.1), `event_schema`, `ts` |
| `lesson_read` (v2.2) | `action`, `lesson_ids` (list), `lesson_count`, `archetype`, `keywords` (list), `k`, `consumer`, `event_schema`, `ts` |
| `lesson_archived` (v2.2) | `action`, `lesson_id`, `archetype`, `hit_count`, `miss_count`, `hit_rate_bps` (int 0..1000 — hit_rate × 1000; canonical_json no-float invariant), `archive_path`, `reason`, `event_schema`, `ts` |
| `lesson_restored` (v2.2) | `action`, `lesson_id`, `archetype`, `restored_from`, `restored_to`, `event_schema`, `ts` |
| `state_store_write` (v2.4) | `action`, `store_name`, `plan_id_hash` (16-char sha256 prefix), `key_hash` (16-char sha256 prefix), `value_bytes` (int), `ttl_seconds` (nullable int), `redaction_applied` (bool), `event_schema`, `ts` |
| `state_store_read` (v2.4) | `action`, `store_name`, `plan_id_hash`, `key_hash`, `found` (bool), `event_schema`, `ts` |
| `state_store_pruned` (v2.4) | `action`, `store_name`, `plan_id_hash`, `keys_pruned_count` (int), `event_schema`, `ts` |
| `budget_exceeded` (v2.4) | `action`, `plan_id`, `spawn_id`, `tokens_used` (int), `cap` (int), `scope` (enum `{spawn,plan}`), `event_schema`, `ts` |
| `budget_bypass_used` (v2.4) | `action`, `plan_id`, `caller_pid` (int), `reason_preview` (redacted ≤120 chars), `event_schema`, `ts` |
| `otel_export_dropped` (v2.4) | `action`, `fields_dropped_count` (int), `endpoint_host`, `reason`, `event_schema`, `ts` |
| `output_safety_flag` (v2.4) | `action`, `source`, `family_counts` (object), `match_count` (int), `bytes_scanned` (int), `redaction_applied` (bool), `triggered_by_tool`, `snippet_preview` (redacted ≤200 chars), `truncated` (bool), `event_schema`, `ts` |
| `skill_patch_applied` (v2.4) | `action`, `proposal_id`, `skill_slug`, `commit_sha`, `signer_fingerprint`, `shadow_mode` (bool), `event_schema`, `ts` |
| `squad_imported` (v2.4) | `action`, `squad_name`, `manifest_sha256`, `signer_fingerprint`, `source`, `event_schema`, `ts` |
| `live_adapter_call_started` (v2.5) | `action`, `provider`, `url` (query-scrubbed), `attempt` (int ≥1), `event_schema`, `ts` |
| `live_adapter_call_succeeded` (v2.5) | `action`, `provider`, `url` (query-scrubbed), `status` (int 2xx), `duration_ms` (int), `retried` (bool), `event_schema`, `ts` |
| `live_adapter_call_failed` (v2.5) | `action`, `provider`, `failure_mode` (enum per SPEC/v1/live-adapters-policy §3), `http_status` (nullable int), `duration_ms` (int), `retry_count` (int), `event_schema`, `ts` |
| `breaker_opened` (v2.5) | `action`, `provider`, `failures_in_window` (int), `threshold` (int), `reason` (enum from live-adapters-policy §3), `event_schema`, `ts` |
| `breaker_closed` (v2.5) | `action`, `provider`, `from_state` (enum `{open, half_open, reset}`), `event_schema`, `ts` |
| `credential_rotation_due` (v2.5) | `action`, `provider`, `age_days` (int), `warn_threshold_days` (int), `max_threshold_days` (int), `event_schema`, `ts` |
| `mcp_handler_invoked` (v2.5) | `action`, `handler` (enum from ADR-042 §Auth.2 ACL), `client_id` (hex16), `transport` (enum `{http, stdio}`), `duration_ms` (int), `event_schema`, `ts` |
| `mcp_handler_denied` (v2.5) | `action`, `handler`, `client_id` (hex16), `transport`, `reason` (enum per ADR-042 §Auth.5 + §Cost.1), `event_schema`, `ts` |
| `mcp_server_started` (v2.5) | `action`, `transport`, `host`, `port` (int; 0 for stdio), `version`, `handlers_count` (int), `event_schema`, `ts` |
| `mcp_server_disabled_by_kill_switch` (v2.5) | `action`, `reason`, `event_schema`, `ts` |
| `policy_evaluated` (v2.6) | `action`, `policy_id`, `rule_id`, `decision` (enum `{allow, deny, block}`), `duration_ms` (int), `event_schema`, `ts` |
| `policy_denied` (v2.6) | `action`, `policy_id`, `rule_id`, `reason` (closed-enum per SPEC/v1/policy-dsl.schema.md §Error-model), `event_schema`, `ts` |
| `policy_error` (v2.6) | `action`, `policy_id`, `error_kind` (enum `{parse_error, predicate_missing, import_failure, depth_limit, size_limit, alias_rejected, tag_rejected}`), `detail` (redacted ≤200 chars), `event_schema`, `ts` |
| `replay_started` (v2.6) | `action`, `original_session_id`, `mode` (enum `{dry_run, execute}`), `redacted_fragments_count` (int), `as_user`, `event_schema`, `ts` |
| `replay_completed` (v2.6) | `action`, `original_session_id`, `mode`, `duration_ms` (int), `spawn_count` (int), `diff_summary`, `event_schema`, `ts` |
| `replay_diff_produced` (v2.6) | `action`, `original_session_id`, `spawn_ordinal` (int), `divergence_kind` (enum `{output_mismatch, spawn_missing, extra_spawn, env_mismatch, audit_payload_mismatch}`), `artifact_path`, `event_schema`, `ts` |
| `prediction_queried` (v2.6) | `action`, `plan_id`, `bucket_range` (bucketed string; NO raw dollar figures per ADJ-038), `confidence` (enum `{high, medium, low, cold_start}`), `training_window_plans` (int), `event_schema`, `ts` |
| `pattern_stored` (v2.6) | `action`, `topic` (Unicode NFC + lowercase + dash-separated), `content_hash` (sha256), `size_bytes` (int; ≤4096 per SPEC cap), `event_schema`, `ts` |
| `pattern_queried` (v2.6) | `action`, `topic`, `k` (int 1..10 clamped), `match_count` (int), `event_schema`, `ts` |
| `pattern_evicted` (v2.6) | `action`, `topic`, `content_hash`, `reason` (enum `{admin_request, size_cap_breach, redact_violation}`), `event_schema`, `ts` |
| `threat_model_promoted` (v2.6) | `action`, `from_status` (enum `{draft, accepted, stale}`), `to_status`, `accepted_by`, `commit_sha`, `event_schema`, `ts` |
| `threat_model_freshness_breach` (v2.6) | `action`, `new_adr_count_since_review` (int), `threshold` (int; default 2 per ADJ-021), `event_schema`, `ts` |
| `session_start` (v2.7) | `action`, `session_id`, `ts`, `event_schema`. PLAN-028 Wave A ADR-056 — session-lifecycle observability. |
| `session_end` (v2.7) | `action`, `session_id`, `ts`, `event_schema`. PLAN-028 Wave A ADR-056. |
| `prompt_submitted` (v2.7) | `action`, `session_id`, `ts`, `event_schema`. PLAN-028 Wave A ADR-056. |
| `session_stop` (v2.7) | `action`, `session_id`, `ts`, `event_schema`. PLAN-028 Wave A ADR-056. |
| `output_scan_finding` (v2.7) | `action`, `source`, `family_counts` (object), `redaction_applied` (bool), `event_schema`, `ts`. PLAN-029 Wave A ADR-057 — output-scan redaction. |
| `rag_query_issued` (v2.8) | `action`, `query_hash` (sha256), `top_k` (int), `duration_ms` (int), `event_schema`, `ts`. PLAN-041 Wave A+ ADR-062. |
| `rag_query_returned` (v2.8) | `action`, `query_hash`, `chunk_keys` (list[str]), `chunks_count` (int), `event_schema`, `ts`. PLAN-041 Wave A+ ADR-062. |
| `rag_query_fallback` (v2.8) | `action`, `reason` (enum), `event_schema`, `ts`. PLAN-041 Wave A+ ADR-062. |
| `rag_query_redacted` (v2.8) | `action`, `query_hash`, `chunk_keys`, `family_counts` (object), `event_schema`, `ts`. PLAN-041 Wave A+ ADR-062. |
| `rag_index_redacted` (v2.8) | `action`, `file_path`, `reason`, `family_counts` (object), `indexer_version`, `event_schema`, `ts`. PLAN-041 Wave A+ ADR-062. |
| `tier_policy_derived` (v2.9) | `action`, `role`, `task_type`, `derived_tier` (enum `{opus, sonnet, haiku}`), `n_samples` (int), `gap_pp` (float), `event_schema`, `ts`. PLAN-043 Wave B ADR-064 — dynamic tier-policy learned dispatch (learn.py). |
| `tier_policy_promote_applied` (v2.9) | `action`, `role`, `previous_tier`, `new_tier`, `policy_sha` (sha256), `event_schema`, `ts`. PLAN-043 Wave B ADR-064 (apply.py). |
| `tier_policy_promote_cost_gated` (v2.9) | `action`, `agent_slug`, `from_tier`, `to_tier`, `projected_delta_usd_cents` (int, nullable — projected monthly cost delta × 100; canonical_json no-float invariant), `threshold_usd_cents` (int — cost gate threshold × 100), `event_schema`, `ts`. PLAN-043 Wave B ADR-064 (apply.py C-P0-4 3-way gate). |
| `tier_policy_demote_requested` (v2.9) | `action`, `role`, `from_tier`, `to_tier`, `owner_signed` (bool), `event_schema`, `ts`. PLAN-043 Wave B ADR-064 — Owner-signed demote path. |
| `tier_policy_rejected` (v2.9) | `action`, `role`, `reason` (enum `{veto_floor, cost_gated, cooldown, killswitch, hmac_fail, statistical_floor, fixture_corpus_mismatch}`), `event_schema`, `ts`. PLAN-043 Wave B ADR-064. `fixture_corpus_mismatch` added in PLAN-045 F-10-06 — learner fail-CLOSED on tournament fixture content-integrity drift. |
| `tier_policy_hmac_verify_failed` (v2.9) | `action`, `report_path`, `reason` (enum), `event_schema`, `ts`. PLAN-043 Wave B ADR-064 — supply-chain tamper detection. |
| `tier_policy_killswitch_triggered` (v2.9) | `action`, `factor_env` (bool), `factor_sentinel` (bool), `event_schema`, `ts`. PLAN-043 Wave B ADR-064 — two-factor kill-switch. |
| `tier_policy_adopter_override_respected` (v2.9) | `action`, `role`, `adopter_tier`, `learned_tier`, `event_schema`, `ts`. PLAN-043 Wave B ADR-064 — adopter quality-profile takes precedence. |
| `tier_policy_dry_run_complete` (v2.9) | `action`, `changes_count` (int), `diff_sha` (sha256), `event_schema`, `ts`. PLAN-043 Wave B ADR-064 — CLI dry-run preview. |
| `tournament_run_started` (v2.9) | `action`, `tournament_id`, `event_schema`, `ts`. PLAN-032 Wave B ADR-063 — agent-eval tournament start. |
| `tournament_task_scored` (v2.9) | `action`, `swarm_id`, `loop_id`, `score_bps` (int 0..1000 — score × 1000; canonical_json no-float), `tests_passed` (int), `tests_failed` (int), `event_schema`, `ts`. PLAN-032 Wave B ADR-063. |
| `tournament_run_completed` (v2.9) | `action`, `swarm_id`, `winner_loop_id`, `rejected_count` (int), `decisive` (bool), `event_schema`, `ts`. PLAN-032 Wave B ADR-063. |
| `tournament_budget_projected` (v2.9) | `action`, `swarm_id`, `projected_cost_cents` (int ≥0 — USD × 100; canonical_json no-float), `candidate_count` (int), `event_schema`, `ts`. PLAN-032 Wave B ADR-063 — pre-run cost estimate. |
| `tournament_budget_exceeded` (v2.9) | `action`, `swarm_id`, `actual_cost_cents` (int ≥0 — USD × 100; canonical_json no-float), `cap_cents` (int ≥0 — USD × 100), `event_schema`, `ts`. PLAN-032 Wave B ADR-063 — runtime cost-gate trip. |
| `tournament_aborted` (v2.9) | `action`, `tournament_id`, `reason` (enum), `event_schema`, `ts`. PLAN-032 Wave B ADR-063 — kill-switch / budget / error abort. |
| `tournament_fixture_rejected` (v2.9) | `action`, `fixture_path`, `family` (enum), `event_schema`, `ts`. PLAN-032 Wave B ADR-063 — check_fixture.py rejects bidi / zero-width / homoglyph / oversize / jwt / llm01 shapes. |
| `tournament_judge_hijack_suspected` (v2.9) | `action`, `swarm_id`, `loop_id`, `indicator` (str ≤64 — adversarial signal label; no float), `event_schema`, `ts`. PLAN-032 Wave B ADR-063 — judge-response adversarial indicator hardening. |
| `fluency_nudge` (v2.10) | `action`, `session_id`, `project`, `marker_count` (int), `threshold_crossed` (int), `markers_matched` (list[str]), `output_length` (int), `event_schema`, `ts`. PLAN-045 Wave 5 P0-09 (b) — Artifact Paradox SubagentStop advisory. Kill-switch `CEO_FLUENCY_NUDGE=0`. |
| `skill_reference_read_mismatch` (v2.10) | `action`, `session_id`, `project`, `skill_path` (rel), `claimed_sha` (sha256), `read_sha` (sha256), `spawn_ts` (ISO-8601), `read_ts` (ISO-8601), `event_schema`, `ts`. PLAN-045 Wave 5 F-10-07 v2 — TOCTOU between spawn SKILL REFERENCE sha pin and sub-agent Read-time hash. Kill-switch `CEO_SKILL_READ_V2=0`. |
| `skill_reference_read_stale` (v2.10) | `action`, `session_id`, `project`, `skill_path` (rel), `claimed_sha`, `read_sha`, `spawn_ts`, `read_ts`, `delta_seconds` (int), `event_schema`, `ts`. PLAN-045 Wave 5 F-10-07 v2 — spawn event more than 5 minutes older than the sub-agent Read (TOCTOU plausibility window). Kill-switch `CEO_SKILL_READ_V2=0`. |
| `skill_reference_never_read` (v2.10) | `action`, `session_id`, `project`, `skill_path` (rel), `claimed_sha`, `spawn_ts`, `event_schema`, `ts`. PLAN-045 Wave 5 F-10-07 v2 — sub-agent spawned with `## SKILL REFERENCE` but never issued a Read on the declared file. Emit site deferred to SessionEnd hook (future iteration). |
| `swarm_started` (v2.11) | `action`, `swarm_id`, `n_loops` (int), `budget_tokens` (int), `event_schema`, `ts`. PLAN-017 Phase 4 — autonomous-loop swarm coordinator dispatch start. |
| `swarm_iteration` (v2.11) | `action`, `swarm_id`, `loop_id`, `iteration` (int), `event_schema`, `ts`. PLAN-017 Phase 4 — per-loop iteration progress. |
| `swarm_halted_budget` (v2.11) | `action`, `swarm_id`, `tokens_consumed` (int), `event_schema`, `ts`. PLAN-017 Phase 4 — budget ceiling triggered halt. |
| `swarm_halted_convergence` (v2.11) | `action`, `swarm_id`, `jaccard` (float), `event_schema`, `ts`. PLAN-017 Phase 4 — inter-loop output Jaccard similarity ≥ threshold. |
| `swarm_halted_kill` (v2.11) | `action`, `swarm_id`, `source` (enum `{env, file, cli}`), `event_schema`, `ts`. PLAN-017 Phase 4 — kill-switch layers 1-3 fired. |
| `swarm_aborted_error` (v2.11) | `action`, `swarm_id`, `error` (str), `event_schema`, `ts`. PLAN-017 Phase 4 — unrecoverable error aborted swarm. |
| `swarm_killed` (v2.11) | `action`, `swarm_id`, `layer` (int 1-6), `event_schema`, `ts`. PLAN-017 Phase 4 — SIGKILL/watchdog escalation path. |
| `swarm_tournament_selected` (v2.11) | `action`, `swarm_id`, `winner_loop`, `event_schema`, `ts`. PLAN-017 Phase 4 — tournament scorer selected best-of-N loop. |
| `swarm_finalize_grouped` (v2.11) | `action`, `swarm_id`, `groups` (int), `event_schema`, `ts`. PLAN-017 Phase 4 — finalizer groups winner outputs into commit bundles. |
| `swarm_finalize_committed` (v2.11) | `action`, `swarm_id`, `commit` (sha7), `event_schema`, `ts`. PLAN-017 Phase 4 — winner output committed to main branch. |
| `escalation_detected` (v2.11) | `action`, `signal` (enum), `severity` (enum `{low, medium, high}`), `event_schema`, `ts`. PLAN-048 Phase 2 — CEO model escalation signal emitted by detector. |
| `escalation_dispatched` (v2.11) | `action`, `from_model`, `to_model`, `event_schema`, `ts`. PLAN-048 Phase 2 — runtime re-dispatch from Sonnet default to Opus. |
| `escalation_suppressed` (v2.11) | `action`, `reason` (enum `{cooldown_active, kill_switch, baseline_mode}`), `event_schema`, `ts`. PLAN-048 Phase 2 — escalation skipped per suppression rule. |
| `escalation_baseline_recorded` (v2.11) | `action`, `session_tag` (str), `spawn_count` (int), `event_schema`, `ts`. PLAN-048 Phase 2 — observe-only arm session aggregate. |
| `audit_tokens_emitted` (v2.12) | `action`, `session_id`, `timestamp` (ISO-8601), `window_seconds` (int), `events_scanned` (int), `tokens_in_total` (int), `tokens_out_total` (int), `cost_cents` (int), `tier_id_distribution` (dict<str,int>), `detector_findings_count` (dict<str,int>), `hook_duration_ms` (int), `project`. PLAN-060 Phase B / SEC-P0-04 — counts-only audit-tokens stub event emitted by SessionEnd hook via `audit-tokens.py --content-ban=strict`. Allowlist enforced by `scrub_audit_tokens_event()` (defense-in-depth on top of CLI flag). Total payload < 2 KiB. Opt-in via `CEO_AUDIT_TOKENS_AUTO=1`. |
| `audit_tokens_timeout` (v2.12) | `action`, `session_id`, `timeout_ms` (int — timeout budget in milliseconds; canonical_json no-float invariant; e.g. 50ms default → timeout_ms=50), `project`. PLAN-060 Phase B / SEC-P0-04 §Performance budget — fired when `audit-tokens.py` subprocess exceeds the 50ms wall budget. Replaces the `audit_tokens_emitted` that would have fired on success; SessionEnd hook does not block on slow detectors. |
| `audit_tokens_key_dropped` (v2.12) | `action`, `session_id`, `dropped_keys` (list<str>, capped at 50), `dropped_count` (int), `project`. PLAN-060 Phase B / SEC-P0-04 §Defense-in-depth — emitted by `scrub_audit_tokens_event()` when forbidden keys are stripped from an audit-tokens event. Event itself never carries dropped VALUES (only keys), so hostile keys with payload-like names do not leak content. Signals allowlist drift OR injection attempt. |
| `mcp_injection_finding` (v2.13) | `action`, `server_id`, `mcp_tool_name`, `source_kind` (enum `{tool_result, resource_fetch, instructions}`), `family_counts` (dict<str,int>), `match_count` (int), `bytes_scanned` (int), `severity` (enum `{low, medium, high}`), `snippet_preview` (str, redacted ≤200), `scanner_action` (enum `{advisory, stripped, blocked}`), `session_id`, `project`, `event_schema`, `ts`. PLAN-052 / ADR-083 — MCP injection scanner finding. Emitted by `check_mcp_response.py` PostToolUse hook when an MCP tool result contains harness-mimicry or directive-prose markup (reused from `_lib/injection_patterns.py`). STRICT mode opt-in via `CEO_MCP_SCANNER_MODE=strict` (Session 73 wired); when active and severity=high, hook emits `scanner_action="blocked"` and returns `decision: block` to the harness. Otherwise `scanner_action="advisory"` (log-only). `emit_mcp_injection_finding` shipped in `_lib/audit_emit.py` (Wave B audit-v2 C1-P0-03 fix). |
| `skill_bootstrap_used` (v2.15) | `action`, `skill_slug`, `env_set` (bool), `project`, `event_schema`, `ts`. Session 76 audit-v3 / Codex DIM-04 #1 — emitted by `check_skill_patch_sentinel.py:251` when the bootstrap env var is detected on a SKILL.md edit. Pre-Session-76 was dropped by `_write_event` because the action was unregistered (silent observability gap). |
| `skill_bootstrap_post_hash` (v2.15) | `action`, `skill_slug`, `sha256` (64-hex of post-write content), `file_size` (int), `bootstrap_event_correlated` (bool), `bootstrap_ts_s` (int — epoch-seconds of bootstrap event; canonical_json no-float invariant), `suspicious_delay_ms` (int — delay in ms between bootstrap_used and PostToolUse; -1 when not applicable), `anomaly` (bool), `hook_version`, `project`, `event_schema`, `ts`. Session 76 audit-v3 / Codex DIM-04 #1 — emitted by `check_skill_bootstrap_post.py:196` after the SKILL.md write completes; correlates the prior `skill_bootstrap_used` event via timestamp delta. Pre-Session-76 was dropped silently. |
| `replay_capture_started` (v2.16) | `action`, `original_session_id`, `redacted_fragments_count` (int), `as_user`, `session_id`, `project`, `event_schema`, `ts`. PLAN-069 Phase 1 / ADR-101 — emitted by `replay-session.py:_emit_started` when `mode == "capture"`. Distinct from `replay_started` because capture mode produces a redacted JSONL fixture (not a dry_run/execute artifact). |
| `replay_capture_completed` (v2.16) | `action`, `original_session_id`, `duration_ms` (int), `event_count` (int), `fixture_path` (str), `session_id`, `project`, `event_schema`, `ts`. PLAN-069 Phase 1 / ADR-101 — emitted by `replay-session.py:_emit_completed` when `mode == "capture"`. ``event_count`` is total redacted events written to the fixture; ``fixture_path`` is $CLAUDE_PROJECT_DIR-relative resolved out path. |
| `claim_emitted` (v2.19) | `action`, `claim_id` (composite `<claim_type>:<12-hex>`; `<claim_type>` MUST match KNOWN_KINDS grammar `^[a-z_]{1,32}$`, otherwise rehashed to `unknown:<12-hex>` via `_safe_claim_id_hash`), `claim_type` (str ≤32 chars; KNOWN_KINDS recommended), `severity` (closed enum `{info, warn, critical}`; invalid → `info`), `verifier_kind` (str ≤32), `payload_hash` (bare 12-hex; defensive rehash if non-hex), `kind_supported` (bool; FP signal — `True` means kind in KNOWN_KINDS, `False` is extraction-FP), `line_num` (int), `agent_name` (str ≤64), `source` (str ≤32), `session_id`, `project`, `event_schema`, `ts`, `tokens_*`, `hmac`, `hmac_error`. PLAN-090-FOLLOWUP Wave A — per-claim event producer (S138 R2 ACCEPT). Sec MF-3 allowlist `_CLAIM_EMITTED_ALLOWLIST` enforced; emit_generic dispatch wired (Codex iter-1 P0-3+P0-4). LLM06 hold: raw claim body NEVER persisted. Kill-switch `CEO_CONFIDENCE_GATE_PRODUCER_PAIR_DISABLED=1`. |
| `confidence_gate_verdict` (v2.19) | `action`, `claim_id` (defensive rehash via `_safe_claim_id_hash`), `verdict` (closed enum `{pass, fail, refuted}`; invalid → `fail` NOT `refuted` per P1-1 fold — `refuted` is the FP signal in backfill line 134 and a parser sentinel must NOT pollute the FPR numerator), `was_false_positive` (bool; FP signal — `was_false_positive = (NOT kind_supported)` per Wave B.6 contract), `kind_supported` (bool; paired with claim_emitted), `verifier_kind` (str ≤32), `verifier_outcome` (PII-redacted + ≥8-char overlap-scrubbed against claim_args + NFKC + ≤64 chars; security iter-1 P1-B fold), `agent_name` (str ≤64), `source` (str ≤32), `session_id`, `project`, `event_schema`, `ts`, `tokens_*`, `hmac`, `hmac_error`. PLAN-090-FOLLOWUP Wave A. Sec MF-3 allowlist `_CONFIDENCE_GATE_VERDICT_ALLOWLIST` enforced. |
| `persona_demand_opened` (v2.18) | `action`, `demand_id` (str ≤16), `demand_event_type` (enum `{branch_ahead, auth_edit, test_edit, detect_edit}`), `expected_persona` (enum `{code-reviewer, security-engineer, qa-architect, threat-detection-engineer}`), `target_ref_hash` (sha256 truncated 12-hex; raw value NEVER persisted — LLM06 hold), `match_window_hours` (int, default 24), `session_id`, `project`, `event_schema`, `ts`. PLAN-104 Wave A — persona-demand ledger Phase 2 (S134 R2 ACCEPT). Sec MF-3 allowlist `_PERSONA_DEMAND_OPENED_ALLOWLIST` enforced; emit_generic dispatch wired (Codex iter-1 P0 #4). Kill-switch `CEO_PERSONA_DEMAND_LEDGER_DISABLED=1`. |
| `persona_demand_matched` (v2.18) | `action`, `demand_id`, `demand_event_type`, `expected_persona`, `actual_persona` (strict-match: `actual_persona == expected_persona` ALWAYS holds — incl. the codex modality, which sets it to `code-reviewer`), `latency_ms` (int), `match_modality` (enum `{native_spawn, codex_review}`; default `native_spawn`; `codex_review` recognized for `code-reviewer` demands ONLY per PLAN-132 / ADR-145), `session_id`, `project`, `event_schema`, `ts`. PLAN-104 Wave A; PLAN-132 v2.40. Sec MF-3 allowlist `_PERSONA_DEMAND_MATCHED_ALLOWLIST`. |
| `persona_demand_unmet` (v2.18) | `action`, `demand_id`, `demand_event_type`, `expected_persona`, `target_ref_hash`, `window_expired_at` (ISO8601 UTC), `session_id`, `project`, `event_schema`, `ts`. PLAN-104 Wave A — idempotent at most ONE per demand_id (dedup at resolver scan time). Sec MF-3 allowlist `_PERSONA_DEMAND_UNMET_ALLOWLIST`. |
| `persona_demand_waived` (v2.18) | `action`, `demand_id`, `demand_event_type`, `expected_persona`, `waive_reason` (closed enum `{docs-only, generated-or-vendored, emergency-hotfix, explicit-skip}`; free-text replaced with `invalid-enum` forensic sentinel per Codex iter-1 P2 #1), `session_id`, `project`, `event_schema`, `ts`. PLAN-104 Wave A. Sec MF-3 allowlist `_PERSONA_DEMAND_WAIVED_ALLOWLIST`. |
| `ceo_boot_emitted` (v2.17) | `action`, `gate_pass` (bool), `duration_ms` (int), `checks_total` (int), `checks_failed` (int), `cache_hit` (bool), `session_id`, `project`, `event_schema`, `ts`. PLAN-065 Phase 2 / ADR-098 (S82 ceremony lote, 2026-05-04) — emitted by `.claude/scripts/ceo-boot.py:main` once per session-boot autopilot invocation. Sec MF-3 field allowlist enforced via `_scrub_ceo_boot_event`: DENIED fields include `tokens`, `cost_usd`, `prompt`, `paths`, `SKILL` content, `env` values (LLM06 side-channel guard). Closes Reality-Ledger fixture #4 (declared-but-not-wired pattern from PLAN-071 Phase 0 baseline detector D4). |
| `ceo_boot_check_skipped` (v2.17) | `action`, `check_name` (str), `timeout_ms` (int), `session_id`, `project`, `event_schema`, `ts`. PLAN-065 Phase 2 / ADR-098 (S82 ceremony lote, 2026-05-04) — emitted by `.claude/scripts/ceo-boot.py:dispatch_parallel` per Tier-S check that exceeds the aggregate timeout budget (CR-MF6 forensic traceability — silently dropped events block forensic reconstruction). Sec MF-3 field allowlist enforced via `_scrub_ceo_boot_event`. |
| `mcp_canonical_guard_allowed` (v2.18) | `action`, `tool_name` (str — `mcp__*`), `target_path` (str — repo-relative), `reason` (str — sentinel resolver / non-canonical / etc.), `session_id`, `project`, `event_schema`, `ts`. PLAN-070 / ADR-102 (S85 Layer B ceremony, 2026-05-05) — emitted by `.claude/hooks/_lib/mcp/canonical_guard.py:check_mcp_call` on every ALLOW decision for a tool whose name matches `mcp__*`. Sec MF-3 field allowlist (R6-01 tightened) enforced via `_MCP_CANONICAL_GUARD_ALLOWED_ALLOWLIST` in `audit_emit.py`. Closes ADR-095 §gate-#6 NG-06 (custom MCP tools previously bypassed `check_canonical_edit` because the hook only filtered `Edit/Write/MultiEdit/NotebookEdit`). |
| `mcp_canonical_guard_blocked` (v2.18) | `action`, `tool_name` (str — `mcp__*`), `target_path` (str — repo-relative), `reason` (str — stable enum: `canonical_no_sentinel` / `path_escapes_repo_root_fail_closed` / `blob_authoritative_parse_failed_fail_closed` / `middleware_fault:<ExcName>`), `session_id`, `project`, `event_schema`, `ts`. PLAN-070 / ADR-102 (S85 Layer B ceremony, 2026-05-05) — emitted on every BLOCK decision. Same allowlist as `mcp_canonical_guard_allowed`. Closes ADR-095 §gate-#6 NG-06. |
| `task_route_advised` (v2.19) | `action`, `contract_id` (str — uuid4), `classification` (str — `S`/`M`/`L`/`XL`), `task_description_hmac` (hex str OR null when salt unavailable per ADR-079), `duration_ms` (int — `time.perf_counter()` measured `classify()` wall-clock), `session_id`, `project`, `event_schema`, `ts`. PLAN-071 / ADR-104 (S87 v1.14.0 ceremony, 2026-05-05) — emitted by `.claude/scripts/task-route.py:main` per advisory invocation (rate-limited 1/10s OR session_end flush per R-SEC U4). Sec MF-3 field allowlist enforced via `_TASK_ROUTE_ADVISED_ALLOWLIST` + `_scrub_ceo_boot_event` helper (allowlist-agnostic). DENIED fields: task description literal, file paths, recommendation text body, environment values, token counts. |
| `task_route_key_dropped` (v2.19) | `action`, `dropped_keys` (list[str]), `session_id`, `project`, `event_schema`, `ts`. PLAN-071 / ADR-104 — defense-in-depth breadcrumb when `_scrub_ceo_boot_event` strips forbidden caller fields from a `task_route_advised` payload. Anti-allowlist-drift signal (matches `audit_tokens_key_dropped` precedent per ADR-080). |
| `reality_ledger_finding` (v2.19) | `action`, `detector` (str — closed enum: `runtime_read_missing` / `installable_claim_drift` / `model_assignment_divergence` / `enforcement_commit_unpopulated` / `audit_action_phantom`), `severity` (str — `low`/`medium`/`high`), `confidence_bps` (int 0..1000 — confidence × 1000; canonical_json no-float invariant; recover float via confidence_bps / 1000), `claim_source_sha256` (hex str — sha256 of the claim source content), `finding_count_in_run` (int), `session_id`, `project`, `event_schema`, `ts`. PLAN-071 / ADR-104 — emitted by `.claude/scripts/reality-ledger.py` per detected finding (severity ≥ medium per Phase 4 CI workflow filter). Sec MF-3 field allowlist enforced via `_REALITY_LEDGER_FINDING_ALLOWLIST`. **R-SEC2 contract**: `claim_source_path` is NEVER emitted to audit-log (audit-log + GH issue body use `claim_source_sha256` ONLY; `claim_source_path` is local-stdout-only via `--format markdown` for triage). |
| `reality_ledger_key_dropped` (v2.19) | `action`, `dropped_keys` (list[str]), `session_id`, `project`, `event_schema`, `ts`. PLAN-071 / ADR-104 — defense-in-depth breadcrumb when `_scrub_ceo_boot_event` strips forbidden caller fields (e.g. `claim_source_path` leak attempt) from a `reality_ledger_finding` payload. |
| `optimizer_route_recommended` (PLAN-122 WS12) | `action`, `route` (str — closed enum: `passthrough`/`single_agent`/`fanout`), `complexity_bucket` (str), `parallelizable` (int 0/1), `suggested_width` (int 1..8), `prompt_len_bucket` (int 0..3), `kill_switch_state` (str), `session_id`, `project`, `event_schema`, `ts`, plus baseline `tokens_in`/`tokens_out`/`tokens_total`/`hmac`/`hmac_error`. Emitted by `optimizer/recommender.py` via `_skeleton.safe_emit`. Sec MF-3 allowlist `_OPTIMIZER_ALLOWLISTS["optimizer_route_recommended"]`. DENIED: prompt body, file paths, env values. |
| `fanout_recommended` (PLAN-122 WS12) | `action`, `subtask_count` (int), `suggested_width` (int 1..8), `width_capped` (int 0/1), `budget_governed` (int 0/1), `rate_backoff_applied` (int 0/1), `models_basis` (str ≤200), `session_id`, `project`, `event_schema`, `ts`, plus baseline HMAC fields. Sec MF-3 allowlist `_OPTIMIZER_ALLOWLISTS["fanout_recommended"]`. |
| `model_choice_recommended` (PLAN-122 WS12) | `action`, `subtask_index` (int ≥0 — NOT the prompt-derived label; Sec MF-3), `model_recommended` (str — closed model-slug set), `confidence_basis_points` (int 0..1000), `cost_governed` (int 0/1), `fell_back_to_static` (int 0/1), `session_id`, plus baseline `event_schema`/`ts`/`tokens_*`/`hmac`/`hmac_error` added by `_write_event`. Sec MF-3 allowlist `_OPTIMIZER_ALLOWLISTS["model_choice_recommended"]`. |
| `rag_context_recommended` (PLAN-122 WS12) | `action`, `router_decision` (str), `chunks_returned` (int ≥0), `kill_switch_state` (str), `session_id`, `project`, `event_schema`, `ts`, plus baseline HMAC fields. Sec MF-3 allowlist `_OPTIMIZER_ALLOWLISTS["rag_context_recommended"]`. |
| `codex_review_disabled` (PLAN-122 WS12) | `action`, `reason` (str), `session_id`, `project`, `event_schema`, `ts`, plus baseline HMAC fields. Emitted by the WS-3 Codex phase-gate driver (separate WS) when `CEO_CODEX_REVIEW` is OFF. Sec MF-3 allowlist `_OPTIMIZER_ALLOWLISTS["codex_review_disabled"]`. |
| `codex_review_invoked` (PLAN-122 WS3) | `action`, `phase_number` (int ≥0), `review_status` (str — closed enum: `passed`/`failed`/`deferred`), `summary_hash` (str — 16-hex sha256 prefix or `none`; NEVER raw Codex summary), `thread_id_redacted` (str — 16-hex sha256 prefix or `none`; NEVER raw thread id), `codex_model` (str slug, e.g. `gpt-5-codex`), `duration_ms` (int ≥0), `violations_found_count` (int 0..9999), `session_id`, `project`, `event_schema`, `ts`, plus baseline `tokens_in`/`tokens_out`/`tokens_total`/`hmac`/`hmac_error` added by `_write_event` AFTER the scrub. PLAN-122 WS3 — per-phase Codex review event (complement of `codex_review_disabled`): emitted once when a Codex review actually RAN (any verdict), via `optimizer.codex_phase_gate.review_phase` → `_skeleton.safe_emit` from `check_pair_rail.py`. Sec MF-3 allowlist `_OPTIMIZER_ALLOWLISTS["codex_review_invoked"]` — caller-supplied fields ONLY. DENIED: raw Codex thread id / summary / prompt / diff, `tokens_*` side channel, the `review_disabled_signal` bool. |
| `model_routing_advised` (v2.20) | `action`, `archetype` (str), `task_type` (str), `model_recommended` (str), `confidence_basis_points` (int 0..1000 — float-confidence × 1000 normalized at emit time per Codex W1+W2 fix-pack #2), `applied_or_skipped` (str — closed enum: `applied` / `skipped_classify_frontmatter_authoritative` / `skipped_classify_exception` / `advisory_only_no_recommendation` / `advisory_only_classification_emitted`), `override_reason` (str), `session_id`, `project`, `event_schema`, `ts`, plus baseline `tokens_in` / `tokens_out` / `tokens_total` / `hmac` / `hmac_error` per HMAC-chain invariant. PLAN-078 Wave 1 (S89 Fase 1 commit 2cb1472, registered S92 Wave 1b ceremony 2026-05-07) — emitted by `.claude/hooks/check_agent_spawn.py:_emit_model_routing_advisory` per Agent-tool dispatch. Sec MF-3 field allowlist enforced via `_MODEL_ROUTING_ADVISED_ALLOWLIST` in `audit_emit.py`. DENIED fields: raw task description, file paths, prompt body, env values, token counts. |
| `estimate_drift_detected` (v2.20) | `action`, `plan_id` (str — Owner-visible per ADR-033 §plan-budget precedent), `drift_factor_compute_basis_points` (int — multiplier × 1000; `1234` ≡ 1.234×; floats forbidden by canonical_json invariant per Codex W1+W2 fix-pack #2), `drift_factor_owner_basis_points` (int), `severity` (str — closed enum: `low` / `medium` / `high`), `plan_count_in_run` (int), `systematic_bias_direction` (str — closed enum: `""` / `underestimate` (overrun, factor>1.2) / `overestimate` (underrun, factor<0.83); per Codex W1+W2 fix-pack #3 bidirectional detection), `session_id`, `project`, `event_schema`, `ts`, plus baseline `tokens_in` / `tokens_out` / `tokens_total` / `hmac` / `hmac_error` per HMAC-chain invariant. PLAN-078 Wave 2 / Reality Ledger detector #7 — emitted per per-plan drift detection. Sec MF-3 enforced via `_ESTIMATE_DRIFT_DETECTED_ALLOWLIST` in `audit_emit.py`. DENIED fields: raw commit SHAs, file paths, plan body text, CSV row body. |
| `estimate_drift_systematic_bias` (v2.20) | `action`, `bias_direction` (str — closed enum: `underestimate` / `overestimate`; defaults to `underestimate` if caller value not in enum), `plans_affected_count` (int), `avg_drift_factor_compute_basis_points` (int — basis-points form, see `estimate_drift_detected`), `avg_drift_factor_owner_basis_points` (int), `session_id`, `project`, `event_schema`, `ts`, plus baseline `tokens_in` / `tokens_out` / `tokens_total` / `hmac` / `hmac_error` per HMAC-chain invariant. PLAN-078 Wave 2 — emitted per cross-plan systematic bias recommendation (cohort-level). Sec MF-3 enforced via `_ESTIMATE_DRIFT_SYSTEMATIC_BIAS_ALLOWLIST` in `audit_emit.py`. Strict 4-caller-field contract. |
| `ceo_boot_task_candidate_emitted` (v2.21) | `action`, `rank` (int — 1-based ordinal of marker in the boot run; clamped to `[1, 3]`; out-of-range falls back to `0` sentinel), `severity` (str — closed enum: `low` / `medium` / `high`; unknown values become `""` per typed-wrapper input validation), `subject_hash` (str — 12-hex-char prefix of `sha256(NFKC(visible Subject text))`; non-hex chars stripped, length-bounded), `awaiting_confirm` (bool — reserved future flag for "Owner-must-confirm" escape; default `false`; persisted as bool literal), `session_id`, `project`, `event_schema`, `ts`, plus baseline `tokens_in` / `tokens_out` / `tokens_total` / `hmac` / `hmac_error` per HMAC-chain invariant. PLAN-078 Wave 5 (S95 ceremony 2026-05-08) — emitted by `.claude/scripts/ceo-boot.py:_emit_task_candidate_safe` per `<!-- TASKCREATE-CANDIDATE -->` marker block written to stdout when `gate_pass=False AND severity≥medium`. Top-3 max per invocation; dedup via 24h TTL state file under `_lib/filelock`. Sec MF-3 field allowlist enforced via `_CEO_BOOT_TASK_CANDIDATE_EMITTED_ALLOWLIST` in `audit_emit.py`. DENIED fields: subject text body, recommendation body, check name, check stderr/detail, env values, file paths. The orchestrator (Claude running `/ceo-boot`) reconstructs `subject_hash` independently from the visible `Subject:` line via `sha256(NFKC(subject))[:12]` for dedup against the live task list. |
| `pair_rail_review_passed` (v2.22) | `action`, `target_path` (str ≤300 — repo-relative path of the tool's target), `tool_name` (str ≤50 — `Edit` / `Write` / `MultiEdit`), `codex_duration_ms` (int — wall-clock of Codex MCP invoke), `codex_response_sha256` (str ≤64 — SHA-256 of Codex stdout for forensic trace), `session_id`, `project`, `event_schema`, `ts`, plus baseline HMAC-chain invariant. PLAN-075 v1.13.x patch (S96-cont-2 ceremony 2026-05-09) / ADR-106 + ADR-110 — emitted by `.claude/hooks/check_pair_rail.py` PreToolUse on Edit\|Write\|MultiEdit against L3+ canonical-guarded paths when Codex MCP returns a clean read-only review (no write-shaped patches). Allow decision granted. Registered with `KERNEL_OVERRIDE` bypass since `audit_emit.py` is in `_KERNEL_PATHS`. |
| `pair_rail_codex_unavailable` (v2.22) | `action`, `target_path` (str ≤300), `tool_name` (str ≤50), `reason` (str ≤64 — closed enum: `binary_missing` / `connect_timeout` / `spawn_error` / `disabled_via_killswitch`), `session_id`, `project`, `event_schema`, `ts`, plus baseline HMAC-chain invariant. PLAN-075 v1.13.x patch / ADR-106 — emitted by `.claude/hooks/check_pair_rail.py` when Codex MCP is unavailable. Hook fail-OPENs (allow decision); this breadcrumb provides forensic trace for fail-open paths. |
| `pair_rail_codex_violation` (v2.22) | `action`, `target_path` (str ≤300), `tool_name` (str ≤50), `violation_type` (str ≤64 — closed enum: `unified_diff_detected` / `apply_patch_envelope` / `json_patch_rfc6902` / `mcp_write_tool_call`), `codex_response_sha256` (str ≤64), `session_id`, `project`, `event_schema`, `ts`, plus baseline HMAC-chain invariant. PLAN-075 v1.13.x patch / ADR-106 + ADR-110 — emitted by `.claude/hooks/check_pair_rail.py` when Codex MCP review returned a write-shaped patch (Codex is read-only by contract). Hook BLOCKs the tool call. |
| `pair_rail_sentinel_bypass` (v2.22) | `action`, `target_path` (str ≤300), `tool_name` (str ≤50), `sentinel_path` (str ≤300 — path to the sentinel that granted access), `session_id`, `project`, `event_schema`, `ts`, plus baseline HMAC-chain invariant. PLAN-075 v1.13.x patch / ADR-106 — emitted by `.claude/hooks/check_pair_rail.py` when an Owner-signed sentinel (verified by `check_canonical_edit.py` upstream) grants the L3+ path. Pair-rail review short-circuited; allow decision granted without invoking Codex. |
| `pair_rail_codex_injection_detected` (v2.23) | `action`, `tool_name` (str ≤50 — `mcp__codex__codex` or `mcp__codex__codex-reply`), `family_ids` (list[str] — sorted unique subset of `harness_mimicry`, `xml_system_tag`, `tool_use_forgery`), `match_count` (int ≥0), `first_offset_bucket` (str — closed enum `0-100` / `100-1k` / `1k-10k` / `10k-100k` / `100k+`), `session_id`, `project`, `event_schema`, `ts`, plus baseline HMAC-chain invariant. PLAN-081 Phase 1-full / R1 S-Sec-5 (S99 ceremony 2026-05-09) — emitted by `.claude/hooks/check_codex_response.py` PostToolUse on Codex MCP tool responses when ingress sanitization detects prompt-injection patterns. ADVISORY only per ADR-106 (PostToolUse cannot block). Sec MF-3 invariant: NEVER persist raw matched content nor raw offset values — `first_offset_bucket` is the bucketed forensic surface. Registered with `KERNEL_OVERRIDE` bypass since `audit_emit.py` is in `_KERNEL_PATHS`. |
| `dispatcher_route` (v2.23) | `action`, `archetype` (str ≤64), `rail` (str — closed enum: `pair_rail` / `fallback_claude_only` / `fallback_codex_only`), `reason_code` (str ≤80 — `ok` / `predicate_<id>_fired` / `matrix_sha_mismatch` / `health_prereq_unmet_<u-id>` / `override_coder_<provider>` / `override_reviewer_<provider>` / `invalid_coder_override_<sanitized>` / `invalid_reviewer_override_<sanitized>`), `coder` (str ≤32 — closed enum: `claude` / `codex`), `reviewer` (str ≤32 — closed enum: `claude` / `codex` / empty when fallback), `coder_model` (str ≤32 or null), `reviewer_sandbox` (str ≤32 — closed enum: `read-only` / `workspace-write` / `danger-full-access`), `fallback_provider` (str ≤32), `matrix_sha256_prefix` (str — 16-hex prefix only; raw digest forbidden), `matrix_sha256_match` (bool — true iff CEO_PAIR_RAIL_MATRIX_SHA256 env set AND matched loaded matrix), `wall_clock_ms` (int ≥0 — Codex iter 1 P0-1: integer milliseconds, NOT float seconds; canonical_json no-float invariant), `retry_at_timeout_ms` (int ≥0 OPTIONAL — present when codex.py classifier escalated simple→audit), `session_id`, `project`, `event_schema`, `ts`, plus baseline HMAC-chain invariant. PLAN-081 Phase 2 (S100 ceremony 2026-05-10) — emitted by `.claude/scripts/inject-agent-context.sh --pair-mode` per archetype dispatch via `routing-matrix.yaml`. Source action for `codex_latency_p95_s` predicate aggregator (divide `wall_clock_ms` by 1000 to recover seconds). T-4 archetype-spoofing forensic trail (`dispatcher-routes-summary` Phase 6 audit-query.py sub-command). Sec MF-3 invariant: NEVER persist task description / archetype profile body / skill content / raw file paths. Registered with `KERNEL_OVERRIDE` bypass since `audit_emit.py` is in `_KERNEL_PATHS`. |
| `pair_rail_case` (v2.23) | `action`, `case` (str — closed enum: `A` / `B` / `C` / `D` / `E` / `F` per spec.md §11 asymmetric matrix), `claude_verdict` (str — closed enum: `PASS` / `BLOCK`), `codex_verdict` (str — closed enum: `PASS` / `BLOCK` / `ADVISORY` / `TIMEOUT` / `MALFORMED`), `tool_name` (str ≤32 — closed enum: `Edit` / `Write` / `MultiEdit` / `NotebookEdit` / `unknown`), `file_path_hash_prefix` (str — 16-hex SHA-256 prefix of target file path; raw path forbidden per LLM06 side-channel guard), `precondition_met` (bool — Case-B requires file:line cited + rubric_violation_id ∈ catalogue + severity ∈ {P0, P1}), `rubric_violation_id` (str ≤64 — enumerated ID from `.claude/policies/rubric-violation-catalogue.yaml` or empty when not Case-B; free-form rubric IDs are sanitized to `unknown_rubric_id`), `severity` (str — closed enum: `P0` / `P1` / empty), `jaccard_similarity_bucket` (str — closed enum: `<=0.3` / `0.3-0.5` / `0.5-0.8` / `>0.8` / empty; raw float forbidden per Sec MF-3), `human_triage_grace_h` (int ≥0 — hours remaining in 24h grace window per R1 S-TDE-4; 0 = grace expired = closes-as-advisory; CEO_PAIR_RAIL_HUMAN_TRIAGE_HOURS env override), `session_id`, `project`, `event_schema`, `ts`, plus baseline HMAC-chain invariant. PLAN-081 Phase 3 (S100 ceremony 2026-05-10) — emitted by `.claude/hooks/check_pair_rail.py:_decide_with_matrix()` once per Pair-Rail PreToolUse evaluation that reaches the matrix arm (write tool + L3+ path + no sentinel bypass). Source action for `fp_rate_30d` and `disagreement_rate_30d` predicate aggregators. ADR-107 + ADR-108 ACCEPTED gate. Sec MF-3 invariant: NEVER persist raw Codex review body / proposed-content / file path. Registered with `KERNEL_OVERRIDE` bypass since `audit_emit.py` is in `_KERNEL_PATHS`. |
| `pair_rail_promotion` (v2.23) | `action`, `run_id` (str ≤36 — UUID hex), `verdict` (str — closed enum: `PASS` / `PASS_AFTER_RETRY` / `TRIAGE` / `FAIL`), `corpus_n` (int ≥0), `corpus_manifest_sha` (str — 16-hex prefix), `catch_rate_num` (int ≥0), `catch_rate_den` (int ≥1), `fp_rate_bucket` (str — closed enum: `<=15%` / `15-30%` / `>30%` / empty), `schema_adherence_pct_bucket` (str — closed enum: `100%` / `95-99%` / `<95%` / empty), `rubric_gap_pp_bucket` (str — closed enum: `<=0pp` / `0-5pp` / `5-10pp` / `>10pp` / empty), `codex_cli_version` (str ≤32), `python_version` (str ≤16), `git_head_sha_prefix` (str — 12-hex prefix), `pass_2_retry_used` (bool), `manual_triage` (bool), `session_id`, `project`, `event_schema`, `ts`, plus baseline HMAC-chain invariant. PLAN-081 Phase 4 (S100 ceremony 2026-05-10) — emitted by `.claude/scripts/run-promotion-gate.py` at end of each locked-corpus promotion-gate run. Source for `u7_rubric_gap_pp` predicate aggregator. ADR-111 ACCEPTED gate. Sec MF-3 invariant: NEVER persist raw fixture content / Codex review body / proposed-content. Registered with `KERNEL_OVERRIDE` bypass. |
| `token_budget_guard_paused` (v2.24) | `action`, `plan_id` (str — `^PLAN-[0-9]{3}$`), `estimate_tokens` (int ≥0), `actual_tokens` (int ≥0), `ratio_basis_points` (int ≥0 — actual/estimate×1000, canonical_json no-float invariant), `threshold_basis_points` (int ≥0), `session_id`, `project`, `event_schema`, `ts`, plus baseline HMAC-chain invariant. Emitted by `.claude/scripts/token-budget-guard.py` when cumulative plan tokens cross threshold × estimate from sub-agent 0.2 token-estimator. Volume cap ≤10/hr sliding window per AC5c. Sec MF-3 invariant: NEVER persist token TEXT content, prompt body, file paths, estimator metadata, env values. PLAN-083 Wave 0b sub-agent 0.4 (S106 2026-05-11). Atomic 4-source registration per S100 L6 lesson. |
| `anti_ceo_overhead_block` (v2.24) | `action`, `anti_pattern_id` (str — closed enum from P1-P5 predicate set), `count_in_window` (int ≥0 — events in 5-min sliding window), `override_recommended_subagent_type` (str ≤64 — suggested archetype to delegate to), `session_id`, `project`, `event_schema`, `ts`, plus baseline HMAC-chain invariant. Emitted by `.claude/hooks/check_anti_ceo_overhead.py` PreToolUse when CEO-overhead anti-pattern detected (P1 sequential SKILL.md reads / P2 unrelated edits / P3 serial schema authoring / P4 grep-find spam / P5 cross-module tests). Emit budget ≤20/day. Sec MF-3 invariant: NEVER persist tool input content / file paths. PLAN-083 Wave 0a sub-agent 0.5 (S106 2026-05-11). Atomic 4-source registration per S100 L6 lesson. |
| `anti_ceo_overhead_override_used` (v2.24) | `action`, `anti_pattern_id` (str), `override_justification_sha` (str — sha256 of justification, raw justification forbidden), `session_id`, `project`, `event_schema`, `ts`, plus baseline HMAC-chain invariant. Emitted by `.claude/hooks/check_anti_ceo_overhead.py` when `CEO_OVERHEAD_ACK=1` env override bypasses a block. Forensic trail of bypass usage. PLAN-083 Wave 0a sub-agent 0.5 (S106 2026-05-11). Atomic 4-source registration per S100 L6 lesson. |
| `smart_loading_resolved` (v2.24) | `action`, `profile` (str — closed enum: `frontend` / `engine` / `fintech` / `trading-readonly` / `generic`), `active_count` (int ≥0 — skills active after resolver), `suppressed_count` (int ≥0 — dormant/cap-dropped skills), `context_total_tokens` (int ≥0 — sum of context_budget_tokens across active set), `arbitration_dropped_count` (int ≥0 — duplicate-trigger losers), `session_id`, `project`, `event_schema`, `ts`, plus baseline HMAC-chain invariant. Emitted by `.claude/scripts/smart-loading-resolver.py` per resolution. Sec MF-3 invariant: NEVER persist skill names / paths / content. PLAN-083 Wave 0b sub-agent 0.7d (S106 2026-05-11). Atomic 4-source registration per S100 L6 lesson. |
| `first_run_wizard_completed` (v2.24) | `action`, `profile` (str — closed enum from `smart_loading_resolved`), `recommendation_count` (int ≥0 — top-3 recommendations rendered), `user_action` (str — closed enum: `Y` / `n` / `customize` / `--no-interactive`), `session_id`, `project`, `event_schema`, `ts`, plus baseline HMAC-chain invariant. Emitted by `.claude/scripts/first-run-wizard.py` at end of 4-step detect→explain→recommend→ask flow. Sec MF-3 invariant: NEVER persist skill names / paths / user choices verbatim. PLAN-083 Wave 2 sub-agent 2.1 (S106 2026-05-11). Atomic 4-source registration per S100 L6 lesson. |
| `contextual_recommendation_emitted` (v2.24) | `action`, `profile` (str), `recommendation_count` (int ≥0 — strict top-3 cap), `top_score` (int ≥0 — score of #1 recommendation), `suppressed_count` (int ≥0 — dormant filtered + cap-dropped), `session_id`, `project`, `event_schema`, `ts`, plus baseline HMAC-chain invariant. Emitted by `.claude/scripts/contextual-recommender.py` per `recommend()` call. Reuses smart-loading-resolver active set + confidence_labels classifier. Sec MF-3 invariant: NEVER persist skill names / file context / user query. PLAN-083 Wave 2 sub-agent 2.2 (S106 2026-05-11). Atomic 4-source registration per S100 L6 lesson. |
| `value_dashboard_summarized` (v2.24) | `action`, `period_days` (int ≥1 — rollup window), `cost_usd_int_cents` (int ≥0 — total USD × 100; canonical_json no-float), `bugs_count` (int ≥0 — aggregated across 6 governance actions), `dispatches_count` (int ≥0), `plans_count` (int ≥0 — distinct plan_ids), `session_id`, `project`, `event_schema`, `ts`, plus baseline HMAC-chain invariant. Emitted by `.claude/scripts/value-dashboard.py` per `rollup_value()`. Hours-saved estimate framed as ESTIMATE not actual per Codex P1. Sec MF-3 invariant: NEVER persist audit content / file paths / raw cost calculations. PLAN-083 Wave 2 sub-agent 2.4 (S106 2026-05-11). Atomic 4-source registration per S100 L6 lesson. |
| `trading_write_override_used` (v2.24) | `action`, `allowed` (bool — true if override granted), `reason` (str ≤32 — closed enum: `ok` / `not_in_trading_profile` / `env_var_missing` / `justification_too_short` / `justification_too_long` / `justification_missing` / `target_path_invalid` / `target_path_is_glob` / `profile_missing` / `profile_malformed` / `risk_class_missing` / `risk_class_unknown` / `kill_switch_status_check`), `target_path_sha256_prefix` (str — 16-hex sha256 prefix of target file path; raw path FORBIDDEN per Sec MF-3 / Codex P0), `justification_sha256_prefix` (str — 16-hex sha256 prefix of Owner-supplied justification; raw justification body NEVER persisted), `justification_length` (int ≥0 — bounded length only, no content), `err_preview` (str ≤80 OPTIONAL — exception preview on path resolution failure; NO raw paths), `session_id`, `project`, `event_schema`, `ts`, plus baseline HMAC-chain invariant. Emitted by `.claude/scripts/trading-readonly-guardrails.py` when `check_write_override()` accepts an override. Volume cap ≤5/day per AC5c. Atomic register per S100 L6. PLAN-083 Wave 2 sub-agent 2.7 (S106 2026-05-11). Atomic 4-source registration per S100 L6 lesson. |
| `trading_kill_switch_invoked` (v2.24) | `action`, `reason` (str — closed enum: `missing_repo_profile_yaml` / `unknown_needs_confirmation` / `malformed_yaml`), `session_id`, `project`, `event_schema`, `ts`, plus baseline HMAC-chain invariant. Emitted by `.claude/scripts/trading-readonly-guardrails.py` on every `kill_switch_disabled()` read. FAIL-CLOSED invariant: missing repo-profile.yaml DISABLES framework trading actions entirely, does NOT downgrade to generic. Sec MF-3 invariant: NEVER persist file paths / profile content. PLAN-083 Wave 2 sub-agent 2.7 (S106 2026-05-11). Atomic 4-source registration per S100 L6 lesson. |
| `trading_kill_switch_disabled` (v2.24) | `action`, `justification_sha256_prefix` (str — 16-hex sha256 prefix of escape-hatch justification.md content; raw body NEVER persisted), `signer_fingerprint_prefix` (str — 16-hex prefix of Owner GPG fingerprint), `signed_new` (bool — true if .asc freshly created, false if reused via idempotency check), `justification_length` (int ≥0 — bounded length), `session_id`, `project`, `event_schema`, `ts`, plus baseline HMAC-chain invariant. Emitted by `scripts/local/trading-readonly-escape-hatch.sh` ceremony only — explicit Owner ceremony to escape FAIL-CLOSED kill-switch. Idempotent (.asc verify → reuse). Sec MF-3 invariant: NEVER persist justification body content. PLAN-083 Wave 2 sub-agent 2.7 (S106 2026-05-11). Atomic 4-source registration per S100 L6 lesson. |

| `live_adapter_blocked` (v2.25) | `action`, `provider`, `reason` (enum `{not_in_allowlist, allowlist_unreadable, empty_allowlist}`), `atlas_technique` (str `AML.T0049`), `session_id`, `project`, `event_schema`, `ts`. PLAN-085 Wave C.1 (S111 2026-05-12) — ADR-040 §6.3 live_adapter_allowlist runtime gate. ATLAS mapping: AML.T0049 (Exploit Public-Facing Application). |
| `credential_blocked_due_to_age` (v2.25) | `action`, `provider`, `age_days` (int ≥0), `max_age_days` (int ≥0), `session_id`, `project`, `event_schema`, `ts`. PLAN-085 Wave C.2 (S111 2026-05-12) — ADR-040 §4 + ADR-040-AMEND-2 credential lifecycle blocking. Paired with raising `CredentialExpired` from `_lib.exceptions`. |
| `credential_emergency_override_used` (v2.25) | `action`, `provider`, `ticket_id` (str ≤64 — Owner-supplied ops ticket correlation key; raw credential value NEVER persisted), `age_days` (int ≥0), `max_age_days` (int ≥0), `session_id`, `project`, `event_schema`, `ts`. PLAN-085 Wave C.2 (S111 2026-05-12) — ADR-040-AMEND-2 §emergency-override 24h window. As of PLAN-117 WS-A (S176) the override `ticket_id` is sourced SOLELY from the trust-root snapshot and matches `^[A-Z][A-Z0-9]*-\d+$` (letter-led project prefix, e.g. `INC-1234` / `SEV1-42`). |
| `credential_override_late_set_ignored` (v2.35) | `action`, `provider`, `attempted_var_name` (str — FORCED by the emit_generic dispatch gate to the constant env-var name; NOT caller-supplied, so the rejected override VALUE can never be smuggled through this field), `provenance_hint` (str — closed enum, persisted values: `late_os_environ_set` / `spawn_payload_env` / `subprocess_inherited` / `unspecified`; a caller-supplied value outside the first three is COERCED to `unspecified` at the dispatch gate — the rejected value is never echoed; the Layer-1 consumer only ever emits `late_os_environ_set`, `spawn_payload_env` + `subprocess_inherited` are forward-reserved for Layers 2-3, and `unspecified` is the defensive coercion sentinel), `session_id`, `project`, `event_schema`, `ts`. PLAN-117 WS-A (S176 2026-05-27) — ADR-040-AMEND-2 §Layer-1 forensic: an emergency-override value present in LIVE env but ABSENT from the import-time trust-root snapshot (set post-anchor) was IGNORED, not honored. Live `os.environ` is NOT the override source (snapshot-as-SOLE-source). Constant breadcrumb — rejected value never echoed. |
| `mcp_bearer_replay_rejected` (v2.25) | `action`, `reason` (enum `{stale_iat, nonce_reused, stale_iat_and_nonce_reused}`), `nonce_prefix` (str ≤8 — 8-hex prefix for correlation; full nonce NEVER persisted), `session_id`, `project`, `event_schema`, `ts`. PLAN-085 Wave C.3 (S111 2026-05-12) — MCP bearer-token replay defense (loopback-only, 60s skew). |
| `mcp_non_loopback_rejected` (v2.25) | `action`, `remote_addr_family` (enum `{ipv4, ipv6, other}`), `session_id`, `project`, `event_schema`, `ts`. PLAN-085 Wave C.3 (S111 2026-05-12) — handler-entry fail-CLOSED for non-loopback bearer-token requests. Raw remote_addr NEVER logged. |
| `prompt_injection_detected` (v2.25) | `action`, `atlas_technique` (str `AML.T0051`), `signal` (str ≤64), `family` (str ≤64), `snippet_preview` (str ≤200, redacted), `match_count` (int ≥0), `bytes_scanned` (int ≥0), `triggered_by_tool` (str ≤50), `session_id`, `project`, `event_schema`, `ts`. PLAN-085 Wave G.1b (S111 2026-05-12). ATLAS mapping: AML.T0051 (LLM Prompt Injection). |
| `secret_leak_detected` (v2.25) | `action`, `atlas_technique` (str `AML.T0024.001`), `signal` (str ≤64), `family` (str ≤64), `snippet_preview` (str ≤200, redacted), `match_count` (int ≥0), `bytes_scanned` (int ≥0), `triggered_by_tool` (str ≤50), `session_id`, `project`, `event_schema`, `ts`. PLAN-085 Wave G.1b (S111 2026-05-12). ATLAS mapping: AML.T0024.001 (Data Exfiltration: LLM Data Leakage). |
| `pii_redacted_outgoing` (v2.25) | `action`, `atlas_technique` (str `AML.T0048.004`), `signal` (str ≤64), `family` (str ≤64), `match_count` (int ≥0), `bytes_scanned` (int ≥0), `session_id`, `project`, `event_schema`, `ts`. PLAN-085 Wave G.1b (S111 2026-05-12). ATLAS mapping: AML.T0048.004 (Erode ML Model Integrity: User-Injected Information). |
| `codex_egress_redacted` (v2.25) | `action`, `atlas_technique` (str `AML.T0054`), `signal` (str ≤64), `family` (str ≤64), `match_count` (int ≥0), `bytes_scanned` (int ≥0), `callsite` (str ≤200), `session_id`, `project`, `event_schema`, `ts`. PLAN-085 Wave G.1b (S111 2026-05-12). ATLAS mapping: AML.T0054 (LLM Jailbreak). Composition with Wave B.4 `compute_redaction_inputs` fail-CLOSED inversion. |
| `canonical_edit_completed` (v2.25) | `action`, `path` (str ≤300 — canonical guard path mutation observed via Bash write-shape operator), `sentinel_hint` (str ≤64 — `unsigned` or `sentinel-active:<N>`), `session_id`, `project`, `event_schema`, `ts`. PLAN-085 Wave E.4 (S111 2026-05-12) — PostToolUse Bash forensic advisory; emitted by `check_bash_canonical_forensic.py`. NEVER blocks (forensic trail only). |

| `canonical_edit_attempted` | `action`, `path` (str ≤300), `sentinel_path` (str ≤300, nullable), `result` (enum `{allowed, blocked}`), `session_id`, `project`, `event_schema`, `ts`. PLAN-084 Wave 0.5 (S107 ceremony). Emitted at canonical-edit hook entry. |
| `canonical_edit_blocked` | `action`, `path` (str ≤300), `reason` (str ≤120), `session_id`, `project`, `event_schema`, `ts`. PLAN-084 Wave 0.5 (S107 ceremony). |
| `gpg_signed` | `action`, `signed_path` (str ≤300), `signature_path` (str ≤300), `fingerprint_prefix` (str ≤16), `session_id`, `project`, `event_schema`, `ts`. PLAN-084 Wave 0.5 (S107 ceremony). |
| `gpg_verified` | `action`, `verified_path` (str ≤300), `fingerprint_prefix` (str ≤16), `result` (enum `{good, bad, no_signers, no_signature}`), `session_id`, `project`, `event_schema`, `ts`. PLAN-084 Wave 0.5 (S107 ceremony). |
| `sentinel_created` | `action`, `sentinel_path` (str ≤300), `plan_id` (str ≤16), `round_or_wave` (str ≤32), `scope_path_count` (int ≥0), `session_id`, `project`, `event_schema`, `ts`. PLAN-084 Wave 0.5 (S107 ceremony). |
| `sentinel_verified` | `action`, `sentinel_path` (str ≤300), `fingerprint_prefix` (str ≤16), `target_path` (str ≤300), `result` (enum `{granted, denied, no_scope_match, bad_signature}`), `session_id`, `project`, `event_schema`, `ts`. PLAN-084 Wave 0.5 (S107 ceremony). |
| `wave_artifact_written` | `action`, `plan_id` (str ≤16), `wave_label` (str ≤32), `artifact_path` (str ≤300), `bytes_written` (int ≥0), `session_id`, `project`, `event_schema`, `ts`. PLAN-084 Wave 0.10 (S107 ceremony) — R2-iter-2 CODEX-P0-2 staging artifact integrity. |
| `wave_readonly_violation` | `action`, `plan_id` (str ≤16), `wave_label` (str ≤32), `target_path` (str ≤300), `attempted_operation` (str ≤64), `session_id`, `project`, `event_schema`, `ts`. PLAN-084 Wave 0.10. Read-only night discipline. |
| `pair_rail_outgoing_redaction_applied` | `action`, `tool_name` (str ≤50), `family_ids` (list[str]), `match_count` (int ≥0), `first_offset_bucket` (str closed-enum per pair_rail_codex_injection_detected schema), `session_id`, `project`, `event_schema`, `ts`. PLAN-084 Wave 0.5 (S107) — R1 Sec-P0-2 mirror of pair_rail_codex_injection_detected for outgoing direction. |
| `estimate_refined` | `action`, `plan_id` (str ≤16), `phase_label` (str ≤32), `prior_estimate_tokens` (int ≥0), `posterior_estimate_tokens` (int ≥0), `delta_pct` (int — can be negative), `session_id`, `project`, `event_schema`, `ts`. PLAN-084 AC12d — Bayesian-ish estimate refinement per phase milestone. |
| `anthropic_429_observed` (v2.26) | `action`, `model` (str ≤32), `retry_after_s` (int ≥0), `breaker_state` (str — closed enum: `closed` / `open` / `half_open`), `provider` (str ≤16), `session_id`, `project`, `event_schema`, `ts`. PLAN-086 Wave B (S112 2026-05-12) — Anthropic API 429 rate-limit observation by live adapter; advisory (the adapter does its own back-off + breaker bookkeeping). |
| `codex-reply` (v2.26) | `action`, `session_id` (str ≤36), `chain_step` (int ≥0), `prior_action` (str ≤64), `project`, `event_schema`, `ts`. PLAN-086 Wave C (S112 2026-05-12) — Codex reply session-id chain integrity advisory; emitted when a `mcp__codex__codex-reply` invocation references a session prior emit reported. |
| `codex_invoke_dispatched` (v2.26) | `action`, `session_id` (str ≤36), `task_class` (str ≤32), `model_advised` (str ≤32), `phase` (str ≤16), `project`, `event_schema`, `ts`. PLAN-088 Wave 1 canonical-13 (S114 2026-05-13). ATLAS: AML.T0050 (LLM Plugin / supply-chain signal). |
| `git_index_lock_retry` (v2.26) | `action`, `attempt` (int ≥0), `wait_ms` (int ≥0), `outcome` (str — closed enum: `acquired` / `timeout` / `aborted`), `session_id`, `project`, `event_schema`, `ts`. PLAN-086 Wave G (S112 2026-05-12) — git index.lock retry breadcrumb (advisory). |
| `mcp_canonical_guard_internal_error` (v2.26) | `action`, `tool_name` (str ≤50), `error_class` (str ≤64), `error_brief` (str ≤200 — bounded preview; raw traceback FORBIDDEN), `session_id`, `project`, `event_schema`, `ts`. PLAN-086 Wave D (S112 2026-05-12) — MCP canonical-guard internal-error breadcrumb (fail-open invariant). |
| `mcp_route_advised` (v2.26) | `action`, `session_id` (str ≤36), `task_class` (str ≤32), `suggested_servers` (str ≤128 — comma-joined bundle of MCP server names), `kill_switch_overrides` (str ≤128), `signal_source` (str — closed enum: `mcp_task_class` / `specialization_promoted` per PLAN-088 R2 iter-2 strict-13 discriminator), `project`, `event_schema`, `ts`. PLAN-086 Wave D (S112 2026-05-12) — MCP routing advisory emitted by `_lib/mcp_routing.resolve()`. PLAN-088 R2 iter-2 single canonical action covers both AUTO-06 MCP routing AND AUTO-10 general→specialized promotion via `signal_source` discriminator. ATLAS: AML.T0050. |
| `repo_profile_confirmed` (v2.26) | `action`, `profile_slug` (str ≤32), `confidence_basis_points` (int — 0-1000), `caller` (str ≤64), `session_id`, `project`, `event_schema`, `ts`. PLAN-086 Wave H (S112 2026-05-12) — repo-profile detector confirmation breadcrumb. |
| `subagent_findings_partial_drop` (v2.26) | `action`, `subagent_type` (str ≤64), `expected_count` (int ≥0), `actual_count` (int ≥0), `truncation_reason` (str — closed enum: `token_cap` / `time_cap` / `pipe_break`), `session_id`, `project`, `event_schema`, `ts`. PLAN-088 Wave 1 canonical-13 (S114 2026-05-13) — sub-agent dispatch returned partial findings. ATLAS: AML.T0048. |
| `thinking_budget_set` (v2.26) | `action`, `model` (str ≤32), `budget_tokens` (int ≥0), `rationale` (str — closed enum: `task_class_default` / `effort_override` / `opted_out_thinking_auto_disable` / `opted_out_multi_model_manual`), `source` (str — closed enum: `caller_kwarg` / `effort_env` / `task_class_default`), `session_id`, `project`, `event_schema`, `ts`. PLAN-086 Wave A R-013 (S112 2026-05-12) — extended-thinking budget configured for live adapter call. |
| `batch_dispatched` (v2.26) | `action`, `session_id` (str ≤36), `batch_size` (int ≥1), `model` (str ≤32), `policy` (str ≤64), `project`, `event_schema`, `ts`. PLAN-088 Wave 1 canonical-13 (S114 2026-05-13) — batch live-adapter dispatch breadcrumb; reserved for `BatchClaudeLiveAdapter` (PLAN-090 W4.2 production wire). |
| `cache_discipline_alerted` (v2.26) | `action`, `file_path` (str ≤300), `gate_tier` (str — closed enum: `gate_1` / `gate_2` / `gate_3`), `cost_estimate_basis_points` (int ≥0 — cost-of-invalidation × 1000), `session_id`, `project`, `event_schema`, `ts`. PLAN-088 Wave 1 canonical-13 (S114 2026-05-13) — cache-discipline alert breadcrumb; reserved for cache-tier observation when a Gate-1 file edit invalidates the prompt cache mid-session. |
| `cookbook_pattern_advised` (v2.26) | `action`, `pattern_slug` (str ≤64), `recommendation_origin` (str — closed enum: `auto_detector` / `manual_invocation` / `audit_query`), `applied` (str — closed enum: `advisory_only` / `applied` / `dismissed`), `session_id`, `project`, `event_schema`, `ts`. PLAN-088 Wave 1 canonical-13 (S114 2026-05-13) — cookbook pattern advisory (SEMI-11; real wire deferred to PLAN-092). |
| `estimate_calibrator_pipeline_run` (v2.26) | `action`, `plan_id` (str — `^PLAN-[0-9]{3}$`), `iters` (int ≥0), `posterior_mean_ms` (int ≥0), `posterior_p95_ms` (int ≥0), `session_id`, `project`, `event_schema`, `ts`. PLAN-088 Wave 6 (S114 2026-05-13) — Bayesian estimate-calibrator pipeline run; emitted by `_lib/estimation/pipeline.py`. |
| `first_run_wizard_dispatched` (v2.26) | `action`, `repo_profile` (str ≤32), `wizard_step` (str — closed enum: `detect` / `explain` / `recommend` / `ask`), `applied` (str — closed enum: `Y` / `n` / `customize` / `--no-interactive`), `session_id`, `project`, `event_schema`, `ts`. PLAN-088 Wave 1 canonical-13 (S114 2026-05-13) — first-run wizard dispatch breadcrumb; reserved for SessionStart auto-spawn callsite (PLAN-093 production wire). |
| `pair_rail_phase_advanced` (v2.26) | `action`, `prior_phase` (str — closed enum: `DISABLED` / `SHADOW` / `DRY_RUN`), `new_phase` (str — closed enum: `DISABLED` / `SHADOW` / `DRY_RUN`), `trigger` (str — closed enum: `env_override` / `sample_threshold` / `manual`), `samples_observed` (int ≥0), `session_id`, `project`, `event_schema`, `ts`. PLAN-088 Wave 1 canonical-13 (S114 2026-05-13) — Pair-Rail phase transition breadcrumb. ACTIVE phase deferred to PLAN-090. ATLAS: AML.T0050. |
| `tier_policy_misrouting_advised` (v2.26) | `action`, `task_class` (str ≤32), `expected_model` (str ≤32), `actual_model` (str ≤32), `ratio_basis_points` (int ≥0 — misrouting ratio × 1000), `session_id`, `project`, `event_schema`, `ts`. PLAN-088 Wave 1 canonical-13 (S114 2026-05-13) — tier-policy misrouting advisory breadcrumb. PLAN-091 A.1 16th Tier-S check `check_tier_policy_misrouting_24h` queries the 24h audit window for events of this kind. ATLAS: AML.T0048. |
| `tier_policy_loader_fallback_observed` (v2.34) | `action`, `reason_code` (str — closed enum: `advisory_safety_net` / `bad_mode` / `depth_limit` / `key_count` / `missing` / `not_object` / `open_failed` / `oversize` / `parse_error` / `read_failed` / `schema_mismatch` / `stat_error` / `type_mismatch` / `unknown_model`), `session_id`, `project`, `event_schema`, `ts`. PLAN-116 (S172 2026-05-27) — tier-policy loader advisory-only fallback telemetry. Replaces the PLAN-093 Wave C.3 `tier_policy_misrouting_advised` piggyback (which dropped a free-text `reason` field on every emit → audit-log.errors noise). NO ATLAS technique (loader telemetry, not a detection signal — distinct from `tier_policy_misrouting_advised`'s AML.T0048). |
| `audit_producer_path_pollution_detected` (v2.36) | `action`, `chokepoint` (str — closed enum: `chain_reset_marker` / `spool_drain`), `reason_code` (str — closed enum: `audit_emit_path_pollution` / `canonical_json_path_pollution` / `audit_hmac_path_pollution`), `path_sha256_prefix` (str — exactly 8 hex chars; sha256 prefix of the resolved non-canonical path), `expected_canonical_prefix` (str — exactly 8 hex chars; sha256 prefix of the canonical `_lib/` dir), `session_id`, `project`, `event_schema`, `ts`. PLAN-118 AC-B5 (S179 2026-05-28) — producer-side fail-CLOSED forensic breadcrumb. Emitted when `audit_hmac._ensure_canonical_lib_modules()` (invoked at chokepoints 1/3/4/5 per PLAN-118 §Producer runtime fail-CLOSED layer) detects that any of `_lib.audit_emit` / `_lib.canonical_json` / `_lib.audit_hmac` resolves to a non-canonical `_lib/` parent on disk (i.e. a stale `_lib` copy has been injected onto `sys.path`). The producer refuses to compute HMAC (fail-CLOSED for the chain — no signed bytes leak under stale canonicalization); the host hook line is written with `hmac:null` + `hmac_error=producer_path_pollution_detected` (fail-OPEN — user session NEVER blocked). NO `__file__` raw echo per [[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]] (S172) — only sha256[:8] prefixes. NO ATLAS technique (defensive integrity guard, not an attack signal). Registered via kernel-override sentinel `PLAN-118-WS-B-CHOKEPOINTS`. |
| `tool_call_lifecycle_recorded` (v2.37) | `action`, `session_id`, `project`, `tool_name_enum` (str — CLOSED enum: `Agent` / `Task` / `Bash` / `Edit` / `MultiEdit` / `Write` / `Read` / `Glob` / `Grep` / `WebFetch` / `WebSearch` / `NotebookEdit` / `TodoWrite` / `mcp_other` / `other`; ALL `mcp__<server>__<tool>` collapse to `mcp_other` — the raw MCP tool string is FORBIDDEN on the wire, MF-SEC-1; unknown → `other`), `duration_bucket` (str — CLOSED enum: `lt_100ms` / `b_100ms_1s` / `b_1_10s` / `b_10_60s` / `gt_60s`; the raw `duration_ms` integer is FORBIDDEN — timing side-channel, MF-SEC-3), `success` (bool — `PostToolUseFailure` → false; no marker scan), `orphan` (bool — bounded sweeper sets true when no Post/Failure arrives within T=30s, MF-PERF-3), `event_schema`, `ts`, plus the baseline HMAC chain. PLAN-125 WS-1 (kooky-harvest, S20x) — per-tool-call lifecycle telemetry. Emitted via `emit_tool_call_lifecycle_recorded` on PostToolUse / PostToolUseFailure (success / failure) + the bounded orphan sweeper. Routes through the dedicated `_scrub_*` branch + `_TOOL_CALL_LIFECYCLE_RECORDED_ALLOWLIST` frozenset, NEVER `_EMIT_GENERIC_PASSTHROUGH` (MF-SEC-2). The PreToolUse pairing record is written to a 0600 per-session file and emits NO audit-chain event (MF-SEC-5). DENIED on the wire: raw tool name, raw duration, prompt / command / path / output bodies. NO ATLAS technique (observability telemetry, not a detection signal). |
| `git_hook_bypass_blocked` (v2.38) | `action`, `session_id`, `project`, `flag_class` (str — CLOSED enum: `no_verify_commit` / `no_verify_other_subcmd` / `hookspath_inline` / `hookspath_config_write` / `git_config_env_channel` / `git_dir_redirect` / `alias_abuse` / `parse_failure` / `escape_hatch_used`; the matched COMMAND BYTES are FORBIDDEN on the wire, MF-G — a flag value such as `-c http.extraHeader="Bearer <secret>"` is a secret; an unrecognized value is COERCED to `parse_failure`), `event_schema`, `ts`, plus the baseline HMAC chain. PLAN-124 WS-1 (ECC value-harvest, S20x) — git hook-bypass guard breadcrumb. Emitted by `check_bash_safety.py` (PreToolUse Bash) via `emit_git_hook_bypass_blocked` when the `_lib/git_bypass.py` tokenizer blocks a `--no-verify` (6 subcommands: commit/push/merge/cherry-pick/rebase/am; `-n` counts only for commit, push `-n` is `--dry-run` and PASSES) / inline `-c core.hooksPath=` / `git config` core.hooksPath WRITE (split attack) / `GIT_CONFIG_COUNT`+`GIT_CONFIG_KEY_<n>` env channel / `--git-dir`/`-C` redirect / `-c alias.X=` smuggle, AND when the proven dual-auth escape hatch (`CEO_GIT_BYPASS_ALLOW` + `_ACK=I-ACCEPT` + ticket regex, read from the import-time `trusted_env` snapshot per ADR-040-AMEND-2 §Layer-1) ALLOWS one (`flag_class=escape_hatch_used`). An unparseable command that clearly invokes git is fail-CLOSED blocked (`parse_failure`, MF-L). Routes through the dedicated `_scrub_*` branch + `_GIT_HOOK_BYPASS_BLOCKED_ALLOWLIST` frozenset, NEVER `_EMIT_GENERIC_PASSTHROUGH` ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]). DENIED on the wire: the matched flag value, command / message / path bodies. NO ATLAS technique (governance breadcrumb, not a detection signal). |
| `verify_after_edit_finding` (v2.39) | `action`, `session_id`, `checker` (str — CLOSED enum: `py_compile` / `ruff` / `eslint` / `node_check` / `go_build` / `other`; unrecognized value COERCED to `other`, never echoed), `lang` (str — CLOSED enum: `python` / `js_ts` / `go` / `other`), `finding_count` (int 0..99 — clamped), `project`, `event_schema`, `ts`, plus baseline `tokens_in`/`tokens_out`/`tokens_total`/`hmac`/`hmac_error` added by `_write_event` AFTER the scrub. PLAN-128 §7 (S217) — accelerator catch telemetry. Emitted fail-open by `verify_after_edit.py` (PostToolUse via `accel_dispatch.py`) once per dispatch when ≥1 real finding surfaces. Routes through the dedicated dispatch-gate branch + `_VERIFY_AFTER_EDIT_FINDING_ALLOWLIST` (enum coercion + 0..99 clamp; [[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]). DENIED on the wire: file paths, source / diff bodies, checker error text, `tokens_*` side channel. NO ATLAS technique (developer-productivity telemetry, not a detection signal). |
| `adequacy_gate_flag` (v2.39) | `action`, `session_id`, `flag_reason` (str — CLOSED enum: `no_test_delta` / `weak_assertion` / `uncovered_change` / `other`; unrecognized → `other`), `lang` (str — CLOSED enum: `python` / `js_ts` / `go` / `other`), `flag_count` (int 0..99 — clamped), `project`, `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error` added by `_write_event` AFTER the scrub. PLAN-128 §7 (S217) — accelerator test-adequacy telemetry. Emitted fail-open by `adequacy_gate.py` (opt-in `CEO_ADEQUACY_GATE=1`) when a change's tests weakly constrain it (mutation-kill rate below threshold). Routes through the dedicated dispatch-gate branch + `_ADEQUACY_GATE_FLAG_ALLOWLIST` (enum coercion + 0..99 clamp). DENIED on the wire: file paths, source / AST bodies, `tokens_*` side channel. NO ATLAS technique (developer-productivity telemetry, not a detection signal). |
| `audit_flush_dropped_count` (v2.27) | `action`, `begin_no_commit`, `commit_no_drained`, `recovered`, `truly_lost`, `tamper_rejected`, `intentionally_deleted`, `event_schema`, `ts`. PLAN-094 / ADR-055-AMEND-1 — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `audit_spool_duplicate_tuple_rejected` (v2.27) | `action`, `spool_uuid`, `record_id`, `ordinal`, `drain_epoch`, `event_schema`, `ts`. PLAN-094 / ADR-055-AMEND-1 — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `audit_spool_intentionally_deleted` (v2.27) | `action`, `spool_uuid`, `spool_pid`, `drain_epoch`, `event_schema`, `ts`. PLAN-094 / ADR-055-AMEND-1 — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `audit_spool_partial_line_discarded` (v2.27) | `action`, `spool_uuid`, `spool_pid`, `drain_epoch`, `byte_offset`, `event_schema`, `ts`. PLAN-094 / ADR-055-AMEND-1 — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `audit_spool_stale_recovered` (v2.27) | `action`, `spool_uuid`, `spool_pid`, `age_seconds`, `events_recovered`, `drain_epoch`, `event_schema`, `ts`. PLAN-094 / ADR-055-AMEND-1 — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `audit_spool_tamper_detected` (v2.27) | `action`, `mismatch_kind`, `spool_uuid`, `spool_pid`, `drain_epoch`, `corrupt_path`, `event_schema`, `ts`. PLAN-094 / ADR-055-AMEND-1 — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `audit_spool_unexpected_skip` (v2.27) | `action`, `spool_uuid`, `spool_pid`, `drain_epoch`, `severity`, `drain_in_recovery_mode`, `event_schema`, `ts`. PLAN-094 / ADR-055-AMEND-1 — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `bash_canonical_bypass_invoked` (v2.27; P1-fix S163) | `action`, `token_hash_prefix`, `target_path_hash`, `ticket_expires_in_s`, `atlas_technique`, `event_schema`, `ts`. PLAN-085 Wave E (S111) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). Sec MF-3 P1 fix (PLAN-113 Codex): `target_path_preview` (raw filesystem path) replaced by `target_path_hash` (12-hex sha256 prefix of the normalized target; no path body persisted). |
| `capability_rollout_complete` (v2.27) | `action`, `ac_pass_count`, `auto_primitives_enforcing`, `hmac`, `hmac_error`, `project`, `semi_primitives_advisory`, `session_id`, `tag`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-099 Federation (S134) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `ceo_boot_persona_coverage_score` (v2.27) | `action`, `score_x100`, `cells_covered`, `total_cells`, `session_id`, `project`, `event_schema`, `ts`. PLAN-091 16th Tier-S check (S115) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `confidence_gate_baseline_emitted` (v2.27) | `action`, `distinct_classes`, `hmac`, `hmac_error`, `insufficient_data_classes`, `project`, `rows_total`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-100 confidence-gate per-class (S139) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `confidence_gate_blocked` (v2.27) | `action`, `_drain_epoch`, `_drain_sha256`, `agent_name`, `blocking_classes`, `fail_count`, `hmac`, `hmac_error`, `ordinal_within_file`, `pid`, `project`, `record_id`, `session_id`, `source`, `spool_uuid`, `tokens_in`, `tokens_out`, `tokens_total`, `wall_ns`, `event_schema`, `ts`. PLAN-100 confidence-gate per-class (S139) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `confidence_gate_fp_drift_detected` (v2.27) | `action`, `_drain_epoch`, `_drain_sha256`, `agent_name`, `auto_demote_at`, `drift_class`, `fpr_bps`, `hmac`, `hmac_error`, `ordinal_within_file`, `pid`, `project`, `record_id`, `sample_n`, `session_id`, `source`, `spool_uuid`, `threshold_bps`, `tokens_in`, `tokens_out`, `tokens_total`, `wall_ns`, `window_days`, `event_schema`, `ts`. PLAN-100 confidence-gate per-class (S139) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `cost_envelope_capped` (v2.27) | `action`, `cap_cents`, `class_tier`, `current_cents`, `hmac`, `hmac_error`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `window_breached`, `event_schema`, `ts`. PLAN-102 autonomous-loop opt-in (S142) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `execution_context_signed` (v2.27) | `action`, `context_hash`, `hmac`, `hmac_error`, `iteration`, `key_id`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-102 autonomous-loop opt-in (S142) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). **RESERVED — zero producers; cross-process wiring DEFERRED per PLAN-112-FOLLOWUP-execution-context-wire (S154, finding F-1.2-execution_context). Re-wire needs coordinator-exits-scaffold + ADR-133-AMEND-1.** |
| `execution_context_validation_failed` (v2.27) | `action`, `context_hash`, `failure_reason`, `hmac`, `hmac_error`, `iteration`, `key_id`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-102 autonomous-loop opt-in (S142) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). **RESERVED — zero producers; cross-process wiring DEFERRED per PLAN-112-FOLLOWUP-execution-context-wire (S154, finding F-1.2-execution_context). Re-wire needs coordinator-exits-scaffold + ADR-133-AMEND-1.** |
| `federation_autonomous_call_blocked` (v2.27) | `action`, `call_site`, `session_id`, `project`, `event_schema`, `ts`. PLAN-099 Federation MVP / ADR-129 / ADR-135 (S134) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `federation_cert_expiry_warned` (v2.27) | `action`, `peer_id`, `days_remaining`, `session_id`, `project`, `event_schema`, `ts`. PLAN-099 Federation MVP / ADR-129 / ADR-135 (S134) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `federation_cert_revoked` (v2.27) | `action`, `peer_id`, `reason`, `session_id`, `project`, `event_schema`, `ts`. PLAN-099 Federation MVP / ADR-129 / ADR-135 (S134) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `federation_cert_rotated` (v2.27) | `action`, `peer_id`, `old_fingerprint_prefix`, `new_fingerprint_prefix`, `session_id`, `project`, `event_schema`, `ts`. PLAN-099 Federation MVP / ADR-129 / ADR-135 (S134) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `federation_connection_accepted` (v2.27) | `action`, `peer_id`, `client_ip`, `fed_correlation_id`, `session_id`, `project`, `event_schema`, `ts`. PLAN-099 Federation MVP / ADR-129 / ADR-135 (S134) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `federation_connection_rejected` (v2.27) | `action`, `reason`, `peer_id_cert_fingerprint`, `client_ip`, `session_id`, `project`, `event_schema`, `ts`. PLAN-099 Federation MVP / ADR-129 / ADR-135 (S134) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `federation_connection_replay_suspected` (v2.27) | `action`, `peer_id`, `reason`, `client_ip`, `session_id`, `project`, `event_schema`, `ts`. PLAN-099 Federation MVP / ADR-129 / ADR-135 (S134) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `federation_enable_sentinel_invalid` (v2.27) | `action`, `sentinel_kind`, `reason`, `session_id`, `project`, `event_schema`, `ts`. PLAN-099 Federation MVP / ADR-129 / ADR-135 (S134) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `federation_lan_bind_denied` (v2.27) | `action`, `bind_host`, `resolved_ip`, `reason`, `session_id`, `project`, `event_schema`, `ts`. PLAN-099 Federation MVP / ADR-129 / ADR-135 (S134) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `federation_write_attempt_blocked` (v2.27) | `action`, `method`, `path`, `peer_id_cert_fingerprint`, `client_ip`, `fed_correlation_id`, `session_id`, `project`, `event_schema`, `ts`. PLAN-099 Federation MVP / ADR-129 / ADR-135 (S134) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `goap_cycle_detected` (v2.27) | `action`, `state_hash`, `explored`, `session_id`, `project`, `event_schema`, `ts`. PLAN-098 GOAP A* planner / ADR-132 (S132) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `goap_depth_exceeded` (v2.27) | `action`, `state_hash`, `depth`, `session_id`, `project`, `event_schema`, `ts`. PLAN-098 GOAP A* planner / ADR-132 (S132) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `goap_disabled_by_env` (v2.27) | `action`, `session_id`, `project`, `event_schema`, `ts`. PLAN-098 GOAP A* planner / ADR-132 (S132) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `goap_edge_explored` (v2.27) | `action`, `from_state_hash`, `action_id`, `cost`, `frontier_size`, `session_id`, `project`, `event_schema`, `ts`. PLAN-098 GOAP A* planner / ADR-132 (S132) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `goap_recommendation_accepted` (v2.27) | `action`, `plan_id`, `action_id`, `session_id`, `project`, `event_schema`, `ts`. PLAN-098 GOAP A* planner / ADR-132 (S132) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `goap_recommendation_overridden` (v2.27) | `action`, `plan_id`, `original_action_id`, `dispatched_action_id`, `override_type`, `session_id`, `project`, `event_schema`, `ts`. PLAN-098 GOAP A* planner / ADR-132 (S132) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `goap_recommendation_rendered` (v2.27) | `action`, `plan_id`, `action_ids_csv`, `actions_rendered_count`, `goal_verb`, `goal_text_hash`, `session_id`, `project`, `event_schema`, `ts`. PLAN-098 GOAP A* planner / ADR-132 (S132) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `goap_replan_exhausted` (v2.27) | `action`, `attempt`, `session_id`, `project`, `plan_id`, `event_schema`, `ts`. PLAN-098 GOAP A* planner / ADR-132 (S132) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `goap_replan_triggered` (v2.27) | `action`, `attempt`, `state_hash`, `session_id`, `project`, `plan_id`, `event_schema`, `ts`. PLAN-098 GOAP A* planner / ADR-132 (S132) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `goap_search_aborted` (v2.27) | `action`, `reason`, `explored`, `elapsed_ms`, `session_id`, `project`, `event_schema`, `ts`. PLAN-098 GOAP A* planner / ADR-132 (S132) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `goap_search_summary` (v2.27) | `action`, `explored`, `cycles_rejected`, `terminus`, `elapsed_ms`, `plan_depth`, `session_id`, `project`, `event_schema`, `ts`. PLAN-098 GOAP A* planner / ADR-132 (S132) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `kernel_extension_landed` (v2.27) | `action`, `plan_id`, `wave`, `entries_added`, `cardinality_after`, `ceremony_sha`, `atlas_technique`, `event_schema`, `ts`. PLAN-106 burndown sweep (S143) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `kill_switch_invoked` (v2.27) | `action`, `env_value`, `hmac`, `hmac_error`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-099 Federation Tier-C kill-switch (S134) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `mcp_bearer_friction_observed` (v2.27) | `action`, `failure_reason`, `hmac`, `hmac_error`, `mcp_server`, `project`, `replay_suspected`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-085 Wave C.3 (S111) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `mcp_cross_tenant_denied` (v2.27) | `action`, `handler`, `caller_client_id_hash`, `target_client_id_hash`, `transport`, `session_id`, `project`, `event_schema`, `ts`. PLAN-085 Wave C.3 (S111) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `mcp_soak_fpr_breach` (v2.27, amended S163) | `action`, `window_days`, `fpr_observed_bps`, `threshold_bps`, `top_deny_reason`, `session_id`, `project`, `event_schema`, `ts`. PLAN-085 Wave G.1b (S111) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). Float fields re-encoded as int (×10000 bps) per canonical_json no-float invariant (S163 PLAN-113 Phase B). |
| `output_scan_finding_suppressed` (v2.27) | `action`, `command_sha`, `family`, `hmac`, `hmac_error`, `pattern_id`, `project`, `repo_path_hash`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `ttl_hours_remaining`, `event_schema`, `ts`. PLAN-106 Wave H output_scan_dedup (S143) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `persona_auto_decision_emitted` (v2.27) | `action`, `atlas_technique`, `decision`, `decision_rationale`, `hmac`, `hmac_error`, `persona`, `primitive`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-105 GOAP instrumentation (S135) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `persona_auto_rate_capped` (v2.27) | `action`, `dropped_count`, `hmac`, `hmac_error`, `persona`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-105 GOAP instrumentation (S135) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `persona_coverage_synthesized` (v2.27) | `action`, `archetype`, `cell_id`, `hmac`, `hmac_error`, `project`, `session_id`, `source`, `task_type`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-106 Wave C persona_coverage wire-up (S143) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `phase_c_enforcing_flipped` (v2.27) | `action`, `hmac`, `hmac_error`, `migration_phase`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `ts_unix`, `event_schema`, `ts`. PLAN-104 persona-demand ledger Phase 2 (S136) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `rag_auto_wire_skipped_sidecar_down` (v2.27) | `action`, `reason`, `session_id`, `project`, `event_schema`, `ts`. PLAN-097 RAG + first C2 vector-memory sidecar (S131) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `rag_false_large_demoted` (v2.27) | `action`, `false_large_rate_x100`, `window_days`, `session_id`, `project`, `event_schema`, `ts`. PLAN-097 RAG + first C2 vector-memory sidecar (S131) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `rag_hit_rate_degraded` (v2.27) | `action`, `hit_rate_x100`, `window_days`, `session_id`, `project`, `event_schema`, `ts`. PLAN-097 RAG + first C2 vector-memory sidecar (S131) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `rag_profile_recommended` (v2.27) | `action`, `profile`, `decision`, `session_id`, `project`, `event_schema`, `ts`. PLAN-097 RAG + first C2 vector-memory sidecar (S131) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `rag_query_routed` (v2.27) | `action`, `query_class`, `result`, `latency_ms_p50`, `session_id`, `project`, `event_schema`, `ts`. PLAN-097 RAG + first C2 vector-memory sidecar (S131) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `sentinel_signer_expiry_warned` (v2.27) | `action`, `key_id`, `days_remaining`, `expires_at_iso`, `atlas_technique`, `event_schema`, `ts`. PLAN-099 Federation (S134) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `sentinel_signer_quorum_attempted` (v2.27) | `action`, `distinct_signers`, `threshold_required`, `outcome`, `source`, `atlas_technique`, `event_schema`, `ts`. PLAN-099 Federation (S134) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `sentinel_signer_quorum_failed` (v2.27) | `action`, `key_id`, `reason`, `source`, `distinct_signers`, `threshold_required`, `atlas_technique`, `event_schema`, `ts`. PLAN-099 Federation (S134) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `sentinel_signer_revoked` (v2.27) | `action`, `key_id`, `key_type`, `revoked_by`, `reason`, `atlas_technique`, `event_schema`, `ts`. PLAN-099 Federation (S134) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `sentinel_signer_rotated` (v2.27) | `action`, `key_id`, `key_type`, `rotated_from_key_id`, `rotated_by`, `atlas_technique`, `event_schema`, `ts`. PLAN-099 Federation (S134) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `skill_cache_stats` (v2.27) | `action`, `hits`, `misses`, `evictions`, `size_bytes`, `duration_ms`, `event_schema`, `ts`. PLAN-094 Wave B.6 / R2 P1-8 (S121) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `streaming_rate_capped` (v2.27) | `action`, `dropped_count`, `hmac`, `hmac_error`, `persona`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-086 Wave A streaming primitives (S112) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `streaming_token_yielded` (v2.27) | `action`, `atlas_technique`, `hmac`, `hmac_error`, `persona`, `project`, `session_id`, `token_length`, `token_preview`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-086 Wave A streaming primitives (S112) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `stdlib_violation` (v2.28) | `action`, `violation_count`, `event_schema`, `ts`. PLAN-107 v1.38.0 Wave B.4 (S145 2026-05-19) — orphan emit register via kernel-override sentinel `PLAN-107-WAVE-B-ORPHAN-REGISTER`. Tracks `.claude/scripts/check-stdlib-only.py` invocations that detect stdlib violations; previously silently dropped via fail-open before `_KNOWN_ACTIONS` registration. |
| `swarm_layer_3_4_blocked` (v2.23) | `action`, `class_tier`, `reason_code`, `loop_id`, `hmac`, `hmac_error`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-102-FOLLOWUP v1.38.2 Wave B (S145 2026-05-19) — Layer 3+4 gate block emit via kernel-override sentinel `PLAN-102-FOLLOWUP-WAVE-A-AUDIT-EMIT-EXTENSION`. Emitted by `_emit_swarm_layer_3_4_blocked` in `swarm/loop_runner.py` when `is_class_enabled(class_tier)` returns `(False, <reason>)` AND `CEO_SWARM=1` (Layer-1 swarm-on env). 6-layer kill-switch chain per ADR-133 §Part 1 §6. LLM06 producer-boundary: `loop_id` charset `^[A-Za-z0-9_-]+$`, ≤64 chars, fail-open drop on invalid. |
| `swarm_paused_owner_absent` (v2.27) | `action`, `hmac`, `hmac_error`, `last_owner_read_iso`, `loop_duration_hours`, `project`, `session_id`, `swarm_pid`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-102 autonomous-loop weekend-burn (S142) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `swarm_runaway_suspected` (v2.27) | `action`, `hmac`, `hmac_error`, `iteration_count_24h`, `project`, `session_id`, `threshold`, `tokens_in`, `tokens_out`, `tokens_total`, `triggering_class`, `event_schema`, `ts`. PLAN-102 autonomous-loop opt-in (S142) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `task_route_ground_truth_label` (v2.27) | `action`, `contract_id`, `ground_truth_class`, `ground_truth_source`, `annotation_confidence_bps`, `session_id`, `project`, `event_schema`, `ts`. PLAN-101 Wave B / ADR-104-AMEND-1 §E (S141) — registered via PLAN-107 v1.38.0 SPEC v1 backfill (S145). |
| `federation_audit_event_pushed` (v2.29) | `action`, `peer_id`, `event_action`, `hmac_ok`, `origin_overwritten`, `hmac`, `hmac_error`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-099-FOLLOWUP Wave E.3 / ADR-135-AMEND-1 §6 — federation write-mode `/audit-event` ingest success path. ATT&CK T1565 (Data Manipulation). Registered via kernel-override sentinel `PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION` at v1.39.1. |
| `federation_audit_event_pushed_batch` (v2.29) | `action`, `peer_id`, `batch_size`, `accepted_count`, `rejected_count`, `hmac`, `hmac_error`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-099-FOLLOWUP Wave E.3 / ADR-135-AMEND-1 §6 — federation write-mode `/audit-event` batch-ingest aggregate counts (per-event details still emitted as `federation_audit_event_pushed` or `federation_event_action_blocked`). Registered via kernel-override sentinel `PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION` at v1.39.1. |
| `federation_audit_log_backpressure` (v2.29) | `action`, `p99_latency_ms`, `window_seconds`, `action_taken`, `hmac`, `hmac_error`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-099-FOLLOWUP Wave E.1 / ADR-135-AMEND-1 §6 — federation audit-log append-latency backpressure signal (server emits 503 + throttles writes when p99 > 100ms over 30s window). ATT&CK T1499 (Endpoint DoS). `action_taken` closed enum {`throttled_503`, `queue_paused`, `recovered`}. Registered via kernel-override sentinel `PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION` at v1.39.1. |
| `federation_cert_rotated` (v2.29) | `action`, `peer_id`, `old_der_sha256_prefix`, `new_der_sha256_prefix`, `spki_preserved`, `hmac`, `hmac_error`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-099-FOLLOWUP Wave F.2 / ADR-135-AMEND-1 §3 — supersedes the v2.27 MVP shape at line 293. Field renames: `old_fingerprint_prefix` -> `old_der_sha256_prefix`; `new_fingerprint_prefix` -> `new_der_sha256_prefix`. NEW caller field `spki_preserved` (bool) carries the rotation-integrity invariant (SPKI preserved across cert rotation per ADR-135-AMEND-1 §3; `spki_preserved=False` is a red flag — emit `federation_spki_fingerprint_mismatch` alongside). Registered via kernel-override sentinel `PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION` at v1.39.1. |
| `federation_cert_validity_window_too_large` (v2.29) | `action`, `peer_id`, `not_before_iso`, `not_after_iso`, `duration_days`, `hmac`, `hmac_error`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-099-FOLLOWUP Wave F.2 / ADR-135-AMEND-1 §3 — advisory emit when peer cert validity window exceeds the policy ceiling (default 90 days). Does NOT block cert pinning. Registered via kernel-override sentinel `PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION` at v1.39.1. |
| `federation_event_action_blocked` (v2.29) | `action`, `peer_id`, `event_action`, `reason_code`, `hmac`, `hmac_error`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-099-FOLLOWUP Wave E.3 / ADR-135-AMEND-1 §6 — peer-submitted event carries `action` not in `peers.yaml: audit_event_push_allowlist`. ATT&CK T1565 (Data Manipulation). `reason_code` closed enum {`action_not_allowed`, `action_unknown`, `action_kernel_only`}. Registered via kernel-override sentinel `PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION` at v1.39.1. |
| `federation_hmac_secret_rotated` (v2.29) | `action`, `peer_id`, `rotation_reason_code`, `hmac`, `hmac_error`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-099-FOLLOWUP Wave F.2 / ADR-135-AMEND-1 §6 — peer HMAC secret rotated via Owner-co-sign sentinel. `rotation_reason_code` closed enum {`scheduled`, `compromise_suspected`, `owner_initiated`, `key_floor_floor_raise`}. Registered via kernel-override sentinel `PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION` at v1.39.1. |
| `federation_key_floor_rejected` (v2.29) | `action`, `peer_id`, `key_type`, `key_bits`, `curve_name`, `reason_code`, `hmac`, `hmac_error`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-099-FOLLOWUP Wave F.2 / ADR-129-AMEND-1 §3 — peer cert or key fails key-floor policy (minimum RSA 2048 / ECDSA P-256 / Ed25519). ATT&CK T1573 (Encrypted Channel). `key_bits` populated for RSA/DSA; `curve_name` populated for ECDSA. `reason_code` closed enum {`key_too_small`, `curve_not_allowed`, `key_type_not_allowed`, `sig_alg_weak`}. Registered via kernel-override sentinel `PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION` at v1.39.1. |
| `federation_key_floor_stale` (v2.29) | `action`, `peer_id`, `key_floor_verified_at_iso`, `advisory_only`, `hmac`, `hmac_error`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-099-FOLLOWUP Wave F.2 / ADR-129-AMEND-1 §4 — peer's key-floor compliance last verified > 30 days ago. `advisory_only=True` during grace-period (per ADR-129-AMEND-1 §4 lift schedule); flips to `False` post-lift. Registered via kernel-override sentinel `PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION` at v1.39.1. |
| `federation_message_storm_detected` (v2.29) | `action`, `peer_id`, `route`, `ip_prefix`, `hits_in_window`, `window_seconds`, `hmac`, `hmac_error`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-099-FOLLOWUP Wave E.1 / ADR-135-AMEND-1 §2.4 — peer exceeded rate limit ≥3 times within 5 minutes; server auto-revokes `audit_event_push` scope for 15 minutes. ATT&CK T1499 (Endpoint DoS). `ip_prefix` is /24 prefix (NOT full IP — LLM06 + GDPR hold). Registered via kernel-override sentinel `PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION` at v1.39.1. |
| `federation_peer_invalid_no_fingerprint` (v2.29) | `action`, `peer_id`, `source_path`, `hmac`, `hmac_error`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-099-FOLLOWUP Wave E.4 / ADR-135-AMEND-1 §6 — `peers.yaml` loader rejects peer entry lacking required `spki_fingerprint` field (post-lift hard-fail; pre-lift was advisory). Registered via kernel-override sentinel `PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION` at v1.39.1. |
| `federation_peer_registered` (v2.29) | `action`, `peer_id`, `route`, `scopes_count`, `spki_fingerprint_prefix`, `hmac`, `hmac_error`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-099-FOLLOWUP Wave E.2 / ADR-135-AMEND-1 §2.5 — successful `/peer-register` (Owner co-sign sentinel verified at gate #10). `spki_fingerprint_prefix` is first 16 hex chars of new peer's SPKI (LLM06: full fingerprint NOT logged). Registered via kernel-override sentinel `PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION` at v1.39.1. |
| `federation_peer_registered_collision` (v2.29) | `action`, `peer_id`, `attempted_by_origin_peer_id`, `hmac`, `hmac_error`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-099-FOLLOWUP Wave E.2 / ADR-135-AMEND-1 §2.5 — `/peer-register` attempted with existing `peer_id`. ATT&CK T1485 (Data Destruction). Append-only registry per attack-rebinding §2.2 mitigation #3. Registered via kernel-override sentinel `PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION` at v1.39.1. |
| `federation_peer_revoked_remote` (v2.29) | `action`, `peer_id`, `revoked_by_origin_peer_id`, `reason_code`, `hmac`, `hmac_error`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-099-FOLLOWUP Wave E.2 / ADR-135-AMEND-1 §2.5 — successful `/peer-revoke` (Owner co-sign sentinel verified). ATT&CK T1485 (Data Destruction). `revoked_by_origin_peer_id` carries the AUTHENTICATED peer-id (server overwrites pre-emit; peer-side claim discarded). `reason_code` closed enum {`compromise_suspected`, `key_floor_violation`, `owner_directive`, `scheduled_decommission`}. Registered via kernel-override sentinel `PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION` at v1.39.1. |
| `federation_pin_legacy_used` (v2.29) | `action`, `peer_id`, `route`, `der_fingerprint_prefix`, `hmac`, `hmac_error`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-099-FOLLOWUP Wave F.2 / ADR-135-AMEND-1 §3 — peer connection succeeded via legacy DER-fingerprint pinning (`peers.yaml: pin: <der-sha256>`) rather than preferred SPKI path. ATT&CK T1071.001 (App Layer Protocol — Web Protocols). Advisory; pre-lift deprecation of legacy pin column. Registered via kernel-override sentinel `PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION` at v1.39.1. |
| `federation_scope_denied` (v2.29) | `action`, `peer_id`, `route`, `required_scope`, `peer_scopes_count`, `hmac`, `hmac_error`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-099-FOLLOWUP Wave E.3 / ADR-135-AMEND-1 §2.3 — authenticated peer attempted route requiring scope absent from `peers.yaml: scopes`. `peer_scopes_count` is count only (list itself NOT logged — LLM06 side-channel hold). Registered via kernel-override sentinel `PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION` at v1.39.1. |
| `federation_spki_fingerprint_mismatch` (v2.29) | `action`, `peer_id`, `expected_prefix`, `presented_prefix`, `route`, `hmac`, `hmac_error`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-099-FOLLOWUP Wave F.2 / ADR-135-AMEND-1 §3 — peer's presented SPKI fingerprint does NOT match expected pin in `peers.yaml`. ATT&CK T1556 (Modify Authentication Process). Both `*_prefix` fields are first-16-hex-char prefixes (LLM06: full SPKI not logged). Per attack-rebinding §2.3 mitigation #1. Registered via kernel-override sentinel `PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION` at v1.39.1. |
| `federation_tamper_detected` (v2.29) | `action`, `peer_id`, `route`, `tamper_type`, `prev_hash_prefix`, `hmac`, `hmac_error`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-099-FOLLOWUP Wave E.3 / ADR-135-AMEND-1 §6 — HMAC-mismatch / origin-tag-replay / audit-chain hash break. ATT&CK T1565 (Data Manipulation). `tamper_type` closed enum {`hmac_mismatch`, `origin_tag_replay`, `chain_hash_break`, `canonical_form_drift`}. `prev_hash_prefix` is SHA-256 prefix of previous audit-chain anchor that failed to match. Per attack-rebinding §2.3 mitigation #1 + #4. Registered via kernel-override sentinel `PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION` at v1.39.1. |
| `federation_write_disabled_sentinel_invalid` (v2.29) | `action`, `reason_code`, `sentinel_path`, `hmac`, `hmac_error`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-099-FOLLOWUP Wave F.2 / ADR-135-AMEND-1 §5 — server startup detects `write-enabled.md.asc` sentinel present but failing GPG verification or co-sign quorum. Server starts READ-ONLY regardless of `--write-mode` flag. `reason_code` closed enum {`gpg_verify_failed`, `signer_not_authorized`, `quorum_not_met`, `sentinel_corrupt`}. Registered via kernel-override sentinel `PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION` at v1.39.1. |
| `federation_write_endpoint_denied` (v2.29) | `action`, `peer_id`, `route`, `gate_failed`, `reason_code`, `hmac`, `hmac_error`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-099-FOLLOWUP Wave E.2 / ADR-135-AMEND-1 §2 — authenticated peer attempted write-mode endpoint (e.g. `/audit-event`, `/peer-register`, `/peer-revoke`, `/hmac-secret-rotate`) and failed ANY of gates #1-#11. ATT&CK T1485 (Data Destruction). `gate_failed` is integer 1..11 identifying the failing gate; `reason_code` is gate-specific failure code per ADR-135-AMEND-1 §2 table. Registered via kernel-override sentinel `PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION` at v1.39.1. |
| `protocol_edit_missing_amend_paired` (v2.30) | `action`, `protocol_path`, `amend_present`, `hook_origin`, `class_tier`, `reason_code`, `loop_id`, `hmac`, `hmac_error`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-110 v1.39.0 Wave D (S147) — advisory emit from `check_protocol_semver_cascade.py` PreToolUse hook when a PROTOCOL.md edit lands without a paired ADR-AMEND-N artifact. Fail-OPEN (never blocks the session). Registered via kernel-override sentinel `PLAN-110-WAVE-D-AUDIT-EMIT-EXTENSION` at v1.39.0. |
| `chain_reset_marker` (v2.31) | `action`, `previous_archive_path`, `previous_archive_last_hmac`, `rotation_ts`, `rotation_trigger`, `hmac`, `hmac_error`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-112-FOLLOWUP-hmac-tamper-fix v1.39.4 Wave B.3 (S152) — synthetic genesis entry written as line 1 of every rotation-created fresh audit-log.jsonl per ADR-055-AMEND-2. HMAC anchored at `GENESIS_PREV`. Producer emits atomically under canonical FileLock + writes `audit-log.rotation-manifest.json` sidecar in same lock window. Verifier reads sidecar from log's directory (NOT `_audit_dir_from_env`); sidecar present + line 1 not chain_reset_marker = STATUS_TAMPER `reason: "marker_required_but_absent: audit-log.rotation-manifest.json present but line 1 action is not chain_reset_marker per ADR-055-AMEND-2"`. `rotation_trigger` closed enum {`size_threshold`, `manual`, `owner_rotation`, `quarantine_pre_fix`}; defaults to `size_threshold`. `previous_archive_last_hmac` is forensic metadata (NOT chain link; verifier does NOT walk archives — preserves ADR-055 §Non-goals "log = source of truth"). `previous_archive_last_hmac=""` if recovery fails (best-effort). Registered via kernel-override sentinel `PLAN-112-FOLLOWUP-WAVE-B3-AUDIT-EMIT-EXTENSION` at v1.39.4. |
| `model_routing_enforced` (v2.32) | `action`, `archetype`, `mode`, `recommended_model`, `killswitch_armed`, `decision`, `hmac`, `hmac_error`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-112-FOLLOWUP-persona-routing-wire v1.42.0 W1+W2 (S158) — forensic telemetry of the god-mode (persona × primitive) routing-matrix consult in `check_agent_spawn._consult_model_routing_mode()`, emitted AFTER VETO-floor enforcement. CONSULT+AUDIT ONLY — the model-tier BLOCK is DEFERRED (the Agent hook payload exposes no requested-model signal; `metadata.get("model")` is the agent-frontmatter model, not a spawn input). `mode` closed enum {`enforcing`, `advisory`, `disabled`} read off the AUTHORITATIVE `subagent_type`-derived archetype only (NEVER the prompt-regex archetype). `decision` closed enum {`enforce_telemetry`, `advisory`, `eval_error`} — NO `block` value (block deferred per ADR-118; future enable governed by observed-violation volume + FPR, NOT calendar — ADR-095). `killswitch_armed` bool reflects `CEO_GODMODE_ENFORCING=0`; `get_mode()` demotes an enforcing cell to advisory under the kill-switch. `recommended_model` is the best-effort agent-frontmatter model (≤64). NO prompt/description/frontmatter-path content persisted. Sec MF-3 allowlist `_MODEL_ROUTING_ENFORCED_ALLOWLIST` + dispatch-gate scrub. Registered via kernel-override sentinel `PLAN-112-FOLLOWUP-S158-AUDIT-EMIT-EXTENSION`. |
| `model_routing_eval_error` (v2.32) | `action`, `archetype`, `reason_code`, `decision`, `hmac`, `hmac_error`, `project`, `session_id`, `tokens_in`, `tokens_out`, `tokens_total`, `event_schema`, `ts`. PLAN-112-FOLLOWUP-persona-routing-wire v1.42.0 W1+W2 (S158) — fail-OPEN infra branch of the matrix consult: emitted when `persona_routing` import is unavailable OR `get_mode()`/`is_enforcing()` raises. The spawn is ALLOWED regardless (fail-open per CLAUDE.md §5). `reason_code` carries a short failure tag (e.g. `persona_routing_eval_failed`). `decision` is the constant `eval_error` — the third value of the shared closed enum {`enforce_telemetry`, `advisory`, `eval_error`}, kept consistent with `model_routing_enforced` per AC5 (NO `block` value). NO prompt/description content. Sec MF-3 allowlist `_MODEL_ROUTING_EVAL_ERROR_ALLOWLIST` + dispatch-gate scrub. Registered via kernel-override sentinel `PLAN-112-FOLLOWUP-S158-AUDIT-EMIT-EXTENSION`. |
| `federation_peer_list_reloaded` (v2.33) | `action`, `peer_count`, `reload_reason`, `source_path`, `hmac`, `hmac_error`, `event_schema`, `ts`. PLAN-112-FOLLOWUP-federation-wire PHASE2 v1.43.0 (S159) — peer-list reload marker so the <60s revocation-propagation SLO (P0-1) is forensically observable (ADR-135-AMEND-2; write-mode ACTIVATION default-OFF). `reload_reason` closed enum {`content_changed`, `parse_error_kept_last_good`}. Registered via kernel-override sentinel `PLAN-112-FOLLOWUP-FEDERATION-WIRE-AUDIT-EMIT-EXTENSION`. NOTE: `emit_generic` does NOT auto-inject `session_id`/`project` (S153 R9 residual — audit-attribution wart, not chain-integrity). |
| `spec_context_sanitized` (v2.34; P2-fix S163) | `action`, `original_bytes`, `cleaned_bytes`, `truncated`, `sentinel_violations`, `control_chars_stripped`, `bidi_zw_chars_stripped`, `header_escape_count`, `hmac`, `hmac_error`, `event_schema`, `ts`. PLAN-113 Phase B WIRE-DEADMOD v1.45.x (S163) — advisory telemetry from `check_agent_spawn._maybe_sanitize_spec_context()` when a `## SPEC CONTEXT` block is present in the spawn prompt. Kill-switch `CEO_SPEC_CTX_SANITIZER_ENABLED=0`. ADVISORY ONLY — never blocks spawn. `truncated` is int (0 or 1). `sentinel_violations` is the count of sentinel-pattern hits in the block. No prompt content persisted. Sec MF-3 P2 fix (PLAN-113 Codex): removed from `_EMIT_GENERIC_PASSTHROUGH`; routed through explicit `_SPEC_CONTEXT_SANITIZED_ALLOWLIST` scrub branch in `emit_generic`. |
| `spawn_confidence_advisory` (v2.34; P2-fix S163) | `action`, `action_type`, `confidence_level`, `confidence_marker`, `reason_code`, `is_named_spawn`, `hmac`, `hmac_error`, `event_schema`, `ts`. PLAN-113 Phase B WIRE-DEADMOD v1.45.x (S163) — advisory telemetry from `check_agent_spawn._emit_spawn_confidence_advisory()` classifying the spawn action type via `confidence_labels.classify()`. Kill-switch `CEO_SPAWN_CONFIDENCE_ENABLED=0`. ADVISORY ONLY — never blocks spawn. `action_type` ≤32 chars, `confidence_level` ≤32, `confidence_marker` ≤32 (emoji-free), `reason_code` ≤64. `is_named_spawn` is int (0 or 1). No prompt/description content persisted. Sec MF-3 P2 fix (PLAN-113 Codex): removed from `_EMIT_GENERIC_PASSTHROUGH`; routed through explicit `_SPAWN_CONFIDENCE_ADVISORY_ALLOWLIST` scrub branch in `emit_generic`. |
| `env_var_hijack_blocked` (v2.41) | `action`, `session_id`, `project`, `hijack_class` (str — CLOSED enum: `linker_preload` / `linker_path` / `runtime_hook` / `linker_other` / `parse_failure`; unrecognized value COERCED to `parse_failure`, never echoed), `event_schema`, `ts`, plus baseline `tokens_in`/`tokens_out`/`tokens_total`/`hmac`/`hmac_error`. PLAN-133 A1 (Goose-harvest) — env-var hijack guard breadcrumb (`LD_PRELOAD`/`DYLD_*`/`LD_LIBRARY_PATH` and kin blocked on Bash). Routes through the dedicated `_scrub_*` branch + `_ENV_VAR_HIJACK_BLOCKED_ALLOWLIST`, NEVER `_EMIT_GENERIC_PASSTHROUGH`. DENIED on the wire: the var name, the value, the command bytes. NO ATLAS technique (governance breadcrumb, not a detection signal). |
| `invisible_unicode_blocked` (v2.41) | `action`, `session_id`, `project`, `surface` (str — CLOSED enum), `unicode_class` (str — CLOSED enum mirroring `spec_context_sanitizer.INVISIBLE_UNICODE_CLASSES`; coerced), `char_count` (int — bounded), `enforced` (bool), `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error`. PLAN-133 A2 (Goose-harvest) — invisible/bidi/zero-width Unicode guard breadcrumb on prompt/skill surfaces. Routes through the dedicated `_scrub_*` branch + `_INVISIBLE_UNICODE_BLOCKED_ALLOWLIST` (built on `_FEDERATION_ENVELOPE`). DENIED on the wire: prompt/skill text, the matched characters, any var/value. NO ATLAS technique (governance breadcrumb, not a detection signal). |
| `egress_destination_detected` (v2.41) | `action`, `session_id`, `project`, `egress_class` (str — CLOSED enum: `network_http` / `ssh_remote` / `cloud_store` / `container_push` / `package_publish` / `raw_socket` / `pair_rail` / `unknown`; coerced to `unknown`), `destination` (str — BARE HOST only; scheme/userinfo/port/path/query re-truncated off before write, ≤253 chars), `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error`. PLAN-133 A3 (Goose-harvest) — egress-destination taxonomy telemetry. Routes through the dedicated `_scrub_*` branch + `_EGRESS_DESTINATION_DETECTED_ALLOWLIST`. DENIED on the wire: full URL, path, query, inline credentials. NO ATLAS technique (observability telemetry, not a detection signal). |
| `quota_exhausted` (v2.41) | `action`, `session_id`, `error_class` (str — CLOSED enum; coerced to `unknown`), `source` (str — CLOSED enum: `subscription_main_loop` / `metered_api` / `subprocess` / `unknown`; coerced), `http_status` (int — bare status, no body), `retryable` (bool), `metered_api_only` (bool), `attempt` (int 0..99 — clamped), `project`, `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error`. PLAN-133 B1 (Goose-harvest) — provider quota/credits-exhaustion telemetry. Routes through the dedicated dispatch-gate branch + `_QUOTA_EXHAUSTED_ALLOWLIST` (built on `_OPTIMIZER_ENVELOPE`). DENIED on the wire: `retry_delay`/`Retry-After`/body/header values. NO ATLAS technique (developer-productivity telemetry, not a detection signal). |
| `eval_task_completed` (v2.41) | `action`, `task_id`, `reward_bps` (int 0..1000 — reward × 1000; canonical_json no-float), `status` (str), `attempts` (int), `flaky` (bool), `tokens` (int), `turns` (int), `event_schema`, `ts`. PLAN-133 C3 (Goose-harvest) — real-task reward-benchmark result for the eval harness (ADR-147). Routes through the dedicated dispatch-gate branch + `_EVAL_TASK_COMPLETED_ALLOWLIST`. NO ATLAS technique (eval telemetry, not a detection signal). |
| `context_auto_compacted` (v2.41) | `action`, `session_id`, `reason` (str — CLOSED enum mirroring `context-budget.py` REASON_*; coerced), `usage_pct` (int 0..100 — clamped), `reclaim_pct` (int 0..100 — clamped), `turns_since_last` (int), `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error`. PLAN-133 D1 (Goose-harvest) — a proactive auto-compaction WAS performed (high/low-water hysteresis). Routes through the dedicated dispatch-gate branch + `_CONTEXT_AUTO_COMPACTED_ALLOWLIST` (built on `_OPTIMIZER_ENVELOPE`). DENIED on the wire: raw bytes/tokens/transcript text (only bucketed percentages). NO ATLAS technique (developer-productivity telemetry, not a detection signal). |
| `context_auto_compact_suppressed` (v2.41) | `action`, `session_id`, `suppress_reason` (str — CLOSED enum: `cooldown` / `reclaim_floor` / `other`; coerced), `usage_pct` (int 0..100 — clamped), `reclaim_pct` (int 0..100 — clamped), `turns_since_last` (int), `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error`. PLAN-133 D1 (Goose-harvest) — a would-be auto-compaction was SKIPPED by a gate. Routes through the dedicated dispatch-gate branch + `_CONTEXT_AUTO_COMPACT_SUPPRESSED_ALLOWLIST` (built on `_OPTIMIZER_ENVELOPE`). DENIED on the wire: raw bytes/tokens/transcript text. NO ATLAS technique (developer-productivity telemetry, not a detection signal). |
| `context_middle_out_degraded` (v2.41) | `action`, `session_id`, `reason` (str — CLOSED enum mirroring `context-budget.py` MO_REASON_*; coerced), `rung` (int 0..99 — clamped), `degraded_count` (int), `total_count` (int), `protect_last` (int), `reclaim_bucket` (str — coarse reclaim-tokens bucket), `fits_after` (bool), `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error`. PLAN-133 D5 (Goose-harvest) — a middle-out degradation pass elided ≥1 message's middle to fit the context budget. Routes through the dedicated dispatch-gate branch + `_CONTEXT_MIDDLE_OUT_DEGRADED_ALLOWLIST` (built on `_OPTIMIZER_ENVELOPE`). DENIED on the wire: message text, tool/agent identity, file paths, raw token totals. NO ATLAS technique (developer-productivity telemetry, not a detection signal). |
| `context_middle_out_degrade_failed` (v2.41) | `action`, `session_id`, `reason` (str — CLOSED enum mirroring `context-budget.py` MO_REASON_*; coerced), `rung` (int 0..99 — clamped), `degraded_count` (int), `total_count` (int), `protect_last` (int), `reclaim_bucket` (str — coarse reclaim-tokens bucket), `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error`. PLAN-133 D5 (Goose-harvest) — the middle-out ladder was exhausted (or no eligible message) and the context STILL overflows; caller must summarize/compact/fail upstream. Routes through the dedicated dispatch-gate branch + `_CONTEXT_MIDDLE_OUT_DEGRADE_FAILED_ALLOWLIST` (built on `_OPTIMIZER_ENVELOPE`). DENIED on the wire: message text, tool/agent identity, file paths, raw token totals. NO ATLAS technique (developer-productivity telemetry, not a detection signal). |
| `adversary_review_flagged` (v2.41) | `action`, `session_id`, `project`, `decision` (str — CLOSED enum: `deny` / `ask` / `advisory` / `allow`; coerced to `advisory`), `rule_class` (str — CLOSED enum: `destructive` / `exfiltration` / `privilege` / `tampering` / `other`; coerced to `other`), `rule_id` (str — author-controlled config token; carries no command bytes), `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error`. PLAN-133 E1 (Goose-harvest) — adversary-review rule engine breadcrumb (ADR-146; local-rules-only, default-OFF). Routes through the dedicated `_scrub_*` branch + `_ADVERSARY_REVIEW_FLAGGED_ALLOWLIST`. DENIED on the wire: the matched command text, the matched substring, the rule `match`/`regex` source. NO ATLAS technique (governance breadcrumb, not a detection signal). |
| `supply_chain_advisory_emitted` (v2.41) | `action`, `session_id`, `verdict` (str — CLOSED enum: `BLOCK` / `ALLOW` / `SKIP`), `reason` (str — CLOSED enum: `mal_advisory_present` / `clean` / `unknown` / `malformed_response` / `network_timeout` / `network_error` / `offline` / `disabled` / `no_package`), `ecosystem` (str — CLOSED enum: `npm` / `PyPI` / `other`; coerced to `other`), `package` (str — PUBLIC package identifier), `advisory_count` (int 0..99 — clamped), `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error`. PLAN-133 E2 (Goose-harvest) — supply-chain (OSV/advisory) gate telemetry. Routes through the dedicated dispatch-gate branch + `_SUPPLY_CHAIN_ADVISORY_EMITTED_ALLOWLIST` (built on `_OPTIMIZER_ENVELOPE`). DENIED on the wire: paths, commands, env, error bodies (only public pkg name + published OSV id). NO ATLAS technique (governance telemetry, not a detection signal). |
| `spawn_tool_scope_violation` (v2.41) | `action`, `session_id`, `rail` (str — CLOSED enum: `tool_scope` / `depth` / `overlap` / `other`), `enforced` (int 0/1 — coerced), `detail` (str — tool-NAMES + counts only; paths are 12-hex sha256 prefixes), `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error`. PLAN-133 E3 (Goose-harvest) — spawn-rail tool-scope violation breadcrumb. Routes through the dedicated dispatch-gate branch + `_SPAWN_TOOL_SCOPE_VIOLATION_ALLOWLIST` (built on `_OPTIMIZER_ENVELOPE`). DENIED on the wire: raw path / prompt / tool-arg bodies. NO ATLAS technique (governance breadcrumb, not a detection signal). |
| `spawn_depth_or_overlap_blocked` (v2.41) | `action`, `session_id`, `rail` (str — CLOSED enum: `tool_scope` / `depth` / `overlap` / `other`), `enforced` (int 0/1 — coerced), `count` (int — depth/overlap count), `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error`. PLAN-133 E3 (Goose-harvest) — spawn-rail depth/overlap block breadcrumb. Routes through the dedicated dispatch-gate branch + `_SPAWN_DEPTH_OR_OVERLAP_ALLOWLIST` (built on `_OPTIMIZER_ENVELOPE`). DENIED on the wire: raw path / prompt / tool-arg bodies. NO ATLAS technique (governance breadcrumb, not a detection signal). |
| `spawn_file_assignment_recorded` (v2.41) | `action`, `session_id`, `path_hashes` (str — comma-joined 12-hex sha256 prefixes only; any non-hex token silently dropped, ≤512 chars), `path_count` (int), `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error`. PLAN-133 E3 (Goose-harvest) — spawn `## FILE ASSIGNMENT` provenance breadcrumb (hashed). Routes through the dedicated dispatch-gate branch + `_SPAWN_FILE_ASSIGNMENT_RECORDED_ALLOWLIST` (built on `_OPTIMIZER_ENVELOPE`). DENIED on the wire: raw file paths (only 12-hex prefixes). NO ATLAS technique (governance breadcrumb, not a detection signal). |
| `action_required_held` (v2.41) | `action`, `session_id`, `action_id` (str), `kind` (str — CLOSED enum: `bash_command` / `file_write` / `file_delete` / `spend_over_cap` / `spawn` / `network_egress` / `other`; coerced), `token_sha256` (str — 64-hex confirmation-token hash, else `''` fail-closed), `expires_at` (int/str — expiry), `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error`. PLAN-133 E6 (Goose-harvest) — HITL confirmation-rail: an action was HELD pending Owner confirmation. Routes through the dedicated dispatch-gate branch + `_ACTION_REQUIRED_HELD_ALLOWLIST` (built on `_OPTIMIZER_ENVELOPE`). DENIED on the wire: the raw command/path/token (only its 64-hex hash). NO ATLAS technique (governance breadcrumb, not a detection signal). |
| `action_required_resumed` (v2.41) | `action`, `session_id`, `action_id` (str), `token_sha256` (str — 64-hex confirmation-token hash, else `''` fail-closed), `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error`. PLAN-133 E6 (Goose-harvest) — HITL confirmation-rail: a held action was RESUMED after a valid confirmation. Routes through the dedicated dispatch-gate branch + `_ACTION_REQUIRED_RESUMED_ALLOWLIST` (built on `_OPTIMIZER_ENVELOPE`). DENIED on the wire: the raw command/path/token. NO ATLAS technique (governance breadcrumb, not a detection signal). |
| `action_required_rejected` (v2.41) | `action`, `session_id`, `action_id` (str), `token_sha256` (str — 64-hex confirmation-token hash, else `''` fail-closed), `reject_reason` (str — CLOSED enum: `unknown_token` / `replayed` / `expired` / `session_mismatch` / `action_id_mismatch` / `malformed_request` / `infra_error` / `other`; coerced), `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error`. PLAN-133 E6 (Goose-harvest) — HITL confirmation-rail: a resume attempt was REJECTED (bad/replayed/expired token). Routes through the dedicated dispatch-gate branch + `_ACTION_REQUIRED_REJECTED_ALLOWLIST` (built on `_OPTIMIZER_ENVELOPE`). DENIED on the wire: the raw command/path/token. NO ATLAS technique (governance breadcrumb, not a detection signal). |
| `persistent_instructions_blocked` (v2.41) | `action`, `session_id`, `project`, `reason` (str — CLOSED enum: `ok` / `injection_pattern` / `oversize` / `outside_project_dir` / `other`; coerced to `other`), `family_hits` (int), `bytes_scanned` (int), `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error`. PLAN-133 G1 (Goose-harvest) — persistent-instructions guardrail breadcrumb (a `.goosehints`/persistent-instruction file was blocked). Routes through the dedicated `_scrub_*` branch + `_PERSISTENT_INSTRUCTIONS_BLOCKED_ALLOWLIST`. DENIED on the wire: the instruction-file body, the matched line, the resolved path, any env value (no-value-echo). NO ATLAS technique (governance breadcrumb, not a detection signal). |
| `hint_provenance_recorded` (v2.41) | `action`, `session_id`, `project`, `reason` (str — CLOSED enum: `loaded` / `blocked_injection` / `blocked_oversize` / `read_error` / `other`; coerced to `other`), `rel_dir_depth` (int — directory depth below the repo root ONLY), `family_hits` (int), `bytes_scanned` (int), `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error`. PLAN-133 G3 (Goose-harvest) — hint-file provenance breadcrumb. Routes through the dedicated `_scrub_*` branch + `_HINT_PROVENANCE_RECORDED_ALLOWLIST`. DENIED on the wire: the hint-file body, the matched line, the path text (absolute OR relative; only the integer depth is persisted). NO ATLAS technique (governance breadcrumb, not a detection signal). |
| `settings_tamper_detected` (v2.42) | `action`, `session_id`, `project`, `tamper_class` (str — CLOSED enum mirroring `_lib/effective_config.TAMPER_CLASSES`: `settings_tamper_disable_all_hooks` / `settings_tamper_model_remap` / `settings_tamper_endpoint_remap` / `settings_tamper_permission_bypass` / `settings_tamper_hook_count_mismatch` / `settings_tamper_sidecar_redirect` / `other`; coerced to `other`), `layer` (str — CLOSED enum: `user` / `project` / `local` / `managed` / `env` / `disk` / `other`; coerced to `other`), `finding_count` (int — clamped 0..99), `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error`. PLAN-135 W1 S3 (anthropic-surface-harvest) — `/ceo-boot` Tier-S tamper-tripwire breadcrumb: ONE emit per tamper class detected on the RESOLVED multi-layer settings (incl. the gitignored, sentinel-blind `settings.local.json`) + the import-time env snapshot (trusted_env pattern). Producer: `.claude/scripts/ceo-boot.py` `check_settings_tamper_tripwires` via `emit_generic` (no public typed wrapper — `persona_coverage_synthesized` precedent, S142 R2 iter-1 P1 #3). Routes through the dedicated `_scrub_*` branch + `_SETTINGS_TAMPER_DETECTED_ALLOWLIST`, NEVER `_EMIT_GENERIC_PASSTHROUGH`. DENIED on the wire: the finding DETAIL string (endpoint URL / model id / apiKeyHelper path / flag value), any env VALUE (`ANTHROPIC_AUTH_TOKEN` is additionally redacted producer-side). Threat model: PLAN-135/research/THREAT-MODEL-WORKSHEET.md §2 (ADR-003 Path C compensating control). NO ATLAS technique (governance breadcrumb, not a detection signal). |
| `config_change_observed` (v2.43) | `action`, `session_id`, `project`, `layer` (str — CLOSED enum, settings file surfaces only: `user` / `project` / `local` / `managed` / `other`; coerced to `other`), `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error`. PLAN-135 W2 H2 (anthropic-surface-harvest) — ConfigChange-guard ALLOW path: a settings-surface config change fired the harness `ConfigChange` event and NO `_lib/effective_config.FORBIDDEN_KEYS` finding was scoped to it (closes the S197 out-of-band-settings-edit observability gap). Producer: `.claude/hooks/check_config_change.py` via `emit_generic` (no public typed wrapper — `settings_tamper_detected` precedent). Routes through the dedicated `_scrub_*` branch + `_CONFIG_CHANGE_OBSERVED_ALLOWLIST`, NEVER `_EMIT_GENERIC_PASSTHROUGH`. DENIED on the wire: the changed file's PATH text and BODY, any settings key or value. Honest coverage boundary: H2 is itself a hook — disarmed by the very `disableAllHooks` it polices and blind to edits made outside the harness; compensators = S3 boot tripwires + W5 O10 OTEL hook-execution witness (ADR-153 §H2 coverage boundary). NO ATLAS technique (governance breadcrumb, not a detection signal). |
| `config_change_forbidden_key` (v2.43) | `action`, `session_id`, `project`, `tamper_class` (str — CLOSED enum mirroring `_lib/effective_config.TAMPER_CLASSES`: `settings_tamper_disable_all_hooks` / `settings_tamper_model_remap` / `settings_tamper_endpoint_remap` / `settings_tamper_permission_bypass` / `settings_tamper_hook_count_mismatch` / `settings_tamper_sidecar_redirect` / `other`; coerced to `other`; the census class never reaches this event in practice — census findings are observe-only by producer design), `layer` (str — CLOSED enum: `user` / `project` / `local` / `managed` / `other`; coerced to `other`), `finding_count` (int — clamped 0..99), `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error`. PLAN-135 W2 H2 (anthropic-surface-harvest) — ConfigChange-guard ADVISORY-BLOCK path: ONE emit per forbidden-key tamper class scoped to the changed settings layer (`_emit_settings_tamper_detected_safe` shape precedent). Producer: `.claude/hooks/check_config_change.py` via `emit_generic` (no public typed wrapper). Routes through the dedicated `_scrub_*` branch + `_CONFIG_CHANGE_FORBIDDEN_KEY_ALLOWLIST`, NEVER `_EMIT_GENERIC_PASSTHROUGH`. DENIED on the wire: the forbidden key's VALUE (endpoint URL / model id / apiKeyHelper path / dangerously-flag value), the effective_config finding DETAIL string, the changed file's path/body. Forbidden-keys single source: `_lib/effective_config.FORBIDDEN_KEYS` (THREAT-MODEL-WORKSHEET §2). NO ATLAS technique (governance breadcrumb, not a detection signal). |
| `bash_input_rewritten` (v2.43) | `action`, `session_id`, `project`, `rewrite_class` (str — CLOSED enum: `git_push_force_to_lease` / `other`; coerced to `other`), `before_sha256` (str — 64-hex lowercase sha256 of the ORIGINAL command, else `''` fail-closed), `after_sha256` (str — 64-hex lowercase sha256 of the REWRITTEN command, else `''` fail-closed), `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error`. PLAN-135 W2 H5 (anthropic-surface-harvest; ADR-154 single-rewriter) — corrective `updatedInput` rewrite breadcrumb: `check_bash_safety.py` rewrote a single-subcommand `git push --force`/`-f` command to `git push --force-with-lease` via the PreToolUse `updatedInput` channel and surfaced it as a permission prompt (`permissionDecision: "ask"`, NEVER a silent allow — the corrective rewrite may never degrade an existing BLOCK into an allow, Doctrine 1 corollary). Producer: `.claude/hooks/check_bash_safety.py` via the TYPED wrapper `emit_bash_input_rewritten`. Routes through the dedicated `_scrub_*` branch + `_BASH_INPUT_REWRITTEN_ALLOWLIST`, NEVER `_EMIT_GENERIC_PASSTHROUGH`. DENIED on the wire: the command STRING (before OR after the rewrite), the remote URL / refspec, any inline credential — only the closed-enum `rewrite_class` + the before/after sha256 hash PAIR travel (the pair proves audited-cmd == executed-cmd without exposing either; ADR-154 §2). Kill-switch: `CEO_BASH_FORCE_PUSH_REWRITE=0` restores the legacy BLOCK. Single-rewriter invariant (ADR-154 §1): at most ONE rewriting hook per tool-call; downstream hooks see the post-rewrite input. Threat model: PLAN-135/research/THREAT-MODEL-WORKSHEET.md §1. NO ATLAS technique (governance breadcrumb, not a detection signal). |
| `subagent_lifecycle_observed` (v2.43) | `action`, `session_id`, `project`, `agent_archetype` (str — CLOSED enum, persona-ledger archetype: `code-reviewer` / `security-engineer` / `qa-architect` / `threat-detection-engineer` / `other` / `unknown`; coerced to `other`), `wall_bucket` (str — CLOSED bucket enum: `none` / `low` / `medium` / `high` / `very_high` / `unknown`; coerced to `unknown`), `wall_source` (str — CLOSED enum: `bracketed` / `unknown`; coerced to `unknown`), `token_bucket` (str — same CLOSED bucket enum; coerced to `unknown`), `claim_bucket` (str — same CLOSED bucket enum; coerced to `unknown`), `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error`. PLAN-135 W2 H3 (anthropic-surface-harvest) — per-agent SubagentStop lifecycle bracket: emitted ONCE per returning sub-agent by `check_fluency_nudge.py` (the SubagentStop H3 extension) after consuming the SubagentStart sidecar written by `check_subagent_start.py` (keyed `sha256(agent_id)[:16]`, popped on read) + the harness-supplied `agent_transcript_path` (line/byte/wall-bounded; only integer usage fields read; realpath-under-`$HOME/.claude` containment). The S227 `modelUsage` forensic reconstruction becomes a live hook emit; feeds the persona-ledger (PLAN-104) via `agent_archetype`. `wall_bucket` is the stop-instant minus the recorded `start_ts` (bracketed; `wall_source=unknown` when the start was never recorded). `token_bucket` brackets the SUM of `input_tokens + output_tokens + cache_creation_input_tokens + cache_read_input_tokens` across the transcript. `claim_bucket` brackets the confidence-marker count the hook already computes. Producer: `.claude/hooks/check_fluency_nudge.py` via the TYPED wrapper `emit_subagent_lifecycle_observed`. Routes through the dedicated `_scrub_*` branch + `_SUBAGENT_LIFECYCLE_OBSERVED_ALLOWLIST`, NEVER `_EMIT_GENERIC_PASSTHROUGH`. DENIED on the wire: the RAW token counts, the RAW wall-time seconds, the transcript path/body, the confidence-marker snippets and the raw agent_id — only the closed-enum archetype + the four coarse brackets travel (the bracket is the audit signal; the raw counts stay forensic-private). Kill-switch: `CEO_SUBAGENT_LIFECYCLE=0` (shared by the SubagentStart recorder + this SubagentStop consumer). NO ATLAS technique (governance/accounting breadcrumb, not a detection signal). |
| `compaction_continuity_snapshot` (v2.43) | `action`, `session_id`, `project`, `trigger` (str — CLOSED enum: `manual` / `auto` / `other`; coerced to `other`), `plan_id` (str — strict `PLAN-NNN` shape, else `unknown`), `chain_length` (int — clamped 0..99999999), `snapshot_outcome` (str — CLOSED enum: `written` / `scratchpad_unavailable` / `error` / `other`; coerced to `other`), `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error`. PLAN-135 W2 H1 (anthropic-surface-harvest; ADR-153 compaction-continuity) — PreCompact governance snapshot: before the harness compacts a long session (manual `/compact` or auto context-window threshold), `check_precompact_continuity.py` snapshotted plan-id + execution-unit position + pending-ceremony flags to the plan-scoped scratchpad + read the audit HMAC-chain anchor (last-hmac prefix + chain-length). ONE emit per compaction event. Producer: `.claude/hooks/check_precompact_continuity.py` via `emit_generic` (no public typed wrapper — `settings_tamper_detected` precedent). Routes through the dedicated `_scrub_*` branch + `_COMPACTION_CONTINUITY_SNAPSHOT_ALLOWLIST`, NEVER `_EMIT_GENERIC_PASSTHROUGH`. DENIED on the wire: the snapshot BODY — the plan path text, the execution-unit checkbox label, the ceremony script paths, the full last-hmac hex (the snapshot lives in the plan-scoped, secrets-redacted scratchpad; the wire carries closed enums + the chain_length counter only). Honest coverage boundary: ADR-153 §H2 (a hook is disarmed by `disableAllHooks`; S3 boot tripwires + W5 O10 OTEL witness are the named compensators). NO ATLAS technique (governance breadcrumb, not a detection signal). |
| `compaction_context_reinjected` (v2.43) | `action`, `session_id`, `project`, `plan_id` (str — strict `PLAN-NNN` shape, else `unknown`), `snapshot_found` (bool — coerced to `false`), `snapshot_age_s` (int — clamped 0..9999999), `pointer_count` (int — clamped 0..9), `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error`. PLAN-135 W2 H1 (anthropic-surface-harvest; ADR-153 compaction-continuity) — PostCompact governance reinjection: after compaction, `check_postcompact_reinject.py` read the PreCompact snapshot from the plan scratchpad and reinjected governance POINTERS (active PLAN, execution-unit position, Gate-1 re-read reminder, pending ceremonies, HMAC anchor) via `hookSpecificOutput.additionalContext`. POINTERS ONLY — never file CONTENTS (the Option-A prompt-injection surface, ADR-153 §Decision). ONE emit per PostCompact event. Producer: `.claude/hooks/check_postcompact_reinject.py` via `emit_generic` (no public typed wrapper). Routes through the dedicated `_scrub_*` branch + `_COMPACTION_CONTEXT_REINJECTED_ALLOWLIST`, NEVER `_EMIT_GENERIC_PASSTHROUGH`. DENIED on the wire: the reinjected pointer TEXT, the plan path/label, the ceremony paths, the scratchpad body (only the closed enums + counters persist). NO ATLAS technique (governance breadcrumb, not a detection signal). |
| `admin_key_lifecycle_event` (v2.44) | `action`, `operation` (str — CLOSED enum: `list` / `deactivate` / `incident` / `other` — out-of-enum direct-caller value coerced to `other`, S172), `key_count` (int — optional; on `list` = inventory size, on `incident` = # deactivated), `key_id` (str — optional, `deactivate` only; the `apikey_…` id, NEVER key material), `reason` (str — optional, mutations only; CLOSED enum: `compromise` / `suspicion` / `scheduled` / `other` — out-of-enum coerced to `other`, S172), `rotation_log_appended` (bool — optional, mutations only; true iff the audit-pair `docs/rotation-log.md` row was written), `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error`. All fields OPTIONAL except `action` + `operation`. PLAN-135 W5 o9 (anthropic-surface-harvest; ADR-054-AMEND-1 Anthropic Admin-key tier) — Anthropic Admin API key-lifecycle breadcrumb. Producer: `.claude/scripts/key-hygiene.py` (`_audit_emit` → `emit_generic`); a TRUSTED first-party Owner-run script that pre-redacts every field via `_redact()` before emit. Routed through the dedicated `_ADMIN_KEY_LIFECYCLE_EVENT_ALLOWLIST` scrub branch (Codex R5 P1-2 / PLAN-135-FOLLOWUP; NEVER `_EMIT_GENERIC_PASSTHROUGH`) — `operation`/`reason` enum-coerced (else `other`), `key_id` str-bounded, `key_count` int-clamped. DENIED on the wire: any key MATERIAL (only `apikey_…` ids + counts + closed enums travel). Secondary tamper-evident breadcrumb; the load-bearing audit-pair is the append-only `docs/rotation-log.md` row (written regardless). NO ATLAS technique (governance breadcrumb, not a detection signal). |
| `statusline_sidecar_write` (v2.44) | `action`, `sidecar_path` (str — abs path of the snapshot just written, never key material), `plan_id` (str\|null — active `PLAN-NNN` derived from `.claude/plans/`, or `+N` multi-marker), `context_pct_bps` (int\|null — context-window used %, integer basis-points 0..10000; HMAC-covered so NEVER float, S181/ADR-055-AMEND-2), `bucket_count` (int — number of `rate_limits` buckets present), `buckets_used_pct_max_bps` (int\|null — highest bucket used %, integer basis-points 0..99900; rate-limit used_pct is capped at 999% upstream so an over-quota burst is preserved, not floored at 100%), `session_id` (str — the statusLine `session_id`), `digest` (str — 12-char material-digest prefix; the debounce key), `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error`. All fields OPTIONAL except `action` (the renderer fires best-effort; any field may be absent when stdin lacked it — e.g. `context_pct_bps`/`rate_limits` null early in a session or on free-tier where `rate_limits` is absent). PLAN-135 W5 o4 (anthropic-surface-harvest) — statusLine sidecar-write breadcrumb. Producer: `.claude/scripts/statusline-ceo.py` (`maybe_emit` → `emit_generic`); a TRUSTED first-party Owner-configured renderer that passes only numbers + enum-ish ids + a digest prefix (the raw statusLine stdin free text is never echoed; the sidecar build drops `transcript_path` and unknown string fields). Routed through the dedicated `_STATUSLINE_SIDECAR_WRITE_ALLOWLIST` scrub branch (Codex R5 P1-2 / PLAN-135-FOLLOWUP; NEVER `_EMIT_GENERIC_PASSTHROUGH`) — `sidecar_path` length-capped (512), numeric/id fields type-bounded. DEBOUNCED: `maybe_emit` fires only when the MATERIAL digest changes AND ≥ `CEO_STATUSLINE_EMIT_INTERVAL_S` (default 300s) elapsed. The load-bearing artifact is the atomic sidecar JSON (always written); this event is a secondary tamper-evident breadcrumb. NO ATLAS technique (observability breadcrumb, not a detection signal). |
| `model_refusal_observed` (v2.44) | `action`, `provider` (str — e.g. `anthropic`), `model` (str — the request model slug, ≤128 chars), `stop_reason` (const `refusal`), `stop_category` (str — ONLY the closed provider `stop_details.category` vocabulary — e.g. `cyber` / `bio` / `reasoning_extraction` / `frontier_llm` / `""` when absent; ≤64 chars), `http_status` (int — the 2xx the refusal arrived on), `duration_ms` (int), `event_schema`, `ts`, plus baseline `tokens_*`/`hmac`/`hmac_error`. All fields OPTIONAL except `action` + `stop_reason` (the adapter populates `stop_category` only when `stop_details.category` is a string, else `""`). PLAN-135 W5 o7 (anthropic-surface-harvest) — model-refusal observability breadcrumb. Producer: `.claude/hooks/_lib/adapters/live/claude.py` (`_on_response` → `emit_generic` on `stop_reason == "refusal"`); the adapter library itself, routed through the dedicated `_MODEL_REFUSAL_OBSERVED_ALLOWLIST` scrub branch (Codex R5 P1-2 / PLAN-135-FOLLOWUP; NEVER `_EMIT_GENERIC_PASSTHROUGH`) — `stop_reason` const-coerced, `stop_category` ≤64, `http_status`/`duration_ms` int-bounded. DENIED on the wire: `stop_details.explanation` (model free text) is dropped AT THE EMIT SITE and can NEVER reach the audit log — only the closed `stop_details.category` provider vocabulary (truncated ≤64) + provider/model slugs + status/duration ints travel. NO ATLAS technique (observability breadcrumb, not a detection signal). |
<!-- PLAN-135 W2 H1 — 2 NEW v2.43 actions (compaction_continuity_snapshot + compaction_context_reinjected) registered via the staged PLAN-135 W2 bundle (Owner ceremony); ADR-153 compaction-continuity. Per-action SAFE allowlists _COMPACTION_CONTINUITY_SNAPSHOT_ALLOWLIST / _COMPACTION_CONTEXT_REINJECTED_ALLOWLIST in audit_emit.py; closed-enum trigger/snapshot_outcome + strict PLAN-NNN plan_id + clamped ints + bool only (snapshot body + reinjected pointer text NEVER persisted); deny-by-default scrub; S172 coerce-invalid-to-safe-sentinel. Both via emit_generic (no typed wrapper). Additive per SPEC/v1 rules. -->
<!-- PLAN-135 W2 H5 — 1 NEW v2.43 action (bash_input_rewritten) registered via the staged PLAN-135 W2 bundle (Owner ceremony); ADR-154 single-rewriter. Per-action SAFE allowlist _BASH_INPUT_REWRITTEN_ALLOWLIST in audit_emit.py; closed-enum rewrite_class + 64-hex hash pair only (command bytes NEVER persisted); deny-by-default scrub; S172 coerce-invalid-to-safe-sentinel. TYPED wrapper emit_bash_input_rewritten. Additive per SPEC/v1 rules. -->
<!-- PLAN-135 W2 H3 — 1 NEW v2.43 action (subagent_lifecycle_observed) registered via the staged PLAN-135 W2 bundle (Owner ceremony). Per-agent SubagentStop lifecycle bracket; per-action SAFE allowlist _SUBAGENT_LIFECYCLE_OBSERVED_ALLOWLIST in audit_emit.py; closed-enum archetype + 4 coarse buckets only (raw token/wall counts + transcript path/body + agent_id NEVER persisted); deny-by-default scrub; S172 coerce-invalid-to-safe-sentinel. TYPED wrapper emit_subagent_lifecycle_observed. SubagentStart half = check_subagent_start.py (sidecar recorder, NO audit action). Additive per SPEC/v1 rules. -->
<!-- PLAN-135 W1 S3 — 1 NEW v2.42 action (settings_tamper_detected) registered via the staged PLAN-135 W1 bundle (Owner kernel ceremony). Per-action SAFE allowlist in audit_emit.py; closed-enum + clamped-int only; deny-by-default scrub; S172 coerce-invalid-to-safe-sentinel. Additive per SPEC/v1 rules. -->
<!-- PLAN-133 (Goose-harvest) — 19 NEW v2.41 actions (env_var_hijack_blocked + invisible_unicode_blocked + egress_destination_detected + quota_exhausted + eval_task_completed + context_auto_compacted + context_auto_compact_suppressed + context_middle_out_degraded + context_middle_out_degrade_failed + adversary_review_flagged + supply_chain_advisory_emitted + spawn_tool_scope_violation + spawn_depth_or_overlap_blocked + spawn_file_assignment_recorded + action_required_held + action_required_resumed + action_required_rejected + persistent_instructions_blocked + hint_provenance_recorded) registered via the staged PLAN-133 bundle. Per-action SAFE allowlists in audit_emit.py; closed-enum / hash / bucketed-int only; deny-by-default scrub; S172 coerce-invalid-to-safe-sentinel. Additive per SPEC/v1 rules. -->
<!-- PLAN-113 Phase B WIRE-DEADMOD — 2 NEW v2.34 actions (spec_context_sanitized + spawn_confidence_advisory) registered S163 v1.45.x (ADVISORY-ONLY; spawn-prompt telemetry; emitted via emit_generic; kill-switch per action). -->
<!-- PLAN-112-FOLLOWUP-persona-routing-wire W2 — 2 NEW v2.32 actions (model_routing_enforced + model_routing_eval_error) registered S158 (Tier-2; god-mode matrix consult CONSULT+AUDIT, block deferred). Kernel-override sentinel PLAN-112-FOLLOWUP-S158-AUDIT-EMIT-EXTENSION. -->
<!-- PLAN-112-FOLLOWUP-hmac-tamper-fix Wave B.3 — 1 NEW v2.31 action (chain_reset_marker) registered S152 (Tier-A; HMAC chain rotation defense-in-depth per ADR-055-AMEND-2). -->
<!-- PLAN-110 Wave D — 1 NEW v2.30 action (protocol_edit_missing_amend_paired) registered S147 (Tier-A advisory; PROTOCOL.md semver-cascade). -->
<!-- PLAN-099-FOLLOWUP Wave F.2 — 19 NEW v2.29 actions + 1 in-place field-shape supersede (federation_cert_rotated) registered S148 (Tier-C; first federation write-mode plan). ADR-135-AMEND-1 + ADR-129-AMEND-1. -->
<!-- PLAN-107 SPEC v1 backfill — 63 NEW v2.27 actions registered S145 (Tier-A); closes residual gaps S107-S128 + S134-S143. -->
<!-- PLAN-086 v1.20.0 + PLAN-088 v1.22.0 canonical-13 — 16 NEW v2.26 actions backfilled in PLAN-091 v1.22.1 (S115 2026-05-13). -->
<!-- PLAN-085 Wave C credential lifecycle + Wave G.1b ATLAS + Wave E.4 forensic — 10 NEW v2.25 actions. -->

### Version-label disambiguation (P0-06 fix)

The SPEC file tracks **action** additions; `.claude/plans/AUDIT-LOG-SCHEMA.md` §13/14/15 track **field** additions on the existing `agent_spawn` action. Both dimensions evolve independently and can share the same "v2.N" label on different changes. Cross-reference:

| Version bump | SPEC (this file — actions) | Internal (AUDIT-LOG-SCHEMA — fields) |
|---|---|---|
| v2.7 | session_start / session_end / prompt_submitted / session_stop / output_scan_finding | cache-header + rail (§13) |
| v2.8 | rag_query_* + rag_index_redacted | model discriminator (§14) |
| v2.9 | tier_policy_* (9 actions) + tournament_* (8 actions) | hmac chain (§15) |
| v2.10 | fluency_nudge + skill_reference_read_{mismatch,stale,never_read} | *(no new fields)* |
| v2.11 | swarm_* (10 actions) + escalation_* (4 actions) | *(no new fields)* |
| v2.12 | audit_tokens_emitted + audit_tokens_timeout + audit_tokens_key_dropped (PLAN-060 Phase B / SEC-P0-04) | *(no new fields)* |
| v2.13 | mcp_injection_finding (PLAN-052 / ADR-083) | *(no new fields)* |
| v2.14 | *(no new actions)* | veto_triggered: `caller` + `session_id` (PLAN-044 audit-v2 P1 #6 — kernel override forensic traceability) |
| v2.15 | skill_bootstrap_used + skill_bootstrap_post_hash (Session 76 audit-v3 / Codex DIM-04 #1) | *(no new fields)* |
| v2.16 | replay_capture_started + replay_capture_completed (PLAN-069 Phase 1 / ADR-101) | *(no new fields)* |
| v2.17 | ceo_boot_emitted + ceo_boot_check_skipped (PLAN-065 Phase 2 / ADR-098 — S82 ceremony lote 2026-05-04) | *(no new fields)* |
| v2.18 | mcp_canonical_guard_allowed + mcp_canonical_guard_blocked (PLAN-070 / ADR-102 — S85 Layer B ceremony 2026-05-05) | *(no new fields)* |
| v2.19 | task_route_advised + task_route_key_dropped + reality_ledger_finding + reality_ledger_key_dropped (PLAN-071 / ADR-104 — S87 v1.14.0 ceremony 2026-05-05) | *(no new fields; field allowlists in audit_emit.py)* |
| v2.20 | model_routing_advised + estimate_drift_detected + estimate_drift_systematic_bias (PLAN-078 Wave 1+W2 / S89 Fase 1 commit 2cb1472, registered S92 Wave 1b ceremony 2026-05-07) | *(no new fields; field allowlists in audit_emit.py)* |
| v2.21 | ceo_boot_task_candidate_emitted (PLAN-078 Wave 5 / S95 ceremony 2026-05-08 — TaskCreate-candidate orchestration) | *(no new fields; field allowlist `_CEO_BOOT_TASK_CANDIDATE_EMITTED_ALLOWLIST` in audit_emit.py)* |
| v2.40 | PLAN-132 / ADR-145 (S221) — cross-model Codex review as a recognized `code-reviewer` persona-demand satisfaction modality. NO new actions; adds fields `review_source` (enum `{phase_gate, user_code_auto, adhoc_mcp}`) + `target_ref_hash` (12-hex branch binding) to `codex_review_invoked`, and `match_modality` (enum `{native_spawn, codex_review}`, default `native_spawn`) to `persona_demand_matched`. code-reviewer ONLY; branch-bound (R1) + tight review-intent gate (R2); fail-closed on missing binding. Registered via canonical sentinel + Owner GPG. | `review_source`, `target_ref_hash` (codex_review_invoked); `match_modality` (persona_demand_matched). All closed-enum / hash, S172 coerce-invalid-to-safe-sentinel. |
| v2.41 | PLAN-133 (Goose-harvest) — 19 NEW actions across the harvested security/finops/eval/context/guardrail waves: A1 `env_var_hijack_blocked`, A2 `invisible_unicode_blocked`, A3 `egress_destination_detected`, B1 `quota_exhausted`, C3 `eval_task_completed`, D1 `context_auto_compacted` + `context_auto_compact_suppressed`, D5 `context_middle_out_degraded` + `context_middle_out_degrade_failed`, E1 `adversary_review_flagged` (ADR-146; local-rules-only default-OFF), E2 `supply_chain_advisory_emitted`, E3 `spawn_tool_scope_violation` + `spawn_depth_or_overlap_blocked` + `spawn_file_assignment_recorded`, E6 `action_required_held` + `action_required_resumed` + `action_required_rejected` (HITL confirmation-rail), G1 `persistent_instructions_blocked`, G3 `hint_provenance_recorded`. Each routes through a dedicated deny-by-default per-action allowlist in `audit_emit.py` (NEVER `_EMIT_GENERIC_PASSTHROUGH`); closed-enum / 64-hex-token-hash / 12-hex-path-prefix / bucketed-int payloads only; out-of-enum values COERCED to a safe sentinel before emit (S172 doctrine, never echoed). ADRs 146/147/148 (PROPOSED). | *(no new fields on existing actions; per-action allowlists `_ENV_VAR_HIJACK_BLOCKED_ALLOWLIST`, `_INVISIBLE_UNICODE_BLOCKED_ALLOWLIST`, `_EGRESS_DESTINATION_DETECTED_ALLOWLIST`, `_QUOTA_EXHAUSTED_ALLOWLIST`, `_EVAL_TASK_COMPLETED_ALLOWLIST`, `_CONTEXT_AUTO_COMPACTED_ALLOWLIST`, `_CONTEXT_AUTO_COMPACT_SUPPRESSED_ALLOWLIST`, `_CONTEXT_MIDDLE_OUT_DEGRADED_ALLOWLIST`, `_CONTEXT_MIDDLE_OUT_DEGRADE_FAILED_ALLOWLIST`, `_ADVERSARY_REVIEW_FLAGGED_ALLOWLIST`, `_SUPPLY_CHAIN_ADVISORY_EMITTED_ALLOWLIST`, `_SPAWN_TOOL_SCOPE_VIOLATION_ALLOWLIST`, `_SPAWN_DEPTH_OR_OVERLAP_ALLOWLIST`, `_SPAWN_FILE_ASSIGNMENT_RECORDED_ALLOWLIST`, `_ACTION_REQUIRED_HELD_ALLOWLIST`, `_ACTION_REQUIRED_RESUMED_ALLOWLIST`, `_ACTION_REQUIRED_REJECTED_ALLOWLIST`, `_PERSISTENT_INSTRUCTIONS_BLOCKED_ALLOWLIST`, `_HINT_PROVENANCE_RECORDED_ALLOWLIST` in `audit_emit.py`)* |
| v2.42 | PLAN-135 W1 S3 (anthropic-surface-harvest, S231) — 1 NEW action `settings_tamper_detected` (`/ceo-boot` Tier-S settings/env tamper-tripwire breadcrumb; one emit per detected class). Producer: `check_settings_tamper_tripwires` (21st Tier-S check) scanning the RESOLVED multi-layer settings via the shared `_lib/effective_config.py` (user/project/local/managed — incl. the gitignored, sentinel-blind `settings.local.json`) + the import-time env snapshot (trusted_env pattern, check_bash_safety.py precedent). Tamper classes (a)-(e) per PLAN-135/research/THREAT-MODEL-WORKSHEET.md §2: `disableAllHooks`, model remap outside the ADR-149 allowlist, `ANTHROPIC_BASE_URL`/`ANTHROPIC_AUTH_TOKEN`/`apiKeyHelper` endpoint remap, `bypassPermissions`/dangerously-skip flags, registered-vs-on-disk hook census. Advisory fail-open; emitted via `emit_generic` (no public typed wrapper — `persona_coverage_synthesized` precedent). Registered via the PLAN-135 W1 Owner kernel ceremony. | *(no new fields on existing actions; per-action allowlist `_SETTINGS_TAMPER_DETECTED_ALLOWLIST` + closed enums `_SETTINGS_TAMPER_CLASSES` / `_SETTINGS_TAMPER_LAYERS` in `audit_emit.py`)* |
| v2.43 | PLAN-135 W2 (anthropic-surface-harvest hook wave) — NEW actions for the W2 new-event hooks. H2 ConfigChange guard contributes 2: `config_change_observed` (allow+audit path) + `config_change_forbidden_key` (advisory-block path; one emit per forbidden-key tamper class scoped to the changed settings layer). Producer `check_config_change.py` (ConfigChange event, dual-registered dogfood + template) scanning the RESOLVED multi-layer settings via the shared `_lib/effective_config.py` (forbidden-keys SINGLE SOURCE with W1 S3, THREAT-MODEL-WORKSHEET §2); blocks ONLY on forbidden-key findings (disableAllHooks / endpoint remap / permission bypass / model remap), allows+audits everything else; hook-census findings observe-only. Advisory fail-open §5; kill-switch `CEO_CONFIG_CHANGE_GUARD=0`. Honest coverage boundary in ADR-153 §H2 (itself a hook; S3 tripwires + O10 OTEL witness are the named compensators). H5 (ADR-154 single-rewriter) contributes `bash_input_rewritten` — `check_bash_safety.py` rewrote a single-subcommand `git push --force`/`-f` to `--force-with-lease` via the PreToolUse `updatedInput` channel, surfaced as `permissionDecision: "ask"` (never a silent allow; the rewrite NEVER degrades the legacy BLOCK into an allow — Doctrine 1 corollary); TYPED wrapper `emit_bash_input_rewritten`; closed-enum `rewrite_class` + before/after sha256 hash pair only (command bytes never persisted; kill-switch `CEO_BASH_FORCE_PUSH_REWRITE=0`). H1 (ADR-153) contributes the compaction-continuity pair (`compaction_continuity_snapshot` + `compaction_context_reinjected`). H3 contributes `subagent_lifecycle_observed` — per-agent SubagentStop lifecycle bracket emitted by `check_fluency_nudge.py` (H3 extension) after consuming the SubagentStart sidecar (`check_subagent_start.py`, new SubagentStart event dual-registered) + the harness `agent_transcript_path`; closed-enum `agent_archetype` + four coarse buckets (`wall_bucket`/`wall_source`/`token_bucket`/`claim_bucket`) only; raw token/wall counts + transcript path/body + agent_id never persisted; TYPED wrapper `emit_subagent_lifecycle_observed`; kill-switch `CEO_SUBAGENT_LIFECYCLE=0`. Sibling W2 units' actions consolidate into this row at arc-verify. Registered via the PLAN-135 W2 Owner ceremony. | *(no new fields on existing actions; per-action allowlists `_CONFIG_CHANGE_OBSERVED_ALLOWLIST` / `_CONFIG_CHANGE_FORBIDDEN_KEY_ALLOWLIST` + closed enum `_CONFIG_CHANGE_LAYERS`; H5 `_BASH_INPUT_REWRITTEN_ALLOWLIST` + closed enum `_BASH_REWRITE_CLASSES`; H3 `_SUBAGENT_LIFECYCLE_OBSERVED_ALLOWLIST` + closed enums `_SUBAGENT_LIFECYCLE_ARCHETYPES` / `_SUBAGENT_LIFECYCLE_BUCKETS` / `_SUBAGENT_LIFECYCLE_WALL_SOURCES`; in `audit_emit.py`; `tamper_class` reuses `_SETTINGS_TAMPER_CLASSES`)* |
| v2.44 | PLAN-135 ARC (anthropic-surface-harvest W5 ops fold) — 3 NEW actions consolidated in the arc layer: `admin_key_lifecycle_event` (o9; `.claude/scripts/key-hygiene.py` Anthropic Admin API key-lifecycle breadcrumb — closed-enum `operation`/`reason` + ids/counts; key material never reaches the emit via producer `_redact()`; load-bearing audit-pair is the append-only `docs/rotation-log.md` row), `statusline_sidecar_write` (o4; `.claude/scripts/statusline-ceo.py` debounced statusLine sidecar-write breadcrumb — numbers + enum-ish ids + 12-char digest only, never the raw stdin), `model_refusal_observed` (o7; `.claude/hooks/_lib/adapters/live/claude.py` `_on_response` model-refusal breadcrumb — closed `stop_details.category` vocabulary ≤64 + provider/model slugs + status/duration ints only; `stop_details.explanation` dropped at the emit site). All three are TRUSTED first-party / adapter-library producers that PRE-REDACT. Registered via the PLAN-135 arc Owner ceremony. **(Hardened in v2.45, Codex R5 P1-2 — moved OFF `_EMIT_GENERIC_PASSTHROUGH` into dedicated per-action `_scrub_*` allowlist branches; see the v2.45 row.)** | *(no new fields on existing actions; as of v2.45 the 3 actions route through dedicated per-action allowlists, not passthrough)* |
| v2.45 | PLAN-135-FOLLOWUP (Codex R5 P1-2/P1-3, S233) — no new actions, no new fields, `event_schema` stays `v2`. **P1-2:** the 3 W5 arc actions (`admin_key_lifecycle_event`, `statusline_sidecar_write`, `model_refusal_observed`) move OFF `_EMIT_GENERIC_PASSTHROUGH` into dedicated deny-by-default per-action `_scrub_*` allowlist branches in `emit_generic` (`_ADMIN_KEY_LIFECYCLE_EVENT_ALLOWLIST` / `_STATUSLINE_SIDECAR_WRITE_ALLOWLIST` / `_MODEL_REFUSAL_OBSERVED_ALLOWLIST`) with field-allowlist + enum/int VALUE coercion (invisible_unicode_blocked precedent) — the Sec MF-3 boundary now holds against a direct/future `emit_generic` caller, not just the trusted producer. **P1-3:** 1 new closed-enum tamper-class member `settings_tamper_sidecar_redirect` on `settings_tamper_detected` + `config_change_forbidden_key`, mirroring `_lib/effective_config.TAMPER_CLASSES` — a settings-LAYER `CEO_STATUSLINE_SIDECAR` write-path steer (output/exfil-path; detected only in settings layers, not the legitimate Owner launch-env override; the always-on writer also rejects symlink/`..` targets at resolution). Registered via the PLAN-135-FOLLOWUP Owner ceremony. | *(no new fields; the 3 actions gain dedicated allowlists; `_SETTINGS_TAMPER_CLASSES` gains `settings_tamper_sidecar_redirect`)* |
| v2.46 | PLAN-135-FOLLOWUP-2 (S234) — no new action, no new fields, `event_schema` stays `v2`, `_KNOWN_ACTIONS` unchanged. **HMAC-integrity fix:** the `statusline_sidecar_write` (o4) percentage fields `context_pct` / `buckets_used_pct_max` are RENAMED to `context_pct_bps` / `buckets_used_pct_max_bps` and re-typed `float`->**integer basis-points** (pct*100), mirroring `fpr_observed_bps`/`pass_rate_bps`/`confidence_bps`. RATIONALE: the canonical encoder (`_lib/canonical_json._validate_no_floats`) forbids any float in an HMAC-covered payload (S181 / ADR-055-AMEND-2); the float form failed `sha compute` on EVERY emit since v2.44 and was written with `hmac=null` + `hmac_error` (and a breadcrumb to `audit-log.errors`) — present in the jsonl but EXCLUDED from the verifiable chain (the action had never once entered the signed chain). **Ranges DIFFER (Sec MF-3 input contract):** `context_pct_bps` 0..10000 (source 0..100%); `buckets_used_pct_max_bps` 0..99900 (source `used_pct` capped at 999% upstream — NO 100% ceiling, so an over-quota burst is not silently floored). The PRODUCER (`.claude/scripts/statusline-ceo.py`, NOT canonical-guarded) owns the `*100` pct->bps scaling and emits finished `_bps` ints; the `_STATUSLINE_SIDECAR_WRITE_ALLOWLIST` scrub branch is the authoritative boundary that int-coerces + clamps (catching `OverflowError` for `float('inf')`) but does NOT re-scale — a direct/future caller is contracted to pass basis-points, not a raw percentage. MIGRATION: zero legacy — no float datum ever entered the verifiable chain and no consumer reads the field (the only reader, `measure_multiplier.py`, reads the separate non-HMAC `statusline-sidecar/v1` JSON FILE, which keeps its float `context_pct` and is NOT renamed). Regression coverage added: every W5 scrub action's emitted event is carried through `canonical_json.encode` and asserted HMAC-encodable — the test gap that hid the born-broken action. | *(field rename + re-type on `statusline_sidecar_write`: `context_pct`->`context_pct_bps` int 0..10000, `buckets_used_pct_max`->`buckets_used_pct_max_bps` int 0..99900; `_STATUSLINE_SIDECAR_WRITE_ALLOWLIST` updated; NO new action — `_KNOWN_ACTIONS` unchanged)* |
| v2.27 | PLAN-107 v1.38.0 SPEC v1 backfill (S145) — 62 actions registered closing residual S107-S128 + S134-S143 gaps. Includes: audit_spool_* + audit_flush_dropped_count + skill_cache_stats (PLAN-094); bash_canonical_bypass_invoked (PLAN-085); ceo_boot_persona_coverage_score (PLAN-091); confidence_gate_* (PLAN-100); cost_envelope_capped + execution_context_* + swarm_paused_owner_absent + swarm_runaway_suspected (PLAN-102); federation_* (PLAN-099); goap_* (PLAN-098); kernel_extension_landed + output_scan_finding_suppressed + persona_coverage_synthesized (PLAN-106); persona_auto_* (PLAN-105); phase_c_enforcing_flipped (PLAN-104); rag_* (PLAN-097); sentinel_signer_* (PLAN-099); streaming_* (PLAN-086); mcp_bearer_friction_observed + mcp_cross_tenant_denied + mcp_soak_fpr_breach (PLAN-085); capability_rollout_complete + kill_switch_invoked (PLAN-099). | *(no new fields; per-action allowlists in `audit_emit.py` + spool_writer.py forensic emits)* |
| v2.28 | PLAN-107 v1.38.0 Wave B.4 — orphan `stdlib_violation` register via kernel-override sentinel `PLAN-107-WAVE-B-ORPHAN-REGISTER` (S145 2026-05-19). | *(no new fields)* |
| v2.30 | PLAN-110 v1.39.0 Wave D (S147 2026-05-20) — 1 NEW action `protocol_edit_missing_amend_paired` for PROTOCOL.md semver-cascade advisory emit (Tier-A; fail-OPEN). Registered via kernel-override sentinel `PLAN-110-WAVE-D-AUDIT-EMIT-EXTENSION`. | *(no new fields; per-action allowlist `_PROTOCOL_EDIT_MISSING_AMEND_PAIRED_ALLOWLIST` in `audit_emit.py`)* |
| v2.31 | PLAN-112-FOLLOWUP-hmac-tamper-fix v1.39.4 Wave B.3 (S152 2026-05-21) — 1 NEW action `chain_reset_marker` per ADR-055-AMEND-2 (PROPOSED). Synthetic genesis entry on rotation boundary; line 1 of every rotation-created fresh audit-log.jsonl; HMAC anchored at GENESIS_PREV. Producer also writes `audit-log.rotation-manifest.json` sidecar (NEW); verifier marker-enforcement scoped via local sidecar (NO archive walking). Closes F-7.7 STATUS_TAMPER on production audit chain (PLAN-112 D3 confirmed). Registered via kernel-override sentinel `PLAN-112-FOLLOWUP-WAVE-B3-AUDIT-EMIT-EXTENSION`. | *(no new fields on existing actions; new sidecar `audit-log.rotation-manifest.json` per ADR-055-AMEND-2)* |
| v2.32 | PLAN-112-FOLLOWUP-persona-routing-wire v1.42.0 W2 (S158) — 2 NEW actions `model_routing_enforced` + `model_routing_eval_error` for the god-mode routing-matrix consult in check_agent_spawn (CONSULT+AUDIT; block deferred). Registered via kernel-override sentinel `PLAN-112-FOLLOWUP-S158-AUDIT-EMIT-EXTENSION`. | *(no new fields on existing actions; per-action allowlists `_MODEL_ROUTING_ENFORCED_ALLOWLIST` + `_MODEL_ROUTING_EVAL_ERROR_ALLOWLIST` in `audit_emit.py`)* |
| v2.33 | PLAN-112-FOLLOWUP-federation-wire-or-delete PHASE2 v1.43.0 (S159) — 1 NEW action `federation_peer_list_reloaded` so the <60s revocation-propagation SLO (P0-1) is forensically observable on every peers.yaml reload. Write-mode ACTIVATION (default-OFF) per ADR-135-AMEND-2. Registered via kernel-override sentinel `PLAN-112-FOLLOWUP-FEDERATION-WIRE-AUDIT-EMIT-EXTENSION`. | `peer_count` (int), `reload_reason` (str enum {content_changed, parse_error_kept_last_good}), `source_path` (str<=128), + chain envelope (`hmac`, `hmac_error`, `event_schema`, `ts`). NOTE: `emit_generic` does NOT auto-inject `session_id`/`project` (S153 R9 residual — audit-attribution wart, not chain-integrity). |
| v2.34 | PLAN-113 Phase B WIRE-DEADMOD v1.45.x (S163) — 2 NEW actions `spec_context_sanitized` + `spawn_confidence_advisory` (spawn-prompt advisory telemetry emitted via `emit_generic` from `check_agent_spawn.py`). ADVISORY ONLY; each has an individual kill-switch (`CEO_SPEC_CTX_SANITIZER_ENABLED` / `CEO_SPAWN_CONFIDENCE_ENABLED`). No prompt/description content persisted. | `original_bytes`, `cleaned_bytes`, `truncated`, `sentinel_violations`, `control_chars_stripped`, `bidi_zw_chars_stripped`, `header_escape_count` (spec_context_sanitized); `action_type`, `confidence_level`, `confidence_marker`, `reason_code`, `is_named_spawn` (spawn_confidence_advisory). |
| v2.35 | PLAN-117 WS-A (S176 2026-05-27) — 1 NEW action `credential_override_late_set_ignored` (ADR-040-AMEND-2 §Layer-1 forensic). Closes an ACCEPTED-ADR contract violation: the live Claude adapter (`_lib/adapters/live/claude.py`) now sources the credential emergency-override SOLELY from the import-time trust-root snapshot (`_lib/trusted_env`), validates ticket-id `^[A-Z][A-Z0-9]*-\d+$` fail-CLOSED, and emits this action when a late-set (post-anchor) override is ignored instead of honored. 24h-window control (§3.3c) carved out as a tracked follow-up (needs cross-process state; not a regression). Registered under canonical sentinel `PLAN-117/architect/round-3` (Owner GPG) + `CEO_KERNEL_OVERRIDE`. | *(no new fields on existing actions; per-action allowlist `_CREDENTIAL_OVERRIDE_LATE_SET_IGNORED_ALLOWLIST` in `audit_emit.py`)* |
| v2.36 | PLAN-118 AC-B5 (S179 2026-05-28) — 1 NEW action `audit_producer_path_pollution_detected` (producer-side fail-CLOSED forensic breadcrumb). Closes the post-PLAN-117 WS-B `ADR-055-AMEND-2` evidence-red defer: 2 live `chain_reset_marker` lines verified `mismatched-recompute` were produced by a stale `_lib` copy whose canonicalization differs from canonical; this action's chokepoint payload distinguishes the marker vs spool-drain origin AND identifies which of the trio (`audit_emit`/`canonical_json`/`audit_hmac`) drifted, via sha256[:8] prefixes (NO raw path echo). Registered via kernel-override sentinel `PLAN-118-WS-B-CHOKEPOINTS`. Defense-in-depth at chokepoints 1 (audit_emit._emit_chain_reset_marker_under_lock) + 2 (audit_emit._write_event HMAC path) + 3 (audit_hmac.compute_entry_hmac entry) + 4 (audit_emit.emit_generic HMAC-bearing dispatch) + 5 (spool_writer._phase4_build_batch drain-path). Recursion-safety per PLAN-118 §Producer runtime fail-CLOSED layer: chokepoint 1 + 5 write the breadcrumb via fast-path / typed wrapper; chokepoints 2/3/4 route through the existing `hmac:null` + `hmac_error` channel with closed-enum value `producer_path_pollution_detected`. | *(no new fields on existing actions; per-action allowlist `_AUDIT_PRODUCER_PATH_POLLUTION_DETECTED_ALLOWLIST` in `audit_emit.py`)* |
| v2.29 | PLAN-099-FOLLOWUP v1.39.1 Wave F.2 — federation write-mode audit surface (S148 2026-05-20) — 19 NEW actions + 1 in-place field-shape supersede (`federation_cert_rotated`). Includes: `federation_audit_event_pushed{,_batch}`, `federation_audit_log_backpressure`, `federation_cert_validity_window_too_large`, `federation_event_action_blocked`, `federation_hmac_secret_rotated`, `federation_key_floor_{rejected,stale}`, `federation_message_storm_detected`, `federation_peer_invalid_no_fingerprint`, `federation_peer_{registered,registered_collision,revoked_remote}`, `federation_pin_legacy_used`, `federation_scope_denied`, `federation_spki_fingerprint_mismatch`, `federation_tamper_detected`, `federation_write_{disabled_sentinel_invalid,endpoint_denied}`. ATT&CK bindings T1499 + T1485 + T1565 + T1556 + T1071.001 + T1573 per `.claude/plans/PLAN-099-FOLLOWUP/attack-rebinding.md` §2. Registered via kernel-override sentinel `PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION`. | *(no new fields; per-action allowlists in `audit_emit.py` `_FEDERATION_*_ALLOWLIST` frozensets)* |

| v2.38 | PLAN-124 WS-1 (ECC value-harvest, S20x) — 1 NEW action `git_hook_bypass_blocked` (git hook-bypass guard breadcrumb). Emitted by `check_bash_safety.py` via the `_lib/git_bypass.py` tokenizer (clean-room stdlib re-impl crediting `affaan-m/ECC` `scripts/hooks/block-no-verify.js`, MIT) when a `--no-verify`/`core.hooksPath`/env-channel/`git config`-write/`--git-dir`/`-C`/alias bypass is blocked, plus the proven dual-auth escape hatch (`CEO_GIT_BYPASS_ALLOW` via the import-time `trusted_env` snapshot, ADR-040-AMEND-2 §Layer-1) which ALLOWS + emits `escape_hatch_used`. Bounded fail-CLOSED `parse_failure` (MF-L). The ONLY caller-supplied field is the closed-enum `flag_class`; the matched command bytes are NEVER persisted (MF-G — a flag value can carry a secret). Dedicated scrub branch + `_GIT_HOOK_BYPASS_BLOCKED_ALLOWLIST`, NEVER `_EMIT_GENERIC_PASSTHROUGH`. ADR-143 (PROPOSED). | *(no new fields on existing actions; per-action allowlist `_GIT_HOOK_BYPASS_BLOCKED_ALLOWLIST` + closed-enum `_GIT_HOOK_BYPASS_FLAG_CLASSES` in `audit_emit.py`)* |

When grepping for "v2.N" to understand a change, consult BOTH files.

### Additivity

- Adding a field to an existing action → MINOR bump of SPEC
- Removing / renaming a field → MAJOR bump (forbidden within v1 SPEC)
- Adding a new action literal → MINOR bump + new ADR

### Consumer contract

Consumers MUST:
- Tolerate unknown fields (forward-compat)
- Treat absence of `event_schema` as v1
- Handle nullable `tokens_*` fields

### `tokens_*` field semantics (PLAN-006 ADR-016, amended PLAN-045)

`tokens_in`, `tokens_out`, `tokens_total` are **optional, nullable,
always-present when the emitter supports the field**. The field takes
one of two canonical states + one legacy-compatibility state:

| State | Value shape | Producer | Meaning |
|---|---|---|---|
| A | Key **absent** from record | Non-canonical producer OR pre-ADR-016 data import | "Producer does not track tokens at all." Consumer-visible in legacy logs (`event_schema < v2`) only. |
| B | Key **present**, value `null` | Canonical producer (every hook through `audit_emit`) | "Producer tracks the field but cannot extract a count for this entry (e.g. non-LLM action, tool-use envelope missing usage block)." |
| C | Key **present**, value int `>= 0` | Canonical producer | "Producer extracted this count." |

**Canonical producer invariant:** every `audit_emit.*` path sets the
three keys via `setdefault` in `_write_event` (at import-stable line
~290 of `audit_emit.py`). State A therefore **never** appears in a
log written by this framework's reference implementation — it is
reserved for non-canonical producers or pre-ADR-016 historical data.

**Consumer tolerance matrix** (enforced by `audit-query.py tokens`):

| Case | Consumer MUST |
|---|---|
| Key absent (State A) | Treat as "unknown" — do NOT default to 0. Counted under `spawns_without_tokens`. |
| Key present, null (State B) | Treat as "unknown". Counted under `spawns_without_tokens`. |
| Key present, int (State C) | Use as the extracted count. Summed into totals + per-skill / per-subagent_type / per-day. |
| Key present, non-int (malformed) | Reject the entry (upstream producer bug). Treated as null (never summed). |

**Why two-canonical-states + one-legacy-state** (2026-04-20
amendment): the original three-state contract (ADR-016, PLAN-006)
was written before the reference emitter landed in Sprint 6. Once
`audit_emit._write_event` became the sole canonical producer, its
`setdefault(None)` semantics collapsed the "absent-from-canonical"
case. The SPEC is aligned here to match the reference producer's
observable behavior; non-canonical third-party producers are still
permitted to emit State A entries and consumers must tolerate all
three.

Event stream version unchanged by this amendment — `event_schema`
value stays `"v2"` (additive field semantics per §Additivity).

### Rotation

Log rotates at 10 MB or 30 days (whichever first). Archived to
`audit-log-YYYY-MM.jsonl`. Consumers supporting multi-file read use
`--include-rotated`.

### Redaction

`desc_preview` and `reason_preview` are passed through a best-effort
regex secret redactor. `desc_hash` (SHA-256 of raw pre-redaction text)
allows correlation without storing plaintext. See authoritative
`.claude/plans/AUDIT-LOG-SCHEMA.md` §3 for the redaction pattern list.

## Version history

| SPEC version | Source commit | Notes |
|---|---|---|
| 1.0.0-rc.1 | Sprint 4 opening | v1 agent_spawn + v2 five new actions |
| 1.0.0-rc.1 (revised) | Sprint 5 Phase 5 | v2.1 adds `injection_flag` action (ADR-011) |
| 1.0.0-rc.1 (revised) | Sprint 13 Phase A.0 | v2.5 adds 10 new actions — 6 live-adapter/breaker/credential (Gap #3 fix per ADR-040) + 4 MCP server (per ADR-042) |
| 1.0.0-rc.1 (revised) | PLAN-028 Wave A | v2.7 adds 5 lifecycle + output-scan actions (ADR-056 + ADR-057) |
| 1.0.0-rc.1 (revised) | PLAN-041 Wave A+ | v2.8 adds 5 RAG sidecar actions (ADR-062) |
| 1.0.0-rc.1 (revised) | PLAN-043 Wave B | v2.9 adds 9 dynamic tier-policy actions (ADR-064) |
| 1.0.0-rc.1 (revised) | PLAN-060 Phase B | v2.12 adds 3 audit-tokens actions (SEC-P0-04: audit_tokens_emitted + audit_tokens_timeout + audit_tokens_key_dropped) |
| 1.0.0-rc.1 (revised) | PLAN-052 (Session 67) | v2.13 adds 1 MCP scanner action (ADR-083: mcp_injection_finding) |
| 1.0.0-rc.1 (revised) | PLAN-044 audit-v2 (Session 71 D-4) | v2.14 adds 2 optional fields on veto_triggered (caller + session_id) for kernel override forensic traceability (P1 #6) |
| 1.0.0-rc.1 (revised) | PLAN-044 audit-v3 (Session 76) | v2.15 registers 2 skill bootstrap actions (skill_bootstrap_used + skill_bootstrap_post_hash) that were emitted by hooks but dropped silently by `_write_event`. Codex DIM-04 #1 closure. |
| 1.0.0-rc.1 (revised) | PLAN-069 Phase 1 (Session 81) | v2.16 adds 2 capture-mode lifecycle actions (replay_capture_started + replay_capture_completed) per ADR-101. Replaces `replay_started:capture` / `replay_completed:capture` reuse with mode-distinct actions. R9 LIVE LGPD leak closure ships in same Wave D ceremony. |
| 1.0.0-rc.1 (revised) | PLAN-065 Phase 2 (Session 82) | v2.17 adds 2 /ceo-boot autopilot lifecycle actions (ceo_boot_emitted + ceo_boot_check_skipped) per ADR-098. Sec MF-3 enforced via `_scrub_ceo_boot_event`. Closes Reality-Ledger fixture #4 (declared-but-not-wired pattern). |
| 1.0.0-rc.1 (revised) | PLAN-070 (Session 85) | v2.18 adds 2 MCP canonical-guard middleware actions (mcp_canonical_guard_allowed + mcp_canonical_guard_blocked) per ADR-102. Layer B server-side middleware closes ADR-095 §gate-#6 NG-06. |
| 1.0.0-rc.1 (revised) | PLAN-071 (Session 87) | v2.19 adds 4 Adaptive Execution Kernel + Reality Ledger advisory actions (task_route_advised + task_route_key_dropped + reality_ledger_finding + reality_ledger_key_dropped) per ADR-104. Sec MF-3 enforced via dedicated allowlists. |
| 1.0.0-rc.1 (revised) | PLAN-078 Wave 1+2 (Session 92) | v2.20 adds 3 Reality Ledger advisory actions (model_routing_advised + estimate_drift_detected + estimate_drift_systematic_bias). Wave 1 ships in S89 Fase 1 commit 2cb1472; registered S92 Wave 1b ceremony 2026-05-07. |
| 1.0.0-rc.1 (revised) | PLAN-078 Wave 5 (Session 95) | v2.21 adds 1 TaskCreate-candidate orchestration action (ceo_boot_task_candidate_emitted). Emitted by `.claude/scripts/ceo-boot.py` per `<!-- TASKCREATE-CANDIDATE -->` marker block written when gate_pass=False AND severity≥medium. Top-3 cap, 24h TTL dedup. Sec MF-3 enforced via `_CEO_BOOT_TASK_CANDIDATE_EMITTED_ALLOWLIST`. |

---

## Action: `mcp_canonical_guard_allowed` (PLAN-070 v1.13.0+)

Emitted by `.claude/hooks/_lib/mcp/canonical_guard.py:check_mcp_call`
on every Layer B middleware ALLOW decision for a tool whose name
matches `mcp__*`. Sec MF-3 allowlist (R6-01 tightened): caller-side
fields restricted to `tool_name`, `target_path`, `reason`.
Auto-baseline: `action`, `ts`, `session_id`, `project`, `event_schema`,
`tokens_*`, `hmac`, `hmac_error`.

```json
{
  "action": "mcp_canonical_guard_allowed",
  "ts": "2026-05-05T12:34:56.789Z",
  "session_id": "session-xxx",
  "project": "ceo-orchestration",
  "event_schema": "v2",
  "tool_name": "mcp__codex__codex",
  "target_path": "PROTOCOL.md",
  "reason": "sentinel:.claude/plans/PLAN-070/architect/round-4/approved.md",
  "tokens_in": null, "tokens_out": null, "tokens_total": null,
  "hmac": null, "hmac_error": null
}
```

## Action: `mcp_canonical_guard_blocked` (PLAN-070 v1.13.0+)

Emitted on every Layer B middleware BLOCK decision. Same allowlist
as `mcp_canonical_guard_allowed`. The `reason` field encodes a stable
enum (e.g. `canonical_no_sentinel`, `path_escapes_repo_root_fail_closed`,
`blob_authoritative_parse_failed_fail_closed`, `middleware_fault:<ExcName>`).

```json
{
  "action": "mcp_canonical_guard_blocked",
  "ts": "2026-05-05T12:34:56.789Z",
  "session_id": "session-xxx",
  "project": "ceo-orchestration",
  "event_schema": "v2",
  "tool_name": "mcp__codex__apply_patch",
  "target_path": "PROTOCOL.md",
  "reason": "canonical_no_sentinel",
  "tokens_in": null, "tokens_out": null, "tokens_total": null,
  "hmac": null, "hmac_error": null
}
```

## Action: `model_routing_advised` (PLAN-078 v1.15.0+)

Advisory-emit-only telemetry. Emitted by `check_agent_spawn.py`
post-VETO-check when an agent spawn is observed; reads agent payload
archetype + frontmatter `model:` field; if absent, in-process
`task_route.classify()` returns recommendation. Field allowlist
restricted to 6 caller fields:

- `archetype` — string, agent archetype slug
- `task_type` — string, classified task type
- `model_recommended` — string, model id (e.g. `claude-fable-5`)
- `confidence_basis_points` — int 0..1000 (recommendation confidence ×
  1000; `confidence_basis_points / 1000` recovers float ratio).
  Codex S89 W1+W2 fix-pack #2: int basis-points NOT float, because
  `canonical_json.encode()` forbids floats in HMAC-covered events
  (`hmac=null` + `hmac_error=CanonicalJsonError` breadcrumb otherwise).
- `applied_or_skipped` — string enum (`applied` | `skipped_*`)
- `override_reason` — string, why classify was skipped (e.g.
  `frontmatter_model_present`)

Auto-baseline: `action`, `ts`, `session_id`, `project`, `event_schema`,
`tokens_*`, `hmac`, `hmac_error`.

Bypass: `CEO_MODEL_ROUTING=0` (registered in `docs/GOVERNANCE.md`
Kill switches).

```json
{
  "action": "model_routing_advised",
  "ts": "2026-05-06T12:34:56.789Z",
  "session_id": "session-xxx",
  "project": "ceo-orchestration",
  "event_schema": "v2",
  "archetype": "code-reviewer",
  "task_type": "frontmatter",
  "model_recommended": "claude-fable-5",
  "confidence_basis_points": 875,
  "applied_or_skipped": "skipped_classify_frontmatter_authoritative",
  "override_reason": "frontmatter_model_present",
  "tokens_in": null, "tokens_out": null, "tokens_total": null,
  "hmac": null, "hmac_error": null
}
```

## Action: `estimate_drift_detected` (PLAN-078 v1.15.0+)

Reality Ledger detector #7 emits this per-plan when on `status: done`
transition the actual compute span vs estimate exceeds drift threshold
(symmetric `max(f, 1/f) > 1.2` per Codex S89 W1+W2 fix-pack #3 —
bidirectional: overrun OR underrun). Field allowlist restricted to 6
caller fields:

- `plan_id` — string (e.g. `PLAN-070`); Owner-visible per ADR-033
- `drift_factor_compute_basis_points` — int (multiplier × 1000); 1.234×
  → 1234. Float forbidden (HMAC chain integrity).
- `drift_factor_owner_basis_points` — int; computed from
  GPG-signed-commit count; gated on `actual_owner_min > 0` (skipped
  otherwise to avoid false-positive on plans with no GPG ceremonies).
- `severity` — string enum (`low` | `medium` | `high`)
- `plan_count_in_run` — int, total plans evaluated in this detector run
- `systematic_bias_direction` — string enum (`""` | `underestimate` |
  `overestimate`); empty when threshold not crossed.
  `underestimate` = actual span exceeded estimated upper bound (overrun,
  factor > 1.2; we under-estimated).
  `overestimate` = actual span below estimated lower bound (underrun,
  factor < 0.83 = 1/1.2; we over-estimated).

Bypass: `CEO_REALITY_LEDGER_DETECTOR_07=0`.

```json
{
  "action": "estimate_drift_detected",
  "ts": "2026-05-06T12:34:56.789Z",
  "session_id": "session-xxx",
  "project": "ceo-orchestration",
  "event_schema": "v2",
  "plan_id": "PLAN-070",
  "drift_factor_compute_basis_points": 12700,
  "drift_factor_owner_basis_points": 0,
  "severity": "high",
  "plan_count_in_run": 5,
  "systematic_bias_direction": "underestimate",
  "tokens_in": null, "tokens_out": null, "tokens_total": null,
  "hmac": null, "hmac_error": null
}
```

## Action: `estimate_drift_systematic_bias` (PLAN-078 v1.15.0+)

Reality Ledger detector #7 emits this recommendation event after
N=5 plans in same drift direction. Strict 4-caller-field contract:

- `bias_direction` — string enum (`underestimate` | `overestimate`).
  Same semantics as `systematic_bias_direction` field above.
- `plans_affected_count` — int, plans count satisfying threshold
- `avg_drift_factor_compute_basis_points` — int (avg × 1000)
- `avg_drift_factor_owner_basis_points` — int (avg × 1000)

```json
{
  "action": "estimate_drift_systematic_bias",
  "ts": "2026-05-06T12:34:56.789Z",
  "session_id": "session-xxx",
  "project": "ceo-orchestration",
  "event_schema": "v2",
  "bias_direction": "underestimate",
  "plans_affected_count": 5,
  "avg_drift_factor_compute_basis_points": 8500,
  "avg_drift_factor_owner_basis_points": 0,
  "tokens_in": null, "tokens_out": null, "tokens_total": null,
  "hmac": null, "hmac_error": null
}
```

## Action: `ceo_boot_task_candidate_emitted` (PLAN-078 Wave 5 / v1.15.0+)

`/ceo-boot` writes a `<!-- TASKCREATE-CANDIDATE -->` marker block to
stdout for each top-3 high/medium recommendation when `gate_pass=False`
(skipped under `--short`, `--cached`, `--json`, or env
`CEO_BOOT_AUTO_TASK=0`). The Claude orchestrator running the slash
command reads the marker blocks and invokes `TaskCreate`. This audit
event records each emitted marker (Sec MF-3 field allowlist; subject
text NEVER persisted).

Field allowlist restricted to 4 caller fields:

- `rank` — int 1..3 (ordinal of marker in the boot run); out-of-range
  values fall back to `0` (drift sentinel).
- `severity` — string enum (`low` | `medium` | `high`); unknown values
  become `""` per typed-wrapper input validation.
- `subject_hash` — string; 12-hex-char prefix of
  `sha256(NFKC(visible Subject text))`. Non-hex chars stripped,
  length-bounded. The orchestrator reconstructs the same digest from
  the visible `Subject:` line for dedup against the live task list.
- `awaiting_confirm` — bool; reserved future flag for an
  "Owner-must-confirm" escape. Default `false`; the v1.15.0 baseline
  always auto-creates without confirmation.

Bypass: `CEO_BOOT_AUTO_TASK=0` (operator opt-out).
State file: `~/.claude/projects/<project>/state/ceo-boot-tasks-emitted.json`
(24h TTL, filelock-guarded, bounded ≤256 entries; override via env
`CEO_BOOT_TASK_STATE_PATH`).

```json
{
  "action": "ceo_boot_task_candidate_emitted",
  "ts": "2026-05-08T12:34:56.789Z",
  "session_id": "session-xxx",
  "project": "ceo-orchestration",
  "event_schema": "v2",
  "rank": 1,
  "severity": "high",
  "subject_hash": "840915797aa1",
  "awaiting_confirm": false,
  "tokens_in": null, "tokens_out": null, "tokens_total": null,
  "hmac": null, "hmac_error": null
}
```

## Pair-Rail Multi-LLM events (PLAN-075 v1.13.x patch — ADR-106 + ADR-110)

Wired by `check_pair_rail.py` PreToolUse hook on Edit|Write|MultiEdit
against L3+ canonical-guarded paths. SPEC v2.22 introduces 4 new
actions registered in `_lib/audit_emit.py:_KNOWN_ACTIONS` via
`KERNEL_OVERRIDE` ceremony (audit_emit.py is in `_KERNEL_PATHS`).

### `pair_rail_review_passed`

Codex MCP read-only review of an L3+ tool call returned a clean
response (no write-shaped patches). Hook ALLOWED the tool call.

| Field | Type | Notes |
|---|---|---|
| `target_path` | string ≤300 | repo-relative path of the tool's target |
| `tool_name` | string ≤50 | Edit \| Write \| MultiEdit |
| `codex_duration_ms` | int | wall-clock of the Codex invoke |
| `codex_response_sha256` | string ≤64 | SHA-256 of Codex stdout (forensic trace) |

### `pair_rail_codex_unavailable`

Codex MCP unavailable (binary missing, connect timeout, spawn error,
or kill-switch). Hook fail-OPENed (allow). Forensic breadcrumb.

| Field | Type | Notes |
|---|---|---|
| `target_path` | string ≤300 | |
| `tool_name` | string ≤50 | |
| `reason` | string ≤64 | `binary_missing` \| `connect_timeout` \| `spawn_error` \| `disabled_via_killswitch` |

### `pair_rail_codex_violation`

Codex MCP review returned a write-shaped patch. Codex is read-only by
contract — write-shaped response is a contract violation. Hook BLOCKED.

| Field | Type | Notes |
|---|---|---|
| `target_path` | string ≤300 | |
| `tool_name` | string ≤50 | |
| `violation_type` | string ≤64 | `unified_diff_detected` \| `apply_patch_envelope` \| `json_patch_rfc6902` \| `mcp_write_tool_call` |
| `codex_response_sha256` | string ≤64 | |

### `pair_rail_sentinel_bypass`

Owner-signed sentinel (verified by `check_canonical_edit.py` upstream)
grants the L3+ path. Pair-rail review short-circuited.

| Field | Type | Notes |
|---|---|---|
| `target_path` | string ≤300 | |
| `tool_name` | string ≤50 | |
| `sentinel_path` | string ≤300 | path to the sentinel that granted access |

### `pair_rail_codex_injection_detected`

PLAN-081 Phase 1-full / R1 S-Sec-5. Emitted by `check_codex_response.py`
PostToolUse hook on Codex MCP tool responses when ingress sanitization
detects prompt-injection patterns. ADVISORY only per ADR-106 (PostToolUse
hooks cannot block). Forensic surface for SOC alerting via
`audit-query.py codex-injection-summary`.

| Field | Type | Notes |
|---|---|---|
| `tool_name` | string ≤50 | `mcp__codex__codex` or `mcp__codex__codex-reply` |
| `family_ids` | list[string] | sorted unique subset of `harness_mimicry` / `xml_system_tag` / `tool_use_forgery` |
| `match_count` | int ≥0 | total match count across all families |
| `first_offset_bucket` | string | closed enum: `0-100` / `100-1k` / `1k-10k` / `10k-100k` / `100k+` (raw offset is FORBIDDEN per LLM06 side-channel guard) |


### `token_budget_guard_paused` — PLAN-083 Wave 0b sub-agent 0.4 (S106 2026-05-11)

Fired by token-budget-guard.py when cumulative plan tokens cross threshold × estimate. Volume cap ≤10/hr.

**Caller fields:** `plan_id` / `estimate_tokens` / `actual_tokens` / `ratio_basis_points` / `threshold_basis_points`

**Baseline fields:** action, ts, session_id, project, event_schema, tokens_in, tokens_out, tokens_total, hmac, hmac_error.

**Sec MF-3 allowlist:** `_TOKEN_BUDGET_GUARD_PAUSED_ALLOWLIST` in `.claude/hooks/_lib/audit_emit.py`. Deny-by-default; dispatch-gate in `emit_generic` enforces field whitelist; forbidden fields stripped + breadcrumb emitted.

### `anti_ceo_overhead_block` — PLAN-083 Wave 0b sub-agent 0.5 (S106 2026-05-11)

Fired by check_anti_ceo_overhead.py PreToolUse hook when CEO-overhead anti-pattern detected. Emit budget ≤20/day sliding window.

**Caller fields:** `anti_pattern_id` / `count_in_window` / `override_recommended_subagent_type`

**Baseline fields:** action, ts, session_id, project, event_schema, tokens_in, tokens_out, tokens_total, hmac, hmac_error.

**Sec MF-3 allowlist:** `_ANTI_CEO_OVERHEAD_BLOCK_ALLOWLIST` in `.claude/hooks/_lib/audit_emit.py`. Deny-by-default; dispatch-gate in `emit_generic` enforces field whitelist; forbidden fields stripped + breadcrumb emitted.

### `anti_ceo_overhead_override_used` — PLAN-083 Wave 0b sub-agent 0.5 (S106 2026-05-11)

Fired by check_anti_ceo_overhead.py when CEO_OVERHEAD_ACK=1 env override bypasses a block.

**Caller fields:** `anti_pattern_id` / `override_justification_sha`

**Baseline fields:** action, ts, session_id, project, event_schema, tokens_in, tokens_out, tokens_total, hmac, hmac_error.

**Sec MF-3 allowlist:** `_ANTI_CEO_OVERHEAD_OVERRIDE_USED_ALLOWLIST` in `.claude/hooks/_lib/audit_emit.py`. Deny-by-default; dispatch-gate in `emit_generic` enforces field whitelist; forbidden fields stripped + breadcrumb emitted.

### `smart_loading_resolved` — PLAN-083 Wave 0b sub-agent 0.7d (S106 2026-05-11)

Fired by smart-loading-resolver.py per resolution. Carries profile + active/suppressed counts + context budget total + arbitration dropped count.

**Caller fields:** `profile` / `active_count` / `suppressed_count` / `context_total_tokens` / `arbitration_dropped_count`

**Baseline fields:** action, ts, session_id, project, event_schema, tokens_in, tokens_out, tokens_total, hmac, hmac_error.

**Sec MF-3 allowlist:** `_SMART_LOADING_RESOLVED_ALLOWLIST` in `.claude/hooks/_lib/audit_emit.py`. Deny-by-default; dispatch-gate in `emit_generic` enforces field whitelist; forbidden fields stripped + breadcrumb emitted.


### `first_run_wizard_completed` — PLAN-083 Wave 2 sub-agent 2.1 (S106 2026-05-11)

Wizard completion event.

**Caller fields:** `profile` / `recommendation_count` / `user_action`

**Sec MF-3 allowlist:** `_FIRST_RUN_WIZARD_COMPLETED_ALLOWLIST` in audit_emit.py.

### `contextual_recommendation_emitted` — PLAN-083 Wave 2 sub-agent 2.2 (S106 2026-05-11)

Contextual recommender emit.

**Caller fields:** `profile` / `recommendation_count` / `top_score` / `suppressed_count`

**Sec MF-3 allowlist:** `_CONTEXTUAL_RECOMMENDATION_EMITTED_ALLOWLIST` in audit_emit.py.

### `value_dashboard_summarized` — PLAN-083 Wave 2 sub-agent 2.4 (S106 2026-05-11)

Weekly value dashboard rollup.

**Caller fields:** `period_days` / `cost_usd_int_cents` / `bugs_count` / `dispatches_count` / `plans_count`

**Sec MF-3 allowlist:** `_VALUE_DASHBOARD_SUMMARIZED_ALLOWLIST` in audit_emit.py.

### `trading_write_override_used` — PLAN-083 Wave 2 sub-agent 2.7 (S106 2026-05-11)

Trading-readonly write override invoked.

**Caller fields:** `allowed` / `reason` / `target_path_sha256_prefix` / `justification_sha256_prefix` / `justification_length` / `err_preview` (OPTIONAL on path resolution failure)

**Sec MF-3 allowlist:** `_TRADING_WRITE_OVERRIDE_USED_ALLOWLIST` in audit_emit.py.

### `trading_kill_switch_invoked` — PLAN-083 Wave 2 sub-agent 2.7 (S106 2026-05-11)

Trading kill-switch read (missing repo-profile.yaml).

**Caller fields:** `reason`

**Sec MF-3 allowlist:** `_TRADING_KILL_SWITCH_INVOKED_ALLOWLIST` in audit_emit.py.

### `trading_kill_switch_disabled` — PLAN-083 Wave 2 sub-agent 2.7 (S106 2026-05-11)

Trading kill-switch disabled via escape-hatch ceremony.

**Caller fields:** `justification_sha256_prefix` / `signer_fingerprint_prefix` / `signed_new` / `justification_length`

**Sec MF-3 allowlist:** `_TRADING_KILL_SWITCH_DISABLED_ALLOWLIST` in audit_emit.py.

### `anthropic_429_observed` — PLAN-086 Wave B (S112 2026-05-12)

Anthropic API 429 rate-limit response observed by live adapter. Advisory only; the adapter performs its own back-off + breaker bookkeeping.

**Caller fields:** `model` / `retry_after_s` / `breaker_state` / `provider`

**Sec MF-3 allowlist:** `_ANTHROPIC_429_OBSERVED_ALLOWLIST` in audit_emit.py.

### `codex-reply` — PLAN-086 Wave C (S112 2026-05-12)

Codex reply session-id chain integrity advisory; emitted when a `mcp__codex__codex-reply` invocation references a session prior emit reported.

**Caller fields:** `session_id` / `chain_step` / `prior_action`

**Sec MF-3 allowlist:** `_CODEX_REPLY_ALLOWLIST` in audit_emit.py.

### `codex_invoke_dispatched` — PLAN-088 Wave 1 canonical-13 (S114 2026-05-13)

Codex MCP invocation dispatched. ATLAS: AML.T0050 (LLM Plugin / supply-chain signal).

**Caller fields:** `session_id` / `task_class` / `model_advised` / `phase`

**Sec MF-3 allowlist:** `_CODEX_INVOKE_DISPATCHED_ALLOWLIST` in audit_emit.py.

### `git_index_lock_retry` — PLAN-086 Wave G (S112 2026-05-12)

Git index.lock retry breadcrumb (advisory; emitted by hooks that detected `.git/index.lock` and retried).

**Caller fields:** `attempt` / `wait_ms` / `outcome`

**Sec MF-3 allowlist:** `_GIT_INDEX_LOCK_RETRY_ALLOWLIST` in audit_emit.py.

### `mcp_canonical_guard_internal_error` — PLAN-086 Wave D (S112 2026-05-12)

MCP canonical-guard internal-error breadcrumb. Fail-open invariant: never blocks the user session on its own bug.

**Caller fields:** `tool_name` / `error_class` / `error_brief`

**Sec MF-3 allowlist:** `_MCP_CANONICAL_GUARD_INTERNAL_ERROR_ALLOWLIST` in audit_emit.py.

### `mcp_route_advised` — PLAN-086 Wave D (S112 2026-05-12)

MCP routing advisory emitted by `_lib/mcp_routing.resolve()`. PLAN-088 R2 iter-2 strict-13 cardinality: `signal_source ∈ {mcp_task_class, specialization_promoted}` discriminator covers both AUTO-06 MCP routing AND AUTO-10 general→specialized promotion via a SINGLE canonical action. ATLAS: AML.T0050.

**Caller fields:** `session_id` / `task_class` / `suggested_servers` / `kill_switch_overrides` / `signal_source`

**Sec MF-3 allowlist:** `_MCP_ROUTE_ADVISED_ALLOWLIST` in audit_emit.py.

### `repo_profile_confirmed` — PLAN-086 Wave H (S112 2026-05-12)

Repo-profile detector confirmation breadcrumb. Emitted on first-run-wizard + smart-loading entry points.

**Caller fields:** `profile_slug` / `confidence_basis_points` / `caller`

**Sec MF-3 allowlist:** `_REPO_PROFILE_CONFIRMED_ALLOWLIST` in audit_emit.py.

### `subagent_findings_partial_drop` — PLAN-088 Wave 1 canonical-13 (S114 2026-05-13)

Sub-agent dispatch returned partial findings (truncated by token cap / time cap). Advisory only. ATLAS: AML.T0048 (subagent supply-chain).

**Caller fields:** `subagent_type` / `expected_count` / `actual_count` / `truncation_reason`

**Sec MF-3 allowlist:** `_SUBAGENT_FINDINGS_PARTIAL_DROP_ALLOWLIST` in audit_emit.py.

### `thinking_budget_set` — PLAN-086 Wave A R-013 (S112 2026-05-12)

Extended-thinking budget configured for the live adapter call. Advisory; the kill switch `CEO_THINKING_AUTO_DISABLE=1` is honored at the callsite.

**Caller fields:** `model` / `budget_tokens` / `rationale` / `source`

**Sec MF-3 allowlist:** `_THINKING_BUDGET_SET_ALLOWLIST` in audit_emit.py.

### `batch_dispatched` — PLAN-088 Wave 1 canonical-13 (S114 2026-05-13)

Batch live-adapter dispatch breadcrumb. Reserved for `BatchClaudeLiveAdapter` (PLAN-090 W4.2 production wire).

**Caller fields:** `session_id` / `batch_size` / `model` / `policy`

**Sec MF-3 allowlist:** `_BATCH_DISPATCHED_ALLOWLIST` in audit_emit.py.

### `cache_discipline_alerted` — PLAN-088 Wave 1 canonical-13 (S114 2026-05-13)

Cache-discipline alert breadcrumb. Reserved for cache-tier observation when a Gate-1 file edit invalidates the prompt cache mid-session.

**Caller fields:** `file_path` / `gate_tier` / `cost_estimate_basis_points`

**Sec MF-3 allowlist:** `_CACHE_DISCIPLINE_ALERTED_ALLOWLIST` in audit_emit.py.

### `cookbook_pattern_advised` — PLAN-088 Wave 1 canonical-13 (S114 2026-05-13)

Cookbook pattern advisory breadcrumb. SEMI-11 — Owner-facing recommendation, never auto-applied. Real wire deferred to PLAN-092.

**Caller fields:** `pattern_slug` / `recommendation_origin` / `applied`

**Sec MF-3 allowlist:** `_COOKBOOK_PATTERN_ADVISED_ALLOWLIST` in audit_emit.py.

### `estimate_calibrator_pipeline_run` — PLAN-088 Wave 6 (S114 2026-05-13)

Bayesian estimate-calibrator pipeline run breadcrumb. Emitted by `_lib/estimation/pipeline.py`.

**Caller fields:** `plan_id` / `iters` / `posterior_mean_ms` / `posterior_p95_ms`

**Sec MF-3 allowlist:** `_ESTIMATE_CALIBRATOR_PIPELINE_RUN_ALLOWLIST` in audit_emit.py.

### `first_run_wizard_dispatched` — PLAN-088 Wave 1 canonical-13 (S114 2026-05-13)

First-run wizard dispatch breadcrumb. Reserved for SessionStart auto-spawn callsite (PLAN-093 production wire).

**Caller fields:** `repo_profile` / `wizard_step` / `applied`

**Sec MF-3 allowlist:** `_FIRST_RUN_WIZARD_DISPATCHED_ALLOWLIST` in audit_emit.py.

### `pair_rail_phase_advanced` — PLAN-088 Wave 1 canonical-13 (S114 2026-05-13)

Pair-Rail phase transition breadcrumb (SHADOW → DRY_RUN → DISABLED). ACTIVE phase deferred to PLAN-090. ATLAS: AML.T0050.

**Caller fields:** `prior_phase` / `new_phase` / `trigger` / `samples_observed`

**Sec MF-3 allowlist:** `_PAIR_RAIL_PHASE_ADVANCED_ALLOWLIST` in audit_emit.py.

### `tier_policy_misrouting_advised` — PLAN-088 Wave 1 canonical-13 (S114 2026-05-13)

Tier-policy misrouting advisory breadcrumb. PLAN-091 A.1 16th Tier-S check `check_tier_policy_misrouting_24h` queries the 24h audit window for events of this kind. ATLAS: AML.T0048.

**Caller fields:** `task_class` / `expected_model` / `actual_model` / `ratio_basis_points`

**Sec MF-3 allowlist:** `_TIER_POLICY_MISROUTING_ADVISED_ALLOWLIST` in audit_emit.py.

### `persona_demand_opened` (PLAN-104 Wave A — S134 R2 ACCEPT)

Emitted by `.claude/scripts/persona_demand_scan.py` when a new demand
event is detected within the 168h scan horizon (bounded local-git
introspection). Demand sources:

| `demand_event_type` | Expected persona            | Detection                                    |
| ------------------- | --------------------------- | -------------------------------------------- |
| `branch_ahead`      | `code-reviewer`             | Non-trunk branch >=1 commit ahead of `origin/main` |
| `auth_edit`         | `security-engineer`         | File edit matching auth path patterns        |
| `test_edit`         | `qa-architect`              | New test file OR mutation-testing config     |
| `detect_edit`       | `threat-detection-engineer` | SIEM rule / detection-as-code change         |

| Field                | Type   | Required | Notes                                                  |
| -------------------- | ------ | -------- | ------------------------------------------------------ |
| `demand_id`          | string | yes      | `sha256(NFKC(preimage))[:16]`; preimage per demand type |
| `demand_event_type`  | enum   | yes      | `branch_ahead` / `auth_edit` / `test_edit` / `detect_edit` |
| `expected_persona`   | enum   | yes      | code-reviewer / security-engineer / qa-architect / threat-detection-engineer |
| `target_ref_hash`    | string | yes      | `sha256(NFKC(target_ref))[:12]`; raw value NEVER persisted |
| `match_window_hours` | int    | yes      | 24 (uniform across types per S134 R2 Q3)               |
| `session_id`         | string | optional | propagated from caller                                 |
| `project`            | string | optional | repo identifier                                        |

### `persona_demand_matched` (PLAN-104 Wave A; PLAN-132 / ADR-145)

Emitted by `.claude/scripts/persona_demand_resolver.py` when a demand is
satisfied within the `match_window_hours` window after `persona_demand_opened`,
by EITHER of two modalities:

- `native_spawn` (default): an `agent_spawn` of `expected_persona` fires
  in-window. Strict-match: `actual_persona == expected_persona` (S134 R2 Q4 fold;
  no peer substitution).
- `codex_review` (PLAN-132 / ADR-145): a branch-bound, in-window cross-model
  Codex review (`codex_review_invoked` with `review_source` in
  `{adhoc_mcp, user_code_auto}` AND a non-empty `target_ref_hash` equal to the
  demand's `target_ref_hash`) satisfies a `code-reviewer` demand ONLY. The other
  three demand types (`security-engineer`, `qa-architect`,
  `threat-detection-engineer`) keep strict native-spawn match. For this modality
  the emitter sets `actual_persona = "code-reviewer"`, so the invariant
  `actual_persona == expected_persona` STILL HOLDS. Extending `codex_review`
  recognition to any other persona requires a fresh ADR (a code change to the
  resolver's literal guard, not a config toggle).

| Field               | Type   | Required | Notes                                            |
| ------------------- | ------ | -------- | ------------------------------------------------ |
| `demand_id`         | string | yes      | matches the opener's demand_id                   |
| `demand_event_type` | enum   | yes      | same as opener                                   |
| `expected_persona`  | enum   | yes      | same as opener                                   |
| `actual_persona`    | enum   | yes      | satisfying persona (== expected; "code-reviewer" for codex_review) |
| `latency_ms`        | int    | yes      | satisfaction_ts - opened_ts (milliseconds)       |
| `match_modality`    | enum   | yes      | `native_spawn` (default) or `codex_review`       |

### `persona_demand_unmet` (PLAN-104 Wave A)

Emitted by `.claude/scripts/persona_demand_resolver.py` when the
match window expires with no matching dispatch and no waive. Exactly
ONE per `demand_id` (idempotent via terminal-event index lookup).

| Field                | Type   | Required | Notes                                          |
| -------------------- | ------ | -------- | ---------------------------------------------- |
| `demand_id`          | string | yes      | matches the opener's demand_id                 |
| `demand_event_type`  | enum   | yes      | same as opener                                 |
| `expected_persona`   | enum   | yes      | same as opener                                 |
| `target_ref_hash`    | string | yes      | re-emitted for forensic stitching              |
| `window_expired_at`  | string | yes      | ISO8601 UTC; `opened_ts + match_window_hours`  |

### `persona_demand_waived` (PLAN-104 Wave A — S134 R2 P1 #1 fold)

Emitted by ceremony / `/ceo-boot` flow when an operator commit
trailer or in-body annotation parses successfully. Closed enum for
`waive_reason`; free-text values rejected pre-emit (replaced with
`invalid-enum` sentinel for forensic trace without enum surface
pollution).

| Field               | Type   | Required | Notes                                                |
| ------------------- | ------ | -------- | ---------------------------------------------------- |
| `demand_id`         | string | yes      | matches the opener's demand_id                       |
| `demand_event_type` | enum   | yes      | same as opener                                       |
| `expected_persona`  | enum   | yes      | same as opener                                       |
| `waive_reason`      | enum   | yes      | `docs-only` / `generated-or-vendored` / `emergency-hotfix` / `explicit-skip` |

### `claim_emitted` (PLAN-090-FOLLOWUP Wave A — S138 R2 ACCEPT)

Emitted by `.claude/hooks/check_confidence_gate.py` once per CLAIM
token the gate evaluates (PostToolUse Agent hook). Per-claim audit
surface unblocking PLAN-100 Wave 0.5 empirical FPR baseline. Aggregate
`confidence_gate` event retained for backwards compatibility.

| Field           | Type   | Required | Notes                                                              |
| --------------- | ------ | -------- | ------------------------------------------------------------------ |
| `claim_id`      | string | yes      | `<claim_type>:<12-hex>`; defensive rehash via `_safe_claim_id_hash` |
| `claim_type`    | string | yes      | KNOWN_KINDS member preferred; truncated to 32 chars                |
| `severity`      | enum   | yes      | `info` / `warn` / `critical` (ADR-018); invalid → `info`           |
| `verifier_kind` | string | yes      | same as `claim_type` for KNOWN_KINDS                               |
| `payload_hash`  | string | yes      | bare 12-hex `sha256(NFKC(claim_args))[:12]`                        |
| `kind_supported`| bool   | yes      | extraction-FP signal (P0-1 fold); `False` → was_false_positive    |
| `line_num`      | int    | yes      | 1-based line in agent_text                                         |
| `agent_name`    | string | optional | truncated to 64 chars                                              |
| `source`        | string | optional | `post_tool_use` / `stdin` / `<file path>` truncated to 32 chars    |

LLM06 hold: raw claim body NEVER persisted. Kill-switch
`CEO_CONFIDENCE_GATE_PRODUCER_PAIR_DISABLED=1` suppresses emission
(reverts to PLAN-090 v1.24.0 audit-log shape; AC11 byte-identical
diff invariant).

### `confidence_gate_verdict` (PLAN-090-FOLLOWUP Wave A)

Emitted by `.claude/hooks/check_confidence_gate.py` once per claim
verdict, paired with the prior `claim_emitted` via `claim_id`.

| Field               | Type   | Required | Notes                                                                   |
| ------------------- | ------ | -------- | ----------------------------------------------------------------------- |
| `claim_id`          | string | yes      | matches the paired `claim_emitted` event                                |
| `verdict`           | enum   | yes      | `pass` / `fail` / `refuted`; invalid → `fail` (P1-1 fold)               |
| `was_false_positive`| bool   | yes      | PLAN-100 baseline FPR signal; v1.33.1 shipped semantic: `NOT kind_supported` |
| `kind_supported`    | bool   | yes      | paired field for backfill FP join                                       |
| `verifier_kind`     | string | optional | empty when verifier could not run                                       |
| `verifier_outcome`  | string | optional | PII-redacted + overlap-scrubbed + NFKC + ≤64 chars (security P1-B fold) |
| `agent_name`        | string | optional | truncated to 64 chars                                                   |
| `source`            | string | optional | `post_tool_use` (PostToolUse hook only)                                 |

Pair invariant: same loop iteration emits `claim_emitted` BEFORE its
paired `confidence_gate_verdict` in audit-log line order (backfill
reader does not require strict line-order pairing but the ordering
simplifies future PLAN-100 Wave B.3 drift-detector logic).
### `task_route_ground_truth_label` (PLAN-101 Wave B — S141 R2 ACCEPT)

Emitted by `.claude/plans/PLAN-101/synthesize-corpus.py` (synth path)
or future Stage-2 manual-review tooling. Append-only ground-truth
join key for AEK Calibration C3 FPR matrix; pairs with prior
`task_route_advised` event via `contract_id`. Per ADR-104-AMEND-1
§E, NOT a backfill of the original advised row (audit-log append-only
invariant per ADR-018).

| Field                       | Type   | Required | Notes                                                       |
| --------------------------- | ------ | -------- | ----------------------------------------------------------- |
| `contract_id`               | string | yes      | opaque join key — matches `task_route_advised.contract_id` (UUID4 in production, 16-hex sha256 in synth) |
| `ground_truth_class`        | enum   | yes      | `S` / `M` / `L` / `XL`                                       |
| `ground_truth_source`       | enum   | yes      | `heuristic_auto` / `manual_review`                           |
| `annotation_confidence_bps` | int    | yes      | 0..10000 basis-points; 7000 = 70% threshold for Stage 2      |

LLM06 hold: raw task descriptions NEVER persisted. Sec MF-3 deny-by-
default via `_TASK_ROUTE_GROUND_TRUTH_LABEL_ALLOWLIST`. Kill-switch
`CEO_AEK_CALIBRATION_ENABLED=0` suppresses synth-corpus emit (reverts
to pre-PLAN-101 v1.34.0 audit-log shape; AC16 byte-identical diff
invariant).

### PLAN-102 Wave A + Wave B — autonomous-loop opt-in capability (v2.21 — S142 2026-05-18)

Per ADR-133 (PROPOSED at v1.36.0): five new audit-action rows + one
schema extension on the existing `swarm_iteration` row. ALL FIVE
actions ship under the same kernel-override token
`CEO_KERNEL_OVERRIDE=PLAN-102-WAVE-A-AUDIT-EMIT-EXTENSION` per the
atomic kernel-extension pattern (S141 PLAN-101 precedent). Reversal
contract: byte-identical revert per ADR-133 §Reversal — remove the
5 entries from `_KNOWN_ACTIONS`, remove the 5 allowlists, remove the
5 dispatch-gate branches, restore contract gate baseline. Default-OFF
posture preserved (PLAN-017 anti-goal #1 unchanged; ADR-115 §3
instrumentation-without-policy-change exception).

#### `cost_envelope_capped`

Emitted by `.claude/hooks/check_cost_envelope.py` on HARD CAP breach
(PreToolUse gate; class-tier × window matrix per ADR-133 §A). Sec
MF-3 deny-by-default; raw project paths + user IDs + plan body +
command text NEVER persisted via this row.

| Field             | Type   | Required | Notes                                                 |
| ----------------- | ------ | -------- | ----------------------------------------------------- |
| `class_tier`      | enum   | yes      | `vibecoder` / `CTO` / `team`                          |
| `window_breached` | enum   | yes      | `daily` / `weekly` / `monthly` / `per_plan`           |
| `cap_cents`       | int    | yes      | cents; canonical_json no-float invariant              |
| `current_cents`   | int    | yes      | cents; cumulative usage at breach time                |

#### `swarm_runaway_suspected`

Emitted by `.claude/hooks/_lib/swarm_circuit_breaker.py` when iteration
count over a 24h rolling window exceeds the configured threshold per
ADR-133 §B. Advisory signal — the audit-log carries the trigger; the
SIGTERM escalation lives downstream in `kill_switch.py`.

| Field                  | Type | Required | Notes                                        |
| ---------------------- | ---- | -------- | -------------------------------------------- |
| `iteration_count_24h`  | int  | yes      | rolling iterations in last 24h               |
| `threshold`            | int  | yes      | per-class threshold (`vibecoder=10`, etc.)   |
| `triggering_class`     | enum | yes      | `vibecoder` / `CTO` / `team`                 |

#### `swarm_paused_owner_absent`

Emitted by the weekend-burn detector (ADR-133 §C) when a long swarm
loop runs without Owner Read activity. `loop_duration_hours` is
bucketed (>=1h granularity) to avoid wallclock side-channel leakage.

| Field                  | Type   | Required | Notes                                          |
| ---------------------- | ------ | -------- | ---------------------------------------------- |
| `loop_duration_hours`  | int    | yes      | bucketed (>=1h granularity)                    |
| `last_owner_read_iso`  | string | yes      | ISO-8601 UTC datetime                          |
| `swarm_pid`            | int    | yes      | Owner-readable process id; not secret          |

#### `execution_context_signed`

Emitted by `.claude/hooks/_lib/execution_context.py` whenever an HMAC
is computed against an autonomous-loop iteration's execution context
(ADR-133 §D tamper-evidence). NO command text, NO plan body.

> **RESERVED (zero producers).** Cross-process sign->validate is infeasible
> (per-process in-memory key). Wiring DEFERRED — PLAN-112-FOLLOWUP-execution-
> context-wire (S154, finding F-1.2). Schema kept for a future rebind.

| Field           | Type   | Required | Notes                                       |
| --------------- | ------ | -------- | ------------------------------------------- |
| `context_hash`  | string | yes      | sha256 hex of canonical context envelope    |
| `key_id`        | string | yes      | coordinator-process-owned key fingerprint   |
| `iteration`     | int    | yes      | per-loop monotonic counter                  |

#### `execution_context_validation_failed`

Emitted when execution_context HMAC verification fails (tamper signal).
Forbid raw context body via Sec MF-3 deny-by-default.

> **RESERVED (zero producers).** Cross-process sign->validate is infeasible
> (per-process in-memory key). Wiring DEFERRED — PLAN-112-FOLLOWUP-execution-
> context-wire (S154, finding F-1.2). Schema kept for a future rebind.

| Field             | Type   | Required | Notes                                                  |
| ----------------- | ------ | -------- | ------------------------------------------------------ |
| `context_hash`    | string | yes      | sha256 hex of the failing canonical context envelope   |
| `key_id`          | string | yes      | coordinator-process-owned key fingerprint              |
| `iteration`       | int    | yes      | per-loop monotonic counter                             |
| `failure_reason`  | enum   | yes      | `hmac_mismatch` / `key_unknown` / `schema_invalid`     |

#### `swarm_iteration` schema extension (v2.21 — opt-in field)

The existing `swarm_iteration` action (PLAN-017 Phase 4 / v2.11)
optionally carries `cumulative_usd_cents` (int, cents; canonical_json
no-float invariant). Opt-in field — call-sites may omit; consumers
treat absence as "untracked". No `_SWARM_ITERATION_ALLOWLIST` exists
today (action emitted via `emit_generic` direct); the new field is
documented here for the schema-as-spec contract.

LLM06 hold preserved across all six rows: NO raw task descriptions,
NO command text, NO plan bodies persisted. Kill-switch chain
(`CEO_SWARM=0`, `CEO_AUTONOMOUS_LOOPS_DISABLE=1`, per-class
`.claude/data/swarm/<class>-enabled.md.asc` removal, GPG sentinel
revocation, etc. — see ADR-133 §Reversal) suppresses emit paths and
reverts to pre-PLAN-102 v1.35.0 audit-log shape (byte-identical
diff invariant when all five layers are tripped).

### PLAN-102-FOLLOWUP — swarm_layer_3_4_blocked (v2.23 — 2026-05+ tentative)

#### `swarm_layer_3_4_blocked`

Emitted by `.claude/scripts/swarm/loop_runner.py:LoopRunner.step()` when
`is_class_enabled()` denies Layer 3 (GPG sentinel) OR Layer 4 (env flag).
Distinct from `swarm_paused_owner_absent` (weekend-burn detector) — this
is the per-iteration runtime gate enforcement event (ADR-133 §Part 1 §6,
Layers 3+4 of the 6-layer chain).

Side-channel collapse: 6 internal reason codes from
`swarm_enable_gate.is_class_enabled()` collapse to 4 emit reasons at the
boundary (security H1 fold from S144 R1 debate). Full detail remains in
`IterationResult.error` (local to caller, NOT persisted to audit log).

| Field         | Type   | Required | Notes                                                            |
| ------------- | ------ | -------- | ---------------------------------------------------------------- |
| `class_tier`  | enum   | yes      | `vibecoder` / `CTO` / `team` (matches PLAN-102 cost_envelope)    |
| `reason_code` | enum   | yes      | `layer_3_unavailable` / `layer_4_unset` / `kill_switch` / `unknown` |
| `loop_id`     | string | yes      | LoopRunner.loop_id; ≤64 chars; charset `[A-Za-z0-9_-]+` enforced at producer boundary |

LLM06 hold: NO command text, NO sentinel body, NO env var values, NO
file paths, NO error stack traces. Defense-in-depth: even with
CEO_AUTONOMOUS_LOOPS_DISABLE=1 the action remains registered (kernel
surface stable); only the emit path is suppressed by the kill-switch
chain.

## PLAN-106 Wave C — persona_coverage_synthesized

### v2.22 — PLAN-106 v1.37.0 (2026-05-19+ tentative)

Action `persona_coverage_synthesized` emitted by
`check_agent_spawn.py` (source=`dispatch`) and
`check_canonical_edit.py` (source=`canonical_edit`) at allow paths.
Fields (closed-enum allowlist at
`_lib/audit_emit._PERSONA_COVERAGE_SYNTHESIZED_ALLOWLIST`):

| Field | Type | Notes |
|---|---|---|
| `action` | "persona_coverage_synthesized (PLAN-106 Wave C)" | Constant |
| `archetype` | str | Closed-enum `_PERSONA_COVERAGE_ARCHETYPES` |
| `task_type` | str | Closed-enum `_PERSONA_COVERAGE_TASK_TYPES` |
| `cell_id` | str | sha256[:8] of `archetype:task_type` |
| `source` | str | Closed-enum `_PERSONA_COVERAGE_SOURCES` |

## PLAN-106 Wave H — output_scan per-pattern + suppression events

### v2.22 — PLAN-106 v1.37.0 (2026-05-19+ tentative)

Wave H of PLAN-106 absorbs PLAN-095-FOLLOWUP and refactors the
existing `output_scan_finding` action from aggregate-per-invocation
shape to per-pattern shape, and adds a paired
`output_scan_finding_suppressed` action for 24h-TTL dedup hits.

#### Action: `output_scan_finding` — UPDATED shape

Pre-v2.22 (legacy aggregate shape):
- `total_findings` (int): N findings in this invocation
- `family_counts` (dict[str, int]): family → count map
- `kill_switched` (dict[str, bool]): per-family kill-switch state

Post-v2.22 (per-pattern shape):
- `family` (str, closed-enum LLM01..LLM10 + LLM03_2025)
- `pattern_id` (str, closed-enum at `_lib/output_scan._PATTERN_IDS`)
- `repo_path_hash` (str, sha256 64-hex digest of `$CLAUDE_PROJECT_DIR`)
- `command_sha` (str, sha256 64-hex digest of tool-input snippet)
- `total_findings` = 1 (per-pattern); kept for backward-compat read
- `family_counts` = `{family: 1}` (per-pattern); kept for back-compat

**Backward-compat sidecar.** During the 24h deprecation window
(PLAN-095-FOLLOWUP §B.5 / AC15b), `check_output_secrets.py` ALSO
emits a single aggregate-shape `output_scan_finding` per invocation
WITH the legacy `total_findings=N` + `family_counts={...}` fields and
WITHOUT a `pattern_id` field. Audit-query consumers can distinguish
the two by presence of `pattern_id`.

The aggregate sidecar will be REMOVED in a follow-on plan past the
24h window.

#### Action: `output_scan_finding_suppressed` — NEW

Fires when `check_output_secrets.py` calls
`_lib.output_scan_dedup.check_and_record()` and the composite key
`(repo_path_hash, command_sha, pattern_id)` has already fired within
the rolling 24h TTL window.

Fields (closed-enum allowlist at
`_lib/audit_emit._OUTPUT_SCAN_FINDING_SUPPRESSED_ALLOWLIST`):

| Field | Type | Notes |
|---|---|---|
| `action` | "output_scan_finding_suppressed" | Constant |
| `ts` | int (ms epoch) | Standard base field |
| `session_id` | str | Standard base field |
| `project` | str | Standard base field; truncated if oversized |
| `repo_path_hash` | str (64-hex) | sha256 of `$CLAUDE_PROJECT_DIR` |
| `command_sha` | str (64-hex) | sha256 of tool-input snippet |
| `pattern_id` | str | Closed-enum at `_lib/output_scan._PATTERN_IDS` |
| `family` | str | Closed-enum LLM01..LLM10 + 2025 variants |
| `ttl_hours_remaining` | int | Integer hours until first_seen_ts + 24h |

**Sec MF-3 invariant.** NO raw matched-content / regex source /
context preview / tool-input body persists on this event. The
composite-key fields are opaque hashes; `pattern_id` + `family` are
both producer-validated closed enums.

#### Meta-hunt integration

`docs/hunting/llm03-supply-chain.md` §4 (post-Wave H.3.b patch)
uses the SUPPRESSION RATE rather than the finding rate as a
tuning signal:

```
suppression_rate := count(output_scan_finding_suppressed) /
                    (count(output_scan_finding[pattern_id present]) +
                     count(output_scan_finding_suppressed))
```

Thresholds (advisory, NOT blocking):
- `suppression_rate < 5%` over a 7d window → patterns are too narrow
  (consider adding a new pattern; few hits in production).
- `suppression_rate > 30%` over a 7d window → patterns are too noisy
  (consider tightening the regex; many repeat fires within 24h).
- `5% ≤ suppression_rate ≤ 30%` → healthy detection volume.

#### Migration notes for consumers

Audit-query parsers SHOULD switch from "count of
`output_scan_finding` events" to "count of
`output_scan_finding` events WHERE `pattern_id` field is present".
The aggregate sidecar (`pattern_id` absent) is transitional.
