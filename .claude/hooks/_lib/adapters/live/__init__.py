"""Live adapter package — ADR-040 contract surface.

Two generations of API live in this package:

1. **Wave 2 (current — ADR-040)**: typed adapter classes per provider,
   each returning a frozen :class:`LiveAdapterResult`. Adapters NEVER
   raise for network conditions; the typed result carries the
   ``failure_mode`` enum string. Activation gated per-provider via
   ``CEO_LIVE_<PROVIDER>=1`` env vars.

2. **Wave 1 (legacy — Sprint 11)**: single :func:`invoke` entrypoint
   raising :class:`LiveAdapterError` subclasses. Kept for Sprint-11
   call sites and the existing ``test_live_adapters.py`` regression
   suite. New code SHOULD use the Wave 2 classes — they integrate the
   breaker, cost tracker, and audit emission natively.

Default posture (per ADR-040 §6): every provider DISABLED. Enabling
requires both ``CEO_LIVE_<PROVIDER>=1`` env AND a non-empty credential
env var (except ``local`` which has no credential).

The global kill-switch ``CEO_SOTA_DISABLE=1`` short-circuits every
provider in this package via the activation check.
"""

from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Wave 2 (ADR-040) — typed adapters
# ---------------------------------------------------------------------------

from ._breaker import BreakerSnapshot, BreakerState, CircuitBreaker
from ._cost import (
    BudgetHardStop,
    PlanCostTracker,
    SpawnCostSnapshot,
    SpawnCostTracker,
    actual_cost_usd,
    estimate_cost_usd,
)
from ._policy import (
    ClaudeLivePolicy,
    GeminiLivePolicy,
    LiveCallPolicy,
    LocalLivePolicy,
    OpenAILivePolicy,
    default_policy,
)
from ._result import BREAKER_STATES, FAILURE_MODES, LiveAdapterResult
from ._transport import LiveTransport, TransportFailure, TransportResponse

# Provider adapter classes (import after the helpers above to avoid cycles).
from .claude import ClaudeLiveAdapter
from .gemini import GeminiLiveAdapter
from .local import LocalLiveAdapter
from .openai import OpenAILiveAdapter


# ---------------------------------------------------------------------------
# Wave 1 (legacy, Sprint 11) — preserved verbatim for back-compat.
#
# These exception classes + the ``invoke()`` function are pre-existing
# call-sites' contract. We keep them inline so the legacy
# ``test_live_adapters.py`` regression suite stays green while new code
# migrates to the Wave 2 typed result surface.
# ---------------------------------------------------------------------------


DEFAULT_TIMEOUT = 60.0

_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
_OPENAI_URL = "https://api.openai.com/v1/chat/completions"
_GEMINI_URL_TMPL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_LOCAL_URL = "http://localhost:11434/api/chat"


class LiveAdapterError(Exception):
    """Base for every Wave-1 live-adapter failure."""


class LiveAdaptersDisabled(LiveAdapterError):
    """Raised by Wave-1 :func:`invoke` when ``CEO_LIVE_ADAPTERS != 1``."""


class LiveAdapterAuthError(LiveAdapterError):
    """API key missing or rejected."""


class LiveAdapterHTTPError(LiveAdapterError):
    """Non-2xx HTTP response. ``status`` attribute holds the code."""

    def __init__(self, message: str, status: int) -> None:
        super().__init__(message)
        self.status = status


class LiveAdapterTimeoutError(LiveAdapterError):
    """Request exceeded ``timeout`` seconds."""


class LiveAdapterParseError(LiveAdapterError):
    """Response JSON did not match the expected provider shape."""


def _wave1_timeout() -> float:
    raw = os.environ.get("CEO_LIVE_TIMEOUT")
    if raw:
        try:
            return float(raw)
        except ValueError:
            pass
    return DEFAULT_TIMEOUT


def _wave1_assert_enabled() -> None:
    if os.environ.get("CEO_LIVE_ADAPTERS") != "1":
        raise LiveAdaptersDisabled(
            "CEO_LIVE_ADAPTERS=1 required to invoke live providers (default off to prevent accidental spend)"
        )


def _wave1_post_json(
    url: str, body: Dict[str, Any], headers: Dict[str, str], timeout: float
) -> Dict[str, Any]:
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            detail = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:  # pragma: no cover
            detail = ""
        if status in (401, 403):
            raise LiveAdapterAuthError(f"auth rejected ({status}): {detail}") from None
        raise LiveAdapterHTTPError(f"HTTP {status}: {detail}", status=status) from None
    except urllib.error.URLError as e:
        msg = str(getattr(e, "reason", e))
        if "timed out" in msg.lower() or isinstance(getattr(e, "reason", None), socket.timeout):
            raise LiveAdapterTimeoutError(f"request timeout after {timeout}s: {msg}") from None
        raise LiveAdapterHTTPError(f"network error: {msg}", status=0) from None
    except socket.timeout as e:
        raise LiveAdapterTimeoutError(f"request timeout after {timeout}s: {e}") from None
    except TimeoutError as e:
        raise LiveAdapterTimeoutError(f"request timeout: {e}") from None
    try:
        return json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise LiveAdapterParseError(f"invalid JSON from provider: {e}") from None


def _wave1_invoke_anthropic(
    messages: List[Dict[str, Any]], model: str, url: str, timeout: float, **kwargs: Any
) -> Dict[str, Any]:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise LiveAdapterAuthError("ANTHROPIC_API_KEY missing in env")
    body: Dict[str, Any] = {
        "model": model,
        "max_tokens": int(kwargs.get("max_tokens", 1024)),
        "messages": messages,
    }
    if kwargs.get("system"):
        body["system"] = kwargs["system"]
    if kwargs.get("temperature") is not None:
        body["temperature"] = float(kwargs["temperature"])
    headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
    resp = _wave1_post_json(url, body, headers, timeout)
    try:
        content_blocks = resp.get("content") or []
        text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
        usage = resp.get("usage") or {}
        return {
            "content": text,
            "tokens_in": usage.get("input_tokens"),
            "tokens_out": usage.get("output_tokens"),
            "model": resp.get("model") or model,
            "provider": "anthropic",
            "stop_reason": resp.get("stop_reason"),
        }
    except (TypeError, AttributeError) as e:
        raise LiveAdapterParseError(f"unexpected Anthropic shape: {e}") from None


def _wave1_invoke_openai(
    messages: List[Dict[str, Any]], model: str, url: str, timeout: float, **kwargs: Any
) -> Dict[str, Any]:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise LiveAdapterAuthError("OPENAI_API_KEY missing in env")
    body: Dict[str, Any] = {"model": model, "messages": messages}
    if kwargs.get("max_tokens") is not None:
        body["max_tokens"] = int(kwargs["max_tokens"])
    if kwargs.get("temperature") is not None:
        body["temperature"] = float(kwargs["temperature"])
    headers = {"Authorization": f"Bearer {key}"}
    resp = _wave1_post_json(url, body, headers, timeout)
    try:
        choice = (resp.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        text = message.get("content") or ""
        usage = resp.get("usage") or {}
        return {
            "content": text,
            "tokens_in": usage.get("prompt_tokens"),
            "tokens_out": usage.get("completion_tokens"),
            "model": resp.get("model") or model,
            "provider": "openai",
            "stop_reason": choice.get("finish_reason"),
        }
    except (TypeError, AttributeError) as e:
        raise LiveAdapterParseError(f"unexpected OpenAI shape: {e}") from None


def _wave1_invoke_gemini(
    messages: List[Dict[str, Any]], model: str, url_tmpl: str, timeout: float, **kwargs: Any
) -> Dict[str, Any]:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise LiveAdapterAuthError("GEMINI_API_KEY missing in env")
    contents: List[Dict[str, Any]] = []
    for m in messages:
        role = m.get("role", "user")
        if role == "system":
            continue
        contents.append({
            "role": "user" if role in ("user", "human") else "model",
            "parts": [{"text": str(m.get("content", ""))}],
        })
    body: Dict[str, Any] = {"contents": contents}
    sys_msg = next((m.get("content", "") for m in messages if m.get("role") == "system"), None)
    if sys_msg:
        body["system_instruction"] = {"parts": [{"text": str(sys_msg)}]}
    if kwargs.get("temperature") is not None:
        body.setdefault("generationConfig", {})["temperature"] = float(kwargs["temperature"])
    if kwargs.get("max_tokens") is not None:
        body.setdefault("generationConfig", {})["maxOutputTokens"] = int(kwargs["max_tokens"])
    headers = {"x-goog-api-key": key}
    url = url_tmpl.format(model=model)
    resp = _wave1_post_json(url, body, headers, timeout)
    try:
        candidates = resp.get("candidates") or []
        if not candidates:
            raise LiveAdapterParseError("gemini returned no candidates")
        first = candidates[0]
        parts = (first.get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts if "text" in p)
        usage = resp.get("usageMetadata") or {}
        return {
            "content": text,
            "tokens_in": usage.get("promptTokenCount"),
            "tokens_out": usage.get("candidatesTokenCount"),
            "model": model,
            "provider": "gemini",
            "stop_reason": first.get("finishReason"),
        }
    except (TypeError, AttributeError) as e:
        raise LiveAdapterParseError(f"unexpected Gemini shape: {e}") from None


def _wave1_invoke_local(
    messages: List[Dict[str, Any]], model: str, url: str, timeout: float, **kwargs: Any
) -> Dict[str, Any]:
    body: Dict[str, Any] = {"model": model, "messages": messages, "stream": False}
    opts: Dict[str, Any] = {}
    if kwargs.get("temperature") is not None:
        opts["temperature"] = float(kwargs["temperature"])
    if kwargs.get("max_tokens") is not None:
        opts["num_predict"] = int(kwargs["max_tokens"])
    if opts:
        body["options"] = opts
    resp = _wave1_post_json(url, body, {}, timeout)
    try:
        message = resp.get("message") or {}
        text = message.get("content") or ""
        return {
            "content": text,
            "tokens_in": resp.get("prompt_eval_count"),
            "tokens_out": resp.get("eval_count"),
            "model": resp.get("model") or model,
            "provider": "local",
            "stop_reason": "stop" if resp.get("done") else None,
        }
    except (TypeError, AttributeError) as e:
        raise LiveAdapterParseError(f"unexpected Ollama shape: {e}") from None


_WAVE1_PROVIDER_DEFAULTS = {
    "anthropic": ("claude-sonnet-4-6", _ANTHROPIC_URL, _wave1_invoke_anthropic),
    "openai": ("gpt-4o", _OPENAI_URL, _wave1_invoke_openai),
    "gemini": ("gemini-2.5-flash", _GEMINI_URL_TMPL, _wave1_invoke_gemini),
    "local": ("llama3", _LOCAL_URL, _wave1_invoke_local),
}


def invoke(
    messages: List[Dict[str, Any]],
    *,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    timeout: Optional[float] = None,
    endpoint: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Wave-1 dispatch: invoke a live LLM provider with the normalized envelope.

    See module docstring; new code SHOULD use the Wave-2 adapter classes
    (:class:`ClaudeLiveAdapter`, etc.) which return typed
    :class:`LiveAdapterResult` envelopes instead of raising.
    """
    _wave1_assert_enabled()
    prov = (provider or os.environ.get("CEO_LIVE_PROVIDER") or "anthropic").lower()
    if prov not in _WAVE1_PROVIDER_DEFAULTS:
        raise LiveAdapterError(
            f"unknown provider: {prov!r}; one of {sorted(_WAVE1_PROVIDER_DEFAULTS)}"
        )
    default_model, default_url, invoker = _WAVE1_PROVIDER_DEFAULTS[prov]
    mdl = model or os.environ.get(f"CEO_LIVE_{prov.upper()}_MODEL") or default_model
    url = endpoint or default_url
    t = timeout if timeout is not None else _wave1_timeout()
    if prov == "gemini":
        return invoker(messages=messages, model=mdl, url_tmpl=url, timeout=t, **kwargs)
    return invoker(messages=messages, model=mdl, url=url, timeout=t, **kwargs)


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

__all__ = [
    # Wave 2 — typed adapter surface (preferred)
    "LiveAdapterResult",
    "FAILURE_MODES",
    "BREAKER_STATES",
    "LiveCallPolicy",
    "ClaudeLivePolicy",
    "GeminiLivePolicy",
    "OpenAILivePolicy",
    "LocalLivePolicy",
    "default_policy",
    "CircuitBreaker",
    "BreakerState",
    "BreakerSnapshot",
    "LiveTransport",
    "TransportResponse",
    "TransportFailure",
    "estimate_cost_usd",
    "actual_cost_usd",
    "BudgetHardStop",
    "SpawnCostTracker",
    "SpawnCostSnapshot",
    "PlanCostTracker",
    "ClaudeLiveAdapter",
    "GeminiLiveAdapter",
    "OpenAILiveAdapter",
    "LocalLiveAdapter",
    # Wave 1 — legacy contract (preserved for back-compat)
    "invoke",
    "LiveAdapterError",
    "LiveAdaptersDisabled",
    "LiveAdapterAuthError",
    "LiveAdapterHTTPError",
    "LiveAdapterTimeoutError",
    "LiveAdapterParseError",
    "DEFAULT_TIMEOUT",
]
