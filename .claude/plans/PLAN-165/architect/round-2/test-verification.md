# Round 2 — verificacao de testes na invocacao do CI

VERIFICATION REPORT — PLAN-165 (worktree /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/worktrees/plan165)

1. Targeted CI invocation
   `pytest .claude/scripts/tests/test_night_mode.py .claude/scripts/tests/test_ceo_boot_night_mode.py -q --tb=short` → **53 passed** in 5.97s. No failures.

2. Full scripts pass (non-serial, `-n auto -m 'not serial'`)
   **2 failed, 4570 passed, 22 skipped** in 186s. Failing tests:
   - `.claude/scripts/tests/test_reality_ledger.py::test_detector_6_no_phantoms_at_head` — reality-ledger detector 6 flags phantom action `night_mode_toggled` emitted at `.claude/scripts/night-mode.py:287` but not registered in `_KNOWN_ACTIONS` (remediation per test: register the action via KERNEL ceremony or rename the emit call site).
   - `.claude/scripts/tests/test_check_audit_registry_coverage.py::TestRealRepoSmoke::test_real_repo_exit_0` — same root cause: registry checker exits 1 with "Orphan emit_night_mode_toggled called at .claude/scripts/night-mode.py:287; register 'night_mode_toggled' first" (fix requires adding the action to BOTH `_KNOWN_ACTIONS` and the schema table with a v2.X schema bump per ADR-043/SPEC-v1 additivity).
   Both failures are caused by the PLAN-165 change itself (unregistered audit action), not by flakes.

3. Serial pass (`-m 'serial'`)
   **344 passed, 2 skipped** (4594 deselected) in 82s. No failures.

4. Script smoke against throwaway tmp dir (`/private/tmp/claude-501/.../scratchpad/nm-smoke.EQvXs7`, never the real tree)
   - `on` (no pre-existing file): exit 0; message "night-mode: ON ... Previous local value: absent"; writes `<tmp>/.claude/settings.local.json` = `{"permissions": {"defaultMode": "acceptEdits"}}`.
   - `status` (armed): exit 0; reports effective defaultMode 'acceptEdits' (layer: local), marker PRESENT with mode_written/host/ts, reconciliation AGREE (ON).
   - `off`: exit 0; "restored to absent (snapshot)"; since the snapshot was "absent", the settings.local.json file is removed entirely — clean round-trip to the initial state.
   - `status` (disarmed): exit 0; effective defaultMode 'auto' (layer: user), overlay None, marker absent, reconciliation AGREE (OFF).
   - Round-trip with pre-existing keys (`defaultMode: "plan"`, `allow: ["Bash(ls:*)"]`, `env.FOO`): `on` exit 0 flips only defaultMode→acceptEdits and preserves `allow` + `env`; `off` exit 0 restores defaultMode→"plan" with all other keys byte-identical to intent. settings.local.json round-trips correctly.

VERDICT: night-mode feature tests and script behavior are green; full suite is RED with exactly 2 failures, both from the unregistered `night_mode_toggled` audit action at `.claude/scripts/night-mode.py:287` — must be registered in `_KNOWN_ACTIONS` + schema table (schema version bump) before land.
