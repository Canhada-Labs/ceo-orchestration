---
id: PLAN-058
title: Post-v1.10.0 Security response + delta audit
status: done
created: 2026-04-24
completed_at: 2026-04-28
budget_tokens: 250-400k
budget_sessions: 3-5
context_risk: medium
sprint: none
level: L3
tags: [post-v110, security, webfetch-injection, delta-audit, done]
---

# PLAN-058 — Post-v1.10.0 Security + Audit (reactive)

## 4. Phases

### §4.0. Phase table

| Phase | Goal | Files touched | Canonical | Reversibility | Tokens (in/out) | Tag |
|---|---|---|---|---|---|---|
| A | Fase A Security: new hook check_webfetch_injection.py + _lib/injection_patterns.py | check_webfetch_injection.py (new hook) + settings.json + ADR-077 | **YES** | HIGH | ~60k / ~35k | v1.11.0 |
| A2 | WebFetch injection detection lib (injection_patterns.py new) | _lib/injection_patterns.py (new 200 LoC script) + tests | no | HIGH | ~40k / ~25k | v1.11.0 |
| A3 | ADR-077 incident + remediation doc | ADR-077-webfetch-injection-incident.md | no | HIGH | ~20k / ~15k | v1.11.0 |
| A4 | Regression fixtures — test_webfetch_injection.py + test_injection_patterns.py | tests (new, 2 test files) | no | HIGH | ~30k / ~20k | v1.11.0 |
| B | Delta audit — 22-dimensional post-v1.10.0 audit | audit findings report only | no | n/a | ~80k / ~50k | v1.11.0 |
| C | Audit remediation P0 burn-down (Round-23 findings) | audit_log.py canonical + UserPromptSubmit.py | **YES** | MEDIUM | ~60k / ~35k | v1.11.1 |
| **CEO orchestration** | session reads + decisions | session context | n/a | n/a | ~50k / ~25k | n/a |

**Total:** ~340k input + ~205k output ≈ **~545k cumulative tokens**
