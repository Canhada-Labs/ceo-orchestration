The enforcement recovery guidance causes unparseable prompts to fail repeatedly because appending another block does not clear the existing taint. The implementation otherwise passed the available static checks and workflow fixture checks.

Review comment:

- [P2] Replace malformed assignments instead of appending — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/hooks/check_agent_spawn.py:2580-2584
  When `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED=1` rejects an `unparseable` assignment, following this recovery text and appending a valid block cannot succeed: `_classify_file_assignment()` aggregates all blocks and any invalid token keeps `invalid_seen=True`, so the retry is blocked again. Recommend replacing/removing the malformed block; appending is valid only for the `absent` state.