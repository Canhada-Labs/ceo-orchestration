The targeted tests pass, but the dry-run restore can still falsely report successful verification when Git fails. The collection-count audit snapshot is also stale within the same patch.

Full review comments:

- [P2] Fail when restore verification cannot run — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/scripts/local/release.sh:233-233
  During `bump --dry-run`, if `git status` fails because of a repository, permission, or object error, `|| true` converts that failure into an empty `_dirty`; the function then prints “asserted clean” and exits successfully even though the postcondition was never verified. Preserve and check the command's exit status so this final verification fails closed.

- [P2] Recompute the collection snapshot after adding tests — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/scripts/local/verify-counts.sh:88-89
  On this proposed tree, the documented commands report 14,263 tests and 14,310 tests with 22 errors, not 14,252 and 14,299. The 11-test difference comes from tests added in this patch, so the newly dated “pasted output” snapshot is already stale and should be regenerated after all test additions.