"""Mutation S1-01: allow draft->done direct transition.

The plan lifecycle forbids draft->done (must go through reviewed->executing).
This mutation adds "done" to the draft->next set, violating S1 no-skip.
"""

from __future__ import annotations

from typing import Dict, Set

PROPERTY = "S1"
DESCRIPTION = (
    "draft->done direct transition allowed: adds 'done' to draft's "
    "allowed next states, violating the no-skip invariant."
)


def apply(transitions: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    """Return mutated transitions with draft->done added."""
    mutated = {k: set(v) for k, v in transitions.items()}
    mutated["draft"].add("done")
    return mutated
