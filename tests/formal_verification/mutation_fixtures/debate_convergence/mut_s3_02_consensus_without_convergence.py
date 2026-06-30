"""Mutation S3-02: consensus reached without Jaccard convergence.

Consensus can be emitted even when Jaccard score is below threshold,
making the convergence check decorative.
"""

from __future__ import annotations

PROPERTY = "S3"
DESCRIPTION = (
    "consensus emitted without convergence: Jaccard threshold check "
    "bypassed, consensus_reached set to True on any score."
)

BYPASS_JACCARD = True
