"""PLAN-017 Phase 1 tests — file assignment (anti-collision)."""

from __future__ import annotations

import pytest

from ..file_assignment import (
    FileAssignmentResult,
    assign_files,
    partition_by_prefix,
)


def test_assign_files_disjoint_returns_ok() -> None:
    proposal = {
        "L1": ["a.py", "b.py"],
        "L2": ["c.py", "d.py"],
    }
    r = assign_files(proposal)
    assert r.ok is True
    assert r.collisions == []
    assert r.assignments["L1"] == ["a.py", "b.py"]
    assert r.assignments["L2"] == ["c.py", "d.py"]


def test_assign_files_collision_reports_pair() -> None:
    proposal = {
        "L1": ["a.py", "b.py"],
        "L2": ["b.py", "c.py"],
    }
    r = assign_files(proposal)
    assert r.ok is False
    assert r.collisions == [("L1", "L2", ["b.py"])]


def test_assign_files_multi_way_collision() -> None:
    proposal = {
        "L1": ["a.py"],
        "L2": ["a.py"],
        "L3": ["a.py"],
    }
    r = assign_files(proposal)
    assert r.ok is False
    # (L1,L2), (L1,L3), (L2,L3) pairs.
    assert len(r.collisions) == 3


def test_assign_files_empty_input() -> None:
    r = assign_files({})
    assert r.ok is True
    assert r.assignments == {}


def test_assign_files_dedup_within_loop() -> None:
    # Duplicates within a single loop's own assignment aren't a collision;
    # they just get deduplicated.
    r = assign_files({"L1": ["a.py", "a.py", "b.py"]})
    assert r.ok is True
    assert r.assignments["L1"] == ["a.py", "b.py"]


def test_assign_files_strips_empty_paths() -> None:
    r = assign_files({"L1": ["a.py", "", "b.py"]})
    assert r.ok is True
    assert r.assignments["L1"] == ["a.py", "b.py"]


def test_collision_summary_text() -> None:
    proposal = {"L1": ["a.py"], "L2": ["a.py"]}
    r = assign_files(proposal)
    assert "L1↔L2" in r.collision_summary()
    assert "a.py" in r.collision_summary()


def test_collision_summary_ok_branch() -> None:
    r = assign_files({"L1": ["a.py"]})
    assert r.collision_summary() == "no_collisions"


def test_partition_by_prefix_round_robin() -> None:
    assigned = partition_by_prefix(["L1", "L2"], ["a.py", "b.py", "c.py", "d.py"])
    assert assigned["L1"] == ["a.py", "c.py"]
    assert assigned["L2"] == ["b.py", "d.py"]


def test_partition_by_prefix_rejects_empty_loops() -> None:
    with pytest.raises(ValueError):
        partition_by_prefix([], ["a.py"])


def test_partition_by_prefix_dedup_and_sort() -> None:
    assigned = partition_by_prefix(["L1"], ["b.py", "a.py", "a.py"])
    assert assigned["L1"] == ["a.py", "b.py"]


def test_file_assignment_result_dataclass_fields() -> None:
    r = FileAssignmentResult(ok=True, assignments={}, collisions=[])
    assert r.ok is True
    assert r.assignments == {}
    assert r.collisions == []
