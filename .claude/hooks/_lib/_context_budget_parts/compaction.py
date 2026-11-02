"""compaction context-budget declarations."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

__all__ = ('ENV_AUTO_COMPACT_THRESHOLD', 'ENV_AUTO_COMPACT_LOW_WATER', 'ENV_AUTO_COMPACT_COOLDOWN_TURNS', 'ENV_AUTO_COMPACT_MIN_RECLAIM_PCT', 'DEFAULT_AUTO_COMPACT_THRESHOLD_PCT', 'DEFAULT_AUTO_COMPACT_LOW_WATER_PCT', 'DEFAULT_AUTO_COMPACT_COOLDOWN_TURNS', 'DEFAULT_AUTO_COMPACT_MIN_RECLAIM_PCT', 'REASON_DISABLED', 'REASON_BELOW_HIGH_WATER', 'REASON_NOT_REARMED', 'REASON_COOLDOWN', 'REASON_RECLAIM_FLOOR', 'REASON_COMPACT', '_env_int', 'CompactionPolicy', '_clamp_pct', 'load_policy_from_env', '_safe_ratio_pct', 'decide_compaction')

# ---------------------------------------------------------------------------
# PLAN-133 D1 — proactive auto-compaction policy (hysteresis state machine)
# ---------------------------------------------------------------------------
#
# Default-OFF behavioral change. The *decision* (this module) is non-canonical
# and lives here in `scripts/`; the actual `context_auto_compacted` /
# `context_auto_compact_suppressed` closed-enum audit emit is CANONICAL and has
# since LANDED in `.claude/hooks/_lib/audit_emit.py` (+ `SPEC/v1/
# audit-log.schema.md` + `.claude/data/audit-registry.golden.txt`) — this file
# never edits it. (The former pointer to `.claude/plans/PLAN-133/staged/
# D1.proposal.md` is stale: that path no longer exists.)
#
# PLAN-179 W3 US11 status: KEEP, as an exported policy — NOT as coverage. The
# emit exists; the EMITTER does not. Zero callers repo-wide and zero observed
# events. See `probe_status()` at the end of the D5 block, and
# `.claude/plans/PLAN-179/orphan-probe-decision.md`.
#
# Doctrine compliance:
#   * Default-OFF: the feature is INACTIVE unless `CEO_AUTO_COMPACT_THRESHOLD`
#     is set to a sane int in (0, 100]. With the env unset, `decide_compaction`
#     always returns a "disabled" decision (compact=False, suppressed=False).
#     The default constant below (80) is the value used WHEN enabled; it is NOT
#     a default-on flip.
#   * Measure-first: every decision carries the numeric reason + ratios so the
#     compaction-rate can be tabulated from logs before any default-on flip.
#   * Hysteresis (perf must-fix): trigger at a HIGH-water mark, re-arm only
#     after dropping below a LOW-water mark, plus a minimum-turns cooldown and
#     a minimum-bytes-reclaimed floor. When the floor (or a still-disarmed
#     re-arm gate, or cooldown) blocks a would-be compaction, the decision is
#     `suppressed=True` so the caller emits `context_auto_compact_suppressed`.
#   * Fail-open-on-infra: any malformed input / read error yields a "disabled"
#     decision (never raises), so a buggy snapshot never blocks a session.
#
# This is a pure, side-effect-free decision function: it does NOT compact, does
# NOT emit, and does NOT write anything. The host wires the side effects.

# Env flags (default-OFF). `CEO_AUTO_COMPACT_THRESHOLD` is the high-water % of
# the model context window at which compaction is proposed. Unset/invalid ⇒ OFF.
ENV_AUTO_COMPACT_THRESHOLD = "CEO_AUTO_COMPACT_THRESHOLD"
ENV_AUTO_COMPACT_LOW_WATER = "CEO_AUTO_COMPACT_LOW_WATER"
ENV_AUTO_COMPACT_COOLDOWN_TURNS = "CEO_AUTO_COMPACT_COOLDOWN_TURNS"
ENV_AUTO_COMPACT_MIN_RECLAIM_PCT = "CEO_AUTO_COMPACT_MIN_RECLAIM_PCT"

# Defaults used ONLY when the feature is enabled (threshold env present + valid).
DEFAULT_AUTO_COMPACT_THRESHOLD_PCT = 80   # high-water trigger (% of window)
DEFAULT_AUTO_COMPACT_LOW_WATER_PCT = 60   # re-arm only after dropping below this
DEFAULT_AUTO_COMPACT_COOLDOWN_TURNS = 5   # min turns between compactions
DEFAULT_AUTO_COMPACT_MIN_RECLAIM_PCT = 10  # skip if < this % of bytes would be freed

# Decision reason codes (stable strings for log tabulation; closed set).
REASON_DISABLED = "disabled"                  # feature OFF (env unset/invalid)
REASON_BELOW_HIGH_WATER = "below_high_water"   # usage under trigger
REASON_NOT_REARMED = "not_rearmed"             # above low-water since last compaction
REASON_COOLDOWN = "cooldown"                   # min-turns cooldown not elapsed
REASON_RECLAIM_FLOOR = "reclaim_floor"         # < min-bytes-reclaimed freed → skip
REASON_COMPACT = "compact"                     # all gates pass → compact now


def _env_int(name: str, env: Optional[Dict[str, str]]) -> Optional[int]:
    """Read an int from `env` (or os.environ) — None on absent/malformed.

    Fail-open: never raises. A non-integer, empty, or whitespace value reads as
    None (treated by callers as "not configured").
    """
    src = env if env is not None else os.environ
    raw = src.get(name)
    if raw is None:
        return None
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return None


class CompactionPolicy:
    """Hysteresis config + re-arm state for the auto-compaction decision.

    Stateless across processes by design — the host owns persistence. The host
    passes the prior `armed` flag and `turns_since_last_compaction` from its own
    session state; this object only derives the next decision + next state.

    `armed` means "eligible to trigger again": it is set False right after a
    compaction and re-set True once usage has dropped below the low-water mark.
    """

    def __init__(
        self,
        high_water_pct: int,
        low_water_pct: int,
        cooldown_turns: int,
        min_reclaim_pct: int,
    ) -> None:
        # Clamp to a sane, monotone config (fail-open: never raise on bad nums).
        self.high_water_pct = _clamp_pct(high_water_pct, DEFAULT_AUTO_COMPACT_THRESHOLD_PCT)
        low = _clamp_pct(low_water_pct, DEFAULT_AUTO_COMPACT_LOW_WATER_PCT)
        # Low-water MUST sit strictly below high-water for hysteresis to exist;
        # if a caller inverts them, pin low to high-1 (degenerate but safe).
        if low >= self.high_water_pct:
            low = max(0, self.high_water_pct - 1)
        self.low_water_pct = low
        self.cooldown_turns = cooldown_turns if cooldown_turns is not None and cooldown_turns >= 0 else DEFAULT_AUTO_COMPACT_COOLDOWN_TURNS
        self.min_reclaim_pct = _clamp_pct(min_reclaim_pct, DEFAULT_AUTO_COMPACT_MIN_RECLAIM_PCT)


def _clamp_pct(value: Any, fallback: int) -> int:
    """Coerce `value` to an int in [0, 100]; `fallback` on any malformed input."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return fallback
    if n < 0:
        return 0
    if n > 100:
        return 100
    return n


def load_policy_from_env(env: Optional[Dict[str, str]] = None) -> Optional[CompactionPolicy]:
    """Build a CompactionPolicy from env, or None when the feature is OFF.

    The feature is OFF (returns None) unless `CEO_AUTO_COMPACT_THRESHOLD` is set
    to an int in (0, 100]. All other knobs fall back to their documented
    defaults when unset/invalid. Fail-open: never raises.
    """
    threshold = _env_int(ENV_AUTO_COMPACT_THRESHOLD, env)
    if threshold is None or threshold <= 0 or threshold > 100:
        return None  # default-OFF
    return CompactionPolicy(
        high_water_pct=threshold,
        low_water_pct=(
            _env_int(ENV_AUTO_COMPACT_LOW_WATER, env)
            if _env_int(ENV_AUTO_COMPACT_LOW_WATER, env) is not None
            else DEFAULT_AUTO_COMPACT_LOW_WATER_PCT
        ),
        cooldown_turns=(
            _env_int(ENV_AUTO_COMPACT_COOLDOWN_TURNS, env)
            if _env_int(ENV_AUTO_COMPACT_COOLDOWN_TURNS, env) is not None
            else DEFAULT_AUTO_COMPACT_COOLDOWN_TURNS
        ),
        min_reclaim_pct=(
            _env_int(ENV_AUTO_COMPACT_MIN_RECLAIM_PCT, env)
            if _env_int(ENV_AUTO_COMPACT_MIN_RECLAIM_PCT, env) is not None
            else DEFAULT_AUTO_COMPACT_MIN_RECLAIM_PCT
        ),
    )


def _safe_ratio_pct(numerator: Any, denominator: Any) -> Optional[float]:
    """numerator/denominator as a percent (0..100), or None if not derivable."""
    try:
        num = float(numerator)
        den = float(denominator)
    except (TypeError, ValueError):
        return None
    if den <= 0:
        return None
    pct = (num / den) * 100.0
    if pct < 0:
        return 0.0
    return pct


def decide_compaction(
    used_tokens: Any,
    window_tokens: Any,
    *,
    reclaimable_tokens: Any = None,
    armed: bool = True,
    turns_since_last_compaction: Any = None,
    policy: Optional[CompactionPolicy] = None,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Decide whether to auto-compact NOW. Pure + side-effect-free + fail-open.

    Parameters
    ----------
    used_tokens, window_tokens
        Current context usage and the model window size (tokens). The usage
        ratio drives the high/low-water hysteresis.
    reclaimable_tokens
        Estimated tokens a compaction would free. Drives the minimum-reclaim
        floor. When None, the floor is treated as PASSED (host could not
        estimate — do not block on a missing estimate; fail-open).
    armed
        Host-supplied re-arm flag (False right after a prior compaction until
        usage has dropped below the low-water mark).
    turns_since_last_compaction
        Host-supplied turn counter for the cooldown gate. None ⇒ cooldown
        treated as elapsed (no prior compaction this session).
    policy
        Explicit policy; when None, derived from `env` (default-OFF if the
        threshold env is unset/invalid).

    Returns a decision dict (never raises):
      {
        "compact": bool,            # caller should compact now
        "suppressed": bool,         # a would-be compaction was skipped by a gate
        "reason": <REASON_*>,       # stable reason code
        "enabled": bool,            # feature active
        "usage_pct": float|None,    # used/window * 100
        "reclaim_pct": float|None,  # reclaimable/used * 100 (estimate)
        "next_armed": bool,         # re-arm state the host should persist
        "high_water_pct": int|None,
        "low_water_pct": int|None,
        "cooldown_turns": int|None,
        "min_reclaim_pct": int|None,
      }

    NOTE — no payload echo: this dict carries ONLY numeric ratios + closed
    reason codes. It never includes any transcript text, command bytes, env
    values, or file paths. The canonical emit (staged proposal) scrubs to the
    same closed-field allowlist.
    """
    base = {
        "compact": False,
        "suppressed": False,
        "reason": REASON_DISABLED,
        "enabled": False,
        "usage_pct": None,
        "reclaim_pct": None,
        "next_armed": bool(armed),
        "high_water_pct": None,
        "low_water_pct": None,
        "cooldown_turns": None,
        "min_reclaim_pct": None,
    }

    if policy is None:
        policy = load_policy_from_env(env)
    if policy is None:
        return base  # default-OFF — disabled decision

    base["enabled"] = True
    base["high_water_pct"] = policy.high_water_pct
    base["low_water_pct"] = policy.low_water_pct
    base["cooldown_turns"] = policy.cooldown_turns
    base["min_reclaim_pct"] = policy.min_reclaim_pct

    usage_pct = _safe_ratio_pct(used_tokens, window_tokens)
    base["usage_pct"] = usage_pct
    if usage_pct is None:
        # Cannot derive usage (bad/zero window) → fail-open: do nothing.
        base["reason"] = REASON_BELOW_HIGH_WATER
        return base

    # Hysteresis re-arm: once usage drops below low-water, become eligible again.
    next_armed = bool(armed)
    if usage_pct < policy.low_water_pct:
        next_armed = True
    base["next_armed"] = next_armed

    # Below the high-water trigger: nothing to do (and we've already updated the
    # re-arm flag above for the drop-below-low case).
    if usage_pct < policy.high_water_pct:
        base["reason"] = REASON_BELOW_HIGH_WATER
        return base

    # At/above high-water but NOT re-armed (we are still riding the band above
    # low-water since the last compaction) → hold (not a suppression event; we
    # simply have not earned a fresh trigger).
    if not next_armed:
        base["reason"] = REASON_NOT_REARMED
        return base

    # Cooldown gate: a would-be compaction blocked by min-turns IS a suppression.
    turns = turns_since_last_compaction
    if turns is not None:
        try:
            turns_int = int(turns)
        except (TypeError, ValueError):
            turns_int = None
        if turns_int is not None and turns_int < policy.cooldown_turns:
            base["reason"] = REASON_COOLDOWN
            base["suppressed"] = True
            return base

    # Minimum-reclaim floor: skip a compaction that would free too little.
    reclaim_pct = _safe_ratio_pct(reclaimable_tokens, used_tokens)
    base["reclaim_pct"] = reclaim_pct
    if reclaim_pct is not None and reclaim_pct < policy.min_reclaim_pct:
        base["reason"] = REASON_RECLAIM_FLOOR
        base["suppressed"] = True
        return base

    # All gates pass → compact now; consume the re-arm (host disarms until the
    # next drop below low-water).
    base["compact"] = True
    base["reason"] = REASON_COMPACT
    base["next_armed"] = False
    return base


