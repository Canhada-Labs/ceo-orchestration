---
lesson_id: good-auth-1
archetype: security-engineer
scope_tags: [security, authentication]
---

# Clean lesson: verify token expiry before cache hit

remember: Always check token expiry before returning a cached principal — stale tokens bypass the fresh auth check and silently re-authenticate revoked sessions.

Observed in a benchmark where a revoked JWT kept granting access because the cache layer did not re-validate expiry.
