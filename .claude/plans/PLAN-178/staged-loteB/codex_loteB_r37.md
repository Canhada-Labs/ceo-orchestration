The new FILE ASSIGNMENT enforcement has parser differentials that can accept fenced or non-concrete grants. These undermine the fail-closed spawn contract and workflow pre-dispatch validation.

Full review comments:

- [P2] Require same-character closing fences — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/hooks/check_agent_spawn.py:1756-1756
  When `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED=1`, a prompt containing an opening ``` fence followed by a fake ` ```~~~ ` close and a fenced FILE ASSIGNMENT is classified as concrete, even though CommonMark keeps that assignment inside the unclosed code block. The suffix ``[`~]*`` accepts mixed marker characters despite the comment requiring the same character, allowing fenced examples to satisfy the gate and corrupt overlap telemetry.

- [P2] Reject non-concrete workflow assignment values — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/workflows/audit-fanout.js:107-110
  When a workflow prompt gains an appended assignment such as `- CAN edit: $HOME/.ssh` or `- CAN edit: all files`—for example through the raw `scope` argument—this predicate marks it valid, although ADR-191 and the Python hook reject `$`, whitespace, Unicode separators, and empty-normalized paths. Because the canonical block already makes `faOk` true, dispatch proceeds with the injected authority; the same incomplete predicate is duplicated in all four workflows.