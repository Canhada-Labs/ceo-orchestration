"""Mutation S2-02: Red Team fires at wrong round threshold.

Instead of round <= 2, uses round <= 0 (never fires since
round is 1-indexed).
"""

from __future__ import annotations

PROPERTY = "S2"
DESCRIPTION = (
    "Red Team round threshold set to 0: the M1 gate condition "
    "round_number <= 0 is never true (rounds are 1-indexed)."
)

RED_TEAM_ROUND_THRESHOLD = 0
