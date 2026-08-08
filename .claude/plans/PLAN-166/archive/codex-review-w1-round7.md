The new delivery-record paths can trust a modified version marker, lose ownership across ceremony transitions, and mishandle valid link targets containing spaces. These cause incorrect update reporting and persistent stale framework surfaces.

Full review comments:

- [P2] Verify the live marker against its manifest record — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/scripts/check-framework-updates.sh:123-128
  When a delivered marker is later edited or replaced with any other well-formed version, the old manifest still satisfies this regex and the checker trusts the live bytes without validating the recorded hash or LINK target. For example, changing `1.3.0` to `9.9.9` makes the checker report up-to-date against an upstream `1.3.0`, suppressing the needed update; validate the live marker against its record before selecting it, otherwise fall back.

- [P2] Preserve delivery records when switching to user ceremony — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1747-1749
  If a maintainer installation is rerun with `install.sh --ceremony user`, installer continuity preserves its SPEC delivery records while the state records `ceremony=user`; this early return then leaves `_SPEC_DELIVERED=0`, so the post-upgrade manifest rewrite erases those records while leaving the tree in place. After switching back to maintainer mode once the source changes, that unrecorded v1.3 tree matches neither the current source nor the legacy fingerprints and remains a stale `ADOPTER-FORK`; carry prior ownership through this skip (and the analogous PROTOCOL skip).

- [P2] Parse LINK targets without splitting on spaces — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1760-1760
  For a `--link` installation whose framework checkout path contains whitespace, the recorded target is the complete path but `awk '{print $3}'` returns only its first whitespace-delimited component. The unchanged live SPEC link is therefore treated as redirected and loses framework ownership; the marker lookup at line 1961 has the same defect. Parse the target using the manifest's fixed double-space delimiters instead.
