# EXT-011 — MITRE ATLAS

- **Source:** https://atlas.mitre.org/ +
  https://github.com/mitre-atlas/atlas-data
- **License:** Apache-2.0 (atlas-data) + MITRE public → compatible
- **Last retrieved:** 2026-04-16
- **Primary targets:** `adapter_exfil`, `sandbox_escape` (taxonomy
  mapping only)

## Category coverage

ATT&CK-style knowledge base for AI/ML. Tactic mapping:
Reconnaissance → `mcp_handler` ACL enum; Initial Access →
`sandbox_escape`; Exfiltration → `adapter_exfil`; Impact →
`audit_log_tamper`.

## Ingestion shape

Taxonomy-only. Reviewers cross-reference ATLAS tactic IDs (e.g.
`AML.TA0007 Exfiltration`) in fixture `notes` field.

## References

- MITRE ATLAS (2024).
- ADR-035, ADR-040, ADR-042.
