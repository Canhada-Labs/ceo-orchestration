The installer rerun path corrupts baseline provenance for rendered files, and symlink-preservation branches can abort upgrades instead of preserving safely. The landing script also omits an approved change required for its newly wired parity gate.

Full review comments:

- [P1] Preserve rendered hashes on installer reruns — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2338-2339
  On any rerun over a v1.3 install, the prior marker record makes `_CONTINUITY_FIRED=1`, and this switches the baseline for every enumerated file to the pristine source tree, not just the skipped SPEC. Installer-rendered files such as `.claude/team.md` and skills after `--project` or other substitutions legitimately differ from source, so a no-op reinstall rewrites their manifest hashes to values that do not match disk; `doctor.sh` then reports widespread adopter drift and later upgrades classify these files as customized/conflicting and stop refreshing them.

- [P2] Make missing LINK records follow the preserve path — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1781-1781
  When a copy-mode or manifestless adopter has replaced `SPEC/v1` with a symlink, there is intentionally no matching `LINK` row. Under `set -euo pipefail`, this assignment receives status 1 from `grep | head` and terminates the entire upgrade before the intended warning-and-preserve branch, potentially after earlier surfaces were already updated; the marker lookup at line 1985 has the identical failure mode.

- [P2] Apply the staged parity-classifier edit in the landing script — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh:52-54
  Running this documented landing script from the approved anchor applies the F3 implementation and smoke workflow but never copies `scripts/tests/_parity_classify.py`, even though the signed scope and staged manifest include it. The old classifier retains the mandatory-fire F3 `KNOWN_OPEN` entries; once these fixes land and the entries stop matching, the newly wired parity e2e exits 1 for ledger rot, so this script cannot reproduce the validated tree.
