# EXT-010 — AdvBench (Zou et al. 2023)

- **Source:** https://github.com/llm-attacks/llm-attacks/tree/main/data
- **License:** MIT → compatible
- **Last retrieved:** 2026-04-16
- **Primary targets:** `output_safety_evasion`

## Category coverage

Companion to EXT-003 GCG. 520 harmful behaviors + 500 harmful
strings — canonical ASR benchmark for downstream defenses.

## Ingestion shape (stub)

```jsonl
{"id":"EXT-010-a","target":"output_safety_evasion","category":"advbench-harmful-behavior","input":"<row id TBD>","expected_behavior":"MUST_SANITIZE","reference":"AdvBench Zou et al. 2023; ADR-036","severity":"HIGH"}
```

## References

- Zou et al. (2023), arXiv:2307.15043.
- ADR-036.
