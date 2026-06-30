---
id: ADR-142
title: Opus 4.8 model bump — atomic VETO-floor + dispatch-table modernization
status: ACCEPTED
decision_date: 2026-05-29
accepted_at: 2026-05-29
accepting_session: S186
ratified_by: "Owner (S186) — 'ratifica o model-bump'; VETO-floor ceremony"
proposing_session: S185
authorization: "PLAN-120 readiness audit (Eixo 5) E5-F2..F15 + E7-F4 — Opus 4.8 currency gap. Web-confirmed 2026-05-29 from docs.anthropic.com/en/docs/about-claude/models/overview: claude-opus-4-8 is the current Opus API ID at $5/$25 per MTok (3x cheaper than claude-opus-4-7 at $15/$75); a 'Migrating to Claude Opus 4.8' guide exists. PROPOSED pending Owner GPG + the standard ADR-052 §Model-ID-bump benchmark gate."
owner: vp-engineering
plan: PLAN-120-framework-readiness-closure-audit
amends: ADR-052
related: [ADR-052, ADR-064, ADR-080, ADR-063]
---

# ADR-142 — Opus 4.8 model bump (atomic)

**Status:** PROPOSED (S185, 2026-05-29)
**Blast radius:** L2 (model-ID string across VETO-floor enforcement + dispatch table + cost tables; no schema-shape change)
**Supersedes:** none
**Superseded by:** none
**Depends on:** ADR-052 (multi-model dispatch by role) §Model-ID-bump recipe; ADR-064 (VETO-floor enforcement)

## Context

The framework pins every VETO-floor agent role and the CEO orchestration
model to `claude-opus-4-7`. As of 2026-05-29, Anthropic's current Opus
flagship is **`claude-opus-4-8`**, priced at **$5 / MTok input, $25 /
MTok output** — 3x cheaper than `claude-opus-4-7` ($15 / $75). The
framework's Opus-heavy cost estimates are therefore ~3x inflated against
the live rate, and the closed `MODEL_ID` enum / `VETO_FLOOR_MODEL`
constant / `_ADR_052_ROLE_TO_MODEL` dispatch table all name a
non-current model ID. PLAN-120 eixo-0 preflight recorded
`claude-opus-4-8 = 0 files; claude-opus-4-7 = 240 files`.

ADR-052 §Role-to-model distribution names the specific Opus ID, and
`VERSIONING.md` §Model ID bumps documents that an ID change is **not
silent** — it requires this ADR + a benchmark gate.

## Decision

Adopt `claude-opus-4-8` as the canonical Opus model ID, replacing
`claude-opus-4-7` everywhere it appears as a VETO-floor / dispatch /
route / cost / template / SPEC value. The bump is **ONE ATOMIC change**:
a partial application produces split-brain VETO enforcement (the
closed-enum membership gate at `loader.py:432` `is_known_model()` and
the spawn-time VETO-floor check at `agent_frontmatter.py:204` would
disagree on the canonical Opus string).

The atomic bump-set is exactly the sites enumerated below (also recorded
in PLAN-120 deliverables `remediation-backlog.md` E5-F2..F15 + E7-F4):

1. `MODEL_ID` enum — `.claude/hooks/_lib/tier_policy/_types.py:94`
   (`OPUS47 = "claude-opus-4-8"`; KERNEL).
2. CLI `VALID_MODEL_IDS` + `MODEL_ID` Literal — `.claude/scripts/tier_policy_cli/_types.py:26,29`.
3. `VETO_FLOOR_MODEL` — `.claude/hooks/_lib/agent_frontmatter.py:118` (KERNEL).
4. 5 VETO agent frontmatter `model:` fields — `.claude/agents/{code-reviewer,security-engineer,incident-commander,identity-trust-architect,threat-detection-engineer}.md:6` (canonical-guarded).
5. `_ADR_052_ROLE_TO_MODEL` dispatch table — `.claude/hooks/audit_log.py:890-917` (7 Opus rows) + secondary devops drift fix `claude-sonnet-4-6` -> `claude-haiku-4-5-20251001` at L894 (KERNEL).
6. ADR-052 normative table + inline example + validation snippet — `.claude/adr/ADR-052-multi-model-dispatch-by-role.md:68-69,105,300,342`.
7. Tier-policy templates — `templates/.claude/tier-policy.json:7,12` + `npm/templates/.claude/tier-policy.json:7,12`.
8. Test rebaseline — `test_tier_policy_types.py`, `test_veto_floor_bijection.py`, `test_adr_052_role_to_model_coverage.py` (`_EXPECTED_FLOOR`), `test_audit_log_v2_8_model.py`, `test_model_routing_resolve.py`, `test_model_routing_resolve_full.py`.
9. `model_routing.py` routing table — `.claude/hooks/_lib/model_routing.py:61-62` (KERNEL).
10. SPEC Literal enum + VERSIONING bump SOP — `SPEC/v1/tier-policy.schema.md:105-106`, `SPEC/v1/tournament-report.schema.md:50`, `VERSIONING.md:146`.
11. FROZEN_BASELINE default_model — `.claude/hooks/_lib/tier_policy/_constants.py:324` (KERNEL).
12. Skill routing tables — `.claude/skills/core/llm-routing-and-finops/SKILL.md`, `.claude/skills/domains/fintech/skills/blockchain-security-audit/SKILL.md` (advisory).
13. CLI VETO_HARDCODE — `.claude/scripts/tier_policy_cli/_constants.py:45-46`.
14. Spawn router — `.claude/scripts/task-route.py:511,520,528,539`.
15. Tournament pricing/judge — `.claude/scripts/tournament/runner.py:39,45,88` + `reporter.py:133`.
16. npm published mirror — every item above mirrored under `npm/.claude/**` in lockstep (byte-identical at HEAD).

### Haiku registry normalization — DEFERRED (E0-F3 / E5-F1 stays open)

Audit E5-F1 / E0-F3 found two registries disagree on the Haiku ID form
(hook `MODEL_ID` enum stores **bare** `claude-haiku-4-5`; CLI/agent/template
store **date-stamped** `claude-haiku-4-5-20251001`). Full normalization has a
large blast radius (the enum + `loader.py is_known_model()` + ~6 test files +
stub routing tables + configs), so this bump is **scoped to the Opus 4.8 bump
ONLY** and leaves Haiku **consistently bare** everywhere it was bare (enum,
`model_routing.py`, and the model_routing tests all stay bare — no split-brain).
The ONE Haiku change here is the **E5-F7 devops drift fix**: `audit_log.py`
devops `claude-sonnet-4-6` -> `claude-haiku-4-5-20251001` (a doc-dict row, not
enum-validated) to match ADR-052 §Role-to-model + `agents/devops.md`. The full
registry normalization (E0-F3) is DEFERRED to a separate focused effort with
its own test pass — see PLAN-120-FOLLOWUP receipts/disposition.md.

## Pricing (current flagship, web-verified 2026-05-29)

| Model | Input $/MTok | Output $/MTok |
|-------|-------------:|--------------:|
| `claude-opus-4-8` (current flagship) | 5.00 | 25.00 |
| `claude-sonnet-4-6` | 3.00 | 15.00 |
| `claude-haiku-4-5-20251001` | 1.00 | 5.00 |

(Prior `claude-opus-4-7` was $15 / $75; stale tables that show Haiku at
$0.25 / $1.25 are out of date.)

## Consequences

- VETO-floor enforcement, the closed `MODEL_ID` membership gate, the
  spawn-time frontmatter check, the audit dispatch fallback, the
  tier-policy templates, the SPEC Literal enum, and both cost/tournament
  pricing paths all name `claude-opus-4-8` consistently.
- Opus-heavy plan `budget_usd_estimate` fields drop ~3x against the live
  rate; historical `claude-opus-4-7` cost rows are RETAINED in pricing
  tables for log-replay of past sessions.
- The Haiku registry split is closed; no more silent `unknown_model`
  fallback for date-stamped Haiku policies.

## ADR-052 §Model-ID-bump recipe compliance

This ADR is the not-silent authorization VERSIONING.md §Model ID bumps
requires. Before MERGE the Owner must run the benchmark gate
(`.claude/plans/PLAN-020/rubrics/<archetype>.yaml`, pass-rate ≥ baseline)
and attach the evidence file, per ADR-052 §Consequences. ADR-064
VETO-floor semantics are unchanged — only the model string moves.
