"""Sub-agent N-of-M dispatch aggregator with partial-drop emit surface.

PLAN-106 Wave G.1 (absorption of PLAN-093-FOLLOWUP §G.1 plus security folds).
Closes the dead-callsite finding on `emit_subagent_findings_partial_drop`
(registered S114 PLAN-088 W1.4 SEMI-13 — see `_lib/audit_emit.py:5623`).

## Contract

Bounded N-of-M dispatch with a timeout `T=30s` (configurable via the
dispatcher). On partial return (k < expected_N), emit
`subagent_findings_partial_drop` with the drop_reason classification.

Drop-reason taxonomy (closed enum at the audit-emit allowlist edge):
- `"timeout"` — agent did not return within `T` seconds.
- `"agent_error"` — agent returned an exception object.
- `"retry_exhaust"` — coordinator retried up to budget and gave up.
- `"unknown"` — fallback for unclassified drops (defensive default).

## Usage

    from _lib.subagent_dispatch import aggregate_findings, DropReason

    results = aggregate_findings(
        expected_n=4,
        completed_findings=[finding_a, finding_b],  # k=2 of N=4
        dropped_count=2,
        drop_reason=DropReason.TIMEOUT,
        archetype="security-engineer",
    )
    # → emits 1 `subagent_findings_partial_drop` event;
    #   returns dict with {"findings": [...], "partial_drop": True, ...}

## Fail-open

Any audit-emit exception is swallowed and a stderr breadcrumb is written.
The aggregator never raises on the emit path; it returns the
findings-list either way.

## Design notes

- Pure-Python stdlib only (ADR-002 / framework discipline).
- Python >= 3.9 compatible. `from __future__ import annotations`.
- Tested via `.claude/hooks/tests/test_subagent_dispatch.py` (7 cases).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Make the _lib package importable from this file's directory.
_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))


class DropReason:
    """Closed enum of drop_reason classifications.

    The wire-level audit emit accepts the bare string; this class
    provides constants so callers don't typo a literal.
    """

    TIMEOUT = "timeout"
    AGENT_ERROR = "agent_error"
    RETRY_EXHAUST = "retry_exhaust"
    UNKNOWN = "unknown"

    _ALL = frozenset({TIMEOUT, AGENT_ERROR, RETRY_EXHAUST, UNKNOWN})

    @classmethod
    def is_valid(cls, reason: str) -> bool:
        return reason in cls._ALL


def _safe_emit_partial_drop(
    *,
    findings_total: int,
    findings_dropped: int,
    drop_reason: str,
    archetype: str,
    session_id: str,
    project: str,
) -> bool:
    """Best-effort audit emit. Returns True on success, False on failure.

    Never raises. Wraps the import + call in try/except so that an
    audit-emit module failure (e.g. missing on disk during a test, broken
    install) never breaks the dispatch.
    """
    try:
        # PLAN-094 Wave E lazy-import dispatch shim closes AC9c hook regression.
        # Prefer the dispatch shim if available (mirrors check_agent_spawn.py
        # pattern); fall back to direct audit_emit module otherwise.
        try:
            from _lib import audit_emit_dispatch as _audit  # type: ignore
            emit_fn = getattr(_audit, "emit_subagent_findings_partial_drop", None)
            if emit_fn is None:
                # Shim doesn't expose this symbol — fall through to direct.
                raise ImportError("dispatch shim lacks emit_subagent_findings_partial_drop")
        except Exception:
            from _lib import audit_emit as _audit  # type: ignore
            emit_fn = getattr(_audit, "emit_subagent_findings_partial_drop", None)
            if emit_fn is None:
                return False

        emit_fn(
            session_id=session_id,
            findings_total=int(findings_total),
            findings_dropped=int(findings_dropped),
            drop_reason=str(drop_reason)[:256],
            archetype=str(archetype)[:64],
            project=project,
        )
        return True
    except Exception as e:  # pragma: no cover — defensive
        sys.stderr.write(
            f"[subagent_dispatch] WARN: partial-drop emit failed: "
            f"{type(e).__name__}: {e}\n"
        )
        return False


def aggregate_findings(
    *,
    expected_n: int,
    completed_findings: List[Any],
    dropped_count: int = 0,
    drop_reason: str = DropReason.UNKNOWN,
    archetype: str = "",
    session_id: str = "",
    project: str = "",
    emit_threshold_full: bool = False,
) -> Dict[str, Any]:
    """Aggregate N-of-M dispatch results and emit partial-drop on shortfall.

    Args:
        expected_n: The N in "N-of-M" — total dispatched count expected.
        completed_findings: List of findings actually returned (k items).
        dropped_count: Number known dropped by the coordinator. If 0 and
            len(completed_findings) < expected_n, dropped_count is computed
            from the delta.
        drop_reason: One of DropReason constants. Defaults to UNKNOWN.
        archetype: Sub-agent archetype (e.g. "security-engineer").
        session_id: Claude Code session id (best-effort; "" when unknown).
        project: Project directory (audit-emit base field).
        emit_threshold_full: If True, also emit on k==N (testing only —
            production callers leave False to honor "partial-drop" semantics).

    Returns:
        Dict with keys:
            findings: the list passed in (pass-through, unchanged).
            partial_drop: bool — True iff k < expected_n.
            expected_n, completed_n, dropped_n: integers.
            drop_reason: the classification used for emit (or "" if no emit).
            emit_attempted: bool — True if we tried to emit (regardless of
                whether the emit succeeded; audit-emit is fail-open).

    Never raises on the emit path. Argument validation defends against
    negative counts and non-string archetype.
    """
    # Defensive coercions
    try:
        expected_n_i = int(expected_n)
    except Exception:
        expected_n_i = 0
    if expected_n_i < 0:
        expected_n_i = 0

    completed_list = list(completed_findings or [])
    completed_n = len(completed_list)

    # Resolve dropped_n:
    # - if caller passed a positive dropped_count, trust it (caller knows
    #   more than the bare list, e.g. coordinator may track retry-exhaust
    #   distinct from raw completion).
    # - else infer from the delta.
    try:
        dropped_n = int(dropped_count)
    except Exception:
        dropped_n = 0
    if dropped_n <= 0:
        dropped_n = max(0, expected_n_i - completed_n)

    # Classify
    reason = str(drop_reason or DropReason.UNKNOWN)
    if not DropReason.is_valid(reason):
        # Reject unknown reasons to keep the audit field a closed enum at
        # the source. Caller passing an unexpected string lands as
        # `unknown` for forensic clarity.
        reason = DropReason.UNKNOWN
    archetype_s = str(archetype or "")[:64]

    partial = completed_n < expected_n_i
    emit_attempted = False

    if partial or emit_threshold_full:
        emit_attempted = _safe_emit_partial_drop(
            findings_total=completed_n,
            findings_dropped=dropped_n,
            drop_reason=reason,
            archetype=archetype_s,
            session_id=str(session_id or ""),
            project=str(project or ""),
        )

    return {
        "findings": completed_list,
        "partial_drop": partial,
        "expected_n": expected_n_i,
        "completed_n": completed_n,
        "dropped_n": dropped_n,
        "drop_reason": reason if (partial or emit_threshold_full) else "",
        "emit_attempted": emit_attempted,
        "archetype": archetype_s,
    }


def classify_drop_from_outcome(
    *,
    timed_out: bool = False,
    raised: bool = False,
    retries_exhausted: bool = False,
) -> str:
    """Translate boolean outcome flags into a DropReason string.

    Precedence (highest first):
        timed_out > raised > retries_exhausted > unknown
    """
    if timed_out:
        return DropReason.TIMEOUT
    if raised:
        return DropReason.AGENT_ERROR
    if retries_exhausted:
        return DropReason.RETRY_EXHAUST
    return DropReason.UNKNOWN


__all__ = [
    "DropReason",
    "aggregate_findings",
    "classify_drop_from_outcome",
]
