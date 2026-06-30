"""Mutation S4-02: redaction applied AFTER agent prompts are built.

The contract requires redaction BEFORE building next-round prompts.
This mutation applies redaction after the agents have already received
unredacted content.
"""

from __future__ import annotations

PROPERTY = "S4"
DESCRIPTION = (
    "redaction applied after prompt construction: agents in round N+1 "
    "receive unredacted content; redaction happens post-hoc."
)

REDACTION_LATE = True
