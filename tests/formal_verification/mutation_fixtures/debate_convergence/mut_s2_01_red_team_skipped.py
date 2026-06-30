"""Mutation S2-01: Red Team gate completely skipped.

When convergence occurs at round <= 2 with N <= 2, the M1 gate
should fire. This mutation removes the gate entirely.
"""

from __future__ import annotations

PROPERTY = "S2"
DESCRIPTION = (
    "Red Team M1 gate removed: convergence at round <= 2 with N <= 2 "
    "proceeds to consensus without spawning Red Team."
)

SKIP_RED_TEAM = True
