---
lesson_id: good-log-1
archetype: observability-engineer
scope_tags: [observability, logging]
---

# Clean lesson: redact secrets in all log sinks

remember: Run every log line through redact_secrets at the sink, not at the call site — relying on callers to remember redaction leaks secrets from any forgotten path.

Debate round 1 consensus on PLAN-003 surfaced this as H5.
