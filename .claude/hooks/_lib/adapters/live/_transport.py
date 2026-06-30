"""urllib-based HTTP transport with timeout / retry / audit — ADR-040 §1, §2.

This module is the sole network egress point for the live adapters.
Every provider adapter routes through :class:`LiveTransport` so that:

- timeouts are uniform (connect + read from policy)
- retries are bounded (max 1 with full-jitter backoff per ADR-040 §1)
- credentials are NEVER logged (Authorization / x-api-key / URL query
  string scrubbed before audit emission)
- audit events fire on entry + exit (no silent network)

Stdlib only: ``urllib.request`` + ``ssl`` + ``socket`` + ``json``.

Failure-mode mapping (ADR-040 §2):

============  ============================  ============
HTTP / cause  failure_mode                  Retry?
============  ============================  ============
401, 403      auth_permanent                No
429           rate_limited                  1×
5xx           server_error                  1×
ConnRefused   connection_refused            1×
ConnTimeout   connect_timeout               1×
ReadTimeout   read_timeout                  1×
JSON error    parse_error                   No
============  ============================  ============
"""

from __future__ import annotations

import json
import random
import socket
import ssl
import time as _time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

from ._policy import LiveCallPolicy


# Reasonable upper bound on response body — protects against a misbehaving
# provider streaming GBs. Live chat completions sit comfortably below this.
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # 2 MiB

# Header names that MUST NEVER hit logs / audit.
_REDACTED_HEADER_NAMES = frozenset(
    {
        "authorization",
        "x-api-key",
        "x-goog-api-key",
        "anthropic-api-key",
        "openai-api-key",
        "api-key",
        "cookie",
    }
)


@dataclass
class TransportResponse:
    """Successful network exchange (2xx)."""

    status: int
    body_bytes: bytes
    duration_ms: int
    retried: bool

    def text(self) -> str:
        return self.body_bytes.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return json.loads(self.text())


@dataclass
class TransportFailure:
    """Failure terminal (post-retry)."""

    failure_mode: str
    http_status: Optional[int]
    duration_ms: int
    retried: bool
    detail: str  # short — never includes the body when 4xx auth
    # PLAN-135 W5 O7-(5) — provider request id captured on the HTTP-error
    # path: `request-id` / `x-request-id` response header, else the
    # `request_id` key of the JSON error body. Empty when unavailable
    # (network-level failures never reach the provider). Never a
    # credential; safe to log / quote to provider support.
    request_id: str = ""


def _scrub_url_query(url: str) -> str:
    """Return URL without query-string values (preserves path).

    Google's Generative Language API embeds the API key in the query;
    audit must never carry it. We keep the path so dashboards can group
    by endpoint family.
    """
    try:
        parts = urllib.parse.urlsplit(url)
        if parts.query:
            return urllib.parse.urlunsplit(
                (parts.scheme, parts.netloc, parts.path, "", "")
            )
        return url
    except Exception:  # pragma: no cover - urllib never raises here in practice
        return "<scrubbed>"


def _scrub_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Return a header dict safe to log."""
    safe: Dict[str, str] = {}
    for k, v in headers.items():
        if k.lower() in _REDACTED_HEADER_NAMES:
            safe[k] = "[REDACTED]"
        else:
            safe[k] = v
    return safe


def _extract_request_id(error: Any, detail: str) -> str:
    """PLAN-135 W5 O7-(5) — best-effort provider request-id extraction.

    Order: ``request-id`` header → ``x-request-id`` header → top-level
    ``request_id`` key of the JSON error body (``detail`` is the already
    truncated/decoded body text). Fail-soft: any shape mishap returns
    ``""``. The id is an opaque correlation token (never a credential).
    Truncated to 128 chars defensively.
    """
    req_id = ""
    try:
        headers = getattr(error, "headers", None)
        if headers is not None:
            req_id = (
                headers.get("request-id")
                or headers.get("x-request-id")
                or ""
            )
    except Exception:
        req_id = ""
    if not req_id and detail:
        try:
            payload = json.loads(detail)
            candidate = payload.get("request_id") if isinstance(payload, dict) else None
            if isinstance(candidate, str):
                req_id = candidate
        except (ValueError, TypeError):
            pass
    return str(req_id)[:128]


def audit_emit_dispatch(action: str, fields: Dict[str, Any]) -> None:
    """Default production ``on_audit`` wiring for :class:`LiveTransport`.

    Routes the transport's three audit callbacks (``live_adapter_call_started``
    / ``_succeeded`` / ``_failed`` — ADR-040 §7) to the framework's
    :mod:`_lib.audit_emit` typed emitters. The four production adapters
    (claude / gemini / openai / local) pass this as ``on_audit=`` so live-adapter
    call telemetry actually reaches the audit log. Before PLAN-120 S185 every
    adapter omitted ``on_audit=`` and the events were silently swallowed by the
    no-op ``__init__`` default (PLAN-120 finding E2-F2).

    ``audit_emit`` is imported lazily so the transport stays usable standalone
    (the ``__init__`` default remains a no-op for that decoupling), and the whole
    dispatch is fail-open — telemetry must NEVER break the live-call path. Only
    the whitelisted fields each typed emitter accepts are forwarded (the transport
    also passes ``headers`` / ``attempt`` extras that the emitters legitimately
    drop). ``url`` is already query-scrubbed and ``headers`` redacted by the
    transport before this callback fires (credentials never reach the log).
    """
    try:
        from _lib import audit_emit

        if action == "live_adapter_call_started":
            audit_emit.emit_live_adapter_call_started(
                provider=str(fields.get("provider", "")),
                url=str(fields.get("url", "")),
                attempt=int(fields.get("attempt", 1)),
            )
        elif action == "live_adapter_call_succeeded":
            audit_emit.emit_live_adapter_call_succeeded(
                provider=str(fields.get("provider", "")),
                url=str(fields.get("url", "")),
                status=int(fields.get("status", 0)),
                duration_ms=int(fields.get("duration_ms", 0)),
                retried=bool(fields.get("retried", False)),
            )
        elif action == "live_adapter_call_failed":
            audit_emit.emit_live_adapter_call_failed(
                provider=str(fields.get("provider", "")),
                failure_mode=str(fields.get("failure_mode", "")),
                http_status=fields.get("http_status"),
                duration_ms=int(fields.get("duration_ms", 0)),
                retry_count=int(fields.get("retry_count", 0)),
            )
    except Exception:  # pragma: no cover - fail-open; telemetry never breaks the call
        pass


class LiveTransport:
    """Stdlib HTTP transport with timeout + retry + breaker handoff.

    Args:
        policy: per-call policy (timeouts, retry, jitter).
        ssl_context: optional override (default ``ssl.create_default_context()``
            with system CAs — no pinning in Sprint 12 per ADR-040 §note).
        clock: monotonic-seconds source (test-injectable).
        sleeper: callable taking seconds (test-injectable; default
            :func:`time.sleep`).
        rng: callable returning a uniform float in [0,1) (test-injectable).
        on_audit: optional callable invoked with audit events. Signature:
            ``(action: str, fields: dict) -> None``. Default no-op so the
            transport stays usable without the framework's audit module.

    Public method: :meth:`post_json`.
    """

    def __init__(
        self,
        policy: LiveCallPolicy,
        *,
        ssl_context: Optional[ssl.SSLContext] = None,
        clock: Optional[Callable[[], float]] = None,
        sleeper: Optional[Callable[[float], None]] = None,
        rng: Optional[Callable[[], float]] = None,
        on_audit: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> None:
        self._policy = policy
        self._ssl_context = ssl_context or ssl.create_default_context()
        self._clock = clock or _time.monotonic
        self._sleeper = sleeper or _time.sleep
        self._rng = rng or random.random
        self._on_audit = on_audit or (lambda *_a, **_k: None)

    # ------------------------------------------------------------------
    # Public surface
    # ------------------------------------------------------------------

    def get_json(
        self,
        url: str,
        headers: Dict[str, str],
    ) -> Tuple[Optional[TransportResponse], Optional[TransportFailure]]:
        """GET request (no body). Returns (response, None) or (None, failure).

        Used for Anthropic Batch API status/results polling endpoints which
        use GET — not POST. Same retry / audit / failure-mode semantics as
        :meth:`post_json`. Never raises on network error.
        """
        retried = False
        attempt = 0
        max_attempts = 1 + max(0, self._policy.max_retries)
        last_failure: Optional[TransportFailure] = None

        while attempt < max_attempts:
            attempt += 1
            self._on_audit(
                "live_adapter_call_started",
                {
                    "url": _scrub_url_query(url),
                    "headers": _scrub_headers(headers),
                    "attempt": attempt,
                    "provider": self._policy.provider,
                },
            )
            response, failure = self._attempt_get_once(url, headers)
            if response is not None:
                response.retried = retried
                self._on_audit(
                    "live_adapter_call_succeeded",
                    {
                        "provider": self._policy.provider,
                        "url": _scrub_url_query(url),
                        "status": response.status,
                        "duration_ms": response.duration_ms,
                        "retried": retried,
                    },
                )
                return response, None

            last_failure = failure
            assert failure is not None
            if failure.failure_mode in ("auth_permanent", "parse_error"):
                self._on_audit(
                    "live_adapter_call_failed",
                    {
                        "provider": self._policy.provider,
                        "failure_mode": failure.failure_mode,
                        "http_status": failure.http_status,
                        "duration_ms": failure.duration_ms,
                        "retry_count": 1 if retried else 0,
                    },
                )
                return None, failure

            if attempt >= max_attempts:
                break

            jitter = self._rng() * (self._policy.backoff_jitter_pct / 100.0)
            delay_ms = self._policy.backoff_initial_ms * (1 + jitter)
            delay_ms = min(delay_ms, self._policy.backoff_max_ms)
            self._sleeper(delay_ms / 1000.0)
            retried = True

        final_failure = last_failure or TransportFailure(
            failure_mode="server_error",
            http_status=None,
            duration_ms=0,
            retried=retried,
            detail="exhausted retries with no failure recorded (bug)",
        )
        final_failure.retried = retried
        self._on_audit(
            "live_adapter_call_failed",
            {
                "provider": self._policy.provider,
                "failure_mode": final_failure.failure_mode,
                "http_status": final_failure.http_status,
                "duration_ms": final_failure.duration_ms,
                "retry_count": 1 if retried else 0,
            },
        )
        return None, final_failure

    def post_json(
        self,
        url: str,
        headers: Dict[str, str],
        body: Dict[str, Any],
    ) -> Tuple[Optional[TransportResponse], Optional[TransportFailure]]:
        """POST ``body`` as JSON. Returns (response, None) or (None, failure).

        Never raises on network error — every failure is mapped to a
        :class:`TransportFailure` with a ``failure_mode`` enum string.
        Programmer errors (bad headers/body shape) DO raise — those are
        bugs, not network conditions.
        """
        try:
            payload = json.dumps(body).encode("utf-8")
        except (TypeError, ValueError) as e:
            # Programmer bug — surface fast.
            raise ValueError(f"body not JSON-serializable: {e}") from None

        retried = False
        attempt = 0
        max_attempts = 1 + max(0, self._policy.max_retries)
        last_failure: Optional[TransportFailure] = None
        last_response: Optional[TransportResponse] = None

        while attempt < max_attempts:
            attempt += 1
            self._on_audit(
                "live_adapter_call_started",
                {
                    "url": _scrub_url_query(url),
                    "headers": _scrub_headers(headers),
                    "attempt": attempt,
                    "provider": self._policy.provider,
                },
            )
            response, failure = self._attempt_once(url, headers, payload)
            if response is not None:
                response.retried = retried
                self._on_audit(
                    "live_adapter_call_succeeded",
                    {
                        "provider": self._policy.provider,
                        "url": _scrub_url_query(url),
                        "status": response.status,
                        "duration_ms": response.duration_ms,
                        "retried": retried,
                    },
                )
                return response, None

            last_failure = failure
            assert failure is not None  # for type narrowing
            # Permanent → no retry
            if failure.failure_mode in ("auth_permanent", "parse_error"):
                self._on_audit(
                    "live_adapter_call_failed",
                    {
                        "provider": self._policy.provider,
                        "failure_mode": failure.failure_mode,
                        "http_status": failure.http_status,
                        "duration_ms": failure.duration_ms,
                        "retry_count": 1 if retried else 0,
                    },
                )
                return None, failure

            if attempt >= max_attempts:
                break

            # Schedule retry with full-jitter backoff
            jitter = self._rng() * (self._policy.backoff_jitter_pct / 100.0)
            delay_ms = self._policy.backoff_initial_ms * (1 + jitter)
            delay_ms = min(delay_ms, self._policy.backoff_max_ms)
            self._sleeper(delay_ms / 1000.0)
            retried = True

        # All attempts exhausted
        final_failure = last_failure or TransportFailure(
            failure_mode="server_error",
            http_status=None,
            duration_ms=0,
            retried=retried,
            detail="exhausted retries with no failure recorded (bug)",
        )
        final_failure.retried = retried
        self._on_audit(
            "live_adapter_call_failed",
            {
                "provider": self._policy.provider,
                "failure_mode": final_failure.failure_mode,
                "http_status": final_failure.http_status,
                "duration_ms": final_failure.duration_ms,
                "retry_count": 1 if retried else 0,
            },
        )
        return None, final_failure

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _attempt_get_once(
        self,
        url: str,
        headers: Dict[str, str],
    ) -> Tuple[Optional[TransportResponse], Optional[TransportFailure]]:
        """Single GET attempt (no body). Same error-mapping as _attempt_once."""
        timeout_s = (
            self._policy.connect_timeout_ms + self._policy.read_timeout_ms
        ) / 1000.0

        req = urllib.request.Request(url, method="GET")
        for k, v in headers.items():
            req.add_header(k, v)

        is_https = url.lower().startswith("https://")
        start = self._clock()

        try:
            if is_https:
                resp = urllib.request.urlopen(
                    req, timeout=timeout_s, context=self._ssl_context
                )
            else:
                resp = urllib.request.urlopen(req, timeout=timeout_s)
            with resp:
                body_bytes = resp.read(_MAX_RESPONSE_BYTES)
                status = resp.getcode() or 0
        except urllib.error.HTTPError as e:
            elapsed_ms = int((self._clock() - start) * 1000)
            status = int(e.code)
            try:
                detail_bytes = e.read(2048) or b""
                detail = detail_bytes.decode("utf-8", errors="replace")
            except Exception:
                detail = ""
            mode = self._classify_http_status(status)
            return None, TransportFailure(
                failure_mode=mode,
                http_status=status,
                duration_ms=elapsed_ms,
                retried=False,
                detail=("" if mode == "auth_permanent" else detail[:500]),
                # O7-(5) — request-id is an opaque correlation token; safe
                # to keep even when the detail body is suppressed (auth).
                request_id=_extract_request_id(e, detail),
            )
        except urllib.error.URLError as e:
            elapsed_ms = int((self._clock() - start) * 1000)
            reason = getattr(e, "reason", e)
            mode = self._classify_url_error(reason)
            return None, TransportFailure(
                failure_mode=mode,
                http_status=None,
                duration_ms=elapsed_ms,
                retried=False,
                detail=str(reason)[:200],
            )
        except TimeoutError as e:
            elapsed_ms = int((self._clock() - start) * 1000)
            return None, TransportFailure(
                failure_mode="read_timeout",
                http_status=None,
                duration_ms=elapsed_ms,
                retried=False,
                detail=str(e)[:200],
            )
        except Exception as e:  # pragma: no cover — safety net
            elapsed_ms = int((self._clock() - start) * 1000)
            return None, TransportFailure(
                failure_mode="server_error",
                http_status=None,
                duration_ms=elapsed_ms,
                retried=False,
                detail=f"{type(e).__name__}: {e!s}"[:200],
            )

        elapsed_ms = int((self._clock() - start) * 1000)
        if 200 <= status < 300:
            return (
                TransportResponse(
                    status=status,
                    body_bytes=body_bytes,
                    duration_ms=elapsed_ms,
                    retried=False,
                ),
                None,
            )
        return None, TransportFailure(
            failure_mode="server_error",
            http_status=status,
            duration_ms=elapsed_ms,
            retried=False,
            detail=f"unexpected status {status}",
        )

    def _attempt_once(
        self,
        url: str,
        headers: Dict[str, str],
        payload: bytes,
    ) -> Tuple[Optional[TransportResponse], Optional[TransportFailure]]:
        # urllib accepts a single timeout; we approximate connect + read
        # by using the larger of the two, then re-checking elapsed time
        # before/after. This is conservative — preferable to no bound.
        timeout_s = (
            self._policy.connect_timeout_ms + self._policy.read_timeout_ms
        ) / 1000.0

        req = urllib.request.Request(url, data=payload, method="POST")
        for k, v in headers.items():
            req.add_header(k, v)
        # Always set Content-Type if caller forgot.
        if "Content-Type" not in headers and "content-type" not in headers:
            req.add_header("Content-Type", "application/json")

        is_https = url.lower().startswith("https://")
        start = self._clock()

        try:
            if is_https:
                resp = urllib.request.urlopen(
                    req, timeout=timeout_s, context=self._ssl_context
                )
            else:
                # http:// — used by local Ollama only.
                resp = urllib.request.urlopen(req, timeout=timeout_s)
            with resp:
                body_bytes = resp.read(_MAX_RESPONSE_BYTES)
                status = resp.getcode() or 0
        except urllib.error.HTTPError as e:
            elapsed_ms = int((self._clock() - start) * 1000)
            status = int(e.code)
            # Read body for error context (truncated; never logged for 4xx auth).
            try:
                detail_bytes = e.read(2048) or b""
                detail = detail_bytes.decode("utf-8", errors="replace")
            except Exception:
                detail = ""
            mode = self._classify_http_status(status)
            # PLAN-093 Wave C.4.1 — SEMI-13 rate-limited telemetry wire.
            if mode == "rate_limited":
                try:
                    from _lib import audit_emit as _ae  # type: ignore
                    if hasattr(_ae, "emit_generic"):
                        _ae.emit_generic(
                            "anthropic_429_observed",
                            http_status=int(status),
                            duration_ms=int(elapsed_ms),
                        )
                except Exception:
                    pass
            # For 4xx/5xx we still treat parse-shaped errors uniformly via mode.
            return None, TransportFailure(
                failure_mode=mode,
                http_status=status,
                duration_ms=elapsed_ms,
                retried=False,
                detail=("" if mode == "auth_permanent" else detail[:500]),
                # O7-(5) — request-id is an opaque correlation token; safe
                # to keep even when the detail body is suppressed (auth).
                request_id=_extract_request_id(e, detail),
            )
        except urllib.error.URLError as e:
            elapsed_ms = int((self._clock() - start) * 1000)
            reason = getattr(e, "reason", e)
            mode = self._classify_url_error(reason)
            return None, TransportFailure(
                failure_mode=mode,
                http_status=None,
                duration_ms=elapsed_ms,
                retried=False,
                detail=str(reason)[:200],
            )
        except socket.timeout as e:  # pragma: no cover - alias-handled below on 3.10+
            elapsed_ms = int((self._clock() - start) * 1000)
            return None, TransportFailure(
                failure_mode="read_timeout",
                http_status=None,
                duration_ms=elapsed_ms,
                retried=False,
                detail=str(e)[:200],
            )
        except TimeoutError as e:
            elapsed_ms = int((self._clock() - start) * 1000)
            return None, TransportFailure(
                failure_mode="read_timeout",
                http_status=None,
                duration_ms=elapsed_ms,
                retried=False,
                detail=str(e)[:200],
            )
        except Exception as e:  # pragma: no cover — safety net
            elapsed_ms = int((self._clock() - start) * 1000)
            return None, TransportFailure(
                failure_mode="server_error",
                http_status=None,
                duration_ms=elapsed_ms,
                retried=False,
                detail=f"{type(e).__name__}: {e!s}"[:200],
            )

        elapsed_ms = int((self._clock() - start) * 1000)
        if 200 <= status < 300:
            return (
                TransportResponse(
                    status=status,
                    body_bytes=body_bytes,
                    duration_ms=elapsed_ms,
                    retried=False,
                ),
                None,
            )
        # 1xx / 3xx are unexpected for our APIs — treat as server_error
        return None, TransportFailure(
            failure_mode="server_error",
            http_status=status,
            duration_ms=elapsed_ms,
            retried=False,
            detail=f"unexpected status {status}",
        )

    @staticmethod
    def _classify_http_status(status: int) -> str:
        if status in (401, 403):
            return "auth_permanent"
        if status == 429:
            return "rate_limited"
        if 500 <= status < 600:
            return "server_error"
        # 4xx other than auth/rate-limit → permanent (e.g. 400 bad request)
        if 400 <= status < 500:
            return "auth_permanent"
        return "server_error"

    @staticmethod
    def _classify_url_error(reason: Any) -> str:
        if isinstance(reason, socket.timeout) or isinstance(reason, TimeoutError):
            return "read_timeout"
        msg = str(reason).lower() if reason is not None else ""
        if "timed out" in msg or "timeout" in msg:
            # connect-vs-read distinction is best-effort from the message
            if "connect" in msg:
                return "connect_timeout"
            return "read_timeout"
        if "refused" in msg or "errno 61" in msg or "errno 111" in msg:
            return "connection_refused"
        # Unknown URLError — treat as server_error (transient)
        return "server_error"


__all__ = ["LiveTransport", "TransportResponse", "TransportFailure"]
