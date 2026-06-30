"""Mutation S4-01: redaction not applied between rounds.

The orchestrator must call redact_secrets() on consolidated critiques
before feeding them to the next round. This mutation skips redaction.
"""

from __future__ import annotations

PROPERTY = "S4"
DESCRIPTION = (
    "redaction skipped between rounds: consolidated critiques are "
    "passed to next round without redact_secrets() call."
)

SKIP_REDACTION = True
