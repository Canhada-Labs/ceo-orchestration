---------------------------- MODULE breaker ----------------------------
EXTENDS Integers, Sequences, FiniteSets, TLC

(***************************************************************************
 ADR-040 circuit breaker: finite abstraction of adapters/live/_breaker.py.
 A half-open epoch admits one NEW probe. Calls admitted before opening can
 still be in flight; should_allow does not cancel them. Counting all such
 calls as probes produced the 2026-10-13 false S2 counterexample.

 Time is represented by relative ages, not a clock frozen at MaxTime.
 Failure history is capped at the threshold: older entries cannot change a
 closed-state decision, and opening/closing clears it before recovery.
 Only the latest audit event and an alternating event bit are retained;
 the action property still checks that EACH opening emits a new event.
 These quotients keep the state graph finite without cutting off traces.

 Reports model counting failures only. Permanent/non-counting reasons,
 reset(), exceptions and audit I/O are covered by Python tests, not TLC.
 Progress assumes time advances, available callers attempt calls, and
 admitted calls eventually report; it does not promise network completion.
***************************************************************************)
CONSTANTS FAILURE_THRESHOLD, WINDOW_S, HALF_OPEN_HOLD_S, MAX_CALLERS
ASSUME /\ FAILURE_THRESHOLD >= 2 /\ WINDOW_S > 0
       /\ HALF_OPEN_HOLD_S > 0 /\ MAX_CALLERS > 0

VARIABLES breaker_state, failures, opened_age, in_flight,
          probe_available, probe_admissions, audit_log, audit_epoch
vars == <<breaker_state, failures, opened_age, in_flight,
          probe_available, probe_admissions, audit_log, audit_epoch>>
CallerIDs == 1..MAX_CALLERS
States == {"closed", "open", "half_open"}
Events == [action: {"breaker_opened"},
           cause: {"threshold_crossed", "half_open_probe_failed"}]
TypeOK ==
  /\ breaker_state \in States
  /\ failures \in Seq(0..WINDOW_S)
  /\ Len(failures) <= FAILURE_THRESHOLD
  /\ opened_age \in -1..HALF_OPEN_HOLD_S
  /\ in_flight \subseteq CallerIDs
  /\ probe_available \in BOOLEAN
  /\ probe_admissions \in 0..MAX_CALLERS
  /\ audit_log \in {<<>>} \cup {<<e>> : e \in Events}
  /\ audit_epoch \in BOOLEAN

Init ==
  /\ breaker_state = "closed" /\ failures = <<>>
  /\ opened_age = -1 /\ in_flight = {}
  /\ probe_available = FALSE /\ probe_admissions = 0
  /\ audit_log = <<>> /\ audit_epoch = FALSE

Min(a,b) == IF a < b THEN a ELSE b
AgeFailures == SelectSeq([i \in 1..Len(failures) |-> failures[i] + 1],
                        LAMBDA age: age <= WINDOW_S)
AddFailure == LET f == Append(failures, 0) IN
              IF Len(f) > FAILURE_THRESHOLD THEN Tail(f) ELSE f
Tick ==
  /\ failures' = AgeFailures
  /\ opened_age' = IF opened_age < 0 THEN -1
                    ELSE Min(opened_age + 1, HALF_OPEN_HOLD_S)
  /\ UNCHANGED <<breaker_state, in_flight, probe_available,
                  probe_admissions, audit_log, audit_epoch>>

RefreshToHalfOpen ==
  /\ breaker_state = "open" /\ opened_age = HALF_OPEN_HOLD_S
  /\ breaker_state' = "half_open" /\ probe_available' = TRUE
  /\ probe_admissions' = 0 /\ failures' = <<>>
  /\ UNCHANGED <<opened_age, in_flight, audit_log, audit_epoch>>

StartCall(c) ==
  /\ c \in CallerIDs \ in_flight
  /\ breaker_state = "closed" \/
       (breaker_state = "half_open" /\ probe_available)
  /\ in_flight' = in_flight \cup {c}
  /\ probe_available' = IF breaker_state = "half_open" THEN FALSE
                         ELSE probe_available
  /\ probe_admissions' = IF breaker_state = "half_open"
                          THEN probe_admissions + 1 ELSE probe_admissions
  /\ UNCHANGED <<breaker_state, failures, opened_age, audit_log, audit_epoch>>

\* The implementation refreshes lazily before reporting. Force the abstract
\* refresh first when the timer has elapsed, then allow the report.
CanReport == breaker_state # "open" \/ opened_age < HALF_OPEN_HOLD_S
ReportSuccess(c) ==
  /\ c \in in_flight /\ CanReport
  /\ in_flight' = in_flight \ {c}
  /\ breaker_state' = "closed"
  /\ failures' = IF breaker_state = "closed" THEN failures ELSE <<>>
  /\ opened_age' = -1 /\ probe_available' = FALSE
  /\ UNCHANGED <<probe_admissions, audit_log, audit_epoch>>

ReportFailure(c) ==
  /\ c \in in_flight /\ CanReport
  /\ in_flight' = in_flight \ {c}
  /\ failures' = AddFailure
  /\ IF breaker_state = "half_open" \/
         (breaker_state = "closed" /\ Len(AddFailure) >= FAILURE_THRESHOLD)
     THEN /\ breaker_state' = "open" /\ opened_age' = 0
          /\ probe_available' = FALSE
          /\ audit_epoch' = ~audit_epoch
          /\ audit_log' = <<[action |-> "breaker_opened",
               cause |-> IF breaker_state = "half_open"
                         THEN "half_open_probe_failed"
                         ELSE "threshold_crossed"]>>
     ELSE UNCHANGED <<breaker_state, opened_age, probe_available,
                       audit_epoch, audit_log>>
  /\ UNCHANGED probe_admissions

StartAny == \E c \in CallerIDs : StartCall(c)
Report(c) == ReportSuccess(c) \/ ReportFailure(c)
Next == Tick \/ RefreshToHalfOpen \/ StartAny \/
        (\E c \in CallerIDs : Report(c))
Spec == Init /\ [][Next]_vars
        /\ WF_vars(Tick) /\ WF_vars(RefreshToHalfOpen)
        /\ WF_vars(StartAny) /\ (\A c \in CallerIDs : WF_vars(Report(c)))

\* Count only admissions in the CURRENT recovery epoch, never legacy calls.
S2_HalfOpenSingleton == [](breaker_state = "half_open" =>
  (probe_admissions <= 1 /\ (probe_available => probe_admissions = 0)))
\* A counting failure at the threshold cannot leave the breaker closed.
S1_OpenOnThreshold == [](breaker_state = "closed" =>
                         Len(failures) < FAILURE_THRESHOLD)
S3_OpenEmitsAudit == [][
  (breaker_state # "open" /\ breaker_state' = "open") =>
    (audit_epoch' # audit_epoch /\ Len(audit_log') = 1 /\
     audit_log'[1].action = "breaker_opened")
]_vars
\* A legacy success may close OPEN directly: _breaker.py explicitly handles
\* that race. Neither OPEN nor HALF_OPEN may remain stuck under fairness.
L1_EventuallyHeal ==
  /\ [](breaker_state = "open" => <>(breaker_state # "open"))
  /\ [](breaker_state = "half_open" => <>(breaker_state # "half_open"))

THEOREM Spec => []TypeOK
THEOREM Spec => S1_OpenOnThreshold
THEOREM Spec => S2_HalfOpenSingleton
THEOREM Spec => S3_OpenEmitsAudit
THEOREM Spec => L1_EventuallyHeal
=============================================================================
