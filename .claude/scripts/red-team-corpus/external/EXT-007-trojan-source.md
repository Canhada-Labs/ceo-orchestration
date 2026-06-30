# EXT-007 — Trojan Source (CVE-2021-42574)

- **Source:** https://trojansource.codes/ (Boucher & Anderson 2021,
  arXiv:2111.00169)
- **License:** public domain / CC-BY-4.0 or MIT (paper PoC code)
- **Last retrieved:** 2026-04-16
- **Primary targets:** `skill_patch_sentinel`

## Category coverage

Demonstrates bidirectional Unicode controls (U+202E RLO, etc.)
smuggling code past reviewers. Directly maps to ADR-031 §10-point
mitigation. SYN-001 covers the same pattern synthetically; EXT-007
serves as external ground truth for regression detection.

## Ingestion shape (stub)

```jsonl
{"id":"EXT-007-a","target":"skill_patch_sentinel","category":"trojan-source-bidi","input":"<paper Fig. 2 PoC TBD>","expected_behavior":"MUST_BLOCK","reference":"CVE-2021-42574; ADR-031","severity":"CRITICAL"}
```

## References

- Boucher & Anderson (2021), arXiv:2111.00169.
- CVE-2021-42574.
- ADR-031.
