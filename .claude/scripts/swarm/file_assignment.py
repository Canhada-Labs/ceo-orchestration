"""PLAN-017 Phase 1 — file assignment (anti-collision).

Compute disjoint file sets per loop, matching the anti-collision rule
in `team.md` §Step 0 (PROTOCOL.md §Spawn Protocol):

> Two agents NEVER edit the same file in parallel.

This module does NOT own the assignment — the coordinator + hypothesis
generator decide. This module validates the proposed assignment and
surfaces collisions deterministically so they can be reported to the
audit-log instead of silently overlapping.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set, Tuple


@dataclass
class FileAssignmentResult:
    """Verdict of ``assign_files``.

    ``ok`` is True iff no pair of loops shares a file. When False,
    ``collisions`` lists (loop_a, loop_b, shared_files_sorted) tuples
    and the caller MUST either (a) drop one loop, (b) merge, or (c)
    fall back to sequential execution.
    """

    ok: bool
    assignments: Dict[str, List[str]]
    collisions: List[Tuple[str, str, List[str]]]

    def collision_summary(self) -> str:
        if self.ok:
            return "no_collisions"
        parts: List[str] = []
        for a, b, files in self.collisions:
            parts.append(f"{a}↔{b}: {','.join(files)}")
        return "; ".join(parts)


def _normalize_paths(paths: List[str]) -> List[str]:
    """Deduplicate + sort for deterministic output. Drops empties."""

    seen: Set[str] = set()
    out: List[str] = []
    for p in paths:
        if not p:
            continue
        if p in seen:
            continue
        seen.add(p)
        out.append(p)
    return sorted(out)


def assign_files(proposed: Dict[str, List[str]]) -> FileAssignmentResult:
    """Validate a proposed per-loop file assignment.

    Does NOT mutate the input. Returns ``FileAssignmentResult`` with
    ``ok=True`` if all loops have disjoint file sets; else ``ok=False``
    and ``collisions`` enumerates the overlaps.

    Empty assignment (``{}``) is valid → ``ok=True`` with empty
    collisions list. A loop with an empty file list is also valid
    (it'll only touch in-memory state).
    """

    normalized: Dict[str, List[str]] = {
        loop_id: _normalize_paths(files) for loop_id, files in proposed.items()
    }
    ids = list(normalized.keys())
    collisions: List[Tuple[str, str, List[str]]] = []
    for i, a_id in enumerate(ids):
        a_set = set(normalized[a_id])
        for b_id in ids[i + 1 :]:
            b_set = set(normalized[b_id])
            overlap = a_set & b_set
            if overlap:
                collisions.append((a_id, b_id, sorted(overlap)))

    return FileAssignmentResult(
        ok=not collisions,
        assignments=normalized,
        collisions=collisions,
    )


def partition_by_prefix(
    loop_ids: List[str], candidate_files: List[str]
) -> Dict[str, List[str]]:
    """Round-robin partition of ``candidate_files`` across ``loop_ids``.

    Deterministic (sorts both inputs). Useful for scaffolded tests +
    for the default "no hypothesis generator" case — the coordinator
    calls this to get a starting assignment when the adopter hasn't
    supplied one.

    Raises ValueError if ``loop_ids`` is empty.
    """

    if not loop_ids:
        raise ValueError("loop_ids must not be empty")

    ids_sorted = sorted(loop_ids)
    files_sorted = sorted(dict.fromkeys(p for p in candidate_files if p))
    assignments: Dict[str, List[str]] = {lid: [] for lid in ids_sorted}
    for idx, path in enumerate(files_sorted):
        assignments[ids_sorted[idx % len(ids_sorted)]].append(path)
    return assignments
