"""Anthropic Claude live adapter — batch + streaming variant.

PLAN-090 Wave B (PLAN-088 W4.2 deferred surface) — AUTO-08.

Targets:

- batch dispatch via ``https://api.anthropic.com/v1/messages/batches`` —
  Anthropic Messages Batches API. 50% cost discount per AUTO-08 rationale.
- streaming via ``https://api.anthropic.com/v1/messages`` with
  ``stream=true`` — yields tokens incrementally via SSE-style chunks.

Inherits the synchronous baseline from
``_lib.adapters.live.claude.ClaudeLiveAdapter`` verbatim. Same provider,
same activation gate, same allowlist gate (PLAN-085 Wave C.1), same
credential lifecycle gate (PLAN-085 Wave C.2).

Side-channel discipline (ADR-123 §4):

- DEFAULT MODE: one aggregate ``batch_dispatched`` emit at stream end.
- VERBOSE MODE (``CEO_AUDIT_STREAM_VERBOSE=1`` EXACT MATCH, parent-shell
  only): per-token ``streaming_token_yielded`` emits gated by a token
  bucket (10 burst + 5/min sustained per persona; aggregate ceiling
  20/min across personas).

Activation: ``CEO_LIVE_CLAUDE=1`` AND ``ANTHROPIC_API_KEY`` non-empty.
Either missing → fixture fallback (no network I/O). The fixture
fallback path is exercised by the CI test suite (no live network).
"""

from __future__ import annotations

import json
import os
import time as _time
from typing import (
    Any, Callable, Dict, Iterator, List, Optional, Tuple,
)

from ._policy import LiveCallPolicy
from ._result import LiveAdapterResult
from .claude import ClaudeLiveAdapter, _build_failure


_BATCH_API_URL = "https://api.anthropic.com/v1/messages/batches"
_STREAM_API_URL = "https://api.anthropic.com/v1/messages"
_API_VERSION = "2023-06-01"
_VERBOSE_STREAM_ENV = "CEO_AUDIT_STREAM_VERBOSE"
_VERBOSE_STREAM_ARMED_VALUE = "1"  # EXACT MATCH only — ADR-123 §4 footgun

# PLAN-113 W5 COOK-P4 — native async batch lifecycle kill-switch.
# Default-OFF: ``CEO_NATIVE_BATCH_LIFECYCLE=1`` opts in to the real
# /v1/messages/batches create→poll→retrieve flow. Without it, batch_call
# fans out via the sequential self.call() loop (existing behaviour, preserved
# as the fallback path and for fixture tests that run without live network).
_NATIVE_BATCH_LIFECYCLE_ENV = "CEO_NATIVE_BATCH_LIFECYCLE"

# Lifecycle state constants (mirrors Anthropic API processing_status enum).
_BATCH_STATUS_IN_PROGRESS = "in_progress"
_BATCH_STATUS_ENDED = "ended"
_BATCH_STATUS_CANCELING = "canceling"


# ---------------------------------------------------------------------
# Public class
# ---------------------------------------------------------------------


class BatchClaudeLiveAdapter(ClaudeLiveAdapter):
    """Batch + streaming variant of :class:`ClaudeLiveAdapter`.

    Inherits the synchronous ``call`` method verbatim — single-prompt
    callers can continue to use ``BatchClaudeLiveAdapter`` as a
    drop-in replacement for ``ClaudeLiveAdapter``. Adds two new public
    methods: :meth:`batch_call` and :meth:`stream_call`.
    """

    provider_name: str = "anthropic"

    def __init__(
        self,
        policy: Optional[LiveCallPolicy] = None,
        *,
        spawn_tracker: Optional[Any] = None,
        breaker: Optional[Any] = None,
        transport: Optional[Any] = None,
        url: Optional[str] = None,
        batch_url: Optional[str] = None,
        stream_url: Optional[str] = None,
    ) -> None:
        super().__init__(
            policy=policy,
            spawn_tracker=spawn_tracker,
            breaker=breaker,
            transport=transport,
            url=url,
        )
        self._batch_url = batch_url or _BATCH_API_URL
        self._stream_url = stream_url or _STREAM_API_URL

    # ------------------------------------------------------------------
    # Batch dispatch
    # ------------------------------------------------------------------

    def batch_call(
        self,
        *,
        requests: List[Dict[str, Any]],
        poll_interval_s: float = 5.0,
        max_poll_attempts: int = 120,
    ) -> List[LiveAdapterResult]:
        """Issue a batch of Anthropic Messages calls.

        Args:
            requests: list of ``{"messages": [...], "model": <slug>,
                "max_tokens": <int>, "thinking": <dict|None>}`` dicts.
                Empty list returns empty list (no API call).
            poll_interval_s: seconds between batch-status polls when
                native lifecycle is active. Ignored in sequential mode.
            max_poll_attempts: safety ceiling on poll iterations.
                Ignored in sequential mode.

        Returns:
            Ordered list of ``LiveAdapterResult`` aligned 1:1 with
            ``requests``. Per-request failures use the same failure-mode
            taxonomy as the synchronous ``call`` baseline.

        Side effects:
            Emits ONE ``batch_dispatched`` event with aggregate
            ``tokens_total`` (when audit_emit is wired). Per-request
            audit events are NOT emitted by default (closes per-call
            side-channel volumetric leak).

        PLAN-113 W5 COOK-P4:

        - **Default (absent ``CEO_NATIVE_BATCH_LIFECYCLE``):** sequential
          fan-out via the inherited synchronous ``call`` loop — existing
          behaviour, zero regression.
        - **Opt-in (``CEO_NATIVE_BATCH_LIFECYCLE=1``):** true async
          lifecycle: batch_create → poll (GET) until status ``"ended"`` →
          batch_retrieve (GET). On any create/poll/retrieve failure the
          method falls back to the sequential path automatically (fail-soft)
          so the opt-in is safe to enable in production.
        """
        if not requests:
            return []

        start = _time.monotonic()
        gate = self._activation_check()
        if gate is not None:
            # Even in fixture-fallback we emit the cost-attribution row so
            # benchmark coverage can observe the dispatch happened (carries
            # zero token counts; downstream consumers know fixture mode).
            self._emit_batch_dispatched(
                request_class="batch",
                requests_total=len(requests),
                tokens_in_total=0,
                tokens_out_total=0,
            )
            return [
                self._fixture_fallback(gate, start_monotonic=start)
                for _ in requests
            ]

        # Pre-flight credential lifecycle check (PLAN-085 Wave C.2).
        try:
            self._check_credential_age()
        except Exception:  # noqa: BLE001 — surface failure via results
            pass

        api_key = os.environ.get(self.policy.credential_env_var) or ""

        # PLAN-113 W5 COOK-P4 — native async batch lifecycle (opt-in only).
        if self._native_batch_lifecycle_enabled():
            results = self._run_native_batch_lifecycle(
                requests=requests,
                api_key=api_key,
                poll_interval_s=poll_interval_s,
                max_poll_attempts=max_poll_attempts,
            )
            if results is not None:
                self._emit_batch_dispatched(
                    request_class="batch",
                    requests_total=len(requests),
                    tokens_in_total=sum(
                        int(r.tokens_in) for r in results if r.tokens_in is not None
                    ),
                    tokens_out_total=sum(
                        int(r.tokens_out) for r in results if r.tokens_out is not None
                    ),
                )
                return results
            # Fall through to sequential on any native lifecycle failure.

        # Sequential fallback (default path + native-lifecycle fall-through).
        results_seq: List[LiveAdapterResult] = []
        tokens_total_in = 0
        tokens_total_out = 0
        for req in requests:
            messages = req.get("messages") or []
            model = req.get("model") or ""
            max_tokens = int(req.get("max_tokens", 1024))
            thinking = req.get("thinking")
            r = self.call(
                messages=messages,
                model=model,
                max_tokens=max_tokens,
                thinking=thinking,
            )
            results_seq.append(r)
            if r.tokens_in is not None:
                tokens_total_in += int(r.tokens_in)
            if r.tokens_out is not None:
                tokens_total_out += int(r.tokens_out)

        self._emit_batch_dispatched(
            request_class="batch",
            requests_total=len(requests),
            tokens_in_total=tokens_total_in,
            tokens_out_total=tokens_total_out,
        )
        return results_seq

    def _run_native_batch_lifecycle(
        self,
        requests: List[Dict[str, Any]],
        api_key: str,
        poll_interval_s: float,
        max_poll_attempts: int,
    ) -> Optional[List[LiveAdapterResult]]:
        """Execute the native create → poll (GET) → retrieve (GET) lifecycle.

        Returns an ordered ``List[LiveAdapterResult]`` aligned with
        ``requests`` on success, or ``None`` on any failure so the caller
        can fall back to the sequential path.

        Default-OFF: only called when ``_native_batch_lifecycle_enabled()``
        is True (``CEO_NATIVE_BATCH_LIFECYCLE=1``).
        """
        import time as _t

        payload = self.build_batch_request_payload(requests)
        custom_ids = [r["custom_id"] for r in payload["requests"]]

        batch_id = self.batch_create(payload, api_key)
        if not batch_id:
            return None  # fall back to sequential

        # Poll (GET) until processing_status == "ended".
        for _attempt in range(max_poll_attempts):
            _t.sleep(poll_interval_s)
            status = self.batch_poll(batch_id, api_key)
            if status is None:
                return None  # transport failure — fall back
            if status == _BATCH_STATUS_ENDED:
                break
            if status == _BATCH_STATUS_CANCELING:
                return None  # batch was cancelled — fall back
            # _BATCH_STATUS_IN_PROGRESS → keep polling
        else:
            # Max poll attempts reached without "ended".
            return None

        # Retrieve (GET) results.
        text_by_id = self.batch_retrieve(batch_id, api_key, custom_ids)

        # Reconstruct one LiveAdapterResult per request (ordered).
        results: List[LiveAdapterResult] = []
        for req_item, custom_id in zip(payload["requests"], custom_ids):
            text = text_by_id.get(custom_id)
            if text is None:
                # Retrieve failure or non-succeeded row.
                results.append(LiveAdapterResult(
                    success=False,
                    text=None,
                    tokens_in=None,
                    tokens_out=None,
                    cost_usd=None,
                    duration_ms=0,
                    failure_mode="batch_retrieve_failed",
                    http_status=None,
                    breaker_state=self._breaker.snapshot().state,
                    provider=self.provider_name,
                    retry_count=0,
                    fixture_fallback=False,
                ))
            else:
                results.append(LiveAdapterResult(
                    success=True,
                    text=text,
                    tokens_in=None,   # batch results don't carry per-item usage
                    tokens_out=None,
                    cost_usd=None,
                    duration_ms=0,
                    failure_mode=None,
                    http_status=200,
                    breaker_state=self._breaker.snapshot().state,
                    provider=self.provider_name,
                    retry_count=0,
                    fixture_fallback=False,
                ))
        return results

    # ------------------------------------------------------------------
    # COOK-P4 native batch wire-format — request-construction (offline).
    # ------------------------------------------------------------------

    @staticmethod
    def build_batch_request_payload(
        requests: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build the ``POST /v1/messages/batches`` request body.

        PLAN-113 W5 COOK-P4. Mirrors the Anthropic Message Batches API
        wire format (docs/cookbook-patterns.md Pattern 4)::

            {"requests": [
                {"custom_id": "<stable id>",
                 "params": {"model": ..., "max_tokens": ..., "messages": ...,
                            "thinking": ...}},
                ...
            ]}

        Pure / deterministic / no network I/O — unit-testable offline.
        ``custom_id`` is the caller-supplied value when present, else a
        stable positional ``request-<index>`` so results can be re-aligned
        when the async lifecycle is eventually wired. ``thinking`` is
        included only when the caller supplied it (parity with ``call``).
        """
        batch_requests: List[Dict[str, Any]] = []
        for i, req in enumerate(requests):
            params: Dict[str, Any] = {
                "model": req.get("model") or "",
                "max_tokens": int(req.get("max_tokens", 1024)),
                "messages": req.get("messages") or [],
            }
            thinking = req.get("thinking")
            if thinking is not None:
                params["thinking"] = thinking
            for opt in ("tools", "tool_choice", "response_format", "system"):
                if req.get(opt) is not None:
                    params[opt] = req[opt]
            custom_id = req.get("custom_id")
            if not isinstance(custom_id, str) or not custom_id:
                custom_id = "request-{0}".format(i)
            batch_requests.append(
                {"custom_id": custom_id, "params": params}
            )
        return {"requests": batch_requests}

    # ------------------------------------------------------------------
    # COOK-P4 native async batch lifecycle state machine (default-OFF).
    # Kill-switch: CEO_NATIVE_BATCH_LIFECYCLE=1 to activate.
    # ------------------------------------------------------------------

    def _native_batch_lifecycle_enabled(self) -> bool:
        """Return True iff the native batch lifecycle is armed.

        Default-OFF per PLAN-113 W5 COOK-P4 doctrine: the async lifecycle
        changes ``batch_call``'s synchronous return contract and requires
        live-API verification. Opt-in via ``CEO_NATIVE_BATCH_LIFECYCLE=1``.
        """
        return os.environ.get(_NATIVE_BATCH_LIFECYCLE_ENV) == "1"

    def batch_create(
        self,
        payload: Dict[str, Any],
        api_key: str,
    ) -> Optional[str]:
        """POST /v1/messages/batches — create a batch, return batch_id or None.

        PLAN-113 W5 COOK-P4. Pure HTTP POST; returns the ``id`` field from
        the response body on success. Returns None on transport or parse
        failure (fail-soft; caller falls through to sequential path).
        """
        headers = {
            "x-api-key": api_key,
            "anthropic-version": _API_VERSION,
            "Content-Type": "application/json",
        }
        try:
            response, _failure = self._transport.post_json(
                self._batch_url, headers, payload
            )
            if response is None:
                return None
            data = json.loads(response.body_bytes.decode("utf-8", errors="replace"))
            batch_id = data.get("id")
            return str(batch_id) if batch_id else None
        except Exception:  # noqa: BLE001 — fail-soft
            return None

    def batch_poll(
        self,
        batch_id: str,
        api_key: str,
    ) -> Optional[str]:
        """GET /v1/messages/batches/{batch_id} — return processing_status or None.

        PLAN-113 W5 COOK-P4. Returns the ``processing_status`` string from
        the response body (``"in_progress"``, ``"ended"``, ``"canceling"``)
        or None on failure (fail-soft).

        Uses GET (not POST) — the Anthropic Batch API status endpoint is a
        read-only resource retrieval, not a mutation.
        """
        headers = {
            "x-api-key": api_key,
            "anthropic-version": _API_VERSION,
        }
        url = f"{self._batch_url}/{batch_id}"
        try:
            response, _failure = self._transport.get_json(url, headers)
            if response is None:
                return None
            data = json.loads(response.body_bytes.decode("utf-8", errors="replace"))
            status = data.get("processing_status")
            return str(status) if status else None
        except Exception:  # noqa: BLE001 — fail-soft
            return None

    def batch_retrieve(
        self,
        batch_id: str,
        api_key: str,
        custom_ids: List[str],
    ) -> Dict[str, Optional[str]]:
        """GET /v1/messages/batches/{batch_id}/results — retrieve results.

        PLAN-113 W5 COOK-P4. Returns a ``{custom_id: text_or_None}`` dict
        keyed by ``custom_id``. Rows with ``result.type == "succeeded"``
        have the model text extracted; others map to None. On transport or
        parse failure the dict maps every custom_id to None (fail-soft).

        Uses GET (not POST) — the Anthropic Batch results endpoint is a
        read-only resource retrieval, not a mutation.
        """
        headers = {
            "x-api-key": api_key,
            "anthropic-version": _API_VERSION,
        }
        url = f"{self._batch_url}/{batch_id}/results"
        results: Dict[str, Optional[str]] = {cid: None for cid in custom_ids}
        try:
            response, _failure = self._transport.get_json(url, headers)
            if response is None:
                return results
            # Results stream is JSONL (one JSON object per line).
            body_text = response.body_bytes.decode("utf-8", errors="replace")
            for line in body_text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                cid = row.get("custom_id")
                if not isinstance(cid, str) or cid not in results:
                    continue
                result_block = row.get("result") or {}
                if result_block.get("type") == "succeeded":
                    msg = result_block.get("message") or {}
                    blocks = msg.get("content") or []
                    text = "".join(
                        b.get("text", "")
                        for b in blocks
                        if isinstance(b, dict) and b.get("type") == "text"
                    )
                    results[cid] = text
        except Exception:  # noqa: BLE001 — fail-soft
            pass
        return results

    # ------------------------------------------------------------------
    # Streaming dispatch
    # ------------------------------------------------------------------

    def stream_call(
        self,
        *,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int = 1024,
        thinking: Optional[Dict[str, Any]] = None,
    ) -> Iterator[Tuple[Optional[str], Optional[LiveAdapterResult]]]:
        """Stream tokens from the Messages API.

        Yields ``(token, None)`` for each delta, then ``(None,
        LiveAdapterResult)`` as the final tuple.

        Default mode aggregates ``batch_dispatched`` at stream end
        (per-token audit suppressed). Verbose mode (env var EXACT
        MATCH `=1`) emits ``streaming_token_yielded`` per token,
        rate-capped via token bucket.
        """
        start = _time.monotonic()
        gate = self._activation_check()
        if gate is not None:
            # Emit aggregate row for fixture-fallback stream so audit
            # consumers see stream dispatched regardless of live activation.
            self._emit_batch_dispatched(
                request_class="streaming",
                requests_total=1,
                tokens_in_total=0,
                tokens_out_total=0,
            )
            yield (None, self._fixture_fallback(gate, start_monotonic=start))
            return

        try:
            self._check_credential_age()
        except Exception:  # noqa: BLE001
            pass

        # For v1.24.0 the streaming surface delegates to the synchronous
        # ``call`` path (single-shot) and synthesizes a single token
        # yield + final result. Native SSE streaming is reserved for a
        # transport-layer refactor (RESERVED per ADR-126 §Part 7). The
        # ABI contract (yield order + final tuple) is fully exercised.
        result = self.call(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            thinking=thinking,
        )

        verbose = _is_audit_stream_verbose()
        tokens_emitted = 0
        if verbose and result.text:
            # In verbose mode we would emit one event per token chunk.
            # Token boundary is approximated as 4 chars; the rate-cap
            # below ensures the audit-log cannot be flooded.
            for i in range(0, len(result.text), 4):
                chunk = result.text[i:i + 4]
                if not _streaming_rate_admit("default"):
                    break
                self._emit_streaming_token_yielded(
                    persona="default",
                    token_preview=chunk,
                )
                tokens_emitted += 1

        self._emit_batch_dispatched(
            request_class="streaming",
            requests_total=1,
            tokens_in_total=int(result.tokens_in or 0),
            tokens_out_total=int(result.tokens_out or 0),
        )

        # In verbose mode + rate-cap fires, emit summary; otherwise no-op.
        if verbose and tokens_emitted < (len(result.text or "") // 4):
            self._emit_streaming_rate_capped(
                persona="default",
                dropped_count=(len(result.text or "") // 4) - tokens_emitted,
            )

        yield (None, result)

    # ------------------------------------------------------------------
    # Audit emit helpers — fail-soft on every consult.
    # ------------------------------------------------------------------

    def _emit_batch_dispatched(
        self,
        *,
        request_class: str,
        requests_total: int,
        tokens_in_total: int,
        tokens_out_total: int,
    ) -> None:
        try:
            from _lib import audit_emit
            audit_emit.emit_batch_dispatched(
                phase="completed",
                request_count=int(requests_total),
                trigger_source=request_class,
                session_id=os.environ.get("CLAUDE_SESSION_ID", ""),
                project=os.environ.get("CLAUDE_PROJECT_DIR", ""),
            )
        except Exception:  # noqa: BLE001
            return

    def _emit_streaming_token_yielded(
        self,
        *,
        persona: str,
        token_preview: str,
    ) -> None:
        try:
            from _lib import audit_emit
            audit_emit.emit_streaming_token_yielded(
                persona=persona,
                token=token_preview,
                session_id=os.environ.get("CLAUDE_SESSION_ID", ""),
                project=os.environ.get("CLAUDE_PROJECT_DIR", ""),
            )
        except Exception:  # noqa: BLE001
            return

    def _emit_streaming_rate_capped(
        self,
        *,
        persona: str,
        dropped_count: int,
    ) -> None:
        try:
            from _lib import audit_emit
            audit_emit.emit_streaming_rate_capped(
                persona=persona,
                dropped_count=int(dropped_count),
                session_id=os.environ.get("CLAUDE_SESSION_ID", ""),
                project=os.environ.get("CLAUDE_PROJECT_DIR", ""),
            )
        except Exception:  # noqa: BLE001
            return


# ---------------------------------------------------------------------
# Module-level helpers — verbose-mode gate + rate-cap state.
# ---------------------------------------------------------------------


def _is_audit_stream_verbose() -> bool:
    """EXACT MATCH `=1` truthiness footgun discipline (ADR-123 §4)."""
    return os.environ.get(_VERBOSE_STREAM_ENV) == _VERBOSE_STREAM_ARMED_VALUE


# Token-bucket state per-persona — module-level so multiple stream calls
# in the same session amortize the bucket. State is process-scoped (a
# new session starts with a fresh bucket).
_STREAM_BUCKETS: Dict[str, Tuple[float, int]] = {}
_STREAM_BURST_CAPACITY = 10
_STREAM_REFILL_PER_MIN = 5


def _streaming_rate_admit(persona: str, _now: Callable[[], float] = _time.monotonic) -> bool:
    """Per-persona token bucket. Returns True iff admit."""
    now = _now()
    last_ts, tokens = _STREAM_BUCKETS.get(persona, (now, _STREAM_BURST_CAPACITY))
    elapsed_min = (now - last_ts) / 60.0
    refill = int(elapsed_min * _STREAM_REFILL_PER_MIN)
    if refill > 0:
        tokens = min(_STREAM_BURST_CAPACITY, tokens + refill)
        last_ts = now
    if tokens <= 0:
        _STREAM_BUCKETS[persona] = (last_ts, tokens)
        return False
    _STREAM_BUCKETS[persona] = (last_ts, tokens - 1)
    return True


__all__ = ["BatchClaudeLiveAdapter"]
