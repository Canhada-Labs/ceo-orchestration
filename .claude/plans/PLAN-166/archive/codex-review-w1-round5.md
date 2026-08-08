The new delivery-record and forced-refresh paths can reclassify user-modified SPEC content as framework baseline, misreport a failed backup as successful, and ignore valid target-only skip requests. These create data-loss or contract-violation scenarios that should be fixed before landing.

Full review comments:

- [P1] Preserve prior hashes when carrying delivery records forward — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2311-2314
  When `install.sh` is rerun after a delivered `SPEC/v1` has been edited, `install_one` skips it and this branch restores `_DELIVERED_SPEC=1`; `_write_baseline_manifest` then hashes the edited target because install does not set `FMS_HASH_ROOT`, replacing the original baseline. A subsequent `uninstall.sh` therefore sees the fork's hash as framework-owned and deletes the user-modified SPEC instead of preserving it; continuity must retain framework/prior hashes rather than re-baseline skipped content.

- [P1] Verify the fork snapshot before advertising recovery — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1813-1817
  When backup creation or copying fails—for example because `.claude.bak` is unwritable, the disk is full, or the SPEC is unreadable—both failures are suppressed here, but the following warning claims the snapshot exists and tells the operator to delete and replace the target SPEC. Following that printed recovery can destroy the only copy of the fork, so the copy result must be checked and recovery guidance withheld when no snapshot was created.

- [P2] Honor skips for target-only SPEC files — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1771-1771
  When an adopter has a target-only file such as `SPEC/v1/local.md` and runs `upgrade.sh --skip SPEC/v1/local.md`, this scan considers only files in `$SOURCE_DIR/SPEC/v1`, so the skip is never detected. For a recorded SPEC, the forced-refresh branch then removes the whole target tree and replaces it, removing the explicitly skipped file from the active tree; skip detection needs to inspect the union of source and destination paths.