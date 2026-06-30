---
lesson_id: good-retry-1
archetype: staff-backend
scope_tags: [reliability, retry]
---

# Clean lesson: exponential backoff must include jitter

remember: Plain exponential backoff synchronizes retries across clients and causes thundering herds — always compose with randomized jitter (AWS "full jitter" recipe) to spread load.

Surfaced from a PLAN-005 benchmark failure on the rate-limit skill.
