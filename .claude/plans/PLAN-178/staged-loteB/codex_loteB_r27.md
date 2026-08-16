The new shared-memory reopen trigger can miss events in the framework's default audit spool path, allowing the security signal to remain falsely green for long-lived producers.

Review comment:

- [P1] Include pending audit spools in the reopen scan — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/workflows/nightly-hygiene.js:240-240
  Under the default asynchronous audit mode, `emit_pattern_stored` first writes to `state/audit-spool.<pid>.jsonl`; a long-lived process producing fewer than 100 events can leave those rows undrained until another trigger or process exit. Because this source set scans only the canonical log, rotations, and fallback, nightly can report green while a live spool already contains two distinct hashes for one topic/session. Include pending spools or force a drain before evaluating the trigger.