# deny-write-twins.patch — NOTES

**What:** removes the 3 `Write()` twins from the night-mode/posture deny surface in
`.claude/settings.json` (lines 794/796/798 pre-patch) and mirrors the removal
byte-identically in `templates/settings/settings.base.json`, updating the
`_night_mode_deny_surface_comment` in both files.

**Why:** the current harness (>= 2.1.216) does NOT consult `Write(path)` rules in its
file-permission check (the CLI emits an active warning for such rules); `Edit(path)`
deny entries cover ALL file-editing tools. This is the same class PLAN-161 C1 already
removed from the credential-read DENY_BASELINE. The old-CLI residual documented there
is now accepted for the posture files too; the load-bearing defense for these paths is
the `_CANONICAL_GUARDS` rail in `check_canonical_edit.py` + kernel-tier listing in
`check_arbitration_kernel.py` (CX-1) — both untouched by this patch.

**Base commit:** `9c63750` (overlay clone + clean-clone apply-check both at this HEAD).

## Files changed (2)

| File | Change |
|---|---|
| `.claude/settings.json` | deny 30→27 entries (removed `Write(.claude/settings.local.json)`, `Write(.claude/state/night-mode.json)`, `Write(.claude/scripts/night-mode.py)`); `_night_mode_deny_surface_comment` sentence "The Write() twins are kept deliberately despite PLAN-161 C1 (…)" replaced with the removal rationale; "six entries" → "three entries" (both occurrences) |
| `templates/settings/settings.base.json` | deny 10→7 entries (same 3 removals); same comment adjustment ("kept deliberately" → removal rationale; "six entries are byte-identical" → "three entries are byte-identical") |

Parity claim kept TRUE: the surviving 3-entry block is byte-identical in both files —
`Edit(.claude/settings.local.json)`, `Edit(.claude/state/night-mode.json)`,
`Edit(.claude/scripts/night-mode.py)` (asserted by script during validation).

## Consumer sites verified (derived from disk, `grep -rln 'Write(.claude/…'` + night-mode/DENY_BASELINE sweeps)

Sites that PIN the twins or the 6-entry block — **only the 2 patched files**:

1. `.claude/settings.json` — patched.
2. `templates/settings/settings.base.json` — patched.

Sites verified and NOT needing change:

3. `.claude/hooks/check_harness_config.py` — `DENY_BASELINE` = 4 entries
   (`Bash(git push --force*)`, `Edit(PROTOCOL.md)`, `Edit(.claude/settings.json)`,
   `Edit(SPEC/**)`); PLAN-161 C1 already removed its Write() twins. Still a strict
   subset of both post-patch deny lists — proven by `test_check_harness_config.py`
   (`test_live_settings_green`, `test_missing_deny_baseline_goes_red`), 32 passed,
   including re-run in the clean clone AFTER `git apply`.
4. `scripts/install.sh` — `DENY_BASELINE_ENTRIES` (20 credential/env/curl entries)
   contains no night-mode/posture entries; the PLAN-165 CX-3 section
   (`install_posture_state_ignores`) touches only `.gitignore`, not deny.
5. `scripts/tests/test-install-deny-baseline.sh` — pins the 20 baseline entries +
   `deny[:4] == template_head` (4 entries) + no-duplicates; never pins the night-mode
   block. Full behavioral run (legs A–E, real installer): PASS.
6. `.claude/hooks/tests/test_template_dogfood_parity.py` — parity over HOOK
   registrations only, not deny lists. PASS.
7. `.claude/scripts/tests/test_upgrade_settings_migration.py` (incl. U1
   TemplateParity) — checks `defaultMode` baseline, not the deny block. PASS.
8. `.claude/scripts/tests/test_fingerprint_parity.py`, `test_check_install_profiles.py`,
   `test_pair_rail_timeout_invariant.py`, `test_exit2_chokepoint.py`,
   `test_check_protocol_semver_cascade_settings_wired.py`,
   `test_subagent_model_override_removed.py`, `test_available_models_mirror.py` —
   consume the template path as fixture/name or other settings subtrees (hooks,
   models, timeouts); none pins deny entries.
9. `.claude/hooks/tests/fixtures/harness-config/settings/settings_missing_deny.json` —
   fixture for the DENY_BASELINE gate (unchanged baseline), untouched.
10. `.claude/scripts/verify-counts.sh` + `.claude/scripts/check-claude-md-claims.py` —
    no deny-entry count is a watched metric (grep 'deny': none).
11. `docs/deny-baseline.md` — no reference to the twins/night-mode entries.
12. PLAN-165 records (`PLAN-165-night-mode-owner-autonomy-toggle.md`,
    `PLAN-165/architect/round-2/*`, `PLAN-165/ceremony-staged/README.md`) — historical
    debate/ceremony records that documented the 6-entry state at the time; left
    untouched by design (records, not live config).
13. Other tests matching `settings.local.json` (`test_check_config_change.py`,
    `test_effective_config.py`, `test_fact_gate_deny_once.py`,
    `test_ceo_boot_tamper_tripwires.py`, `test_generate_available_models.py`) — use
    the file as a scratch overlay in TestEnvContext sandboxes, not the deny entries.

## Validation (all in the overlay clone at `9c63750`, CI invocation shape)

- `python3 -m json.tool` on both JSONs: VALID (pre-emit and again post-apply in a
  clean clone).
- 3-entry block byte-parity assertion script: PASS (printed both blocks).
- Residual sweep: `grep -n 'Write(.claude/'` over both files → 0 hits.
- `python3 -m pytest <8 derived hooks suites> -n auto --strict-markers -q` →
  **208 passed** (harness_config, audit_emit_night_mode_toggled,
  audit_emit_api_contract, audit_emit_plan163_lifecycle_actions,
  codex_egress_proof_telemetry, git_bypass_guard, w5_scrub_enforcement,
  template_dogfood_parity).
- `python3 -m pytest test_upgrade_settings_migration.py test_ceo_boot_tamper_tripwires.py -n auto` →
  **75 passed**.
- `bash scripts/tests/test-install-deny-baseline.sh` → **PASS** (legs A–E).
- `git apply --check` of the emitted patch on a FRESH `git clone --local` at
  `9c63750` → clean; after real apply, JSONs valid + harness-config suite
  **32 passed**.

## Residual / for the ceremony record

- deny counts after patch: dogfood 27 (4 head + 20 baseline + 3 posture),
  template 7 (4 head + 3 posture).
- The Bash-rail and kernel rails for the three posture paths are unchanged
  (`check_canonical_edit.py` `_CANONICAL_GUARDS`, `check_arbitration_kernel.py`).
- Comment text in the two files differs (as before); only the ENTRY block is claimed
  byte-identical, and that claim is now true for 3 entries.
