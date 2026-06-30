"""Pre-flight + runtime cost estimation — ADR-040 §3.

Two roles:

1. **Pre-flight estimate** — :func:`estimate_cost_usd` rough-bounds
   the spend of a call BEFORE we hit the wire, so the adapter can
   trip ``budget_hard_stop`` without burning network IO.

2. **Runtime tally** — :func:`actual_cost_usd` uses real provider
   token counts. :class:`SpawnCostTracker` and :class:`PlanCostTracker`
   accumulate spend; both raise :class:`BudgetHardStop` when ceilings
   are crossed.

Pricing source: ``docs/provider-pricing.md`` (parsed once, cached for
the process lifetime). The parser tolerates rows containing ``TBD`` —
they emit ``(input=None, output=None)`` and the cost estimate falls
back to the conservative default ($0.01/1k tokens both directions) so
the budget hard stop still trips on misconfigured rows.

Local provider always returns 0.0 — Ollama / llama.cpp incur compute
not API spend, and ADR-033 §pricing-policy treats them as zero by
construction.

All trackers are thread-safe via :class:`threading.Lock`.
"""

from __future__ import annotations

import os
import re
import threading
import time as _time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Deque, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Pricing parser
# ---------------------------------------------------------------------------


# Conservative fallback when a model row is missing or marked TBD.
# Picked higher than the most expensive shipped 2026-Q2 row to ensure
# the budget guard trips early when pricing is unknown.
_FALLBACK_INPUT_PER_1K = 0.02
_FALLBACK_OUTPUT_PER_1K = 0.10

# Empirical token-density multiplier for a UTF-8 word-split estimate.
# Real tokenizers vary; 1.3× whitespace tokens is the rough upper bound
# we've seen in 2025-Q4 benchmarks. We err on the high side so the
# pre-flight estimate over-counts (safer for budget guard).
_WORD_TO_TOKEN_RATIO = 1.3

# Module-level cache. Cleared by tests via :func:`_reset_pricing_cache`.
_PRICING_CACHE_LOCK = threading.Lock()
_PRICING_CACHE: Optional[Dict[Tuple[str, str], Tuple[Optional[float], Optional[float]]]] = None
_PRICING_CACHE_PATH: Optional[Path] = None


def _pricing_path() -> Path:
    """Resolve the pricing file path; honours ``CEO_PRICING_PATH`` env."""
    env_override = os.environ.get("CEO_PRICING_PATH")
    if env_override:
        return Path(env_override)
    # Resolve relative to repo root: this file lives at
    # .claude/hooks/_lib/adapters/live/_cost.py — six parents up = repo root.
    return Path(__file__).resolve().parents[5] / "docs" / "provider-pricing.md"


_HEADER_RE = re.compile(r"^\s*\|\s*provider\s*\|\s*model\s*\|", re.IGNORECASE)
_ROW_RE = re.compile(r"^\s*\|")


def _parse_pricing_table(text: str) -> Dict[Tuple[str, str], Tuple[Optional[float], Optional[float]]]:
    """Parse the primary pricing table from ``text`` (markdown).

    Returns map of ``(provider_lower, model_lower) → (input_per_1k, output_per_1k)``.
    Rows with ``TBD`` in either cost column become ``(None, None)``.

    The parser scans for the first ``| Provider | Model | Input ... | Output ... |``
    header, skips the divider, then consumes contiguous ``|`` rows.
    """
    out: Dict[Tuple[str, str], Tuple[Optional[float], Optional[float]]] = {}
    lines = text.splitlines()
    in_table = False
    seen_divider = False
    for line in lines:
        if not in_table:
            if _HEADER_RE.match(line):
                in_table = True
                seen_divider = False
            continue
        if not seen_divider:
            # The divider row begins with `|---`; the next row is the first data row
            if line.strip().startswith("|") and "---" in line:
                seen_divider = True
            continue
        if not _ROW_RE.match(line):
            # Table ended (blank line or non-pipe content)
            break
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        provider, model, in_cost, out_cost = cells[0], cells[1], cells[2], cells[3]
        in_v: Optional[float]
        out_v: Optional[float]
        try:
            in_v = float(in_cost) if in_cost.upper() != "TBD" else None
        except ValueError:
            in_v = None
        try:
            out_v = float(out_cost) if out_cost.upper() != "TBD" else None
        except ValueError:
            out_v = None
        out[(provider.lower(), model.lower())] = (in_v, out_v)
    return out


def _load_pricing(*, force: bool = False) -> Dict[Tuple[str, str], Tuple[Optional[float], Optional[float]]]:
    """Return the cached pricing map, loading on first access.

    Args:
        force: ignore cache and reload (test helper).
    """
    global _PRICING_CACHE, _PRICING_CACHE_PATH
    with _PRICING_CACHE_LOCK:
        path = _pricing_path()
        if not force and _PRICING_CACHE is not None and _PRICING_CACHE_PATH == path:
            return _PRICING_CACHE
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            _PRICING_CACHE = {}
            _PRICING_CACHE_PATH = path
            return _PRICING_CACHE
        _PRICING_CACHE = _parse_pricing_table(text)
        _PRICING_CACHE_PATH = path
        return _PRICING_CACHE


def _reset_pricing_cache() -> None:
    """Test helper — drops the module cache."""
    global _PRICING_CACHE, _PRICING_CACHE_PATH
    with _PRICING_CACHE_LOCK:
        _PRICING_CACHE = None
        _PRICING_CACHE_PATH = None


def _provider_aliases(provider: str) -> Tuple[str, ...]:
    """Provider-name aliases used in pricing table rows."""
    p = provider.lower()
    if p in ("anthropic", "claude"):
        return ("anthropic", "claude")
    if p in ("google", "gemini"):
        return ("google", "gemini")
    if p == "openai":
        return ("openai",)
    if p == "local":
        return ("local",)
    return (p,)


def _lookup_rate(provider: str, model: str) -> Tuple[float, float]:
    """Return ``(input_per_1k, output_per_1k)`` falling back when missing."""
    table = _load_pricing()
    model_l = model.lower()
    for alias in _provider_aliases(provider):
        rate = table.get((alias, model_l))
        if rate is not None:
            in_v, out_v = rate
            return (
                in_v if in_v is not None else _FALLBACK_INPUT_PER_1K,
                out_v if out_v is not None else _FALLBACK_OUTPUT_PER_1K,
            )
    return _FALLBACK_INPUT_PER_1K, _FALLBACK_OUTPUT_PER_1K


# ---------------------------------------------------------------------------
# Estimators
# ---------------------------------------------------------------------------


def _estimate_input_tokens(messages: List[Dict[str, str]]) -> int:
    """Rough token estimate from message text (whitespace × 1.3)."""
    total_words = 0
    for m in messages:
        content = m.get("content", "")
        if isinstance(content, str):
            total_words += len(content.split())
    # +5 per message accounts for role tags / framing tokens.
    framing = 5 * max(1, len(messages))
    return int(total_words * _WORD_TO_TOKEN_RATIO) + framing


def estimate_cost_usd(
    provider: str,
    model: str,
    messages: List[Dict[str, str]],
    max_tokens: int = 1024,
) -> float:
    """Estimate the upper-bound cost of a call BEFORE issuing it.

    Local provider always returns 0.0.
    """
    if provider.lower() == "local":
        return 0.0
    in_per_1k, out_per_1k = _lookup_rate(provider, model)
    in_tokens = _estimate_input_tokens(messages)
    return (in_tokens / 1000.0) * in_per_1k + (float(max_tokens) / 1000.0) * out_per_1k


def actual_cost_usd(
    provider: str,
    model: str,
    tokens_in: Optional[int],
    tokens_out: Optional[int],
) -> float:
    """Compute the real cost of a completed call.

    ``None`` token counts default to 0 — the pricing table cannot be
    blamed for the provider omitting the field. Callers concerned about
    silent zero-cost should propagate the ``None`` themselves.
    Local provider is always 0.0.
    """
    if provider.lower() == "local":
        return 0.0
    in_per_1k, out_per_1k = _lookup_rate(provider, model)
    in_n = int(tokens_in or 0)
    out_n = int(tokens_out or 0)
    return (in_n / 1000.0) * in_per_1k + (out_n / 1000.0) * out_per_1k


# ---------------------------------------------------------------------------
# Trackers
# ---------------------------------------------------------------------------


class BudgetHardStop(Exception):
    """Raised when adding a charge would cross a ceiling.

    The exception carries the ceiling kind for the audit emitter.

    Attributes:
        scope: ``"per_spawn"`` | ``"per_plan_5min"`` | ``"debate_max_rounds"``
        ceiling_usd: the configured ceiling.
        observed_usd: cumulative spend that triggered the stop.
    """

    def __init__(self, scope: str, ceiling_usd: float, observed_usd: float) -> None:
        super().__init__(
            f"budget_hard_stop scope={scope} ceiling=${ceiling_usd:.4f} observed=${observed_usd:.4f}"
        )
        self.scope = scope
        self.ceiling_usd = float(ceiling_usd)
        self.observed_usd = float(observed_usd)


@dataclass(frozen=True)
class SpawnCostSnapshot:
    """Read-only view — handy for audit emission."""

    total_usd: float
    call_count: int
    ceiling_usd: float


class SpawnCostTracker:
    """Per-spawn rolling tally with hard ceiling.

    Thread-safe. The default ceiling matches ADR-040 §3
    ``MAX_SPEND_USD_PER_SPAWN=0.50``.
    """

    def __init__(self, *, ceiling_usd: float = 0.50) -> None:
        if ceiling_usd <= 0:
            raise ValueError(f"ceiling_usd must be >0, got {ceiling_usd}")
        self._ceiling = float(ceiling_usd)
        self._lock = threading.Lock()
        self._total: float = 0.0
        self._calls: int = 0

    @property
    def total_usd(self) -> float:
        with self._lock:
            return self._total

    @property
    def ceiling_usd(self) -> float:
        return self._ceiling

    def snapshot(self) -> SpawnCostSnapshot:
        with self._lock:
            return SpawnCostSnapshot(self._total, self._calls, self._ceiling)

    def would_exceed(self, additional_usd: float) -> bool:
        """True iff adding ``additional_usd`` would cross the ceiling."""
        with self._lock:
            return (self._total + float(additional_usd)) > self._ceiling

    def add(self, charge_usd: float) -> None:
        """Add a real charge. Raises BudgetHardStop if it crosses the ceiling.

        The charge IS still recorded when raising — callers that want to
        roll back must do so themselves. (This matches the ADR contract:
        the request was issued; spend was incurred.)
        """
        if charge_usd < 0:
            raise ValueError(f"charge_usd must be >=0, got {charge_usd}")
        with self._lock:
            self._total += float(charge_usd)
            self._calls += 1
            if self._total > self._ceiling:
                raise BudgetHardStop("per_spawn", self._ceiling, self._total)

    def reset(self) -> None:
        with self._lock:
            self._total = 0.0
            self._calls = 0


class PlanCostTracker:
    """Per-plan rolling-window cost tracker (default 5-minute window).

    Holds (timestamp_seconds, usd) tuples and prunes on every access.
    Default ceiling matches ADR-040 §3
    ``MAX_SPEND_USD_PER_PLAN_5MIN=2.00``.
    """

    def __init__(
        self,
        *,
        ceiling_usd: float = 2.00,
        window_s: int = 300,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        if ceiling_usd <= 0:
            raise ValueError(f"ceiling_usd must be >0, got {ceiling_usd}")
        if window_s <= 0:
            raise ValueError(f"window_s must be >0, got {window_s}")
        self._ceiling = float(ceiling_usd)
        self._window_s = float(window_s)
        self._clock: Callable[[], float] = clock or _time.monotonic
        self._lock = threading.Lock()
        self._entries: Deque[Tuple[float, float]] = deque()

    @property
    def ceiling_usd(self) -> float:
        return self._ceiling

    def total_usd(self) -> float:
        """Sum of charges in the current rolling window."""
        with self._lock:
            self._prune_locked()
            return sum(usd for _, usd in self._entries)

    def add(self, charge_usd: float) -> None:
        """Record a charge. Raises BudgetHardStop if window total crosses ceiling."""
        if charge_usd < 0:
            raise ValueError(f"charge_usd must be >=0, got {charge_usd}")
        with self._lock:
            now = self._clock()
            self._entries.append((now, float(charge_usd)))
            self._prune_locked(now)
            total = sum(usd for _, usd in self._entries)
            if total > self._ceiling:
                raise BudgetHardStop("per_plan_5min", self._ceiling, total)

    def reset(self) -> None:
        with self._lock:
            self._entries.clear()

    def _prune_locked(self, now: Optional[float] = None) -> None:
        if now is None:
            now = self._clock()
        cutoff = now - self._window_s
        while self._entries and self._entries[0][0] < cutoff:
            self._entries.popleft()


__all__ = [
    "estimate_cost_usd",
    "actual_cost_usd",
    "BudgetHardStop",
    "SpawnCostTracker",
    "PlanCostTracker",
    "SpawnCostSnapshot",
]
