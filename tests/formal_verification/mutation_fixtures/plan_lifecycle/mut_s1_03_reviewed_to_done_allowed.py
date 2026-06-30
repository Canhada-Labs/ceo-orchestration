"""Mutation S1-03: allow reviewed->done direct transition.

Skips the executing state. The lifecycle requires reviewed->executing->done.
This mutation adds "done" to reviewed's allowed set.
"""

from __future__ import annotations

from typing import Dict, Set

PROPERTY = "S1"
DESCRIPTION = (
    "reviewed->done direct transition allowed: skips executing state, "
    "violating the sequential lifecycle."
)


def apply(transitions: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    """Return mutated transitions with reviewed->done added."""
    mutated = {k: set(v) for k, v in transitions.items()}
    mutated["reviewed"].add("done")
    return mutated
