------------------------- MODULE debate_convergence -------------------------
(***************************************************************************)
(* TLA+ specification of the DEBATE-SCHEMA §12 N-round debate convergence  *)
(* protocol with Jaccard similarity, Red Team contingent, and secret        *)
(* redaction between rounds.                                                *)
(*                                                                         *)
(* Correspondence: ``.claude/scripts/debate-converge.py`` (Jaccard),       *)
(*   ``.claude/scripts/debate-orchestrate.py`` (orchestrator).             *)
(*   - debate_state  ↔ orchestrator phase tracking                        *)
(*   - round_number  ↔ current round index (1-indexed)                    *)
(*   - agents_contributed ↔ set of archetype slugs that wrote critique    *)
(*   - jaccard_score ↔ compute_convergence().jaccard                      *)
(*   - red_team_spawned ↔ M1 gate fired flag                             *)
(*   - redaction_applied ↔ redact_consolidated() called                   *)
(*   - consensus_reached ↔ convergence_met AND all agents contributed     *)
(*                                                                         *)
(* Author: QA Architect + Security composite, PLAN-014 Phase B.2.         *)
(* Date:   2026-04-15                                                      *)
(*                                                                         *)
(* Toolchain: TLA+ Tools 1.8.0 (SHA-pinned in run-tlc.sh).               *)
(***************************************************************************)

EXTENDS Integers, Sequences, FiniteSets, TLC

(***************************************************************************)
(* Model parameters.                                                       *)
(***************************************************************************)
CONSTANTS
  N,                  \* number of debate agents (2..7)
  MAX_ROUNDS,         \* hard stop (default 5, hard cap 10)
  JACCARD_THRESHOLD   \* convergence threshold (modeled as integer percentage 0..100)

ASSUME
  /\ N \in 2..7
  /\ MAX_ROUNDS \in 1..10
  /\ JACCARD_THRESHOLD \in 0..100

(***************************************************************************)
(* State variables.                                                         *)
(***************************************************************************)
VARIABLES
  debate_state,         \* "proposal" | "critiquing" | "synthesis" | "consensus" | "failed"
  round_number,         \* current round (1-indexed)
  agents_contributed,   \* set of agent IDs that contributed this round
  jaccard_score,        \* simulated Jaccard × 100 (integer percentage)
  red_team_spawned,     \* TRUE if M1 gate has fired
  redaction_applied,    \* sequence of booleans: index i = redaction applied before round i+1
  consensus_reached,    \* TRUE once final consensus emitted
  all_agents            \* the full set of agent IDs (1..N)

vars == <<debate_state, round_number, agents_contributed, jaccard_score,
          red_team_spawned, redaction_applied, consensus_reached, all_agents>>

(***************************************************************************)
(* Type invariant.                                                          *)
(***************************************************************************)
DebateStates == {"proposal", "critiquing", "synthesis", "consensus", "failed"}
AgentIDs == 1..N

TypeOK ==
  /\ debate_state \in DebateStates
  /\ round_number \in 1..(MAX_ROUNDS + 1)
  /\ agents_contributed \subseteq AgentIDs
  /\ jaccard_score \in 0..100
  /\ red_team_spawned \in BOOLEAN
  /\ redaction_applied \in Seq(BOOLEAN)
  /\ consensus_reached \in BOOLEAN
  /\ all_agents = AgentIDs

(***************************************************************************)
(* Initial state.                                                           *)
(***************************************************************************)
Init ==
  /\ debate_state = "proposal"
  /\ round_number = 1
  /\ agents_contributed = {}
  /\ jaccard_score = 0
  /\ red_team_spawned = FALSE
  /\ redaction_applied = <<>>
  /\ consensus_reached = FALSE
  /\ all_agents = AgentIDs

(***************************************************************************)
(* Action: CEO posts proposal, debate enters critiquing phase.             *)
(***************************************************************************)
StartCritiquing ==
  /\ debate_state = "proposal"
  /\ debate_state' = "critiquing"
  /\ UNCHANGED <<round_number, agents_contributed, jaccard_score,
                  red_team_spawned, redaction_applied, consensus_reached, all_agents>>

(***************************************************************************)
(* Action: an agent contributes its critique for the current round.        *)
(***************************************************************************)
AgentContributes(a) ==
  /\ debate_state = "critiquing"
  /\ a \in AgentIDs
  /\ a \notin agents_contributed
  /\ agents_contributed' = agents_contributed \cup {a}
  /\ UNCHANGED <<debate_state, round_number, jaccard_score,
                  red_team_spawned, redaction_applied, consensus_reached, all_agents>>

(***************************************************************************)
(* Action: all agents contributed -> CEO synthesizes (checks convergence). *)
(* Jaccard score is non-deterministic in the model (TLC explores all       *)
(* possible scores 0..100).                                                 *)
(***************************************************************************)
Synthesize ==
  /\ debate_state = "critiquing"
  /\ agents_contributed = AgentIDs     \* all N agents must contribute
  /\ debate_state' = "synthesis"
  /\ \E score \in 0..100 : jaccard_score' = score
  /\ UNCHANGED <<round_number, agents_contributed, red_team_spawned,
                  redaction_applied, consensus_reached, all_agents>>

(***************************************************************************)
(* Action: synthesis -> consensus (convergence met).                        *)
(* If round <= 2 AND N <= 2, Red Team must fire before consensus.          *)
(***************************************************************************)
ReachConsensus ==
  /\ debate_state = "synthesis"
  /\ jaccard_score >= JACCARD_THRESHOLD
  /\ round_number >= 2                 \* round 1 cannot converge (no prev round)
  /\ \/ (round_number > 2)             \* no red team needed after round 2
     \/ (N > 2)                         \* red team only when N <= 2
     \/ red_team_spawned                \* red team already fired
  /\ debate_state' = "consensus"
  /\ consensus_reached' = TRUE
  /\ UNCHANGED <<round_number, agents_contributed, jaccard_score,
                  red_team_spawned, redaction_applied, all_agents>>

(***************************************************************************)
(* Action: M1 Red Team gate fires (early convergence with small N).        *)
(***************************************************************************)
SpawnRedTeam ==
  /\ debate_state = "synthesis"
  /\ jaccard_score >= JACCARD_THRESHOLD
  /\ round_number <= 2
  /\ N <= 2
  /\ ~red_team_spawned
  /\ red_team_spawned' = TRUE
  /\ UNCHANGED <<debate_state, round_number, agents_contributed, jaccard_score,
                  redaction_applied, consensus_reached, all_agents>>

(***************************************************************************)
(* Action: advance to next round (diverged or not converged yet).          *)
(* Redaction MUST be applied before advancing.                              *)
(***************************************************************************)
AdvanceRound ==
  /\ debate_state = "synthesis"
  /\ \/ jaccard_score < JACCARD_THRESHOLD  \* not converged
     \/ round_number < 2                    \* round 1 always advances (no Jaccard yet)
  /\ round_number < MAX_ROUNDS
  /\ ~consensus_reached
  /\ round_number' = round_number + 1
  /\ agents_contributed' = {}               \* reset for new round
  /\ debate_state' = "critiquing"
  /\ redaction_applied' = Append(redaction_applied, TRUE)  \* redaction applied
  /\ UNCHANGED <<jaccard_score, red_team_spawned, consensus_reached, all_agents>>

(***************************************************************************)
(* Action: max rounds reached without convergence -> failed.               *)
(***************************************************************************)
MaxRoundsExhausted ==
  /\ debate_state = "synthesis"
  /\ round_number >= MAX_ROUNDS
  /\ ~consensus_reached
  /\ jaccard_score < JACCARD_THRESHOLD
  /\ debate_state' = "failed"
  /\ UNCHANGED <<round_number, agents_contributed, jaccard_score,
                  red_team_spawned, redaction_applied, consensus_reached, all_agents>>

(***************************************************************************)
(* Next-state relation.                                                     *)
(***************************************************************************)
Next ==
  \/ StartCritiquing
  \/ \E a \in AgentIDs : AgentContributes(a)
  \/ Synthesize
  \/ ReachConsensus
  \/ SpawnRedTeam
  \/ AdvanceRound
  \/ MaxRoundsExhausted

(***************************************************************************)
(* Specification with weak fairness on all actions.                         *)
(***************************************************************************)
Spec == Init /\ [][Next]_vars /\ WF_vars(Next)

(***************************************************************************)
(* ========== PROPERTIES ==========                                        *)
(***************************************************************************)

(***************************************************************************)
(* S1 — Max rounds respected: round_number never exceeds MAX_ROUNDS.       *)
(***************************************************************************)
S1_MaxRoundsRespected ==
  [](round_number <= MAX_ROUNDS)

(***************************************************************************)
(* S2 — Red Team fires: if converged at round <= 2 with N <= 2,            *)
(* red_team_spawned must be TRUE before consensus can be reached.           *)
(***************************************************************************)
S2_RedTeamFires ==
  [](
    (consensus_reached /\ round_number <= 2 /\ N <= 2)
    => red_team_spawned
  )

(***************************************************************************)
(* S3 — Consensus idempotent: once consensus is reached it cannot flip.    *)
(***************************************************************************)
S3_ConsensusIdempotent ==
  [](consensus_reached => [](consensus_reached))

(***************************************************************************)
(* S4 — Redaction applied between rounds: before round N+1 starts,         *)
(* redaction MUST have been applied to round N's output.                    *)
(***************************************************************************)
S4_RedactionApplied ==
  [](
    round_number >= 2
    => (Len(redaction_applied) >= round_number - 1
        /\ \A i \in 1..Len(redaction_applied) : redaction_applied[i] = TRUE)
  )

(***************************************************************************)
(* Auth — All agents contributed before consensus (ADJ-037).               *)
(* Prevents forged consensus where not all N agents have contributed.       *)
(***************************************************************************)
Auth_AllContributed ==
  [](consensus_reached => agents_contributed = AgentIDs)

(***************************************************************************)
(* Theorems.                                                                *)
(***************************************************************************)
THEOREM Spec => []TypeOK
THEOREM Spec => S1_MaxRoundsRespected
THEOREM Spec => S2_RedTeamFires
THEOREM Spec => S3_ConsensusIdempotent
THEOREM Spec => S4_RedactionApplied
THEOREM Spec => Auth_AllContributed

=============================================================================
