The new ownership-continuity logic can both legitimize foreign symlinks and silently discard prior SPEC ownership. Version reporting is also incorrect for pinned downgrades and for preserved pre-existing marker files.

Full review comments:

- [P2] Reject hash-to-link transitions during continuity — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2326-2328
  On a `--link` rerun after a copy-installed SPEC or marker has been replaced by a symlink, the prior manifest contains only HASH rows, so this early success bypasses target validation. The continuity branch then marks the destination delivered and records the arbitrary live symlink as a trusted LINK entry. Require the live type to agree with the prior record rather than treating the absence of a LINK row as a match.

- [P2] Preserve records when continuity finds missing SPEC files — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2330-2337
  When a previously delivered `SPEC/v1` still exists but has become empty, `install_one` skips it and this branch claims continuity, yet the manifest rewrite emits no SPEC file records from the empty target. The next upgrade therefore classifies the tree as an unowned adopter fork and will not restore the compliance contract. Carry forward validated prior rows or re-deliver missing files instead of setting only the delivery flag.

- [P2] Keep downgrade version reporting tied to the pinned source — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1987-1992
  For an external target downgraded with `--pin` to a pre-marker release, dropping the marker record does not make the target's root `VERSION` reflect the pinned source: this upgrader deliberately never modifies that adopter-owned file. Readers therefore fall back to the original install version and can report the target as newer than its actual framework content. Derive a version signal from the pinned source rather than relying on the unchanged target `VERSION`.

- [P2] Gate forensic marker guidance on its delivery record — /Users/joaocanhada/canhada-labs/ceo-orchestration/INSTALL.md:592-595
  If `.claude/.framework-version` existed before installation, the installer intentionally preserves it without adding a delivery record, but this command still reports its arbitrary value as the framework version. The checker and upgrader trust the marker only when its manifest record is valid, so the documented forensic procedure should use that checker or first verify the delivery record.
