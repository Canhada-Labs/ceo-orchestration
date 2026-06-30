"""Mutation Auth-03: duplicate agent contributions counted.

The same agent can contribute twice and each contribution is counted
separately, allowing consensus with fewer unique agents.
"""

from __future__ import annotations

PROPERTY = "Auth"
DESCRIPTION = (
    "duplicate agent contributions counted: a single agent contributing "
    "twice counts as 2, allowing forged N-agent consensus."
)

ALLOW_DUPLICATES = True
