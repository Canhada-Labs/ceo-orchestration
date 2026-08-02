ID: F1
SEVERITY: P1
CLAIM: The public `--full` acknowledgment token does not prove Owner invocation because an agent can supply the same CLI argument.
EVIDENCE: `.claude/worktrees/plan165/.claude/plans/PLAN-165-night-mode-owner-autonomy-toggle.md:88` accepts a fixed token passed to an executable script, while the existing Owner-only precedent uses parent-process environment state specifically because agents cannot forge it (`.claude/hooks/check_arbitration_kernel.py:25` and `.claude/hooks/check_arbitration_kernel.py:38`).
FIX: Make `--full` unavailable through model-executed Bash and require an external interactive launcher, or add a ceremony-gated PreToolUse check using trusted parent-environment authorization; test that an agent-supplied token is rejected.

ID: F2
SEVERITY: P1
CLAIM: `off` can remove every warning while the current session remains in `acceptEdits` or `bypassPermissions`.
EVIDENCE: The plan acknowledges that settings affect only the next session at `.claude/worktrees/plan165/.claude/plans/PLAN-165-night-mode-owner-autonomy-toggle.md:57`, but `off` immediately removes the marker at line 92 and boot visibility exists only while that marker exists at line 96.
FIX: Represent `off` as `pending_restart_to_manual`, retain the warning until a new session attests the restored configuration, and make status distinguish configured-next-session posture from current-session posture.

ID: F3
SEVERITY: P1
CLAIM: W0 does not verify that adding a local `permissions` object preserves the project deny baseline or actually changes behavior relative to manual mode.
EVIDENCE: T0.2 tests only allowlisted actions at `.claude/worktrees/plan165/.claude/plans/PLAN-165-night-mode-owner-autonomy-toggle.md:122`, which already run without prompts under manual mode, while the repository documents special deep-merge behavior for permission lists at `.claude/hooks/_lib/effective_config.py:23`.
FIX: In a scratch project, prove that a non-allowlisted edit becomes automatic under `acceptEdits`, dangerous actions still prompt, and representative project `permissions.deny` entries remain enforced under both modes; remove `--full` or explicitly ratify any floor it bypasses.

ID: F4
SEVERITY: P1
CLAIM: The proposed `status` command and T0.1 evidence cannot reliably report the effective runtime posture across all precedence layers.
EVIDENCE: The plan relies on `/ceo-info` at `.claude/worktrees/plan165/.claude/plans/PLAN-165-night-mode-owner-autonomy-toggle.md:118`, but `/ceo-info` reads only project and local files and treats the last valid file as effective (`.claude/scripts/ceo-info.py:184` and `.claude/scripts/ceo-info.py:213`); the authoritative resolver documents managed-over-local precedence and an invisible CLI override at `.claude/hooks/_lib/effective_config.py:7` and `.claude/hooks/_lib/effective_config.py:19`.
FIX: Inspect user, project, local, and managed layers; report CLI/current-session posture as unknown unless live harness evidence exists; and make `on` return non-zero when a higher layer prevents the requested mode.

ID: F5
SEVERITY: P1
CLAIM: Snapshot and rollback are underspecified and can corrupt configuration or overwrite a concurrent user change.
EVIDENCE: The plan promises a saved snapshot at `.claude/worktrees/plan165/.claude/plans/PLAN-165-night-mode-owner-autonomy-toggle.md:84`, but the only defined state schema contains timestamp, mode, and hostname at line 90, and the test matrix at line 136 omits malformed JSON, stale snapshots, races, partial writes, and rollback failure.
FIX: Define a versioned state record containing original presence/value, project identity, expected enabled value, and configuration hashes; use locking plus atomic replace, refuse malformed/non-object input, compare-and-swap on `off`, and delete the marker only after verified restoration.

ID: F6
SEVERITY: P1
CLAIM: The marker-based boot warning can be stale or absent on cache hits.
EVIDENCE: Acceptance requires the warning iff the marker exists at `.claude/worktrees/plan165/.claude/plans/PLAN-165-night-mode-owner-autonomy-toggle.md:170`, but the boot cache key includes only HEAD and audit-log metadata (`.claude/scripts/ceo-boot.py:2390`), and a cache hit returns before any later live rendering at `.claude/scripts/ceo-boot.py:3930`.
FIX: Read and render night-mode state outside the cached digest on every path, or include its state hash in the cache key; test on/off/corrupt-marker transitions under cached, short, full, and JSON modes.

ID: F7
SEVERITY: P1
CLAIM: The plan’s pre-ceremony audit claim is false and its ceremony rider is insufficient to create a valid dedicated audit event.
EVIDENCE: The plan claims `audit_log.py` chains the invocation at `.claude/worktrees/plan165/.claude/plans/PLAN-165-night-mode-owner-autonomy-toggle.md:99`, but that hook is registered only for `Agent` at `.claude/settings.json:349`; adding only `_KNOWN_ACTIONS` as proposed at plan line 160 would also violate the mandatory branched/reserved/passthrough partition enforced by `.claude/hooks/tests/test_audit_emit_ghost_action_guard.py:250`.
FIX: Make audited shipment depend on a complete ceremony adding the action, deny-by-default field scrub or typed wrapper, SPEC schema/version entry, producer, HMAC-chain tests, and partition tests; do not claim audit coverage before that lands.

ID: F8
SEVERITY: P1
CLAIM: The `--full` path is not live-fire tested against existing controls that classify `bypassPermissions` as tampering.
EVIDENCE: W0 tests only `acceptEdits` at `.claude/worktrees/plan165/.claude/plans/PLAN-165-night-mode-owner-autonomy-toggle.md:122`, while `.claude/hooks/_lib/effective_config.py:534` classifies `bypassPermissions` as nullifying the native permission floor and `.claude/hooks/check_config_change.py:263` returns a block decision for that finding.
FIX: Add a dedicated full-mode live-fire probe covering ConfigChange, boot red status, explicit deny behavior, restart, and recovery; document the expected alarm without suppressing it.

ID: F9
SEVERITY: P1
CLAIM: The clean-tree guarantee is false for adopters whose repositories do not already ignore `.claude/settings.local.json`.
EVIDENCE: The framework repository ignores the file at `.gitignore:78`, but installation distributes all commands and top-level scripts (`scripts/install.sh:1116` and `scripts/install.sh:1265`) without installing that ignore rule; this contradicts the adopter-unaffected claim at `.claude/worktrees/plan165/.claude/plans/PLAN-165-night-mode-owner-autonomy-toggle.md:73`.
FIX: Refuse to mutate a tracked or non-ignored settings file, or ceremony-update install/upgrade handling to add a local-safe exclusion; verify clean status in scratch adopter repositories with absent, existing, and tracked settings files.

ID: F10
SEVERITY: P1
CLAIM: The L2 classification contradicts the repository’s mandatory-debate rules.
EVIDENCE: The plan itself calls the change VETO-relevant at `.claude/worktrees/plan165/.claude/plans/PLAN-165-night-mode-owner-autonomy-toggle.md:140` yet declares L2 at line 197; `PROTOCOL.md:130` mandates debate for multi-subsystem new features and VETO-protected domains, and `PROTOCOL.md:402` requires Staff Security approval for security changes.
FIX: Reclassify as L3, run the mandatory debate with the Security Engineer/VETO owner, and require the full V0–V3 verification cascade rather than an advisory V2 review.

ID: F11
SEVERITY: P2
CLAIM: The boot-marker tests are not explicitly covered by the mandatory environment-isolation requirement.
EVIDENCE: TestEnvContext is specified only for T1.3 at `.claude/worktrees/plan165/.claude/plans/PLAN-165-night-mode-owner-autonomy-toggle.md:136`, while separate boot tests are introduced at line 148 and necessarily read state under HOME; the repository rule is explicit at `AGENTS.md:24`.
FIX: Require every night-mode and ceo-boot test to use `TestEnvContext` with `mock.patch.dict`, isolated state/cache paths, and assertions that real HOME and `CLAUDE_PROJECT_DIR` were untouched.

ID: F12
SEVERITY: P2
CLAIM: The count-drift wave does not identify all zero-tolerance command-count surfaces and incorrectly relies on a checker that does not check command counts.
EVIDENCE: The plan names only selected docs plus vague “derived surfaces” at `.claude/worktrees/plan165/.claude/plans/PLAN-165-night-mode-owner-autonomy-toggle.md:150`; current exact claims also exist in `CLAUDE.md:54`, `README.md:58`, `docs/ARCHITECTURE.md:51`, `npm/README.md:58`, and `docs/COMMAND-SKILL-HOOK-MAP.md:127`, while `.claude/scripts/check-claude-md-claims.py:139` has no command-count check.
FIX: Enumerate and update every live `26` claim, regenerate `docs/COMMAND-SKILL-HOOK-MAP.md`, and require `verify-counts.sh` plus a command-map drift check after the new command exists on disk.

ID: F13
SEVERITY: P2
CLAIM: The fallback branch does not satisfy the plan’s one-command or acceptance contracts.
EVIDENCE: The fallback at `.claude/worktrees/plan165/.claude/plans/PLAN-165-night-mode-owner-autonomy-toggle.md:109` ships only a launcher note while the toggle manages an unrelated marker, but acceptance still requires `/night-mode on` to start `acceptEdits` and `/night-mode off` to restore manual at lines 166–169.
FIX: Either abort the plan when W0 fails or implement and probe a real launcher with conditional fallback-specific acceptance criteria, lifecycle-bound marker cleanup, and explicit managed/CLI precedence behavior.

VERDICT: REJECT