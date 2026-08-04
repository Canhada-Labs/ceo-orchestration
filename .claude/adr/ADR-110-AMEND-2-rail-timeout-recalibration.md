# ADR-110-AMEND-2 — Pair-rail timeout recalibration (120/150 → 180/210)

---
adr_id: ADR-110-AMEND-2
title: Pair-rail timeout contract — internal 120→180 s, harness registration 150→210 s; §3 recalibration query promoted to a versioned instrument
status: ACCEPTED
amends: ADR-110-AMEND-1
proposed_at: 2026-08-03
proposed_by: CEO (ADR-110-AMEND-1 §3 recalibration trigger met — n=20 healthy cases post-uplift)
session_origin: 2026-08-03 (S291)
accepted_at: 2026-08-03
authorization: PLAN-162/165 consolidated Owner-GPG ceremony commit tagged [SENT-S292-C] — this file reaches the canonical tree ONLY via that ceremony; a landed copy implies the gate fired
risk_tier: A
debate_required: true
debate_record: .claude/plans/PLAN-164/debate/amend-2-round-1/ (3 lanes: performance / security / code-review — 3x ADJUST, no VETO; consensus.md)
related_plans: [PLAN-075, PLAN-081, PLAN-163, PLAN-164, PLAN-162]
related_adrs: [ADR-106, ADR-110, ADR-110-AMEND-1, ADR-182]
---

## §1 What this amendment changes

ADR-110-AMEND-1 set the operative timeout pair at internal 120 s /
registration 150 s and scheduled its own revisit in §3 ("≥10 healthy
cases, then recompute p95 and revisit; any change is a new amendment via
ceremony"). The trigger is met (n=20). This amendment:

1. **Internal `CEO_PAIR_RAIL_TIMEOUT_S`: 120 → 180.** Four sites in
   `.claude/hooks/check_pair_rail.py` — the env-read default string
   (`:1717`), the parse-error fallback float (`:1720`), the clamp-reset
   float (`:1722`), **and the module docstring** (`:51`). Clamp bound
   `>600` unchanged (see §5(c)).
2. **Harness registration: 150 → 210** for the `check_pair_rail.py`
   PreToolUse entry in kernel `.claude/settings.json` (`:285-286`) AND
   template `templates/settings/settings.base.json` (`:98-99`), parity
   enforced. The tested layering invariant `registration >= internal + 30`
   holds at equality (210 = 180 + 30).
3. **`statusMessage` updated** in both mirrors (~1-2 min → up to ~3 min),
   plus the two `_comment` blocks that narrate the pair (kernel `:279`,
   template `:92`), and `CHANGELOG.md:43` which carries the old
   "may take 1-2 min" string (doc-freshness class — this exact class
   redded rc.2 in S287).
4. **`test_pair_rail_timeout_invariant.py` is part of the change, not a
   passenger.** It pins `_RATIFIED_INTERNAL_S = 120` (`:103`) and
   `_RATIFIED_REGISTRATION_S = 150` (`:104`), and
   `test_ratified_absolute_values` asserts the absolute literals in three
   places. Its own docstring says a deliberate recalibration must edit it
   in the same change. It does — the proposal that claimed otherwise was
   wrong, and the review caught it.
5. **The §3 recalibration query becomes a versioned instrument**
   (`.claude/scripts/local/pair-rail-latency.py`) instead of normative
   prose. See §3.
6. **`timeout_ms` (post-clamp, integer milliseconds) is added to the
   `pair_rail_case` / `pair_rail_review_expected` events** — see §4
   residual (i), which this is the minimum honest cost of keeping true
   under a 180 s budget. *(Correction during implementation, S292: the
   first draft specified a float `timeout_s`; `_lib/canonical_json.py:96`
   forbids floats in HMAC-covered fields and the spool writer DROPS the
   whole event on violation — a float field here would have blinded the
   very rail it instruments. Integer milliseconds mirror the
   `dispatcher_route.wall_clock_ms` precedent; divide by 1000 for
   seconds.)*

## §2 Evidence — measured 2026-08-03, cutoff frozen

Instrument: `.claude/scripts/local/pair-rail-latency.py --since 2026-07-29 --budget-s 120`
(o `--budget-s` é OBRIGATÓRIO e sem default: estes números foram colhidos
sob o orçamento de 120 s, e re-avaliá-los contra 180 daria 0 no lugar do
7/27 citado — a evidência tem de vir com o budget que a produziu)
(the union of rotated archives + the live log; 8 files). **Frozen cutoff:
`ts = 2026-08-03T19:16:53Z`.** Post-uplift partition (the AMEND-1
ceremony landed 2026-07-29; the fastest healthy sample is 33 s, so no
sample could have survived the retired 30 s cap — the partition is clean).

| Metric | Value |
|---|---|
| healthy (cases A–E) | **n = 20** — A:14, B:6 |
| latencies (s) | 33, 41, 44, 48, 49, 54, 55, 61, 70, 71, 79, 82, 92, 95, 105, 105, 114, 115, 115, 120 |
| median | 75 s |
| p95 interpolated (`quantiles(n=20)[18]`) | **119.8 s — BELOW the 120 s budget** |
| p95 empirical (nearest-rank) | 115 s |
| censored (case F, joinable) | n = 7 — 30, 120, 120, 120, 120, 120, 121 |
| **censoring rate** | **7/27 = 25.9 %** |
| reviews at or above the 120 s budget | 7/27 = **25.9 %** |
| F events dropped from the join (no `review_id`, pre-PLAN-161 schema) | 11 |
| true orphans (`review_expected` with no case at all) | **0** |

> **Re-validação independente (S292, 2026-08-04).** O mesmo instrumento,
> agora com budget EXPLÍCITO (`--since 2026-07-29 --budget-s 120` — a
> flag deixou de ter default justamente para que nenhum número apareça
> sem o budget que o produziu), sobre o dataset crescido para n=41
> (31 healthy + 10 censored, cutoff `2026-08-03T21:15:06Z`):
> **taxa de censura 24.4 %** (era 25.9 % em n=27), `p95 >= budget BY
> COUNT: True`, **0 órfãos verdadeiros**. A conclusão de §2.1 é robusta
> à ampliação da amostra — o gatilho de >5 % continua largamente
> ultrapassado e o argumento de contagem continua valendo.

### §2.1 The decision argument — counting, not interpolation

The first draft of this amendment argued "p95 = 121.2 s exceeds the
budget, so escalation is mandatory". **That number was wrong and the
argument was elastic.** Two independent re-measurements refuted it: the
hand-run union glob had read 7 of the 8 log files (a rotation created
`audit-log-2026-08-1.jsonl` mid-session), returning a SUBSET whose p95
supported the desired conclusion where the full set does not. The honest
p95 is 119.8 s — *below* the budget.

The correct argument needs no interpolation and no extrapolation above
the observed maximum:

- 25.9 % of post-uplift reviews take **≥ 120 s** (7 of 27);
- a distribution with 25.9 % of its mass at or above 120 s has its 95th
  percentile **≥ 120 s by count** — this is arithmetic, not an estimator;
- the AMEND-1 folga convention (~1.5 × p95) over a p95 that is ≥ 120
  yields **≥ 180**.

180 is therefore the **floor** the existing convention implies, not a
generous pick — and it is estimator-robust: 1.5 × 119.8 = 179.6 and
1.5 × 115 = 172.5 both round to 180 under the same convention. This also
refutes alternative (a) 150/180 rigorously (150 < 180 ≤ 1.5 × p95),
without appealing to right-censoring as a rhetorical device.

**The number this amendment refuses to leave unstated:** 25.9 % of
post-uplift canonical L3+ edits proceeded WITHOUT a completed
cross-model review. That is the present fail-open rate of the rail. The
trade is not "fail-open window vs synchronous hold" in the abstract — it
is "25.9 % now, vs up to ~3 minutes of hold in the worst case".

### §2.2 What the measurement does NOT establish

- **The measured quantity is a superset of the capped quantity.**
  `pair_rail_review_expected` is emitted before `_invoke_codex_review`;
  inside it, before `subprocess.run(timeout=…)`, run the ADR-182 pin
  verification (sha256 of the native payload), prompt build, ADR-114
  egress redaction and `mkdtemp`; readback + re-validation + parse +
  redaction follow. So `logged_latency = uncapped_overhead +
  subprocess(≤ cap)`. A *healthy* case clocked at 120.0 s therefore had a
  subprocess strictly under 120 s. The censored F's appear at the same
  wall-clock values (120/121) — the metric cannot separate "review
  completed at the boundary" from "review killed at the boundary".
- **Whether 180 is sufficient is unknown.** With 25.9 % censored today,
  the true tail may well exceed 180. §3 replaces the unmeasurable p95
  trigger with the censoring rate for exactly this reason.
- One censored sample sits at 30 s — evidence that a knob-set-low session
  is indistinguishable from a Codex outage in the current schema. This is
  the §4(i) residual, and §1.6 is its minimum remedy.

## §3 Recalibration trigger — superseded metric + versioned instrument

**The p95-of-healthy-samples trigger from AMEND-1 §3 is retired.** It is
structurally unestimable under right-censoring: a review slower than the
budget becomes case F and never enters the healthy set, so more healthy
samples cannot reveal the tail. The successor metric is observable under
any budget:

> **Reopen when the CENSORING RATE — the fraction of joined reviews whose
> case is F — exceeds 5 % over n ≥ 20 post-change reviews.** Any change
> is a new amendment via ceremony, never a literal edit.

The query is no longer normative prose. It is
`.claude/scripts/local/pair-rail-latency.py`, which prints its INPUTS
(every file read with mtime, the case histogram, the count of F events
dropped for lacking `review_id`, the true-orphan count, the censoring
rate, and the `ts` cutoff) alongside its result. Rationale, on the record:
the prose query failed twice, both times silently — once returning `n=0`
after rotation, and once returning a subset with the wrong number while
looking healthy. A gate that answers with the wrong number is the
vacuous-gate class in its worst form. A governance verdict must be
reproducible by a third party.

**Dataset hygiene, now normative:** the dataset moves while it is
measured — an active session both generates samples and can rotate the
log mid-run. Any amendment citing these numbers freezes the `ts` cutoff
in its text (this one: `2026-08-03T19:16:53Z`).

## §4 Named residuals (accepted, on the record)

- **(i) Env-knob sub-floor — now partially instrumented.** A session
  exporting `CEO_PAIR_RAIL_TIMEOUT_S` below real verdict latency
  re-creates fail-open by env alone. AMEND-1 accepted this because "every
  such miss is auditable as a case-F event". Measurement shows that claim
  was true only about the EXISTENCE of the failure, never its CAUSE: no
  event recorded the effective budget, so `CEO_PAIR_RAIL_TIMEOUT_S=5`
  produced a case F indistinguishable from a genuine Codex outage —
  making the undocumented knob **stealthier than the documented
  kill-switch** (`CEO_PAIR_RAIL_DISABLE=1` emits its own loud event
  before any `review_expected`). §1.6 closes the ambiguity by emitting the
  post-clamp `timeout_ms` (integer milliseconds — see §1.6 correction).
  A minimum floor on the knob remains DEFERRED
  (changing a documented knob's semantics is a new contract —
  AMEND-1 consensus item 2), but the incentive gradient is no longer
  inverted, and the next amendment's historical series is no longer born
  ambiguous.
- **(ii) Clamp overflow — unchanged wart, larger magnitude.** A value
  `>600` or a parse error RESETS to the default rather than clamping to
  the bound. Under this amendment an operator setting `9999` silently
  gets 180 instead of 120 — the same wart, now more permissive.
- **(iii) Uncapped overhead is absolute, not proportional.** The
  pre/post-subprocess work (§2.2) grows with payload and prompt size and
  is bounded by nothing but the 30 s inter-layer margin, which stays
  absolute deliberately (§5(d)).
- **(iv) The harness ceiling is asserted, not assumed.** See §6.

## §5 Alternatives rejected

- **(a) 150/180.** Refuted arithmetically in §2.1: 150 < 180 ≤ 1.5 × p95.
  It would repeat the near-miss→F cycle that motivated AMEND-1, at the
  cost of another full ceremony.
- **(b) No new ceiling; calibrate via the env knob.** Rejected: §4(i)
  records the knob as a universal fail-open residual, and it is stealthier
  than the official kill-switch. Institutionalising it as the calibration
  mechanism would promote the quietest bypass to a governance instrument.
- **(c) Wait for more samples.** Rejected: right-censoring guarantees
  future healthy samples cannot reveal the tail (F's never enter the
  set). Waiting only accumulates F's. Only raising the cap and
  re-measuring the censoring rate reveals it.
- **(d) Scale the inter-layer margin (30 → 45/60) "by proportion".**
  Rejected: the margin covers Python startup + pin-verify + validation,
  which are absolute costs. Scaling them by percentage is numerology.
- **(e) Turn timeout into a block.** Rejected (unchanged from ADR-106):
  it would convert a Codex outage into a DoS of the operator — the C3
  self-DoS class. Timeout stays fail-OPEN, as a registered decision.

## §6 Pre-ceremony gate — harness ceiling probe (BLOCKING)

`_python-hook.sh` imposes no timeout of its own; the only ceiling is the
harness registration. If Claude Code enforces a hard ceiling below 210 s,
the harness kills the hook BEFORE the internal 180 s cap — and a killed
hook emits no `pair_rail_case` at all. That failure mode is strictly
worse than today's case F: fail-open with **no event**, invisible to the
instrument in both numerator and denominator.

Acceptance criterion, to be satisfied before this amendment lands:

- a hook registered at 210 s that blocks for ~185 s still RETURNS and
  still emits `pair_rail_case`; and
- the true-orphan count (`review_expected` with no case) stays **0**
  — measured baseline today at the 150 s registration: **0**.

If the probe fails, the amendment does not land as written.

## §7 Declared cost

- A non-sentineled canonical edit that triggers a live review now holds
  the session synchronously for up to ~180 s (was ~120 s). Mitigation is
  the `statusMessage`, which under a 3-minute hold stops being cosmetic.
  The hold also keeps pushing heavy canonical work toward staged copies +
  ceremony, which is the desired flow.
- Reviews that would have died between 121 s and 180 s now COMPLETE —
  recurring Codex spend that the shorter-budget era never paid because
  those invocations died before billing a verdict. That spend is the
  rail's purpose. Tracked in the finops lane.
- Raising the honest path's UX cost raises the pressure to use the quiet
  knob (§4(i)). §1.6 is what keeps that pressure observable.
