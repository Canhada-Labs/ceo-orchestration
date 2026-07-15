---
round: 1
archetype: security-engineer
skill: security-and-auth
generated_at: 2026-07-15T16:40:10Z
---

# PLAN-159 round-1 critique — Security Engineer (Capt. Abernathy)

> Lens: this perf gate is not "just perf." It profiles three **governance /
> security hooks** (`check_agent_spawn`, `check_anti_ceo_overhead`,
> `check_output_secrets`) and carries **two live security controls** inside
> the same job — the S254 anti-vacuity **positive** control and the
> **MF-SEC-5 negative** control on the observe rail. My question is not
> "does N=200 make it stable" (it does) but "does raising N or adding a
> retry silently demote any detection or anti-vacuity contract, and does it
> widen the workflow's supply-chain surface." Every number below was
> verified against the code, not the proposal.

## Verdict

ADJUST

## Summary

- **The direction is security-*positive*, not negative.** N=200 makes the
  p99 index (197) finally separate from p95 (189) — verified: at N=20
  `int(19*0.99)=int(19*0.95)=18`, so today the `p99<160` ceiling is *dead
  code* (`profile-opus-4-7.py:325`). And the MF-SEC-5 negative control
  (`off_rows==0 and pre_rows==0`, line 627) gets 10× more must-write-nothing
  samples. The change *strengthens* two contracts.
- **The one lever that can silently demote the gate is the retry (lever 2).**
  A loosely-written shell wrapper (`|| true`, swallowed `$?` under
  `set -euo pipefail`) turns a hard gate into `continue-on-error` — the exact
  demotion the plan says it rejects, re-introduced by accident. This is a
  blocking must-fix, and the Wave-2 positive control must run *through* the
  wrapper, not the bare command.
- **Supply-chain surface is UNCHANGED and correctly so** — plain-shell retry
  (no third-party retry action), job already SHA-pins checkout+setup-python
  and runs `permissions: contents: read`. No new action/permission/secret/egress.

## Risks

**R1 — Retry wrapper silently demotes the hard gate to advisory**
- Severity: **HIGH**
- Description: Lever 2 is a hand-written shell retry under `set -euo
  pipefail`. The failure modes are subtle: `python3 … || python3 …` disables
  `set -e` for attempt 1, and if attempt 2 also fails the loop must still
  propagate non-zero; a trailing `|| true`, an unquoted `exit $?` after a
  pipe, or a `break` on the wrong condition yields a job that is GREEN even
  when both attempts breached the ceiling. That is a silent demotion of a
  security-hook regression gate — my skill's Fail-Fast rule ("never degrade
  security silently") names exactly this. It is indistinguishable from a
  passing run in the UI.
- Mitigation: (a) implement the loop so that **two failures ⇒ job exit
  non-zero** (explicit `exit 1` after the final attempt; do not rely on
  implicit `$?`); (b) hardcode **exactly 2 attempts** — no unbounded
  `until`; (c) Wave-2's deliberate-regression fixture MUST run through the
  full retry wrapper and confirm the *job* goes RED after both attempts, not
  merely that the profiler returns non-zero once (see MF1).

**R2 — N-bump changes the anti-vacuity control's threshold without empirical confirmation**
- Severity: **MEDIUM**
- Description: The positive control requires `on_rows >= iterations and
  on_paired == on_rows` (lines 609-611); raising N to 200 raises the bar to
  ≥200 paired rows. Code review says this scales safely — the assertion is
  parameterized on `iterations` (not hardcoded 20) and I found **no
  row-count/eviction cap** on the observe `*.observe.jsonl` in
  `tool_lifecycle.py` (only `_MAX_OBSERVATION_LINE_BYTES=512` per line, which
  the benign fixed payload never approaches; the "evict" at lines 688/753 is
  the pairing-record eviction, not a store truncation). BUT `measurements.md
  §3` reports only latency percentiles at N=200 — it does **not** report
  `observe_positive_control.passed` / `rows` at N=200 with the rail present.
  So the control's behaviour at the new N is code-plausible but empirically
  unconfirmed. If a hidden cap ever truncated below N, the N-bump would
  convert a latency flake into an anti-vacuity-control flake (RED for a
  non-regression reason).
- Mitigation: Wave-1 acceptance must show a real N=200 run with
  `observe_rail_present=true`, `observe_positive_control` `{required:true,
  rows>=200, paired_rows==rows, passed:true}`, and both negative-control arms
  (`unset_store_rows`, `pre_side_store_rows`) at 0. **Forbid** any future
  "fix" that relaxes `>= iterations` to `>= min(iterations, cap)` — that
  silently weakens the S254 guard.

**R3 — Retry masks a bursty / probabilistic slowdown**
- Severity: **LOW**
- Description: The retry is safe against a *deterministic* ≥2× regression
  (fails both attempts, as the proposal argues) because the corpus payloads
  are fixed and benign. It could in principle pass a slowdown that only
  manifests ~50% of scheduling windows. But N=200 dilutes an intra-window
  burst, and a 50%-probability 2× path would still dominate a 200-sample p95;
  a truly rare pathological path is below the gate's design sensitivity
  regardless. Residual, not blocking.
- Mitigation: none required beyond keeping lever 1 (N=200) as the primary
  fix and the retry as secondary (the plan already orders them this way).

**R4 — More subprocesses at N=200 raise the odds of an uncaught `TimeoutExpired`**
- Severity: **LOW**
- Description: `_run_once` calls `subprocess.run(..., timeout=10)` (lines
  527-546) with no `except TimeoutExpired`. N=200 issues ~10× more subprocess
  calls per entry, so on a badly contended runner the cumulative chance one
  call stalls >10s and raises `TimeoutExpired` rises. That is an **uncaught
  crash → job non-zero** — it fails *closed* (safe direction), but as an
  opaque traceback rather than a clean "p95 exceeded", and lever-2 would
  retry it. Acceptable but not clean.
- Mitigation (advisory): fold `TimeoutExpired` into the existing
  `entry_hook_failed=True` fail-closed sink so a stall reads as a graceful
  gate failure, not a stack trace. Not blocking (already fails closed).

## Must-fix (blocking)

- **MF1 — Retry fails closed on double-failure, proven by the Wave-2 fixture
  through the wrapper.** The step's retry loop must exit non-zero when both
  attempts breach, with exactly 2 attempts hardcoded and attempt-1 failure
  `::warning`-logged (never `::error`-suppressed). Wave-2's deliberate
  sleep-injection must be run through the **full retry wrapper** and assert
  the *job* is RED after both attempts. (Addresses R1; skill Fail-Fast rule
  + the plan's own rejection of `continue-on-error`.)
- **MF2 — Confirm the observe positive + negative controls arm and pass at
  N=200 in Wave-1 acceptance**, with the row-count assertion left as
  `>= iterations` (never re-scaled to a cap). Evidence: a captured N=200 run
  showing `observe_positive_control.passed=true, rows>=200, paired_rows==rows`
  and negative arms at 0. (Addresses R2; S254 anti-vacuity + MF-SEC-5.)

## Nice-to-have (advisory)

- Catch `subprocess.TimeoutExpired` in `_run_once` and fold into
  `entry_hook_failed` for clean fail-closed diagnostics at high N (R4).
- Record the **"exactly 2 attempts" bound as a stated invariant** in both the
  step comment and the ADR, so a later drift to unbounded retry is visibly a
  spec violation the validate.yml sentinel/pair-rail can catch.
- The ADR should state, in one line, that this gate is **not** a
  malicious-behaviour detector (fixed benign corpus) — its security value is
  the observe-rail write-path controls, not input-dependent leak detection —
  so future readers don't over-trust it or under-trust the N-change.

## Unseen by the original plan

- **The "≥2× regression still fails" success criterion is hook-specific under
  a fixed absolute ceiling.** With N=200 clean baselines of ~55 ms
  (`check_agent_spawn`), a genuine *multiplicative* 2× regression → ~110 ms,
  which stays **under** the 120 ms p95 ceiling and is NOT caught; only the
  slower entries (`check_output_secrets` ~65-76 ms → 130-152 ms) breach. This
  is **pre-existing** (a property of the fixed ceiling, not introduced by
  PLAN-159 — and N=200 makes the ceiling that *does* exist fire more
  reliably), but the Wave-2 fixture injects an *additive* sleep of arbitrary
  size, so it will pass trivially and does **not** actually validate the
  stronger "detects 2×" wording on the fastest hook. Either reword the
  criterion to the true contract ("an injected over-ceiling regression still
  RED-flags") or acknowledge that catching 2× on the fastest hook would need
  a per-hook relative baseline (out of scope for a flake fix).
- **`CEO_SOTA_DISABLE` remains the broad escape hatch** (`validate.yml:1179`,
  a `vars.` repo variable). Nothing in this plan touches it, but it is worth
  the ADR noting explicitly that the *sanctioned* response to this flake is
  PLAN-159's narrow fix, and flipping `CEO_SOTA_DISABLE` (which also kills
  `--smoke` and `--floor`) is a silent wholesale demotion that must never be
  used as a flake workaround.

## What I would NOT change

- **Keep the ceilings at p95<120 / p99<160.** Lever 3 is correctly NOT
  exercised — measured N=200 p95 ≤ 76 ms leaves no evidence to loosen the
  absolute threshold, and loosening is the only lever that reduces detection
  sensitivity. Do not touch it without post-land evidence.
- **Keep the retry as plain shell — no third-party retry action.** This is
  the right supply-chain call; a marketplace retry action would add an
  unpinned/opaque dependency to a job that today is clean (SHA-pinned
  checkout `de0fac2e…` + setup-python `a309ff8b…`, `permissions: contents:
  read`). Keep the retry a pure re-invocation of the identical command — no
  new env, no network, no shared-state write.
- **Keep the OQ2 bootstrapping landing gated by the sentinel + pair-rail, not
  by the perf gate's colour.** The workflow edit's authorization already
  rests on the canonical-edit ceremony; a bounded documented rerun to land it
  past the OLD flaky gate is acceptable precisely because green-ness of the
  perf gate is not (and cannot be) the authorization for the edit.
- **Do not "fix" the `_pct_of_sorted` `int()` truncation in this plan.**
  Changing the index formula is a wider-blast-radius behavioural change;
  N=200 compensates for it (p99 separates), and the CEO default to document
  the index table rather than re-derive percentiles is the lower-risk path.
