The patch leaves a FILE ASSIGNMENT bypass in the canonical generated-prompt flow, introduces contradictory workflow instructions, and adds an amendment that fails the repository's lineage checker. These issues should be resolved before the patch is considered correct.

Full review comments:

- [P1] Reject invalid blocks even after a read-only declaration — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/hooks/check_agent_spawn.py:1758-1761
  When the generator emits `NONE-READ-ONLY` and a caller later appends `- CAN edit: src/**`, this branch drops the wildcard and the classifier returns `readonly`. The malformed assignment therefore passes `CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED=1` and records no writable paths, while the agent still sees a wildcard grant. Track invalid tokens/blocks and classify the whole declaration as unparseable rather than letting an earlier read-only token hide them.

- [P2] Authorize seed files in the eval transport exception — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/workflows/eval-baseline-n20.js:245-247
  Every normal eval task copies the corpus seed into `/tmp` in step 2 and the subject model then inspects those files, but this new rule says the only authorized movement of corpus contents is the frozen prompt from steps 3–4. A policy-following batch runner can refuse the seed copy or subject access, voiding the paid evaluation cells. The exception needs to include seed staging and subject access explicitly.

- [P2] Resolve the fallback parse-failure status conflict — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/workflows/nightly-hygiene.js:220-223
  When the fallback audit sink exists but cannot be parsed, step 1 requires `status=yellow`, while the final rule says this dimension is never yellow. Both values are schema-valid, so the agent can choose either and produce inconsistent nightly severity for the same infrastructure failure. Define one degraded status consistently.

- [P2] Declare ADR-089 as the amendment target — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/adr/ADR-089-AMEND-1-shared-memory-reopen-trigger-and-query-fence.md:10-12
  This filename is an `ADR-NNN-AMEND-K` record, but its frontmatter has no `amends:` target. `python3 .claude/scripts/check-adr-chain.py` consequently reports this new file as broken lineage; add `amends: ADR-089` so the amendment chain is machine-verifiable.