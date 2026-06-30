"""Mutation S2-03: allow done->abandoned transition.

The lifecycle says done is terminal. This mutation adds "abandoned"
to done's allowed set, violating the terminal-state invariant.
"""

from __future__ import annotations

from typing import Dict, Set

PROPERTY = "S2"
DESCRIPTION = (
    "done->abandoned allowed: done is no longer terminal, "
    "violating the absorbing-state invariant for done."
)


def apply(transitions: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    """Return mutated transitions with done->abandoned added."""
    mutated = {k: set(v) for k, v in transitions.items()}
    mutated["done"].add("abandoned")
    return mutated
