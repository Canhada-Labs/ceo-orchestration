"""Mutation S1-02: allow draft->executing direct transition.

Skips the Owner review gate. The lifecycle requires draft->reviewed->executing.
This mutation adds "executing" to draft's allowed set.
"""

from __future__ import annotations

from typing import Dict, Set

PROPERTY = "S1"
DESCRIPTION = (
    "draft->executing direct transition allowed: skips the reviewed state, "
    "violating the mandatory Owner review gate."
)


def apply(transitions: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    """Return mutated transitions with draft->executing added."""
    mutated = {k: set(v) for k, v in transitions.items()}
    mutated["draft"].add("executing")
    return mutated
