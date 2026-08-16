The new file-assignment enforcement can accept authority declarations that it does not fully parse or track. This permits required-assignment and overlap checks to pass while writable files remain unrepresented.

Full review comments:

- [P1] Taint unsupported Markdown edit bullets — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/hooks/check_agent_spawn.py:1598-1600
  When `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED=1`, a block containing `- CAN edit: safe.py` followed by the valid CommonMark bullet `+ CAN edit: secret.py` is classified as concrete because the second grant is neither parsed nor tainted. The spawn therefore passes enforcement and overlap telemetry hashes only `safe.py`, leaving the additional authority invisible; unsupported bullet and numbered-list forms should fail closed.

- [P1] Reject non-concrete edit values — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/hooks/check_agent_spawn.py:1802-1804
  When file-assignment enforcement is enabled, broad or expandable values such as `CAN edit: all files`, `CAN edit: any path`, or `CAN edit: $HOME/.ssh/config` pass as concrete because only a small punctuation set and three exact placeholders are rejected. These values do not identify the files the agent can actually modify, so the acceptance gate succeeds while collision hashes cannot represent the granted authority; broad prose and shell-expansion forms need to be rejected.

- [P2] Reject assignments exceeding the tracked-path cap — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/hooks/check_agent_spawn.py:1837-1838
  For a valid assignment containing more than 64 paths, the classifier silently drops every path after the cap but still returns `concrete`. With `CEO_SPAWN_OVERLAP_GUARD=1`, collisions involving those omitted paths are therefore not detected; over-cap assignments should be rejected or otherwise represented without silently losing authority.