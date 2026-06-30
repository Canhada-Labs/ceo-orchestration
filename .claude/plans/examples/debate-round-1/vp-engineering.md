---
round: 1
archetype: VP Engineering
skill: architecture-decisions
agent_persona: (example — populate from team.md in real runs)
generated_at: 2026-04-11T14:30:00Z
---

## Verdict

**ADJUST**

## Summary

- Moving rate limit state out of per-instance memory is correct; the
  current implementation is broken for horizontally-scaled deployments.
- The `INCR + EXPIRE` pattern is fine for a single Redis shard but the
  proposal glosses over the race condition on window boundary.
- The fail-open → fail-closed transition is untested in the proposal
  and is the single most likely place for an outage to convert into an
  incident.

## Risks

1. **R-VP1 — INCR+EXPIRE race on first request in a new window**
   - Severity: MEDIUM
   - Description: Between `INCR` (which returns 1 if key is new) and
     `EXPIRE`, the key has no TTL. If the process crashes between
     the two commands, the key stays forever and all future requests
     count toward the same "window" until manual cleanup.
   - Mitigation: Use a Lua script (`SCRIPT LOAD` once, `EVALSHA` per
     call) that runs `INCR` + `EXPIRE` atomically. Redis single-command
     atomicity applies to the script.

2. **R-VP2 — No sharding strategy for high-cardinality routes**
   - Severity: MEDIUM
   - Description: `rl:<route>:<user_id>` is fine while the user count
     is low, but at 10x scale a single Redis shard carries every
     rate-limit key. When we outgrow one shard, re-sharding is
     painful without consistent hashing.
   - Mitigation: Document the re-sharding path now (move keys to
     Redis Cluster with hash tag `{user_id}` so all of a user's rate
     limits land on the same shard). No code change today, but the
     key shape already has to accommodate it.

3. **R-VP3 — 30-second fail-open window is a magic number**
   - Severity: HIGH
   - Description: "Fail open for 30s then fail closed" mixes two
     different failure philosophies and has no tests. What if Redis
     flaps every 20s? The limiter never flips to closed, and attackers
     get unlimited traffic.
   - Mitigation: Replace with a clear state machine: (a) healthy,
     (b) degraded = fail-open with explicit metric + alert, (c) down =
     fail-closed after 3 consecutive INCR failures. Test the transitions.

4. **R-VP4 — No ADR**
   - Severity: MEDIUM
   - Description: This is an L3 architectural change. It replaces a
     mechanism. The proposal mentions decisions inline but doesn't
     capture the trade-offs in an ADR. Future maintainers won't know
     why we chose Redis over Memcached, sticky sessions, or a rate
     limit header enforced by the LB.
   - Mitigation: Write `.claude/adr/ADR-NNN-rate-limit-backend.md`
     with the 3 options considered, chosen one, and consequences.

5. **R-VP5 — Bootstrap env var validation is missing a recovery path**
   - Severity: LOW
   - Description: Adding `REDIS_URL` to required env vars means an
     existing deploy without the var crashes on start. The proposal
     says "document the rollback" but doesn't describe what happens
     during the upgrade window.
   - Mitigation: Make `REDIS_URL` optional during the feature-flag
     rollout (flag = `memory` → Redis client is not instantiated).
     Only validate it as required when flag = `redis`.

## Must-fix (blocking)

1. Resolve R-VP1 by using an atomic Lua script for INCR+EXPIRE
2. Resolve R-VP3 by specifying the fail-open → fail-closed state
   machine + tests
3. Write an ADR capturing the trade-offs

## Nice-to-have

1. R-VP2 re-sharding documentation
2. R-VP5 graceful env var validation during the rollout window

## Unseen by the original plan

1. **Key expiration storm on Redis restart.** If Redis restarts, all
   TTLs are reset, and every user effectively gets a fresh window.
   Depending on the threshold, this is either "harmless" or "burst of
   3x normal traffic for 1 minute after every Redis restart".
2. **Clock skew between app instances.** Sliding window math assumes
   `Date.now()` is consistent. NTP drift of ±250ms is common; if your
   window is 1 minute, that's 0.4% error — fine. If you later tighten
   to 10 seconds, it's 2.5% — matters for high-precision limits.
3. **Observability: no metric for "rate limit hit rate per route".**
   Without this, you can't tell whether limits are working, and the
   feature-flag flip to `redis` has no before/after comparison.

## What I would NOT change

- The feature-flag deploy strategy is correct. Ship the code, flip the
  flag later. This is the right pattern for a backend swap.
- Keeping the in-memory version in the codebase for one sprint as the
  rollback path is a good call.
- The decision to accept slight overcounting at window boundaries
  (sliding-window-light) in exchange for simplicity is fine — a full
  sliding window with sorted sets adds 3x cost for marginal precision.
