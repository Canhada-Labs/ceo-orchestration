"""Google Gemini live adapter — ADR-040 §6.

Targets ``https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent``.

The API key flows via ``?key=<GOOGLE_API_KEY>`` query string. The
transport layer redacts the URL query before audit emission so the
key never lands in logs. (The header alternative ``x-goog-api-key``
is also accepted by Google but the documented public convention is
the query string.)

Activation: ``CEO_LIVE_GEMINI=1`` AND ``GOOGLE_API_KEY`` non-empty.
"""

from __future__ import annotations

import json
import os
import time as _time
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from ._breaker import CircuitBreaker
from ._cost import (
    BudgetHardStop,
    SpawnCostTracker,
    actual_cost_usd,
    estimate_cost_usd,
)
from ._policy import GeminiLivePolicy, LiveCallPolicy
from ._result import LiveAdapterResult
from ._transport import LiveTransport, audit_emit_dispatch
from .claude import _build_failure  # shared helper


_BASE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)


class GeminiLiveAdapter:
    """Live adapter for Google's Gemini Generative Language API."""

    provider_name: str = "google"

    def __init__(
        self,
        policy: Optional[LiveCallPolicy] = None,
        *,
        spawn_tracker: Optional[SpawnCostTracker] = None,
        breaker: Optional[CircuitBreaker] = None,
        transport: Optional[LiveTransport] = None,
        base_url: Optional[str] = None,
    ) -> None:
        if policy is not None and policy.provider != "gemini":
            raise ValueError(
                f"GeminiLiveAdapter requires policy.provider='gemini', got {policy.provider!r}"
            )
        self.policy: LiveCallPolicy = policy or GeminiLivePolicy()
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
        self._base_url = base_url or _BASE_URL

    def _activation_check(self) -> Optional[str]:
        if os.environ.get("CEO_SOTA_DISABLE") == "1":
            return "sota_disabled"
        if os.environ.get(self.policy.activation_env_var) != "1":
            return "activation_off"
        if not os.environ.get(self.policy.credential_env_var):
            return "missing_credential"
        return None

    def call(
        self,
        *,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int = 1024,
    ) -> LiveAdapterResult:
        """Issue one Gemini generateContent call.

        Translates the canonical ``messages`` list into Gemini's
        ``{"contents": [{"role":"user","parts":[{"text":...}]}]}`` shape.
        System messages flow via the dedicated ``system_instruction`` field.
        """
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

        api_key = os.environ.get(self.policy.credential_env_var) or ""
        # Build URL with model in path + key in query (Google convention).
        url = self._base_url.format(model=quote(model, safe="")) + "?key=" + quote(api_key, safe="")

        contents: List[Dict[str, Any]] = []
        system_text: Optional[str] = None
        for m in messages:
            role = m.get("role", "user")
            text = str(m.get("content", ""))
            if role == "system":
                system_text = (system_text or "") + ("\n" if system_text else "") + text
                continue
            contents.append(
                {
                    "role": "user" if role in ("user", "human") else "model",
                    "parts": [{"text": text}],
                }
            )
        body: Dict[str, Any] = {"contents": contents}
        if system_text:
            body["system_instruction"] = {"parts": [{"text": system_text}]}
        body["generationConfig"] = {"maxOutputTokens": int(max_tokens)}

        # Header-based auth omitted intentionally — the URL query carries
        # the key per Google's public convention. Transport scrubs query.
        headers = {"Content-Type": "application/json"}

        response, failure = self._transport.post_json(url, headers, body)

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
            text=None,
            tokens_in=None,
            tokens_out=None,
            cost_usd=None,
            duration_ms=failure.duration_ms,
            failure_mode=failure.failure_mode,
            http_status=failure.http_status,
            breaker_state=self._breaker.snapshot().state,
            provider=self.provider_name,
            retry_count=1 if failure.retried else 0,
            fixture_fallback=False,
        )

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
            candidates = payload.get("candidates") or []
            if not candidates:
                # Empty candidates is a parse-shaped issue (no usable content)
                self._breaker.record_failure("parse_error")
                return _build_failure(
                    self.provider_name,
                    self._breaker,
                    "parse_error",
                    http_status=status,
                    duration_ms=duration_ms,
                    retried=retried,
                )
            first = candidates[0] or {}
            parts = ((first.get("content") or {}).get("parts") or [])
            text = "".join(p.get("text", "") for p in parts if isinstance(p, dict) and "text" in p)
            usage = payload.get("usageMetadata") or {}
            tokens_in = (
                int(usage["promptTokenCount"]) if "promptTokenCount" in usage else None
            )
            tokens_out = (
                int(usage["candidatesTokenCount"])
                if "candidatesTokenCount" in usage
                else None
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
            failure_mode=None,
            http_status=status,
            breaker_state=self._breaker.snapshot().state,
            provider=self.provider_name,
            retry_count=1 if retried else 0,
            fixture_fallback=False,
        )


__all__ = ["GeminiLiveAdapter"]
