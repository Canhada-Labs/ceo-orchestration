The new fail-closed FILE ASSIGNMENT gate can be bypassed by fenced example content because the shared Markdown fence masker does not honor fence type and length.

Review comment:

- [P1] Keep long or mixed Markdown fences masked — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/hooks/check_agent_spawn.py:1797-1798
  When `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED=1`, a named prompt can satisfy the new gate using a FILE ASSIGNMENT that is still inside a CommonMark fence. `_strip_fenced_and_comments` toggles on every line beginning with ``` or ~~~ without tracking the opener character or length, so a four-backtick opener followed by three backticks—or a backtick opener followed by tildes—is treated as closed; `_classify_file_assignment` then accepts a following fake assignment even though Markdown keeps it fenced. Track the opener type and minimum closing length before classifying.