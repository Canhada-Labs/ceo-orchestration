"""Mutation Auth-03: illegal status values accepted.

The lifecycle restricts status to {draft, reviewed, executing, done, abandoned}.
This mutation adds "in_progress" as a valid status, bypassing the legal-set check.
"""

from __future__ import annotations

from typing import Set

PROPERTY = "Auth"
DESCRIPTION = (
    "illegal status 'in_progress' accepted: status validation does not "
    "reject unknown status values."
)

ILLEGAL_STATUS = "in_progress"


def apply_legal_statuses(legal: Set[str]) -> Set[str]:
    """Return mutated legal status set with illegal value added."""
    mutated = set(legal)
    mutated.add(ILLEGAL_STATUS)
    return mutated
