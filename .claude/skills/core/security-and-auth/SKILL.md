---
name: security-and-auth
description: Security architecture, authentication, authorization, and hardening for
  the {{PROJECT_NAME}}. Covers JWT+HMAC auth patterns, AES-256-GCM credential
  encryption, rate limiting design, OWASP Top 10 for Node.js/Hono, RLS policy design,
  timing-safe comparisons, API key lifecycle, input validation, CORS configuration,
  WebSocket auth, and proxy relay security. Use when reviewing or writing any code
  that touches authentication, authorization, credential storage, API key management,
  rate limiting, input validation, CORS, WebSocket security, proxy security, or any
  route that handles sensitive data or actions.
owner: Security Engineer (archetype)
version: 1.1.0
allowed-tools: Read, Grep, Glob
inspired_by:
  - source: msitarzewski/agency-agents/engineering/engineering-security-engineer.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
  - source: msitarzewski/agency-agents/engineering/engineering-threat-detection-engineer.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
  - source: affaan-m/ecc/skills/security-review@81af40761939056ab3dc54732fd4f562a27309d0
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-07-07
  - source: affaan-m/ecc/skills/security-bounty-hunter@81af40761939056ab3dc54732fd4f562a27309d0
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-07-07
source: affaan-m/ecc@81af4076 skills/security-review/ + skills/security-bounty-hunter/
license: MIT
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 1
risk_class: high
stack: [typescript, node, python]
context_budget_tokens: 1400
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 2}
  engine: {active: true, priority: 1}
  fintech: {active: true, priority: 1}
  trading-readonly: {active: true, priority: 1}
  generic: {active: true, priority: 3}
activation_triggers:
  - {event: file-edit, glob: "**/auth/**"}
  - {event: file-edit, glob: "**/.env*"}
  - {event: help-me-invoked, regex: "(?i)auth|jwt|oauth|rate.?limit"}
---

# Security and Authentication

## When to Activate

Read this skill when you are:

- writing or reviewing ANY code that touches authentication, authorization,
  session/token handling, or credential storage;
- adding or changing a route, WebSocket upgrade, proxy relay, or edge
  function that handles sensitive data or mutating actions;
- reviewing rate limiting, CORS, RLS policies, or input validation;
- provisioning cloud infrastructure, IAM policies, a CI/CD pipeline, or
  edge/CDN config — load `references/cloud-and-ci-cd-security.md` for the
  least-privilege deploy-substrate posture;
- reviewing LLM-adjacent code (prompt handling, tool scopes, agent
  authority) — load `references/owasp.md` for the OWASP LLM Top-10 rubric;
- hunting for a reachable, exploitable vulnerability (vs. a broad
  best-practices pass) — load `references/vulnerability-hunting.md` for
  reachability-first triage;
- filing or triaging a security finding — severity requires a PoC; load
  `references/proof-of-exploitability.md`.

The machine-first `activation_triggers` frontmatter remains the canonical
auto-load rule; this section is its human-scannable mirror.

## Fail-Fast Rule

If any security invariant, validation, or precondition fails, **stop and
return a structured rejection**. Never degrade security silently. Never
skip auth checks "because it's internal." Never log secrets, even partially,
unless behind explicit masking. Never assume a route is unreachable.

## Reference Files — progressive disclosure (PLAN-153 Wave C)

The deep-dive sections of this skill were extracted VERBATIM into the eight
**Wave-C** `references/*.md` files listed below — zero content loss (every
content line of the pre-split SKILL.md appears verbatim either in this file
or in one of those eight references; the loader additionally ADDS loader-only
sections — When to Activate, the pointer tables, the changelog). Load on
demand:

| Load `references/<file>` | For |
|---|---|
| `known-vulnerabilities.md` | The SEC-1..SEC-16 audit-finding tables (template posture baseline) |
| `auth-and-credentials.md` | Auth architecture + rules for new routes, timing-safe comparisons, AES-256-GCM credential encryption |
| `perimeter-and-transport.md` | Rate-limiting design, CORS, WebSocket security, proxy-relay security |
| `data-access-and-validation.md` | Supabase RLS policy design, input validation, API-key lifecycle |
| `owasp.md` | OWASP Top-10 checklist + OWASP LLM Top-10 (2024) inference-path rubric |
| `threat-model-worksheet.md` | Adversary-first worksheet, STRIDE matrix, POST /v1/withdrawals worked example |
| `detection-as-code.md` | Detection-rule pipeline, required metadata, tuning targets, CI replay fixtures |
| `proof-of-exploitability.md` | PoC-anchored severity gate, finding bundle structure, disclosure discipline |

**Wave-G enrichment (net-new; NOT part of the verbatim Wave-C split).** The two
references below are knowledge ported clean-room and rewritten in house voice
(provenance in the `inspired_by:` frontmatter) — they add coverage the pre-split file never had, so the containment
claim above scopes to the Wave-C rows only:

| Load `references/<file>` | For |
|---|---|
| `cloud-and-ci-cd-security.md` | IAM least-privilege, cloud secrets + rotation, network posture, CI/CD pipeline (OIDC, scanning gates, signed commits/tags), edge/CDN, backup/recovery, consolidated pre-deploy gate |
| `vulnerability-hunting.md` | Exploitability-first triage: reachability bias, in-scope CWE table, low-signal skip list, hunt workflow, report quality gate (pairs with `proof-of-exploitability.md`) |

## Anti-Patterns to Reject

| Anti-Pattern | Why It's Wrong | Correct Approach |
|---|---|---|
| `===` for secret comparison | Timing oracle | `timingSafeEqual` |
| Auth in "most" routes | One miss = full bypass | Auth middleware on route group |
| CORS `origin: "*"` | Allows any origin to call API | Explicit origin allowlist |
| Logging full API keys | Credential leak in logs | `key.slice(0,4) + "***"` |
| User ID from request body | Horizontal privilege escalation | Extract from verified JWT |
| Proxy without auth | Free infrastructure for attackers | Shared secret + conn limit |
| WS without auth on upgrade | Unauthenticated access to all channels | Verify token before accepting |
| `catch {}` on auth errors | Silently passes invalid auth | Always return 401/403 |
| Hardcoded secrets in source | Leak via git history | Env vars with bootstrap validation |
| Password change in memory only | Lost on restart (SEC-27) | Persist to Supabase |
| Wildcard IAM / public data store | Deploy-substrate bypass of app auth | See `references/cloud-and-ci-cd-security.md` |
| Chasing unreachable theoretical bugs | Queue fills; real reachable flaws starve | See `references/vulnerability-hunting.md` |

## 20. Benchmarks

This skill has a measurable benchmark suite at
`.claude/skills/core/security-and-auth/benchmarks/owasp-basics.yaml`
(14 scenarios: 10 positive OWASP Top 10 + 4 precision controls).

Run locally:
```
python3 .claude/scripts/run-skill-benchmark.py \
    .claude/skills/core/security-and-auth/benchmarks/owasp-basics.yaml \
    --json
```

The benchmark runs each scenario 3× (median-of-3) at `temperature=0`
against `claude-haiku-4-5-20251001` and scores against `must_flag_tags`
+ `must_suggest_keywords` + `must_identify_severity`. Control scenarios
are scored on PRECISION (must NOT flag the listed tags at MEDIUM+).

CI mode is advisory in Sprint 2 (soft-fail + `$GITHUB_STEP_SUMMARY`
annotation). Sprint 3 tightens to an absolute floor. Sprint 4 adds
regression gating against `main`'s last-known-good score.

Scenario edit policy: any change to code samples, expected tags, or
severity bumps the scenario's `version:` and carries a `validated_by:
YYYY-MM-DD` line. CODEOWNERS gates the benchmark YAML.

## Changelog

- **1.1.0** (2026-07-09, PLAN-153 Wave G, SP-034): ADAPT-merge enrichment —
  added two net-new references, `cloud-and-ci-cd-security.md` (deploy-substrate
  least-privilege: IAM, cloud secrets + rotation, network, CI/CD pipeline with
  OIDC + scanning + signed tags, edge/CDN, backup/recovery, consolidated
  pre-deploy gate) and `vulnerability-hunting.md` (exploitability-first
  reachability triage, in-scope CWE table, skip list, hunt workflow, quality
  gate). Both ported clean-room (provenance in
  `inspired_by:` frontmatter). Added two pointer rows, two `## When to Activate`
  bullets, and two `## Anti-Patterns` rows. No pre-existing content changed;
  zero new skill files, catalog count unchanged. Soak: parallel-shadow
  (OQ3=c) until >= 2026-07-14.
- **1.0.0** (2026-07-07, PLAN-153 Wave C, SP-023): progressive-disclosure
  restructure — deep-dive sections extracted verbatim to `references/*.md`;
  added `version:` frontmatter, least-privilege `allowed-tools:` frontmatter
  (this skill is `risk_class: high`), this changelog, and the human-scannable
  `## When to Activate` section. Zero change to the extracted content.
Skill-Import-Attestation: reviewed-by=AE9B236FDAF0462874060C6BCFCFACF00335DC74; sha256=13e34380c9da6cd837418640251b63d567f49fd723b4c464f04315abaa399f59
