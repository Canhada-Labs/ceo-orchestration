"""Mutation Auth-01: consensus emitted without all agents contributing.

The Auth invariant requires all N agents to have contributed before
consensus can be reached. This mutation allows consensus with N-1 agents.
"""

from __future__ import annotations

PROPERTY = "Auth"
DESCRIPTION = (
    "consensus without full contribution: consensus_reached set to True "
    "when only N-1 of N agents have contributed."
)

PARTIAL_CONSENSUS = True
