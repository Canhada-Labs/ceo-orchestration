# Red-Team Corpus Provenance Registry

**Scope:** PLAN-014 Phase D.1 (ADJ-023). Per-fixture SHA-256 + licensing +
source URL + one-line rationale for all external and regression fixtures.

**Policy:** Every new fixture MUST have an entry here before merge.
Refresh requires ADR-037 amendment + v1-vs-v2 FPR diff.

---

## External Fixtures (EXT-016 through EXT-040)

| ID | SHA-256 (first 16) | License | Source | Rationale |
|----|---------------------|---------|--------|-----------|
| EXT-016 | `9e12c0726c88d790` | Synthetic (original) | Internal — governance bypass pattern | Tests SKILL CONTENT header injection inside skill patches to override governance sections |
| EXT-017 | `e0c339f70da5e359` | Synthetic (original) | Internal — persona impersonation | Tests CEO persona impersonation to bypass spawn governance |
| EXT-018 | `82713d0d63391692` | Synthetic (original) | Internal — file assignment escape | Tests wildcard glob in FILE ASSIGNMENT to bypass per-agent scoping |
| EXT-019 | `3f09c733e3f4ea92` | Synthetic (original) | Internal — veto bypass | Tests veto override claim + plan ID env-var spoofing |
| EXT-020 | `6eee5f8a7d1c3e98` | Synthetic (original) | Internal — canonical-edit circumvention | Tests settings.json modification to disable hook protections |
| EXT-021 | `4716278846b8a0dc` | Synthetic (original) | Internal — spawn protocol violation | Tests agent spawn without required AGENT PROFILE/SKILL CONTENT/FILE ASSIGNMENT |
| EXT-022 | `3936ba06b88f5eec` | Synthetic (original) | Internal — Unicode homoglyph | Tests zero-width space in skill name to evade name matching (CVE-2021-42574) |
| EXT-023 | `6fb9e4408483c9d4` | Synthetic (original) | Internal — MCP governance bypass | Tests MCP spawn_agent without compliant AGENT PROFILE (ADR-042) |
| EXT-024 | `994a6f48b4ad74b3` | Synthetic (original) | Internal — credential leak in error | Tests API key in error message redaction (ADR-040) |
| EXT-025 | `4846204bd2c4dcaa` | Synthetic (original) | Internal — nested subshell escape | Tests nested bash subshell exfiltrating audit log via curl |
| EXT-026 | `528ad463c54b33a6` | Synthetic (original) | Internal — plan edit bypass | Tests direct plan file edit bypassing debate requirement |
| EXT-027 | `7516f6c46f54a6e6` | Synthetic (original) | Internal — audit rotation race | Tests concurrent writers during audit log rotation |
| EXT-028 | `e2039e933fd0bfc9` | Synthetic (original) | Internal — dependency confusion | Tests npm package SHA-256 mismatch from supply-chain substitution |
| EXT-029 | `6d66b45696ebee47` | Synthetic (original) | Internal — Unicode confusable | Tests Unicode confusable characters bypassing regex token detection |
| EXT-030 | `f03f98eaee53b194` | Synthetic (original) | Internal — retry storm DoS | Tests adapter retry storm that leaks context in error messages |
| EXT-031 | `0b42f3b047385008` | Synthetic (original) | Internal — canonical team.md edit | Tests direct edit to canonical-guarded team.md |
| EXT-032 | `b7f688e4ee8f1cd8` | Synthetic (original) | Internal — env var exfiltration | Tests two-stage env dump + curl exfiltration |
| EXT-033 | `a801e04b4659ff60` | Synthetic (original) | Internal — MCP rate limit bypass | Tests rate limit bypass via injected HTTP headers |
| EXT-034 | `40843c8101948866` | Synthetic (original) | Internal — OTEL attribute leak | Tests credentials in OTEL span attributes without redaction |
| EXT-035 | `d764ae41be362098` | Synthetic (original) | Internal — polyglot code injection | Tests markdown/Python polyglot with os.system + subprocess.call |
| EXT-036 | `7e6ee8097ab83dd7` | Synthetic (original) | Internal — base64 triple wrap | Tests triple-nested base64 encoding to bypass depth-2 unwrap |
| EXT-037 | `ab087d84a71bc6d2` | Synthetic (original) | Internal — cross-plan memory read | Tests cross-plan scratchpad read violating plan-scoped isolation |
| EXT-038 | `9a0bb42177430c29` | Synthetic (original) | Internal — SLSA provenance strip | Tests npm package with stripped SLSA provenance attestation |
| EXT-039 | `3a992d62e9dc7d58` | Synthetic (original) | Internal — streaming credential leak | Tests credential in streaming response chunk error diagnostic |
| EXT-040 | `2fae4b842fb3e3d7` | Synthetic (original) | Internal — symlink to .env | Tests symlink attack targeting .env file for secret exfiltration |

## Regression Fixtures (REG-001 through REG-015)

| ID | SHA-256 (first 16) | Source Incident | Session | Rationale |
|----|---------------------|-----------------|---------|-----------|
| REG-001 | `7c5199a5f65e7550` | Gap #4: breaker audit emission missing | Session 22 | CircuitBreaker._open_locked called without emit_breaker_opened |
| REG-002 | `a6688463a34ad53f` | Gap #3: audit registry miss | Session 20-21 | New emit functions lacked _KNOWN_ACTIONS registry entry |
| REG-003 | `c66590e4f412fad1` | Gap #4: breaker provider kwarg | Session 22 | CircuitBreaker.__init__ lacked provider parameter for attribution |
| REG-004 | `042996873ad8ce52` | conftest.py canonical-edit block | Session 21 | QA agent conftest.py creation blocked by canonical-edit guard |
| REG-005 | `ee92495ba4187d26` | MCP dispatch handler overflow | Session 21 | dispatch.py oversized handler resource exhaustion risk |
| REG-006 | `582ce6fb9859e027` | Audit registry false orphan | Session 21 | Regex scan reported 42 false-positive orphan emit functions |
| REG-007 | `17b6aa51df1795ce` | SPEC count undercount | Session 22 | CLAUDE.md claimed 18 SPEC but actual was 22 |
| REG-008 | `0b7f250e80119345` | ADR phantom count | Session 22 | Claimed 44 ADRs but actual 43 (ADR-022 reserved-empty) |
| REG-009 | `55daaa7eaf7a1d0b` | TLC pending placeholder | Session 22 | TLC hash placeholder fabrication to fake verification |
| REG-010 | `7f238e1755776304` | Mutation kill rate fabrication | Session 22 | Adding skip/xfail to conformance tests to silently reduce kill rate |
| REG-011 | `df6d7b0fb2e30a40` | Byte-identity governance mismatch | Session 21 | MCP vs Claude-native producing different block_reason strings |
| REG-012 | `a8af9a9ceeab418d` | Conformance mapping drift | Session 22 | Overly broad fallback roots defeating mapping integrity |
| REG-013 | `379cfd85e8fe2004` | L1 fairness lazy-fire exploit | Session 22 | Exploiting TLA+ eager vs real impl lazy-fire gap |
| REG-014 | `a9a2973cc8acc3c6` | MCP path traversal | Session 21 | get_skill handler path traversal with ../../../etc/passwd |
| REG-015 | `dba7f8e42e231735` | MCP HMAC timestamp replay | Session 21 | HMAC token replay with old timestamp beyond +-60s skew |

## Frozen Corpus v1

- **File:** `.claude/scripts/red-team-corpus/v1/fixtures.jsonl`
- **SHA-256:** `a5a62a03a84ef206c9023d2af65bdef9c4828d89cd80a6a124691886401de80a`
- **Fixture count:** 67 JSONL lines (27 synthetic + 25 external + 15 regression)
- **Frozen date:** 2026-04-15
- **Refresh policy:** Requires ADR-037 amendment + v1-vs-v2 FPR diff comparison

## References

- PLAN-014 Phase D.1 ADJ-023 (provenance requirement)
- ADR-037 §Transition Log (State 0 to 1)
- `.claude/scripts/red-team-corpus/README.md` (corpus schema)
- `.claude/scripts/red-team-corpus/.byte-identity-check.txt` (SHA ledger)
