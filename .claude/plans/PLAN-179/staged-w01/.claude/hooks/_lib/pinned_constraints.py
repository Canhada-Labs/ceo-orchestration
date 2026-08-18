"""PLAN-179 W1-b (amendment r1-C5) — pinned governance constraints.

## Why this module exists

A POINTER is not a RESTRICTION. ADR-153's PostCompact half reinjects
pointers ("re-read CLAUDE.md", "the active plan is PLAN-NNN") — but the
measured Governance Decay failure (§2.2 of PLAN-179) is not "the model
forgot WHERE the rules live", it is "the rules themselves were summarized
away and the model then violated them". The mitigation is to quarantine a
SMALL, CLOSED set of invariants from the lossy compression and re-state
them verbatim after every compaction.

## Amendment r1-C5 — the set is a CODE CONSTANT, never disk-sourced

``PINNED_CONSTRAINTS`` is a literal tuple in this module. It is **never**
loaded from a ``.md`` (or any other file) at runtime. That is not a style
preference — it is what makes two claims TRUE by construction:

1. *"Not derived from disk"* — there is no file read on this path, so
   there is no window in which a compacted/edited/replaced document can
   change what the model is told the rules are.
2. *"Immune to Compaction-Eviction"* — the constant lives in code that is
   re-executed per hook invocation, outside the transcript the summarizer
   rewrites.

This module therefore performs **no file I/O whatsoever** — that property
is asserted by a test that scans this source. Changing the pinned set is a
canonical edit of ``.claude/hooks/_lib/`` and requires the Owner-signed
sentinel ceremony (ADR-031), which is exactly the friction the set
deserves.

## Cut criterion (OQ-2, answered in PLAN-179 W1-b)

Only invariants whose violation is **IRREVERSIBLE**. A big set re-creates
the context-floor problem the plan is trying to solve (§2.1), and a rule
that can be undone next turn does not need to survive compaction. Four
entries today; the ceiling is deliberately low.

## Public API

    from _lib.pinned_constraints import (
        PINNED_CONSTRAINTS,
        constraint_count,
        render_pinned_block,
    )

    lines = render_pinned_block()   # List[str] — labelled lines, not prose

``render_pinned_block`` returns a STRUCTURED payload: a list of
individually labelled lines. It never returns free text, so a consumer
(and a test) can count, index and assert on the entries instead of
pattern-matching a paragraph.

Stdlib only, Python >= 3.9.
"""

from __future__ import annotations

from typing import List, Tuple

# PLAN-179 W1-b [amendment r1-C5] — THE pinned set. A literal code constant:
# no file is consulted to build it, at import time or at call time. Keep this
# tuple small and irreversible-only (see the cut criterion in the docstring);
# every addition costs context on EVERY compaction of EVERY session.
PINNED_CONSTRAINTS: Tuple[str, ...] = (
    "PROTOCOL.md vetoes (ADR-052) are absolute. A fired veto is not a "
    "risk to accept, re-scope, or argue past — it stops the work until "
    "the Owner rules on it.",
    "Canonical-sentinel discipline (ADR-031): no edit to a canonical "
    "governance path without a matching Owner-signed sentinel. Never "
    "disable, weaken or route around the guard to land an edit.",
    "Never commit, push, tag or publish without explicit Owner "
    "authorization for that specific action.",
    "Fail-CLOSED on input inside a security matcher; fail-OPEN only on "
    "infrastructure error. Never invert the two to make a gate go green.",
)

# PLAN-179 W1-b — the block header is itself a labelled line so a consumer can
# strip it by index; it names the channel property that makes the block worth
# reading (these survived the compaction because they were never IN it).
_BLOCK_HEADER = (
    "PINNED GOVERNANCE CONSTRAINTS (PLAN-179 W1-b) — restated verbatim "
    "from code, not recalled from the transcript. Anything summarized "
    "away does NOT weaken these."
)

# Label prefix for each entry. Numbered n/N so a truncated block is detectable
# by the reader (and by the W1-b test) instead of silently looking complete.
_ENTRY_LABEL = "PINNED CONSTRAINT"


def constraint_count() -> int:
    """Return the number of pinned constraints (audit counter source).

    Kept as a function so the reinject hook reports the SET size rather than
    the rendered LINE count — the rendered block carries a header line, and
    an audit counter that drifts with formatting is not a counter."""
    return len(PINNED_CONSTRAINTS)


def render_pinned_block() -> List[str]:
    """Render the pinned set as a structured list of labelled lines.

    Returns one header line followed by one ``PINNED CONSTRAINT n/N: ...``
    line per entry. NEVER free text and NEVER a joined string — the caller
    owns the joining, and a test can assert per-entry rather than by
    substring search over a paragraph.

    PLAN-179 W1-b: there is deliberately no budget/truncation knob here.
    The constraint budget is SEPARATE from the pointer budget precisely so
    that the pointer cap can never eat a governance rule; a set small
    enough to satisfy the cut criterion does not need trimming."""
    total = len(PINNED_CONSTRAINTS)
    lines: List[str] = [_BLOCK_HEADER]
    for index, text in enumerate(PINNED_CONSTRAINTS, start=1):
        lines.append("%s %d/%d: %s" % (_ENTRY_LABEL, index, total, text))
    return lines


__all__ = [
    "PINNED_CONSTRAINTS",
    "constraint_count",
    "render_pinned_block",
]
