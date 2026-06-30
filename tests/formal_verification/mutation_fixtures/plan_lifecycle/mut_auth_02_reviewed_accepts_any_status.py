"""Mutation Auth-02: any status can transition to reviewed.

The lifecycle restricts reviewed as a target of draft only.
This mutation allows executing->reviewed and done->reviewed.
"""

from __future__ import annotations

from typing import Dict, Set

PROPERTY = "Auth"
DESCRIPTION = (
    "any->reviewed allowed: executing and done can transition to reviewed, "
    "bypassing the sequential lifecycle flow."
)


def apply(transitions: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    """Return mutated transitions where any state can reach reviewed."""
    mutated = {k: set(v) for k, v in transitions.items()}
    mutated["executing"].add("reviewed")
    mutated["done"].add("reviewed")
    return mutated
