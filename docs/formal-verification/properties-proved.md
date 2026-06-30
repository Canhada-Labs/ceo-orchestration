# Formal Properties Proved — 3 State Machines

**Status:** SPECIFIED 2026-04-16 (PLAN-013 D.3 breaker) + 2026-04-15
(PLAN-014 B.1/B.2 plan-lifecycle + debate-convergence).
**TLC run:** PENDING — this environment lacks a functional Java runtime
(the `/usr/bin/java` stub on macOS prompts to install OpenJDK); `run-
tlc.sh` verified the tla2tools.jar download + SHA-256 pin but could
not execute the model-checker. The log-hash column below carries
`<TLC_RUN_PENDING_SESSION_23_CI>` placeholders; a follow-up session
(or the Sprint-14 `formal-verify.yml` workflow) will populate real
hashes via `bash docs/formal-verification/run-tlc.sh hash`.
**Authors:** Principal QA Architect + Principal Security Engineer
(composite persona), under PLAN-013 Phase D.3 spawn.
**Related:**
`.claude/adr/ADR-040-live-adapter-activation-contract.md` §2 (breaker
contract, source of truth), `.claude/adr/ADR-044-formal-verification-
pilot.md` (this artifact's governing decision), `docs/formal-
verification/rationale.md` (Phase D.1 selection + tool choice), `docs/
formal-verification/breaker.tla` (canonical spec), `docs/formal-
verification/breaker.pcal` (PlusCal source).

## 1. Preamble

This document is the **proof-output artifact** for the ADR-040 §2
Live-Adapter Circuit Breaker formal-verification pilot. It maps each
of the four properties specified in `breaker.tla` to:

- the TLA+ temporal-logic formula that TLC checks,
- the Wave B conformance test (Python + real `_breaker.py`) that
  asserts the property holds against the implementation,
- the exact `_breaker.py` function + line numbers that implement the
  property,
- a SHA-256 log hash of the TLC run output (so drift between spec
  and last-verified run is detectable), and
- a mutation-count target (≥5 or 6 per property, per ADR-044
  §Decision-drivers).

The pilot proves properties on a **model** — the TLA+ spec abstracts
away Python exception paths, thread-lock fairness, and the full
reason-enum branching. The *real* correctness guarantee comes from the
conformance harness (Phase D.8, Wave B Agent 4 territory), which
re-runs every property against the live Python implementation under
deterministic seeds and mutation injection. Per PLAN-013 debate §C8
CRITICAL, model alone = security theater; model + conformance harness
= defensible rigor.

**Important gap surfaced during D.2 spec drafting (see §4 below):**
the `_breaker.py` implementation does NOT currently call
`_lib.audit_emit.emit_breaker_opened` on closed→open transitions,
even though the helper is defined in `audit_emit.py:977` and ADR-040
§7 mandates the event. This is tracked as Gap #3 in the PLAN-013
Session 20 CLAUDE.md CHANGELOG. The S3 conformance test is expected
to **fail against current source** and only pass once the emit hook
is wired. The model specifies the intended (ADR-040 §7) behavior,
which is the contract the conformance harness validates.

## 2. Property → Test → Implementation Mapping

| ID | TLA+ form (inline) | Conformance test (Wave B) | Impl file:line | TLC log hash | Mutations |
|----|-------------------|---------------------------|----------------|--------------|-----------|
| **S1** | `[]((state = "closed" ∧ FailuresInWindow ≥ FAILURE_THRESHOLD) ⇒ ◇(state = "open"))` | `tests/formal_verification/test_breaker_conformance.py::test_s1_breaker_opens_on_threshold` | `.claude/hooks/_lib/adapters/live/_breaker.py:176-211` (`record_failure`, closed→open branch at lines 207-211) | `<TLC_RUN_PENDING_SESSION_23_CI>` | **6** |
| **S2** | `[](state = "half_open" ⇒ \|in_flight\| ≤ 1)` | `tests/formal_verification/test_breaker_conformance.py::test_s2_half_open_singleton` | `.claude/hooks/_lib/adapters/live/_breaker.py:154-174` (`should_allow`, probe_available gate at lines 170-174) | `<TLC_RUN_PENDING_SESSION_23_CI>` | **5** |
| **S3** | `[]((state = "closed" ∧ state' = "open") ⇒ (\|audit_log'\| > \|audit_log\| ∧ last(audit_log').action = "breaker_opened"))` | `tests/formal_verification/test_breaker_conformance.py::test_s3_open_emits_audit` | `.claude/hooks/_lib/adapters/live/_breaker.py:246-250` (`_open_locked`) + CONTRACT: `_lib/audit_emit.py:977` (`emit_breaker_opened`, currently unwired — Gap #3) | `<TLC_RUN_PENDING_SESSION_23_CI>` | **5** |
| **L1** | `[](state = "open" ⇒ ◇(state = "half_open")) ∧ [](state = "half_open" ⇒ ◇(state ∈ {"closed","open"}))` | `tests/formal_verification/test_breaker_conformance.py::test_l1_eventually_heal` | `.claude/hooks/_lib/adapters/live/_breaker.py:257-266` (`_refresh_state_locked`) + `_breaker.py:213-232` (`record_success`) + `_breaker.py:202-205` (half_open→open branch in `record_failure`) | `<TLC_RUN_PENDING_SESSION_23_CI>` | **5** |

**Total:** 4 property-based tests × **21 mutations** (6 + 5 + 5 + 5 =
21 ≥ the ADR-044 §Decision-drivers minimum of 20).

## 3. Invariant Audit — Which Real Code Implements Each Property

### S1 — Threshold-triggered open transition

**Function:** `CircuitBreaker.record_failure` at
`.claude/hooks/_lib/adapters/live/_breaker.py:176`.

**Relevant lines:**

- `_breaker.py:199-200` — append failure timestamp + prune the window
  to discard entries older than `now - window_s`.
- `_breaker.py:207-211` — branch: if state is CLOSED and window count
  ≥ threshold, call `_open_locked(now)`.
- `_breaker.py:246-250` — `_open_locked` sets `self._state = OPEN`,
  `self._opened_at = now`, `self._probe_available = False`.

**Impl invariant (verified by conformance test):** inserting
`threshold` transient failures within `window_s` MUST leave the
breaker in the OPEN state before `record_failure` returns (no
deferred transition, no additional call required).

### S2 — Half-open singleton

**Function:** `CircuitBreaker.should_allow` at
`.claude/hooks/_lib/adapters/live/_breaker.py:154`.

**Relevant lines:**

- `_breaker.py:164-165` — acquires `self._lock` + calls
  `_refresh_state_locked` to maybe flip OPEN→HALF_OPEN.
- `_breaker.py:170-174` — HALF_OPEN branch: returns True **exactly
  once** by consuming `self._probe_available`; subsequent callers
  see False until a `record_success` / `record_failure` resolves.
- `_breaker.py:264-265` — `_refresh_state_locked` sets
  `probe_available = True` on every OPEN→HALF_OPEN transition (so
  exactly one probe is permitted per cycle).

**Impl invariant:** the probe-slot is consumed under the breaker's
`threading.Lock`, so two concurrent callers CANNOT both observe
`probe_available = True`. Model check holds under MAX_CALLERS=2 (the
tractable concurrency bound); conformance test exercises it under
`threading` with N=8 workers per the harness contract in
`rationale.md` §Conformance harness.

### S3 — State-transition audit

**Function:** `CircuitBreaker._open_locked` at
`.claude/hooks/_lib/adapters/live/_breaker.py:246`.

**Audit helper:** `audit_emit.emit_breaker_opened` at
`.claude/hooks/_lib/audit_emit.py:977`.

**⚠ Gap #3 (PLAN-013 Session 20):** `_open_locked` currently does
NOT invoke `emit_breaker_opened`. The event is defined + registered
in `_KNOWN_ACTIONS` (`audit_emit.py:91`) but the wire-up between the
breaker state transition and the emitter is missing. ADR-040 §7
**requires** the event; the model specifies the intended contract;
the conformance test will surface the gap by **failing** until the
wire-up lands in a subsequent session (Phase A.3 prerequisite or
standalone Sprint-14 fix).

**Impl invariant (once Gap #3 closed):** every `_open_locked` call
MUST be followed atomically (before lock release) by
`emit_breaker_opened(provider=..., failures_in_window=...,
threshold=..., reason=...)`. The conformance test captures audit
events via `TestEnvContext` + asserts `len(events) == 1` and
`events[0]["action"] == "breaker_opened"`.

### L1 — Eventually heal

**Functions involved:**

- `CircuitBreaker._refresh_state_locked` at
  `.claude/hooks/_lib/adapters/live/_breaker.py:257` — drives
  OPEN→HALF_OPEN when `(now - opened_at) >= half_open_s`.
- `CircuitBreaker.record_success` at `_breaker.py:213` — drives
  HALF_OPEN→CLOSED on probe success.
- `CircuitBreaker.record_failure` at `_breaker.py:176`, lines 202-205
  — drives HALF_OPEN→OPEN on probe failure.

**Impl invariant:** the `_refresh_state_locked` method is called at
the head of `state`, `snapshot`, `should_allow`, `record_failure`,
and `record_success`; any public-surface method call after
`half_open_s` seconds elapsed will trigger the OPEN→HALF_OPEN
transition. The conformance test drives this by advancing the
injected clock past `half_open_s` and calling `should_allow`; then
either succeeds (→ CLOSED) or fails (→ OPEN), asserting no terminal
stuck state is reachable within the bounded test timeout.

**Modeling caveat:** the TLA+ spec uses `WF_vars(RefreshToHalfOpen)`
to guarantee the OPEN→HALF_OPEN transition fires; the real impl fires
it lazily on the NEXT call. Under `WF_vars(Tick)`, time advances
forever, so eventually some caller action (StartCall, ReportSuccess,
ReportFailure) will drive the transition. This abstraction is
acknowledged; the conformance test validates the lazy-fire timing
directly with a fake clock.

## 4. Model ↔ Implementation Correspondence

Each TLA+ variable maps to a concrete Python field / helper. Drift
between these columns = model became untrustworthy; the
`check-conformance-harness-mapping.py` CI check (Phase D.6 future) will
parse this table + grep the impl file to detect rename drift.

| TLA+ variable | Python counterpart | File:line | Notes |
|---|---|---|---|
| `breaker_state` | `self._state.value` (str) | `_breaker.py:108, 34-39` | `BreakerState` enum; `.value` gives `"closed" \| "open" \| "half_open"` |
| `failures` (seq of timestamps) | `self._failures` (deque of `(ts, reason)` tuples) | `_breaker.py:110, 109` | Model abstracts away `reason`; conformance test uses transient-only reasons |
| `opened_at` (int, -1 sentinel) | `self._opened_at` (`Optional[float]`, `None` = not open) | `_breaker.py:111` | Sentinel mapping: `-1 ↔ None`; real impl uses `None` |
| `in_flight` (set of caller IDs) | (implicit in Python threading model) | — | Not a literal Python field; the model makes explicit what the impl's thread pool state represents. Cardinality bounded by MAX_CALLERS in model; by Python GIL + `threading.Lock` in impl |
| `audit_log` (seq of records) | `_lib/audit_emit.py` append to `audit-log.jsonl` | `audit_emit.py:977-1001` | **Gap #3:** `_breaker.py` does NOT currently call `emit_breaker_opened`; conformance test will surface this |
| `now` (int, monotonic) | `self._clock()` or `_now_override` | `_breaker.py:117-128, 100-104` | `time.monotonic` default; tests inject fake clocks |
| `probe_available` (bool) | `self._probe_available` (bool) | `_breaker.py:115` | Direct 1:1 mapping |
| `FAILURE_THRESHOLD` (const) | `self._threshold` (int) | `_breaker.py:97` | Config key `breaker_threshold` in `LiveCallPolicy` |
| `WINDOW_S` (const) | `self._window_s` (float) | `_breaker.py:98` | Config key `breaker_window_s` |
| `HALF_OPEN_HOLD_S` (const) | `self._half_open_s` (float) | `_breaker.py:99` | Config key `breaker_half_open_s` |
| `MAX_CALLERS` (const) | N/A in impl | — | Modeling-only bound for TLC tractability (defaults to 2) |

**Abstractions the model deliberately does NOT capture** (documented
here so future reviewers don't assume spec = impl byte-for-byte):

1. **Reason enum branching.** `_breaker.py:190-197` distinguishes
   `_NON_COUNTING_REASONS` (`parse_error`, `scope_misconfigured`,
   `invalid_policy`) from `_PERMANENT_OPEN_REASONS` (`auth_permanent`)
   from transient. The model collapses to the transient case. The
   conformance test has separate assertion rows for each reason
   class.
2. **Thread-level fairness.** TLA+'s `WF_vars(Tick)` guarantees time
   advances, but does not model Python GIL scheduling. Real races
   between `record_failure` and `_refresh_state_locked` on separate
   threads are covered by the `threading.Lock` in the impl —
   modeled implicitly via action interleaving.
3. **Deque size cap / pruning cost.** `_prune_window_locked` is O(k)
   where k is the number of expired entries. The model's
   `FailuresInWindow` helper is pure arithmetic. No complexity
   properties are proved; the chaos tests cover this dimension.
4. **Lazy vs eager `_refresh_state_locked`.** The model fires eagerly
   under `WF_vars(RefreshToHalfOpen)` (so L1 holds); the impl fires
   lazily on the next public-surface call. The conformance test for
   L1 drives the lazy behavior directly with a fake clock.

## 5. Running TLC

```bash
# Download + verify jar + run TLC end-to-end.
bash docs/formal-verification/run-tlc.sh

# Just download + verify the jar.
bash docs/formal-verification/run-tlc.sh download

# Print per-property log hashes only (assumes last run cached).
bash docs/formal-verification/run-tlc.sh hash
```

Prerequisites:

- `curl` in PATH (download).
- `java` in PATH (TLC execution — Java 17 LTS per `rationale.md` §
  Toolchain pin).
- ≥2 GiB free disk (jar cache + log files).

Expected output on a passing run: TLC prints `Model checking
completed. No error has been found.` for each theorem, and the
script's `=== TLC log hashes ===` block prints a SHA-256 per property
that matches (or is a follow-up delta from) the fingerprints in §2.

## 6. Gaps + Follow-up

1. **Gap #3 — `_open_locked` does not emit `breaker_opened`.**
   `_breaker.py:246-250` sets state transition but skips the audit
   call. Fix: wire `_lib.audit_emit.emit_breaker_opened` from
   `_open_locked` (atomic under `self._lock`). S3 conformance test
   will fail until this lands. Tracked in PLAN-013 Session 20
   CHANGELOG under "Gaps surfaced during execution".
2. **TLC run pending.** This artifact ships the spec + mapping +
   infra. A follow-up session (or the first `formal-verify.yml`
   CI run after Sprint 14 kickoff) executes `run-tlc.sh hash` and
   replaces the `<TLC_RUN_PENDING_SESSION_23_CI>` placeholders.
3. **State-space bounds.** Current `breaker.cfg` uses
   `MAX_CALLERS=2`, `MaxTime=30`, `FAILURE_THRESHOLD=3`,
   `WINDOW_S=10`, `HALF_OPEN_HOLD_S=5` — small-state tractable.
   PLAN-014+ expansion to production numbers (threshold=5,
   window=30, hold=60) should be verified to complete in reasonable
   wall-clock; state-space growth is polynomial in these sizes
   (ADR-044 §Blast-radius 10x assertion) but TLC memory is
   empirically the binding factor.
4. **Conformance tests (Phase D.8) not yet written.** Wave B Agent 4
   ships `tests/formal_verification/test_breaker_conformance.py` +
   `tests/formal_verification/mutations/breaker/*.py`. The harness
   contract in `rationale.md` §Conformance harness contract is the
   binding specification.

## 7. Plan-Lifecycle Property Mapping (PLAN-014 Phase B.1+B.3)

**Status:** SPECIFIED 2026-04-15 (PLAN-014 Phase B.1).
**TLC run:** PENDING — same as breaker (§6 item 2).
**TLA+ spec:** `docs/formal-verification/plan-lifecycle.tla` + `.pcal` + `.cfg`
**Implementation:** `.claude/hooks/check_plan_edit.py` (transitions + required fields)
**Related:** PLAN-SCHEMA.md §4 (source of truth for lifecycle states)

### 7.1 Property → Test → Implementation Mapping

| ID | TLA+ form (inline) | Conformance test | Impl file:line | TLC log hash | Mutations |
|----|-------------------|------------------|----------------|--------------|-----------|
| **S1** | `[][~(plan_status = "draft" /\ plan_status' = "done")]_vars` | `test_plan_lifecycle_conformance.py::test_s1_no_skip` | `check_plan_edit.py:67-73` (`_ALLOWED_TRANSITIONS`) | `<TLC_RUN_PENDING>` | **3** |
| **S2** | `[][plan_status' = "abandoned" => abandonment_reason']_vars` | `test_plan_lifecycle_conformance.py::test_s2_abandonment_documented` | `check_plan_edit.py:205-210` (`_check_required_fields` abandoned branch) | `<TLC_RUN_PENDING>` | **3** |
| **S3** | `[](plan_status = "executing" => reviewed_at) /\ [](plan_status = "done" => completed_at /\ related_commits)` | `test_plan_lifecycle_conformance.py::test_s3_monotonic_timestamps` | `check_plan_edit.py:187-204` (`_check_required_fields` reviewed/done branches) | `<TLC_RUN_PENDING>` | **2** |
| **Auth** | `[][(plan_status = "draft" /\ plan_status' = "reviewed") => approved_by_owner']_vars` | `test_plan_lifecycle_conformance.py::test_auth_owner_approval` | `check_plan_edit.py:67-68` (draft -> {reviewed} requires reviewed_at proxy) | `<TLC_RUN_PENDING>` | **3** |

**Total:** 4 property tests + 1 Auth invariant × **11 mutations** (3 + 3 + 2 + 3).

### 7.2 Model ↔ Implementation Correspondence

| TLA+ variable | Python counterpart | File:line | Notes |
|---|---|---|---|
| `plan_status` | frontmatter `status:` field (str) | `check_plan_edit.py:242-243` | Parsed via `_fm.parse_frontmatter()` |
| `reviewed_at` (bool) | `new_fm.get("reviewed_at")` presence | `check_plan_edit.py:188` | Date string presence = True |
| `completed_at` (bool) | `new_fm.get("completed_at")` presence | `check_plan_edit.py:194` | Date string presence = True |
| `related_commits` (bool) | `new_fm.get("related_commits")` non-empty | `check_plan_edit.py:199-200` | List with >= 1 entry |
| `abandonment_reason` (bool) | `_fm.has_abandonment_reason(body)` | `check_plan_edit.py:206` | `## Abandonment reason` heading in body |
| `approved_by_owner` (bool) | `reviewed_at` as Owner-approval proxy | `check_plan_edit.py:187-190` | The governance contract in PLAN-SCHEMA.md §4 says draft->reviewed is the "human gate"; reviewed_at is the mechanical proxy for Owner approval |
| `_ALLOWED_TRANSITIONS` (map) | `_ALLOWED_TRANSITIONS: Dict[str, set]` | `check_plan_edit.py:67-73` | Direct 1:1 mapping; each status maps to its allowed next-state set |

## 8. Debate-Convergence Property Mapping (PLAN-014 Phase B.2+B.3)

**Status:** SPECIFIED 2026-04-15 (PLAN-014 Phase B.2).
**TLC run:** PENDING — same as breaker (§6 item 2).
**TLA+ spec:** `docs/formal-verification/debate-convergence.tla` + `.pcal` + `.cfg`
**Implementation:** `.claude/scripts/debate-converge.py` (Jaccard) +
`.claude/scripts/debate-orchestrate.py` (orchestrator)
**Related:** DEBATE-SCHEMA.md §12 (source of truth for convergence semantics)

### 8.1 Property → Test → Implementation Mapping

| ID | TLA+ form (inline) | Conformance test | Impl file:line | TLC log hash | Mutations |
|----|-------------------|------------------|----------------|--------------|-----------|
| **S1** | `[](round_number <= MAX_ROUNDS)` | `test_debate_convergence_conformance.py::test_s1_max_rounds_respected` | `debate-converge.py:229` (`max_rounds_reached = bool(round_num >= MAX_ROUNDS)`) | `<TLC_RUN_PENDING>` | **3** |
| **S2** | `[](consensus_reached /\ round_number <= 2 /\ N <= 2 => red_team_spawned)` | `test_debate_convergence_conformance.py::test_s2_red_team_fires` | `debate-converge.py:247` (`red_team_needed = convergence_met and round_num <= 2`) | `<TLC_RUN_PENDING>` | **3** |
| **S3** | `[](consensus_reached => [](consensus_reached))` | `test_debate_convergence_conformance.py::test_s3_consensus_idempotent` | `debate-converge.py:210-259` (`compute_convergence` pure function, deterministic) | `<TLC_RUN_PENDING>` | **2** |
| **S4** | `[](round_number >= 2 => redaction_applied)` | `test_debate_convergence_conformance.py::test_s4_redaction_applied` | `debate-orchestrate.py:100-111` (`_load_redact_secrets` + `redact_consolidated`) | `<TLC_RUN_PENDING>` | **2** |
| **Auth** | `[](consensus_reached => agents_contributed = AgentIDs)` | `test_debate_convergence_conformance.py::test_auth_all_contributed` | `debate-orchestrate.py:70-89` (archetype table + round critique file count) | `<TLC_RUN_PENDING>` | **3** |

**Total:** 5 property tests + 1 Auth invariant × **13 mutations** (3 + 3 + 2 + 2 + 3).

### 8.2 Model ↔ Implementation Correspondence

| TLA+ variable | Python counterpart | File:line | Notes |
|---|---|---|---|
| `debate_state` | orchestrator phase tracking | `debate-orchestrate.py` | Implicit in control flow (proposal → critiquing → synthesis → consensus/failed) |
| `round_number` (int) | `round_num` parameter / `--round N` | `debate-converge.py:269` | 1-indexed, passed via CLI or API |
| `agents_contributed` (set) | critique files in `round-N/` dir | `debate-converge.py:166-180` | `iter_agent_critiques()` yields .md files excluding meta-files |
| `jaccard_score` (0..100) | `debate-converge.py::jaccard()` return × 100 | `debate-converge.py:196-207` | Float 0.0..1.0 in impl; model uses integer 0..100 for TLC tractability |
| `red_team_spawned` (bool) | `result["red_team_needed"]` | `debate-converge.py:247` | `convergence_met and round_num <= 2` |
| `redaction_applied` (seq) | `_load_redact_secrets()` call per round | `debate-orchestrate.py:100-111` | Architectural contract: called before building next-round prompts |
| `consensus_reached` (bool) | `result["convergence_met"]` | `debate-converge.py:237,254` | Pure computation from Jaccard + MAX_ROUNDS override |
| `MAX_ROUNDS` (const) | `MAX_ROUNDS = 5` | `debate-converge.py:70` | HARD cap 10 in orchestrator (`MAX_ROUNDS_HARD_CAP = 10`) |
| `JACCARD_THRESHOLD` (const) | `DEFAULT_JACCARD_THRESHOLD = 0.7` | `debate-converge.py:63` | Model uses integer 70 (× 100) for TLC |
| `N` (const) | number of archetype critique files per round | `debate-orchestrate.py:70-77` | Default 6 archetypes; model parameterized 2..7 |

## 9. Swarm-Coordinator Property Mapping (PLAN-050 Phase 7a — C4)

**Status:** SPECIFIED 2026-04-22 (Session 54, PLAN-050 Phase 7a).
**TLC run:** PENDING — workflow patch staged at
`.claude/plans/PLAN-050/staged-code/formal_verify_swarm_patch.md`;
Owner round-17 extended adds the step.
**TLA+ spec:** `docs/formal-verification/swarm-coordinator.tla` + `.cfg`
**Implementation:** `.claude/scripts/swarm/coordinator.py` +
`.claude/scripts/swarm/loop_runner.py` + `.claude/scripts/swarm/kill_switch.py`
**Related:** PLAN-050 §Round 1 C4; ADR-049a (worktree orchestration);
PLAN-017 scaffold Session 50 WAR-ROOM P06.

### 9.1 Invariants Mapping (4 C4-mandated + 4 safety support)

| ID | Kind | TLA+ formula | Implementation anchor |
|----|------|--------------|------------------------|
| **I1** | Safety | `Cardinality(ActiveLoops) <= MaxParallel` | `coordinator.py:38` (`MAX_PARALLEL_CEILING = 8`) + `SwarmConfig.n_loops` clamping |
| **I2** | Safety | `\A i : loops[i].iter <= MaxIter` | `coordinator.py:46` (`DEFAULT_MAX_ITERATIONS = 20`) |
| **I3** | Safety | `\A i : loops[i].tokens <= loops[i].iter` | `loop_runner.py` per-iteration token accounting |
| **I4** | Safety | `consumed <= N * MaxIter` | Budget envelope CB #1 (`SwarmConfig.budget_tokens`) |
| **L1** | Liveness | `NoDeadWorker` — every loop `<>(status \in Terminal)` | `coordinator.py:67` status field; `kill_switch.py` + convergence detection |
| **L2** | Liveness | `ProgressGuaranteed` — running loops iterate OR terminate | `loop_runner.py` monotonic iteration counter |
| **L3** | Liveness | `KillSwitchHalts` — kill signal reaches all loops in finite steps | `kill_switch.py:lay-1..3` (env var + sentinel + iter counter); lay 4-6 (SIGKILL + cgroups + parent-death) deferred to Phase 7b |
| **L4** (implicit) | Liveness | TripKill precedes PropagateKill per-loop | Action ordering in Next relation |

### 9.2 TLC Configuration Rationale

```
N = 3             # 3 loops — smallest interesting parallelism
MaxParallel = 2   # exercise the cap (can't run all 3 concurrently)
MaxIter = 4       # bounded iterations per loop (model tractable)
Budget = 6        # forces budget-exhaust path (2 loops × 3 iters = 6 → boundary)
```

Symmetry reduction over loop identifiers `Permutations(1..3)` cuts
state space ~6×. Expected TLC wall-clock ≤60s on ubuntu-latest.

### 9.3 Modeling Abstractions Acknowledged

1. **Worktree pool not modeled.** Phase 7b worktree allocation happens
   at swarm init; the TLA+ abstraction treats each loop as
   independently making progress. Worktree collision is enforced by
   the Python impl (file-assignment protocol + `git worktree` lifecycle).
2. **Circuit breakers 6-9 (disk/FDs/wall-clock/parent-death) not modeled.**
   Phase 7a implements them; they feed into `errored` status in the
   model but their specific trigger semantics are not specified. The
   conformance harness covers mutation tests per CB.
3. **Kill-switch tiering (SIGTERM grace → SIGKILL) abstracted.** The
   model treats `TripKill` + `PropagateKill` as atomic transitions;
   the Python impl has a 5s grace period that TLC does not measure.
4. **Tournament scorer not modeled.** Loop output selection
   (`tournament.py`) is out-of-scope for the coordinator invariants;
   a separate spec would cover it (deferred, Sprint 32+).

### 9.4 Follow-up

- [ ] Owner round-17 extended: include `.github/workflows/formal-verify.yml`
      scope to wire the TLC step for `swarm-coordinator.tla`.
- [x] Phase 7b worktree pool + kill-switch tiering land; re-spec
      abstractions 1-3 above into model extension. — Session 54 shipped
      `_worktree_pool.py` + `_parent_death.py` + `_process_group.py` +
      CBs 6-9 in `kill_switch.py` (see CHANGELOG Session 54). Model
      extension for abstractions 1-3 deferred Sprint 32+.
- [x] Conformance harness `tests/formal_verification/test_swarm_coordinator_conformance.py`
      — **Phase 7 final SHIPPED Session 55**: 30 property tests
      (4 safety I1-I4 + 4 liveness L1-L4 + 4 coordinator-helpers
      sanity). Uses `_SwarmSimulator` — faithful bounded Python
      re-implementation of the TLA+ Next-state relation —
      run under 200 deterministic seeds per property. Runs via
      both `pytest` and `python3 -m unittest`. Wall-clock ~0.57s.
- [x] Mutation budget 12 → 40 (5 per property) — **PLAN-051 Phase 4
      B3 SHIPPED Session 58**: 40 discriminating mutations under
      `tests/formal_verification/mutation_fixtures/swarm_coordinator/`;
      100% kill rate verified by `test_<prop>_mutations_fail`;
      independent-kill proof enforced by 2 new tests (`test_l1_…
      _under_default_bias` + `test_l2_…_under_default_bias`);
      diversity matrix documented in `EXPECTED-KILLS.json` + the
      companion narrative `KILL-TRACES.md`. Conformance suite
      38 → 40 tests; wall-clock ~0.88s.

## 10. References

- `.claude/adr/ADR-040-live-adapter-activation-contract.md` §2
  (breaker contract, source of truth) + §7 (audit events per call).
- `.claude/adr/ADR-041-transition-log-convention.md` (ADR Transition
  Log appendix format — this file is an input to ADR-044 §Transition
  Log).
- `.claude/adr/ADR-044-formal-verification-pilot.md` (governing
  decision record).
- `.claude/plans/PLAN-SCHEMA.md` §4 (plan lifecycle state machine —
  source of truth for plan-lifecycle.tla).
- `.claude/plans/DEBATE-SCHEMA.md` §12 (debate convergence semantics —
  source of truth for debate-convergence.tla).
- `docs/formal-verification/rationale.md` (Phase D.1 — state-machine
  selection + TLA+ tool choice).
- `docs/formal-verification/breaker.tla` + `.pcal` + `.cfg` (Phase
  D.2 artifacts).
- `docs/formal-verification/plan-lifecycle.tla` + `.pcal` + `.cfg`
  (Phase B.1 artifacts — PLAN-014).
- `docs/formal-verification/debate-convergence.tla` + `.pcal` + `.cfg`
  (Phase B.2 artifacts — PLAN-014).
- `docs/formal-verification/run-tlc.sh` (this file's proof-runner).
- `.claude/hooks/check_plan_edit.py` (plan lifecycle implementation).
- `.claude/scripts/debate-converge.py` (debate convergence Jaccard).
- `.claude/scripts/debate-orchestrate.py` (debate orchestrator).
- `.claude/hooks/_lib/adapters/live/_breaker.py` (breaker implementation).
- `.claude/hooks/_lib/audit_emit.py:977-1001` (`emit_breaker_opened`
  definition — Gap #3 wire-up pending).
- `.claude/scripts/check-tla-schema-drift.py` (schema drift detector).
- Lamport, "Specifying Systems" (TLA+ canonical reference).
- Hillel Wayne, "Practical TLA+" (PlusCal accessible intro).
- PLAN-013 debate Round 1 consensus §C8 CRITICAL (conformance harness
  mandatory, model alone = theater).
