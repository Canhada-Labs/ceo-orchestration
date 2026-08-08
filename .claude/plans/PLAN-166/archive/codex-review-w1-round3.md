The new forced SPEC refresh can delete a non-directory replacement after a failed backup, and its advertised recovery path cannot transition newer unrecorded SPEC trees into managed ownership.

Full review comments:

- [P2] Abort when the non-directory SPEC backup fails — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1820-1822
  When a recorded `SPEC/v1` directory has been replaced by a regular file and that file cannot be copied (for example, it is unreadable), `|| true` suppresses the backup failure and `rm -f` immediately deletes it before installing the new directory. This violates the promised backup-before-forced-refresh behavior and can lose adopter content; only remove the path after a successful backup.

- [P2] Make the SPEC recovery command establish ownership — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1792-1794
  For an unrecorded SPEC newer than v1.2, following this instruction with the current framework checkout does not work: the next run compares the copied tree only against `_SPEC_PRISTINE_FINGERPRINTS` for v1.2 and earlier, classifies it as `ADOPTER-FORK` again, and omits it from the rewritten manifest. Consequently affected installs remain permanently outside forced refresh; accept an exact current-source match or print a takeover procedure that makes `SPEC/v1` absent before rerunning.