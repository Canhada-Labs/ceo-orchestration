"""Mutation S1-03: MAX_ROUNDS compared against wrong variable.

Instead of comparing round_number against MAX_ROUNDS, compares
len(agents) against MAX_ROUNDS (always < MAX_ROUNDS for small N).
"""

from __future__ import annotations

PROPERTY = "S1"
DESCRIPTION = (
    "MAX_ROUNDS compared against agent count instead of round number: "
    "the check fires on number of agents, not rounds."
)

MUTATED_MAX_ROUNDS_CHECK = "wrong_var"
