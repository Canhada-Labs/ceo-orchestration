# EXT-013 — Log-tamper PoCs

- **Source:** Multiple public-domain CVE repos (CVE-2021-44228 follow-on
  bypass, CVE-2018-8822 utmp tampering, sysadmin PoCs)
- **License:** public domain / CVE aggregator → compatible
- **Last retrieved:** 2026-04-16
- **Primary targets:** `audit_log_tamper`

## Category coverage

Publicly-documented append-only + filelock bypass techniques:
in-place byte rewrite (SYN-005), truncation+replay (SYN-006),
lock-acquisition race (SYN-007), `chattr -a` escalation (out of scope,
needs root). Our `_lib/audit_emit.py` must resist all four classes.

## Ingestion shape (stub)

```jsonl
{"id":"EXT-013-a","target":"audit_log_tamper","category":"cve-log-tamper-pattern","input":"<CVE PoC TBD>","expected_behavior":"MUST_EMIT_AUDIT","reference":"NVD CVE-2021-44228 follow-ons; ADR-035","severity":"HIGH"}
```

## References

- NVD CVE-2021-44228.
- ADR-035.
