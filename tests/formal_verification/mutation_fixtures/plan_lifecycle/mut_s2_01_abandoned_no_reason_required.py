"""Mutation S2-01: abandon without requiring abandonment_reason.

The lifecycle requires body to contain ``## Abandonment reason`` section.
This mutation removes the check, allowing undocumented abandonment.
"""

from __future__ import annotations

PROPERTY = "S2"
DESCRIPTION = (
    "abandonment_reason check removed: transition to 'abandoned' succeeds "
    "without the ## Abandonment reason section."
)


def apply_check(old_status, new_status, new_fm, new_body):  # noqa: ARG001
    """Mutated _check_required_fields (Session 76 audit-v3 4-arg signature) that skips abandonment check."""
    if new_status == "reviewed":
        if not new_fm.get("reviewed_at"):
            return (
                "PLAN-LIFECYCLE: transition to 'reviewed' requires "
                "`reviewed_at: <YYYY-MM-DD>` in frontmatter."
            )
    elif new_status == "done":
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
    # MUTATION: no check for abandoned + abandonment_reason
    return None
