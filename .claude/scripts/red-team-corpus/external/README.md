# External Adversarial Corpus — Pointer Documents

**Scope:** PLAN-013 Phase D.7 (≥15 external public adversarial
datasets, license-permitting). Defeats training-blindspot in
synthetic-only corpora (consensus §C9 CRITICAL).

**Policy:** We DO NOT mirror binary data from external datasets.
Each pointer file below documents:

1. Dataset name + source URL
2. License + compatibility assessment with PLAN-013 anti-goals
3. Last retrieved date (ISO-8601)
4. Category coverage (which of 8 targets the dataset exercises)
5. A short stub fixture illustrating the pattern type (in the
   same JSONL schema as `synthetic/`) that a reviewer could
   validate against the real dataset if license permits.

**Fixture id convention:** `EXT-NNN` for pointer docs.

## Index (15 entries)

| #   | Dataset                             | Primary targets                             | License          | File                               |
|-----|-------------------------------------|---------------------------------------------|------------------|------------------------------------|
| 01  | PromptInject                        | `mcp_handler`, `adapter_exfil`              | MIT              | `EXT-001-prompt-inject.md`         |
| 02  | HackAPrompt corpus                  | `skill_patch_sentinel`, `output_safety_evasion` | CC-BY-4.0   | `EXT-002-hackaprompt.md`           |
| 03  | GCG (Greedy Coordinate Gradient)    | `adapter_exfil`, `output_safety_evasion`    | MIT              | `EXT-003-gcg.md`                   |
| 04  | TAP (Tree of Attacks with Pruning)  | `mcp_handler`, `adapter_exfil`              | MIT              | `EXT-004-tap.md`                   |
| 05  | CyberSecEval (Meta)                 | `sandbox_escape`, `adapter_exfil`           | Llama Community  | `EXT-005-cybersecurity-eval.md`    |
| 06  | Anthropic public jailbreak samples  | `output_safety_evasion`                     | Apache-2.0-like  | `EXT-006-anthropic-samples.md`     |
| 07  | Trojan Source (CVE-2021-42574 PoC)  | `skill_patch_sentinel`                      | Public domain    | `EXT-007-trojan-source.md`         |
| 08  | OWASP Top-10 LLM (2024)             | all 8 targets (taxonomy reference)          | Creative Commons | `EXT-008-owasp-llm-top10.md`       |
| 09  | JailbreakBench                      | `output_safety_evasion`, `mcp_handler`      | MIT              | `EXT-009-jailbreak-bench.md`       |
| 10  | AdvBench (Zou et al. 2023)          | `output_safety_evasion`                     | MIT              | `EXT-010-advbench.md`              |
| 11  | MITRE ATLAS                         | `adapter_exfil`, `sandbox_escape` (taxonomy)| Apache-2.0       | `EXT-011-mitre-atlas.md`           |
| 12  | NPM Typosquatting dataset (Socket)  | `npm_tamper`                                | research-only    | `EXT-012-npm-typosquat.md`         |
| 13  | log4shell + audit tamper PoCs       | `audit_log_tamper`                          | public domain    | `EXT-013-log-tamper-poc.md`        |
| 14  | CWE-798 (hardcoded credentials)     | `adapter_exfil`                             | MITRE public     | `EXT-014-cwe-798-credentials.md`   |
| 15  | Garak (NVIDIA LLM red-team harness) | all 8 targets (taxonomy + generator)        | Apache-2.0       | `EXT-015-garak.md`                 |

## Ingestion protocol

(1) Fetch dataset via pointer URL (never committed). (2) Re-verify
license at fetch. (3) Hand-pick subset matching category coverage.
(4) Re-serialize into JSONL under local non-committed
`external/cache/`. (5) `red-team-eval.py --fixture-dir external/cache`
runs adversarial inputs. (6) Cache NEVER committed.

Phase D.5 ships pointer docs only; live-ingestion is Phase D.6 future
work.

## License compatibility

- **MIT / Apache-2.0 / CC-BY-4.0 / public domain** → permitted, with
  attribution when required
- **Llama Community License** → conditional (§1.b evaluations exception);
  CI-local only; re-audit if commercial use emerges
- **research-only** → CI-local only, never commit
- **unknown / proprietary** → skip

## References

- PLAN-013 Phase D.7 + consensus §C9.
- `../README.md`, `../.byte-identity-check.txt`.
