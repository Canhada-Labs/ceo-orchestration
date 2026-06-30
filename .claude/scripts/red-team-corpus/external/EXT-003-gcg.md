# EXT-003 — GCG (Greedy Coordinate Gradient)

- **Source:** https://github.com/llm-attacks/llm-attacks
- **License:** MIT → compatible
- **Last retrieved:** 2026-04-16
- **Primary targets:** `adapter_exfil`, `output_safety_evasion`

## Category coverage

Zou et al. (2023), "Universal and Transferable Adversarial Attacks
on Aligned Language Models" (arXiv:2307.15043). Optimized adversarial
suffixes that transfer across aligned LLMs. Useful for live-adapter
boundary sanitization + output safety pipeline (GCG suffixes produce
high-entropy tokens).

## Safety note

GCG suffixes are ADVERSARIAL. Reviewers keep suffixes in local
non-committed cache; never verbatim in committed fixtures (byte-
identity pin + PLAN-013 anti-goal #3 = public-repo risk).

## Ingestion shape (stub)

```jsonl
{"id":"EXT-003-a","target":"adapter_exfil","category":"gcg-universal-suffix","input":"<GCG suffix TBD>","expected_behavior":"MUST_SANITIZE","reference":"GCG Zou et al. 2023; ADR-040","severity":"CRITICAL"}
```

## References

- Zou et al. (2023), arXiv:2307.15043.
- ADR-040.
