"""Mutation Auth-01: draft->reviewed without Owner approval gate.

The lifecycle requires Owner approval for draft->reviewed. This mutation
removes the reviewed_at check entirely, allowing unapproved transitions.
"""

from __future__ import annotations

from typing import Dict, Set

PROPERTY = "Auth"
DESCRIPTION = (
    "Owner approval gate removed: draft->reviewed transition proceeds "
    "without any reviewed_at or owner-approval check."
)


def apply_check(old_status, new_status, new_fm, new_body):  # noqa: ARG001
    """Mutated _check_required_fields (Session 76 audit-v3 4-arg signature) with NO reviewed_at requirement."""
    # MUTATION: reviewed has no required fields at all
    if new_status == "done":
        if not new_fm.get("completed_at"):
            return (
                "PLAN-LIFECYCLE: transition to 'done' requires "
                "`completed_at: <YYYY-MM-DD>` in frontmatter."
            )
        rc = new_fm.get("related_commits")
        if not rc or (isinstance(rc, list) and len(rc) == 0):
            return (
                "PLAN-LIFECYCLE: transition to 'done' requires non-empty "
                "`related_commits: [sha1, sha2, ...]` in frontmatter."
            )
    elif new_status == "abandoned":
        if "## Abandonment reason" not in new_body:
            return (
                "PLAN-LIFECYCLE: transition to 'abandoned' requires an "
                "`## Abandonment reason` section in the plan body."
            )
    return None
