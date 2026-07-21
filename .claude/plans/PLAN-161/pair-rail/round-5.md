Findings:

1. **P1** — `.claude/plans/PLAN-161-maintenance-sweep.md:543-546`, `:561-568`, `:687-690`  
   The round-4 OQ3 fix is incomplete. The Wave-3 check and success criterion accept an explicit Owner-approved 2-lane fallback, but L3 still says every degraded run leaves PLAN-156-FOLLOWUP at `reviewed`. Thus an accepted fallback cannot execute the required transition to `done`.  
   **Change:** Add an explicit L3 branch where Owner acceptance of the documented 2-lane result transitions the follow-up `reviewed → executing → done`; retain the current open-plan behavior only for HOLD.

2. **P1** — `.claude/plans/PLAN-161-maintenance-sweep.md:264-283`  
   Wave 1’s check requires the new upgrade regression tests to exit successfully, while W1a explicitly requires those same tests to remain RED against the current sources until Wave 2. Because the command is an `&&` chain, the intended RED result makes the stated Wave-1 oracle fail and prevents later checks from running.  
   **Change:** Define the Wave-1 oracle as an explicit expected-failure proof for those regression tests, with the count checks run separately, or move their green execution exclusively into the staged Wave-2 oracle.

Round-4 verification: F1 is substantively specified at `:485-501`; F2 at `:569-588`; and F4 at `:444-452`. F3 remains unresolved because of finding 1.

VERDICT: REJECT