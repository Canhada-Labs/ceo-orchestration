The new canonical injector rejects ordinary hyphenated paths, blocking a common supported input. The patch also leaves the required operating contract inconsistent with the implementation it declares landed.

Full review comments:

- [P1] Accept hyphens in concrete file paths — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/scripts/inject-agent-context.sh:1091-1095
  When `--files` contains a normal hyphenated path such as `src/foo-bar.py`, this bracket expression also matches the literal `-`, so the injector reports control characters and exits 2. Hyphens are common in repository paths, making the new canonical file-assignment path unusable for valid inputs; the control-character check should avoid treating the range separators as characters to reject.

- [P2] Close out the spawn contract in CLAUDE.md — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/plans/PLAN-178-mast-audit-substrate-adoption.md:238-241
  This patch records Lote B and ADR-191 as landed but explicitly leaves the mandatory operating-contract rewrite pending. Every session must read `CLAUDE.md`, whose line 88 still says omission hides the spawn from collision detection and calls ADR-191 a draft, contradicting the new `path_count=0` telemetry and accepted ADR; update that canonical contract in this change rather than landing the acknowledged stale state.