"""WS-3 — the Cross-LLM Codex phase-gate DRIVER (mechanism only, mocked Codex).

PLAN-122 ships a *phase-by-phase* cross-LLM review loop: Claude codes a phase,
Codex reviews that phase's diff, and the result gates whether the orchestration
advances. This module is the **driver** for one such review. It is mechanism
ONLY — it never calls a real Codex (the ``codex_invoke`` callable is INJECTED so
tests stay offline) and it claims NO speed/cost/quality number (those are proven
later by WS-0b).

Trust-boundary contract (the load-bearing rule):

* Codex is a LOWER-trust channel. NOTHING from the Codex side is laundered
  verbatim into the higher-trust audit channel — not a thread id, not a prompt,
  not a summary, not a secret (S190 prompt-leak P0). Everything that leaves this
  driver in :class:`PhaseReview` is an enum, a bounded int, a stable hash, or a
  fixed model slug. The raw Codex text never escapes ``review_phase``.
* Fail-OPEN: any parse error, any ``codex_invoke`` exception, any malformed
  result → ``review_status="deferred"``. The driver NEVER raises on the happy
  path or any path; a review failure must not block the orchestration.

Kill-switch (SAFETY partition — PLAN-122 §6 P0-07): ``CEO_CODEX_REVIEW=0``
(``os.environ`` ONLY, never a settings file) short-circuits to ``deferred`` and
sets the ``review_disabled_signal`` boolean. We do NOT emit the (already
registered) ``codex_review_disabled`` audit action from here — the canonical
emit is a later GPG task; this driver only EXPOSES the signal so the caller can
emit it through the proper chokepoint.

Pure stdlib, Python >= 3.9, ``from __future__ import annotations``.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Mapping, NamedTuple, Optional

from ._codex_redaction import redact_thread_id, summary_hash
from ._skeleton import kill_switch_off

# --- Review-status enum -----------------------------------------------------
REVIEW_PASSED: str = "passed"      # Codex found no blocking violation
REVIEW_FAILED: str = "failed"      # Codex flagged >=1 blocking violation
REVIEW_DEFERRED: str = "deferred"  # kill-switch OFF, error, or malformed result

_VALID_STATUSES = frozenset({REVIEW_PASSED, REVIEW_FAILED, REVIEW_DEFERRED})

# Default model slug for the Codex reviewer. A string label only — this driver
# never selects or invokes a model; the slug is forwarded for telemetry parity.
DEFAULT_CODEX_MODEL: str = "gpt-5-codex"

# SAFETY kill-switch (os.environ ONLY). Default posture: review ENABLED.
_CODEX_REVIEW_SWITCH: str = "CEO_CODEX_REVIEW"

# Bounded cap on the violations count we will report — keeps the int sane even
# if a malformed result claims a billion violations (no side-channel via size).
_MAX_VIOLATIONS: int = 9999

# Tokens (lowercased, exact-match against an enum field) that mean each verdict.
# Exact set membership — NO regex over the Codex text for the verdict, so there
# is no ReDoS surface on the hot path. (The only regex in this package is the
# bounded thread-id extractor in ``_codex_redaction``.)
_PASSED_TOKENS = frozenset({"passed", "pass", "accept", "accepted", "approve",
                            "approved", "ok", "clean", "green"})
_FAILED_TOKENS = frozenset({"failed", "fail", "block", "blocked", "reject",
                            "rejected", "changes_requested", "red"})
_DEFERRED_TOKENS = frozenset({"deferred", "defer", "error", "unknown", "timeout",
                              "skipped", "skip"})


class PhaseReview(NamedTuple):
    """Immutable, audit-safe result of one Codex phase review.

    Every field is an enum / bounded int / stable hash / fixed slug — NOTHING
    here carries raw Codex text, so the whole tuple is safe to fold into the
    higher-trust audit channel. ``review_disabled_signal`` is the kill-switch
    tell the caller uses to emit ``codex_review_disabled`` (we never emit it).
    """

    phase_number: int
    review_status: str               # one of REVIEW_*
    thread_id_redacted: str          # stable short hash, never the raw id
    violations_found_count: int      # 0.._MAX_VIOLATIONS
    summary_hash: str                # stable hex hash, never the raw summary
    codex_model: str                 # forwarded slug, e.g. "gpt-5-codex"
    duration_ms: int                 # wall-clock of the invoke, >= 0
    review_disabled_signal: bool     # True iff CEO_CODEX_REVIEW is OFF


def _noop_codex_invoke(payload: str, model: str) -> Mapping[str, Any]:
    """Default injected Codex stub: invokes nothing, yields a deferred verdict.

    Keeps :func:`review_phase` offline-by-default — a caller that forgets to
    inject a real driver gets a safe ``deferred``, never a network call.
    """
    return {"status": REVIEW_DEFERRED, "reason": "no_codex_invoke_injected"}


def _coerce_int(value: Any, lo: int, hi: int) -> int:
    """Best-effort int in ``[lo, hi]``; ``lo`` on any non-int/oversize. No raise.

    Rejects bool explicitly (``bool`` is an ``int`` subclass) so a stray
    ``True`` cannot masquerade as a count of 1.
    """
    try:
        if isinstance(value, bool):
            return lo
        ivalue = int(value)
    except (ValueError, TypeError):
        return lo
    if lo > hi:
        lo, hi = hi, lo
    return max(lo, min(hi, ivalue))


def _classify_status(raw_status: Any) -> str:
    """Map a raw status token to one of REVIEW_*. Unknown/odd → deferred.

    Exact set membership on a lowercased, stripped, length-bounded token — no
    regex, no substring scan, so there is no ReDoS surface here.
    """
    try:
        if not isinstance(raw_status, str):
            return REVIEW_DEFERRED
        token = raw_status.strip().lower()[:32]
        if token in _PASSED_TOKENS:
            return REVIEW_PASSED
        if token in _FAILED_TOKENS:
            return REVIEW_FAILED
        # _DEFERRED_TOKENS and everything else fall through to deferred — the
        # conservative default (we never advance the orchestration on an
        # unrecognised verdict).
        return REVIEW_DEFERRED
    except Exception:
        return REVIEW_DEFERRED


def _extract_fields(result: Any) -> "tuple[str, int, str, str]":
    """Defensively pull (status, violations, thread_raw, summary_raw) from a
    Codex result. Accepts a Mapping (preferred) or a bare string; anything else
    or any access error → a deferred-shaped tuple. Never raises.

    The raw thread/summary are returned ONLY to be hashed by the caller — they
    are never placed on the returned :class:`PhaseReview`.
    """
    try:
        if isinstance(result, Mapping):
            raw_status = result.get("status", result.get("verdict", ""))
            violations = _coerce_int(
                result.get("violations_found_count",
                           result.get("violations", 0)),
                0, _MAX_VIOLATIONS,
            )
            thread_raw = result.get("thread_id", result.get("thread", ""))
            summary_raw = result.get("summary", result.get("review", ""))
            status = _classify_status(raw_status)
            # If the result asserts a failed verdict but reports zero
            # violations, normalise to >=1 so a downstream gate sees a non-zero
            # count for a fail (defensive; never the other way around).
            if status == REVIEW_FAILED and violations == 0:
                violations = 1
            # If the result asserts passed, force the violation count to 0 —
            # a "passed with N violations" is internally inconsistent; trust
            # the verdict, zero the count.
            if status == REVIEW_PASSED:
                violations = 0
            return (
                status,
                violations,
                thread_raw if isinstance(thread_raw, str) else "",
                summary_raw if isinstance(summary_raw, str) else "",
            )
        if isinstance(result, str):
            # A bare string result: treat the whole string as the status token
            # AND as the summary to hash. No violation count available.
            status = _classify_status(result)
            return (status, 1 if status == REVIEW_FAILED else 0, "", result)
        # None / int / list / unexpected shape → deferred, nothing to hash.
        return (REVIEW_DEFERRED, 0, "", "")
    except Exception:
        return (REVIEW_DEFERRED, 0, "", "")


def review_phase(
    phase_number: int,
    diff_or_summary: str,
    codex_invoke: Optional[Callable[[str, str], Any]] = None,
    codex_model: str = DEFAULT_CODEX_MODEL,
) -> PhaseReview:
    """Run one Codex phase review and return an audit-safe :class:`PhaseReview`.

    ``codex_invoke`` is an INJECTED ``(payload, model) -> result`` callable
    (default :func:`_noop_codex_invoke`, which invokes nothing) so this driver
    never touches a real Codex in tests. ``diff_or_summary`` is the phase diff
    or summary to review; it is passed to ``codex_invoke`` and otherwise only
    HASHED — never echoed back out.

    Behaviour:

    * ``CEO_CODEX_REVIEW=0`` (os.environ) → short-circuit to ``deferred`` with
      ``review_disabled_signal=True`` WITHOUT calling ``codex_invoke``. (We do
      not emit the ``codex_review_disabled`` audit action — the caller does.)
    * Otherwise call ``codex_invoke`` and parse defensively. Any exception, any
      malformed/odd result → ``deferred`` (fail-open). NEVER raises.

    Every field of the result is an enum / bounded int / stable hash / fixed
    slug; the raw Codex thread id and summary are hashed via
    :mod:`optimizer._codex_redaction` and never leave this function.
    """
    phase = _coerce_int(phase_number, 0, 1_000_000)
    model_slug = codex_model if isinstance(codex_model, str) and codex_model else DEFAULT_CODEX_MODEL

    # SAFETY kill-switch — checked FIRST, before any invoke. Default posture:
    # review ENABLED (switch absent → not OFF). os.environ ONLY.
    if kill_switch_off(_CODEX_REVIEW_SWITCH):
        return PhaseReview(
            phase_number=phase,
            review_status=REVIEW_DEFERRED,
            thread_id_redacted="none",
            violations_found_count=0,
            summary_hash="none",
            codex_model=model_slug,
            duration_ms=0,
            review_disabled_signal=True,
        )

    invoke = codex_invoke if callable(codex_invoke) else _noop_codex_invoke
    payload = diff_or_summary if isinstance(diff_or_summary, str) else ""

    start = time.monotonic()
    try:
        result = invoke(payload, model_slug)
    except Exception:
        # The injected Codex call blew up — fail-open to deferred. The duration
        # still reflects the (failed) attempt so telemetry isn't a flat zero.
        result = None
    duration_ms = _duration_ms(start)

    status, violations, thread_raw, summary_raw = _extract_fields(result)

    return PhaseReview(
        phase_number=phase,
        review_status=status if status in _VALID_STATUSES else REVIEW_DEFERRED,
        thread_id_redacted=redact_thread_id(thread_raw),
        violations_found_count=violations,
        summary_hash=summary_hash(summary_raw),
        codex_model=model_slug,
        duration_ms=duration_ms,
        review_disabled_signal=False,
    )


def _duration_ms(start: float) -> int:
    """Non-negative elapsed milliseconds since ``start`` (monotonic). No raise."""
    try:
        elapsed = (time.monotonic() - start) * 1000.0
        return max(0, int(elapsed))
    except Exception:
        return 0
