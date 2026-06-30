"""LiveCallPolicy — frozen dataclass codifying ADR-040 §1-§5.

Per-call timeout, retry, breaker, cost ceiling, credential lifecycle
constants live HERE. Adapters consume an instance; they never hardcode
numbers. Tests patch via ``replace(policy, ...)`` for chaos coverage.

Validation runs at construction (``__post_init__``) per
``SPEC/v1/live-adapters-policy.schema.md §2``; an invalid policy raises
``ValueError`` so an adapter cannot silently ship with bad numbers.

Provider subclasses (:class:`ClaudeLivePolicy`, :class:`GeminiLivePolicy`,
:class:`OpenAILivePolicy`, :class:`LocalLivePolicy`) override only the
provider-specific scope / activation / credential fields. Numeric
defaults are identical across providers — see ADR-040 §1 rationale.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Numeric defaults (ADR-040 §1, §3, §4)
# ---------------------------------------------------------------------------

_DEFAULT_CONNECT_TIMEOUT_MS = 2500
_DEFAULT_READ_TIMEOUT_MS = 8000
_DEFAULT_MAX_RETRIES = 1
_DEFAULT_BACKOFF_INITIAL_MS = 250
_DEFAULT_BACKOFF_MAX_MS = 1000
_DEFAULT_BACKOFF_JITTER_PCT = 100
_DEFAULT_BREAKER_THRESHOLD = 5
_DEFAULT_BREAKER_WINDOW_S = 30
_DEFAULT_BREAKER_HALF_OPEN_S = 60

_DEFAULT_MAX_SPEND_USD_PER_SPAWN = 0.50
_DEFAULT_MAX_SPEND_USD_PER_PLAN_5MIN = 2.00
_DEFAULT_MAX_DEBATE_ROUNDS = 5

_DEFAULT_CRED_MAX_AGE_DAYS = 90
_DEFAULT_CRED_WARN_AGE_DAYS = 75

# Per ADR-040 §4 — provider-prefix detection patterns.
_DEFAULT_LEAK_PATTERNS: List[str] = [
    r"sk-ant-[A-Za-z0-9_\-]{8,}",
    r"AIza[A-Za-z0-9_\-]{35}",
    r"sk-proj-[A-Za-z0-9_\-]{8,}",
    r"sk-[A-Za-z0-9]{32,}",
    r"AKIA[A-Z0-9]{16}",
]

_VALID_SCOPES = ("chat_only", "embeddings_only", "chat_and_embeddings")
_VALID_PROVIDERS = ("claude", "gemini", "openai", "local")
_ACTIVATION_RE = re.compile(r"^CEO_LIVE_[A-Z_]+$")


# ---------------------------------------------------------------------------
# Base policy
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LiveCallPolicy:
    """Per-call policy enforced at the adapter layer.

    The defaults below match ADR-040 numerically. Per-provider
    subclasses override only the §5 fields (``provider``, ``scope``,
    ``credential_env_var``, ``activation_env_var``,
    ``data_retention_opt_out_header``).

    Validation rules from SPEC §2 are enforced in :meth:`__post_init__`:

    1. ``connect_timeout_ms > 0`` and ``read_timeout_ms > connect_timeout_ms``
    2. ``max_retries <= 3``
    3. ``backoff_max_ms >= backoff_initial_ms`` and ``<= 5000``
    4. ``breaker_threshold >= 2``
    5. ``max_spend_usd_per_spawn > 0`` and
       ``<= max_spend_usd_per_plan_5min``
    6. ``credential_warn_age_days < credential_max_age_days``
    7. ``scope`` ∈ enum
    8. OpenAI + embeddings → opt-out header non-None
    9. ``leak_detection_patterns`` non-empty + each compiles
    10. ``activation_env_var`` matches ``^CEO_LIVE_[A-Z_]+$``
    """

    # §1 — timeout + retry + breaker
    connect_timeout_ms: int = _DEFAULT_CONNECT_TIMEOUT_MS
    read_timeout_ms: int = _DEFAULT_READ_TIMEOUT_MS
    max_retries: int = _DEFAULT_MAX_RETRIES
    backoff_initial_ms: int = _DEFAULT_BACKOFF_INITIAL_MS
    backoff_max_ms: int = _DEFAULT_BACKOFF_MAX_MS
    backoff_jitter_pct: int = _DEFAULT_BACKOFF_JITTER_PCT
    breaker_threshold: int = _DEFAULT_BREAKER_THRESHOLD
    breaker_window_s: int = _DEFAULT_BREAKER_WINDOW_S
    breaker_half_open_s: int = _DEFAULT_BREAKER_HALF_OPEN_S

    # §3 — cost ceiling (USD)
    max_spend_usd_per_spawn: float = _DEFAULT_MAX_SPEND_USD_PER_SPAWN
    max_spend_usd_per_plan_5min: float = _DEFAULT_MAX_SPEND_USD_PER_PLAN_5MIN
    max_debate_rounds: int = _DEFAULT_MAX_DEBATE_ROUNDS

    # §4 — credential lifecycle
    credential_env_var: str = "ANTHROPIC_API_KEY"
    credential_max_age_days: int = _DEFAULT_CRED_MAX_AGE_DAYS
    credential_warn_age_days: int = _DEFAULT_CRED_WARN_AGE_DAYS
    leak_detection_patterns: List[str] = field(
        default_factory=lambda: list(_DEFAULT_LEAK_PATTERNS)
    )

    # §5 — provider-side scope (Security S1)
    scope: str = "chat_only"
    data_retention_opt_out: bool = False
    data_retention_opt_out_header: Optional[str] = None

    # §6 — activation
    provider: str = "claude"
    activation_env_var: str = "CEO_LIVE_CLAUDE"
    fixture_fallback_enabled: bool = True

    def __post_init__(self) -> None:
        # Rule 1
        if self.connect_timeout_ms <= 0:
            raise ValueError(
                f"connect_timeout_ms must be >0, got {self.connect_timeout_ms}"
            )
        if self.read_timeout_ms <= self.connect_timeout_ms:
            raise ValueError(
                "read_timeout_ms must exceed connect_timeout_ms ("
                f"{self.read_timeout_ms} <= {self.connect_timeout_ms})"
            )
        # Rule 2
        if not (0 <= self.max_retries <= 3):
            raise ValueError(
                f"max_retries must be in [0,3], got {self.max_retries}"
            )
        # Rule 3
        if self.backoff_max_ms < self.backoff_initial_ms:
            raise ValueError(
                "backoff_max_ms < backoff_initial_ms is invalid"
            )
        if self.backoff_max_ms > 5000:
            raise ValueError(
                f"backoff_max_ms exceeds 5000ms cap, got {self.backoff_max_ms}"
            )
        if not (0 <= self.backoff_jitter_pct <= 100):
            raise ValueError(
                f"backoff_jitter_pct must be in [0,100], got {self.backoff_jitter_pct}"
            )
        # Rule 4
        if self.breaker_threshold < 2:
            raise ValueError(
                f"breaker_threshold must be >=2, got {self.breaker_threshold}"
            )
        if not (5 <= self.breaker_window_s <= 300):
            raise ValueError(
                f"breaker_window_s out of range [5,300], got {self.breaker_window_s}"
            )
        if not (10 <= self.breaker_half_open_s <= 600):
            raise ValueError(
                f"breaker_half_open_s out of range [10,600], got {self.breaker_half_open_s}"
            )
        # Rule 5
        if self.max_spend_usd_per_spawn <= 0:
            raise ValueError(
                f"max_spend_usd_per_spawn must be >0, got {self.max_spend_usd_per_spawn}"
            )
        if self.max_spend_usd_per_spawn > self.max_spend_usd_per_plan_5min:
            raise ValueError(
                "max_spend_usd_per_spawn must be <= max_spend_usd_per_plan_5min"
            )
        if not (1 <= self.max_debate_rounds <= 20):
            raise ValueError(
                f"max_debate_rounds out of range [1,20], got {self.max_debate_rounds}"
            )
        # Rule 6
        if self.credential_warn_age_days >= self.credential_max_age_days:
            raise ValueError(
                "credential_warn_age_days must be strictly < credential_max_age_days"
            )
        if not (7 <= self.credential_max_age_days <= 365):
            raise ValueError(
                f"credential_max_age_days out of range [7,365], got {self.credential_max_age_days}"
            )
        # Rule 7
        if self.scope not in _VALID_SCOPES:
            raise ValueError(
                f"scope must be one of {_VALID_SCOPES}, got {self.scope!r}"
            )
        # Rule 8
        if (
            self.provider == "openai"
            and self.scope in ("embeddings_only", "chat_and_embeddings")
        ):
            if not self.data_retention_opt_out:
                raise ValueError(
                    "OpenAI embeddings scope requires data_retention_opt_out=True"
                )
            if self.data_retention_opt_out_header is None:
                raise ValueError(
                    "OpenAI embeddings scope requires data_retention_opt_out_header"
                )
        # Rule 9
        if not self.leak_detection_patterns:
            raise ValueError("leak_detection_patterns must be non-empty")
        for pat in self.leak_detection_patterns:
            try:
                re.compile(pat)
            except re.error as e:  # pragma: no cover - patterns are static
                raise ValueError(
                    f"invalid leak_detection_patterns regex {pat!r}: {e}"
                ) from None
        # Rule 10
        if not _ACTIVATION_RE.match(self.activation_env_var):
            raise ValueError(
                f"activation_env_var must match ^CEO_LIVE_[A-Z_]+$, got {self.activation_env_var!r}"
            )
        # Provider whitelist
        if self.provider not in _VALID_PROVIDERS:
            raise ValueError(
                f"provider must be one of {_VALID_PROVIDERS}, got {self.provider!r}"
            )


# ---------------------------------------------------------------------------
# Per-provider subclasses (immutable dataclass field overrides)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClaudeLivePolicy(LiveCallPolicy):
    provider: str = "claude"
    activation_env_var: str = "CEO_LIVE_CLAUDE"
    credential_env_var: str = "ANTHROPIC_API_KEY"
    scope: str = "chat_only"
    # Anthropic has no REST opt-out header (operator attests via dashboard)
    data_retention_opt_out: bool = False
    data_retention_opt_out_header: Optional[str] = None


@dataclass(frozen=True)
class GeminiLivePolicy(LiveCallPolicy):
    provider: str = "gemini"
    activation_env_var: str = "CEO_LIVE_GEMINI"
    credential_env_var: str = "GOOGLE_API_KEY"
    scope: str = "chat_only"
    # Google has no REST opt-out header in 2026-Q2 — same operator attestation
    data_retention_opt_out: bool = False
    data_retention_opt_out_header: Optional[str] = None


@dataclass(frozen=True)
class OpenAILivePolicy(LiveCallPolicy):
    provider: str = "openai"
    activation_env_var: str = "CEO_LIVE_OPENAI"
    credential_env_var: str = "OPENAI_API_KEY"
    scope: str = "chat_only"
    data_retention_opt_out: bool = True
    # Per ADR-040 §5 — exact header name confirmed against 2026-Q2 OpenAI policy
    # docs at provisioning time. Best-effort name; verify on flip.
    data_retention_opt_out_header: Optional[str] = "OpenAI-Data-Retention: opt_out"


@dataclass(frozen=True)
class LocalLivePolicy(LiveCallPolicy):
    provider: str = "local"
    activation_env_var: str = "CEO_LIVE_LOCAL"
    # No credential needed — we still set a sentinel name so SPEC field is non-empty
    credential_env_var: str = "CEO_LOCAL_NO_CREDENTIAL"
    scope: str = "chat_only"
    data_retention_opt_out: bool = False
    data_retention_opt_out_header: Optional[str] = None
    # Local runtimes are typically fast — no need to relax timeouts but cost
    # ceiling is moot. Still enforced for parity (always 0.00 actual).


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


_POLICY_FACTORY: Dict[str, type] = {
    "claude": ClaudeLivePolicy,
    "anthropic": ClaudeLivePolicy,  # alias accepted for convenience
    "gemini": GeminiLivePolicy,
    "google": GeminiLivePolicy,  # alias
    "openai": OpenAILivePolicy,
    "local": LocalLivePolicy,
}


def default_policy(provider: str) -> LiveCallPolicy:
    """Return the per-provider default policy.

    Args:
        provider: ``"claude"`` (or ``"anthropic"``), ``"gemini"`` (or
            ``"google"``), ``"openai"``, ``"local"``.

    Raises:
        ValueError: provider not recognised.
    """
    key = provider.lower()
    cls = _POLICY_FACTORY.get(key)
    if cls is None:
        raise ValueError(
            f"unknown provider {provider!r}; expected one of {sorted(set(_POLICY_FACTORY))}"
        )
    return cls()


__all__ = [
    "LiveCallPolicy",
    "ClaudeLivePolicy",
    "GeminiLivePolicy",
    "OpenAILivePolicy",
    "LocalLivePolicy",
    "default_policy",
]
