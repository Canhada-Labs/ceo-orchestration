# EXT-008 — OWASP Top-10 LLM (2024)

- **Source:** https://owasp.org/www-project-top-10-for-large-language-model-applications/
- **License:** CC-BY-SA-4.0 → compatible as taxonomy reference
- **Last retrieved:** 2026-04-16
- **Primary targets:** all 8 (taxonomy reference only)

## Category coverage

OWASP LLM Top-10 v2.1 (April 2024). Mapping to our targets:

| OWASP                        | Our target(s)                                 |
|------------------------------|------------------------------------------------|
| LLM01 Prompt Injection       | `mcp_handler`, `adapter_exfil`                 |
| LLM02 Insecure Output        | `output_safety_evasion`                        |
| LLM04 Model DoS              | `mcp_handler` (rate-limit)                     |
| LLM05 Supply Chain           | `npm_tamper`                                   |
| LLM06 Sensitive Info Disc    | `adapter_exfil`, `output_safety_evasion`       |
| LLM07 Insecure Plugin Design | `mcp_handler`                                  |
| LLM08 Excessive Agency       | `sandbox_escape`                               |

LLM03/09/10 are out of scope (training data / user behavior / model
theft).

## Ingestion shape

Taxonomy-only, no payload rows. Reviewer confirms each LLM0x in scope
maps to ≥1 target.

## References

- OWASP (2024).
- ADR-031, ADR-035, ADR-036, ADR-040, ADR-042.
