"""Mutation S3-01: consensus flag can flip back to False.

Once consensus_reached is set to True, it should never become False.
This mutation allows the flag to be reset on a subsequent synthesis.
"""

from __future__ import annotations

PROPERTY = "S3"
DESCRIPTION = (
    "consensus_reached can flip back to False: a subsequent synthesis "
    "round resets the consensus flag, violating idempotency."
)

CONSENSUS_CAN_FLIP = True
