# EXT-015 — Garak (NVIDIA LLM red-team harness)

- **Source:** https://github.com/NVIDIA/garak
- **License:** Apache-2.0 → compatible
- **Last retrieved:** 2026-04-16
- **Primary targets:** all 8 (generator framework — probes produce
  artifacts dynamically)

## Category coverage

Derczynski et al. (2024) "Garak" (arXiv:2406.11036). Plugin-based
probes: malware generation, prompt injection, training-data extract,
DAN jailbreaks, encoding obfuscation (→ `output_safety_evasion`),
plugin-hijack (→ `mcp_handler`), goal-hijack (→ `adapter_exfil`).

## Ingestion shape (generator-based)

Probes run against provider-adapter test doubles in CI-local cache;
hand-pick artifacts exercising our defenses; re-serialize into JSONL.

```jsonl
{"id":"EXT-015-a","target":"mcp_handler","category":"garak-plugin-hijack","input":"<probe artifact TBD>","expected_behavior":"MUST_BLOCK","reference":"Garak Derczynski et al. 2024; ADR-042","severity":"HIGH"}
```

## References

- Derczynski et al. (2024), arXiv:2406.11036.
- ADR-036, ADR-040, ADR-042.
