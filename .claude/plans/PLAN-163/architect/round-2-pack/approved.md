---
plan: PLAN-163
round: 2-pack
type: architect-sentinel
segment: SUBSTRATE-UPLIFT-MAIN-PACK
---

# PLAN-163 main-pack — substrate uplift ceremony (Owner sentinel)

Anchor-SHA: 9477bde1484784363fff438ece8523021eebdf17

Approved-By: @Canhada-Labs (Owner GPG — signed inline by the ceremony)
Approved-At: 2026-07-30

## What this sentinel authorizes (sign this breadth KNOWINGLY)

SECOND of the TWO declared PLAN-163 ceremonies. Pre-conditions already
proven when this is signed: GATE-PIN ceremony landed (commit tagged
`[SENT-PLAN163-PIN]` in log), GATE-V2 fresh-liveness PASS anchored
strictly AFTER that commit, and the 3-vendor pack review APPROVE.
Scope = the main-pack (43 files, `staged/main-pack/MANIFEST.sha256`,
tracked twin `inputs-pack.sha256`). Guard classes concentrated here:

1. **Model refresh Claude 5 (T1 / ADR-181 NEW):** ADR-149 amendment
   (working-set += claude-opus-5, claude-sonnet-5 appended at END;
   `FALLBACK_MODEL_CHAIN` → `["claude-opus-5"]`; VETO floor += opus-5,
   Fable 5 stays the ceiling), regen of both `availableModels` mirrors,
   independent validators (`validate-governance.sh`,
   `tier_policy_cli/_types.py`), routing (`model_routing.py`,
   `audit_log.py` role→model), presence-based pricing/detector fixes.
2. **Hook-stdout schema oracle (T2):** `check-hook-stdout-schema.py` +
   versioned 2.1.220 schema snapshot + new `hook-stdout-schema-oracle`
   job in validate.yml (additions-only).
3. **New hook events (T3 / ADR-183 NEW):** `check_directory_added.py`
   (observer-writer → `.claude/state/session-roots.json`, gitignored) +
   `check_notification.py` + session-roots write-guard extension of
   `check_canonical_edit.py` + typed audit actions in `audit_emit.py`
   (KERNEL) + SPEC audit-log schema v2.53 + registrations 46 → 48
   (dogfood) / template stays 45 behind the T3.4 feature gate.
4. **Settings posture (OQ5(c)) + migration (T5.4/T5.5):** dogfood
   settings.json turns on the fail-closed posture keys; template exposes
   them commented; `upgrade.sh` baseline-aware idempotent settings
   migration (3-state per leaf key) + oracles. FXε (C5): the user
   template `settings.user.json` pins the session default
   `"model": "claude-opus-5"` (advisory path — deliberately NO
   availableModels/enforceAvailableModels), regression-guarded by
   `UserTemplateSessionDefaultPinTest` in the parity test.
5. **Docs (T6):** substrate-adopt-2026-08, CEO-MODEL-ROUTING,
   ACCELERATORS (fast-mode = cost×latency trade-off, NO speed numbers).

THREE kernel surfaces in this scope, applied under ONE declared token
`CEO_KERNEL_OVERRIDE=PLAN-163-T3-EVENT-ACTIONS`: `.claude/settings.json`,
`.github/workflows/validate.yml`, `.claude/hooks/_lib/audit_emit.py`.
The two SPEC/deny-Edit surfaces (`SPEC/v1/audit-log.schema.md`) are
applied via Bash under this sentinel. The Owner-shell apply route does
not trip in-session canonical hooks — this signed sentinel IS the
authorization record (S261 precedent); the kernel-override export is the
ADR-031 declaration.

ADR count 181 → **183** (ADR-181 + ADR-183 are NEW; ADR-149 is an
in-place amendment). Count surfaces (CLAUDE.md triple: hooks on disk
55→57, wired 44→46, registrations 46→48; ADRs →183) update in the
session-closeout commit BEFORE push — cache discipline; this ceremony
does NOT edit CLAUDE.md.

Non-canonical W2 live-tree fixes (audit-telemetry presence fixes and
siblings) are committed SEPARATELY by the ceremony script BEFORE this
sentinel is signed — they are NOT in this scope.

## Scope

Scope:
  - .claude/adr/ADR-149-model-id-allowlist.md
  - .claude/adr/ADR-181-claude-5-model-refresh.md
  - .claude/adr/ADR-183-directory-added-notification-events.md
  - .claude/data/hook-schema-2.1.220.json
  - .claude/hooks/_lib/agent_frontmatter.py
  - .claude/hooks/_lib/audit_emit.py
  - .claude/hooks/_lib/model_routing.py
  - .claude/hooks/audit_log.py
  - .claude/hooks/check_canonical_edit.py
  - .claude/hooks/check_directory_added.py
  - .claude/hooks/check_notification.py
  - .claude/hooks/tests/test_adr149_validator_parity.py
  - .claude/hooks/tests/test_adr_052_role_to_model_coverage.py
  - .claude/hooks/tests/test_audit_emit_api_contract.py
  - .claude/hooks/tests/test_audit_emit_plan163_lifecycle_actions.py
  - .claude/hooks/tests/test_check_directory_added.py
  - .claude/hooks/tests/test_check_notification.py
  - .claude/hooks/tests/test_check_tier_policy_misrouting_24h.py
  - .claude/hooks/tests/test_codex_egress_proof_telemetry.py
  - .claude/hooks/tests/test_git_bypass_guard.py
  - .claude/hooks/tests/test_model_routing_resolve.py
  - .claude/hooks/tests/test_model_routing_resolve_full.py
  - .claude/hooks/tests/test_session_roots_write_guard.py
  - .claude/hooks/tests/test_template_dogfood_parity.py
  - .claude/hooks/tests/test_w5_scrub_enforcement.py
  - .claude/scripts/check-hook-stdout-schema.py
  - .claude/scripts/tests/test_check_hook_stdout_schema.py
  - .claude/scripts/tests/test_generate_available_models.py
  - .claude/scripts/tests/test_upgrade_settings_migration.py
  - .claude/scripts/tier_policy_cli/_types.py
  - .claude/scripts/tier_policy_cli/tests/test_types.py
  - .claude/scripts/validate-governance.sh
  - .claude/settings.json
  - .github/workflows/validate.yml
  - .gitignore
  - SPEC/v1/audit-log.schema.md
  - docs/ACCELERATORS.md
  - docs/CEO-MODEL-ROUTING.md
  - docs/substrate-adopt-2026-08.md
  - scripts/local/smoke-install-parity.sh
  - scripts/upgrade.sh
  - templates/settings/settings.base.json
  - templates/settings/settings.user.json
