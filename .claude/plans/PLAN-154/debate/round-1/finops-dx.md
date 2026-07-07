---
plan: PLAN-154
round: 1
archetype: finops-dx
skill: llm-routing-and-finops
verdict: ADJUST_PROCEED
created_at: 2026-07-06
---

## Verdict

ADJUST_PROCEED — the plan's economic instincts are already better than most
learning-loop proposals (metadata-only v1 is also the *cheapest* v1; the
TTL-30d red line doubles as a cost garbage-collector; extending the PLAN-125
rail reuses a surface that already solved hot-path economics). But every
recurring-cost lever is currently a vibe, not a number: the observe rail has
no stated zero-new-registration invariant against the p95<120ms/p99<160ms CI
gate, the distiller has no cadence / input ceiling / cursor / cost
visibility, the "~1k boot cap" contradicts nothing only because it is
unreconciled with the two injection surfaces that already exist, and the
kill-switch is the word "env" with no name, no polarity, and no registration
path. None of this needs redesign; all of it must be numbers-in-the-plan
before `draft → reviewed`. I also flag one legibility landmine the security
constraints don't cover: the dampening ordinal's *DX contract* (what survives
condensation) is unspecified, and a condensed advisory that loses its ID or
its pointer to full text is operator-training damage even when no blocking
guard is touched.

## Summary (≤ 3 bullets)

- **What it does:** import ecc's observe → distill → candidate funnel under
  this framework's governance: opt-in metadata rail on PostToolUse, offline
  cheap-model distiller into the guarded `lessons.py` store, confidence
  decay, top-3 fenced boot one-liners, advisory-only dampening, deny-once
  fact-forcing, `/lesson-evolve`.
- **Strong (from my seat):** the six binding constraints are individually the
  cheap option too — metadata-only avoids a payload store + PII pass;
  bounded lesson schema is the only thing that makes a boot cap *enforceable*;
  zero self-activation means $0 spent when the Owner doesn't engage.
- **Weak (from my seat):** the plan prices nothing. Recurring context rent
  (every session's boot injection + every spawn's lesson injection, forever)
  will dominate the one-shot distiller cost, yet only the distiller is called
  "cheap"; the spawn-side injection path already carries a 2K-token cap
  (`lessons.py:86`) that is 8× the boot cap being debated, and the plan never
  mentions it.

## Risks

- **R-FX-01 — Observe rail as a new PostToolUse registration blows the hook
  latency budget. Severity: HIGH.**
  Description: `settings.json:265` already carries ~10 PostToolUse
  registrations (confidence gate, output safety, output scan, WebFetch/MCP
  injection scanners, Codex ingress, canonical-edit forensics…), each one a
  subprocess per matching tool call through `_python-hook.sh`. The CI gate is
  p95<120ms / p99<160ms per hook (`validate.yml:996-1003`, PLAN-063 DIM-15).
  A new rail registered with a broad matcher fires on EVERY call — the single
  most expensive placement in the whole framework. The plan says "extends the
  content-free PLAN-125 WS-1 `tool_lifecycle.py` rail" but never states the
  invariant that makes that extension cheap: `tool_lifecycle.py:24-25`
  (MF-PERF-1) — *no new subprocess; the Post emit is co-located in an
  already-running PostToolUse hook*, and MF-SEC-5 keeps the PreToolUse write
  to a 0600 per-session file with zero audit-chain traffic.
  Mitigation: write the invariant into the plan: **zero new hook
  registrations**; new metadata rides `record_pre`/`record_post` in-place;
  the extended write path is added to the `hook-profiler.py` /
  `profile-opus-4-7.py --hook-latency` corpus so the existing p95/p99 CI gate
  covers the regression, not a promise.

- **R-FX-02 — Distiller economics unbounded: no cadence, no input ceiling,
  no cursor, no spend visibility. Severity: HIGH.**
  Description: "offline distiller (cheap model)" is the entire economic spec.
  The distiller's input is audit-log content (binding constraint 2); the log
  rotates at 10 MB (`CEO_AUDIT_LOG_ROTATE_BYTES`, `docs/CHEAT-SHEET.md:121`).
  Without a delta cursor each batch re-reads history, so per-run cost grows
  with log size; without a per-run input-token ceiling a chatty session
  produces an unboundedly expensive batch; without emitting its own token
  usage into the audit log the spend is invisible to `/agent-budget`
  (`budget-summary.py` + `docs/provider-pricing.md` per
  `agent-budget.md:12-20` — the rollup rail already exists and costs nothing
  to join). Cadence matters too: per-session automatic distillation converts
  a batch job into a per-session tax.
  Mitigation: plan must state (a) cadence — Owner-invoked command or
  piggyback on the nightly-hygiene advisory sweep, NOT per-session automatic;
  (b) a persisted watermark/cursor so each run consumes only the delta;
  (c) a hard per-run input-token ceiling; (d) token-usage audit events so
  `/agent-budget` shows the distiller as a line item.

- **R-FX-03 — "Cheap model" pinned via a stub resolver silently no-ops.
  Severity: MEDIUM-HIGH.**
  Description: the natural routing home is the digest tier
  (`model_routing.py:65` → `claude-haiku-4-5`), but that module says of
  itself "STUB per PLAN-086 Wave B. Full resolver overlays tier-policy"
  (`model_routing.py:72`), and `tier-policy.yml:1` is itself "STAGED …
  Owner promotion target". A plan that says "route through model_routing"
  ships a distiller whose tier pin resolves to nothing.
  Mitigation: pin the distiller model explicitly in its own invocation
  (haiku-tier id + a named env override), with a TODO pointer to adopt the
  resolver when PLAN-086 Wave B lands. Never let the tier pin depend on
  staged machinery.

- **R-FX-04 — Kill-switch env story: no name, mixed fleet polarity, and the
  S218 registration footgun. Severity: MEDIUM-HIGH.**
  Description: item 1 says only "kill-switch env". The fleet has BOTH
  polarities in production: `CEO_OUTPUT_SCAN=0` / `CEO_WEBFETCH_INJECTION_SCAN=0`
  disable (`settings.json:339,363`) while `CEO_MCP_SCANNER_DISABLE=1` /
  `CEO_SOTA_DISABLE=1` disable (`settings.json:375`, `CHEAT-SHEET.md:109`).
  For a **default-off opt-in** feature the correct precedent is
  `cost_envelope.py:31-35`: master engaged when the flag is "unset OR ==0" —
  i.e. an *enable* flag, not a *disable* flag. Separately: an unregistered
  env var is the exact S218 footgun the nightly-hygiene dimension (vi)
  (`env-inventory-check.py`) exists to catch; `CEO_LESSONS_DIR` /
  `CEO_LESSON_CONSUMER` are already registered at
  `env-inventory.json:1238,1245` and are the naming lineage to extend.
  Mitigation: name the flags in the plan: one opt-in enable (suggest
  `CEO_LEARNING_OBSERVE=1`; unset = structurally off, matching the
  vp-engineering PLAN-153 note that the "opt-in observe hook is a no-op when
  `CEO_OBSERVE` is unset"), plus `CEO_SOTA_DISABLE=1` honored as master kill
  with precedence documented (`CHEAT-SHEET.md:170`). Register every new var
  in `env-inventory.json` AND the `CHEAT-SHEET.md` env table in the same
  commit that consumes it.

- **R-FX-05 — The ~1k boot cap is unreconciled with the bounds that already
  exist, and ignores the BIGGER injection surface. Severity: MEDIUM.**
  Description: three relevant bounds pre-exist: (a) `/ceo-boot` bounds every
  disk-sourced string to 200 chars per item post-NFKC with the
  `scan_harness_mimicry` pipeline (`ceo-boot.md:69`); (b) the lesson schema
  already caps `remember_this` at ≤200 chars (`lessons.py:105`); (c) the
  spawn-injection path caps at `_MAX_INJECT_TOKENS = 2000`
  (`lessons.py:86`) ≈ 8k chars — **8× the boot cap under debate**, injected
  per-spawn, and the plan never says whether confidence decay / review /
  dampening govern that path too. A widened, distiller-fed lessons store
  flowing into the untouched 2K-token spawn path is a larger recurring token
  rent and a larger injection surface than anything in item 4. Also:
  `/ceo-boot --json` DENIES "recommendation text body" as an LLM06
  side-channel (`ceo-boot.md:104`) — lesson text must join that list or the
  telemetry mode leaks what the display mode fences.
  Mitigation: formalize the cap as ≤3 lessons × ≤200 chars each + fencing,
  enforced at render time through the EXISTING ceo-boot bound + scan
  pipeline (no new truncation code); add lesson text to the `--json` DENIED
  fields; state explicitly that the confidence/decay/review lifecycle governs
  BOTH consumers (boot one-liners AND `top3` spawn injection) or shrink the
  spawn cap to match.

- **R-FX-06 — Dampening ordinal has no DX contract; condensation that drops
  the advisory ID or the recall pointer is operator-training damage.
  Severity: MEDIUM.**
  Description: binding constraint 4 protects blocking guards; it says nothing
  about what a condensed *advisory* must retain. A condensed line like
  "(3 advisories suppressed)" hides WHICH advisories — the operator can no
  longer correlate with the audit log, and an advisory the operator never saw
  in ANY session (because dampening state persisted across sessions) is
  indistinguishable from a rail that never fired. Bookkeeping is a cost
  surface too: a per-repeat audit-chain write puts hot-path traffic exactly
  where MF-SEC-5 forbids it.
  Mitigation: contract in the plan: condensed form ALWAYS retains
  {advisory ID, ordinal count, one-line pointer to the full text's location};
  dampening counters are **session-scoped** (fresh session ⇒ full advisory
  once before any condensation); counter state uses the per-session 0600
  file pattern (`tool_lifecycle.py:19-23`), with at most ONE
  condensation-summary audit event per advisory ID per session.

- **R-FX-07 — Score legibility: three stacked scoring mechanisms with no
  operator breakdown. Severity: MEDIUM.**
  Description: item 3 adds confidence-with-decay on top of two mechanisms
  already in `lessons.py`: relevance ranking
  `archetype_match × scope_overlap × recency_decay` (`lessons.py:20-24`) and
  the ADR-015 hit/miss outcome loop (`lessons.py:109-119`). Three multiplied
  signals make "why did this lesson appear / disappear?" unanswerable from
  `/lesson-review`, which today just shells `lessons.py list`
  (`lesson-review.md:28-31`). Note also the header's own precision bug as a
  warning sign: it calls `exp(-days/90)` a "90-day half-life"
  (`lessons.py:24`) — that formula's half-life is ≈62 days. Adding a second
  decay on top of an already-misdocumented one guarantees operator confusion.
  Mitigation: `/lesson-review` (and `lessons.py list`) must print the score
  COMPONENTS per lesson (relevance, hit-rate, confidence, decay age), not a
  single opaque float; fix the half-life docstring while in there under the
  same SENT-F.

- **R-FX-08 — Stale ADR pointer will fork the paper trail. Severity: LOW
  (but blocks consensus-doc coherence).**
  Description: the stub gates execution on "ADR-174 is drafted and accepted"
  (`PLAN-154-gated-learning-loop.md:31`, also line 85's "draft ADR-174"),
  but the reserved learning-loop ADR number is **ADR-160** (index correction
  S261). Neither ADR-160 nor ADR-174 exists on disk yet, so the fix is free
  today and expensive after consensus/approved files start citing it.
  Mitigation: s/ADR-174/ADR-160/ in the plan before this round's consensus
  is written.

- **R-FX-09 — Per-call latency creep from item 6, and LLM spend creep from
  item 7. Severity: LOW-MEDIUM.**
  Description: item 6's fail-CLOSED citation verification implies a
  transcript/store read on a PreToolUse path whose whole budget is 120ms p95;
  item 7's "trigger-clustering" is an LLM call if implemented lazily.
  Mitigation: citation verification runs ONLY after the destructive-op
  matcher already fired (rare path), never on the common path, and is
  profiled; the deny-once message must state the exact citation format that
  unlocks retry (deny-once DX: a block the operator cannot decode is a block
  they`ll disable). `/lesson-evolve` clustering is deterministic v1 (Jaccard
  over `scope_tags` — the machinery pattern already exists in
  `debate-converge.py`), $0 in model spend.

## Must-fix (blocking)

1. **Zero-new-registration invariant for the observe rail (R-FX-01).** The
   plan text must state: no new PostToolUse/PreToolUse hook registrations;
   metadata extensions ride `tool_lifecycle.record_pre/record_post` in-place
   per MF-PERF-1/MF-SEC-5; the extended path joins the hook-latency profiler
   corpus so the existing p95<120ms/p99<160ms CI gate enforces it.
2. **Bounded distiller economics (R-FX-02 + R-FX-03).** Named cadence
   (Owner-invoked or nightly-hygiene piggyback — not per-session), persisted
   delta cursor over the audit log, hard per-run input-token ceiling,
   distiller model pinned EXPLICITLY (haiku-tier) rather than via the stub
   `model_routing.py`/staged `tier-policy.yml`, and distiller token usage
   emitted so `/agent-budget` shows it as a line item.
3. **Named, registered kill-switch story (R-FX-04).** Opt-in enable flag
   (unset = off, `cost_envelope.py` posture) + `CEO_SOTA_DISABLE=1` master
   precedence documented; every new env registered in `env-inventory.json` +
   `CHEAT-SHEET.md` env table in the consuming commit (S218 class).
4. **Reconcile the boot cap with the existing bounds AND the spawn-injection
   path (R-FX-05).** Cap = ≤3 × ≤200 chars via the existing ceo-boot
   bound+scan pipeline; lesson text added to `--json` DENIED fields; the
   plan states whether decay/review/dampening govern the `top3` 2K-token
   spawn path — and if not, why an 8× larger un-dampened consumer is
   acceptable.
5. **Dampening ordinal DX contract (R-FX-06).** Condensed advisory always
   retains {ID, ordinal, pointer-to-full-text}; counters session-scoped;
   bookkeeping off the audit-chain hot path (per-session 0600 file); one
   condensation event per advisory ID per session.
6. **Fix the ADR pointer to ADR-160 (R-FX-08)** before any consensus file
   cites ADR-174.

## Nice-to-have (advisory)

1. **Score-component display in `/lesson-review` (R-FX-07)** — plus the
   half-life docstring fix under the same SENT-F.
2. **Boot-cache staleness note:** `/ceo-boot --cached` keys on
   HEAD + audit-log mtime with TTL 1h (`ceo-boot.md:26`); lessons live in
   their own dir (`lessons.py:13`), so a fresh lesson can be invisible to a
   cache-hit boot for up to 1h. Either fold the lessons-dir mtime into the
   cache key or document the staleness as accepted.
3. **Item-6/7 cost hygiene (R-FX-09):** profile the citation-verification
   read; deterministic clustering v1 for `/lesson-evolve`.
4. **Per-event byte budget for the extended rail:** name a ceiling for the
   widened `tool_call_lifecycle_recorded` event so audit-log rotation (10 MB)
   and distiller input volume stay modelable.

## Unseen by the original plan

1. **The dominant cost is the rent, not the distiller.** The plan prices the
   distiller ("cheap model") but the recurring cost center is injection:
   ~1k chars per session boot + up to 2K tokens per spawn
   (`lessons.py:86`), paid on every session and every spawn forever. The
   TTL-30d + decay red line is therefore also the *economic* garbage
   collector — say so in the plan, and treat any future proposal to raise
   lesson counts/caps as a FinOps change, not a UX tweak.
2. **Metadata widening compounds downstream.** Every field added to the rail
   grows each per-call audit event → faster 10 MB rotation → bigger distiller
   input per run → more boot/spawn candidates. The closed-enum discipline of
   `tool_lifecycle.py` (MF-SEC-1/MF-SEC-3 — raw strings and raw durations
   never reach the wire) must be stated as binding for every NEW field, not
   just inherited by vibes.
3. **A deliberately-off opt-in rail must not become a standing yellow.**
   Binding constraint 6 handles `check_harness_config.py` allowlisting, but
   PLAN-153 Wave E also ships *liveness* ("RED in /ceo-boot when a fail-open
   rail never fires"). A default-off learning rail that never fires is
   correct behavior, yet it is shaped exactly like the S254 dead rail. If
   the liveness check yellows it, operators learn to ignore yellow — the
   documented two-yellows fatigue pattern. The Wave-E marker must suppress
   liveness alarms for rails that are off *by recorded operator choice*,
   and the fixtures must prove that direction too.
4. **Pricing-table dependency:** `/agent-budget` falls back to "TBD" cost
   when `docs/provider-pricing.md` lacks a row (`agent-budget.md:18-21`).
   If the distiller pins a model with no pricing row, must-fix #2's spend
   visibility silently degrades to token-counts-only. Add the pricing row in
   the same commit that pins the model.

## What I would NOT change

- **Extending the PLAN-125 WS-1 rail instead of building a new observe
  surface.** That rail already paid for the hard economics: no PreToolUse
  audit traffic (MF-SEC-5), no extra subprocess (MF-PERF-1), ~1 in-flight
  entry steady state (MF-PERF-2), injectable clock for $0 tests (MF-PERF-3).
  Reuse is the whole savings; defend it against "just add a small new hook".
- **Metadata-only v1.** It is simultaneously the security floor (constraint
  1) and the cheapest possible v1: no payload store, no PII/PHI redaction
  pass to build or run, minimal distiller input tokens.
- **Zero self-activation + TTL 30d + 7d warning.** $0 when the Owner doesn't
  engage; bounded store growth when they do. The human gate is also a spend
  gate.
- **Bounded lesson schema (constraint 3).** A constrained
  trigger → advisory-text vocabulary is the only reason a hard boot cap is
  enforceable at all; free-form prose would make every cap a truncation bug.
- **Advisory-only dampening with block reasons untouched (constraint 4).**
  From the DX seat: a blocking guard's reason text is the operator's
  incident-response interface. No token saving justifies degrading it —
  ever.
