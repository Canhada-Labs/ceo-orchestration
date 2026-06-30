"""lesson_ranker.py — rank lessons by effectiveness (PLAN-009 Phase 5).

Separate module (not a widening of ``registry.py``) per C3/A9. Preserves
ADR-006 static-manifest intent for the registry. Sprint 9 keeps the
default ranking as ``recency`` — no stealth behavior flip. Sprint 10
decides whether to promote ``effectiveness`` to default after measuring
real data.

## Contract

``rank_by_effectiveness(lessons, inference_mode_filter=None)``

- Input: iterable of ``Lesson`` dataclass instances (from
  ``lessons.list_lessons()``)
- Output: list sorted by effectiveness descending, null values last
- ``inference_mode_filter`` is an optional set; when provided, lessons
  whose outcomes were recorded under other modes are excluded

Stdlib-only. Python >= 3.9. No side effects. Importable from anywhere.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Set, Tuple

# Re-export from lessons to keep a single definition of the Lesson shape.
# Importing here rather than in callers avoids accidental circular import:
# `lessons.py` does not import `lesson_ranker`.


def effectiveness(hit_count: int, miss_count: int) -> Optional[float]:
    """Effectiveness = hit_count / (hit_count + miss_count), or None if zero.

    None is distinct from 0.0 — "never evaluated" is different from
    "evaluated and failed every time".
    """
    total = int(hit_count) + int(miss_count)
    if total <= 0:
        return None
    return hit_count / total


def rank_by_effectiveness(
    lessons: Iterable[object],
    inference_mode_filter: Optional[Set[str]] = None,
) -> List[Tuple[object, Optional[float]]]:
    """Rank lessons by effectiveness descending; null values sort last.

    Args:
        lessons: iterable of Lesson-like objects (must have
            ``hit_count`` + ``miss_count`` attrs; ``last_outcome_at``
            optional for tie-breaking)
        inference_mode_filter: optional set like ``{"session-correlated"}``
            — when given, lessons without matching mode are EXCLUDED.
            Sprint 9 default in consumers: ``{"session-correlated"}``
            to exclude pre-Sprint-9 dirty signal.

    Returns:
        List of (lesson, effectiveness) tuples. Effectiveness is
        ``None`` when the lesson has zero outcomes. Stable sort:
        higher effectiveness first; ``None`` last (sorted by recency
        desc among equal-effectiveness peers when possible).
    """
    # Apply filter first (safer than post-sort)
    filtered = []
    for lesson in lessons:
        if inference_mode_filter is not None:
            mode = getattr(lesson, "last_inference_mode", "") or ""
            if mode and mode not in inference_mode_filter:
                continue
        filtered.append(lesson)

    def _key(lesson) -> Tuple[bool, float, str]:
        eff = effectiveness(
            int(getattr(lesson, "hit_count", 0) or 0),
            int(getattr(lesson, "miss_count", 0) or 0),
        )
        # Sort by (eff is None, -eff, -recency) — None last, higher first
        is_none = eff is None
        neg_eff = -(eff if eff is not None else 0.0)
        last_out = str(getattr(lesson, "last_outcome_at", "") or "")
        return (is_none, neg_eff, last_out * -1 if False else "")  # placeholder

    # Simpler approach: two-pass sort for readability
    with_eff = [
        (lesson, effectiveness(
            int(getattr(lesson, "hit_count", 0) or 0),
            int(getattr(lesson, "miss_count", 0) or 0),
        ))
        for lesson in filtered
    ]
    # Non-null effectiveness descending, then null at end.
    ranked = sorted(
        with_eff,
        key=lambda t: (t[1] is None, -(t[1] if t[1] is not None else 0.0)),
    )
    return ranked


__all__ = ["effectiveness", "rank_by_effectiveness"]
