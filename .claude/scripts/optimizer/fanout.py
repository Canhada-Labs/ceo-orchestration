"""WS-2(b)+(c) — fan-out recommender + budget governor + token-rate governor.

Decomposes a parallelizable prompt into a bounded sub-task list, assigns each a
model via :func:`optimizer.model_choice.choose`, then governs the suggested width
by (i) a **budget ceiling** (estimated total input tokens vs
``CEO_FANOUT_BUDGET_TOKENS``) and (ii) an **ITPM/OTPM rate ceiling** that backs
off because heavy fan-out hits account-wide 429s (the framework already emits
``anthropic_429_observed`` — PLAN-122 §6 convergence). It reads recent 429
pressure best-effort to decide backoff. It **NEVER dispatches** — it only returns
a :class:`optimizer.types.FanoutPlan`. Nothing here raises into the caller.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Optional, Tuple

from . import model_choice
from ._skeleton import env_int, estimate_tokens, kill_switch_off
from .types import (
    FanoutPlan,
    MAX_FANOUT_WIDTH,
    SubTask,
    ROUTE_FANOUT,
)

# Bounded splitters (pre-compiled). Same enumeration signals as the gate, kept
# local so this leaf imports no sibling but model_choice.
_RE_LIST_ITEM = re.compile(r"(?m)^\s{0,8}(?:\d{1,3}[.)]|[-*•])\s+(.+?)\s*$")
# Inline numbered marker (mirrors complexity_gate._RE_INLINE_NUM); used to SPLIT
# a single-line "1. x 2. y 3. z" enumeration. No capturing group → safe re.split.
_RE_INLINE_SPLIT = re.compile(r"(?<![\d.])\b\d{1,2}[.)]\s+")
_RE_SENTENCE = re.compile(r"[^.;\n]+(?:[.;\n]|$)")
_SCAN_CAP = 20000

# True-ish env values for the manual rate-pressure override (tests / ops).
_TRUE_VALUES = frozenset({"1", "true", "on", "yes"})
_FALSE_VALUES = frozenset({"0", "false", "off", "no"})


def decompose(prompt: str, max_units: int) -> Tuple[SubTask, ...]:
    """Pure bounded split of ``prompt`` into ≤ ``max_units`` labelled SubTasks.

    Prefers explicit list items (numbered/bulleted); falls back to sentence-ish
    segments. Each SubTask gets ``est_tokens_in`` via ``estimate_tokens`` and a
    model via ``model_choice.choose``. Deterministic; never raises.
    """
    try:
        cap = max(1, min(int(max_units), MAX_FANOUT_WIDTH))
        text = prompt[:_SCAN_CAP]
        items = [m.strip() for m in _RE_LIST_ITEM.findall(text) if m.strip()]
        if len(items) < 2:
            # Inline numbered enumeration ("... 1. x 2. y 3. z"): split on the
            # markers. raw[0] is the (possibly empty) preamble before the first
            # marker; raw[1:] are the item bodies. Index BEFORE filtering empties
            # so the first item is NOT lost when the prompt starts on "1."
            # (off-by-one caught by the multi-lens review).
            raw = _RE_INLINE_SPLIT.split(text)
            if len(raw) >= 3:  # >= 2 inline markers
                items = [s.strip() for s in raw[1:] if s.strip()]
        if len(items) < 2:
            items = [s.strip() for s in _RE_SENTENCE.findall(text) if len(s.strip()) >= 8]
        if not items:
            items = [text.strip() or "task"]
        items = items[:cap]

        subtasks: List[SubTask] = []
        for i, label in enumerate(items):
            est = estimate_tokens(label)
            choice = model_choice.choose(context_size=est)
            subtasks.append(
                SubTask(
                    index=i,
                    label=label[:120],
                    model=choice.model or "",
                    est_tokens_in=est,
                    confidence_basis_points=choice.confidence_basis_points,
                    cost_governed=choice.cost_governed,
                    fell_back_to_static=choice.fell_back_to_static,
                )
            )
        return tuple(subtasks)
    except Exception:
        return ()


def width_governor(requested_width: int, est_total_tokens_in: int) -> Tuple[int, bool, bool]:
    """Return ``(governed_width, width_capped, budget_governed)``.

    Caps by (1) the hard ceiling ``MAX_FANOUT_WIDTH`` and (2) the token budget:
    if the estimated total input tokens exceed ``CEO_FANOUT_BUDGET_TOKENS``,
    shrink the width proportionally so the per-task budget stays in band. Pure.
    """
    try:
        requested = max(1, int(requested_width))
        governed = min(requested, MAX_FANOUT_WIDTH)
        budget_governed = False

        budget = env_int("CEO_FANOUT_BUDGET_TOKENS", 400000, 10000, 20000000)
        total = max(0, int(est_total_tokens_in))
        if total > budget and total > 0:
            scaled = int(governed * budget / total)
            governed = max(1, min(governed, scaled))
            budget_governed = True

        width_capped = governed < requested
        return governed, width_capped, budget_governed
    except Exception:
        # True fail-open: a non-int / unexpected input must yield a safe literal,
        # not re-evaluate the bad input. Conservative: width 1, governed.
        return 1, True, True


def recent_429_pressure() -> bool:
    """Best-effort, bounded check for recent account-wide 429 pressure.

    Honours an explicit ``CEO_RATE_PRESSURE`` override (deterministic for tests /
    ops); otherwise reads only the TAIL of the audit log for a recent
    ``anthropic_429_observed`` event. Bounded (tail-only); fail-open to False on
    ANY error so it can never block or slow the optimizer.
    """
    try:
        forced = os.environ.get("CEO_RATE_PRESSURE", "").strip().lower()
        if forced in _TRUE_VALUES:
            return True
        if forced in _FALSE_VALUES:
            return False
        path = _audit_log_path()
        if path is None or not path.exists():
            return False
        for line in _tail_lines(path, 200):
            if "anthropic_429_observed" in line:
                return True
        return False
    except Exception:
        return False


def rate_backoff(governed_width: int, est_tokens_per_task: int) -> Tuple[int, bool]:
    """Token-RATE concurrency governor. Return ``(final_width, backoff_applied)``.

    Projects in-flight ITPM/OTPM = ``width * per-task`` against the account
    ceilings (``CEO_ITPM_CEILING`` / ``CEO_OTPM_CEILING``) and, if the projection
    exceeds either ceiling OR ``recent_429_pressure()`` is True, halves the width
    until under the ceiling (min 1). ``os.environ``-only knobs. Never raises.
    """
    try:
        width = max(1, int(governed_width))
        per_task_in = max(1, int(est_tokens_per_task))
        per_task_out = max(1, per_task_in // 4)  # rough output proxy

        itpm = env_int("CEO_ITPM_CEILING", 400000, 10000, 50000000)
        otpm = env_int("CEO_OTPM_CEILING", 80000, 2000, 20000000)
        pressure = recent_429_pressure()

        def over(w: int) -> bool:
            return (w * per_task_in) > itpm or (w * per_task_out) > otpm

        backoff = False
        if pressure and width > 1:
            width = max(1, width // 2)
            backoff = True
        while width > 1 and over(width):
            width = max(1, width // 2)
            backoff = True
        return width, backoff
    except Exception:
        # True fail-open: safe literal, never re-evaluate the bad input.
        return 1, True


def plan(prompt: str, gate) -> Optional[FanoutPlan]:
    """Build a :class:`FanoutPlan` from a fan-out gate verdict, or None.

    Returns None when the gate did not route to fan-out OR ``CEO_FANOUT`` is off.
    Otherwise decomposes, governs the width by budget then by token-rate, and
    returns the plan. NEVER dispatches; never raises.
    """
    try:
        if getattr(gate, "route", None) != ROUTE_FANOUT:
            return None
        if kill_switch_off("CEO_FANOUT"):
            return None

        requested = max(2, int(getattr(gate, "suggested_width", 2)))
        subtasks = decompose(prompt, requested)
        if not subtasks:
            return None

        est_total = sum(st.est_tokens_in for st in subtasks)
        governed, width_capped, budget_governed = width_governor(requested, est_total)
        est_per_task = max(1, est_total // max(1, len(subtasks)))
        final_width, backoff = rate_backoff(governed, est_per_task)
        return FanoutPlan(
            subtasks=subtasks,
            suggested_width=final_width,
            width_capped=width_capped or (final_width < requested),
            budget_governed=budget_governed,
            rate_backoff_applied=backoff,
        )
    except Exception:
        return None


# --- bounded audit-log tail helpers (best-effort) ---------------------------

def _audit_log_path() -> Optional[Path]:
    """Locate the audit log without importing _lib. Honours the test-isolation
    redirect (``CEO_AUDIT_LOG_DIR``) so this never touches the live chain under
    pytest. Returns None if not locatable."""
    try:
        env_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
        if env_dir:
            return Path(env_dir) / "audit-log.jsonl"
        # Adopter-correct: derive the project slug from CLAUDE_PROJECT_DIR rather
        # than hardcoding "ceo-orchestration" (which makes the 429-backoff
        # silently inoperative in any other repo — multi-lens review).
        proj = os.environ.get("CLAUDE_PROJECT_DIR")
        home = os.environ.get("HOME")
        if proj:
            slug = Path(proj).name
            if home:
                return Path(home) / ".claude" / "projects" / slug / "audit-log.jsonl"
        if not home:
            return None
        return Path(home) / ".claude" / "projects" / "ceo-orchestration" / "audit-log.jsonl"
    except Exception:
        return None


def _tail_lines(path: Path, n: int) -> List[str]:
    """Return up to the last ``n`` lines of ``path`` with a bounded read.

    Reads at most a fixed byte window from the end so a huge log cannot blow the
    latency budget. Best-effort; returns [] on any error.
    """
    try:
        window = 64 * 1024  # 64 KiB tail is plenty for ~200 short JSONL lines.
        size = path.stat().st_size
        with path.open("rb") as fh:
            if size > window:
                fh.seek(size - window)
            data = fh.read()
        text = data.decode("utf-8", errors="replace")
        return text.splitlines()[-n:]
    except Exception:
        return []
