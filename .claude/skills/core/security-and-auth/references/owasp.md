<!-- PLAN-153 Wave C progressive-disclosure pilot (rides SP-022 via /skill-review). Extracted VERBATIM from core/security-and-auth/SKILL.md (pre-split state); zero content loss. Edit only via a new SP-NNN that bumps the parent SKILL.md version. -->

## OWASP Top 10 Checklist for {{PROJECT_NAME}}

| OWASP | {{PROJECT_NAME}} Status | Key File(s) |
|-------|----------------|-------------|
| A01: Broken Access Control | WEAK — N mutation endpoints unprotected | routes/mutations-*.ts |
| A02: Cryptographic Failures | GOOD — AES-256-GCM, HMAC-SHA256, PBKDF2 | auth.ts, config.ts |
| A03: Injection | GOOD — PostgREST, no raw SQL, JSON only | All routes |
| A04: Insecure Design | PARTIAL — proxy relays, WS unauth | proxy/*.ts, index.ts |
| A05: Security Misconfiguration | WEAK — CORS wildcard, defaults in dev | public-router-inline.ts |
| A06: Vulnerable Components | OK — small prod dep set, vitest dev only | package.json |
| A07: Auth Failures | WEAK — timing oracles, password not persisted | auth.ts, routes/admin.ts |
| A08: Data Integrity | GOOD — HMAC webhooks, signed tokens | auth.ts, stripe handler |
| A09: Logging Failures | GOOD — structured logging, IP masking | structured-log.ts |
| A10: SSRF | LOW RISK — no user-supplied URLs fetched | — |

<!-- non-adjacent sections of the pre-split SKILL.md joined here; each block below is verbatim -->
## OWASP LLM Top 10 (2024) — inference-path rubric

> Cross-ref: full rubric + framework-defense mapping at
> `docs/OWASP-LLM-TOP-10.md`. Benchmark fixtures at
> `benchmarks/owasp-llm-top-10.yaml` (14 positive + 6 control
> scenarios, model_baseline_version = claude-opus-4-7).

When reviewing LLM-adjacent code, the security specialist MUST
verify each of the 10 categories:

| ID | Category | First-pass audit question |
|----|----------|---------------------------|
| LLM01 | Prompt injection | Does untrusted input reach a prompt concatenated with system instructions without separator/pre-scan/escape? |
| LLM02 | Insecure output handling | Is LLM output piped to an HTML / shell / SQL sink without sanitization? |
| LLM03 | Training-data poisoning | Is a fine-tune pinned by hash + behavioral regression test before hot-path? |
| LLM04 | Model DoS | Is there a per-caller rate limit + per-request max-token clamp + cumulative budget? |
| LLM05 | Supply chain | Is every MCP server pinned (SHA + signature), not `npx -y`? |
| LLM06 | Sensitive info disclosure | Is PII / secrets absent from prompt + logs + retrieved content? |
| LLM07 | Insecure plugin design | Does every spawned agent carry `## SKILL CONTENT` or `## SKILL REFERENCE`? Tool scopes least-privilege? |
| LLM08 | Excessive agency | Is destructive tool authority kill-switched + dry-run-able + human-confirmed? |
| LLM09 | Overreliance | Is the merge gate re-verifying via CI, not accepting agent "tests pass" self-report? (PROTOCOL §Artifact Paradox) |
| LLM10 | Model theft | Is the prompt library redacted before export to external sinks? |

Failure to audit any category = reviewer strike (ADR-031 §Review
discipline).

Benchmark runs per quarter (advisory in Sprint 2; strict in Sprint 3+) via
`python3 .claude/scripts/run-skill-benchmark.py .claude/skills/core/security-and-auth/benchmarks/owasp-llm-top-10.yaml --floor 0.7 --strict`.
The `--floor 0.7` flag gates aggregate score; `--strict` fails the run on
any individual scenario below the floor (without `--strict`, failed
scenarios pass the run if aggregate ≥ 0.7). Control scenarios (must NOT
flag) are scored binary today — 1.0 if uncaught, 0.0 if false-positive;
the YAML's `control_threshold: 0.85` is metadata reserved for stricter
runner scoring (Sprint 3+) and is NOT enforced by the runner currently.
Manual inspection of any failed positive AND any false-positive control
is required regardless of CLI exit code. (NOTE: this corrects a
pre-existing canonical-content bug where the documented invocation used
non-existent `--skill` / `--benchmark` flags; see PLAN-074 Wave 1a fix-pack.)

