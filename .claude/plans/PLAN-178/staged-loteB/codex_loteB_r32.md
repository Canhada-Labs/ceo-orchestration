The new FILE ASSIGNMENT security contract has multiple parser differentials that allow visible write grants to bypass enforcement and overlap telemetry. The canonical generator also accepts inputs that its paired hook rejects.

Full review comments:

- [P1] Taint Markdown-equivalent assignment headers — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/hooks/check_agent_spawn.py:1767-1769
  When the injector's read-only block is followed by an appended `## File Assignment` block, or by a valid heading indented 1–3 spaces, this exact column-zero uppercase search ignores the later grant. The classifier consequently returns `readonly`, so `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED=1` accepts the spawn and overlap telemetry omits paths the agent can see; recognize or fail-close on these visible header variants.

- [P1] Taint legacy grants using every valid list marker — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/hooks/check_agent_spawn.py:1605-1607
  With a valid `- CAN edit: safe.py` line, an additional `+ MAY edit: hidden.py` or `1. MAY edit: hidden.py` is visible write authority but matches neither this `[-*]` regex nor the numbered-CAN-only regex. The declaration therefore remains `concrete`, allowing enforcement to pass while telemetry hashes only `safe.py`; include `+` and numbered markers for these legacy positive verbs.

- [P1] Reject all whitespace in concrete grant tokens — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/hooks/check_agent_spawn.py:1822-1828
  A grant such as `CAN edit: all files` using U+00A0 displays as the prohibited broad prose “all files,” but the literal ASCII-space check and subsequent control-character check both miss it, so the classifier accepts and hashes it as one concrete path. Under the required gate this is a parser differential that hides broad authority; reject internal Unicode whitespace as well.

- [P2] Validate --files against the full hook grammar — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/scripts/inject-agent-context.sh:1125-1134
  When `--files` contains an internal space, a literal `$` expansion such as `$HOME/x.py`, or more than 64 paths, this validation counts it as concrete and emits a prompt that `_classify_file_assignment` marks unparseable. The canonical generator therefore produces would-block telemetry now and will be rejected when enforcement is enabled; mirror the hook's no-space/no-`$` and path-count constraints here.