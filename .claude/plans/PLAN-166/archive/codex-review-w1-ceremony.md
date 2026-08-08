The delivery-record implementation loses ownership information on installer reruns and mishandles link-mode baseline rewrites. Its legacy SPEC fingerprint can also misclassify customized trees and force-refresh them.

Full review comments:

- [P1] Preserve earlier delivery records on installer reruns — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2301-2303
  When `install.sh` is rerun on an already-installed target, `install_one` returns EXISTS for these paths, leaving all three flags zero, and this rewrite replaces the existing manifest without consulting its prior delivery records. The rerun therefore drops ownership of SPEC, PROTOCOL, and the marker; a user install then has no trusted version source, and a v1.3 SPEC will be preserved indefinitely as an ADOPTER-FORK because it is absent from the legacy fingerprints. Preserve valid pre-run delivery records rather than treating every EXISTS result as adopter-owned.

- [P2] Retain LINK records during baseline rewrites — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1817-1819
  For a target installed with `--mode link`, the new refresh branches preserve the symlinks and mark them delivered, but the later manifest rewrite still uses `FMS_MODE=copy`. Consequently the `SPEC/v1` directory symlink is omitted from the rewritten manifest, while the marker symlink becomes a hash record that `doctor.sh` reports as a type-change drift. Preserve LINK serialization or recover the original install mode when rewriting the baseline.

- [P2] Reject non-regular entries from pristine SPEC matching — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1657-1658
  On a legacy tree whose regular files match a pristine release but which also contains an adopter-added symlink, `find -type f` omits that entry, so the fingerprint still matches and the forced refresh replaces the tree instead of preserving it as an ADOPTER-FORK. Traversal errors can similarly produce a partial fingerprint because the pipeline status is not checked. Include the complete entry inventory or reject non-regular/partially traversed trees.