The new FILE ASSIGNMENT security gate has multiple parser differentials that can accept non-grants or miss hidden grants. The new shared-memory trigger instructions also contain contradictory status semantics.

Full review comments:

- [P1] Anchor whitelisted assignment lines — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/hooks/check_agent_spawn.py:1609-1612
  When the assignment or overlap guards are enabled, a line such as `- If you need permission: CAN edit: hidden.py` passes this prefix-only whitelist. The classifier then treats the block as read-only, so the hidden path is neither hashed for overlap detection nor rejected by the required-assignment gate even though the agent sees a positive grant; validate the complete allowed line or reject grant text in its suffix.

- [P1] Reject code-indented CAN-edit examples — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/hooks/check_agent_spawn.py:1592-1594
  With `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED=1`, a four-space-indented `- CAN edit: fake.py` is a CommonMark code block rather than an assignment, but this regex accepts arbitrary indentation and classifies the declaration as concrete. An empty assignment can therefore satisfy the new gate using example text, while overlap telemetry reserves a path the agent was not actually granted; constrain indentation to valid list syntax.

- [P2] Bound assignments with indented H2 headings — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/hooks/check_agent_spawn.py:1587-1589
  After recognizing 1–3-space-indented FILE ASSIGNMENT headings, block extraction still stops only at the column-zero `_NEXT_H2_RE`. If the following `## TASK` is validly indented, its bullets remain inside the assignment parser, so a task-side `CAN edit` can satisfy an empty declaration or ordinary task bullets can taint a valid one.

- [P2] Remove the fallback status contradiction — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/workflows/nightly-hygiene.js:240-240
  When the fallback file is corrupt but the primary or a rotated source is usable, this instruction requires `status=skipped`, while the final rule says skipped is allowed only when no source is usable. This makes the security trigger nondeterministic and can even conflict with the monotone-red requirement when another source fires; a corrupt sibling should mark the result incomplete without overriding usable-source severity.