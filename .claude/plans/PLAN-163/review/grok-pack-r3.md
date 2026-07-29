I'll review the R2 fixes against the staged packs and live W2 diff, then hunt for remaining blockers.Verifying the five R2 fixes in staged sources, then scanning pin-path env seams and settings surfaces.VERDICT: APPROVE

- `.claude/plans/PLAN-163/staged/pin-pack/.claude/hooks/check_pair_rail.py:831-832` (+ docs `:61-66`, tests `test_check_pair_rail_payload_pin.py:453-482`, `test_check_pair_rail.py:201-209`): CLOSED R2-B1 — `CEO_PAIR_RAIL_FIXTURE_RESPONSE` only under `CEO_PAIR_RAIL_TEST_MODE=1`; live path falls through to `_resolve_codex_bin()` pin verify
- `.claude/plans/PLAN-163/staged/main-pack/scripts/upgrade.sh:147-149,1827-1838` (+ help `:330-336,:357-359`, tests `test_upgrade_settings_migration.py:246-297,435-437`): CLOSED R2-B2 — top-level `model` is 4th 3-state leaf (absent→`claude-opus-5`, pin OK, customized preserve+WARN); help corrected
- `.claude/plans/PLAN-163/staged/main-pack/scripts/local/smoke-install-parity.sh:218-261`: CLOSED R2-B3 — `[6/6]` asserts `model=="claude-opus-5"` and membership in installed `availableModels`
- `.claude/plans/PLAN-163/staged/main-pack/.claude/hooks/check_directory_added.py:209-215`: CLOSED R2-M1 — `isabs` before `realpath`; relative → `(None, raw)` unparseable fail-closed at consumer
- `.claude/plans/PLAN-163/staged/main-pack/.claude/scripts/check-hook-stdout-schema.py:612-617` (+ tests `test_check_hook_stdout_schema.py:349-391`): CLOSED R2-M2 — recognized-but-empty allowed-keys → `snapshot is None` → `--require-snapshot` fails closed
- ACCEPTED: dated haiku id `claude-haiku-4-5-20251001` in validate-governance / tier_policy `_types.py` (pre-existing, tested)
- ACCEPTED: ~70 pre-existing `emit_generic` H4 TypeError-class branches (out of PLAN-163 scope)
- ACCEPTED: empty-registry-overwrite allow residual (f); M1 session-roots deny-before-allowlist under missing `session_id` (strictly-more-restrictive, anomalous-input-only)

R2 closures hold (5/5); no pin-path ungated env seam remains (`CODEX_BIN` still sha-verified; only `TEST_MODE` unlocks fixture/manifest/triple; `DISABLE` is the documented kill-switch). Settings surfaces that ship `claude-sonnet-5` also pin `model=claude-opus-5` (staged `settings.json` + `settings.base.json` + upgrade T5.4); manifests 42/18 self-verify clean; live W2 is additive telemetry/STALE_RE only — no new blocker.
