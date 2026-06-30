---
round: 1
archetype: Staff Security Engineer
skill: security-and-auth
agent_persona: (example — populate from team.md in real runs)
generated_at: 2026-04-11T14:32:00Z
---

## Verdict

**ADJUST**

## Summary

- Moving rate limits to a shared store is a security improvement —
  the current per-instance limiter is a broken defense.
- The `fail open for 30s` decision is a **critical** security flaw
  masquerading as a pragmatic trade-off. It turns Redis outages into
  temporary auth-bypass windows.
- The key shape `rl:<route>:<user_id>` has a subtle anti-pattern for
  unauthenticated routes — what gets used when there is no user_id?
  If it's "rl:/login:anonymous", that's a single counter for every
  brute-force login attempt on the planet.

## Risks

1. **R-SEC1 — Fail-open is a temporary auth-bypass window**
   - Severity: **CRITICAL**
   - Description: The proposal says "fail open for 30s if Redis is
     unreachable". On auth-adjacent routes (password reset, MFA
     challenge, token refresh), fail-open means an attacker who can
     cause Redis unreachability (even momentarily — e.g. noisy neighbor
     at the provider) gets unlimited brute-force attempts for 30s per
     outage. Against per-password-guess primitives (bcrypt), 30s is a
     real window.
   - Mitigation: **auth-adjacent routes must fail CLOSED**, always,
     with no 30s grace. The 30s grace is acceptable only on low-stakes
     read endpoints. Split the policy per route category.

2. **R-SEC2 — Unauthenticated routes collapse into one counter**
   - Severity: HIGH
   - Description: For `/login` and `/signup`, there is no user_id.
     If the key falls back to `rl:/login:anonymous`, every attacker on
     earth shares one counter, meaning the limit trips instantly under
     any real attack and legitimate users get blocked.
   - Mitigation: For unauthenticated routes, key by **IP address +
     User-Agent hash**. Not perfect (IP can be spoofed upstream) but
     dramatically better than a shared anonymous bucket. Document that
     the IP comes from `X-Forwarded-For` only if the proxy sets it to
     a trusted single-hop value.

3. **R-SEC3 — Redis URL contains credentials**
   - Severity: MEDIUM
   - Description: `REDIS_URL` typically includes user:password.
     Adding it to env var validation at bootstrap means any log line
     that echoes env vars at startup leaks the cred. A recent CI
     incident elsewhere showed this exact leak via
     `console.log(process.env)`.
   - Mitigation: (a) Parse `REDIS_URL` once at bootstrap, pass the
     parsed object forward, never log the raw URL. (b) Add
     `REDIS_URL` to the audit-log redaction regex
     (`[a-z]+://[^\s:@/]+:[^\s@]+@[^\s]+`) — which is already there,
     good — and (c) require a bootstrap assertion that
     `process.env.REDIS_URL` is only read in the Redis client
     constructor and nowhere else.

4. **R-SEC4 — No replay protection for the counter key**
   - Severity: LOW
   - Description: An attacker with write access to Redis (via a
     separate vulnerability) could manually `DEL rl:/login:victim`
     to reset a victim's counter. Low because it requires prior
     access, but worth noting.
   - Mitigation: Redis ACLs — the app's Redis user should only have
     INCR, EXPIRE, GET, EVAL — not DEL, not CONFIG. Document this in
     the rollout plan.

## Must-fix (blocking)

1. **R-SEC1 — split fail policy per route category. Auth-adjacent
   routes fail CLOSED. This is the single most important change.**
2. **R-SEC2 — unauthenticated routes must key by IP+UA hash, not a
   shared anonymous bucket.**

## Nice-to-have

1. R-SEC3 — env var handling hygiene
2. R-SEC4 — Redis ACL scoping for the app's user

## Unseen by the original plan

1. **No mention of the Redis auth configuration.** What user does the
   app connect as? Is TLS required? Is the Redis instance public
   (internet-reachable)? These are all critical for the threat model
   but absent from the proposal.
2. **No CAPTCHA or proof-of-work fallback** for the auth routes.
   Rate limiting alone is weak against distributed attacks. The
   proposal is a necessary improvement but does not replace the
   need for a secondary defense.
3. **Rate limit bypass via double-submit cookies.** If the same user
   can hit an endpoint via two different auth flows (e.g. cookie
   session + API token), they effectively have two rate limit
   buckets. The proposal's key shape doesn't protect against this.

## What I would NOT change

- Moving to a shared store is correct and overdue.
- Accepting slight overcounting at the window boundary is fine
  (imprecision at the user's benefit, not the attacker's).
- The feature-flag rollout strategy is safer than a hard cut.
