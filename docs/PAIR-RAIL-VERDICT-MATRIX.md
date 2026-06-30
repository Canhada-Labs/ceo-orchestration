# Pair-Rail Asymmetric VETO Matrix — Cases A-F Reference

**Plan:** PLAN-081 Phase 3 + 6-bis
**ADRs:** ADR-107 (mandatory L2+) · ADR-108 (cross-LLM VETO floor — **authoritative for Cases A-F enumeration**) · ADR-111 (locked corpus)
**Spec:** PLAN-075 spec.md v5 §11

This is the operational reference for the Pair-Rail Cases A-F. All
case definitions in this document MUST agree with ADR-108 §Decision —
ADR-108 is the canonical source of truth.

## §1. Overview — what asymmetric matrix means

Pair-Rail dispatches 2 LLMs per L2+ task: typically Claude Opus as
reviewer and Codex as coder/peer-reviewer. Each emits a verdict
(PASS / BLOCK / ADVISORY) and the dispatch is classified into ONE of
6 enumerated cases per ADR-108. The matrix is **intentionally
asymmetric** — it is NOT a Cartesian product of all PASS/BLOCK
combinations. Instead, the cases enumerate the operational situations
that have distinct handling:

- A two-LLM agreement case (A / D)
- A reviewer-VETO case where Claude blocks (C — VETO floor)
- A coder-VETO-with-precondition case (B — Codex BLOCK gated by rubric ID)
- A divergence case driven by Jaccard semantic similarity (E)
- A fail-OPEN case for Codex outage / timeout / malformed output (F)

The asymmetry preserves Claude Opus VETO authority per ADR-052 (Case C
hard-blocks; Codex PASS does NOT unblock) while permitting Codex to
contribute as a peer-blocker with precondition guardrails (Case B).

## §2. Cases A-F matrix table (per ADR-108 §Decision)

| Case | Trigger | Outcome | Audit action | Rationale |
|---|---|---|---|---|
| A | Both PASS | dispatch proceeds | `pair_rail_case` (verdict=PASS, case=A) | Cross-LLM agreement — clean. |
| B | Claude PASS + Codex BLOCK | block IFF preconditions met (see §3); else fail-OPEN advisory | `pair_rail_case` (verdict=BLOCK or ADVISORY, case=B, precondition_met=bool) | Asymmetric — Codex peer block requires rubric guardrail. |
| C | Claude BLOCK + Codex PASS | hard-block (Claude Opus VETO authority preserved) | `pair_rail_case` (verdict=BLOCK, case=C) | ADR-052 — Claude reviewer VETO is non-negotiable. Codex PASS does NOT unblock. |
| D | Both BLOCK | hard-block; escalate | `pair_rail_case` (verdict=BLOCK, case=D) | High-confidence agreed block. |
| E | Divergent (Jaccard ≤ 0.3 between coder/reviewer notes) | flag for human review; allow with `systemMessage` warning | `pair_rail_case` (verdict=ADVISORY, case=E, jaccard=<float>) | Both LLMs returned advisory but disagreement is semantic, not verdict-level. Owner triage. |
| F | Codex timeout / outage / malformed output | fail-OPEN per ADR-106 hook semantics | `pair_rail_case` (verdict=PASS, case=F, codex_verdict=TIMEOUT|MALFORMED) | Hooks NEVER block on infra failure. Outage is audit-emitted; Owner monitors via `audit-query.py case-summary`. |

## §3. Case B precondition (asymmetric handling per ADR-108 §Decision)

Case B (Claude PASS + Codex BLOCK) is the asymmetric case requiring a
precondition before the block takes effect. The precondition is
enforced by `check_pair_rail.py:_validate_provider_pair()` — if not
met, the case downgrades to **Case B'** (advisory, fail-OPEN per
ADR-106). The Owner CANNOT dismiss a precondition-met Case B without
ADR rebut.

**Precondition (all 3 required):**

1. `file:line` cited in the verdict envelope
2. `rubric_violation_id` ∈ `.claude/policies/rubric-violation-catalogue.yaml` (19 enumerated IDs)
3. `severity` ∈ {P0, P1}

**Severity routing (ADR-108 §Operational labeling protocol):**

| severity_default in catalogue | Behavior |
|---|---|
| P0 | mechanically blocks immediately on Case B precondition met |
| P1 | 24h human-triage grace window via `CEO_PAIR_RAIL_HUMAN_TRIAGE_HOURS=24` env (default 24h); T+24h unlabeled = closes as advisory; explicit Owner upgrade to `tp` blocks |

**Owner labels (per ADR-108 §Owner labeling protocol):**

- `fp` — false-positive (Codex was wrong; close as advisory)
- `tp` — true-positive (block stands)
- `triage_pending` — extends grace by 24h; max 1 extension before mechanical close-as-advisory
- `retracted` — explicit revocation of prior label (creates new chain entry that supersedes)

Append via `audit-query.py label --run-id <id> --case B --label <fp|tp|triage_pending|retracted>`. Records are HMAC-SHA256 chained in `.claude/scripts/audit-log-labels.jsonl` to prevent silent retroactive editing.

## §4. Cases E and F (advisory + fail-OPEN propagation)

**Case E (Jaccard divergence):** When both LLMs return advisory with
Jaccard semantic similarity ≤ 0.3, dispatch proceeds with a
`systemMessage` warning to the next turn. Owner reviews via
`audit-query.py case-summary --window-days 7` looking for `case=E`
spikes. Persistent E spikes → reopen criterion under ADR-108
§FP-rate.

**Case F (Codex outage):** Codex timeout / connection error / malformed
output triggers fail-OPEN per ADR-106 hook semantics (hooks NEVER block
on infra failure). The outage IS audit-emitted (`pair_rail_case case=F
codex_verdict=TIMEOUT|MALFORMED`) — fail-OPEN is NOT silent. SOC
alerting on `case=F` rate spike >5% over 1h surfaces DoS attack
patterns (T-6 in `docs/CROSS-LLM-THREAT-MODEL.md`).

## §5. Disambiguation — divergent_rate vs disagreement_rate

These two metrics are often confused. Authoritative definitions:

**`disagreement_rate`** — fraction of Case-B/C/D/E events (any
non-agreement case) over total dispatches:
```
disagreement_rate = count(case ∈ {B, C, D, E}) / count(all pair_rail_case events)
```
Healthy range: 5%–25% per ADR-108 §Operational. Outside range
triggers reopen (high disagreement = LLMs poorly calibrated; low =
monoculture lurking).

**`divergent_rate`** — fraction of Case-E events specifically (semantic
divergence detected via Jaccard ≤ 0.3) over total dispatches:
```
divergent_rate = count(case == E) / count(all pair_rail_case events)
```
Healthy range: typically 1%–5%. Higher = systematic semantic gap
between Codex and Claude reasoning style.

The two metrics complement each other:
- `disagreement_rate` = total cross-LLM signal (block + advisory + jaccard divergence + outage)
- `divergent_rate` = Jaccard-divergence subset specifically

## §6. Worked examples (one per case)

### Case A (both PASS)
- **Fixture:** `.claude/plans/PLAN-081/corpus/locked/adversarial/red-herring-comments-payment-flow.py`
- **Coder verdict envelope:** `{verdict: "PASS", file_line_cites: [], notes: "decoy comments noted; code is correct"}`
- **Reviewer verdict envelope:** `{verdict: "PASS", file_line_cites: [], notes: "ASCII-digit regex valid"}`
- **Dispatcher action:** allow; emit `pair_rail_case verdict=PASS case=A`

### Case B (Codex BLOCK + Claude PASS, precondition met)
- **Fixture:** `.claude/plans/PLAN-081/corpus/locked/trivial/sql-injection-user-search.py`
- **Coder (Codex) verdict envelope:** `{verdict: "BLOCK", file_line_cites: ["sql-injection-user-search.py:43"], rubric_violation_id: "sec-injection-sql", severity: "P0", notes: "f-string SQL concat"}`
- **Reviewer (Claude) verdict envelope:** `{verdict: "PASS", file_line_cites: [], notes: "review missed it on first pass"}`
- **Precondition check:** `file:line` ✓ + `rubric_violation_id ∈ catalogue` ✓ + `severity=P0` ✓ → precondition met
- **Dispatcher action:** block; emit `pair_rail_case verdict=BLOCK case=B precondition_met=true rubric_violation_id=sec-injection-sql severity=P0`

### Case C (Claude BLOCK + Codex PASS — VETO authority preserved)
- **Fixture:** `.claude/plans/PLAN-081/corpus/locked/medium/path-traversal-asset-fetch.py`
- **Coder (Codex) verdict envelope:** `{verdict: "PASS", file_line_cites: [], notes: "startswith() check looks correct"}`
- **Reviewer (Claude) verdict envelope:** `{verdict: "BLOCK", file_line_cites: ["path-traversal-asset-fetch.py:78"], rubric_violation_id: "sec-input-no-validation", severity: "P1", notes: "string startswith fails on `..` traversal payloads"}`
- **Dispatcher action:** block (Claude VETO authority); emit `pair_rail_case verdict=BLOCK case=C`

### Case D (both BLOCK)
- **Fixture:** `.claude/plans/PLAN-081/corpus/locked/trivial/jwt-alg-none-bypass.py`
- **Both verdict envelopes:** `{verdict: "BLOCK", file_line_cites: [...], rubric_violation_id: "sec-crypto-alg-none", severity: "P0"}`
- **Dispatcher action:** block + escalate; emit `pair_rail_case verdict=BLOCK case=D`

### Case E (Jaccard divergence)
- **Scenario:** L3 architectural change. Coder notes focus on type-system implications; Reviewer notes focus on backwards-compat shims. Both return ADVISORY but the union of their recommendation tokens has Jaccard ≤ 0.3.
- **Coder verdict envelope:** `{verdict: "ADVISORY", file_line_cites: [...], notes: "Generic[T] introduces variance constraint that breaks ABCMeta subclasses"}`
- **Reviewer verdict envelope:** `{verdict: "ADVISORY", file_line_cites: [...], notes: "consider keeping the legacy `__init_subclass__` path for adopter migration window"}`
- **Dispatcher action:** allow with `systemMessage`; emit `pair_rail_case verdict=ADVISORY case=E jaccard=0.18`

### Case F (Codex outage / fail-OPEN)
- **Scenario:** Codex CLI subprocess times out at 240s after retry.
- **Codex stdout:** empty / truncated
- **Reviewer envelope:** unchanged (Claude completed fine)
- **Dispatcher action:** allow with `systemMessage` warning; emit `pair_rail_case verdict=PASS case=F codex_verdict=TIMEOUT`

## §7. Operational metrics (from audit log)

```bash
# Case distribution over last 7 days (advisory rollup — exact sub-command name
# emitted by `audit-query.py` when used in operational queries)
.claude/scripts/audit-query.py case-summary --window-days 7

# Case-B FP rate aggregator (Wilson 95% bounds; reopen-trigger threshold 0.30)
.claude/scripts/audit-query.py fp-rate --window-days 30

# Codex codando deny-list hit summary
.claude/scripts/audit-query.py codex-writeguard-summary --window-days 30
```

**Healthy distribution** (per ADR-108 §Operational):
- Case A (both PASS): 70%–85% (most dispatches clean)
- Case B (precondition-met blocks): 1%–8%
- Case C (Claude VETO): 2%–10%
- Case D (both BLOCK): 1%–5%
- Case E (Jaccard divergence): 1%–5%
- Case F (fail-OPEN): <2%

**Concerning patterns:**
- Case A < 60% → both LLMs over-blocking; check rubric drift
- Case F > 5% sustained → Codex CLI / connectivity issue OR T-6 DoS
- `fp_rate_lower_bound > 30%` (Wilson) → `fp_rate_30d_above_30pct` predicate fires; `disable_predicate_eval.py` disables pair-rail for affected archetypes (ADR-108 §FP-rate reopen criterion)

## §8. Cross-references

- `.claude/adr/ADR-052-multi-model-dispatch-by-role.md` — Claude Opus VETO authority preserved per ADR-108 Case C
- `.claude/adr/ADR-106-codex-mcp-adapter-contract.md` — fail-OPEN semantics for Cases B' / F
- `.claude/adr/ADR-107-pair-rail-mandatory-l2-plus.md` — L2+ mandatory dispatch trigger
- `.claude/adr/ADR-108-cross-llm-veto-floor.md` — **authoritative source of truth for Cases A-F** + Owner labeling protocol + FP-rate reopen criterion
- `.claude/adr/ADR-111-locked-corpus-governance.md` — locked-corpus N=15 fixtures exercise specific cases
- `.claude/policies/rubric-violation-catalogue.yaml` — 19 rubric IDs for Case-B precondition
- `.claude/hooks/check_pair_rail.py:_validate_provider_pair()` — case classifier implementation
- `.claude/dispatcher/disable_predicate_eval.py` — `fp_rate_30d_above_30pct` predicate
- `docs/CROSS-LLM-THREAT-MODEL.md` — T-1 through T-9 threat catalog (Case F intersects T-6 DoS)
- `.claude/skills/core/cross-llm-pair-review/SKILL.md` — operational SKILL teaching pair-rail invocation
