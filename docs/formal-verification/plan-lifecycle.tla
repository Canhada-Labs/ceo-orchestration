---------------------------- MODULE plan_lifecycle ----------------------------
(***************************************************************************)
(* TLA+ specification of the PLAN-SCHEMA §4 Plan Lifecycle state machine.  *)
(*                                                                         *)
(* Correspondence: ``.claude/hooks/check_plan_edit.py``                    *)
(*   - plan_status  ↔ frontmatter ``status:`` field (str)                 *)
(*   - reviewed_at  ↔ frontmatter ``reviewed_at:`` presence (bool)        *)
(*   - completed_at ↔ frontmatter ``completed_at:`` presence (bool)       *)
(*   - related_commits ↔ frontmatter ``related_commits:`` non-empty       *)
(*   - abandonment_reason ↔ body contains ``## Abandonment reason``       *)
(*   - approved_by_owner ↔ Owner approval (Auth invariant ADJ-037)        *)
(*                                                                         *)
(* Author: QA Architect + Security composite, PLAN-014 Phase B.1.         *)
(* Date:   2026-04-15                                                      *)
(*                                                                         *)
(* Toolchain: TLA+ Tools 1.8.0 (SHA-pinned in run-tlc.sh).               *)
(***************************************************************************)

EXTENDS Integers, Sequences, FiniteSets, TLC

(***************************************************************************)
(* Model parameters.                                                       *)
(***************************************************************************)
CONSTANTS
  MaxSteps          \* finite step bound for TLC

ASSUME MaxSteps \in Nat

(***************************************************************************)
(* State variables.                                                         *)
(***************************************************************************)
VARIABLES
  plan_status,           \* "draft" | "reviewed" | "executing" | "done" | "abandoned"
  reviewed_at,           \* TRUE when reviewed_at field is present
  completed_at,          \* TRUE when completed_at field is present
  related_commits,       \* TRUE when related_commits is non-empty
  abandonment_reason,    \* TRUE when ## Abandonment reason section exists
  approved_by_owner,     \* TRUE when Owner approved the transition (Auth)
  step_count,            \* monotonic step counter for bounded model
  transition_log         \* Sequence of [from, to] records for audit

vars == <<plan_status, reviewed_at, completed_at, related_commits,
          abandonment_reason, approved_by_owner, step_count, transition_log>>

(***************************************************************************)
(* Type invariant.                                                          *)
(***************************************************************************)
Statuses == {"draft", "reviewed", "executing", "done", "abandoned"}

TypeOK ==
  /\ plan_status \in Statuses
  /\ reviewed_at \in BOOLEAN
  /\ completed_at \in BOOLEAN
  /\ related_commits \in BOOLEAN
  /\ abandonment_reason \in BOOLEAN
  /\ approved_by_owner \in BOOLEAN
  /\ step_count \in 0..MaxSteps
  /\ transition_log \in Seq([from: Statuses, to: Statuses])

(***************************************************************************)
(* Initial state.                                                           *)
(***************************************************************************)
Init ==
  /\ plan_status = "draft"
  /\ reviewed_at = FALSE
  /\ completed_at = FALSE
  /\ related_commits = FALSE
  /\ abandonment_reason = FALSE
  /\ approved_by_owner = FALSE
  /\ step_count = 0
  /\ transition_log = <<>>

(***************************************************************************)
(* Transition: draft -> reviewed (requires Owner approval + reviewed_at).  *)
(***************************************************************************)
DraftToReviewed ==
  /\ plan_status = "draft"
  /\ step_count < MaxSteps
  /\ approved_by_owner'  = TRUE    \* Owner must approve
  /\ reviewed_at' = TRUE           \* Required field
  /\ plan_status' = "reviewed"
  /\ step_count' = step_count + 1
  /\ transition_log' = Append(transition_log, [from |-> "draft", to |-> "reviewed"])
  /\ UNCHANGED <<completed_at, related_commits, abandonment_reason>>

(***************************************************************************)
(* Transition: reviewed -> executing.                                       *)
(***************************************************************************)
ReviewedToExecuting ==
  /\ plan_status = "reviewed"
  /\ step_count < MaxSteps
  /\ plan_status' = "executing"
  /\ step_count' = step_count + 1
  /\ transition_log' = Append(transition_log, [from |-> "reviewed", to |-> "executing"])
  /\ UNCHANGED <<reviewed_at, completed_at, related_commits,
                  abandonment_reason, approved_by_owner>>

(***************************************************************************)
(* Transition: executing -> done (requires completed_at + related_commits).*)
(***************************************************************************)
ExecutingToDone ==
  /\ plan_status = "executing"
  /\ step_count < MaxSteps
  /\ completed_at' = TRUE
  /\ related_commits' = TRUE
  /\ plan_status' = "done"
  /\ step_count' = step_count + 1
  /\ transition_log' = Append(transition_log, [from |-> "executing", to |-> "done"])
  /\ UNCHANGED <<reviewed_at, abandonment_reason, approved_by_owner>>

(***************************************************************************)
(* Transition: any non-terminal -> abandoned (requires abandonment_reason).*)
(***************************************************************************)
ToAbandoned ==
  /\ plan_status \in {"draft", "reviewed", "executing"}
  /\ step_count < MaxSteps
  /\ abandonment_reason' = TRUE
  /\ plan_status' = "abandoned"
  /\ step_count' = step_count + 1
  /\ transition_log' = Append(transition_log,
                               [from |-> plan_status, to |-> "abandoned"])
  /\ UNCHANGED <<reviewed_at, completed_at, related_commits, approved_by_owner>>

(***************************************************************************)
(* Next-state relation.                                                     *)
(***************************************************************************)
Next ==
  \/ DraftToReviewed
  \/ ReviewedToExecuting
  \/ ExecutingToDone
  \/ ToAbandoned

(***************************************************************************)
(* Specification.                                                           *)
(***************************************************************************)
Spec == Init /\ [][Next]_vars

(***************************************************************************)
(* ========== PROPERTIES ==========                                        *)
(***************************************************************************)

(***************************************************************************)
(* S1 — No-skip: draft cannot jump directly to done.                       *)
(* The lifecycle enforces draft->reviewed->executing->done; there is no    *)
(* direct draft->done edge in the transition graph.                        *)
(***************************************************************************)
S1_NoSkip ==
  [][~(plan_status = "draft" /\ plan_status' = "done")]_vars

(***************************************************************************)
(* S2 — Abandonment documented: every transition to abandoned requires     *)
(* abandonment_reason to be present in the post-state.                     *)
(***************************************************************************)
S2_AbandonmentDocumented ==
  [][plan_status' = "abandoned" => abandonment_reason']_vars

(***************************************************************************)
(* S3 — Monotonic timestamps: reviewed_at is set before executing,         *)
(* completed_at is set before done. Models the ordering constraint that    *)
(* check_plan_edit.py enforces via required-field checks.                  *)
(***************************************************************************)
S3_MonotonicTimestamps ==
  /\ [](plan_status = "executing" => reviewed_at)
  /\ [](plan_status = "done" => completed_at /\ related_commits)

(***************************************************************************)
(* Auth — Owner approval required for draft->reviewed (ADJ-037).           *)
(* The transition to reviewed MUST have approved_by_owner = TRUE.          *)
(***************************************************************************)
Auth_OwnerApproval ==
  [][
    (plan_status = "draft" /\ plan_status' = "reviewed")
    => approved_by_owner'
  ]_vars

(***************************************************************************)
(* Terminal — done and abandoned are absorbing states.                      *)
(***************************************************************************)
Terminal_Done ==
  [](plan_status = "done" => [](plan_status = "done"))

Terminal_Abandoned ==
  [](plan_status = "abandoned" => [](plan_status = "abandoned"))

(***************************************************************************)
(* Theorems.                                                                *)
(***************************************************************************)
THEOREM Spec => []TypeOK
THEOREM Spec => S1_NoSkip
THEOREM Spec => S2_AbandonmentDocumented
THEOREM Spec => S3_MonotonicTimestamps
THEOREM Spec => Auth_OwnerApproval
THEOREM Spec => Terminal_Done
THEOREM Spec => Terminal_Abandoned

=============================================================================
