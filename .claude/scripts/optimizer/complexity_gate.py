"""WS-1 — the pure-heuristic parallelizability / complexity gate.

CI-enforced p99 < 5ms (see ``.claude/scripts/tests/perf/
test_optimizer_complexity_gate_p99.py``). Routes on **PARALLELIZABILITY**, not
just raw complexity: a long-but-serial refactor stays ``single_agent``; an
enumerable multi-file audit goes ``fanout``. ``CEO_OPTIMIZER`` off →
``ROUTE_PASSTHROUGH`` (full pass-through, pure raw Claude).

All regexes are pre-compiled at module load with BOUNDED char classes (mirrors
``UserPromptSubmit.py`` discipline) and scanning is capped to ``_SCAN_CAP`` chars,
so per-call cost is deterministic and independent of prompt size. NO unbounded
regex, NO LLM call, NO IO. ``classify`` never raises.
"""

from __future__ import annotations

import re

from ._skeleton import optimizer_enabled
from .types import (
    COMPLEXITY_COMPLEX,
    COMPLEXITY_MODERATE,
    COMPLEXITY_SIMPLE,
    COMPLEXITY_TRIVIAL,
    GateResult,
    MAX_FANOUT_WIDTH,
    MAX_UNIT_COUNT,
    ROUTE_FANOUT,
    ROUTE_PASSTHROUGH,
    ROUTE_SINGLE,
)

# Cap regex scanning so a pathological 1MB prompt cannot blow the latency budget.
_SCAN_CAP = 20000

# --- Pre-compiled BOUNDED patterns ------------------------------------------
# Numbered list items: "1. ", "2) " at line start.
_RE_NUMBERED = re.compile(r"(?m)^\s{0,8}\d{1,3}[.)]\s")
# Inline numbered items: "... 1. add x 2. add y ...". The lookbehind blocks
# version strings ("1.2.3") and the trailing \s+ blocks "line 4 of" (no punct).
_RE_INLINE_NUM = re.compile(r"(?<![\d.])\b\d{1,2}[.)]\s+\S")
# Bullet items: "- ", "* ", "• " at line start.
_RE_BULLET = re.compile(r"(?m)^\s{0,8}[-*•]\s")
# File-path-ish tokens with a known code/doc extension (bounded stem length).
_RE_FILE = re.compile(
    r"\b[\w./-]{1,80}\."
    r"(?:py|js|ts|tsx|jsx|md|ya?ml|json|sh|go|rs|java|rb|c|cpp|h|hpp|txt|toml|cfg)\b"
)
# Parallel/aggregative conjunctions (independent units joined): "and", "plus",
# "also", "as well as". Bounded word boundaries.
_RE_PARALLEL_CONJ = re.compile(r"\b(?:and|plus|also|as well as)\b", re.IGNORECASE)
# Serial-dependency markers — their presence SUPPRESSES parallelizability.
# NOTE: the "first ... then" sequence is handled by a SEPARATE bounded check
# (_has_first_then) — NOT an `.*?` arm here, which would catastrophically
# backtrack on adversarial input ('first '*N with no 'then') and breach the
# hot-path latency budget (multi-lens review P0).
_RE_SERIAL = re.compile(
    r"\b(?:then|afterwards?|once|subsequently|finally|sequential(?:ly)?|"
    r"depends? on|in order|step\s*\d)\b",
    re.IGNORECASE,
)
# Bounded "first ... then" detector — at most 500 chars between the two words,
# and only runs when BOTH words are present (cheap pre-filter in _has_serial).
_RE_FIRST_THEN = re.compile(r"\bfirst\b.{0,500}?\bthen\b", re.IGNORECASE | re.DOTALL)


def _has_serial(text: str) -> bool:
    """True if a serial-dependency marker is present. Bounded; never catastrophic."""
    if _RE_SERIAL.search(text) is not None:
        return True
    low = text.lower()
    # Cheap pre-filter: only run the bounded first/then regex when both appear.
    if "first" in low and "then" in low:
        return _RE_FIRST_THEN.search(text) is not None
    return False
# High-complexity scope keywords (whole-repo / sweeping work).
_RE_SCOPE = re.compile(
    r"\b(?:refactor|migrat\w+|audit|across|entire|comprehensive|every|all\s+"
    r"(?:files?|modules?|tests?|endpoints?)|whole|codebase|end-to-end)\b",
    re.IGNORECASE,
)


def _estimate_unit_count(prompt: str) -> int:
    """Bounded count of independently-parallelizable units from enumerations.

    Takes the strongest enumeration signal (numbered ≈ bullet ≈ file-mentions ≈
    parallel-conjunctions+1) and caps at ``MAX_UNIT_COUNT``. Pure, never raises.
    """
    text = prompt[:_SCAN_CAP]
    numbered = len(_RE_NUMBERED.findall(text))
    inline_num = len(_RE_INLINE_NUM.findall(text))
    bullets = len(_RE_BULLET.findall(text))
    files = len(set(_RE_FILE.findall(text))) if files_enabled(text) else 0
    conj = len(_RE_PARALLEL_CONJ.findall(text))
    structural = max(numbered, inline_num, bullets, files)
    # A bare conjunction ("fix X and update Y and run Z") with NO enumeration
    # structure is NOT a fan-out signal — counting it caused systematic
    # false-positives (multi-lens review). Only let conjunctions BOOST an
    # already-structured prompt.
    conj_units = (conj + 1) if (conj and structural > 0) else 0
    units = max(structural, conj_units)
    return max(0, min(MAX_UNIT_COUNT, units))


def files_enabled(text: str) -> bool:
    """Cheap pre-check so the (slightly heavier) file regex only runs when a
    dot-extension could plausibly be present. Keeps the common no-file prompt
    off the file scan. Pure."""
    return "." in text


def _complexity_rank(prompt: str, unit_count: int) -> int:
    """Return a 0..3 complexity rank from bounded signals."""
    text = prompt[:_SCAN_CAP]
    length = len(prompt)  # O(1); use full length as the size signal.
    if length < 80:
        rank = 0
    elif length < 240:
        rank = 1
    elif length < 800:
        rank = 2
    else:
        rank = 3
    if unit_count >= 4:
        rank = max(rank, 3)
    elif unit_count >= 2:
        rank = max(rank, 2)
    if _RE_SCOPE.search(text):
        rank = min(3, rank + 1)
    return max(0, min(3, rank))


_RANK_TO_BUCKET = (
    COMPLEXITY_TRIVIAL,
    COMPLEXITY_SIMPLE,
    COMPLEXITY_MODERATE,
    COMPLEXITY_COMPLEX,
)


def classify(prompt: str) -> GateResult:
    """Pure-heuristic WS-1 verdict. Never raises.

    ``CEO_OPTIMIZER`` off → ``ROUTE_PASSTHROUGH``. Otherwise: estimate
    parallelizable unit count, derive a complexity bucket, decide
    parallelizability (enumerable units AND no serial-dependency markers), and
    route — ``fanout`` only when parallelizable AND complexity ≥ moderate.
    """
    try:
        if not optimizer_enabled():
            return GateResult(
                route=ROUTE_PASSTHROUGH,
                complexity=COMPLEXITY_TRIVIAL,
                parallelizable=False,
                suggested_width=1,
                reason="kill_switch:CEO_OPTIMIZER",
            )
        if not isinstance(prompt, str) or not prompt.strip():
            return GateResult(
                route=ROUTE_PASSTHROUGH,
                complexity=COMPLEXITY_TRIVIAL,
                parallelizable=False,
                suggested_width=1,
                reason="empty_prompt",
            )

        unit_count = _estimate_unit_count(prompt)
        rank = _complexity_rank(prompt, unit_count)
        bucket = _RANK_TO_BUCKET[rank]

        has_serial = _has_serial(prompt[:_SCAN_CAP])
        parallelizable = (unit_count >= 2) and not has_serial

        if rank == 0:
            route = ROUTE_PASSTHROUGH
            reason = "trivial"
        elif parallelizable and rank >= 2:
            route = ROUTE_FANOUT
            reason = "parallelizable_units=%d" % unit_count
        else:
            route = ROUTE_SINGLE
            reason = (
                "serial_dependency" if has_serial
                else "below_fanout_threshold"
            )

        suggested_width = (
            max(2, min(unit_count, MAX_FANOUT_WIDTH))
            if route == ROUTE_FANOUT else 1
        )
        return GateResult(
            route=route,
            complexity=bucket,
            parallelizable=parallelizable,
            suggested_width=suggested_width,
            reason=reason,
        )
    except Exception:
        # Fail-safe: a gate failure must never block — recommend the most
        # conservative non-optimizing route.
        return GateResult(
            route=ROUTE_SINGLE,
            complexity=COMPLEXITY_SIMPLE,
            parallelizable=False,
            suggested_width=1,
            reason="gate_error",
        )
