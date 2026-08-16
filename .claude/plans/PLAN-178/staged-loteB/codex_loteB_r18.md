The new enforcement path conflicts with a canonical prompt template, and the generator can emit assignments that the hook itself rejects for edge-case inputs. These should be reconciled before the patch is considered correct.

Full review comments:

- [P2] Update the canonical template before enabling the gate — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/hooks/check_agent_spawn.py:1964-1966
  When `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED=1`, the canonical prompt template in `.claude/team.md:686-688` still emits `- MAY edit: ...`; this classifier recognizes only `CAN edit:` lines, so following the repository's standard template now produces `fa_state=unparseable` and blocks every named spawn. Update that template to the new grammar before exposing this enforcement path.

- [P3] Reject DEL in `--files` values — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/scripts/inject-agent-context.sh:1092-1094
  If a caller supplies a path containing ASCII DEL (`\x7f`), this control-character guard accepts and emits it, while `_classify_file_assignment()` explicitly marks DEL-bearing paths unparseable. With `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED=1`, the canonical generator therefore produces a prompt that the hook immediately rejects, contrary to its conformance guarantee.

- [P3] Normalize backtick-wrapped tokens before validation — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/scripts/inject-agent-context.sh:1110-1112
  When `--files` contains a literal backtick-wrapped placeholder such as `` `none` `` or `` `./` ``, this raw-token check accepts it and emits a concrete assignment, but the hook strips surrounding backticks before validation and classifies the result as unparseable. Validate the same normalized token the hook sees so generated prompts remain valid under enforcement.