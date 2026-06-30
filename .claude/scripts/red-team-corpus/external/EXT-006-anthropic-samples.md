# EXT-006 — Anthropic public jailbreak samples

- **Source:** https://www.anthropic.com/research (papers + disclosure
  blog posts)
- **License:** Apache-2.0-like for published examples (review
  per-sample); public domain for responsible-disclosure references
- **Last retrieved:** 2026-04-16
- **Primary targets:** `output_safety_evasion`

## Category coverage

Anil et al. (2024) "Many-shot Jailbreaking" + Bai et al. (2022)
"Constitutional AI" (arXiv:2212.08073). Many-shot evasion via benign
few-shot examples flipping final behavior; base-rate of
production-adversarial patterns.

## Ingestion shape (stub)

```jsonl
{"id":"EXT-006-a","target":"output_safety_evasion","category":"many-shot-evasion","input":"<TBD>","expected_behavior":"MUST_SANITIZE","reference":"Anthropic many-shot 2024; ADR-036","severity":"MEDIUM"}
```

## References

- Anil et al. (2024). Bai et al. (2022).
- ADR-036.
