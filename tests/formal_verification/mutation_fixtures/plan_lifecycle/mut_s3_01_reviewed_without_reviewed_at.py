"""Mutation S3-01: transition to reviewed without reviewed_at field.

The lifecycle requires reviewed_at to be present when transitioning to
reviewed. This mutation skips that check.
"""

from __future__ import annotations

PROPERTY = "S3"
DESCRIPTION = (
    "reviewed_at check removed: transition to 'reviewed' succeeds "
    "without the reviewed_at field in frontmatter."
)


def apply_check(old_status, new_status, new_fm, new_body):  # noqa: ARG001
    """Mutated _check_required_fields (Session 76 audit-v3 4-arg signature) that skips reviewed_at check."""
    # MUTATION: no check for reviewed + reviewed_at
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
