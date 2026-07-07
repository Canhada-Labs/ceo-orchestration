# harness-config fixtures — INERT TEST DATA

Fixture corpus for `check_harness_config.py` (PLAN-153 Wave E item 1,
ADR-173) and its test suite `test_check_harness_config.py`.

**Everything in this directory is inert, non-executable test data.**
The "secrets" are canonical public documentation examples (e.g. the AWS
docs example access key `AKIAIOSFODNN7EXAMPLE`), the "destructive
commands" are JSON string values that are only ever fed to a blocking
hook's stdin so the hook can be asserted to BLOCK them, and the settings
files are synthetic — they are never loaded by the harness.

## Layout

- `replay/` — known-bad stdin payloads for the behavioral
  positive-control replay (`check_harness_config.py --replay`). Each file
  declares `"expect": "block"`; the replay runner REDDENS if the fixture
  is missing, unparseable, tampered, or if the hook under test does not
  emit a block-shaped decision. `{{PROJECT_DIR}}` is substituted with the
  absolute repo root at replay time.
- `settings/` — synthetic settings.json documents for the static checks:
  - `settings_good.json` — anchored commands + full deny baseline: green.
  - `settings_runtime_unresolvable.json` — planted cwd-relative shim path
    (the S254 dead-rail class): must go RED.
  - `settings_inline_secret.json` — planted inert secret value: must go RED.
  - `settings_noop_unlisted.json` — constant-emitter hook without the
    `[harness-noop-ok]` annotation: must go RED.
  - `settings_noop_allowlisted.json` — same no-op WITH the annotation:
    must pass.
  - `settings_missing_deny.json` — permissions.deny missing baseline
    entries: must go RED.

The `settings/` fixtures reference `check_ok_hook.py` / `_python-hook.sh`
paths that only exist inside the synthetic project tree each test builds
(via `TestEnvContext`), so they resolve nowhere in the real repo.
