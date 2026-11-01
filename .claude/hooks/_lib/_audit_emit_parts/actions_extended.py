"""Audit action registrations; combined by schemas_actions."""
from __future__ import annotations

_ACTIONS = {
    "goap_search_aborted",
    "goap_search_summary",
    "goap_cycle_detected",
    "goap_depth_exceeded",
    "goap_replan_triggered",
    "goap_replan_exhausted",
    "goap_disabled_by_env",
    "goap_recommendation_accepted",
    # PLAN-105 Wave A.1 + A.2 — GOAP recommendation outcome telemetry.
    "goap_recommendation_rendered",
    "goap_recommendation_overridden",
    # PLAN-099 (ADR-129 / ADR-135) — federation cross-machine MVP audit surface.
    "federation_connection_accepted",
    "federation_connection_rejected",
    "federation_connection_replay_suspected",
    "federation_cert_expiry_warned",
    "federation_cert_rotated",
    "federation_cert_revoked",
    "federation_write_attempt_blocked",
    "federation_lan_bind_denied",
    "federation_autonomous_call_blocked",
    "federation_enable_sentinel_invalid",
    # PLAN-099-FOLLOWUP Wave F — federation write-mode audit surface
    # (ADR-129-AMEND-1 / ADR-135-AMEND-1 / attack-rebinding.md §2).
    # 20 actions touched; +19 net-new (federation_cert_rotated already
    # in set from PLAN-099 MVP S134, field-shape-superseded in-place).
    # Registered via kernel-override
    # PLAN-099-FOLLOWUP-WAVE-F-AUDIT-EMIT-EXTENSION at v1.39.1.
    "federation_audit_event_pushed",
    "federation_audit_event_pushed_batch",
    "federation_audit_log_backpressure",
    "federation_cert_validity_window_too_large",
    "federation_event_action_blocked",
    "federation_hmac_secret_rotated",
    "federation_key_floor_rejected",
    "federation_key_floor_stale",
    "federation_message_storm_detected",
    "federation_peer_invalid_no_fingerprint",
    "federation_peer_registered",
    "federation_peer_registered_collision",
    "federation_peer_revoked_remote",
    "federation_pin_legacy_used",
    "federation_scope_denied",
    "federation_spki_fingerprint_mismatch",
    "federation_tamper_detected",
    "federation_write_disabled_sentinel_invalid",
    "federation_write_endpoint_denied",
    "federation_peer_list_reloaded",
    # PLAN-104 Wave A — persona-demand ledger audit surface (S134 R2 ACCEPT).
    "persona_demand_opened",
    "persona_demand_matched",
    "persona_demand_unmet",
    "persona_demand_waived",
    # PLAN-090-FOLLOWUP Wave A — claim producer pair (S138 R2 ACCEPT).
    "claim_emitted",
    "confidence_gate_verdict",
    # PLAN-100 Wave B — per-class block-mode (S139 R2 ACCEPT;
    # ADR-019-AMEND-1 PROPOSED). confidence_gate_blocked emitted when
    # decision.action == "block"; confidence_gate_fp_drift_detected
    # emitted by check-confidence-gate-drift.py on 7d rolling FPR > 2%.
    "confidence_gate_blocked",
    "confidence_gate_fp_drift_detected",
    # PLAN-106 Wave C — persona-coverage 4×4 cell emit from production
    # hooks (check_agent_spawn allow path + check_canonical_edit allow
    # path). Source field carries `dispatch` | `canonical_edit` for
    # downstream attribution. NO public typed wrapper — emit_generic +
    # Sec MF-3 scrub keeps `_EXPECTED_PUBLIC_SYMBOLS` stable per
    # PLAN-102 Wave A precedent (S142 R2 iter-1 P1 #3 fold).
    "persona_coverage_synthesized",
    # PLAN-110 Wave D — protocol_semver_cascade advisory hook
    "protocol_edit_missing_amend_paired",
    # PLAN-112-FOLLOWUP-hmac-tamper-fix Wave B.3 — chain_reset_marker is
    # the synthetic genesis entry written as line 1 of every rotation-
    # created fresh audit-log.jsonl. Per ADR-055-AMEND-2 (drafted in
    # this plan): verifier reads `audit-log.rotation-manifest.json`
    # sidecar; if present, line 1 of fresh log MUST be a
    # chain_reset_marker entry — non-marker line 1 = STATUS_TAMPER.
    # Registered via kernel-override
    # PLAN-112-FOLLOWUP-WAVE-B3-AUDIT-EMIT-EXTENSION at v1.39.4.
    "chain_reset_marker",
    # PLAN-118 AC-B5 — closed-enum producer-pollution forensic breadcrumb.
    # Emitted by chokepoint 1 (audit_emit._emit_chain_reset_marker_under_lock)
    # + chokepoint 4 (spool_writer._phase4_build_batch) when the canonical-
    # resolution check (audit_hmac._ensure_canonical_lib_modules) detects
    # a stale `_lib` copy on sys.path. Allowlist payload: chokepoint
    # (enum: chain_reset_marker | spool_drain) + reason_code (enum:
    # audit_emit_path_pollution | canonical_json_path_pollution |
    # audit_hmac_path_pollution) + path_sha256_prefix (8 hex chars) +
    # expected_canonical_prefix (8 hex chars). NO `__file__` raw echo
    # per [[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]].
    "audit_producer_path_pollution_detected",
    # PLAN-125 WS-1 (kooky-harvest) — per-tool-call lifecycle telemetry.
    # Deny-by-default: routes through the dedicated _scrub_ branch +
    # _TOOL_CALL_LIFECYCLE_RECORDED_ALLOWLIST below, NEVER
    # _EMIT_GENERIC_PASSTHROUGH (Sec MF-SEC-2). Carries ONLY 4 closed fields:
    # tool_name_enum (mcp__* → mcp_other, Sec MF-SEC-1), duration_bucket
    # (coarse enum, never raw duration_ms, Sec MF-SEC-3), success, orphan.
    "tool_call_lifecycle_recorded",
    # PLAN-124 WS-1 (ECC value-harvest) — git hook-bypass guard breadcrumb.
    # Deny-by-default: routes through the dedicated _scrub_ branch +
    # _GIT_HOOK_BYPASS_BLOCKED_ALLOWLIST below, NEVER _EMIT_GENERIC_PASSTHROUGH
    # ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    # The ONLY caller-supplied field is `flag_class` (closed enum, MF-G); the
    # matched command bytes are NEVER persisted (a malicious flag value such as
    # `-c http.extraHeader="Bearer <secret>"` could otherwise leak).
    "git_hook_bypass_blocked",
    # PLAN-133 A1 — linker/loader/runtime env-hijack denylist breadcrumb.
    # Deny-by-default: routes through the dedicated _scrub_ branch +
    # _ENV_VAR_HIJACK_BLOCKED_ALLOWLIST below, NEVER _EMIT_GENERIC_PASSTHROUGH
    # ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    # The ONLY caller-supplied field is `hijack_class` (closed enum); the matched
    # variable NAME and the assigned VALUE are NEVER persisted (the value can be
    # a path/preload payload or a smuggled secret).
    "env_var_hijack_blocked",
    # PLAN-133 A3 — egress-destination taxonomy breadcrumb (advisory). Routes
    # through the dedicated _scrub_ branch + _EGRESS_DESTINATION_DETECTED_ALLOWLIST
    # below, NEVER _EMIT_GENERIC_PASSTHROUGH
    # ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]). The ONLY
    # caller-supplied fields are `egress_class` (closed enum) + `destination`
    # (BARE HOST only — never the full URL/path/query/credential).
    "egress_destination_detected",
    # PLAN-133 E1 — adversary local-rules deny/ask gate breadcrumb. Deny-by-default:
    # routes through the dedicated _scrub_ branch + _ADVERSARY_REVIEW_FLAGGED_ALLOWLIST
    # below, NEVER _EMIT_GENERIC_PASSTHROUGH
    # ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]). The ONLY
    # caller-supplied fields are `decision` + `rule_class` (both closed enums) and
    # `rule_id` (author-controlled config token). The matched COMMAND bytes and any
    # env value are NEVER persisted.
    "adversary_review_flagged",
    # PLAN-133 G1 — MOIM persistent-instructions BLOCKING validator breadcrumb.
    # Deny-by-default: routes through the dedicated _scrub_ branch +
    # _PERSISTENT_INSTRUCTIONS_BLOCKED_ALLOWLIST below, NEVER
    # _EMIT_GENERIC_PASSTHROUGH
    # ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]). The
    # ONLY caller-supplied fields are `reason` (closed enum) + integer counts
    # `family_hits`/`bytes_scanned`. The instruction-file body, the matched
    # line, and any path/env value are NEVER persisted.
    "persistent_instructions_blocked",
    # PLAN-133 G3 — hierarchical nested .claude/hints.md provenance breadcrumb.
    # Deny-by-default: routes through the dedicated _scrub_ branch +
    # _HINT_PROVENANCE_RECORDED_ALLOWLIST below, NEVER _EMIT_GENERIC_PASSTHROUGH
    # ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]). The
    # ONLY caller-supplied fields are `reason` (closed enum) + integer
    # `rel_dir_depth` / `family_hits` / `bytes_scanned`. The hint-file body, the
    # matched line, and the absolute/relative PATH text are NEVER persisted —
    # only the integer directory DEPTH below the repo root.
    "hint_provenance_recorded",
    # PLAN-135 W1 S3 — /ceo-boot Tier-S settings/env tamper tripwire
    # breadcrumb (one emit per detected tamper class). Deny-by-default:
    # routes through the dedicated _scrub_ branch +
    # _SETTINGS_TAMPER_DETECTED_ALLOWLIST below, NEVER
    # _EMIT_GENERIC_PASSTHROUGH
    # ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    # The ONLY caller-supplied fields are `tamper_class` + `layer` (both
    # closed enums mirroring _lib/effective_config; coerced to "other" on
    # a miss) and integer `finding_count` (clamped 0..99). The tamper
    # finding DETAIL (endpoint URL / model id / helper path / flag value)
    # and any env VALUE are NEVER persisted.
    "settings_tamper_detected",
    # PLAN-135 W2 H2 — ConfigChange guard: a settings-surface config change
    # was observed and NO forbidden-key finding was scoped to it (allow +
    # audit path of check_config_change.py). Deny-by-default: routes through
    # the dedicated _scrub_ branch + _CONFIG_CHANGE_OBSERVED_ALLOWLIST
    # below, NEVER _EMIT_GENERIC_PASSTHROUGH
    # ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    # The ONLY caller-supplied field is `layer` (closed enum
    # user/project/local/managed/other; coerced to "other" on a miss). The
    # changed file's CONTENT, its path text and any key/value are NEVER
    # persisted.
    "config_change_observed",
    # PLAN-135 W2 H2 — ConfigChange guard: a forbidden-key finding
    # (_lib/effective_config.FORBIDDEN_KEYS, the S3/H2 single source) was
    # scoped to a settings-surface config change → advisory-block (one emit
    # per tamper class, settings_tamper_detected producer precedent).
    # Deny-by-default: dedicated _scrub_ branch +
    # _CONFIG_CHANGE_FORBIDDEN_KEY_ALLOWLIST below, NEVER
    # _EMIT_GENERIC_PASSTHROUGH. The ONLY caller-supplied fields are
    # `tamper_class` (closed enum mirroring _lib/effective_config
    # TAMPER_CLASSES; coerced to "other") + `layer` (closed enum
    # user/project/local/managed/other; coerced to "other") and integer
    # `finding_count` (clamped 0..99). The forbidden key's VALUE (endpoint
    # URL / model id / helper path / flag value) and the finding DETAIL are
    # NEVER persisted.
    "config_change_forbidden_key",
    # PLAN-135 W2 H1 (ADR-153 compaction-continuity) — PreCompact governance
    # snapshot breadcrumb (one emit per compaction event,
    # check_precompact_continuity.py). Deny-by-default: routes through the
    # dedicated _scrub_ branch + _COMPACTION_CONTINUITY_SNAPSHOT_ALLOWLIST
    # below, NEVER _EMIT_GENERIC_PASSTHROUGH
    # ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    # The ONLY caller-supplied fields are `trigger` + `snapshot_outcome`
    # (closed enums, coerced to "other"), `plan_id` (strict PLAN-NNN shape
    # check, coerced to "unknown") and integer `chain_length` (clamped
    # 0..99999999). The snapshot BODY (plan path, checkbox position,
    # ceremony flags, last-hmac prefix) lives in the plan-scoped scratchpad
    # ONLY and is NEVER persisted on the audit wire.
    "compaction_continuity_snapshot",
    # PLAN-135 W2 H1 (ADR-153 compaction-continuity) — PostCompact
    # governance-pointer reinjection breadcrumb
    # (check_postcompact_reinject.py). Deny-by-default: dedicated _scrub_
    # branch + _COMPACTION_CONTEXT_REINJECTED_ALLOWLIST below, NEVER
    # _EMIT_GENERIC_PASSTHROUGH. The ONLY caller-supplied fields are
    # `plan_id` (strict PLAN-NNN shape check, coerced to "unknown"),
    # boolean `snapshot_found` (any non-bool coerced to False) and integers
    # `snapshot_age_s` (clamped 0..9999999) + `pointer_count` (clamped
    # 0..9). The reinjected additionalContext TEXT is NEVER persisted
    # (pointers-only by design; the audit wire carries counters, not
    # context).
    "compaction_context_reinjected",
    # PLAN-135 W2 H5 (ADR-154 single-rewriter) — check_bash_safety rewrote a
    # `git push --force`/`-f` Bash input to `--force-with-lease` via the
    # PreToolUse `updatedInput` channel (surfaced as an `ask`, never a silent
    # allow). Deny-by-default: dedicated _scrub_ branch +
    # _BASH_INPUT_REWRITTEN_ALLOWLIST below, NEVER _EMIT_GENERIC_PASSTHROUGH
    # ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]). The
    # ONLY caller-supplied fields are `rewrite_class` (closed enum, coerced to
    # "other") + the before/after sha256 hash PAIR (`before_sha256` /
    # `after_sha256`, each validated to 64-hex else coerced to ""). The
    # command BYTES (before OR after) are NEVER persisted — a force-push line
    # can carry a remote URL with an inline token; the hash pair lets an
    # auditor prove audited-cmd == executed-cmd without seeing either command
    # (ADR-154 §2 before/after hash invariant).
    "bash_input_rewritten",
    # PLAN-135 W2 H3 — per-agent lifecycle bracket emitted ONCE at SubagentStop
    # (.claude/hooks/check_fluency_nudge.py H3 extension) after consuming the
    # SubagentStart sidecar (check_subagent_start.py) + the harness-supplied
    # `agent_transcript_path`: the S227 `modelUsage` forensic reconstruction
    # becomes a live hook emit, feeding the persona-ledger (PLAN-104) + quota
    # economics. Deny-by-default: dedicated _scrub_ branch +
    # _SUBAGENT_LIFECYCLE_OBSERVED_ALLOWLIST below, NEVER _EMIT_GENERIC_PASSTHROUGH
    # ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]). EVERY
    # caller-supplied field is a CLOSED enum or a coarse BUCKET — `agent_archetype`
    # (persona-ledger archetype enum, coerced to "other"/"unknown"), `wall_bucket`
    # + `wall_source` + `token_bucket` + `claim_bucket` (closed enums). RAW
    # wall-time seconds, RAW token counts, the transcript path/body, the
    # confidence-marker snippets and the raw agent_id are NEVER persisted —
    # only the closed-enum brackets travel (the bracket is the audit signal; the
    # raw counts stay forensic-private, mirroring the S227 reconstruction).
    "subagent_lifecycle_observed",
    # ---- PLAN-135 ARC CONSOLIDATION — W5 ops actions folded in one place ----
    # The three W5 actions are TRUSTED-producer emit_generic actions (the
    # emitter is a standalone Owner-run / Owner-configured script OR the
    # adapter library itself, not a deny-by-default hook). The producers
    # pre-redact at the emit site (key-hygiene.py `_redact()`; statusline-ceo.py
    # passes only numbers/enum-ids; claude.py drops `stop_details.explanation`
    # and forwards ONLY the closed `stop_details.category` vocabulary) — BUT per
    # Codex R5 P1-2 (PLAN-135-FOLLOWUP) producer-side pre-redaction is NOT the
    # only line: each action is ALSO given a dedicated deny-by-default scrub
    # branch in emit_generic (NEVER _EMIT_GENERIC_PASSTHROUGH) so the Sec MF-3
    # field-allowlist + enum-value-coercion boundary holds against a direct /
    # future mis-caller that bypasses the trusted producer — the established
    # invisible_unicode_blocked / tool_call_lifecycle_recorded precedent. They
    # are "branched" members of the ghost-action-guard tri-state invariant.
    # PLAN-135 W5 o9 — Anthropic Admin API key-lifecycle breadcrumb
    # (.claude/scripts/key-hygiene.py `_audit_emit` -> emit_generic). Closed-enum
    # `operation`/`reason` + IDs/counts only; key material never reaches the emit
    # (producer `_redact()` on free text). Secondary tamper-evident breadcrumb;
    # the load-bearing artifact is the append-only docs/rotation-log.md row.
    "admin_key_lifecycle_event",
    # PLAN-135 W5 o4 — statusLine sidecar-write breadcrumb
    # (.claude/scripts/statusline-ceo.py `maybe_emit` -> emit_generic). Debounced
    # (material-digest + CEO_STATUSLINE_EMIT_INTERVAL_S); carries only the sidecar
    # abs path, plan-id, percentages, bucket count, session_id + a 12-char digest
    # prefix — never the raw statusLine stdin free text. The load-bearing artifact
    # is the atomic sidecar JSON (always written); this event arms post-ceremony.
    "statusline_sidecar_write",
    # PLAN-135 W5 o7 — model-refusal observability breadcrumb
    # (.claude/hooks/_lib/adapters/live/claude.py `_on_response` -> emit_generic on
    # stop_reason == "refusal"). Forwards ONLY the closed provider
    # `stop_details.category` vocabulary (<=64 chars) + provider/model slugs +
    # status/duration ints; `stop_details.explanation` (model free text) is dropped
    # at the emit site and can NEVER reach the audit log.
    "model_refusal_observed",
    # ------------------------------------------------------------------
    # PLAN-154 (Gated Learning Loop / ADR-160) — 11 new actions, all
    # metadata-only (A2: closed enums / booleans / bounded IDs / hashes;
    # NO free-text field). Every one routes through a dedicated
    # deny-by-default scrub branch + allowlist below — NEVER
    # _EMIT_GENERIC_PASSTHROUGH (Sec MF-3). Count: 303 -> 314.
    # ------------------------------------------------------------------
    # Candidate lifecycle (lessons.py add_candidate — birth event carrying
    # the A6 content pin sha256(trigger+"\n"+advisory_text); its chain ts
    # is the created_at authority for TTL + approval).
    "lesson_candidate_written",
    # /lesson-review approval (lessons.py approve_candidate) — THE A6
    # hash-pinned approval event; get_boot_lessons_verified recomputes
    # and verifies against it before any render.
    "lesson_approved",
    # Post-birth terminal QUARANTINED transition (INPUT failures at the
    # fail-CLOSED promotion boundary, A4).
    "lesson_quarantined",
    # Terminal TTL expiry (A9 — never any default disposition toward
    # activation).
    "lesson_expired",
    # A6 verify-before-render drop breadcrumb (hash mismatch / missing
    # approval event / vocab tamper) — feeds the item-6 flip criterion
    # "zero unresolved integrity flags".
    "lesson_integrity_flag",
    # /ceo-boot render-gate drop breadcrumb (item 4 / A5 — closed reason
    # enum + bounded lesson_id; count-only human counterpart in digest).
    "lesson_boot_render_dropped",
    # A12 disabled-this-session breadcrumb, shared by all four rails
    # (observe / distill / boot_render / fact_gate); wired to the ADR-158
    # fail-open-rail liveness surface. Emitted ONLY on explicit disable.
    "learning_rail_disabled",
    # A8 governance event — every observed ADVISORY<->ENFORCE flip of the
    # item-6 fact-forcing deny-once gate (settings-backed; lazy detection
    # on the already-matched destructive path in check_bash_safety).
    "fact_gate_activation_changed",
    # A10 dampening condensation — <=1 per advisory ID per session
    # (_lib/advisory_dampen.py; bounded ID + ordinal + closed channel).
    "advisory_dampened",
    # Item-2 offline distiller run rollup — tokens_in/tokens_out make the
    # distiller its own /agent-budget line item; closed outcome enum.
    "distiller_run_completed",
    # Item-7 $0 deterministic clustering pass — counts-only breadcrumb.
    "lesson_evolve_run",
    # PLAN-155 Wave 4 (Codex harness audit chain / SENT-CX-B, ADR-161) — two
    # NEW metadata-only actions so the HMAC chain appends under OpenAI Codex.
    # Both are distinct from agent_spawn (the claude-only spawn record) AND
    # from tool_call_lifecycle_recorded, so codex-completeness analysis can
    # tell the per-tool rail from the turn-level backstop apart in the same
    # log slice (the completeness query IS the Wave-4 replay test).
    # Deny-by-default: each routes through a dedicated `_scrub_` branch in
    # emit_generic + its own closed-enum allowlist below, NEVER
    # _EMIT_GENERIC_PASSTHROUGH. NO command bytes / patch body / paths /
    # prompt / last_assistant_message / tool_response text is EVER persisted
    # — only closed-enum + bool scalars (Sec MF-3). Emitted by audit_log.py
    # under CEO_HOOK_ADAPTER=codex (via the codex host adapter). The HMAC
    # chain shape + verify_chain() are UNTOUCHED; only the enum grows.
    #
    # (A) per-tool-call append for the codex PostToolUse `*` matcher — the
    # completeness-bounded record that "a tool call happened", tool identity
    # coerced to a closed enum (raw mcp__<server>__<tool> -> mcp_other).
    "codex_tool_recorded",
    # (B) turn-ended backstop (Stop / SubagentStop / notify / headless-wrapper
    # bracket) — a DISTINCT action so a turn-level append is never conflated
    # with a per-tool append when partial shell interception drops per-tool
    # events (the named completeness residual).
    "codex_turn_ended",
    # PLAN-156 Wave 4 (SENT-GK-B) — grok host per-tool + turn-ended pair.
    # Same completeness contract as the codex pair above: a `grok`
    # discriminator so analysis can pivot the grok rail without inferring
    # from the action name. Grok fires PostToolUse per tool call and Stop
    # per turn (both passive — a deny there is cosmetic, but the AUDIT
    # append still lands); SessionEnd is not reliable on grok, so
    # turn-ended accounting hangs off Stop (completeness caveat documented).
    "grok_tool_recorded",
    "grok_turn_ended",
    # PLAN-156 Wave 6 (SENT-GK-F) — cross-vendor council lane invocation.
    # One append per AVAILABLE external lane per council run (who asked what,
    # when) so cross-vendor egress is itself auditable. Registered HERE, not
    # in Wave 4, so a slipped Wave 6 never publishes a contract action the
    # framework cannot yet emit (pair-rail R11). Completeness-bounded.
    "council_lane_invoked",
    # PLAN-161 W2 C5 (CF-9) — pair-rail liveness telemetry pair. Registered
    # via the PLAN-161 W2 ceremony (CEO_KERNEL_OVERRIDE=
    # PLAN-161-C5-LIVENESS-ACTIONS); _KNOWN_ACTIONS 319 -> 321. Both are
    # deny-by-default: dedicated _scrub_ branches +
    # _CODEX_REVIEW_VERDICT_ALLOWLIST / _PAIR_RAIL_REVIEW_EXPECTED_ALLOWLIST
    # below, NEVER _EMIT_GENERIC_PASSTHROUGH
    # ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    #
    # (A) Stop-hook cross-review OUTCOME, emitted by
    # codex_review_user_code.py (the Stop hook wired in settings.json) once
    # per distinct (diff_sha256, outcome) pair: closed-enum `outcome`
    # {clean, findings, skipped_failopen, detected_only} (unrecognized
    # COERCED to skipped_failopen — never a healthy-class value) +
    # `diff_sha256` (64-lowercase-hex shape-validated, else ""). DENIED on
    # the wire: the verdict TEXT, the diff content, file paths (a Codex
    # finding can quote secrets from the reviewed diff). Deliberately NOT
    # `pair_rail_codex_unavailable` — that would pollute the dispatcher's
    # Codex-outage predicate (disable_predicate_eval.py).
    "codex_review_verdict",
    # (B) canonical-edit review ENTERED, emitted by check_pair_rail.py
    # _decide() only after the kill-switch / non-write-tool / not-L3+ /
    # sentinel-bypass arms have all returned: the durable session-correlated
    # DENOMINATOR for the /ceo-boot `pair_rail` activity-conditioned
    # liveness row (the S254 class — expected-without-outcome must escalate,
    # and a healthy outcome from session B must never mask session A). The
    # ONLY caller fields are `session_id` + closed-enum `tool_name` + the
    # bounded 16-hex `file_path_hash_prefix` (r4 F2 legacy bucket key —
    # same token as `pair_rail_case`) + the exact-16-hex-or-"" `review_id`
    # (r5 F2 — per-invocation correlation id minted at review entry and
    # identical on this emit and its own `pair_rail_case`, so the
    # /ceo-boot deficit pairs invocation-EXACT: no completed case — even
    # for the SAME (session, file) — can ever offset a different dead
    # review).
    "pair_rail_review_expected",
    # PLAN-163 T3.1/T3.2 (CC 2.1.220 substrate uplift, ADR-183) — 2 NEW
    # metadata-only actions for the two NEW harness lifecycle events
    # (DirectoryAdded + Notification). Registered via the PLAN-163 pack
    # ceremony; _KNOWN_ACTIONS 321 -> 323. Both are deny-by-default:
    # dedicated _scrub_ branches + _DIRECTORY_ADDED_RECORDED_ALLOWLIST /
    # _NOTIFICATION_LIFECYCLE_ALLOWLIST below, NEVER
    # _EMIT_GENERIC_PASSTHROUGH
    # ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    #
    # (A) DirectoryAdded workspace-root append, emitted by
    # check_directory_added.py (the DirectoryAdded observer — the event is
    # NOTIFICATION-ONLY on CC 2.1.220: permission/sandbox already include
    # the dir BEFORE dispatch, so this row is the POST-FACTO forensic
    # record that the session's write surface grew). Closed-enum `source`
    # {slash_command, register_repo_root, session_start_snapshot, other}
    # (the wire carries the first two; session_start_snapshot is reserved
    # for the documented --add-dir-at-LAUNCH blind-spot mitigation — the
    # launch flag never fires the event, so a SessionStart roots snapshot
    # is the only producer that can cover it) + `directory_hash_prefix`
    # (exact 12-lowercase-hex sha256 prefix of the absolute path, or "";
    # the RAW directory path is NEVER persisted — LLM06 side-channel
    # guard, same 12-hex token class as message_sha256_prefix below and
    # the exact length check_directory_added.py computes).
    "directory_added_recorded",
    # (B) Notification lifecycle telemetry, emitted by
    # check_notification.py (pure observer on the Notification event).
    # Closed-enum `notification_type` {agent_needs_input, agent_completed,
    # permission_request, other} — the harness enum is OPEN, so any
    # unrecognized wire value COERCES to `other` (never echoed) — +
    # `has_title` (bool) + `message_sha256_prefix` (exact 12-lowercase-hex
    # sha256 prefix of the message body, or ""; the message/title TEXT is
    # NEVER persisted — no-value-echo, a notification message can quote
    # tool output or secrets).
    "notification_lifecycle",
    # PLAN-165 P2 (night-mode / D2) — Owner-invoked autonomy posture toggle
    # forensic record, emitted by .claude/scripts/night-mode.py (the SINGLE
    # writer of the per-machine overlay .claude/settings.local.json — the
    # PLAN-165 P1 deny rule closes the tool Edit/Write path) once per on|off
    # invocation. Registered via the PLAN-165 prerequisite ceremony;
    # _KNOWN_ACTIONS 323 -> 324. Deny-by-default: dedicated _scrub_ branch +
    # _NIGHT_MODE_TOGGLED_ALLOWLIST below, NEVER _EMIT_GENERIC_PASSTHROUGH
    # ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    # Closed-enum `mode` / `previous_mode` {acceptEdits, manual, absent,
    # other} + closed-enum `result` {applied, noop, refused, failed, other}
    # + `hostname_hash` (exact 12-lowercase-hex sha256 prefix of the machine
    # hostname, or ""). DENIED on the wire: the overlay PATH, settings file
    # CONTENT, marker content, the RAW hostname — settings JSON and paths
    # can carry usernames, allowlists, and project identity (LLM06
    # side-channel guard).
    "night_mode_toggled",
    # PLAN-179 W0 US2 (amendment 8.1 — the ADR-153 continuity successor
    # rail) — EDGE-TRIGGERED context-pressure breadcrumb: the session
    # crossed INTO a new context-usage percent bucket. A TRANSITION, never
    # a per-turn sample — the hysteresis gate is
    # should_emit_context_pressure() below, and without it the HMAC chain
    # would take one row per prompt while the session sits in one rung.
    # Registered via the staged PLAN-179 W0/W1 bundle; _KNOWN_ACTIONS
    # 324 -> 325. Deny-by-default: dedicated _scrub_ branch +
    # _CONTEXT_PRESSURE_OBSERVED_ALLOWLIST below, NEVER
    # _EMIT_GENERIC_PASSTHROUGH
    # ([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).
    # The ONLY caller-supplied fields are `used_bucket` (closed set of
    # INTEGER PERCENT buckets {40,60,80,90,95} — the name carries the unit;
    # the check is TYPE-strict because canonical_json refuses floats and a
    # float here would discard the WHOLE event, S181/ADR-055-AMEND-2),
    # `event_source` (closed enum, coerced to "other") and `plan_id`
    # (strict PLAN-NNN shape check, coerced to "unknown"). DENIED on the
    # wire: the raw token/byte counts, the transcript text, the plan path
    # text, the prompt body.
    "context_pressure_observed",
    # PLAN-174 W1 (registered by the SENT-S318 pack; _KNOWN_ACTIONS
    # 325 -> 326) — ceremony-lint ADR-186 escape-hatch breadcrumb:
    # CEO_CEREMONY_LINT_UNLOCK=<sha256> + _REASON consumed by
    # check-ceremony-script.py. Metadata-only wire (`file_sha256` 16-hex
    # prefix + `reason_len` int); the reason TEXT never reaches the log.
    # Emitter parked in 908707e until this registration existed.
    "ceremony_lint_unlock_used",
    # PLAN-182 W1 (ADR-079 S318 amendment §2; _KNOWN_ACTIONS 326 -> 327)
    # — the ONE sanctioned salt-rotation register: minting a per-project
    # .salt is OBSERVABLE in the chain, never silent. Metadata-only wire
    # (`reason` closed enum + `salt_scope` fixed + `slug_sha256` 16-hex
    # prefix); raw slug and salt-file path are excluded from the payload.
    # The base `project` field still carries the absolute repository path.
    # Emitted lazily
    # by _lib/injection_salt.py at mint time (marker sidecar is the
    # forensic ground truth when the emit path is unavailable).
    "salt_rotation_registered",
    # PLAN-179 W2/W4 (ADR-195 — work-boundary persistence; registered by the
    # staged-w24 ceremony pack, Owner decision 2026-08-25 "3 actions";
    # _KNOWN_ACTIONS 327 -> 330). All THREE are deny-by-default: a dedicated
    # `action ==` scrub branch in emit_generic + the allowlists
    # _LEDGER_CHECKPOINT_RECORDED_ALLOWLIST /
    # _LEDGER_CHECKPOINT_SKIPPED_ALLOWLIST / _LEDGER_ENTRY_REJECTED_ALLOWLIST
    # below, NEVER _EMIT_GENERIC_PASSTHROUGH.
    #
    # (1) The advisory work-boundary observation: a `git commit` landing
    # plan-scoped work was inspected for its LEDGER.md checkpoint. Producer =
    # check_ledger_checkpoint.py (PreToolUse/Bash), which never denies. Wire =
    # closed enums (`outcome`, `scope_source`, `state_kind`), the strict
    # PLAN-NNN id, and TYPE-strict INT counters clamped 0..99 (a float is
    # refused by canonical_json and would discard the WHOLE event —
    # S181/ADR-055-AMEND-2). DENIED on the wire: the commit MESSAGE, the
    # committed PATHS, the ledger CONTENT, the repo root, any AC text.
    "ledger_checkpoint_recorded",
    # (2) The same rail's negative case, kept as its OWN action so "the rail
    # did not fire" is countable instead of inferred from absence: the
    # measure-first window needs a denominator, and "skipped because the
    # commit was out of scope" and "never observed at all" are different
    # facts.
    "ledger_checkpoint_skipped",
    # (3) The W4 ledger write-gate discard: an externally-sourced entry was
    # refused fail-CLOSED. Producer = _lib/ledger_provenance.py. This action
    # exists precisely so the discard is NOT filed as
    # `prompt_injection_detected`: routing `scanner_unavailable` / `oversize`
    # / `malformed_input` into a DETECTION action would poison the very FPR
    # series the advisory window has to measure. Wire = closed enums + INT
    # counters. DENIED on the wire: the rejected entry BODY (not even a
    # preview), the entry id, and any path.
    "ledger_entry_rejected",
    # PLAN-179 W2 US8 (wave-179-close ceremony; SPEC v2.60) — SessionEnd
    # memory-delta observation: one emit per session, immediately before
    # `session_end` — activity in the shared project memory directory during
    # this session's window; it does not establish session authorship.
    # Stat-only producer; closed enums + INT counters only.
    # DENIED on the wire: memory file names/basenames, file bodies, the
    # memory-dir absolute path and the $HOME-derived slug, the raw
    # session_start source line, any env value (LLM06 side-channel guard
    # — the producer renders counts on the systemMessage operator channel,
    # and never forwards basenames to the signed chain).
    "session_memory_delta_observed",
}
