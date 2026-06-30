"""Mutation S2-03: Red Team N check inverted.

Instead of firing when N <= 2, fires when N > 2 (wrong direction).
This means small debates skip the anti-groupthink gate.
"""

from __future__ import annotations

PROPERTY = "S2"
DESCRIPTION = (
    "Red Team N check inverted: fires when N > 2 instead of N <= 2, "
    "so small debates (most vulnerable to groupthink) skip the gate."
)

RED_TEAM_N_INVERTED = True
