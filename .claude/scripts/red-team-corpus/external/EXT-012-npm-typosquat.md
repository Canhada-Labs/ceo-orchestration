# EXT-012 — NPM Typosquatting (Socket)

- **Source:** https://socket.dev/blog
- **License:** research-only (Socket data); CC-BY-4.0 blogs with
  attribution. CI-local ingestion only, never commit payloads.
- **Last retrieved:** 2026-04-16
- **Primary targets:** `npm_tamper`

## Category coverage

Continuous feed of malicious NPM packages — typosquats (`express-cors`
vs `cors-express`), dependency-confusion, post-install payloads.

## Ingestion shape (stub)

```jsonl
{"id":"EXT-012-a","target":"npm_tamper","category":"socket-typosquat-pattern","input":"<Socket advisory id TBD>","expected_behavior":"MUST_BLOCK","reference":"Socket NPM advisory feed; PLAN-013 Phase E.7","severity":"HIGH"}
```

## References

- Socket Inc. research blog.
- PLAN-013 Phase E.7.
