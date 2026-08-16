The patch exposes unfenced shared-memory content while also breaking the published query contract. It additionally leaves council ingress unfenced and can return incorrect paid-evaluation accounting after truncation.

Full review comments:

- [P1] Keep raw memory content out of default query results — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/hooks/_lib/memory_shared.py:503-507
  When a caller serializes the complete result of `query()` into an agent prompt, the new `content_raw` field includes the attacker-controlled stored body without the fence, directly restoring the prompt-injection path this change is intended to close. Raw access should require a separate explicit tooling API rather than appearing in every default query result.

- [P1] Preserve the published query content contract — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/hooks/_lib/memory_shared.py:499-502
  Existing API consumers that parse `content` as the stored pattern or verify `content_hash` against it now receive fence markers and a different hash input. Adding `content_raw` does not preserve unmodified callers, while `SPEC/v1/memory-shared.schema.md` publishes `content` in the return shape and forbids semantic changes within v1; this needs a versioned API or another backward-compatible migration.

- [P1] Apply the new fence to council return values — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/workflows/council-audit.js:147-152
  `fenceUntrusted` is never called in this workflow: lane findings, verifier output, and unavailable reasons are still interpolated directly into the verify/reduce prompts. Consequently a hostile lane or refuter return bypasses the anti-spoof fence, and synthesis truncation remains silent despite ADR-191 requiring fenced, capped ingress with explicit degradation.

- [P2] Recompute reconciliation after row-ingest truncation — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/1916b9c8-0ae5-43db-b462-179c4c6cfd18/scratchpad/loteB-work/.claude/workflows/eval-baseline-n20.js:473-476
  When unbounded row strings make `rowsFence.truncated` true, the reconciler sees only a prefix of the rows, but its `n`, histogram, pass count, and `total_cost_usd` are still accepted unchanged; appending an anomaly does not prevent incorrect accounting from being returned. Since the complete `rows` array remains available locally, this path should use the same mechanical derivation as the null-reconciler fallback.