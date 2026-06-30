"""Mutation S1-02: MAX_ROUNDS check disabled entirely.

The orchestrator's max-rounds gate is removed, allowing unbounded rounds.
"""

from __future__ import annotations

PROPERTY = "S1"
DESCRIPTION = (
    "MAX_ROUNDS check disabled: orchestrator never triggers "
    "max_rounds_reached, allowing infinite rounds."
)

MUTATED_MAX_ROUNDS_CHECK = "disabled"
