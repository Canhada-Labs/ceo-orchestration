"""Live adapter smoke — gated on ``CEO_LIVE_ADAPTERS=1``.

Per ADR-040 §6 + PLAN-012 D3.6: this test fires a minimal chat
completion against each enabled provider and asserts the call
completed with non-empty text within the bounded budget.

When ``CEO_LIVE_ADAPTERS=1`` is NOT set the entire module is skipped
(``pytest.skip``) so CI stays green without credentials. Per-provider
flags follow ADR-040 §6 — a provider is only exercised when its
``CEO_LIVE_<PROVIDER>=1`` flag AND the credential env var are present.

Acceptance gates (per provider):

- ``success=True``
- non-empty ``text``
- ``cost_usd`` strictly less than $0.01 per call (basic sanity bound)
- ``duration_ms`` strictly less than 10_000ms (10 s wall-clock)
- ``failure_mode`` is ``None``
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Make `.claude/hooks/` importable so we can use the live adapter classes.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))


# Module-level skip when umbrella flag is off.
pytestmark = pytest.mark.skipif(
    os.environ.get("CEO_LIVE_ADAPTERS") != "1",
    reason="CEO_LIVE_ADAPTERS=1 required for live smoke (set with credentials provisioned)",
)


_HELLO_MSG = [{"role": "user", "content": "Reply with the single word: hello"}]


def _adapter_module():
    """Lazy import — kept lazy so the module-level skip fires first."""
    from _lib.adapters.live import (  # noqa: F401
        ClaudeLiveAdapter,
        GeminiLiveAdapter,
        LocalLiveAdapter,
        OpenAILiveAdapter,
    )
    return {
        "claude": ClaudeLiveAdapter,
        "gemini": GeminiLiveAdapter,
        "openai": OpenAILiveAdapter,
        "local": LocalLiveAdapter,
    }


def _smoke_provider(name: str, model: str, env_flag: str, credential_env: str):
    if os.environ.get(env_flag) != "1":
        pytest.skip(f"{env_flag}!=1; provider {name} smoke skipped")
    if credential_env and not os.environ.get(credential_env):
        pytest.skip(f"{credential_env} unset; provider {name} smoke skipped")
    cls = _adapter_module()[name]
    adapter = cls()
    result = adapter.call(messages=_HELLO_MSG, model=model, max_tokens=20)
    assert result.success is True, (
        f"{name} smoke failed: failure_mode={result.failure_mode} "
        f"http_status={result.http_status} duration_ms={result.duration_ms}"
    )
    assert result.text and result.text.strip(), f"{name} smoke returned empty text"
    assert result.duration_ms < 10_000, f"{name} smoke exceeded 10s wall-clock"
    if result.cost_usd is not None:
        assert result.cost_usd < 0.01, f"{name} smoke exceeded $0.01 cost ceiling"
    assert result.failure_mode is None
    assert result.fixture_fallback is False


def test_smoke_claude():
    _smoke_provider(
        "claude",
        os.environ.get("CEO_LIVE_CLAUDE_MODEL", "claude-haiku-4-5"),
        "CEO_LIVE_CLAUDE",
        "ANTHROPIC_API_KEY",
    )


def test_smoke_openai():
    _smoke_provider(
        "openai",
        os.environ.get("CEO_LIVE_OPENAI_MODEL", "gpt-4o-mini"),
        "CEO_LIVE_OPENAI",
        "OPENAI_API_KEY",
    )


def test_smoke_gemini():
    _smoke_provider(
        "gemini",
        os.environ.get("CEO_LIVE_GEMINI_MODEL", "gemini-2.5-flash"),
        "CEO_LIVE_GEMINI",
        "GOOGLE_API_KEY",
    )


def test_smoke_local():
    # Local has no credential — only the activation flag.
    _smoke_provider(
        "local",
        os.environ.get("CEO_LIVE_LOCAL_MODEL", "llama3"),
        "CEO_LIVE_LOCAL",
        "",
    )
