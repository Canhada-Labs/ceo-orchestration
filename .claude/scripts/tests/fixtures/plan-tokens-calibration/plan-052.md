---
id: PLAN-052
title: MCP injection scanner — close C-P0-01 G4/G5/G6 + unblock 42-ledger
status: done
created: 2026-04-27
completed_at: 2026-04-29
budget_tokens: 400-600k
budget_sessions: 5-15
context_risk: high
sprint: none
level: L3
tags: [mcp-scanner, security, injection, done]
---

# PLAN-052 — MCP Injection Scanner

## 4. Phases

### §4.0. Phase table

| Phase | Goal | Files touched | Canonical | Reversibility | Tokens (in/out) | Tag |
|---|---|---|---|---|---|---|
| 0 | Pre-plan brainstorm + Round 1 debate (5 archetypes) | spec.md + debate/round-1/ | no | HIGH | ~120k / ~70k | v1.11.0 |
| 1 | Detection lib — new hook _lib/mcp_injection_scan.py | _lib/mcp_injection_scan.py (new script 300+ LoC) + tests | no | HIGH | ~80k / ~50k | v1.11.0 |
| 2 | PostToolUse hook check_mcp_response.py | check_mcp_response.py (new hook) + settings.json | **YES** | MEDIUM | ~50k / ~30k | v1.11.0 |
| 3 | 50 adversarial fixtures + soak harness | tests/fixtures/mcp-injection/ (50 files) + harness | no | HIGH | ~60k / ~40k | v1.11.0 |
| 4 | Soak window validation + FPR measurement | soak/baseline.md + empirical run | no | n/a | ~30k / ~15k | v1.11.0 |
| 5 | STRICT mode + env var kill-switch | check_mcp_response.py (canonical edit) + settings.json | **YES** | MEDIUM | ~40k / ~25k | v1.11.0 |
| 6 | audit_emit wire-up (emit_mcp_injection_finding) | audit_emit.py canonical + tests | **YES** | MEDIUM | ~60k / ~30k | v1.11.0 |
| **CEO orchestration** | session reads + decisions | session context | n/a | n/a | ~80k / ~40k | n/a |

**Total:** ~520k input + ~300k output ≈ **~820k cumulative tokens**
