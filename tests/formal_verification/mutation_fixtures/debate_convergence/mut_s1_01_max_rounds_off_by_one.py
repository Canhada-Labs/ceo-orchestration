"""Mutation S1-01: MAX_ROUNDS off-by-one — allows round MAX_ROUNDS+1.

compute_convergence uses ``round_num >= MAX_ROUNDS`` to trigger
max_rounds_reached. This mutation uses ``>`` instead of ``>=``,
allowing one extra round.
"""

from __future__ import annotations

PROPERTY = "S1"
DESCRIPTION = (
    "MAX_ROUNDS off-by-one: uses `>` instead of `>=`, allowing "
    "round_number to equal MAX_ROUNDS+1."
)

MUTATED_MAX_ROUNDS_CHECK = "gt"  # > instead of >=
