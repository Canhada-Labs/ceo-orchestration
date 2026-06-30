"""Mutation Auth-02: agent count check uses wrong comparison.

Instead of checking agents_contributed == all_agents, checks
len(agents_contributed) > 0 (at least one agent is enough for consensus).
"""

from __future__ import annotations

PROPERTY = "Auth"
DESCRIPTION = (
    "forged agent count: consensus allowed when len(contributed) > 0 "
    "instead of len(contributed) == N."
)

MIN_AGENTS_FOR_CONSENSUS = 1  # should be N
