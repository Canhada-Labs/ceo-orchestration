The new fail-closed assignment grammar can be bypassed through an allowed prose prefix, leaving undeclared edit authority outside overlap telemetry. The canonical generator also accepts Unicode-whitespace inputs that its corresponding hook rejects.

Full review comments:

- [P1] Reject edit grants hidden in allowed prose — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/hooks/check_agent_spawn.py:1630-1633
  When enforcement is enabled, a block containing a valid grant plus `- MAY read docs; MUST edit hidden.py` is classified as concrete because the allowed-prose prefix matches and this check only searches for the literal `can edit`. The hidden path is therefore neither rejected by the new grammar gate nor included in overlap telemetry; reject any edit-grant suffix rather than only `can edit`.

- [P2] Reject all whitespace accepted by `--files` — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/scripts/inject-agent-context.sh:1161-1162
  When a `--files` segment contains non-ASCII whitespace such as U+00A0, this case only detects an ASCII space while `_classify_file_assignment()` rejects every character for which `str.isspace()` is true. The injector consequently exits successfully and emits a prompt that becomes `unparseable` and is blocked once enforcement is enabled, contrary to its conformant-output guarantee.