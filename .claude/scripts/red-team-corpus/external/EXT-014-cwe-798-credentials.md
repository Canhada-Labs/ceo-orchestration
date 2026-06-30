# EXT-014 — CWE-798 (hardcoded credentials)

- **Source:** https://cwe.mitre.org/data/definitions/798.html
- **License:** MITRE public → compatible
- **Last retrieved:** 2026-04-16
- **Primary targets:** `adapter_exfil`

## Category coverage

Parent taxonomy for credential-in-source patterns. Applicable classes:
error-message echo (SYN-017), OTEL span attr echo (SYN-018), retry-
storm debug-log (SYN-019). Out of framework scope: `.env` committed
to git (target pre-commit hooks); shell history (user behavior).

## Ingestion shape (stub)

```jsonl
{"id":"EXT-014-a","target":"adapter_exfil","category":"cwe-798-echo","input":"<pattern TBD>","expected_behavior":"MUST_SANITIZE","reference":"CWE-798 MITRE; ADR-040","severity":"CRITICAL"}
```

## References

- MITRE CWE-798.
- ADR-040.
