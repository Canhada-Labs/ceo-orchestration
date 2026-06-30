# Common Pitfalls — Top 10 for Adopters

> PLAN-025 Batch H F-ux-012 — surfaces the most-frequently-triggered
> pitfalls from `.claude/pitfalls-catalog.yaml` into a single adopter-
> facing doc. Each pitfall has: symptom, cause, fix command.

This is a curated subset of the 16-pitfall catalog at
`.claude/pitfalls-catalog.yaml`. The CEO injects these into agent
prompts automatically when the pitfall's `whenToUse:` condition matches
the work at hand. Adopters don't need to memorize them — the framework
applies them. But seeing the top 10 helps adopters understand WHY a
Claude spawn is getting extra context.

Last updated: 2026-04-18 (Session 33 Phase D / PLAN-025 Batch H).

## 1. IPC-001 — Don't move hot-path CPU to main thread

- **Symptom:** Your backend event-loop latency spikes when you "refactor
  out" a worker computation into the main process.
- **Cause:** The main thread is ALWAYS the bottleneck in
  `worker_threads` backends. Moving CPU to main multiplies tail
  latency.
- **Fix:** `git revert` the refactor; keep CPU-bound work in workers.
  Auto-injected for agents touching IPC / worker code.

## 2. IPC-002 — Batch messages, don't send individually

- **Symptom:** Backend CPU = low, but every few hundred messages the
  main loop stalls for tens of ms.
- **Cause:** `process.send()` overhead is in the tens of ms per call.
  Message COUNT matters more than SIZE.
- **Fix:** Coalesce small messages into batches; benchmark with
  `.claude/scripts/benchmarks/replay.py`. Auto-injected for IPC agents.

## 3. SEC-001 — Literal routes BEFORE parameterized

- **Symptom:** Auth bypass on `/users/me` (or similar literal paths)
  randomly matches a different user's record.
- **Cause:** Express/Fastify match ORDER matters. `/users/:id`
  declared first will catch `/users/me` as `id=me`.
- **Fix:** Declare `/users/me` BEFORE `/users/:id` in your route
  registration. Auto-injected for security-engineer agents.

## 4. SEC-002 — Wrap async timers with safe()

- **Symptom:** Production crashes at random times with
  `UnhandledPromiseRejection` no-op in Node 20+.
- **Cause:** `setInterval(async () => { ... })` where the async
  throws has no parent to catch.
- **Fix:** Wrap with `safe()` helper: `setInterval(safe(async () =>
  { ... }))` where `safe = (fn) => (...args) => fn(...args).catch(log)`.

## 5. ARCH-001 — Don't do fix-of-fix-of-fix

- **Symptom:** You're on your third attempted fix of the same bug and
  each fix introduces a new symptom.
- **Cause:** The bug is in the design, not the code. Fix 1-3 keep
  working around an invariant violation you haven't named yet.
- **Fix:** STOP. Propose an architectural change (ADR) documenting
  the invariant. Auto-injected for VP Engineering.

## 6. ARCH-002 — Event-loop stalls are distributed, not single-op

- **Symptom:** You identified the "slow operation" causing loop lag;
  after fixing it, the lag hasn't improved much.
- **Cause:** Loop stalls aggregate across ALL hot-path operations.
  Fixing the loudest doesn't fix the tail.
- **Fix:** Reduce ALL hot-path ops simultaneously; benchmark the
  aggregate before/after.

## 7. FE-001 — CSS variable naming consistency

- **Symptom:** One theme renders but the other is invisible; no
  console error; diff shows `var(--text1)` vs `var(--text-1)`.
- **Cause:** CSS variable mismatch fails SILENTLY. No build warning.
- **Fix:** Enforce a project convention; pre-commit hook greps for
  mismatches.

## 8. FE-002 — No opacity on design-system background tokens

- **Symptom:** Dark-mode shows a "see-through" panel; light-mode is
  fine.
- **Cause:** `bg-surface/50` applied to an alpha-carrying token
  collapses to fully transparent in one theme.
- **Fix:** Use SOLID tokens for backgrounds OR explicit color mixing
  (never token + opacity modifier).

## 9. FE-003 — Backend numeric types may be strings

- **Symptom:** `price + 1` concatenates instead of adding because
  price came from an API as `"100.00"` not `100.00`.
- **Cause:** Many backend APIs serialize numerics as strings for
  precision (especially financial). TypeScript can't verify across
  network boundary.
- **Fix:** Type your DTO layer with `z.coerce.number()` or equivalent
  runtime validator at the API boundary.

## 10. FE-004 — SSE dependencies in useMemo/useEffect

- **Symptom:** Real-time panel goes stale after first few seconds;
  data sourced from `[restData, ...]` but SSE update doesn't trigger
  re-memo.
- **Cause:** SSE event handler updated a ref, but `useMemo` dep
  array didn't include the SSE source, so the merge captured stale
  closure.
- **Fix:** Include SSE source (or its version-bump counter) in
  `useMemo`/`useEffect` deps; auto-injected for Real-Time Data
  Engineer agents.

## Where the rest live

The other 6 pitfalls cover:

- `IPC-003/004/005` — setImmediate/batching correctness
- `DB-001` — PostgreSQL query patterns (see `skills/core/data-schema-design`)
- `FE-*` — additional frontend patterns
- `ARCH-003` — module boundary discipline

Read `.claude/pitfalls-catalog.yaml` for the full catalog and see
`.claude/skills/domains/<domain>/pitfalls.yaml` for domain-specific
pitfalls (e.g., fintech's 25-item pitfall catalog covers exchange
quirks + financial math).

## How pitfalls are injected into agent prompts

When the CEO spawns an agent, the helper
`.claude/scripts/inject-agent-context.sh` consults the `whenToUse:`
field of each pitfall. Matching pitfalls get prepended to the agent's
prompt as:

```
## RELEVANT PITFALLS

- IPC-001: NEVER shift hot-path CPU from worker to main thread.
- IPC-002: IPC message COUNT > SIZE. Batch small messages.
```

This ensures the agent sees the lesson BEFORE making the decision the
pitfall warns against. The agent's spawn prompt includes both the
persona + the skill + the relevant pitfalls.

## Cross-references

- `.claude/pitfalls-catalog.yaml` — full catalog (16 universal pitfalls)
- `.claude/skills/domains/<domain>/pitfalls.yaml` — domain-specific pitfalls
- `.claude/scripts/inject-agent-context.sh` — the injector
- `docs/SKILL-AUTHORING-TUTORIAL.md` §Pitfalls — how to author a new
  pitfall
- PLAN-025 Batch H F-ux-012 — originating finding
