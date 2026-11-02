"""middle_out context-budget declarations."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

__all__ = ('ENV_MIDDLE_OUT_DEGRADE', 'ENV_MIDDLE_OUT_PROTECT_LAST', 'ENV_MIDDLE_OUT_MIN_MSG_TOKENS', 'DEFAULT_MIDDLE_OUT_KEEP_FLOOR_PCT', 'DEFAULT_MIDDLE_OUT_PROTECT_LAST', 'DEFAULT_MIDDLE_OUT_MIN_MSG_TOKENS', 'MIDDLE_OUT_LADDER', 'MIDDLE_OUT_ELISION_MARKER', 'MO_REASON_DISABLED', 'MO_REASON_NO_OVERFLOW', 'MO_REASON_DEGRADED', 'MO_REASON_FAILED', 'MiddleOutPolicy', 'load_middle_out_policy_from_env', '_message_is_pinned', '_message_content', '_message_token_size', '_elide_middle', 'decide_middle_out_degradation', 'apply_middle_out_degradation')

# ---------------------------------------------------------------------------
# PLAN-133 D5 (Wave D) — middle-out degradation ladder on the context-overflow
# path (drop growing fractions of tool-response messages, middle-out, before
# failing)
# ---------------------------------------------------------------------------
#
# Default-OFF behavioral change. The *decision + transform* (this module) is
# non-canonical and lives here in `scripts/`; the actual
# `context_middle_out_degraded` / `context_middle_out_degrade_failed`
# closed-enum audit emit is CANONICAL and has since LANDED in
# `.claude/hooks/_lib/audit_emit.py` (+ `SPEC/v1/audit-log.schema.md` +
# `.claude/data/audit-registry.golden.txt`) — this file never edits it. (The
# former pointer to `.claude/plans/PLAN-133/staged/D5.proposal.md` is stale:
# that path no longer exists.)
#
# PLAN-179 W3 US11 status: KEEP, as an exported policy — NOT as coverage. Same
# shape as D1: the emit exists, the EMITTER does not. See `probe_status()`
# below and `.claude/plans/PLAN-179/orphan-probe-decision.md`.
#
# The IDEA (re-implemented from scratch, stdlib-only, NOT vendored): when the
# assembled context would OVERFLOW the model window, do NOT hard-fail. Instead,
# walk a **degradation ladder** — a sequence of growing fractions (e.g. 25% →
# 50% → 75% → 90%) — and at each RUNG drop that fraction from the MIDDLE of the
# largest tool-response messages, preserving a HEAD and a TAIL slice of each
# (the head carries the request/the first lines of output; the tail carries the
# conclusion/error/exit status — the two highest-signal regions). Keep climbing
# rungs (degrading more, on more messages) only while still over budget; stop
# the instant the projection fits (success) or the ladder is exhausted (the
# caller then decides to summarize/compact/fail — D1/D2 are the upstream knobs).
#
# Why MIDDLE-out and not head/tail truncation: a tool response's first lines
# (the command echoed + the start of stdout) and its last lines (the tail of
# stdout + the exit/error) are what the orchestrator actually reasons over; the
# bulk in the middle (repetitive log lines, large dumps) is the cheapest to drop
# with the least loss of meaning. This is the same rationale as a unified-diff
# context window: keep the edges, elide the center.
#
# Doctrine compliance (§3):
#   * Default-OFF: INACTIVE unless `CEO_MIDDLE_OUT_DEGRADE` is set to a truthy
#     int in (0, 100] — the per-message head+tail-preserved floor PERCENT (the
#     minimum fraction of each degraded message that MUST be kept; e.g. 40 ⇒ at
#     most 60% of any message is ever dropped). Unset/invalid ⇒
#     `decide_middle_out_degradation` returns a "disabled" plan (degraded=[],
#     enabled=False) and `apply_middle_out_degradation` returns the messages
#     UNCHANGED. The DEFAULT constants below are the values used WHEN enabled;
#     they are NOT a default-on flip.
#   * Measure-first: the plan carries the rung reached + reclaimed-token
#     estimate + a closed reason so the degradation-rate (and how often it
#     SAVED an overflow vs FAILED) can be tabulated from logs before any
#     default-on flip. Named promotion-measure: count(`context_middle_out_degraded`)
#     vs count(`context_middle_out_degrade_failed`) per week at /ceo-boot.
#   * protect-last-N + pinned: the `protect_last` most-recent messages and any
#     message marked `pinned`/`agent_visible`-True are NEVER degraded, so the
#     active working set and explicitly-pinned context are safe.
#   * growing-fraction ladder (the named AC): rungs are applied in ascending
#     aggressiveness; a rung is only entered if the prior projection still
#     overflows — never drop more than the overflow requires.
#   * head/tail floor: a degraded message ALWAYS keeps at least `min_keep_pct`
#     of its content (split head/tail), so a message is never reduced to a
#     meaningless stub. The floor is the env value.
#   * Fail-open-on-infra: any malformed input / read error yields a "disabled"
#     plan (never raises) and the apply function returns the input untouched, so
#     a buggy snapshot never blocks a session and a message is never corrupted.
#   * No payload echo: the plan carries ONLY integer indices + token-size
#     buckets + a rung integer + closed reason codes. It NEVER includes any
#     message text, tool name, agent name, file path, or command bytes. The
#     canonical emit (staged proposal) scrubs to the same closed-field allowlist.
#
# `decide_middle_out_degradation` is PURE + side-effect-free (does not mutate
# inputs, does not emit, does not write). `apply_middle_out_degradation` returns
# NEW message dicts (copies) with the middle elided — it likewise never emits,
# never writes, and never mutates the inputs in place.

# Env flag (default-OFF). `CEO_MIDDLE_OUT_DEGRADE` is the per-message keep-floor
# PERCENT (minimum % of each degraded message preserved, split head/tail).
# Unset/invalid/<=0/>100 ⇒ OFF.
ENV_MIDDLE_OUT_DEGRADE = "CEO_MIDDLE_OUT_DEGRADE"
ENV_MIDDLE_OUT_PROTECT_LAST = "CEO_MIDDLE_OUT_PROTECT_LAST"
ENV_MIDDLE_OUT_MIN_MSG_TOKENS = "CEO_MIDDLE_OUT_MIN_MSG_TOKENS"

# Defaults used ONLY when the feature is enabled (the keep-floor env is present
# and a valid int in (0, 100]).
DEFAULT_MIDDLE_OUT_KEEP_FLOOR_PCT = 40   # keep >= this % of any degraded message
DEFAULT_MIDDLE_OUT_PROTECT_LAST = 3      # never degrade the last N messages
DEFAULT_MIDDLE_OUT_MIN_MSG_TOKENS = 1000  # only degrade messages bigger than this

# The degradation ladder: ascending fractions of a message's content to TARGET
# for removal at each rung. The actual removal is clamped so the kept fraction
# never drops below the keep-floor (so a "90% drop" rung with a 40% keep-floor
# removes at most 60%). A closed, ordered tuple — the rungs are stable for log
# tabulation. Rung index 0 is the least aggressive.
MIDDLE_OUT_LADDER = (0.25, 0.50, 0.75, 0.90)

# Marker inserted where the middle was elided (token-cheap, signals truncation).
MIDDLE_OUT_ELISION_MARKER = "\n…[middle-out: {n} chars elided]…\n"

# Degradation-plan reason codes (stable strings for log tabulation; closed set,
# mirrored by the canonical `_MIDDLE_OUT_REASON_ENUM`).
MO_REASON_DISABLED = "disabled"        # feature OFF (env unset/invalid)
MO_REASON_NO_OVERFLOW = "no_overflow"   # already within budget — nothing to do
MO_REASON_DEGRADED = "degraded"         # ladder reclaimed enough → fits now
MO_REASON_FAILED = "failed"             # ladder exhausted, still over budget


class MiddleOutPolicy:
    """Config for the middle-out degradation ladder.

    Stateless by design — the host owns the message list and applies the plan.
    This object only holds the three knobs + the (constant) ladder.
    """

    def __init__(
        self,
        keep_floor_pct: int,
        protect_last: int,
        min_msg_tokens: int,
    ) -> None:
        # Clamp to sane, fail-open values (never raise on a bad number). The
        # keep-floor is a percent in [1, 100] (0 would allow dropping a whole
        # message — middle-out always keeps SOMETHING, so floor is >= 1).
        floor = _clamp_pct(keep_floor_pct, DEFAULT_MIDDLE_OUT_KEEP_FLOOR_PCT)
        self.keep_floor_pct = floor if floor >= 1 else 1
        self.protect_last = _clamp_nonneg_int(
            protect_last, DEFAULT_MIDDLE_OUT_PROTECT_LAST)
        self.min_msg_tokens = _clamp_nonneg_int(
            min_msg_tokens, DEFAULT_MIDDLE_OUT_MIN_MSG_TOKENS)


def load_middle_out_policy_from_env(
    env: Optional[Dict[str, str]] = None,
) -> Optional[MiddleOutPolicy]:
    """Build a MiddleOutPolicy from env, or None when the feature is OFF.

    OFF (returns None) unless `CEO_MIDDLE_OUT_DEGRADE` is set to an int in
    (0, 100] (the per-message keep-floor percent). Other knobs fall back to
    documented defaults when unset/invalid. Fail-open: never raises.
    """
    floor = _env_int(ENV_MIDDLE_OUT_DEGRADE, env)
    if floor is None or floor <= 0 or floor > 100:
        return None  # default-OFF
    protect = _env_int(ENV_MIDDLE_OUT_PROTECT_LAST, env)
    min_tokens = _env_int(ENV_MIDDLE_OUT_MIN_MSG_TOKENS, env)
    return MiddleOutPolicy(
        keep_floor_pct=floor,
        protect_last=protect if protect is not None else DEFAULT_MIDDLE_OUT_PROTECT_LAST,
        min_msg_tokens=min_tokens if min_tokens is not None else DEFAULT_MIDDLE_OUT_MIN_MSG_TOKENS,
    )


def _message_is_pinned(record: Any) -> bool:
    """True if a message record is explicitly pinned / kept-in-model.

    A mapping carrying ``pinned``-truthy or ``agent_visible`` is NEVER degraded
    (the dual-visibility D3 marker + an explicit pin both protect a message).
    Anything we cannot interpret is treated as NOT pinned (fail-open: we never
    refuse to consider a message just because it lacks a flag — but see the
    size/protect-window gates which independently protect it).
    """
    if isinstance(record, dict):
        if record.get("pinned"):
            return True
        if record.get("agent_visible") is True:
            return True
    return False


def _message_content(record: Any) -> Optional[str]:
    """Best-effort text content of one message record, or None.

    Accepts a mapping with a ``content`` (preferred) or ``text`` str field, or a
    bare str. Returns None when no text can be derived (the record is then never
    degraded — fail-open: we never elide content we cannot read).
    """
    if isinstance(record, str):
        return record
    if isinstance(record, dict):
        for key in ("content", "text"):
            v = record.get(key)
            if isinstance(v, str):
                return v
    return None


def _message_token_size(record: Any) -> Optional[int]:
    """Best-effort estimated token size of one message record.

    Prefers an explicit ``est_tokens`` / ``tokens`` field; else estimates from
    the text content length (chars/4). Returns None when no size can be derived
    (the record is then treated as below-floor and never degraded).
    """
    if isinstance(record, bool):
        return None
    if isinstance(record, int):
        return record if record >= 0 else None
    if isinstance(record, dict):
        for key in ("est_tokens", "tokens"):
            if key in record:
                try:
                    n = int(record[key])
                except (TypeError, ValueError):
                    return None
                return n if n >= 0 else None
        if "chars" in record:
            try:
                c = int(record["chars"])
            except (TypeError, ValueError):
                return None
            return estimate_tokens(c) if c >= 0 else None
    text = _message_content(record)
    if text is not None:
        return estimate_tokens(len(text))
    return None


def _elide_middle(text: str, drop_fraction: float, keep_floor_pct: int) -> Tuple[str, int]:
    """Drop the MIDDLE of `text`, keeping head+tail. Returns (new_text, chars_dropped).

    `drop_fraction` is the TARGET fraction (0..1) of chars to remove; the actual
    removal is clamped so the kept fraction never falls below `keep_floor_pct`%.
    The kept portion is split as evenly as possible head/tail (head gets the odd
    char on an odd split). A token-cheap elision marker replaces the gap.

    Fail-open: a non-str, empty, or degenerate input returns the text unchanged
    with 0 dropped (never raises).
    """
    if not isinstance(text, str) or not text:
        return text, 0
    total = len(text)
    try:
        frac = float(drop_fraction)
    except (TypeError, ValueError):
        return text, 0
    if frac <= 0:
        return text, 0
    if frac > 1:
        frac = 1.0
    # Clamp the drop so the kept fraction stays at/above the keep-floor.
    max_drop_frac = max(0.0, 1.0 - (keep_floor_pct / 100.0))
    eff_frac = min(frac, max_drop_frac)
    drop_chars = int(total * eff_frac)
    if drop_chars <= 0:
        return text, 0
    keep_chars = total - drop_chars
    if keep_chars <= 0:
        # Degenerate (keep-floor 0 path defended elsewhere) — keep 1 char head.
        keep_chars = 1
        drop_chars = total - 1
        if drop_chars <= 0:
            return text, 0
    head_len = (keep_chars + 1) // 2  # head gets the odd char
    tail_len = keep_chars - head_len
    head = text[:head_len]
    tail = text[total - tail_len:] if tail_len > 0 else ""
    marker = MIDDLE_OUT_ELISION_MARKER.format(n=drop_chars)
    new_text = head + marker + tail
    # Report the NET char delta actually removed (the marker adds a few back).
    net_dropped = total - len(new_text)
    if net_dropped <= 0:
        # The marker was longer than what we dropped (tiny message) — no-op.
        return text, 0
    return new_text, net_dropped


def decide_middle_out_degradation(
    messages: Any,
    budget_tokens: Any,
    *,
    policy: Optional[MiddleOutPolicy] = None,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Decide which messages to degrade middle-out, and at which ladder rung.

    Pure + side-effect-free + fail-open. PROTECTS the last N + pinned messages.
    Does NOT mutate `messages` and does NOT perform the elision — it returns a
    plan that `apply_middle_out_degradation` (or the host) executes.

    Parameters
    ----------
    messages
        An ordered sequence of message records, OLDEST FIRST (index 0 is the
        oldest, index ``len-1`` the most recent). Each record may be a mapping
        carrying ``content``/``text`` and/or a size (``est_tokens`` / ``tokens``
        / ``chars``), or a bare str. The order determines the protect-last-N
        window; the host supplies it.
    budget_tokens
        The token budget the assembled context must fit within (e.g. the model
        window minus a safety margin). Overflow = sum(sizes) > budget.
    policy
        Explicit policy; when None, derived from `env` (default-OFF if the
        keep-floor env is unset/invalid).

    Returns a plan dict (never raises):
      {
        "enabled": bool,            # feature active
        "reason": <MO_REASON_*>,    # stable plan-level reason code
        "rung": int,                # ladder rung reached (-1 if none entered)
        "degraded": [               # per-message degradation directives
          {"index": int, "drop_fraction": float}, ...
        ],
        "degraded_count": int,
        "reclaim_tokens": int,      # est tokens the plan would reclaim
        "total_tokens": int,        # sum of message sizes (pre-degrade)
        "budget_tokens": int,       # the budget projected against
        "fits_after": bool,         # projected to fit after degradation
        "protected_count": int,     # last-N + pinned + below-floor skips
        "protect_last": int|None,
        "min_msg_tokens": int|None,
        "keep_floor_pct": int|None,
        "ladder_len": int,
      }

    NO payload echo: the plan carries ONLY integer indices + token totals + a
    rung integer + a float fraction + closed reason codes. It NEVER includes any
    message text, tool name, agent name, file path, or command bytes. The
    canonical emit (staged proposal) scrubs to the same closed-field allowlist.
    """
    plan: Dict[str, Any] = {
        "enabled": False,
        "reason": MO_REASON_DISABLED,
        "rung": -1,
        "degraded": [],
        "degraded_count": 0,
        "reclaim_tokens": 0,
        "total_tokens": 0,
        "budget_tokens": 0,
        "fits_after": True,
        "protected_count": 0,
        "protect_last": None,
        "min_msg_tokens": None,
        "keep_floor_pct": None,
        "ladder_len": len(MIDDLE_OUT_LADDER),
    }

    if policy is None:
        policy = load_middle_out_policy_from_env(env)
    if policy is None:
        return plan  # default-OFF — disabled plan

    plan["enabled"] = True
    plan["protect_last"] = policy.protect_last
    plan["min_msg_tokens"] = policy.min_msg_tokens
    plan["keep_floor_pct"] = policy.keep_floor_pct

    # Normalize the budget (fail-open: a bad/<=0 budget ⇒ disabled-ish no-op).
    try:
        budget = int(budget_tokens)
    except (TypeError, ValueError):
        budget = 0
    if budget <= 0:
        plan["reason"] = MO_REASON_NO_OVERFLOW
        return plan
    plan["budget_tokens"] = budget

    # Normalize the messages list (fail-open: a non-sequence ⇒ empty).
    try:
        items = list(messages)
    except TypeError:
        items = []
    total_msgs = len(items)
    if total_msgs == 0:
        plan["reason"] = MO_REASON_NO_OVERFLOW
        return plan

    # Size every message; sum the total (None-sized rows count as 0 — they are
    # never degraded so they cannot help, but they DO occupy real budget the
    # host is responsible for; we conservatively count what we can size).
    sizes: List[Optional[int]] = [_message_token_size(m) for m in items]
    total_tokens = sum(s for s in sizes if isinstance(s, int))
    plan["total_tokens"] = total_tokens

    # No overflow → nothing to do (the common, cheap path).
    if total_tokens <= budget:
        plan["reason"] = MO_REASON_NO_OVERFLOW
        return plan

    overflow = total_tokens - budget

    # Determine the protected window: the last `protect_last` indices + any
    # pinned message + any below-floor (too-small to bother) message.
    protect_last = policy.protect_last
    protect_from = max(0, total_msgs - protect_last) if protect_last > 0 else total_msgs

    # Eligible = age-eligible (before protect window) AND not pinned AND big
    # enough to bother (>= min_msg_tokens AND sizeable). Build (index, size),
    # LARGEST FIRST so we degrade the heaviest messages first within a rung.
    eligible: List[Tuple[int, int]] = []
    protected = 0
    for idx in range(total_msgs):
        size = sizes[idx]
        if idx >= protect_from:
            protected += 1
            continue
        if _message_is_pinned(items[idx]):
            protected += 1
            continue
        if size is None or size < policy.min_msg_tokens:
            protected += 1
            continue
        eligible.append((idx, size))
    plan["protected_count"] = protected

    if not eligible:
        # Nothing we are allowed to degrade — the ladder cannot help. FAILED
        # (the caller must summarize/compact/fail upstream).
        plan["reason"] = MO_REASON_FAILED
        plan["fits_after"] = False
        return plan

    # Largest-first ordering within a rung.
    eligible.sort(key=lambda t: (-t[1], t[0]))

    keep_floor = policy.keep_floor_pct
    # The most a single message can ever reclaim (its size × max-drop-fraction).
    max_drop_frac = max(0.0, 1.0 - (keep_floor / 100.0))

    # Climb the ladder. At rung r, every eligible message is degraded at the
    # rung's TARGET fraction (clamped by the keep-floor). We stop the instant
    # the cumulative reclaim covers the overflow, recording the per-message
    # directive + the rung reached. Higher rungs subsume lower ones (we recompute
    # from scratch per rung so the directive is the FINAL fraction per message).
    best_plan: Optional[Tuple[int, List[Dict[str, Any]], int]] = None
    for rung, target_frac in enumerate(MIDDLE_OUT_LADDER):
        eff_frac = min(float(target_frac), max_drop_frac)
        if eff_frac <= 0:
            continue
        directives: List[Dict[str, Any]] = []
        reclaim = 0
        for idx, size in eligible:
            drop = int(size * eff_frac)
            if drop <= 0:
                continue
            directives.append({"index": idx, "drop_fraction": round(eff_frac, 4)})
            reclaim += drop
            if reclaim >= overflow:
                break
        if reclaim >= overflow:
            # This rung fits — record and STOP (do not climb further).
            best_plan = (rung, directives, reclaim)
            break
        # This rung did not fit; remember the most-aggressive attempt so far
        # (the last rung, fully applied) for the FAILED-but-best report.
        best_plan = (rung, directives, reclaim)

    if best_plan is None:
        # No applicable rung (Codex pair-rail #3): e.g. keep-floor=100% -> max_drop_frac=0
        # -> every rung is skipped. Fail-OPEN with an empty FAILED plan instead of
        # crashing on the unpack below.
        plan["rung"] = -1
        plan["degraded"] = []
        plan["degraded_count"] = 0
        plan["reclaim_tokens"] = 0
        plan["fits_after"] = False
        plan["reason"] = MO_REASON_FAILED
        return plan
    rung, directives, reclaim = best_plan  # type: ignore[misc]
    # Sort directives by index for a deterministic, log-friendly order.
    directives.sort(key=lambda d: d["index"])
    plan["rung"] = rung
    plan["degraded"] = directives
    plan["degraded_count"] = len(directives)
    plan["reclaim_tokens"] = reclaim
    fits = reclaim >= overflow
    plan["fits_after"] = fits
    plan["reason"] = MO_REASON_DEGRADED if fits else MO_REASON_FAILED
    return plan


def apply_middle_out_degradation(
    messages: Any,
    plan: Dict[str, Any],
    *,
    policy: Optional[MiddleOutPolicy] = None,
    env: Optional[Dict[str, str]] = None,
) -> List[Any]:
    """Apply a `decide_middle_out_degradation` plan, returning NEW messages.

    Does NOT mutate the input list or its records — it returns a new list whose
    degraded entries are shallow copies with the middle of their text elided.
    Non-degraded messages are passed through unchanged (same object). Fail-open:
    a disabled/empty plan, a malformed message list, or a record we cannot read
    text from returns the input messages (as a list) untouched; never raises.

    `policy`/`env` resolve the keep-floor used by the elision; when None they are
    derived from env (default-OFF ⇒ the input is returned unchanged).
    """
    try:
        items = list(messages)
    except TypeError:
        return []

    if not isinstance(plan, dict) or not plan.get("enabled"):
        return items
    directives = plan.get("degraded") or []
    if not directives:
        return items

    if policy is None:
        policy = load_middle_out_policy_from_env(env)
    if policy is None:
        return items  # feature OFF at apply time ⇒ no-op
    keep_floor = policy.keep_floor_pct

    # Map index → drop_fraction for O(1) lookup.
    drop_by_index: Dict[int, float] = {}
    for d in directives:
        if not isinstance(d, dict):
            continue
        try:
            i = int(d.get("index"))
            f = float(d.get("drop_fraction"))
        except (TypeError, ValueError):
            continue
        drop_by_index[i] = f

    out: List[Any] = []
    n = len(items)
    for idx in range(n):
        rec = items[idx]
        frac = drop_by_index.get(idx)
        if frac is None or frac <= 0:
            out.append(rec)
            continue
        text = _message_content(rec)
        if text is None:
            out.append(rec)  # cannot read text ⇒ pass through unchanged
            continue
        new_text, dropped = _elide_middle(text, frac, keep_floor)
        if dropped <= 0:
            out.append(rec)  # nothing actually dropped ⇒ pass through
            continue
        if isinstance(rec, str):
            out.append(new_text)
        elif isinstance(rec, dict):
            new_rec = dict(rec)  # shallow copy — never mutate the input
            if "content" in rec and isinstance(rec.get("content"), str):
                new_rec["content"] = new_text
            elif "text" in rec and isinstance(rec.get("text"), str):
                new_rec["text"] = new_text
            else:
                new_rec["content"] = new_text
            new_rec["middle_out_degraded"] = True
            out.append(new_rec)
        else:
            out.append(rec)
    return out


