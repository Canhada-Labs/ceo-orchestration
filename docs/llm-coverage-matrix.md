# LLM Coverage Matrix — output_scan families vs. OWASP LLM Top 10

> **Status:** LANDED 2026-04-22 (PLAN-050 Phase 3 C7 consensus deliverable;
> 14 matrix families + NFKC-delta detector shipped in
> `_lib/output_scan.py` + 43 new tests in `test_output_scan.py`).
> Maps each detection family in the framework's output-scan pipeline to its
> corresponding OWASP LLM Top 10 (2024) entry. Used by reviewers to verify
> coverage is explicit, not accidental, and to trace regressions when a
> family is removed in future refactors.

## Purpose

PLAN-050 Round 1 consensus C7 (security-engineer #6 + qa-architect #3):
without explicit mapping from each output_scan family to a specific
OWASP/MITRE-ATLAS entry, coverage regresses silently. This matrix is
the source of truth a future reviewer consults when asking
"does the framework cover LLM02 indirect prompt injection?"

If a family is removed without updating this matrix, `validate-governance.sh`
should warn (advisory, not blocking — this is a process guard, not a
runtime guard).

## OWASP LLM Top 10 (2024) — project-scope entries

This project touches the following OWASP entries. Entries omitted here
(e.g. LLM03 training-data poisoning, LLM05 supply-chain) are either
out-of-scope (we do not train models) or covered by a different
mechanism (supply-chain → check-action-sha-drift.py + SHA-pin audit, not
output_scan).

| OWASP ID | Name | In scope for output_scan? |
|----------|------|---------------------------|
| LLM01 | Prompt Injection | **Yes** — direct + indirect |
| LLM02 | Insecure Output Handling | **Yes** — data-URL / file-URL / tool-invocation sigils |
| LLM04 | Model Denial-of-Service | No (covered by ITIMER budgets in hook layer, not output-scan) |
| LLM06 | Sensitive Information Disclosure | **Yes** — secret/PII family catalog |
| LLM07 | Insecure Plugin Design | No (Claude native Agent tool; not user-managed plugins) |
| LLM08 | Excessive Agency | **Yes** — tool-invocation sigils (prompt tries to re-enter agent loop) |
| LLM09 | Overreliance | Partial — Artifact Paradox nudge hook (`check_fluency_nudge.py`) addresses this at SubagentStop, not output_scan |
| LLM10 | Model Theft | No (not applicable to framework scope) |

## Family → OWASP mapping

### Output-scan families (runtime scan of subagent / tool output)

The output_scan pipeline runs on `PostToolUse` (and SubagentStop for
fluency nudge). It inspects the subagent-emitted text, the tool
response, and any content that crosses a trust boundary into the
parent conversation.

| Family ID | OWASP Entry | Detector | Phase | Staged? |
|-----------|-------------|----------|-------|---------|
| `prompt_injection_sigil_system` | LLM01 | Matches `<\|system\|>`, `<\|user\|>`, `<\|assistant\|>` and similar role-override markers | 3 | Phase 3 item p0_10 |
| `prompt_injection_sigil_instruction` | LLM01 | Matches `### Instruction`, `### System Prompt`, `---BEGIN PROMPT---` | 3 | Phase 3 item p0_10 |
| `prompt_injection_ignore_previous` | LLM01 | Matches `Ignore previous instructions`, `Disregard above`, `Forget everything before` (case-insensitive) | 3 | Phase 3 item p0_10 |
| `prompt_injection_jailbreak_persona` | LLM01 | Matches `You are now DAN`, `You are now in developer mode`, `Pretend you are an unrestricted AI` | 3 | Phase 3 item p0_10 |
| `unicode_tag_chars` | LLM01 | Matches U+E0000–U+E007F Unicode tag block (invisible prompt-injection vector, 2024 research) | 3 | Phase 3 item p0_10 |
| `unicode_rtl_override` | LLM01 | Matches U+202E (RTL override) and U+202D (LTR override) | 3 | Phase 3 item p0_10 |
| `unicode_zero_width` | LLM01 | Matches U+200B (ZWSP), U+200C (ZWNJ), U+200D (ZWJ), U+FEFF (BOM) | 3 | Phase 3 item p0_10 |
| `unicode_homoglyph_nfkc_delta` | LLM01 | Detects text where NFKC normalization changes content (fullwidth→halfwidth, compat ligatures, superscripts) | 3 | Landed (`scan_nfkc_homoglyph()` — compat-only; canonical composition excluded) |
| `encoded_exfil_base64` | LLM02, LLM06 | Base64 blobs ≥200 chars outside code fence | 3 | Phase 3 item p0_10 |
| `encoded_exfil_hex` | LLM02, LLM06 | Hex blobs ≥160 chars (80+ bytes of arbitrary data) | 3 | Phase 3 item p0_10 |
| `encoded_exfil_url_encoded` | LLM02 | Dense URL-encoded payloads (>30% `%XX` sequences in a run) | 3 | Phase 3 item p0_10 |
| `data_url_reference` | LLM02 | Matches `data:` URLs in output (could side-load content) | 3 | Phase 3 item p0_10 |
| `file_url_reference` | LLM02 | Matches `file://` URLs in output | 3 | Phase 3 item p0_10 |
| `tool_invocation_sigil` | LLM08 | Matches patterns that try to re-enter the agent loop from within a response (`<tool_use>...`, `function_call:`, `<function_calls>`) | 3 | Phase 3 item p0_10 |

### Secret / PII families (consumed by spawn-scan + output_scan)

These come from the `_lib/secret_patterns.py` catalog (Phase 0.5 —
currently STAGED in `.claude/plans/PLAN-050/staged-code/`) and are
shared between `check_agent_spawn.py` (pre-spawn scan) and
`check_output_secrets.py` / `check_fluency_nudge.py` (post-tool scan
+ redact-before-emit).

Full list: see `secret_patterns.py::SECRETS` (19 families) +
`secret_patterns.py::PII` (4 families).

| Category | OWASP Entry | Coverage |
|----------|-------------|----------|
| API tokens (Anthropic, OpenAI, AWS, Google, GitHub, GitLab, Stripe, HuggingFace, Slack, npm, DigitalOcean, Linear, Twilio) | LLM06 | 13 families |
| Credential formats (AWS secret, Google OAuth refresh, PEM private keys, JWT) | LLM06 | 4 families |
| Brazilian PII (CPF, CNPJ, BR phone, credit card — all checksum-validated where applicable) | LLM06 + LGPD | 4 families |

**Total: 23 families.** Each family has a stable `family_id` emitted
to `audit-log.jsonl` when matched, allowing per-family triage in
`audit-query.py`.

## Redaction contract

Every match produces a `[REDACTED:<label>]` replacement. The redaction
labels are stable across catalog versions within the same major
SemVer. Consumers downstream of the audit log (dashboards, compliance
reports) can reverse-engineer the family from the label.

Bumping `CATALOG_VERSION` major → redaction labels MAY change; minor
and patch → labels MUST be backward-compatible.

## Not in scope for output_scan

The following families exist as risks but are **not** caught by
output_scan:

| Risk | Why out-of-scope | Where it IS handled |
|------|------------------|---------------------|
| Training-data poisoning (LLM03) | We do not train models | Upstream model vendor |
| Direct model theft (LLM10) | Application-layer concern | Out-of-scope |
| Insecure plugin design (LLM07) | Claude Code native Agent tool is vetted; no user-plugins | Upstream Claude Code |
| Supply-chain compromise (LLM05) | Covered by action SHA-pin discipline | `.github/workflows/` + `check-action-sha-drift.py` |
| Model denial-of-service (LLM04) | Covered by hook-level ITIMER budgets (500ms scan budget + 30s per-subagent wall-clock) | Phase 4 (audit_log) + Phase 7 (swarm kill-switch) |
| Overreliance (LLM09) | Process risk, not content risk | `check_fluency_nudge.py` (Artifact Paradox advisory) + PROTOCOL.md §Artifact Paradox |

## Maintenance contract

Rules for evolving this matrix:

1. **Add a family → update this matrix in the same PR.** No exceptions.
2. **Remove a family → mark as `DEPRECATED` in this matrix first** (one
   sprint grace), then remove in the next sprint. Do NOT silently drop.
3. **OWASP version bump** — when OWASP publishes an updated Top 10
   (e.g. 2025 revision), this file's §OWASP entries table must be
   re-validated within 30 days.
4. **Catalog version (`_lib/secret_patterns.py::CATALOG_VERSION`)** —
   SemVer. Matrix should cite the current version.

Current coverage snapshot: **14 output_scan families + 23 secret/PII
families** across LLM01, LLM02, LLM06, LLM08. Phase 3 landed 14 of
14 output_scan families in commit (Session 53, output_scan.py +
test_output_scan.py — 43 new tests, 0 regressions on 2408-test baseline).

Note the 4 OWASP-group patterns retained from the legacy Phase 3
staged expansion (LLM04 / LLM05 / LLM07 / LLM09) are NOT in the
official matrix; they survived for opt-in FPR observation (env
kill-switch `CEO_OUTPUT_SCAN_LLM0{4,5,7,9}=0`) and can be deprecated
after Phase 3 soak confirms the matrix families cover their signal
adequately.

## Cross-references

- OWASP LLM Top 10 2024: https://owasp.org/www-project-top-10-for-large-language-model-applications/
- ADR-057: `output_scan` redaction architecture
- ADR-065: Audit-event naming convention (`family_id` stability contract)
- PLAN-039: OWASP LLM Top 10 rubric (14+6 scenarios evaluation harness)
- PLAN-050 Round 1 consensus C7: this matrix's origin in the debate synthesis
- `_lib/secret_patterns.py` (Phase 0.5 STAGED): secret/PII catalog
