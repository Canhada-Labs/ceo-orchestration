---------------------------- MODULE breaker ----------------------------
(***************************************************************************)
(* TLA+ specification of the ADR-040 §2 Live-Adapter Circuit Breaker.      *)
(*                                                                         *)
(* Correspondence: ``.claude/hooks/_lib/adapters/live/_breaker.py``       *)
(*   - breaker_state   ↔ self._state.value (str)                          *)
(*   - failures        ↔ self._failures (deque of (ts, reason))           *)
(*   - opened_at       ↔ self._opened_at (Optional[float], -1 ≡ None)     *)
(*   - in_flight       ↔ set of caller IDs holding a slot after          *)
(*                       should_allow() returned True and before          *)
(*                       record_success/record_failure resolves            *)
(*   - audit_log       ↔ sequence appended on every closed→open  or      *)
(*                       half_open→open transition (INTENDED behavior per *)
(*                       ADR-040 §7 — see properties-proved.md §4 gap).   *)
(*   - now             ↔ self._clock() monotonic seconds                  *)
(*   - probe_available ↔ self._probe_available                           *)
(*                                                                         *)
(* Author: Principal QA Architect + Principal Security Engineer           *)
(*         (composite), PLAN-013 Phase D.2.                               *)
(* Date:   2026-04-16                                                     *)
(*                                                                         *)
(* Toolchain: TLA+ Tools 1.8.0 (SHA-pinned in run-tlc.sh). Invoke via     *)
(* ``bash docs/formal-verification/run-tlc.sh``.                          *)
(***************************************************************************)

EXTENDS Integers, Sequences, FiniteSets, TLC

(***************************************************************************)
(* Model parameters. Defaults match ``LiveCallPolicy`` in _policy.py.      *)
(* Override via ``breaker.cfg`` or ``-config`` when wider pilots run.      *)
(***************************************************************************)
CONSTANTS
  FAILURE_THRESHOLD,   \* breaker opens after this many consecutive fails
  WINDOW_S,            \* rolling failure window in seconds
  HALF_OPEN_HOLD_S,    \* open → half_open delay in seconds
  MaxTime,             \* finite time bound for TLC
  MAX_CALLERS          \* concurrency bound (2 for tractability)

ASSUME
  /\ FAILURE_THRESHOLD \in Nat \ {0, 1}
  /\ WINDOW_S \in Nat \ {0}
  /\ HALF_OPEN_HOLD_S \in Nat \ {0}
  /\ MaxTime \in Nat
  /\ MAX_CALLERS \in Nat \ {0}

(***************************************************************************)
(* State variables.                                                         *)
(***************************************************************************)
VARIABLES
  breaker_state,       \* "closed" | "open" | "half_open"
  failures,            \* Sequence of failure timestamps (monotonic seconds)
  opened_at,           \* monotonic seconds; -1 sentinel for None
  in_flight,           \* Set of caller IDs currently in flight (<= MAX_CALLERS)
  audit_log,           \* Sequence of audit records ({action, time, cause})
  now,                 \* current monotonic time
  probe_available      \* half-open singleton probe slot

vars == <<breaker_state, failures, opened_at, in_flight, audit_log, now, probe_available>>

(***************************************************************************)
(* Type invariant. Every reachable state is well-formed.                    *)
(***************************************************************************)
States == {"closed", "open", "half_open"}
CallerIDs == 1..MAX_CALLERS

TypeOK ==
  /\ breaker_state \in States
  /\ failures \in Seq(0..MaxTime)
  /\ opened_at \in -1..MaxTime
  /\ in_flight \subseteq CallerIDs
  /\ audit_log \in Seq([action: {"breaker_opened"}, time: 0..MaxTime, cause: {"threshold_crossed", "half_open_probe_failed"}])
  /\ now \in 0..MaxTime
  /\ probe_available \in BOOLEAN

(***************************************************************************)
(* Helper: count of failure timestamps within the rolling window.          *)
(* Mirrors the deque pruner in _breaker.py:252-255 _prune_window_locked.   *)
(***************************************************************************)
FailuresInWindow(seq, t) ==
  Cardinality({ i \in 1..Len(seq) : seq[i] >= t - WINDOW_S })

(***************************************************************************)
(* Initial state.                                                           *)
(***************************************************************************)
Init ==
  /\ breaker_state = "closed"
  /\ failures = <<>>
  /\ opened_at = -1
  /\ in_flight = {}
  /\ audit_log = <<>>
  /\ now = 0
  /\ probe_available = FALSE

(***************************************************************************)
(* Action: time advances. Models _breaker.py:117-128 self._now() progress. *)
(* This action is the only one that advances ``now``; TLC with weak        *)
(* fairness on Tick guarantees no stuck-state for liveness property L1.    *)
(***************************************************************************)
Tick ==
  /\ now < MaxTime
  /\ now' = now + 1
  /\ UNCHANGED <<breaker_state, failures, opened_at, in_flight, audit_log, probe_available>>

(***************************************************************************)
(* Action: open→half_open timer. Fires whenever open state AND             *)
(* HALF_OPEN_HOLD_S elapsed. Mirrors _breaker.py:257-266                   *)
(* _refresh_state_locked. Note: impl fires this lazily on the NEXT         *)
(* call; model fires eagerly so liveness property L1 holds. This is a      *)
(* modeling abstraction — the real impl transitions at the latest on      *)
(* the next should_allow() / record_* call, which the conformance test    *)
(* validates with fake-clock injection.                                    *)
(***************************************************************************)
RefreshToHalfOpen ==
  /\ breaker_state = "open"
  /\ opened_at >= 0
  /\ (now - opened_at) >= HALF_OPEN_HOLD_S
  /\ breaker_state' = "half_open"
  /\ probe_available' = TRUE
  /\ failures' = <<>>
  /\ UNCHANGED <<opened_at, in_flight, audit_log, now>>

(***************************************************************************)
(* Action: caller acquires an in-flight slot. Models should_allow().       *)
(* Mirrors _breaker.py:154-174.                                            *)
(***************************************************************************)
StartCall(c) ==
  /\ c \in CallerIDs
  /\ c \notin in_flight
  /\ \/ /\ breaker_state = "closed"
        /\ in_flight' = in_flight \cup {c}
        /\ UNCHANGED <<breaker_state, failures, opened_at, audit_log, now, probe_available>>
     \/ /\ breaker_state = "half_open"
        /\ probe_available
        /\ probe_available' = FALSE
        /\ in_flight' = in_flight \cup {c}
        /\ UNCHANGED <<breaker_state, failures, opened_at, audit_log, now>>

(***************************************************************************)
(* Action: caller reports success. Mirrors _breaker.py:213-232.            *)
(***************************************************************************)
ReportSuccess(c) ==
  /\ c \in in_flight
  /\ in_flight' = in_flight \ {c}
  /\ \/ /\ breaker_state = "half_open"
        /\ breaker_state' = "closed"
        /\ opened_at' = -1
        /\ probe_available' = FALSE
        /\ failures' = <<>>
        /\ UNCHANGED <<audit_log, now>>
     \/ /\ breaker_state = "closed"
        /\ UNCHANGED <<breaker_state, failures, opened_at, audit_log, now, probe_available>>

(***************************************************************************)
(* Action: caller reports failure. Mirrors _breaker.py:176-211.            *)
(* transient-only abstraction (permanent/non-counting reasons are folded   *)
(* into the "transient" case for modeling tractability). The concrete     *)
(* impl's reason-branch is covered by the conformance test matrix.        *)
(***************************************************************************)
ReportFailure(c) ==
  /\ c \in in_flight
  /\ in_flight' = in_flight \ {c}
  /\ LET window_fails == FailuresInWindow(Append(failures, now), now)
     IN
       \* Half-open probe failed → re-open.
       \/ /\ breaker_state = "half_open"
          /\ breaker_state' = "open"
          /\ opened_at' = now
          /\ failures' = Append(failures, now)
          /\ probe_available' = FALSE
          /\ audit_log' = Append(audit_log,
                                 [action |-> "breaker_opened",
                                  time   |-> now,
                                  cause  |-> "half_open_probe_failed"])
          /\ UNCHANGED now
       \* Threshold crossed in closed state → open.
       \/ /\ breaker_state = "closed"
          /\ window_fails >= FAILURE_THRESHOLD
          /\ breaker_state' = "open"
          /\ opened_at' = now
          /\ failures' = Append(failures, now)
          /\ probe_available' = FALSE
          /\ audit_log' = Append(audit_log,
                                 [action |-> "breaker_opened",
                                  time   |-> now,
                                  cause  |-> "threshold_crossed"])
          /\ UNCHANGED now
       \* Closed + failure but below threshold → stay closed, append.
       \/ /\ breaker_state = "closed"
          /\ window_fails < FAILURE_THRESHOLD
          /\ failures' = Append(failures, now)
          /\ UNCHANGED <<breaker_state, opened_at, audit_log, now, probe_available>>

(***************************************************************************)
(* Next-state relation.                                                     *)
(***************************************************************************)
Next ==
  \/ Tick
  \/ RefreshToHalfOpen
  \/ \E c \in CallerIDs : StartCall(c) \/ ReportSuccess(c) \/ ReportFailure(c)

(***************************************************************************)
(* Specification with weak fairness on Tick + RefreshToHalfOpen so L1      *)
(* (liveness) holds. Without fairness, an infinite stutter of zero Tick    *)
(* would falsify L1 trivially.                                              *)
(***************************************************************************)
Spec == Init /\ [][Next]_vars /\ WF_vars(Tick) /\ WF_vars(RefreshToHalfOpen)

(***************************************************************************)
(* ========== PROPERTIES ==========                                        *)
(***************************************************************************)

(***************************************************************************)
(* S1 — Threshold-triggered open transition (safety).                      *)
(*                                                                          *)
(* When FAILURE_THRESHOLD failures accumulate within WINDOW_S, the         *)
(* breaker MUST transition from closed to open.                            *)
(*                                                                          *)
(* Corresponds to _breaker.py:207-211 in ``record_failure``.               *)
(***************************************************************************)
S1_OpenOnThreshold ==
  [](
    (breaker_state = "closed" /\ FailuresInWindow(failures, now) >= FAILURE_THRESHOLD)
    => <>(breaker_state = "open")
  )

(***************************************************************************)
(* S2 — Half-open singleton (safety).                                      *)
(*                                                                          *)
(* While in "half_open", at most ONE caller may hold an in-flight slot.    *)
(* Enforced by probe_available gate in _breaker.py:170-174.                *)
(***************************************************************************)
S2_HalfOpenSingleton ==
  [](breaker_state = "half_open" => Cardinality(in_flight) <= 1)

(***************************************************************************)
(* S3 — State-transition audit (safety).                                   *)
(*                                                                          *)
(* Every closed→open transition appends an audit record with action         *)
(* "breaker_opened". Corresponds to the INTENDED contract in ADR-040 §7;   *)
(* the real impl currently does NOT emit this event from _open_locked     *)
(* (Gap #3 from PLAN-013 Session-20 findings). The conformance test        *)
(* asserts intended behavior; it will fail against current _breaker.py    *)
(* and pass once the emit hook is added.                                   *)
(***************************************************************************)
S3_OpenEmitsAudit ==
  [][
    (breaker_state = "closed" /\ breaker_state' = "open")
    => /\ Len(audit_log') > Len(audit_log)
       /\ audit_log'[Len(audit_log')].action = "breaker_opened"
  ]_vars

(***************************************************************************)
(* L1 — Eventually heal (liveness).                                        *)
(*                                                                          *)
(* A breaker in "open" eventually transitions to "half_open" (under        *)
(* HALF_OPEN_HOLD_S bounded time), and a breaker in "half_open" eventually *)
(* transitions to either "closed" (success) or "open" (failure). No        *)
(* terminal stuck state.                                                   *)
(*                                                                          *)
(* Requires weak-fairness on Tick + RefreshToHalfOpen + some caller        *)
(* eventually reporting (modeled implicitly by the non-empty process       *)
(* pool; the spec does NOT require WF on caller reports — if no caller    *)
(* EVER reports, the half_open state may persist indefinitely, which is    *)
(* a modeling gap acknowledged in properties-proved.md §4).                *)
(***************************************************************************)
L1_EventuallyHeal ==
  /\ []( breaker_state = "open"
         => <>(breaker_state = "half_open") )
  /\ []( breaker_state = "half_open"
         => <>(breaker_state \in {"closed", "open"}) )

(***************************************************************************)
(* Top-level theorems. TLC verifies each by enumerating reachable states   *)
(* under Spec. Run via run-tlc.sh.                                         *)
(***************************************************************************)
THEOREM Spec => []TypeOK
THEOREM Spec => S1_OpenOnThreshold
THEOREM Spec => S2_HalfOpenSingleton
THEOREM Spec => S3_OpenEmitsAudit
THEOREM Spec => L1_EventuallyHeal

=============================================================================
