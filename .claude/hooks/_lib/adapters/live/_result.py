"""Typed result envelope for live adapter calls — ADR-040 §7.

Every adapter ``call()`` returns a :class:`LiveAdapterResult`. Adapters
NEVER raise — exceptions inside the transport layer are caught and
mapped to ``failure_mode``. The contract is enforced by
``test_adapters.py::test_call_never_raises`` and
``tests/chaos/test_live_adapter_failure_injection.py``.

The dataclass is frozen (immutable). All fields are typed; ``None``
values are explicit (a missing token count is never silently 0).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Failure mode enum-ish (string literal — Python 3.9 compat, no Literal[] at
# runtime in dataclass annotation contexts).
# ---------------------------------------------------------------------------

# Authoritative list per SPEC/v1/live-adapters-policy.schema.md §3.
FAILURE_MODES = (
    "auth_permanent",
    "rate_limited",
    "server_error",
    "connect_timeout",
    "read_timeout",
    "connection_refused",
    "parse_error",
    "breaker_open",
    "budget_hard_stop",
    "scope_misconfigured",
    "invalid_policy",
    "fixture_fallback",  # used only on activation gate off (success-shaped)
    "missing_credential",
    "timeout",  # alias for connect/read_timeout in test assertions
)


# ---------------------------------------------------------------------------
# Breaker state literals (mirror _breaker.py BreakerState enum values)
# ---------------------------------------------------------------------------

BREAKER_STATES = ("closed", "open", "half_open")


# ---------------------------------------------------------------------------
# Stop-reason vocabulary — PLAN-135 W5 O7-(1).
#
# Anthropic Messages API stop_reason enum (2026 surface):
#   end_turn | max_tokens | stop_sequence | tool_use | pause_turn | refusal
# plus an optional stop_details {category, explanation} object.
#
# COMPLETION_STOP_REASONS is the subset that means "the model ran to a
# normal completion-shaped stop". Anything else (max_tokens truncation,
# pause_turn continuation, refusal) parses as transport SUCCESS but is
# NOT a completion — callers use is_complete()/is_refusal() to tell.
# Unknown/new provider values are conservatively treated as NOT complete.
# ---------------------------------------------------------------------------

COMPLETION_STOP_REASONS = ("end_turn", "stop_sequence", "tool_use")


@dataclass(frozen=True)
class LiveAdapterResult:
    """The single shape every live adapter returns.

    Contract (ADR-040 §7):

    - ``success=True`` MUST imply ``text`` is a (possibly empty) string,
      ``tokens_in`` / ``tokens_out`` are ints, ``failure_mode is None``.
    - ``success=False`` MUST imply ``failure_mode`` is one of the
      :data:`FAILURE_MODES` strings.
    - ``duration_ms`` is ALWAYS present (elapsed wall-clock from call
      entry to result construction). 0 is acceptable when fixture
      fallback short-circuits before any timing.
    - ``fixture_fallback=True`` is a SUCCESS path (``success=True``)
      indicating the activation gate was off; callers may pass the
      result through unchanged.
    - ``retry_count`` is 0 or 1 (ADR-040 §1 max_retries=1).

    Attributes:
        success: True iff the call returned a parseable provider response
            OR the activation gate short-circuited to fixture fallback.
        text: assistant message text on success; ``None`` on failure.
        tokens_in: prompt token count reported by provider; ``None`` on
            failure or when provider omits the field.
        tokens_out: completion token count; same null semantics.
        cost_usd: estimated USD spend (input_tokens × rate + output × rate).
            ``None`` on failure; ``0.0`` for ``provider="local"``.
        duration_ms: wall-clock milliseconds. Always present (>=0).
        failure_mode: one of :data:`FAILURE_MODES` on failure, ``None``
            on success. The enum is closed; new values require an ADR-040
            amendment + SPEC bump.
        http_status: HTTP status code if the transport layer received a
            response; ``None`` on transport-layer failure (timeout,
            refused, breaker-open) or activation-gate fallback.
        breaker_state: state of the per-provider breaker AT RESULT TIME.
            One of :data:`BREAKER_STATES`. Always present.
        provider: short slug ``"anthropic" | "google" | "openai" | "local"``.
            Always present (matches adapter ``provider_name``).
        retry_count: 0 if no retry occurred, 1 if exactly one retry was
            attempted. Per ADR-040 §1 max_retries=1.
        fixture_fallback: True iff activation-gate short-circuited; the
            adapter delegated to the fixture-adapter without network I/O.
        stop_reason: PLAN-135 W5 O7-(1) — the provider's stop_reason
            string, surfaced verbatim (e.g. ``end_turn``, ``max_tokens``,
            ``pause_turn``, ``refusal``). ``None`` on failure, on the
            fixture path, or when the provider omits it (pre-O7 results
            constructed without the field also default to ``None``).
            IMPORTANT: ``success=True`` means transport + parse success
            ONLY — completion semantics live here. Use
            :meth:`is_complete` / :meth:`is_refusal`.
        stop_details: optional provider ``stop_details`` object
            (``{"category": ..., "explanation": ...}``) accompanying
            non-trivial stop reasons. Surfaced verbatim for callers;
            NEVER forwarded to the audit log as free text (only the
            ``category`` field is audited, by the adapter).
    """

    success: bool
    text: Optional[str] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    cost_usd: Optional[float] = None
    duration_ms: int = 0
    failure_mode: Optional[str] = None
    http_status: Optional[int] = None
    breaker_state: str = "closed"
    provider: str = ""
    retry_count: int = 0
    fixture_fallback: bool = False

    # Optional debug correlation field — never carries credentials. Empty
    # by default; transport layer fills it on retries to disambiguate
    # audit entries. PLAN-135 W5 O7-(5): the transport now also captures
    # the provider request id on the HTTP-error path (``request-id`` /
    # ``x-request-id`` response header, else the ``request_id`` key of the
    # JSON error body) and the Claude adapter threads it into failed
    # results so paid-run forensics can quote the id to support.
    request_id: str = field(default="")

    # PLAN-135 W5 O7-(1) — completion semantics (additive, optional;
    # pre-O7 constructors omit them and get the None defaults).
    stop_reason: Optional[str] = None
    stop_details: Optional[Dict[str, Any]] = None

    def is_refusal(self) -> bool:
        """True iff the model refused (stop_reason == "refusal").

        PLAN-135 W5 O7-(1). A refusal is a transport-level SUCCESS (the
        spend was incurred, usage/cost fields are real) but NOT a
        completion — graders/instruments must not score the refusal text
        as an answer.
        """
        return self.stop_reason == "refusal"

    def is_complete(self) -> bool:
        """True iff the call succeeded AND ran to a completion-shaped stop.

        PLAN-135 W5 O7-(1) — refusal != completion (the pre-O7 latent
        bug: every 2xx parsed as a normal completion). Semantics:

        - ``success=False`` → False.
        - ``stop_reason is None`` → True (back-compat: fixture path,
          legacy constructors, providers that omit the field — preserves
          the pre-O7 meaning of ``success``).
        - else → ``stop_reason in COMPLETION_STOP_REASONS`` (max_tokens
          truncation, pause_turn, refusal, and unknown future values are
          all NOT complete).
        """
        if not self.success:
            return False
        if self.stop_reason is None:
            return True
        return self.stop_reason in COMPLETION_STOP_REASONS

    def is_retryable(self) -> bool:
        """True iff the failure mode is in the transient class.

        Used by the breaker to decide whether to count toward threshold.
        Permanent modes (``auth_permanent``, ``parse_error``,
        ``budget_hard_stop``, ``scope_misconfigured``,
        ``invalid_policy``, ``missing_credential``) return False.
        """
        if self.success or self.failure_mode is None:
            return False
        return self.failure_mode in (
            "rate_limited",
            "server_error",
            "connect_timeout",
            "read_timeout",
            "connection_refused",
            "timeout",
        )


__all__ = [
    "LiveAdapterResult",
    "FAILURE_MODES",
    "BREAKER_STATES",
    "COMPLETION_STOP_REASONS",
]
