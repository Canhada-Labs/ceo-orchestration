The multi-plan budget rollup excludes the actual event shape, and the new shared-memory reopen detector misses default compact JSON and rotated audit data. These defects leave both intended safeguards ineffective in production scenarios.

Full review comments:

- [P1] Keep real spawn rows in multi-plan budget rollups — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/hooks/check_budget.py:945-945
  When two or more plans are active, this enables strict attribution, but the live `agent_spawn` producer in `.claude/hooks/audit_log.py:640` does not emit a `plan_id`. Consequently `_plan_tokens_total` skips every real spawn row, returns zero usage, and no budget warning can fire in the multi-plan state this change intends to cure.

- [P1] Parse pattern events independently of JSON spacing — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/workflows/nightly-hygiene.js:220-220
  Under the default asynchronous audit path, `.claude/hooks/_lib/spool_writer.py:1936` serializes events with compact separators, producing `"action":"pattern_stored"`. This exact-space grep therefore selects no rows, so even a qualifying pair of stored patterns is reported green and the reopen trigger remains inert.

- [P1] Include rotated logs in the 24-hour trigger window — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/workflows/nightly-hygiene.js:220-220
  When the audit log rotates during the requested 24-hour window, this reads only the active `audit-log.jsonl`, while prior events are moved to `audit-log-YYYY-MM*.jsonl` at the 10 MiB threshold. Triggering events that are archived, or split across the archive and active file, are therefore omitted and can produce a false green result.