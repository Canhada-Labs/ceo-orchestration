# EXT-001 — PromptInject

- **Source:** https://github.com/agencyenterprise/PromptInject
- **License:** MIT → compatible; CI-local ingestion only
- **Last retrieved:** 2026-04-16
- **Primary targets:** `mcp_handler`, `adapter_exfil`

## Category coverage

PromptInject (Perez & Ribeiro, NeurIPS ML Safety Workshop 2022,
"Ignore Previous Prompt") formalizes goal-hijacking + prompt-leaking
attacks. Subsets useful here: goal-hijack overriding system-instructed
handler ACL; prompt-leak for `adapter_exfil`.

## Ingestion shape (stub — payload filled after local fetch)

```jsonl
{"id":"EXT-001-a","target":"mcp_handler","category":"goal-hijack-acl","input":"<TBD>","expected_behavior":"MUST_BLOCK","reference":"PromptInject Perez & Ribeiro 2022; ADR-042","severity":"HIGH"}
```

## References

- Perez & Ribeiro (2022), NeurIPS ML Safety Workshop.
- ADR-040, ADR-042.
