The new FILE ASSIGNMENT classifier rejects valid documented negative path declarations and corrupts the advisory signal used to decide whether enforcement can be enabled.

Review comment:

- [P2] Exempt denied path names from authority-word scanning — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/hooks/check_agent_spawn.py:1647-1647
  When `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED=1`, a documented assignment such as `- CAN edit: safe.py` plus `- CANNOT edit: src/write.py` is classified as unparseable because this scans the denied path for bare words like `write`, `delete`, or `allowed`. Even before enforcement, this records a false `path_count=0` and pollutes calibration telemetry; detect hidden grant clauses without interpreting filename components as authority words.