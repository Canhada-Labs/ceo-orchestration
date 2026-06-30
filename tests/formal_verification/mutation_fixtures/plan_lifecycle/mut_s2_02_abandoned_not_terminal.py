"""Mutation S2-02: abandoned is not terminal — allows abandoned->draft.

The lifecycle says abandoned is absorbing. This mutation adds "draft"
to abandoned's allowed set, allowing resurrection without proper process.
"""

from __future__ import annotations

from typing import Dict, Set

PROPERTY = "S2"
DESCRIPTION = (
    "abandoned not terminal: allows abandoned->draft transition, "
    "violating the absorbing-state invariant."
)


def apply(transitions: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    """Return mutated transitions with abandoned->draft added."""
    mutated = {k: set(v) for k, v in transitions.items()}
    mutated["abandoned"].add("draft")
    return mutated
