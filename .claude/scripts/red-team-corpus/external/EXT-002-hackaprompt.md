# EXT-002 — HackAPrompt corpus

- **Source:** https://huggingface.co/datasets/hackaprompt/hackaprompt-dataset
- **License:** CC-BY-4.0 → compatible with attribution
- **Last retrieved:** 2026-04-16
- **Primary targets:** `skill_patch_sentinel`, `output_safety_evasion`

## Category coverage

~600k competitive prompt attacks (Schulhoff et al. 2023, "Ignore
This Title and HackAPrompt", EMNLP Findings, arXiv:2311.16119).
Covers: instruction override, Unicode trickery (overlaps Trojan
Source), base64/ROT-13/hex encoding evasion, few-shot payload
smuggling.

## Ingestion shape (stub)

```jsonl
{"id":"EXT-002-a","target":"output_safety_evasion","category":"encoding-evasion","input":"<hackaprompt row id TBD>","expected_behavior":"MUST_SANITIZE","reference":"HackAPrompt Schulhoff et al. 2023; ADR-036","severity":"HIGH"}
```

## References

- Schulhoff et al. (2023), EMNLP Findings.
- ADR-036.
