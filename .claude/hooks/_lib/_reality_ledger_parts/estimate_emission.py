"""Reality ledger: estimate emission."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Tuple

from .constants import *  # shared declaration defaults

def _to_basis_points(value: float, *, lo: int = 0, hi: int = 1_000_000) -> int:
    """Convert a float multiplier to integer basis-points (×1000), clamped.

    Mirrors audit_emit._to_basis_points; duplicated here so reality-ledger
    can run with a not-yet-Wave-2-extended audit_emit at HEAD (the typed
    helpers in audit_emit are guarded by hasattr — fail-open if absent).
    """
    try:
        f = float(value)
    except (TypeError, ValueError):
        return lo
    if f != f or f in (float("inf"), float("-inf")):
        return lo
    bp = int(round(f * 1000.0))
    if bp < lo:
        return lo
    if bp > hi:
        return hi
    return bp


def _emit_estimate_drift_detected_typed(
    *,
    audit_emit_module: Optional[Any],
    session_id: str,
    project: str,
    plan_id: str,
    drift_factor_compute: float,
    drift_factor_owner: float,
    severity: str,
    plan_count_in_run: int,
    systematic_bias_direction: str,
) -> bool:
    """Best-effort emit of estimate_drift_detected via typed wrapper.

    Codex W1+W2 fix-pack #1: detector #7 emits via the dedicated typed
    wrapper, NOT via the generic ``reality_ledger_finding`` dispatch.
    Fail-open per Sec NTH #5: any exception is swallowed.
    """
    try:
        if audit_emit_module is None:
            try:
                from _lib import audit_emit as audit_emit_module  # type: ignore
            except Exception:
                return False
        emit_fn = getattr(audit_emit_module, "emit_estimate_drift_detected", None)
        if emit_fn is None:
            return False
        emit_fn(
            session_id=session_id,
            plan_id=plan_id,
            drift_factor_compute_basis_points=_to_basis_points(
                drift_factor_compute
            ),
            drift_factor_owner_basis_points=_to_basis_points(
                drift_factor_owner
            ),
            severity=severity,
            plan_count_in_run=plan_count_in_run,
            systematic_bias_direction=systematic_bias_direction,
            project=project,
        )
        return True
    except Exception:  # pragma: no cover - fail-open invariant
        return False


def _emit_estimate_drift_systematic_bias_typed(
    *,
    audit_emit_module: Optional[Any],
    session_id: str,
    project: str,
    bias_direction: str,
    plans_affected_count: int,
    avg_drift_factor_compute: float,
    avg_drift_factor_owner: float,
) -> bool:
    """Best-effort emit of estimate_drift_systematic_bias via typed wrapper."""
    try:
        if audit_emit_module is None:
            try:
                from _lib import audit_emit as audit_emit_module  # type: ignore
            except Exception:
                return False
        emit_fn = getattr(
            audit_emit_module, "emit_estimate_drift_systematic_bias", None
        )
        if emit_fn is None:
            return False
        emit_fn(
            session_id=session_id,
            bias_direction=bias_direction,
            plans_affected_count=plans_affected_count,
            avg_drift_factor_compute_basis_points=_to_basis_points(
                avg_drift_factor_compute
            ),
            avg_drift_factor_owner_basis_points=_to_basis_points(
                avg_drift_factor_owner
            ),
            project=project,
        )
        return True
    except Exception:  # pragma: no cover - fail-open invariant
        return False


# ---------------------------------------------------------------------------
# Finding shape + redaction + rendering
# ---------------------------------------------------------------------------


__all__ = ['_to_basis_points', '_emit_estimate_drift_detected_typed', '_emit_estimate_drift_systematic_bias_typed']
