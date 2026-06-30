# EXT-011 — MITRE ATLAS technique-ID coverage matrix

> **Status:** Wave G.1a (docs + fixtures + scripts) — `atlas_technique`
> wire-up to `.claude/hooks/_lib/audit_emit.py` is **Wave G.1b**
> (SERIAL after Wave E.4; PLAN-085 §8 dispatch order).
>
> **Last refreshed:** 2026-05-12 (PLAN-085 Wave G.1a)
> **Upstream source:** [MITRE ATLAS v4.5](https://atlas.mitre.org/) +
> [atlas-data](https://github.com/mitre-atlas/atlas-data)
> **License:** Apache-2.0 (atlas-data) + MITRE public — compatible.

## 1. Scope and contract

The framework's detection layer (audit-log emitters + scan families +
egress redactors) is being progressively tagged with **MITRE ATLAS
technique IDs** under the optional `atlas_technique` payload field
on `audit_emit.py` events. The contract:

- **Closed enum.** Tags MUST come from canonical ATLAS technique IDs
  (`AML.TNNNN` or `AML.TNNNN.NNN` sub-techniques). The framework does
  NOT mint custom IDs.
- **Optional but stable.** The field is nullable; once set on a
  specific action, the mapping is immutable for that minor version
  to preserve longitudinal analytics.
- **Auditable via `audit-query.py`.** Wave G.1b adds the
  `--atlas-technique <id>` filter; until then, query manually via
  `jq '. | select(.atlas_technique == "AML.T0051")'`.

## 2. v1.19.0 — seeded mappings (5 — COVERED tier, pending G.1b production wire)

The first 5 mappings are **seeded** in Wave G.1a (PLAN-085 §4 R-045
partial). **G.1b production wire-up — adding the `atlas_technique`
field to `_KNOWN_ACTIONS` + 5 emit callsites in `audit_emit.py` — is
DEFERRED to the next session per PLAN-085 §8 dispatch order
(SERIAL after Wave E.4).** Source of truth post-G.1b: this section +
`audit_emit.py` `_KNOWN_ACTIONS` registry + fixture pairs under
`tests/fixtures/atlas/`. Until G.1b lands, the
`tests/test_atlas_technique_id_tagging.py` `fires_on_positive`
assertions are marked `@unittest.expectedFailure` (Codex R2 iter-1
P1:F fold) — the milestone landing flips them to "unexpected pass"
which surfaces in CI.

| Audit action | ATLAS technique | Confidence | Fixture pair |
|---|---|---|---|
| `prompt_injection_detected` | **AML.T0051** — LLM Prompt Injection | HIGH | `AML-T0051-{should-fire,should-not-fire}.ndjson` |
| `secret_leak_detected` | **AML.T0024.001** — Exfiltration via Model Inversion → LLM Data Leakage<br><sub>**OWASP 2024 LLM06 / 2025 LLM02 retag** (PLAN-095 Wave A — Sensitive Information Disclosure renumbered; semantic preserved)</sub> | HIGH | `AML-T0024-{should-fire,should-not-fire}.ndjson` + `AML-T0024-LLM02-2025-{should-fire,should-not-fire}.ndjson` (PLAN-095 retag fixture pair) |
| `pii_redacted_outgoing` | **AML.T0048.004** — Erode ML Model Integrity: User-injected Information | MEDIUM | `AML-T0048-{should-fire,should-not-fire}.ndjson` |
| `live_adapter_blocked` | **AML.T0049** — Exploit Public-Facing Application | HIGH | `AML-T0049-{should-fire,should-not-fire}.ndjson` |
| `codex_egress_redacted` | **AML.T0054** — LLM Jailbreak | HIGH | `AML-T0054-{should-fire,should-not-fire}.ndjson` |

## 2.1. PLAN-095 Wave B cross-link — OWASP LLM03:2025 Supply Chain (S128)

The OWASP **LLM03:2025 Supply Chain** detection rule ships in
`_lib/output_scan.py::_LLM_PATTERN_GROUPS` as the `LLM03_2025_supply_chain`
family (PLAN-095 Wave B; `_FAMILY_COUNT` raised 9 → 10). This rule is a
**family-level concern over output payloads** (dependency installs,
unverified MCP servers, fetch operations without checksum, untrusted
package indexes) — it is NOT bound to a single technique-ID row in the
ATLAS registry above. The cross-link is intentional:

- Detection lives in: `_lib/output_scan.py::_LLM_PATTERN_GROUPS["LLM03_2025_supply_chain"]`
- Audit emit family: `output_scan_finding` with `family="LLM03_2025_supply_chain"`
- Alert dedup: `output_scan_finding_suppressed` (24h TTL per `(repo_path_hash, command_sha, pattern_id)`)
- Kill-switch: `CEO_OUTPUT_SCAN_LLM03=0` (matches existing per-family pattern)
- Supplement: `.claude/plans/PLAN-086/llm03-supplement.md` (OWASP 2025 wording + 5-field source pin)
- Hunting playbook: `docs/hunting/llm03-supply-chain.md`
- FPR/TPR gate: `python3 .claude/scripts/check_atlas_fpr.py --pattern-class LLM03_2025_supply_chain --corpus tests/fixtures/red-team-corpus/ --threshold 0.15 --min-tpr 0.80`

The ATLAS registry stays at 19 entries / 11 unique technique IDs;
LLM03:2025 detection is OUTSIDE the technique-ID enum scope.

## 3. Enumeration table — full ATLAS v4.5 matrix coverage

Tags:

- **COVERED** — already mapped, fixtures exist (5 rows, v1.19.0).
- **RELEVANT-DEFER** — applicable to the framework's threat surface
  but not yet tagged (pre-staged for PLAN-088 god-mode capability
  expansion or earlier).
- **NOT-APPLICABLE** — technique presupposes capability the framework
  does NOT have (e.g. model-training data access, GPU compute
  scheduling, deployed inference endpoints).
- **UNKNOWN-INVESTIGATE** — needs research; investigation hook listed.

| ATLAS ID | Name | Tag | Audit action (if COVERED) / rationale or hook |
|---|---|---|---|
| AML.T0000 | Search for Victim's Publicly Available Research Materials | NOT-APPLICABLE | Framework not adversarial recon target |
| AML.T0001 | Search for Victim's Publicly Available ML Artifacts | NOT-APPLICABLE | No published ML model artifacts |
| AML.T0002 | Acquire Public ML Artifacts | RELEVANT-DEFER | Sub-agent skill downloads — PLAN-088 ATLAS tagging pass |
| AML.T0003 | Search Application Repositories | RELEVANT-DEFER | RAG retrieval over public repos — `rag_query_issued` candidate |
| AML.T0004 | Search Victim-Owned Websites | NOT-APPLICABLE | Framework not target |
| AML.T0005 | ML Supply Chain Compromise | RELEVANT-DEFER | `skill_patch_applied` + `squad_imported` — PLAN-088 supply-chain pass |
| AML.T0006 | Active Scanning | NOT-APPLICABLE | Framework not target |
| AML.T0007 | Search for Victim ML Artifacts | NOT-APPLICABLE | No published artifacts |
| AML.T0008 | Acquire Infrastructure | NOT-APPLICABLE | Adversary capability, not framework |
| AML.T0009 | Develop Capabilities | NOT-APPLICABLE | Adversary capability |
| AML.T0010 | ML Supply Chain Compromise: Hardware | NOT-APPLICABLE | No hardware supply chain |
| AML.T0010.001 | ML Supply Chain Compromise: Hardware → GPU Firmware | NOT-APPLICABLE | No GPU dependency |
| AML.T0010.002 | ML Supply Chain Compromise: Hardware → Network Equipment | NOT-APPLICABLE | No network appliances |
| AML.T0011 | User Execution | RELEVANT-DEFER | `agent_spawn` + `plan_transition` user-initiated — PLAN-088 tagging |
| AML.T0011.000 | User Execution: Unsafe ML Artifact | RELEVANT-DEFER | `skill_patch_applied` — PLAN-088 |
| AML.T0012 | Valid Accounts | RELEVANT-DEFER | `live_adapter_call_started` w/ credentials — PLAN-088 tagging pass |
| AML.T0013 | Discover ML Model Ontology | NOT-APPLICABLE | No model ontology endpoint |
| AML.T0014 | Discover ML Model Family | NOT-APPLICABLE | No deployed model |
| AML.T0015 | Evade ML Model | RELEVANT-DEFER | `injection_flag` adjacent — possible split-mapping vs AML.T0051 |
| AML.T0016 | Obtain Capabilities | NOT-APPLICABLE | Adversary capability |
| AML.T0017 | Develop ML Artifacts | NOT-APPLICABLE | Adversary capability |
| AML.T0018 | Backdoor ML Model | NOT-APPLICABLE | No model training surface |
| AML.T0019 | Publish Poisoned Datasets | NOT-APPLICABLE | No dataset publication |
| AML.T0020 | Poison Training Data | NOT-APPLICABLE | No training stage |
| AML.T0021 | Establish Accounts | RELEVANT-DEFER | `live_adapter_call_started` creds onboarding — PLAN-088 |
| AML.T0022 | Stage Capabilities | NOT-APPLICABLE | Adversary capability |
| AML.T0023 | ML Model Inference API Access | NOT-APPLICABLE | Framework is consumer of API, not provider |
| AML.T0024 | Exfiltration via ML Inference API | RELEVANT-DEFER | Parent of COVERED `.001`; tagged at sub-technique granularity per §6 |
| AML.T0024.000 | Exfiltration via ML Inference API: Infer Training Data Membership | NOT-APPLICABLE | No training data |
| AML.T0024.001 | Exfiltration via ML Inference API: LLM Data Leakage | COVERED | `secret_leak_detected` — `tests/fixtures/atlas/AML-T0024-*.ndjson` |
| AML.T0024.002 | Exfiltration via ML Inference API: Invert ML Model | NOT-APPLICABLE | No model inversion surface |
| AML.T0024.003 | Exfiltration via ML Inference API: Extract ML Model | NOT-APPLICABLE | Framework not target |
| AML.T0025 | Exfiltration via Cyber Means | RELEVANT-DEFER | `live_adapter_call_failed` w/ scope misconfigured — PLAN-088 |
| AML.T0026 | Discover ML Artifacts | RELEVANT-DEFER | `skill_bootstrap_used` enumeration — PLAN-088 |
| AML.T0027 | ML Model Stealing | NOT-APPLICABLE | No model to steal |
| AML.T0028 | Backdoor ML Model: Poison ML Model | NOT-APPLICABLE | No model training |
| AML.T0029 | Denial of ML Service | RELEVANT-DEFER | `budget_exceeded` budget-DoS — PLAN-088 |
| AML.T0030 | Craft Adversarial Data | RELEVANT-DEFER | `injection_flag` — could be split-mapping vs AML.T0051 |
| AML.T0031 | Erode ML Model Integrity | RELEVANT-DEFER | parent of `.004` PII mapping |
| AML.T0032 | ML Intellectual Property Theft | NOT-APPLICABLE | No IP-bearing model |
| AML.T0033 | External Harms | UNKNOWN-INVESTIGATE | Investigate: do `output_safety_flag` events constitute external-harm vector? |
| AML.T0034 | Cost Harvesting | RELEVANT-DEFER | `budget_exceeded` + Codex token-undercount (PLAN-084 C.5) — PLAN-088 |
| AML.T0035 | ML Artifact Collection | RELEVANT-DEFER | `pattern_stored` cross-plan memory collection — PLAN-088 |
| AML.T0036 | Data from Information Repositories | RELEVANT-DEFER | `rag_query_issued` retrieval — PLAN-088 |
| AML.T0037 | Data from Local System | RELEVANT-DEFER | `output_scan_finding` local-fs scans — PLAN-088 |
| AML.T0038 | Command and Scripting Interpreter | RELEVANT-DEFER | Bash interceptor `check_bash_safety` — split between Initial-Access + Execution per ATLAS terminology |
| AML.T0039 | Drive-by Compromise | NOT-APPLICABLE | No web-app target |
| AML.T0040 | ML Model Inference API Compromise | NOT-APPLICABLE | Framework is consumer, not provider |
| AML.T0041 | Physical Environment Access | NOT-APPLICABLE | No physical access surface |
| AML.T0042 | Replication Through Removable Media | NOT-APPLICABLE | No removable media |
| AML.T0043 | Craft Adversarial Data: Adversarial Patch | NOT-APPLICABLE | No image-classification surface |
| AML.T0044 | Full ML Model Access | NOT-APPLICABLE | No deployed model |
| AML.T0045 | Evade Stealth Surveillance | NOT-APPLICABLE | Framework not surveillance target |
| AML.T0046 | Spamming ML System with Chaff Data | RELEVANT-DEFER | RAG chaff — PLAN-088 RAG hardening |
| AML.T0047 | ML-Enabled Product or Service | NOT-APPLICABLE | Framework not deployed product |
| AML.T0048 | Erode ML Model Integrity | RELEVANT-DEFER | Parent of COVERED `.004`; tagged at sub-technique granularity per §6 |
| AML.T0048.000 | Erode ML Model Integrity: Functional Degradation | NOT-APPLICABLE | No served model |
| AML.T0048.001 | Erode ML Model Integrity: Adversarial Examples | RELEVANT-DEFER | Same surface as AML.T0030 |
| AML.T0048.002 | Erode ML Model Integrity: Poisoning | NOT-APPLICABLE | No training |
| AML.T0048.003 | Erode ML Model Integrity: Backdoor | NOT-APPLICABLE | No training |
| AML.T0048.004 | Erode ML Model Integrity: User-injected Information | COVERED | `pii_redacted_outgoing` — `tests/fixtures/atlas/AML-T0048-*.ndjson` |
| AML.T0049 | Exploit Public-Facing Application | COVERED | `live_adapter_blocked` — `tests/fixtures/atlas/AML-T0049-*.ndjson` |
| AML.T0050 | Command and Control | RELEVANT-DEFER | `mcp_handler_invoked` w/ external server — PLAN-088 |
| AML.T0051 | LLM Prompt Injection | COVERED | `prompt_injection_detected` — `tests/fixtures/atlas/AML-T0051-*.ndjson` |
| AML.T0051.000 | LLM Prompt Injection: Direct | RELEVANT-DEFER | Family-split refinement under AML.T0051 — PLAN-088 |
| AML.T0051.001 | LLM Prompt Injection: Indirect | RELEVANT-DEFER | Family-split refinement — PLAN-088 |
| AML.T0052 | Phishing | NOT-APPLICABLE | Framework not user-facing target |
| AML.T0053 | LLM Plugin Compromise | RELEVANT-DEFER | `mcp_canonical_guard_blocked` — PLAN-088 |
| AML.T0054 | LLM Jailbreak | COVERED | `codex_egress_redacted` — `tests/fixtures/atlas/AML-T0054-*.ndjson` |
| AML.T0055 | Unsecured Credentials | RELEVANT-DEFER | `credential_rotation_due` — PLAN-088 credential telemetry pass |
| AML.T0056 | Extract LLM System Prompt | RELEVANT-DEFER | `output_safety_flag` system-prompt leak — PLAN-088 |
| AML.T0057 | LLM Data Leakage | UNKNOWN-INVESTIGATE | Investigate: redundant with AML.T0024.001? May fold/alias |
| AML.T0058 | Publish Poisoned Models | NOT-APPLICABLE | No model publication |
| AML.T0059 | Erode Dataset Integrity | NOT-APPLICABLE | No dataset surface |
| AML.T0060 | LLM Trusted Output Components Manipulation | RELEVANT-DEFER | `output_scan_finding` — PLAN-088 |
| AML.T0061 | LLM Plugin Compromise | RELEVANT-DEFER | `mcp_canonical_guard_blocked` — possibly merges with AML.T0053 |
| AML.T0062 | Discover LLM System Information | RELEVANT-DEFER | Spawn-payload introspection — PLAN-088 |
| AML.T0063 | Acquire Infrastructure: Domains | NOT-APPLICABLE | Adversary capability |
| AML.T0064 | Acquire Infrastructure: Servers | NOT-APPLICABLE | Adversary capability |
| AML.T0065 | LLM Prompt Crafting | RELEVANT-DEFER | Adjacent to AML.T0051 — PLAN-088 |
| AML.T0066 | Retrieval Tool Poisoning | RELEVANT-DEFER | `rag_query_redacted` — PLAN-088 |
| AML.T0067 | LLM Plugin Compromise: External Service | UNKNOWN-INVESTIGATE | Investigate: split between MCP + live-adapter — research before mapping |
| AML.T0068 | LLM Plugin Compromise: Internal Service | UNKNOWN-INVESTIGATE | Investigate: needs MCP server-side context (PLAN-070 R4) |
| AML.T0069 | Discover LLM Hallucinations | UNKNOWN-INVESTIGATE | Investigate: does `fluency_nudge` constitute partial detection? |
| AML.T0070 | LLM Trusted Output Components Manipulation (Aliased) | UNKNOWN-INVESTIGATE | Investigate: alias of AML.T0060 per ATLAS v4.5 changelog |

## 4. Tag distribution summary

- **COVERED:** 5 seeded (v1.19.0 docs+fixtures via PLAN-085 Wave G.1a; production wire pending G.1b serial commit)
- **RELEVANT-DEFER:** 33 (queued for PLAN-088 ATLAS-tagging pass +
  related god-mode capability work — includes 2 parent rows whose
  sub-techniques are COVERED but the parent itself remains untagged
  per §6 sub-technique-granularity rule)
- **NOT-APPLICABLE:** 41 (with rationale)
- **UNKNOWN-INVESTIGATE:** 6 (each with investigation hook)
- **TOTAL §3 ROWS:** 85

## 5. Refresh cadence

ATLAS releases new technique IDs ~quarterly. Per PLAN-085 AC8, each
minor version SHIPPED MUST refresh:

1. Pull latest `atlas-data` git tag.
2. Diff technique-ID set against this table.
3. Categorize new IDs (COVERED / RELEVANT-DEFER / NOT-APPLICABLE /
   UNKNOWN-INVESTIGATE).
4. Update "Last refreshed" header.

Stale-doc gate: `check-staleness.py` raises advisory after 120 days.

## 6. Field encoding contract (G.1b)

When Wave G.1b lands, the `atlas_technique` field is added to
`emit_*` functions for the 5 COVERED actions. Encoding rules:

- **Type:** `Optional[str]`, default `None`.
- **Format:** `AML.TNNNN` or `AML.TNNNN.NNN` exactly (validated by
  `_validate_atlas_id()` private helper — regex
  `^AML\.T\d{4}(\.\d{3})?$`).
- **Single-mapping per action.** Multi-tag is rejected at emit time;
  add a sub-action variant instead.
- **Audit-query filter.** `audit-query.py count --action <X>
  --filter "atlas_technique=AML.T<NNNN>"` returns the count.

## 7. Related ADRs

- ADR-035 (legacy adversarial taxonomy)
- ADR-040 (live-adapter scope policy)
- ADR-042 (MCP server-side defense)
- ADR-114 (Codex egress redaction symmetry)

## 8. References

- [MITRE ATLAS v4.5](https://atlas.mitre.org/matrices/ATLAS)
- [atlas-data Apache-2.0](https://github.com/mitre-atlas/atlas-data)
- PLAN-085 §4 Wave G — ATLAS technique-ID seed batch
- PLAN-088 (queued) — full RELEVANT-DEFER batch tag-pass
- `.claude/scripts/red-team-corpus/external/EXT-011-mitre-atlas.md`
  (legacy short reference — superseded by this file)
