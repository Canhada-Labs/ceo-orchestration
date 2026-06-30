"""FakeLLMDispatcher — deterministic mock boundary for tournament tests.

QA A1 / C-P0-8 closure. Pattern mirrors `FakeSidecar` from PLAN-041
tests. Every unit + integration test in the tournament suite runs
without live Anthropic API calls.

Live-API tests (if any) MUST be marked `@pytest.mark.slow` and excluded
from the default `pytest -q` run.

Non-conftest module (not under canonical-edit sentinel). Tests import
and instantiate directly:

    from _fake_dispatcher import FakeLLMDispatcher, FakeRateLimitError

    def test_my_runner_behavior():
        dispatcher = FakeLLMDispatcher()
        dispatcher.register_response("opus", "fx-001", "verdict PASS")
        ...
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple


class FakeLLMDispatcherError(Exception):
    """Configurable error class for FakeLLMDispatcher error-mode simulation.

    Subclassing allows tests to distinguish "FakeLLMDispatcher threw because
    we asked it to" vs "real code bug threw unexpectedly".
    """


class FakeRateLimitError(FakeLLMDispatcherError):
    """Simulates Anthropic 429 rate-limit. Should trigger backoff in runner."""


class FakeServerError(FakeLLMDispatcherError):
    """Simulates Anthropic 5xx. Should trigger backoff in runner."""


class FakeTimeoutError(FakeLLMDispatcherError):
    """Simulates per-call timeout. Task marked `errored`, tournament continues."""


@dataclass
class FakeResponse:
    """Canned response for a (model, fixture_id) key.

    Mirrors Anthropic SDK `Message` shape subset needed by the runner.
    """

    content: str
    tokens_in: int
    tokens_out: int
    stop_reason: str = "end_turn"

    def cost_usd(self, in_rate_per_m: float, out_rate_per_m: float) -> float:
        """Compute cost given input/output USD/M-token rates."""
        return (self.tokens_in / 1_000_000) * in_rate_per_m + (
            self.tokens_out / 1_000_000
        ) * out_rate_per_m


@dataclass
class DispatchCall:
    """Record of a single dispatch() invocation, for assertion purposes."""

    model: str
    fixture_id: str
    prompt: str
    max_tokens: int
    seed: Optional[int]
    timestamp: float = field(default_factory=time.monotonic)


class FakeLLMDispatcher:
    """Deterministic mock for Anthropic API dispatch.

    Test code configures via `register_response` + `register_error` +
    `set_latency`. Runner code calls via
    `dispatch(model, fixture_id, prompt, max_tokens, seed)`.

    Thread-safe: internal state guarded by a `threading.RLock` so the
    concurrency-semaphore tests (Round 1 F-PERF2) can spawn multiple
    worker threads against a single dispatcher instance.
    """

    def __init__(self) -> None:
        self._responses: Dict[Tuple[str, str], FakeResponse] = {}
        self._errors: Dict[Tuple[str, str], FakeLLMDispatcherError] = {}
        self._default_response: Optional[FakeResponse] = None
        self._latency_s: float = 0.0
        self._call_log: List[DispatchCall] = []
        self._lock = threading.RLock()

    # --- configuration API (test-code facing) ---

    def register_response(
        self,
        model: str,
        fixture_id: str,
        content: str,
        tokens_in: int = 1000,
        tokens_out: int = 500,
        stop_reason: str = "end_turn",
    ) -> None:
        """Register a canned response for a specific (model, fixture_id) key."""
        with self._lock:
            self._responses[(model, fixture_id)] = FakeResponse(
                content=content,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                stop_reason=stop_reason,
            )

    def register_error(
        self,
        model: str,
        fixture_id: str,
        error: FakeLLMDispatcherError,
    ) -> None:
        """Register a canned error for a specific (model, fixture_id) key.

        When dispatch() hits this key, it raises the error instead of
        returning a response. Used for fail-open + retry-backoff testing.
        """
        with self._lock:
            self._errors[(model, fixture_id)] = error

    def set_default_response(
        self,
        content: str = "OK",
        tokens_in: int = 1000,
        tokens_out: int = 500,
    ) -> None:
        """Set fallback response for any (model, fixture_id) not explicitly registered.

        If neither a registered response nor a default is set, dispatch()
        raises KeyError — this surfaces test-configuration errors loudly
        rather than silently returning None.
        """
        with self._lock:
            self._default_response = FakeResponse(
                content=content,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
            )

    def set_latency(self, seconds: float) -> None:
        """Artificially delay each dispatch() call by `seconds` (timeout testing)."""
        if seconds < 0:
            raise ValueError("latency must be non-negative")
        with self._lock:
            self._latency_s = float(seconds)

    def reset(self) -> None:
        """Clear all registered responses, errors, latency, and call log."""
        with self._lock:
            self._responses.clear()
            self._errors.clear()
            self._default_response = None
            self._latency_s = 0.0
            self._call_log.clear()

    # --- assertion API (test-code facing) ---

    @property
    def call_log(self) -> List[DispatchCall]:
        """Immutable snapshot of all dispatch() calls (in order)."""
        with self._lock:
            return list(self._call_log)

    @property
    def call_count(self) -> int:
        with self._lock:
            return len(self._call_log)

    def calls_for(self, model: str) -> List[DispatchCall]:
        with self._lock:
            return [c for c in self._call_log if c.model == model]

    # --- dispatch API (runner-code facing) ---

    def dispatch(
        self,
        model: str,
        fixture_id: str,
        prompt: str,
        max_tokens: int,
        seed: Optional[int] = None,
    ) -> FakeResponse:
        """Simulate an Anthropic API dispatch.

        Resolution order:
        1. Registered error for this (model, fixture_id) → raise
        2. Registered response for this (model, fixture_id) → return
        3. Default response → return
        4. Raise KeyError (test misconfigured)
        """
        with self._lock:
            # Log every attempt (including those that will raise) for
            # forensic assertion coverage.
            self._call_log.append(
                DispatchCall(
                    model=model,
                    fixture_id=fixture_id,
                    prompt=prompt,
                    max_tokens=max_tokens,
                    seed=seed,
                )
            )
            latency = self._latency_s
            err = self._errors.get((model, fixture_id))
            response = self._responses.get((model, fixture_id))
            default = self._default_response

        if latency > 0:
            time.sleep(latency)

        if err is not None:
            raise err
        if response is not None:
            return response
        if default is not None:
            return default
        raise KeyError(
            f"FakeLLMDispatcher: no response or error configured for "
            f"(model={model!r}, fixture_id={fixture_id!r}). "
            "Test misconfigured — register_response or set_default_response."
        )
