---
plan: example
round: 1
created_at: 2026-04-11T14:00:00Z
archetypes_invited: [vp-engineering, security-engineer, devops-engineer]
---

# Proposal — Move rate limiting from per-instance memory to Redis

> This is a **fixture** demonstrating the debate-round-1 structure. It
> lives under `.claude/plans/examples/` because the plan namespace
> (`PLAN-<NNN>-<slug>.md`) is reserved for real plans. The content is
> synthesized for teaching purposes and does not reference any real
> project.

## Thesis

The current rate limiter lives in each app instance's in-memory map
(`Map<string, {count, resetAt}>`). This worked when we had one
instance. Now we have 3 instances behind a load balancer, and users
are hitting the cap at 1/3 the documented threshold because each
instance only sees its share of requests.

The proposal: move the rate limit state to Redis using the
`INCR + EXPIRE` pattern with a sliding 1-minute window.

## Scope

- Add `ioredis` dependency
- New module `src/infra/rate-limit.ts` with `checkAndIncrement(key, limit, windowSec)`
- Refactor all 4 rate-limited routes to call the new module
- Remove the in-memory map
- Add `REDIS_URL` to the bootstrap env var validation
- Document the rollback path (revert commit; the in-memory version is
  behind a feature flag for 1 sprint)

## Decisions (defaults)

- **Sliding window:** `INCR` the key, set `EXPIRE` on the first hit of
  a new window, return `count > limit`. Accepts slight overcounting at
  window boundaries as a trade-off for simplicity.
- **Key shape:** `rl:<route>:<user_id>`. Flat namespace, no per-tenant
  sharding.
- **Failure mode:** if Redis is unreachable, **fail open** (allow the
  request) for 30 seconds then **fail closed** (return 503) until
  Redis is back. Rationale: a Redis outage shouldn't take down the API,
  but an extended outage shouldn't let attackers bypass limits forever.
- **Deploy order:** ship the code with a feature flag `RATE_LIMIT_BACKEND`
  default `memory`, flip to `redis` in a separate commit after the new
  Redis instance is provisioned. Rollback is a flag flip.
- **Testing:** unit tests with a fake Redis client (`ioredis-mock`),
  integration tests against a real Redis on CI.

## Open questions

1. Should the window be per-user or per-IP? (Currently per-user, but
   unauthenticated routes have no user ID.)
2. Do we need Lua scripts for atomicity, or is `INCR + EXPIRE` enough
   given a single-shard Redis?
3. How do we handle the Redis client reconnect storm during failover?
4. Is there a monitoring plan for "rate limit hit rate" as a metric?

## Blast radius

L3 — new dependency, new infrastructure component, 4 route changes,
bootstrap env validation, deployment procedure change.
