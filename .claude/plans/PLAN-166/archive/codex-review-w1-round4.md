The newly enabled parity gate is guaranteed to fail because its mandatory-fire exceptions were not removed. The marker and SPEC refresh paths also mishandle symlinks and can write outside the target or adopt stale content as framework-owned.

Full review comments:

- [P1] Delete closed parity exceptions before running the gate — /Users/joaocanhada/canhada-labs/ceo-orchestration/.github/workflows/smoke-install.yml:176-176
  The unchanged `scripts/tests/_parity_classify.py` still declares `F3-spec-stale` and `F3-protocol-user-mode` as mandatory-fire `KNOWN_OPEN` entries. This patch closes both defects, so the classifier's ledger-rot audit returns 1 when this newly wired command runs, making every affected smoke workflow fail before reaching the ownership test.

- [P1] Block marker writes through symlinked ancestors — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1904-1905
  When `$TARGET/.claude` is a symlink, testing `-L "$dst"` only checks the marker leaf while `-f` and this `cp` follow the ancestor, so the upgrade overwrites `.framework-version` outside the target tree. Apply `_lg_ancestor_is_symlink` before any marker backup or write, as the new SPEC route already does.

- [P2] Validate SPEC symlinks against the prior LINK record — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1720-1725
  If a copy-mode installation's recorded `SPEC/v1` directory is replaced with a leaf symlink, or a genuine link-mode target is redirected, this branch assumes it is the original link install based only on the current file type. It skips the forced refresh, marks SPEC delivered using any hash/LINK record, and the baseline rewrite adopts the current arbitrary link, leaving the compliance contract stale; only an unchanged prior `LINK  SPEC/v1` target should take this path.

- [P2] Validate marker symlinks before trusting link mode — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1879-1882
  When a copy-mode marker is replaced by a symlink, or an original link-mode marker is redirected, this branch treats it as a healthy link install and preserves ownership from any marker record. The later rewrite records the new link and `check-framework-updates.sh` trusts its potentially stale or arbitrary version; require the live link target to match the prior marker LINK record, otherwise preserve it without delivery ownership.

- [P2] Require the marker backup to succeed before overwrite — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1901-1902
  For a differing existing marker that cannot be read or copied to the backup but can still be replaced, suppressing this failure causes the next `cp` to destroy the old bytes while falsely reporting `BACKED UP`. Preserve the marker or stop the refresh when the backup fails, matching the backup-before-replace handling used for non-directory SPEC targets.