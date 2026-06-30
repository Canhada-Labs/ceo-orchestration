# EXT-005 — CyberSecEval (Meta)

- **Source:** https://github.com/meta-llama/PurpleLlama/tree/main/CybersecurityBenchmarks
- **License:** Llama Community License → conditional (§1.b evaluations
  exception); CI-local only, no redistribution
- **Last retrieved:** 2026-04-16
- **Primary targets:** `sandbox_escape`, `adapter_exfil`

## Category coverage

Bhatt et al. (2024) "CyberSecEval 3". Sandbox-escape coding prompts,
credential exfil + SSRF chains, prompt-injection suite (overlaps with
EXT-001).

## License note

Llama §2 restricts commercial use >700M MAU; ceo-orchestration is
below this by orders of magnitude. Re-audit if PLAN-017 public launch
materializes.

## Ingestion shape (stub)

```jsonl
{"id":"EXT-005-a","target":"sandbox_escape","category":"exploit-assistance","input":"<TBD>","expected_behavior":"MUST_BLOCK","reference":"CyberSecEval v3 Meta 2024","severity":"HIGH"}
```

## References

- Bhatt et al. (2024), Meta research.
- ADR-040.
