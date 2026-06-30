"""Local LLM live adapter — ADR-040 §6 (Ollama-compatible).

Targets ``http://localhost:11434/api/chat`` by default (Ollama
convention). Override via ``CEO_LOCAL_URL`` env or constructor arg.

Activation: ``CEO_LIVE_LOCAL=1`` (no credential — local runtimes are
unauthenticated by convention). Cost is always 0.0 — Ollama / llama.cpp
incur compute, not API spend.

The breaker still applies because a runaway local model can hang the
adapter just as effectively as a remote 502; ADR-037 chaos coverage
exercises the same modes.
"""

from __future__ import annotations

import json
import os
import time as _time
from typing import Any, Dict, List, Optional

from ._breaker import CircuitBreaker
from ._cost import SpawnCostTracker
from ._policy import LiveCallPolicy, LocalLivePolicy
from ._result import LiveAdapterResult
from ._transport import LiveTransport, audit_emit_dispatch
from .claude import _build_failure  # shared helper


_DEFAULT_URL = "http://localhost:11434/api/chat"


class LocalLiveAdapter:
    """Live adapter for Ollama-compatible local LLM runtimes."""

    provider_name: str = "local"

    def __init__(
        self,
        policy: Optional[LiveCallPolicy] = None,
        *,
        spawn_tracker: Optional[SpawnCostTracker] = None,
        breaker: Optional[CircuitBreaker] = None,
        transport: Optional[LiveTransport] = None,
        url: Optional[str] = None,
    ) -> None:
        if policy is not None and policy.provider != "local":
            raise ValueError(
                f"LocalLiveAdapter requires policy.provider='local', got {policy.provider!r}"
            )
        self.policy: LiveCallPolicy = policy or LocalLivePolicy()
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
        self._url = url or os.environ.get("CEO_LOCAL_URL") or _DEFAULT_URL

    def _activation_check(self) -> Optional[str]:
        if os.environ.get("CEO_SOTA_DISABLE") == "1":
            return "sota_disabled"
        if os.environ.get(self.policy.activation_env_var) != "1":
            return "activation_off"
        # No credential check — local doesn't auth.
        return None

    def call(
        self,
        *,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int = 1024,
    ) -> LiveAdapterResult:
        """Issue one Ollama /api/chat call."""
        start = _time.monotonic()

        gate = self._activation_check()
        if gate is not None:
            return self._fixture_fallback(start_monotonic=start)

        # Cost ceiling is moot for local (always $0.00) but the breaker
        # still gates.
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
            "stream": False,
            "options": {"num_predict": int(max_tokens)},
        }
        # No auth headers; some Ollama deployments require Content-Type.
        headers = {"Content-Type": "application/json"}

        response, failure = self._transport.post_json(self._url, headers, body)

        if response is not None:
            return self._on_response(
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

    def _fixture_fallback(self, *, start_monotonic: float) -> LiveAdapterResult:
        # Local has no missing-credential mode; activation-off is benign.
        elapsed_ms = int((_time.monotonic() - start_monotonic) * 1000)
        return LiveAdapterResult(
            success=True,
            duration_ms=elapsed_ms,
            cost_usd=0.0,
            breaker_state=self._breaker.snapshot().state,
            provider=self.provider_name,
            fixture_fallback=True,
        )

    def _on_response(
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
            message = payload.get("message") or {}
            text = message.get("content") or ""
            tokens_in = (
                int(payload["prompt_eval_count"]) if "prompt_eval_count" in payload else None
            )
            tokens_out = int(payload["eval_count"]) if "eval_count" in payload else None
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
        # Cost is 0.0 by construction (ADR-033 §pricing-policy).
        self._breaker.record_success()
        return LiveAdapterResult(
            success=True,
            text=text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=0.0,
            duration_ms=duration_ms,
            http_status=status,
            breaker_state=self._breaker.snapshot().state,
            provider=self.provider_name,
            retry_count=1 if retried else 0,
        )


__all__ = ["LocalLiveAdapter"]
