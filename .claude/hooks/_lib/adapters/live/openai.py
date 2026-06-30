"""OpenAI live adapter — ADR-040 §5, §6.

Targets ``https://api.openai.com/v1/chat/completions`` (chat) and
``https://api.openai.com/v1/embeddings`` (embeddings).

ADR-040 §5 / Security S1 mandates that EMBEDDING calls send the
``OpenAI-Data-Retention: opt_out`` header (the canonical 2026-Q2 name
for the opt-out signal — verify against the provider doc on flip).
This adapter sets the header on every call to be safe (Anthropic /
Google do not have an equivalent and operator attestation in
``docs/rotation-log.md`` is the compensating control there).

Activation: ``CEO_LIVE_OPENAI=1`` AND ``OPENAI_API_KEY`` non-empty.
"""

from __future__ import annotations

import json
import os
import time as _time
from typing import Any, Dict, List, Optional

from ._breaker import CircuitBreaker
from ._cost import (
    BudgetHardStop,
    SpawnCostTracker,
    actual_cost_usd,
    estimate_cost_usd,
)
from ._policy import LiveCallPolicy, OpenAILivePolicy
from ._result import LiveAdapterResult
from ._transport import LiveTransport, audit_emit_dispatch
from .claude import _build_failure  # shared helper


_CHAT_URL = "https://api.openai.com/v1/chat/completions"
_EMBED_URL = "https://api.openai.com/v1/embeddings"

# Header name + value per ADR-040 §5. Documented as best-known 2026-Q2
# convention; if OpenAI publishes a different name at flip-time, swap
# here AND update ADR-040 §5.
_OPT_OUT_HEADER_NAME = "OpenAI-Data-Retention"
_OPT_OUT_HEADER_VALUE = "opt_out"


class OpenAILiveAdapter:
    """Live adapter for OpenAI Chat Completions + Embeddings.

    Two entry points:

    - :meth:`call` — chat completion (canonical ``messages`` list).
    - :meth:`embed` — embeddings; sets the opt-out header per S1.
    """

    provider_name: str = "openai"

    def __init__(
        self,
        policy: Optional[LiveCallPolicy] = None,
        *,
        spawn_tracker: Optional[SpawnCostTracker] = None,
        breaker: Optional[CircuitBreaker] = None,
        transport: Optional[LiveTransport] = None,
        chat_url: Optional[str] = None,
        embed_url: Optional[str] = None,
    ) -> None:
        if policy is not None and policy.provider != "openai":
            raise ValueError(
                f"OpenAILiveAdapter requires policy.provider='openai', got {policy.provider!r}"
            )
        self.policy: LiveCallPolicy = policy or OpenAILivePolicy()
        self._spawn_tracker = spawn_tracker or SpawnCostTracker(
            ceiling_usd=self.policy.max_spend_usd_per_spawn
        )
        self._breaker = breaker or CircuitBreaker(
            threshold=self.policy.breaker_threshold,
            window_s=self.policy.breaker_window_s,
            half_open_s=self.policy.breaker_half_open_s,
        )
        self._transport = transport or LiveTransport(
            self.policy, on_audit=audit_emit_dispatch
        )
        self._chat_url = chat_url or _CHAT_URL
        self._embed_url = embed_url or _EMBED_URL

    def _activation_check(self) -> Optional[str]:
        if os.environ.get("CEO_SOTA_DISABLE") == "1":
            return "sota_disabled"
        if os.environ.get(self.policy.activation_env_var) != "1":
            return "activation_off"
        if not os.environ.get(self.policy.credential_env_var):
            return "missing_credential"
        return None

    def _base_headers(self) -> Dict[str, str]:
        api_key = os.environ.get(self.policy.credential_env_var) or ""
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            # Always send opt-out — chat data retention is a separate
            # surface from embeddings but the header is harmless on chat.
            _OPT_OUT_HEADER_NAME: _OPT_OUT_HEADER_VALUE,
        }

    def call(
        self,
        *,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int = 1024,
    ) -> LiveAdapterResult:
        """Issue one Chat Completions call."""
        start = _time.monotonic()

        gate = self._activation_check()
        if gate is not None:
            return self._fixture_fallback(gate, start_monotonic=start)

        try:
            estimated = estimate_cost_usd(
                self.provider_name, model, messages, max_tokens
            )
            if self._spawn_tracker.would_exceed(estimated):
                return _build_failure(
                    self.provider_name,
                    self._breaker,
                    "budget_hard_stop",
                    duration_ms=int((_time.monotonic() - start) * 1000),
                )
        except Exception:  # pragma: no cover
            estimated = 0.0

        if not self._breaker.should_allow():
            return _build_failure(
                self.provider_name,
                self._breaker,
                "breaker_open",
                duration_ms=int((_time.monotonic() - start) * 1000),
            )

        body: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": int(max_tokens),
        }
        response, failure = self._transport.post_json(
            self._chat_url, self._base_headers(), body
        )

        if response is not None:
            return self._on_chat_response(
                response.status,
                response.body_bytes,
                model,
                duration_ms=response.duration_ms,
                retried=response.retried,
            )

        assert failure is not None
        self._breaker.record_failure(failure.failure_mode)
        return LiveAdapterResult(
            success=False,
            text=None,
            duration_ms=failure.duration_ms,
            failure_mode=failure.failure_mode,
            http_status=failure.http_status,
            breaker_state=self._breaker.snapshot().state,
            provider=self.provider_name,
            retry_count=1 if failure.retried else 0,
        )

    def embed(
        self,
        *,
        inputs: List[str],
        model: str = "text-embedding-3-small",
    ) -> LiveAdapterResult:
        """Issue one Embeddings call (the opt-out header is mandatory here).

        ``text`` on success is a JSON-encoded list of vectors (so the
        :class:`LiveAdapterResult` shape stays uniform); callers parse
        with :func:`json.loads`. Token counts come from the response
        ``usage`` block; cost is computed via the embeddings table when
        available, falling back to the conservative default.
        """
        start = _time.monotonic()

        gate = self._activation_check()
        if gate is not None:
            return self._fixture_fallback(gate, start_monotonic=start)

        if not self._breaker.should_allow():
            return _build_failure(
                self.provider_name,
                self._breaker,
                "breaker_open",
                duration_ms=int((_time.monotonic() - start) * 1000),
            )

        # The opt-out header is enforced by _base_headers; make the
        # invariant explicit so misconfiguration surfaces fast.
        headers = self._base_headers()
        if headers.get(_OPT_OUT_HEADER_NAME) != _OPT_OUT_HEADER_VALUE:
            return _build_failure(
                self.provider_name,
                self._breaker,
                "scope_misconfigured",
                duration_ms=int((_time.monotonic() - start) * 1000),
            )

        body: Dict[str, Any] = {"model": model, "input": inputs}
        response, failure = self._transport.post_json(
            self._embed_url, headers, body
        )

        if response is not None:
            return self._on_embed_response(
                response.status,
                response.body_bytes,
                model,
                duration_ms=response.duration_ms,
                retried=response.retried,
            )

        assert failure is not None
        self._breaker.record_failure(failure.failure_mode)
        return LiveAdapterResult(
            success=False,
            duration_ms=failure.duration_ms,
            failure_mode=failure.failure_mode,
            http_status=failure.http_status,
            breaker_state=self._breaker.snapshot().state,
            provider=self.provider_name,
            retry_count=1 if failure.retried else 0,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _fixture_fallback(self, reason: str, *, start_monotonic: float) -> LiveAdapterResult:
        elapsed_ms = int((_time.monotonic() - start_monotonic) * 1000)
        failure_mode = "missing_credential" if reason == "missing_credential" else None
        return LiveAdapterResult(
            success=failure_mode is None,
            duration_ms=elapsed_ms,
            failure_mode=failure_mode,
            breaker_state=self._breaker.snapshot().state,
            provider=self.provider_name,
            fixture_fallback=True,
        )

    def _on_chat_response(
        self,
        status: int,
        body_bytes: bytes,
        model: str,
        *,
        duration_ms: int,
        retried: bool,
    ) -> LiveAdapterResult:
        try:
            payload = json.loads(body_bytes.decode("utf-8", errors="replace"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._breaker.record_failure("parse_error")
            return _build_failure(
                self.provider_name,
                self._breaker,
                "parse_error",
                http_status=status,
                duration_ms=duration_ms,
                retried=retried,
            )
        try:
            choice = (payload.get("choices") or [{}])[0]
            message = choice.get("message") or {}
            text = message.get("content") or ""
            usage = payload.get("usage") or {}
            tokens_in = int(usage["prompt_tokens"]) if "prompt_tokens" in usage else None
            tokens_out = (
                int(usage["completion_tokens"]) if "completion_tokens" in usage else None
            )
        except (TypeError, AttributeError, ValueError):
            self._breaker.record_failure("parse_error")
            return _build_failure(
                self.provider_name,
                self._breaker,
                "parse_error",
                http_status=status,
                duration_ms=duration_ms,
                retried=retried,
            )
        cost = actual_cost_usd(self.provider_name, model, tokens_in, tokens_out)
        try:
            self._spawn_tracker.add(cost)
        except BudgetHardStop:
            pass
        self._breaker.record_success()
        return LiveAdapterResult(
            success=True,
            text=text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost,
            duration_ms=duration_ms,
            http_status=status,
            breaker_state=self._breaker.snapshot().state,
            provider=self.provider_name,
            retry_count=1 if retried else 0,
        )

    def _on_embed_response(
        self,
        status: int,
        body_bytes: bytes,
        model: str,
        *,
        duration_ms: int,
        retried: bool,
    ) -> LiveAdapterResult:
        try:
            payload = json.loads(body_bytes.decode("utf-8", errors="replace"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._breaker.record_failure("parse_error")
            return _build_failure(
                self.provider_name,
                self._breaker,
                "parse_error",
                http_status=status,
                duration_ms=duration_ms,
                retried=retried,
            )
        try:
            data = payload.get("data") or []
            vectors = [d.get("embedding") for d in data if isinstance(d, dict)]
            usage = payload.get("usage") or {}
            tokens_in = int(usage["prompt_tokens"]) if "prompt_tokens" in usage else None
            tokens_out = (
                int(usage["total_tokens"]) if "total_tokens" in usage else None
            )
        except (TypeError, AttributeError, ValueError):
            self._breaker.record_failure("parse_error")
            return _build_failure(
                self.provider_name,
                self._breaker,
                "parse_error",
                http_status=status,
                duration_ms=duration_ms,
                retried=retried,
            )
        cost = actual_cost_usd(self.provider_name, model, tokens_in, tokens_out)
        try:
            self._spawn_tracker.add(cost)
        except BudgetHardStop:
            pass
        self._breaker.record_success()
        return LiveAdapterResult(
            success=True,
            text=json.dumps(vectors),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost,
            duration_ms=duration_ms,
            http_status=status,
            breaker_state=self._breaker.snapshot().state,
            provider=self.provider_name,
            retry_count=1 if retried else 0,
        )


__all__ = ["OpenAILiveAdapter"]
