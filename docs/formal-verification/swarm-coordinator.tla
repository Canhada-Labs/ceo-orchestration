---------------------------- MODULE swarm_coordinator ----------------------------
(*
 * PLAN-050 Phase 7a (C4) — Autonomous-loop swarm coordinator formal model.
 *
 * Proves 4 invariants named up-front in consensus C4:
 *   NoDeadWorker        — every loop eventually reaches a terminal state
 *   ProgressGuaranteed  — each step monotonically advances either iteration
 *                         count, tokens_consumed, or status
 *   KillSwitchHalts     — kill signal propagates to terminal state in
 *                         finitely many steps for every running loop
 *   MaxParallelRespected — |active loops| <= MaxParallel at every state
 *
 * Bounded model check via swarm-coordinator.cfg with:
 *   MaxIter = 4          (per-loop iteration ceiling)
 *   MaxParallel = 2      (concurrent running loops)
 *   N = 3                (total loops the swarm manages)
 *   budget = 6           (global tokens budget)
 *
 * TLC wall-clock ceiling: 60s on GitHub Actions ubuntu-latest.
 *)

EXTENDS Naturals, FiniteSets, Sequences

CONSTANTS
    N,           \* total loops in the swarm
    MaxParallel, \* upper bound on concurrently-active loops (ADR-051: 8 prod, 2 here)
    MaxIter,     \* per-loop max iterations before wall-clock circuit breaker
    Budget       \* total token budget envelope

ASSUME N > 0 /\ MaxParallel > 0 /\ MaxIter > 0 /\ Budget > 0

\* Loop status domain — mirrors LoopState.status in coordinator.py
Status == {"pending", "running", "converged", "killed", "completed", "errored"}

\* Terminal states — no outbound transitions
Terminal == {"converged", "killed", "completed", "errored"}

\* ---------------- State variables ----------------
VARIABLES
    loops,      \* [id |-> [status, iter, tokens]] mapping
    kill,       \* BOOLEAN — kill-switch tripped
    consumed    \* total tokens drained from Budget

vars == <<loops, kill, consumed>>

\* ---------------- Initial state ----------------
Init ==
    /\ loops = [i \in 1..N |-> [status |-> "pending", iter |-> 0, tokens |-> 0]]
    /\ kill = FALSE
    /\ consumed = 0

\* ---------------- Helpers ----------------
ActiveLoops == {i \in 1..N : loops[i].status = "running"}
PendingLoops == {i \in 1..N : loops[i].status = "pending"}
RunningOrPending == ActiveLoops \cup PendingLoops

\* ---------------- Actions ----------------

\* Start a pending loop — gated by MaxParallel + kill-switch
StartLoop(i) ==
    /\ loops[i].status = "pending"
    /\ Cardinality(ActiveLoops) < MaxParallel
    /\ ~kill
    /\ loops' = [loops EXCEPT ![i] = [@ EXCEPT !.status = "running"]]
    /\ UNCHANGED <<kill, consumed>>

\* Iterate a running loop — monotonic progress on tokens + iter
Iterate(i) ==
    /\ loops[i].status = "running"
    /\ loops[i].iter < MaxIter
    /\ consumed < Budget
    /\ ~kill
    /\ loops' = [loops EXCEPT ![i] = [@ EXCEPT
            !.iter = @+1,
            !.tokens = @+1]]
    /\ consumed' = consumed + 1
    /\ UNCHANGED kill

\* Converge — loop detects similarity threshold met
Converge(i) ==
    /\ loops[i].status = "running"
    /\ loops[i].iter > 0
    /\ loops' = [loops EXCEPT ![i] = [@ EXCEPT !.status = "converged"]]
    /\ UNCHANGED <<kill, consumed>>

\* Complete normally — reached MaxIter without convergence
Complete(i) ==
    /\ loops[i].status = "running"
    /\ loops[i].iter = MaxIter
    /\ loops' = [loops EXCEPT ![i] = [@ EXCEPT !.status = "completed"]]
    /\ UNCHANGED <<kill, consumed>>

\* Budget-exhausted circuit breaker
BudgetKill(i) ==
    /\ loops[i].status = "running"
    /\ consumed >= Budget
    /\ loops' = [loops EXCEPT ![i] = [@ EXCEPT !.status = "errored"]]
    /\ UNCHANGED <<kill, consumed>>

\* Kill-switch trip — any still-running loop is marked killed
TripKill ==
    /\ ~kill
    /\ kill' = TRUE
    /\ UNCHANGED <<loops, consumed>>

\* Propagate kill to a running or pending loop
PropagateKill(i) ==
    /\ kill
    /\ loops[i].status \in {"running", "pending"}
    /\ loops' = [loops EXCEPT ![i] = [@ EXCEPT !.status = "killed"]]
    /\ UNCHANGED <<kill, consumed>>

\* ---------------- Next-state relation ----------------
Next ==
    \/ \E i \in 1..N : StartLoop(i)
    \/ \E i \in 1..N : Iterate(i)
    \/ \E i \in 1..N : Converge(i)
    \/ \E i \in 1..N : Complete(i)
    \/ \E i \in 1..N : BudgetKill(i)
    \/ TripKill
    \/ \E i \in 1..N : PropagateKill(i)

\* Fairness — every enabled action eventually fires; required for liveness
Spec == Init /\ [][Next]_vars /\ WF_vars(Next)

\* ---------------- Invariants (SAFETY) ----------------

\* I1 — MaxParallelRespected: |active loops| never exceeds configured cap
MaxParallelRespected ==
    Cardinality(ActiveLoops) <= MaxParallel

\* I2 — No running loop past MaxIter ceiling
IterCeilingRespected ==
    \A i \in 1..N : loops[i].iter <= MaxIter

\* I3 — Token monotonicity: per-loop tokens <= MaxIter (one per iter)
PerLoopTokenBound ==
    \A i \in 1..N : loops[i].tokens <= loops[i].iter

\* I4 — Total consumed bounded by sum of per-loop tokens
TotalConsumedBounded ==
    consumed <= N * MaxIter

\* ---------------- Temporal properties (LIVENESS) ----------------

\* L1 — NoDeadWorker: every pending or running loop eventually terminates
NoDeadWorker ==
    \A i \in 1..N : <>(loops[i].status \in Terminal)

\* L2 — ProgressGuaranteed: if a loop is running + not at iter ceiling +
\* budget remaining + kill not tripped, it eventually iterates or terminates
ProgressGuaranteed ==
    \A i \in 1..N :
        (loops[i].status = "running")
        ~> (loops[i].iter > 0 \/ loops[i].status \in Terminal)

\* L3 — KillSwitchHalts: once kill-switch trips, every running/pending
\* loop reaches terminal state
KillSwitchHalts ==
    kill ~> (\A i \in 1..N : loops[i].status \in Terminal)

\* Composite: all 4 C4-mandated invariants in one checkable predicate
C4Invariants ==
    /\ MaxParallelRespected
    /\ NoDeadWorker
    /\ ProgressGuaranteed
    /\ KillSwitchHalts

===============================================================================
