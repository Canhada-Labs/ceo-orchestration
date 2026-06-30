"""PLAN-088 W4.1 — Pair-Rail substantive _decide() extraction.

stdlib-only. Imported by check_pair_rail.py to keep the hook thin.

Scope per PLAN-088 W4.1 + M-6 amendment:
  - Phase A SHADOW (logged-only)
  - Phase B DRY_RUN (advisory-only)
  - Phase C ACTIVE: [DEFERRED-TO-PLAN-090] — REJECTED at this module.

ADR-107/108 cases A-F semantics:
  A: claude=PASS + codex=PASS                       -> dispatch (allow)
  B: claude=PASS + codex=BLOCK + preconditions MET  -> block
  B': claude=PASS + codex=BLOCK + preconditions NOT -> advisory (fail-OPEN)
  C: claude=BLOCK + codex=PASS  (not reachable PreToolUse)
  D: claude=BLOCK + codex=BLOCK (not reachable PreToolUse)
  E: divergent (Jaccard <=0.3)                      -> advisory + flag
  F: timeout / outage / malformed                   -> fail-OPEN

ADR-114 egress symmetry: this module DOES NOT introduce any outbound
Codex call. All outbound calls remain inside the existing
_lib/adapters/codex.py envelope (redact_outgoing already covers).
Phase C production dispatch path [DEFERRED-TO-PLAN-090].

Fail-open invariant: every public function returns a safe-default dict
on internal error. The caller MUST NEVER raise into hook stdout.

Persistence invariant: this module is STATELESS at module level. The
Phase-A advance gate (phase_a_can_advance) is a pure predicate; no
sidecar counter file is introduced (would be a new tamper surface).
The audit log's HMAC-chained event stream is the authoritative
samples_observed source consumed by closeout/CI tooling, NOT by this
hot-path module.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, Optional

_PHASE_SHADOW = "SHADOW"
_PHASE_DRY_RUN = "DRY_RUN"
_PHASE_DISABLED = "DISABLED"
# NOTE: "ACTIVE" is INTENTIONALLY ABSENT — Phase C is PLAN-090 scope.

_VALID_PHASES = frozenset({_PHASE_SHADOW, _PHASE_DRY_RUN, _PHASE_DISABLED})


def is_active_phase(phase: str) -> bool:
    """True iff phase is a known non-DISABLED Phase-{A,B} value.

    ACTIVE returns False unconditionally per M-6 (Phase C deferred to
    PLAN-090). Caller must treat ACTIVE as DISABLED.
    """
    if not isinstance(phase, str):
        return False
    if phase == "ACTIVE":
        return False
    return phase in (_PHASE_SHADOW, _PHASE_DRY_RUN)


def resolve_phase(env_value: Optional[str]) -> str:
    """Resolve CEO_PAIR_RAIL_PHASE env-var to a canonical phase.

    Unknown / empty / ACTIVE -> DISABLED (fail-CLOSED).
    """
    if not env_value:
        return _PHASE_DISABLED
    v = env_value.strip().upper()
    if v == "ACTIVE":
        return _PHASE_DISABLED  # M-6 fail-CLOSED
    if v in _VALID_PHASES:
        return v
    return _PHASE_DISABLED


class PairRailCase(str, Enum):
    A = "A"
    B = "B"
    B_PRIME = "B'"
    C = "C"
    D = "D"
    E = "E"
    F = "F"


def detect_case(
    *,
    claude_verdict: str,
    codex_verdict: str,
    jaccard_bucket: str = "",
) -> Optional[PairRailCase]:
    """Pure case-detection predicate per ADR-107/108 matrix.

    Returns None when verdicts are inconsistent with the matrix.
    The B vs B' discrimination is NOT made here — caller passes
    precondition_met to evaluate().
    """
    cv = claude_verdict
    xv = codex_verdict
    if xv in ("TIMEOUT", "MALFORMED"):
        return PairRailCase.F
    if cv == "PASS" and xv == "PASS":
        if jaccard_bucket == "<=0.3":
            return PairRailCase.E
        return PairRailCase.A
    if cv == "PASS" and xv == "BLOCK":
        return PairRailCase.B
    if cv == "BLOCK" and xv == "PASS":
        return PairRailCase.C
    if cv == "BLOCK" and xv == "BLOCK":
        return PairRailCase.D
    return None


# Trust-boundary guards (M-10 / Sec MF-3 log-injection defense).
_SAFE_SLUG_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")


def sanitize_signal_source(raw: Optional[str]) -> str:
    """Coerce signal_source to a known-good slug.

    M-10: persona is implicit in this field. Spoofing-via-env-var is
    AUDITED, not blocked. But the field must never carry arbitrary
    user input into the audit log (log-injection / DoS / PII).

    Allowed slugs: env-var, cli-flag, heuristic, default.
    Unknown / malformed -> "unknown" (audit-trail preserved, no leak).
    """
    if not isinstance(raw, str):
        return "unknown"
    v = raw.strip().lower()
    if v in ("env-var", "cli-flag", "heuristic", "default"):
        return v
    return "unknown"


def detect_signal_source(env: Dict[str, str]) -> str:
    """Return the canonical signal_source slug for current invocation.

    Priority order (highest to lowest):
      1. CEO_PERSONA env-var present  -> "env-var"
      2. CEO_PERSONA_CLI_FLAG present -> "cli-flag"
      3. CEO_PERSONA_HEURISTIC set    -> "heuristic"
      4. default
    """
    if env.get("CEO_PERSONA"):
        return "env-var"
    if env.get("CEO_PERSONA_CLI_FLAG"):
        return "cli-flag"
    if env.get("CEO_PERSONA_HEURISTIC"):
        return "heuristic"
    return "default"


def evaluate(
    *,
    claude_verdict: str,
    codex_verdict: str,
    phase: str,
    jaccard_bucket: str = "",
    precondition_met: bool = False,
    rubric_violation_id: str = "",
    severity: str = "",
) -> Dict[str, Any]:
    """Pure evaluation. Fail-open by contract.

    Returns:
        {
          "case":             "A".."F" or "B'" or None,
          "precondition_met": bool,
          "advise_dispatch":  bool,    # True ONLY in DRY_RUN + Case detected
          "rationale":        str,     # bounded slug
        }
    """
    try:
        if phase == _PHASE_DISABLED or not is_active_phase(phase):
            return {
                "case": None,
                "precondition_met": False,
                "advise_dispatch": False,
                "rationale": "phase_disabled",
            }
        case = detect_case(
            claude_verdict=claude_verdict,
            codex_verdict=codex_verdict,
            jaccard_bucket=jaccard_bucket,
        )
        if case is None:
            return {
                "case": None,
                "precondition_met": False,
                "advise_dispatch": False,
                "rationale": "no_matrix_case",
            }
        actual_case = case
        if case == PairRailCase.B and not precondition_met:
            actual_case = PairRailCase.B_PRIME
        # advise_dispatch only DRY_RUN; SHADOW is logged-only; Phase C
        # production dispatch [DEFERRED-TO-PLAN-090].
        advise = (phase == _PHASE_DRY_RUN)
        return {
            "case": actual_case.value,
            "precondition_met": bool(precondition_met),
            "advise_dispatch": bool(advise),
            "rationale": "ok",
        }
    except Exception:
        return {
            "case": None,
            "precondition_met": False,
            "advise_dispatch": False,
            "rationale": "evaluator_error",
        }


_PHASE_A_MIN_ELAPSED_S = 7 * 86400
_PHASE_A_MIN_SAMPLES = 100


def phase_a_can_advance(
    *,
    time_elapsed_seconds: int,
    samples_observed: int,
    no_regression: bool,
) -> bool:
    """Phase-A -> Phase-B advance gate per M-14 / Sec-5.

    Requires ALL THREE:
      - time_elapsed >= 7 days
      - samples_observed >= 100
      - no SHADOW correctness regression
    Prevents low-traffic window-escape (calendar days but no events).
    """
    try:
        t = int(time_elapsed_seconds)
        n = int(samples_observed)
    except (TypeError, ValueError):
        return False
    if t < _PHASE_A_MIN_ELAPSED_S:
        return False
    if n < _PHASE_A_MIN_SAMPLES:
        return False
    return bool(no_regression)
