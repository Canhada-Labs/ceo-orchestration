The new forced-refresh paths can write through a symlinked SPEC ancestor and do not consistently honor existing destination types or documented skip patterns. These issues can modify adopter-owned or external data.

Full review comments:

- [P1] Reject symlinked ancestors before copying SPEC — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1799-1800
  When `TARGET/SPEC` is a symlink, `TARGET/SPEC/v1` is not itself `-L`, so the leaf-only guard does not catch it. If the external `v1` is absent, the new-delivery branch reaches this copy and writes outside the target; if it matches a pristine fingerprint, the preceding `find -delete` can erase external files. Check every ancestor with the existing symlink-safety helper before fingerprinting, deleting, or copying.

- [P2] Honor descendant --skip patterns for SPEC — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1727-1730
  For a documented file-level exclusion such as `--skip 'SPEC/v1/install-cli.md'`, the matcher is only invoked with the literal directory name `SPEC/v1`, so the pattern never matches and the later wholesale refresh overwrites the skipped file. Either detect descendant skip patterns and preserve/refuse the whole contract refresh, or explicitly reject unsupported per-file SPEC exclusions.

- [P2] Refuse non-file marker destinations before copying — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1843-1844
  If an adopter already has a directory at `.claude/.framework-version`, install correctly skips it, but this `cp` copies the source marker inside that adopter-owned directory; validation then warns and continues, leaving an unintended file behind. Other non-regular destinations such as FIFOs can block the upgrade, so non-file, non-symlink destinations should be preserved or rejected before copying.