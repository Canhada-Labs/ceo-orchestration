"""summarization context-budget declarations."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

__all__ = ('ENV_SUMMARIZE_OLDEST', 'ENV_SUMMARIZE_PROTECT_LAST', 'ENV_SUMMARIZE_MIN_TOKENS', 'DEFAULT_SUMMARIZE_PROTECT_LAST', 'DEFAULT_SUMMARIZE_MIN_TOKENS', 'DEFAULT_SUMMARIZE_MAX_PER_PASS', 'SUMM_REASON_DISABLED', 'SUMM_REASON_NO_CANDIDATES', 'SUMM_REASON_SELECTED', 'SUMM_SKIP_PROTECTED', 'SUMM_SKIP_BELOW_FLOOR', 'SUMM_SKIP_OVER_BUDGET', 'SummarizationPolicy', '_clamp_nonneg_int', 'load_summarization_policy_from_env', '_output_token_size', 'decide_summarization')

# ---------------------------------------------------------------------------
# PLAN-133 D2 (Wave D) — cheap-tier summarization of oldest verbose subagent
# outputs (protect last N)
# ---------------------------------------------------------------------------
#
# Default-OFF behavioral change. The *decision* (this module) is non-canonical
# and lives here in `scripts/`.
#
# STALE CLAIM CORRECTED (PLAN-179 W3 US11). This block used to state that
# the `subagent_output_summarized` / `subagent_output_summarize_skipped`
# closed-enum audit emit "is CANONICAL (`.claude/hooks/_lib/audit_emit.py`) and
# is staged for Owner-GPG under `.claude/plans/PLAN-133/staged/D2.proposal.md`".
# BOTH halves are false as measured on 2026-08-18: neither action name occurs
# anywhere in `.claude/hooks/_lib/audit_emit.py` or `SPEC/v1/audit-log.schema.md`
# (they occur ONLY in this file), and neither `.claude/plans/PLAN-133/staged/`
# nor `.claude/plans/PLAN-133/` exists. D2 is an orphan at BOTH ends.
#
# PLAN-179 W3 US11 verdict: **REMOVE — pending co-deletion of its test.** The
# removal must take out this block, the `--summarize-decision` /
# `--output-sizes` / `--output-sizes-file` CLI surface, and
# `TestSummarizationPolicy` in `.claude/scripts/tests/test_context_budget.py`
# in ONE change. Removing the probe alone turns a green suite red, which is
# strictly worse than the debt. Until then the state is DECLARED in
# `probe_status()` so nobody mistakes it for coverage.
#
# The IDEA (re-implemented from scratch, stdlib-only, NOT vendored): when the
# context window fills, the OLDEST + most-VERBOSE subagent tool-outputs are the
# best candidates to compress — they are the least likely to be needed verbatim
# again, and they carry the most tokens. We route those oldest verbose outputs
# to a CHEAP model tier for a short digest, while PROTECTING the last N outputs
# (the recent working set the orchestrator is actively reasoning over) so a
# just-produced result is never silently summarized out from under the loop.
#
# Doctrine compliance (§3):
#   * Default-OFF: INACTIVE unless `CEO_SUMMARIZE_OLDEST` is set to a truthy
#     int budget (the max number of outputs to summarize in one pass, > 0).
#     Unset/invalid ⇒ `decide_summarization` returns a "disabled" plan
#     (selected=[], enabled=False). The DEFAULT constants below are the values
#     used WHEN enabled; they are NOT a default-on flip.
#   * Measure-first: the plan carries the selected count + reclaimable-token
#     estimate + a closed reason so the summarization-rate (and the tokens it
#     would reclaim) can be tabulated from logs before any default-on flip.
#     Named promotion-measure: count(`subagent_output_summarized`) and the
#     summed `reclaim_tokens` per week at /ceo-boot.
#   * protect-last-N (the named AC): the `protect_last` most-recent outputs are
#     NEVER eligible, regardless of size, so the active working set is safe.
#   * verbosity floor: only outputs whose estimated size is >= a minimum-token
#     floor are eligible (summarizing a tiny output costs a cheap-tier call to
#     save nothing — `subagent_output_summarize_skipped` reason=below_floor).
#   * budget cap: at most `max_summaries` oldest-first eligible outputs are
#     selected in one pass (the rest are deferred, not lost).
#   * Fail-open-on-infra: any malformed input / read error yields a "disabled"
#     plan (never raises), so a buggy snapshot never blocks a session and a
#     recent output is never accidentally selected.
#   * No payload echo: the plan carries ONLY integer indices + token-size
#     buckets + closed reason codes. It NEVER includes any subagent output
#     text, agent name, file path, or command bytes. The canonical emit (staged
#     proposal) scrubs to the same closed-field allowlist.
#
# This is a pure, side-effect-free decision function: it does NOT summarize,
# does NOT call any model, does NOT emit, and does NOT write anything. The host
# wires the cheap-tier digest call + the audit emit + the context rewrite.

# Env flags (default-OFF). `CEO_SUMMARIZE_OLDEST` is the per-pass budget (max
# number of oldest verbose outputs to summarize). Unset/invalid/<=0 ⇒ OFF.
ENV_SUMMARIZE_OLDEST = "CEO_SUMMARIZE_OLDEST"
ENV_SUMMARIZE_PROTECT_LAST = "CEO_SUMMARIZE_PROTECT_LAST"
ENV_SUMMARIZE_MIN_TOKENS = "CEO_SUMMARIZE_MIN_TOKENS"

# Defaults used ONLY when the feature is enabled (the budget env is present and
# a valid positive int).
DEFAULT_SUMMARIZE_PROTECT_LAST = 3       # never summarize the last N outputs
DEFAULT_SUMMARIZE_MIN_TOKENS = 2000      # verbosity floor: skip small outputs
DEFAULT_SUMMARIZE_MAX_PER_PASS = 5       # cap per pass when budget is degenerate

# Summarization-plan reason codes (stable strings for log tabulation; closed
# set, mirrored by the canonical `_SUBAGENT_SUMMARIZE_REASON_ENUM`).
SUMM_REASON_DISABLED = "disabled"          # feature OFF (env unset/invalid)
SUMM_REASON_NO_CANDIDATES = "no_candidates"  # nothing past protect-N over floor
SUMM_REASON_SELECTED = "selected"          # >=1 output selected to summarize

# Per-output skip reason codes (why an individual output was NOT selected).
SUMM_SKIP_PROTECTED = "protected"          # within the last-N working set
SUMM_SKIP_BELOW_FLOOR = "below_floor"      # under the verbosity (min-tokens) floor
SUMM_SKIP_OVER_BUDGET = "over_budget"      # eligible but past the per-pass cap


class SummarizationPolicy:
    """Config for the oldest-verbose-output summarization decision.

    Stateless by design — the host owns the list of current subagent outputs
    and applies the resulting plan. This object only holds the three knobs.
    """

    def __init__(
        self,
        max_summaries: int,
        protect_last: int,
        min_tokens: int,
    ) -> None:
        # Clamp to sane, fail-open values (never raise on a bad number).
        self.max_summaries = _clamp_nonneg_int(
            max_summaries, DEFAULT_SUMMARIZE_MAX_PER_PASS)
        self.protect_last = _clamp_nonneg_int(
            protect_last, DEFAULT_SUMMARIZE_PROTECT_LAST)
        self.min_tokens = _clamp_nonneg_int(
            min_tokens, DEFAULT_SUMMARIZE_MIN_TOKENS)


def _clamp_nonneg_int(value: Any, fallback: int) -> int:
    """Coerce `value` to an int >= 0; `fallback` on any malformed input."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return fallback
    return 0 if n < 0 else n


def load_summarization_policy_from_env(
    env: Optional[Dict[str, str]] = None,
) -> Optional[SummarizationPolicy]:
    """Build a SummarizationPolicy from env, or None when the feature is OFF.

    OFF (returns None) unless `CEO_SUMMARIZE_OLDEST` is set to a positive int
    (the per-pass budget). Other knobs fall back to documented defaults when
    unset/invalid. Fail-open: never raises.
    """
    budget = _env_int(ENV_SUMMARIZE_OLDEST, env)
    if budget is None or budget <= 0:
        return None  # default-OFF
    protect = _env_int(ENV_SUMMARIZE_PROTECT_LAST, env)
    min_tokens = _env_int(ENV_SUMMARIZE_MIN_TOKENS, env)
    return SummarizationPolicy(
        max_summaries=budget,
        protect_last=protect if protect is not None else DEFAULT_SUMMARIZE_PROTECT_LAST,
        min_tokens=min_tokens if min_tokens is not None else DEFAULT_SUMMARIZE_MIN_TOKENS,
    )


def _output_token_size(record: Any) -> Optional[int]:
    """Best-effort estimated token size of one subagent-output record.

    Accepts either a mapping with an ``est_tokens`` (preferred) or ``tokens``
    or ``chars`` field, or a bare int (already a token count). Returns None when
    no size can be derived (the record is then treated as below-floor and never
    selected — fail-open: a record we cannot size is never summarized).
    """
    if isinstance(record, bool):
        # bool is an int subclass — reject it as a meaningless size.
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
    return None


def decide_summarization(
    outputs: Any,
    *,
    policy: Optional[SummarizationPolicy] = None,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Decide which oldest verbose subagent outputs to digest on the cheap tier.

    Pure + side-effect-free + fail-open. PROTECTS the last N outputs.

    Parameters
    ----------
    outputs
        An ordered sequence of subagent-output records, OLDEST FIRST (index 0
        is the oldest, index ``len-1`` the most recent). Each record may be a
        mapping carrying an estimated size (``est_tokens`` / ``tokens`` /
        ``chars``) or a bare int token count. The order is the ONLY thing that
        determines age; the host supplies it.
    policy
        Explicit policy; when None, derived from `env` (default-OFF if the
        budget env is unset/invalid).

    Returns a plan dict (never raises):
      {
        "enabled": bool,            # feature active
        "reason": <SUMM_REASON_*>,  # stable plan-level reason code
        "selected": [int, ...],     # indices to summarize (oldest first)
        "selected_count": int,
        "reclaim_tokens": int,      # est tokens the selected digests would free
        "candidate_count": int,     # eligible-before-budget count
        "total_count": int,         # len(outputs)
        "protect_last": int|None,
        "min_tokens": int|None,
        "max_summaries": int|None,
        "skipped": [                # per-index skip provenance (closed reasons)
          {"index": int, "reason": <SUMM_SKIP_*>}, ...
        ],
      }

    NO payload echo: the plan carries ONLY integer indices + token-size buckets
    + closed reason codes. It NEVER includes any output text, agent name, file
    path, or command bytes. The canonical emit (staged proposal) scrubs to the
    same closed-field allowlist.
    """
    plan: Dict[str, Any] = {
        "enabled": False,
        "reason": SUMM_REASON_DISABLED,
        "selected": [],
        "selected_count": 0,
        "reclaim_tokens": 0,
        "candidate_count": 0,
        "total_count": 0,
        "protect_last": None,
        "min_tokens": None,
        "max_summaries": None,
        "skipped": [],
    }

    if policy is None:
        policy = load_summarization_policy_from_env(env)
    if policy is None:
        return plan  # default-OFF — disabled plan

    plan["enabled"] = True
    plan["protect_last"] = policy.protect_last
    plan["min_tokens"] = policy.min_tokens
    plan["max_summaries"] = policy.max_summaries

    # Normalize the outputs list (fail-open: a non-sequence ⇒ empty).
    try:
        items = list(outputs)
    except TypeError:
        items = []
    total = len(items)
    plan["total_count"] = total
    if total == 0:
        plan["reason"] = SUMM_REASON_NO_CANDIDATES
        return plan

    # The protected window is the last `protect_last` indices (the recent
    # working set). Everything strictly before it is age-eligible.
    protect_last = policy.protect_last
    protect_from = max(0, total - protect_last) if protect_last > 0 else total
    # `protect_from` is the first PROTECTED index; indices [0, protect_from) are
    # age-eligible candidates (oldest first).

    candidates: List[Tuple[int, int]] = []  # (index, est_tokens) oldest first
    for idx in range(total):
        if idx >= protect_from:
            # Within the protected last-N working set — never eligible.
            plan["skipped"].append(
                {"index": idx, "reason": SUMM_SKIP_PROTECTED})
            continue
        size = _output_token_size(items[idx])
        if size is None or size < policy.min_tokens:
            # Under the verbosity floor (or unsizeable) — not worth a cheap call.
            plan["skipped"].append(
                {"index": idx, "reason": SUMM_SKIP_BELOW_FLOOR})
            continue
        candidates.append((idx, size))

    plan["candidate_count"] = len(candidates)
    if not candidates:
        plan["reason"] = SUMM_REASON_NO_CANDIDATES
        return plan

    # Select the OLDEST-first candidates up to the per-pass budget. Candidates
    # are already in ascending-index (oldest-first) order; honoring that keeps
    # the selection deterministic and biased to the oldest outputs (the AC).
    budget = policy.max_summaries
    selected: List[int] = []
    reclaim = 0
    for pos, (idx, size) in enumerate(candidates):
        if budget > 0 and len(selected) >= budget:
            # Eligible but past the per-pass cap — deferred, not lost.
            plan["skipped"].append(
                {"index": idx, "reason": SUMM_SKIP_OVER_BUDGET})
            continue
        selected.append(idx)
        reclaim += size

    plan["selected"] = selected
    plan["selected_count"] = len(selected)
    plan["reclaim_tokens"] = reclaim
    plan["reason"] = SUMM_REASON_SELECTED if selected else SUMM_REASON_NO_CANDIDATES
    # Keep the skip provenance deterministically ordered by index.
    plan["skipped"].sort(key=lambda s: s["index"])
    return plan


