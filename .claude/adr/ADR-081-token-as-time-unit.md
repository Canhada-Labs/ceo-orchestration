---
id: ADR-081
title: Canonical time/budget unit — Claude tokens, not human dev-time
status: ACCEPTED
created: 2026-04-25
accepted_at: 2026-04-25
accepted_via: PLAN-060 Round-1 sentinel (.claude/plans/PLAN-060/architect/round-1/approved.md GPG-signed by Owner 0000000000000000000000000000000000000000)
proposed_by: CEO (PLAN-060 Phase C, per Owner directive Session 62 cont 2026-04-25)
co_signers: [Owner (gov), Principal QA Architect (template/schema impact)]
related_plans: [PLAN-059, PLAN-060]
related_adrs: [ADR-058 (debate budget), ADR-064 (tier policy budget), ADR-080 (Layer 4 backfill applies this format)]
blast_radius: L2 (forward-only schema change; existing artifacts grandfathered)
supersedes: none
superseded_by: none
closes_finding: Owner correction Session 62 cont — "para de dar prazo humano a coisas que o claude resolve em minutos"
staged_at: fa6d688
enforcement_commit: pending (set in next commit)
---

# ADR-081 — Canonical time/budget unit: Claude tokens, not human dev-time

## Context

The ceo-orchestration framework historically describes effort
estimates and budgets using human time units: `dev-dias`,
`horas`, `min`, `semana`, `1 week from today`. Examples from the
last 5 sessions:

- ADR-080 §Layer 4: "~3-5 dev-dias of CEO dispatch time"
- PLAN-059 v3: "~5-7 dev-dias of calendar block"
- Session 62 cont closeout: scheduled a `/loop`-style remote
  agent for "1 week from today" to check if Owner ceremony was
  done — when the actual ceremony is 1 GPG signature + 4 file
  ops = ~40 seconds total.

Owner correction (Session 62 cont 2026-04-25, verbatim):
> "pq esperar tanto ? quero resovler agora tud.. para de dar
> prazo humano a coisas que o claude resolve em minutos!"

The mismatch: Claude is the worker, not a human. Claude work is
bounded by tokens-per-session (1M context window for Opus 4.7 with
autocompact at ~90%), not by hours-per-day. The real planning
questions are:

1. **Does this fit in the current context window?** (token
   absolute estimate)
2. **How many sessions will this take?** (sessions integer)
3. **How risky is autocompact mid-task?** (context-risk tier)

Human time becomes relevant ONLY when waiting for external state
to change: deployment soak windows, alert accumulation,
third-party SLAs, ADR-057 FPR observation windows. For everything
else, human-time estimates are misleading — they overestimate
calendar duration AND underestimate cost-of-context-switch (each
new session pays the gate-boot cost of ~27k tokens per ADR-020
cache discipline).

## Decision

**Adopt Claude tokens + sessions + context-risk as the canonical
budget unit for all NEW plans, ADRs, schemas, and CEO
communication.** Reserve human time units for explicitly external
wait conditions.

### Format spec

Frontmatter fields (plans + ADRs):

```yaml
budget_tokens: <range>k or <number>k    # CEO-context tokens, not sub-agent tokens
budget_sessions: <integer>               # how many fresh-terminal sessions
context_risk: low | medium | high        # autocompact probability mid-task
external_wait: <description> or none     # ONLY for genuine external state
```

Free-text supplementation OK but unit must be primary:

```markdown
**Budget:** 95-125k tokens / 1 session (medium context risk —
tight on Phase B if spec phantom-claims surface)
```

### Examples

- Trivial fix: `budget_tokens: 5-15k, budget_sessions: 1, context_risk: low`
- Single SEC-P0 implementation: `budget_tokens: 95-125k, budget_sessions: 1, context_risk: medium`
- Layer 4 full matrix (PLAN-059): `budget_tokens: 1.3-2M, budget_sessions: 8-12, context_risk: high (sessions need fresh terminal each), external_wait: none`
- Soak window post-deploy: `budget_tokens: 2-5k, budget_sessions: 1, context_risk: low, external_wait: 7-day soak per ADR-057`

### Cost reference table (for estimation calibration)

Per CEO-context tokens consumed per common operation:

| Operation | Token cost |
|---|---|
| Read a file (avg 200 lines) | 1-3k |
| Edit/Write (small change) | 1-2k |
| Edit/Write (200 LoC new file) | 5-10k |
| Test suite run (pytest -q output) | 5-10k |
| validate-governance.sh | 1k |
| Commit + push | 2k |
| Single Agent dispatch summary returned to CEO | 2-5k |
| Sub-agent dispatch with skill load (full 27k sub-agent context) | 2-5k in CEO context (just the result summary) |
| Memory file write (1-2k content) | 2-3k |
| Sentinel ceremony (compose + ceremony + canonical edit) | 15-25k |
| ADR draft (full template) | 15-25k |
| Plan draft (full template) | 20-30k |
| Closeout (CLAUDE.md + memory + tests + commit) | 30-50k |

Session capacity reference (Opus 4.7, 1M context):

| Tier | Token range | Risk |
|---|---|---|
| Trivial | <50k | low |
| Small | 50-150k | low |
| Medium | 150-300k | medium |
| Large | 300-500k | high (autocompact likely) |
| Multi-session | >500k | high (split across sessions) |

### Conversion guidance for legacy artifacts

Old plans/ADRs use human time. Approximate conversion (do NOT
mass-migrate; convert opportunistically when an artifact is
already being touched):

- "1 dev-dia" ≈ ~200-400k tokens ≈ 1-2 sessions
- "1 hora CEO" ≈ ~50-150k tokens ≈ part of 1 session
- "5 min Owner ceremony" ≈ ~15-30k CEO tokens (Owner physical
  time is the binding constraint, not CEO tokens — keep human
  unit here)

## Consequences

### Positive

- Owner sees actionable budgets that map directly to "fits this
  session" / "needs N sessions".
- Eliminates over-conservative scheduling (e.g., "wait 1 week"
  for work doable in 40 seconds).
- Forces honest pre-execution estimation — token math is
  empirical (audit log has all past dispatch costs), human-time
  was vibes.
- Aligns with cache discipline (ADR-020): planning in tokens
  surfaces the gate-boot cost of new sessions explicitly.

### Negative

- Templates need update (PLAN-SCHEMA + ADR README + related
  schemas).
- Adopters of the framework who export plans externally may
  need a translation layer (token estimates → human estimates)
  for stakeholders unfamiliar with the unit.
- Token estimates depend on Claude model + context window;
  model swap (e.g., Opus 4.8 future) may shift calibration.
  Mitigation: keep cost reference table per ADR (this one,
  amend on model bump).

### Neutral

- Old artifacts grandfathered. No mass migration. Cost-amortized
  over natural editing cadence.
- Human time units allowed in body text + comments where
  contextually clear; restriction applies to FRONTMATTER fields
  + budget-style claims.

## Alternatives considered

### A. Keep human time units (REJECTED)

Continue using "dev-dias" / "horas". REJECTED because Owner
explicitly corrected this pattern + the units are decoupled from
how work actually flows (Claude session capacity, not human
calendar).

### B. Use only "sessions" as integer (REJECTED)

Drop tokens, just count sessions. REJECTED because session
capacity isn't fixed (depends on what else is in context — gate
files, prior conversation, memory). Tokens are the precise unit;
sessions is derived.

### C. Use only token absolute (REJECTED)

Drop sessions integer. REJECTED because Owner needs to know
"how many fresh terminals do I need to schedule" — a token
estimate doesn't directly answer that.

### D. Adopt model-agnostic token unit (e.g., "context-units" = 1k tokens) (REJECTED)

Abstract away model specifics. REJECTED because Anthropic SDK +
audit log already speak in literal tokens; abstracting adds a
translation layer with no benefit.

## Implementation

### Step 1 — Frontmatter spec update

Edit `.claude/plans/PLAN-SCHEMA.md` (non-canonical, free path):

- Add §Frontmatter spec entries: `budget_tokens`,
  `budget_sessions`, `context_risk`, `external_wait`.
- Mark legacy fields (`estimated_effort`, `dev_days`, etc.) as
  deprecated; old plans not affected.
- Cite this ADR.

### Step 2 — ADR template update

If `.claude/adr/README.md` defines a template, add same
frontmatter spec under sentinel scope (canonical-guarded path).

### Step 3 — Validation tooling (optional, deferred per budget)

Tiny script `.claude/scripts/check-time-unit.py` (~50-80 LoC,
~5-10k tokens to write) that scans NEW plans + ADRs for legacy
human-time keywords in frontmatter; emits advisory warnings.
Not blocking. Wire into validate-governance.sh as soft check.

Defer if PLAN-060 budget tight. Acceptable to ship ADR-081
without tooling and add later.

### Step 4 — Backfill recent ADRs (opportunistic)

ADR-080 §Layer 4 currently says "~3-5 dev-dias". Convert to
`budget_tokens: 1.3-2M, budget_sessions: 8-12, context_risk: high`
under existing sentinel scope (already covers ADR-080).

## Owner ceremony

Estimated cost: **15-30k CEO tokens + 1 GPG signature (Owner ~10 seconds).**

Single sentinel covers:

- `.claude/adr/ADR-081-token-as-time-unit.md` (new canonical ADR)
- `.claude/adr/ADR-080-rail-anomaly-h4-defense-in-depth.md` (Layer 4 §amendment)
- `.claude/adr/README.md` (template update, IF template exists)
- `.claude/plans/PLAN-SCHEMA.md` (NOT canonical-guarded; included in scope for traceability only)

Sentinel template at `.claude/plans/PLAN-060/architect/round-1/approved.md.template`
(pre-composed in Phase C); Owner runs:

```bash
cp .claude/plans/PLAN-060/architect/round-1/approved.md.template \
   .claude/plans/PLAN-060/architect/round-1/approved.md
gpg --detach-sign --armor \
   .claude/plans/PLAN-060/architect/round-1/approved.md
```

CEO completes the canonical edits + commit + push.

## Lesson permanent (for adopters)

When estimating effort for any plan / ADR / TODO:

1. Default to token estimate (CEO context + sessions integer +
   context risk).
2. Use human time ONLY when waiting on external state (deploy,
   alert, soak window, third-party SLA).
3. Skip "calendar-pending" framing for work that is purely
   CEO-driven; that's just "next session" with token estimate.

The framework is a CEO orchestration system. The CEO is Claude.
The unit is tokens.

## References

- Owner correction Session 62 cont, 2026-04-25 (verbatim above)
- Memory: `feedback_no_human_time_for_claude_work.md` (precursor)
- Memory: `feedback_vibecoder_not_cto.md` (persona constraint)
- ADR-020 — Cache discipline (gate-boot cost amortization)
- ADR-057 — FPR observation window (legitimate calendar wait example)
- ADR-058 — Debate budget (token-aware spawn limits)
- ADR-080 — Layer 4 effort estimate to be backfilled per this ADR
