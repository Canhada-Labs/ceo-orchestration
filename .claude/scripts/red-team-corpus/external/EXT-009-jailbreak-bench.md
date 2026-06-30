# EXT-009 — JailbreakBench

- **Source:** https://github.com/JailbreakBench/jailbreakbench
- **License:** MIT → compatible
- **Last retrieved:** 2026-04-16
- **Primary targets:** `output_safety_evasion`, `mcp_handler`

## Category coverage

Chao et al. (2023) "JailbreakBench" (arXiv:2404.01318). 100 harmful
behaviors + paired defense evaluators + standardized jailbreak
artifacts. Useful for output safety pipeline stress-test and future
MCP handler defense.

## Ingestion shape (stub)

```jsonl
{"id":"EXT-009-a","target":"output_safety_evasion","category":"jailbreak-bench-harmful","input":"<TBD>","expected_behavior":"MUST_SANITIZE","reference":"JailbreakBench 2023; ADR-036","severity":"HIGH"}
```

## References

- Chao et al. (2023), arXiv:2404.01318.
- ADR-036.
