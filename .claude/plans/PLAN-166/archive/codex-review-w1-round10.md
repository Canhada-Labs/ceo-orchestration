The main paths pass their new tests, but link-mode manifest rewrites can legitimize redirected or adopter-owned symlinks, and descendant skips can still be violated. The CI path filters also omit a direct dependency of the newly wired regression tests.

Full review comments:

- [P2] Validate LINK targets before preserving ownership — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2311-2313
  On a `--link` reinstall after a managed `SPEC/v1` or marker symlink was retargeted, `install_one` skips the existing path and these continuity checks accept any prior record without comparing its LINK target to the live `readlink`. The manifest writer then serializes the redirected target as the new delivery record, so subsequent upgrades accept the foreign SPEC or stale marker as healthy. Preserve continuity only when the prior and live LINK targets match, or carry the prior LINK record forward unchanged.

- [P2] Restrict link serialization to previously owned paths — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:3048-3050
  When any prior LINK record exists, this globally enables LINK serialization for the entire rewritten manifest. A target-only adopter symlink preserved inside a real enumerated directory such as `.claude/hooks/` is then recorded by `_write_baseline_manifest` before `FMS_HASH_ROOT` can reject it, converting an unowned path into a framework delivery record that `doctor.sh` treats as managed. LINK serialization should be limited to validated pre-upgrade LINK paths rather than every live symlink.

- [P2] Include symlinks in descendant skip detection — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1834-1835
  For a record-owned SPEC containing a target-only symlink, `--skip SPEC/v1/local.md` is ignored because both scans enumerate only `-type f`. The function then proceeds with the wholesale `find -delete` refresh and removes the explicitly excluded symlink. Include link and other removable entry types in this union so descendant skip patterns reliably preserve their paths.

- [P2] Trigger ownership tests when the hash helper changes — /Users/joaocanhada/canhada-labs/ceo-orchestration/.github/workflows/smoke-install.yml:19-22
  The newly wired ownership and historical-parity tests exercise `_hash_file` and `_hash_stdin` from `scripts/_hash_lib.sh`, but that dependency is absent from both path-filter lists. A PR changing only the hash helper therefore skips this workflow and the only CI execution of these shell e2e tests, allowing the legacy SPEC migration to regress unnoticed. Add the helper to both synchronized trigger lists.
