# EXT-004 — TAP (Tree of Attacks with Pruning)

- **Source:** https://github.com/RICommunity/TAP
- **License:** MIT → compatible
- **Last retrieved:** 2026-04-16
- **Primary targets:** `mcp_handler`, `adapter_exfil`

## Category coverage

Mehrotra et al. (2023), "Tree of Attacks" (arXiv:2312.02119).
Tree-search attack refining jailbreak prompts. Useful for MCP handler
robustness + adapter breaker behavior under adversarial retries.

## Ingestion shape (stub)

```jsonl
{"id":"EXT-004-a","target":"mcp_handler","category":"tap-tree-jailbreak","input":"<TBD>","expected_behavior":"MUST_BLOCK","reference":"TAP Mehrotra et al. 2023; ADR-042","severity":"HIGH"}
```

## References

- Mehrotra et al. (2023), arXiv:2312.02119.
- ADR-042.
