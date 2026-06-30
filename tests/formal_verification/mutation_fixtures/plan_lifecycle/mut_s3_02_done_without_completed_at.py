"""Mutation S3-02: transition to done without completed_at field.

The lifecycle requires completed_at + related_commits when transitioning
to done. This mutation skips the completed_at check.
"""

from __future__ import annotations

PROPERTY = "S3"
DESCRIPTION = (
    "completed_at check removed: transition to 'done' succeeds "
    "without the completed_at field in frontmatter."
)


def apply_check(old_status, new_status, new_fm, new_body):  # noqa: ARG001
    """Mutated _check_required_fields (Session 76 audit-v3 4-arg signature) that skips completed_at check."""
    if new_status == "reviewed":
        if not new_fm.get("reviewed_at"):
            return (
                "PLAN-LIFECYCLE: transition to 'reviewed' requires "
                "`reviewed_at: <YYYY-MM-DD>` in frontmatter."
            )
    elif new_status == "done":
        # MUTATION: no check for completed_at
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
