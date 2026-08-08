The new ownership-continuity paths can re-baseline customized root protocol content as framework-owned, enabling later overwrite or deletion. The forced SPEC and version-marker routes also mishandle supported or safely preservable edge cases.

Full review comments:

- [P1] Preserve the prior PROTOCOL digest on installer reruns — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2350-2353
  When `install.sh` is rerun after a delivered `PROTOCOL.md` was customized, this continuity path sets `FMS_HASH_ROOT`, but `_write_baseline_manifest` deliberately ignores that root for generated `PROTOCOL.md` and no `FMS_PROTOCOL_HASH` is supplied here. The edited target bytes therefore become the new framework baseline, so the next upgrade treats them as pristine and overwrites them, while `uninstall.sh` can delete them as hash-matching framework content.

- [P1] Retain the canonical PROTOCOL hash on user-mode skips — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:2943-2948
  After a maintainer installation is transitioned to `--ceremony user`, the prior `PROTOCOL.md` record is intentionally retained here. If the pointer is subsequently customized, this skip never sets `_REFRESH_PROTOCOL_CANON_HASH`, so the manifest rewrite hashes the live customized file as the baseline; a later upgrade or uninstall can then overwrite or remove adopter content that should have remained marked modified.

- [P2] Reject special files before backing up SPEC/v1 — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1931-1933
  When the baseline records `SPEC/v1` but the adopter has replaced that directory with a FIFO, this non-directory branch executes `cp` on the FIFO, which blocks waiting for a writer and hangs the upgrade after earlier surfaces may already have changed. Guard for a regular file, as the marker path does, and preserve unsupported special-file destinations.

- [P2] Generate the marker when pinning pre-v1.3 releases — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1961-1964
  With the documented `--pin` option targeting a pre-v1.3 tag such as `v1.2.0`, the checked-out source lacks this tracked marker, so this branch leaves an existing v1.3 marker unchanged even though the framework content was downgraded. The subsequent source-root manifest rewrite also omits its hash record; user-ceremony targets then have no usable version source, while maintainer targets can report a stale version instead of the pinned one.
