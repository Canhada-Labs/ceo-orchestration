The new FILE ASSIGNMENT enforcement can be bypassed using an unclosed HTML comment, violating its fail-closed input contract when enforcement is enabled.

Review comment:

- [P2] Reject assignments inside unclosed HTML comments — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/hooks/check_agent_spawn.py:1808-1809
  When `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED=1`, a prompt such as `<!--\n## FILE ASSIGNMENT\n- CAN edit: fake.py` passes this gate because `_strip_fenced_and_comments()` removes only closed `<!-- ... -->` pairs, so `_classify_file_assignment()` returns `concrete`. Since an unclosed HTML comment extends to EOF, this lets commented-out content satisfy the new fail-closed acceptance contract; mask unclosed comments to EOF or classify them as unparseable.