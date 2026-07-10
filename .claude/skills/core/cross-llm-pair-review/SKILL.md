---
name: cross-llm-pair-review
description: Cross-LLM Pair-Rail dispatch + verdict interpretation — when to invoke, Cases A-F asymmetric matrix outcomes, Owner override semantics, post-verdict labeling protocol, promotion gate workflow, and anti-patterns to avoid.
when_to_invoke: |
  - Any L2+ task (multi-file refactor; security-critical change; new ADR)
  - Manual cross-LLM second opinion needed (CEO uncertainty on a P0 finding)
  - Investigating a Case-B advisory in audit-query.py output
  - Checking promotion gate eligibility before v1.x.0 GA tag
plan_refs: [PLAN-075, PLAN-081]
adr_refs: [ADR-052, ADR-105, ADR-106, ADR-107, ADR-108, ADR-111]
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 3
risk_class: high
stack: []
context_budget_tokens: 600
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 5}
  engine: {active: true, priority: 4}
  fintech: {active: true, priority: 3}
  trading-readonly: {active: true, priority: 3}
  generic: {active: true, priority: 5}
activation_triggers:
  - {event: plan-opened}
  - {event: help-me-invoked, regex: "(?i)cross.?llm|codex|pair.?rail"}
---

# Cross-LLM Pair-Review Skill

## §1. Why pair-rail exists

Single-LLM review has a systematic blind spot: when the reviewer and
the model that produced the code share architectural / training-set
priors, they share the same blind spots. Cross-LLM disagreement is a
detection signal: when Codex (a different model family with different
priors) flags an issue Claude missed, the disagreement itself is
diagnostic regardless of which side is correct.

PLAN-075 R1 motivated this by measuring a 7.3pp gap between
Codex-only review and Claude-only review on the same locked-corpus
fixtures — neither LLM caught a strict superset; their misses were
disjoint. Pair-Rail closes that gap by requiring both verdicts before
proceeding on L2+ tasks (multi-file changes, security-critical edits,
new ADRs).

The architecture is "asymmetric" rather than "redundant": Claude
Opus retains VETO authority (Case C — see §3), and Codex peer-blocks
only with rubric-violation-ID preconditions (Case B). See
ADR-107 (mandatory L2+) and ADR-108 (cross-LLM VETO floor + asymmetric
matrix) for the binding governance decisions; ADR-108 is the
**authoritative source of truth** for Cases A-F semantics.

## §2. When to dispatch pair-rail

| Task tier | Coder | Reviewer | Notes |
|---|---|---|---|
| L0 (trivial change, <10 LoC, no governance) | single LLM (Claude) | none | overhead not justified |
| L1 (single-file, <100 LoC, low-risk) | single LLM | single LLM (different archetype) | optional pair-rail |
| **L2+ (multi-file, security/governance, ADRs)** | **Codex** | **Claude** | **MANDATORY per ADR-107** |
| Owner-flagged P0 (any size) | Codex | Claude | mandatory |

Mandatory invocation:

```bash
.claude/scripts/inject-agent-context.sh --pair-mode --coder=codex --reviewer=claude
```

The dispatcher reads `.claude/dispatcher/routing-matrix.yaml` to select
the appropriate archetype pair per task scope (8 archetypes covered;
each row declares `coder_adapter`, `reviewer_adapter`,
`reviewer_sandbox`, and `disable_predicates`).

## §3. Reading verdict outcomes (Cases A-F per ADR-108)

Brief operational table — full Case definitions + worked examples are
in `docs/PAIR-RAIL-VERDICT-MATRIX.md`.

| Case | Trigger | Owner action |
|---|---|---|
| A (both PASS) | dispatch proceeds | None — emit `pair_rail_case verdict=PASS case=A` |
| B (Claude PASS + Codex BLOCK) | block IFF preconditions met; else advisory fail-OPEN | If precondition_met=true → block; Owner labels post-hoc via `audit-query.py label` |
| C (Claude BLOCK + Codex PASS) | hard-block (Claude VETO) | Block stands. Codex PASS does NOT unblock per ADR-052. |
| D (both BLOCK) | hard-block; escalate | Block + investigate (both LLMs agreed) |
| E (Jaccard ≤ 0.3) | allow with `systemMessage` warning | Owner reads warning; persistent E spikes → reopen criterion |
| F (Codex timeout/outage) | fail-OPEN per ADR-106 | Hooks never block on infra failure; audit-emit is non-silent |

**Case B precondition checklist** (per ADR-108 §Decision):

1. `file:line` cited in verdict envelope
2. `rubric_violation_id` ∈ `.claude/policies/rubric-violation-catalogue.yaml` (19 IDs)
3. `severity` ∈ {P0, P1}

If any precondition is missing → Case B' (advisory fail-OPEN). Owner
CANNOT dismiss a precondition-met Case B without ADR rebut.

## §4. Owner labeling protocol (Case-B post-hoc triage)

Per ADR-108 §Owner labeling protocol — 4 valid labels:

```bash
# False-positive (Codex was wrong; close as advisory)
.claude/scripts/audit-query.py label \
  --run-id <pair_rail_run_id> --case B --label fp

# True-positive (block stands)
.claude/scripts/audit-query.py label \
  --run-id <pair_rail_run_id> --case B --label tp

# Triage pending — extends grace by 24h (max 1 extension)
.claude/scripts/audit-query.py label \
  --run-id <pair_rail_run_id> --case B --label triage_pending

# Revoke prior label (creates new chain entry that supersedes)
.claude/scripts/audit-query.py label \
  --run-id <pair_rail_run_id> --case B --label retracted
```

Labels are HMAC-SHA256 chained in `.claude/scripts/audit-log-labels.jsonl`
to prevent silent retroactive editing. The chain is verified on every
read (via `audit-query.py fp-rate` or `audit-query.py label`); any
record whose computed HMAC ≠ stored HMAC raises `ValueError` with the
broken record index.

P1 severity: 24h grace window via `CEO_PAIR_RAIL_HUMAN_TRIAGE_HOURS=24`
env (default 24h). Unlabeled P1 events close as advisory at T+24h.
P0 severity: blocks immediately; Owner labels are forensic, not
operational gating.

## §5. Override semantics

Pair-Rail can be disabled via env vars:

```bash
# Disable ALL pair-rail dispatch (entire-architecture kill switch)
export CEO_PAIR_RAIL_DISABLE=1

# Disable Phase 5 codando ONLY (Codex still reviews, but does NOT write canonical files)
export CEO_CODEX_FILEWRITE_DISABLE=1
```

Each disable emits an audit event:
- `pair_rail_disable_emitted` (whole architecture)
- `pair_rail_codex_filewrite_disabled` (Phase 5 codando only)

Use only with documented reason. Persistent disable >24h triggers
forensic review per ADR-108 §Reopen criteria. Audit-query for either
event:

```bash
.claude/scripts/audit-query.py search 'pair_rail_disable_emitted'
```

## §6. Promotion gate (Phase 4 / 4-bis)

Locked corpus N=15 governs production-readiness:

```bash
python3 .claude/scripts/run-promotion-gate.py
```

Verdict logic per ADR-108 §Operational + R1 C6:

| Pass-1 result | Outcome |
|---|---|
| catch_rate=15/15 + fp_rate≤15% + schema_adherence=100% | AUTO-FLIP review-only → coder |
| catch_rate=14/15 with 1 timeout | Pass-2 retry; if 1/1 → AUTO-FLIP |
| catch_rate <14/15 | manual triage forensic artifact (STAY in review-only) |
| catch_rate <12/15 | failure — Owner reads + decides reopen path |

Per ADR-111, the locked corpus is canonical-guarded (post-Phase-4-bis
ceremony). Mutations require sentinel-gated edits + ADR-111 amendment.

## §7. When NOT to use pair-rail

| Scenario | Recommendation |
|---|---|
| L0 trivial tasks (<10 LoC, no governance) | Skip — overhead > value |
| Time-critical incident response | Skip — single LLM faster; pair-rail adds 3-5 min |
| Read-only research / auditing (no write surface) | Skip — no enforcement needed |
| `audit-query.py fp-rate` shows lower_bound >30% | DO NOT use until reopen ceremony resolves — predicate `fp_rate_30d_above_30pct` will disable for affected archetypes |
| Codex CLI broken / catch_rate <80% | Skip — verify via `audit-query.py case-summary --window-days 7` first |
| Phase-2-advisory archetypes (per routing matrix) | Skip — those rows declare `coder_adapter: advisory_only` |

## §8. Anti-patterns

- ❌ Bypassing Pair-Rail on L2+ via `CEO_PAIR_RAIL_DISABLE=1` without documented reason — audit emit makes this visible; persistent abuse triggers reopen
- ❌ Hand-editing `.claude/dispatcher/routing-matrix.yaml` to remove archetype rows — canonical-guarded; requires sentinel + ADR rebut
- ❌ Mutating locked corpus fixtures without ADR-111 amendment — breaks the cross-LLM disagreement signal that the corpus provides
- ❌ Treating Case-B advisory as "ignore" — Owner labeling protocol exists for a reason; label as `fp` if you decide it was wrong, not just silently dismiss
- ❌ Skipping Case-B precondition check — if `rubric_violation_id` is missing, the case is Case B' (advisory), NOT Case B; do NOT treat Case B' as blocking
- ❌ Re-using a `triage_pending` label more than once per run-id — protocol allows max 1 extension before mechanical close-as-advisory

## §9. Cross-references

| Source | What it provides |
|---|---|
| `.claude/adr/ADR-052-multi-model-dispatch-by-role.md` | Claude Opus VETO authority preserved per Case C |
| `.claude/adr/ADR-105-multi-llm-coordinated-supersede.md` | Supersedes ADRs 084/085/096 in Pair-Rail context |
| `.claude/adr/ADR-106-codex-mcp-adapter-contract.md` | fail-OPEN semantics for Cases B' / F |
| `.claude/adr/ADR-107-pair-rail-mandatory-l2-plus.md` | L2+ mandatory dispatch trigger |
| `.claude/adr/ADR-108-cross-llm-veto-floor.md` | **Authoritative source of truth for Cases A-F** + Owner labeling + FP-rate reopen |
| `.claude/adr/ADR-111-locked-corpus-governance.md` | Locked-corpus N=15 governance |
| `.claude/policies/rubric-violation-catalogue.yaml` | 19 rubric IDs for Case-B precondition |
| `.claude/dispatcher/routing-matrix.yaml` | 8-archetype pair-rail capability matrix |
| `.claude/hooks/check_pair_rail.py` | Case classifier (`_validate_provider_pair()` + `_decide()`) |
| `.claude/scripts/audit-query.py` | Operational queries: `fp-rate`, `label`, `codex-writeguard-summary`, `case-summary` |
| `.claude/scripts/audit-log-labels.jsonl` | HMAC-chained Owner label store |
| `.claude/scripts/run-promotion-gate.py` | Phase 4 / 4-bis promotion gate |
| `docs/CROSS-LLM-THREAT-MODEL.md` | T-1 through T-9 threat catalog |
| `docs/PAIR-RAIL-VERDICT-MATRIX.md` | Full Cases A-F reference + worked examples |
