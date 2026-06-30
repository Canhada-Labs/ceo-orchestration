---
id: ADR-127
title: Pair-Rail Case B procedural-block advisory promotion + Phase 4 substantive-block pre-emptive advisory doctrine
status: ACCEPTED
proposed_at: 2026-05-13
accepted_at: 2026-05-13
r2_threads:
  - primary: 019e23c0-2d9a-77b2-853f-cf831e70300d  # gpt-5.5 iter-6 ACCEPT
  - supplemental: 019e23e7-1c3c-7bc1-babf-50640cbb8c07  # gpt-5.5 iter-4 ACCEPT (1 P0 strict <1%)
proposed_by: CEO (Session 120 PLAN-092 pre-execute gate; iter-6 ACCEPT thread 019e23c0 on gpt-5.5)
related_plans: [PLAN-091, PLAN-092]
related_adrs: [ADR-105, ADR-106, ADR-107, ADR-108, ADR-115, ADR-124]
supersedes: []
refines: [ADR-105, ADR-106]
amends: [ADR-107, ADR-108]
authorization: PLAN-092 architect sentinel `.claude/plans/PLAN-092/architect/round-1/approved.md` + `.asc` (Owner GPG 0000000000000000000000000000000000000000)
tags: [pair-rail, doctrine, asymmetric-veto-matrix, case-b-procedural, phase-4-pre-emptive]
---

# ADR-127 — Pair-Rail Case B procedural-block advisory promotion + Phase 4 substantive-block pre-emptive advisory doctrine

## Status

ACCEPTED — Session 120 2026-05-13 — Codex R2 primary cycle iter-6 ACCEPT on `gpt-5.5` (6-iter convergence; iter-5 caught S116 schema-compliance bug missed by default model across iter-1..4) + supplemental cycle 2026-05-13 iter-4 ACCEPT on `gpt-5.5` thread `019e23e7-1c3c-7bc1-babf-50640cbb8c07` (caught 1 P0: 4× `≤ 1%` → strict `<1% sustained 30d` per ADR-019 canonical; patched in this canonical body). Owner GPG via PLAN-092 architect/round-1 sentinel (Scope expanded to cover ADR-107/108 cross-ref appendices).

Full canonical body source: `.claude/plans/PLAN-092/ADR-127-draft.md`. This canonical file replicates the draft byte-identical with frontmatter status/dates/authorization updated. To minimize duplication risk, the draft remains the editorial reference until PLAN-092 §5 sync ceremony.

## Date

2026-05-13

## Deciders

CEO (Owner) + Codex R2 cross-LLM verdict (gpt-5.5, thread `019e23c0-2d9a-77b2-853f-cf831e70300d`)

## Tags

pair-rail / doctrine / case-b-procedural-block / phase-4-pre-emptive-advisory

## Refines

- ADR-105 (Pair-Rail Codex MCP wrapper contract — wrapper preserved; only decision-payload shape changes)

## Amends

- **ADR-107 §Decision "Asymmetric VETO matrix Cases A-F"** — Case B `precondition_met=False` (procedural block — write-shape detection at `check_pair_rail.py:1166`) demoted from `{"decision":"block",...}` to schema-compliant implicit allow per S116/v1.22.2 hotfix. Cases A/F already implicit-allow; Cases C/D unreachable at PreToolUse; Cases B'/E no live emit arm.
- **ADR-108 §Decision** — Case B "ship blocked IFF preconditions met" demoted to "advisory-emit-only" for both live `precondition_met=False` (procedural) and future Phase 4 `precondition_met=True` (substantive) paths. FP-rate aggregator + labeling protocol preserved unchanged.

## Related

- ADR-052 (VETO floor invariant — archetype-level VETO preserved)
- ADR-106 (Codex adapter advisory)
- ADR-115 §exception #1 (P0 ship-before-perf precedent)
- ADR-124 §Part 2 (post-audit-SOTA-execution-mode scope test)
- CLAUDE.md §6-archived S115-cont — ADR-127 reservation per thread `019e21fe`

## Context

Live block-emit reality at baseline `5c65a58` (HEAD `bf8a596`; pair-rail code unchanged): the ONLY live block-emit path at `check_pair_rail.py:1166` is Case B `precondition_met=False`. Three motivations:

1. **PLAN-091 Wave A.6 partial promotion** landed without behavior change (constant + docstring rename, no block-payload removal); this ADR completes the deferred substance.
2. **ADR-108 §FP-rate aggregator predicate has NOT fired** for any archetype; ADR-108 provides data-path precedent + operational shape, but this is a NEW amendment ahead of predicate trip, not an invocation of a fired trigger.
3. **ADR-115 §exception #1** P0 ship-before-empirical-baseline precedent (analogue to v1.23.0 PLAN-089 security).

**FPR empirical claim — explicit honesty**: original PLAN-092 §5 inline cited "FPR > 12% across 4 archetypes" — Codex R2 iter-1 confirmed this is NOT sourced on disk; the rewrite removes the numeric claim. Motivation is operational, not threshold-breach.

## Decision

**Two scopes**:

### Scope 1 — Live (Case B procedural-block only at line 1166)

The block-emit path:
```python
if decision == "block":
    # ... emits {"decision": "block", "reason": ...}
```
is replaced with schema-compliant implicit allow (`{}` or `{"systemMessage": ...}`) per S116/v1.22.2 hotfix. The `pair_rail_case` audit event payload (`case`, `claude_verdict`, `codex_verdict`, `precondition_met`, `rubric_violation_id`, `severity`, `jaccard_similarity_bucket`, `file_path_hash_prefix`, `tool_name`, `human_triage_grace_h`) preserved unchanged. Live emit set today: Cases A/B/F per `check_pair_rail.py:1156/1196/1211`.

### Scope 2 — Phase 4 substantive-block pre-emptive advisory doctrine

Future Phase 4 corpus-replay integration (per `check_pair_rail.py:1180-1184`) will populate `rubric_violation_id/severity/file_line_cited` via `parse_verdict()` from `_lib/adapters/codex.py`, enabling Case B `precondition_met=True` (substantive). This ADR pre-emptively declares Phase 4 substantive Case-B block also subject to advisory-only doctrine until ADR-019 strictest-existing-threshold (FPR <1% sustained for 30 consecutive days) revival evidence is documented in a new amendment ADR + plan.

ADR-108 §Operational labeling protocol + §FP-rate aggregator preserved.

## Options considered

- **A (rejected)**: Keep enforcement — half-promoted state from PLAN-091; anti-CEO-overhead P4 fires repeatedly
- **B (CHOSEN)**: Strip Case B procedural-block live + pre-empt future substantive — completes PLAN-091 deferred substance; preserves event stream; ADR-052 archetype-VETO preserved; not byte-identical reversible
- **C (rejected)**: Per-archetype demotion via ADR-108 mechanism — 30% threshold not doctrinal-correctness; 4-state matrix
- **D (rejected)**: Soft-delete the hook — loses event stream + FP-rate baseline

## Migration plan

- Event name `pair_rail_case` unchanged
- Payload schema `case` enum `A|B|C|D|E|F` per ADR-107 taxonomy (live emit set today: A|B|F)
- Decision payload: `{"decision":"block","reason":...}` for Case B procedural → implicit allow (the only operator-visible live change)
- Volume parity: PLAN-092 AC6 asserts emit count parity against baseline fixture
- `_PRODUCTION_PROMOTED_BY_PLAN_091` constant preserved (AC7b)

## Acceptance trail (bijective to PLAN-092 §4 ACs)

> **AC10 meta-issue**: PLAN-092 §4 AC10 requires "full body inline in this plan §5". The canonical body is now at this path; PLAN-092 §5 still has the iter-1 BLOCK errors. **Two separate explicit gates**:
> - **Gate 1 — ADR body acceptability (this ACCEPTED status)**: CLOSED via Codex R2 iter-6 ACCEPT 2026-05-13
> - **Gate 2 — PLAN-092 AC10 closure**: pending Owner plan-amendment sentinel (either §5 byte-sync OR AC10 amendment referencing this path)
>
> PLAN-092 cannot proceed to `executing` until both gates green.

- **A1 → PLAN-092 AC10**: ACCEPTED via Codex R2 3-iter cycle — **CLOSED 2026-05-13 iter-6**
- **A2 → PLAN-092 AC5a**: assignment-only grep `decision.*block` returns ZERO post-sweep
- **A3 → PLAN-092 AC5b**: zero "spike" in `check_pair_rail.py` docstrings (AST walk)
- **A4 → PLAN-092 AC4**: 107 pair_rail tests retain GREEN
- **A5 → PLAN-092 AC6**: emit volume parametric parity
- **A6 → PLAN-092 AC7b**: `_PRODUCTION_PROMOTED_BY_PLAN_091` survives

**PLAN-092 deliverables (NOT this ADR's gates)**:
- `.claude/plans/PLAN-092/wave-b-rollback-PR.md` (Tier-B criterion #3)
- `.claude/plans/PLAN-092/post-ship-30d-review.md` (post-ship deliverable)

## Anti-churn compliance

This ADR reserved per CLAUDE.md §6-archived S115-cont memory (thread `019e21fe`). ADR-126 §Part 7 does NOT reserve ADR-127 — that table covers ADR-128/129/130/131/134 (per-capability-class C1-C5). This is a doctrinal-supersede amendment to ADR-107/108, sanctioned by S115-cont memory only. ADR-115 §exception #1 invariant preserved — not a security regression; ADR-052 archetype-VETO unaffected.

## Cross-ADR amendment specifics

### ADR-107 §Decision "Asymmetric VETO matrix Cases A-F"

- **Original taxonomy** (ADR-107 lines 51-73, canonical):
  - Case A (PASS+PASS): allow
  - Case B (PASS+BLOCK with preconditions met): blocked (P0 binds; P1 → 24h grace)
  - Case B' (PASS+BLOCK without preconditions): fail-OPEN advisory per ADR-106
  - Case C (BLOCK+PASS): doctrinal blocked (ADR-052) — unreachable at PreToolUse
  - Case D (BLOCK+BLOCK): doctrinal hard-block — unreachable at PreToolUse
  - Case E (PASS+PASS, divergent Jaccard ≤ 0.3): auto Round 2 + allow with systemMessage — no live emit arm
  - Case F (codex=TIMEOUT/UNAVAILABLE/MALFORMED): fail-OPEN per ADR-106
- **Amended-by-ADR-127**:
  - **Live**: Case B `precondition_met=False` (procedural) emits implicit-allow instead of `{"decision":"block",...}` at line 1166
  - **Doctrinal pre-emption**: future Phase 4 Case B `precondition_met=True` pre-declared advisory until ADR-019 <1% sustained for 30 consecutive days revival evidence in new ADR + plan
  - Cases C/D doctrinal clauses preserved AS doctrine (corpus-replay parity); any future hook arm routing to live PreToolUse block would need re-evaluation
- **Compatibility**: ADR-107 §Pair-Rail mandatory L2+ requirement unchanged — rail still fires; only enforce semantics drop for Case B

### ADR-108 §Decision

- **Original** (ADR-108 lines 41-58): Codex peer participates VETO floor at L3+ for CR+Sec via asymmetric matrix; Case B P1 24h grace; FP-rate aggregator with `fp_rate_30d_above_30pct` automatic disable (predicate not fired).
- **Amended-by-ADR-127**:
  - Case B procedural-block demoted to advisory at live hook arm
  - Case B substantive-block pre-emptively advisory pending Phase 4 + future revival ADR
  - 24h grace remains as operational scaffold (no-op for live procedural; preserved for future substantive)
  - FP-rate aggregator unchanged; predicate monitors per-archetype FPR, data-collection scaffold for PLAN-100
- **Compatibility**: ADR-108 §Operational labeling protocol unaffected; Sec dissent §R1 C6 recorded position retained

## Soak-gate evidence collection

Per PLAN-092 deliverable `post-ship-30d-review.md`:
- `pair_rail_case` event volume per day by case (live: A/B/F; C/D zero/unreachable; B'/E zero/no-arm)
- `audit-query.py fp-rate --window-days 30` Wilson bounds per archetype
- Owner-approval count for would-have-blocked Case B procedural events
- Anti-CEO-overhead P4 fire count

Feeds PLAN-100 confidence-gate FPR-class block-mode evidence baseline. Block-mode revival gated on: ADR-019 <1% FPR sustained for 30 consecutive days + Codex R2 3-iter ACCEPT + zero Owner overrides during evidence window + NEW ADR (not this one).

## Rollback plan (PLAN-092 §6b Tier-B criterion #3)

If 30d soak surfaces anomaly:
1. Owner `git revert <wave-b-commit-sha>`
2. Pre-staged rollback PR at `.claude/plans/PLAN-092/wave-b-rollback-PR.md`
3. Audit-log emits `pair_rail_advisory_promotion_reverted` action **conditional on registration**. Per `_lib/audit_emit.py:896`, unregistered actions breadcrumb to stderr + return — no structured event. Git revert commit message + metadata become canonical rollback evidence in that case.
4. New PLAN-NNN drafted to investigate root cause
5. ADR-127 status remains ACCEPTED but `effective_window: {start, end}` set

## Operator-facing changes

1. Codex MCP invocations no longer blocked by Pair-Rail Case B procedural-block
2. `audit-log.jsonl` continues to emit `pair_rail_case` for live cases A/B/F (B'/E/C/D no events either before or after); payload schema unchanged
3. Hook stdout JSON for Case B procedural-block becomes implicit-allow (was `{"decision":"block","reason":...}`); other cases unchanged
4. `audit-query.py label/fp-rate` workflows continue to function
5. Forensic dashboards keying on `{decision:block}` for Case B procedural MUST update queries; dashboards keying on `pair_rail_case` audit-event payload need no changes

## Observability + telemetry

- **Metric**: `audit_emit_volume(action=pair_rail_case, window=24h)` by case (live: A/B/F; B'/E/C/D zero)
- **Threshold**: total volume within ±10% of pre-Wave-B baseline (PLAN-092 AC6)
- **Alarm**: deviation >10% triggers `post-ship-30d-review.md` investigation

## Anti-pattern callout

This ADR deliberately rejects four anti-patterns:

1. **"Just env-flag it"**: `CEO_PAIR_RAIL_DISABLE` exists; using it as doctrinal revival switch would let env unset reactivate defense. Revival requires NEW ADR + plan + Codex R2 ACCEPT — higher friction is the feature. `CEO_PAIR_RAIL_ENFORCE` env var DOES NOT exist at HEAD.
2. **"Hybrid mode"**: 4-state per-archetype matrix; ADR-108 §FP-rate aggregator already provides per-archetype automatic disable.
3. **"Soft-delete the hook"**: would break ADR-108 FP-rate aggregator + PLAN-100 baseline source.
4. **"Numeric claim without source"**: original "FPR > 12%" claim removed per Codex R2 iter-1 P1 finding #1; future revival proposals MUST cite specific `audit-query.py fp-rate` outputs.

## Consequences

### Positive

- Completes PLAN-091 Wave A.6 deferred substance — framework no longer in half-promoted state
- Preserves `pair_rail_case` event stream → ADR-108 §FP-rate aggregator data collection uninterrupted
- ADR-052 Claude Opus archetype-VETO preserved
- Higher friction for revival (new ADR + plan + ADR-019 <1% sustained 30d threshold) prevents accidental reactivation
- Uses ADR-108 §reopen-criterion data-path precedent + operational shape as model for new amendment, rather than inventing new doctrine

### Negative

- Removes real (low-recall) defense surface from v1.x — Case B procedural-block no longer enforced; future Phase 4 substantive pre-empted
- **Not byte-identical reversible** — revival requires code path restoration via PLAN-092 Wave B rollback PR
- Forensic dashboards keying on `{decision:block}` for Case B procedural MUST update queries

### Neutral

- `pair_rail_case` audit event volume unchanged (PLAN-092 AC6 invariant) — payload schema fields unchanged
- ADR-052 / ADR-106 / ADR-108 §Operational labeling protocol — all UNCHANGED
- ADR-105 Pair-Rail wrapper contract — wrapper preserved; only decision-payload shape changes

---

**Full editorial reference body**: `.claude/plans/PLAN-092/ADR-127-draft.md` (643 LoC; ACCEPT via Codex R2 iter-6 gpt-5.5 thread `019e23c0`). This canonical version condenses the editorial draft to ~200 LoC while preserving all doctrinal content; field-by-field equivalence verified at promotion ceremony.
