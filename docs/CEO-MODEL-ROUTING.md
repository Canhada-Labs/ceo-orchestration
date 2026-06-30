# CEO Orchestrator Model Routing

> **See also:** [`docs/ADAPTIVE-EXECUTION-KERNEL.md`](ADAPTIVE-EXECUTION-KERNEL.md) — per-task ceremony classifier. AEK implements the model-upgrade rule from this document (5 upgrade conditions) as an advisory recommendation; it does not depend on `CEO_MODEL_DOWNSHIFT` at runtime.

> **⚠ PLAN-044 audit-v2 C3-P0-04 honest-status disclosure (Wave B,
> 2026-04-27).** The routing rule below is **DESIGN INTENT, NOT
> SHIPPED RUNTIME CODE** at v1.11.0. `CEO_MODEL_DOWNSHIFT=1` is
> read by no production code path today. Setting it has no
> behavioral effect. Treat this document as pre-implementation
> design until PLAN-048 Phase 2 lands the runtime read in
> `inject-agent-context.sh` (or a successor dispatcher). At v1.11.0
> (this disclosure's era) the CEO orchestrator ran Opus 4.7 always,
> regardless of env-var setting (see the S211 update note below for
> the current model).

**Status:** **CONDITIONAL ADOPT — RUNTIME DEFERRED** — ADR-067
flipped `PROPOSED → ACCEPTED-WITH-LIVE-TRAFFIC-FOLLOWUP` on
2026-04-21 (Session 49 P05) at the *policy* level. The runtime
implementation that would consult `CEO_MODEL_DOWNSHIFT` and apply
the upgrade-conditions rubric below remains pending PLAN-048
Phase 2 — at v1.11.0 there is **no code path** that reads the
env var.

> **UPDATED S211:** The code now runs Opus 4.8 (ADR-142 bump per
> `_constants.py` + `VETO_FLOOR_MODEL`); this document is being
> updated to reflect the new current policy.

**Default today (HEAD / S211):** CEO orchestrator runs **Opus 4.8
always** (`claude-opus-4-8[1m]`). This is by *omission* of the
runtime read, not by the kill-switch behavior described below.

**Simulated cost reduction:** 25.3 % against the Phase 0 N=8
baseline (see `.claude/plans/PLAN-048/phase-2-simulated-ab.md`).
This is a **simulation**, not measured live spend at v1.11.0.

**Kill-switch (post-PLAN-048-Phase-2):** `export
CEO_MODEL_DOWNSHIFT=0` in the session shell will revert to
Opus-always once the runtime read ships. **At v1.11.0 the kill-
switch is a no-op — the upgraded path doesn't exist.**

---

## Why this exists

ADR-052 dispatches **sub-agents** by role (VETO floor Opus 4.8; non-VETO
Sonnet or Haiku). The **CEO orchestrator itself** has no such
tiering — it runs Opus 4.8 regardless of workload. Empirically
(PLAN-048 Phase 0 baseline, N=8 sessions, 2026-04-20):

| Session class | spawn_count mean ± σ | Pattern |
|---|---|---|
| `L2-routine` | **0.0 ± 0.0** | Zero sub-agent dispatch; direct-edit polish |
| `mixed-audit` | 1.5 ± 2.1 | Occasional Explore dispatch for re-search |
| `L3+-plan-execution` | **9.8 ± 7.4** | Multi-phase sub-agent work |

L2 sessions don't use the CEO's orchestration capabilities — they
use it as a code editor with protocol discipline. Running Opus 4.8
for that load is overkill. Projected savings from CTO arithmetic
(Session 39 round-3 review): **24–32% session cost reduction** if
80% of non-ceremony turns downshift cleanly.

## The rule

**Default CEO model:** Sonnet 4.6.

**Upgrade to Opus 4.8 upfront at session start if ANY of:**

| # | Condition | Rationale |
|---|---|---|
| a | Plan frontmatter declares `level: L3` or higher | L3+ blast radius requires deep protocol compliance |
| b | Session tag ∈ `{L3+-plan-execution, debate-round, brainstorm, ceremony}` | Empirically spawn-heavy session types |
| c | Canonical-edit path declared in session scope | `.claude/hooks/*`, `.claude/adr/*`, etc. — governance-critical |
| d | VETO-protected domain touched | auth, financial-math, token handling, etc. |
| e | Expected `spawn_count` ≥ 3 by session-tag heuristic | Catches plan-execution sessions that don't use frontmatter |

**Session tag classification happens upfront** (pre-turn), not
post-hoc. If a session starts L2 and escalates, the CEO re-classifies
mid-session by invoking `/effort high` and escalation notes are
logged in audit-log. See `.claude/plans/PLAN-048/experiment-protocol.md`
§1 for the tag taxonomy and §3.3 for the exact routing rule.

## Invariants that do NOT change

These are hardcoded in the dispatcher and are **not affected** by the
routing rule above:

- **VETO roles (`code-reviewer`, `security-engineer`) ALWAYS Opus 4.8.**
  ADR-052 VETO floor is hardcoded in `_lib/adapters/*`. No flag can
  override this. Phase 1 routing only shifts the CEO orchestrator
  identity, never the staff-veto dispatch tier.
- **Sub-agent dispatch tier unchanged.** ADR-052 role-to-model mapping
  (`_lib/policy.py`) governs sub-agent tiering independently of CEO
  tier. Haiku for Explore, Sonnet for non-VETO staff, Opus 4.8 for VETO.
- **Debate round agents receive default Anthropic thinking budget.**
  The `/effort` slash-command is CEO-only (see PROTOCOL.md §Step 3).
  Spawn prompts never embed `/effort` tokens.

## Routing one-liners (PLAN-135 W4 D7 — doctrine)

These extend the invariants above. The kill ledger is stated as-is —
no route may re-litigate a killed thesis without a fresh
pre-registration.

- **Fast mode is not a routing tier.** The speed thesis is dead 5-6
  ways (PLAN-123 E2 $250 pilot through PLAN-134 W2 E5 parallel-read —
  p50 51% slower, 37% costlier at the quality ceiling). Anthropic fast
  mode (`speed: "fast"` — Opus 4.6 only at this writing) is an
  **API-billed premium** outside subscription quota; no route in this
  document may select it. Future use = a **pilot lane ONLY** via a
  PLAN-134 W3-style pre-registration (frozen kill criteria + falsifier
  + budget cap) before the first paid call. See
  `docs/HONEST-LIMITATIONS.md` §14 + `docs/provider-pricing.md`
  §Fast mode.
- **Advisor never satisfies the cross-model VETO.** The server-side
  Advisor tool (`advisor_20260301`, beta `advisor-tool-2026-03-01`)
  is same-vendor guidance — a Claude consulting a Claude. It MAY
  inform a route's reasoning as advisory input, but an ADR-145
  cross-model `code-reviewer` / security persona-demand is discharged
  ONLY by the cross-vendor Codex pair-rail (or an equivalent
  non-Anthropic reviewer). An Advisor consult is never a review
  verdict and never moves a VETO gate.
- **Eval/ceremony sessions pin `--model` explicitly.** The `/model`
  picker choice persists across sessions, and Workflow `opts.model`
  is INERT (PLAN-134 GATE-W0a verdict — the double-ground-truth
  lesson; reinforced by S1b). Any session whose result depends on
  which model actually ran — baselines, pilots, kill-gates, Owner
  ceremonies — MUST launch with an explicit `claude --model <id>`
  (or per-task `claude -p --model <id>` subprocess) and reconcile the
  served model against API ground truth (`modelUsage` per-thread
  accounting, not top-level `usage` — the W0b lesson). Never trust
  an inherited picker default for a measured run.

## Measurement

PLAN-048 Phase 2 (contingent on Phase 1 landing) runs a controlled
experiment:

- Sessions 1–3: baseline Opus-always (already captured)
- Sessions 4–6: Sonnet-default with this rule active
- Sessions 7–9: Opus-always + "would-downshift" shadow observation

Per-session we measure (from `ceo-cost.py --stream`):
- Total tokens (input/output/cache-read/cache-write)
- Total $$ cost
- Turn count + spawn count + debate rounds
- Quality signals: hook-block events, 3-strike hits, VETO events,
  manual task-completion rate (0 / 0.5 / 1)

The verdict rubric (Phase 2 close):

| Cost reduction | Quality regression | Action |
|---|---|---|
| ≥24% | None | Adopt as default |
| 10–24% | None | Conditional flag `CEO_MODEL_DOWNSHIFT=1` |
| 10–24% | Marginal | Keep experiment, refine heuristics |
| <10% | Any | Revert, document in ADR-067 |
| Any | Significant | Revert hard |

"Quality regression" definitions: see `experiment-protocol.md` §5.

## Current state (2026-04-21 Session 49 P05)

- **Phase 0 baseline** ✅ DONE (N=8, three tag classes,
  spawn_count discriminator validated).
- **Phase 1a protocol amendment** ✅ DONE (this doc + spawn_count
  gate in `experiment-protocol.md` §3).
- **Phase 1b team.md sentinel patch** — **STAGED** at
  `.claude/plans/PLAN-048/staged-code/team-md-ceo-model-routing.md`;
  Owner physical-shell sign-off remains open. Non-blocking — the
  routing rule is operational via env flag independent of this
  doc-level amendment.
- **Phase 1c live measurement** — **DEFERRED TO ADOPTER** (see
  `.claude/plans/PLAN-048/phase-1c-deferred-to-adopter.md`).
  Opt-in observability, not framework-ship requirement.
- **Phase 2 A/B** ✅ DONE via **simulated projection** from Phase 0
  baseline (see `.claude/plans/PLAN-048/phase-2-simulated-ab.md`).
  Measured **25.3 % cost reduction** under the rubric.
- **Phase 3 verdict + ADR flip** ✅ DONE — ADR-067 flipped
  `PROPOSED → ACCEPTED-WITH-LIVE-TRAFFIC-FOLLOWUP` on 2026-04-21
  (Session 49 P05 under round-12 sentinel; see
  `.claude/plans/PLAN-048/verdict.md`).

## Operational

### Enable on a session

```bash
# Before launching `claude` in the session shell:
export CEO_MODEL_DOWNSHIFT=1
claude
```

The CEO classifies session upfront (per rule above). L2-routine
sessions pick Sonnet; L3+ / debate / ceremony / canonical-edit /
VETO-protected sessions auto-upgrade to Opus. Check current tier:

```bash
grep ceo_model ~/.claude/projects/*/audit-log.jsonl | tail -5
```

### Kill-switch (instant)

```bash
# In the same shell, before the next turn:
export CEO_MODEL_DOWNSHIFT=0
```

Next CEO turn picks up the new value. Current turn finishes on the
current tier (no mid-turn model swap).

### Monitoring

Audit-log filter for the Sonnet CEO arm:

```bash
jq -r 'select(.model == "claude-sonnet-4-6"
              and .session_tag_primary != "L3+-plan-execution")
        | "\(.session_id)  \(.session_tag_primary)  \(.spawn_count)"' \
   ~/.claude/projects/*/audit-log.jsonl \
  | sort -u
```

Or use the detector to emit per-session signals:

```bash
python3 .claude/scripts/ceo-escalation-detector.py \
  --emit-metrics \
  >> .claude/plans/PLAN-048/experiment-metrics.jsonl
```

### Expected cost delta

**Simulated projection (Phase 0 baseline, N=8):** −25.3 % per
session on turn-count-weighted proxy (see
`phase-2-simulated-ab.md` for caveats). CTO Round-3 estimate
24-32 %. Adopter-1 with more L2-routine workload is
expected toward the upper end.

### Regression monitors (MUST watch)

When `CEO_MODEL_DOWNSHIFT=1` is active, these signals trigger a
revert evaluation if they exceed baseline envelopes by the rubric
thresholds in `experiment-metrics-schema.md` §Verdict mapping:

| Signal | What triggers | Action |
|---|---|---|
| `veto_non_opus` > 0 | VETO floor breach | **hard revert** (set `CEO_MODEL_DOWNSHIFT=0`) |
| `strike_counter` rate > baseline + 1σ | Sonnet under-reasoning | revert evaluation |
| `canonical_edit_block` rate > baseline + 1σ | Sonnet missing governance | revert evaluation |
| Manual task-completion < 0.9 | Sub-agents not delivering | revert evaluation |

### Live-traffic validation (Sprint 32+)

Promotion from **CONDITIONAL → UNCONDITIONAL adopt** requires
≥10 Sonnet sessions + ≥5 Opus observe-only on adopter-1
per the contract in ADR-067 §Acceptance history.

## Anti-pattern guard

If this routing rule lands and a session later shows a governance
violation (strike event, VETO fire, canonical-edit attempt blocked
mid-turn) — **do NOT silently revert**. The correct response is:

1. Note the signal in the audit-log (automatic)
2. Tag the session `regression-candidate` in the next
   `collect-baseline.py` call
3. If 3 regression-candidate sessions accumulate in a 10-session
   window → revert via `CEO_MODEL_DOWNSHIFT=0`
4. Document in Phase 2 `verdict.md` (a triggered revert is still
   valid experimental data)

Do not use the kill-switch as a "dodge the evidence" shortcut.

## References

- `.claude/plans/PLAN-048-ceo-sonnet-escalation-experiment.md` — plan
- `.claude/plans/PLAN-048/phase-0-baseline-summary.md` — empirical baseline
- `.claude/plans/PLAN-048/experiment-protocol.md` — protocol SSOT
- `.claude/plans/PLAN-048/staged-code/team-md-ceo-model-routing.md` — pending sentinel patch
- `.claude/adr/ADR-052-*.md` — dispatch tier policy (VETO floor)
- `PROTOCOL.md` — Spawn Protocol + `/effort` scope clause
