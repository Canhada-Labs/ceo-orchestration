"""PLAN-047 Phase 1 — tests for looping detector."""
from __future__ import annotations

from ..looping import detect
from .fixtures import (
    events_negative_looping_different_desc,
    events_negative_looping_different_subagent,
    events_negative_looping_no_file_assignment,
    events_negative_looping_too_few,
    events_positive_looping,
    make_event,
    write_log,
)


# -------- positive --------

def test_positive_three_same_subagent_same_prefix(tmp_path):
    log = write_log(tmp_path, events_positive_looping())
    findings = detect(log)
    assert len(findings) == 1
    assert findings[0].detector == "looping"
    assert findings[0].evidence["subagent_type"] == "qa-architect"
    assert findings[0].evidence["spawn_count"] == 3


def test_positive_four_spawns_extends_window(tmp_path):
    events = events_positive_looping() + [
        make_event(
            offset_minutes=20,
            subagent_type="qa-architect",
            has_file_assignment=True,
            desc_seed="loop-core",
        )
    ]
    log = write_log(tmp_path, events)
    findings = detect(log)
    assert findings[0].evidence["spawn_count"] == 4


def test_positive_two_groups(tmp_path):
    group_a = events_positive_looping()
    group_b = [
        make_event(
            offset_minutes=float(idx * 5),
            subagent_type="Explore",
            has_file_assignment=True,
            desc_seed="other-loop",
        )
        for idx in range(3)
    ]
    log = write_log(tmp_path, group_a + group_b)
    findings = detect(log)
    assert len(findings) == 2
    subagents = {finding.evidence["subagent_type"] for finding in findings}
    assert subagents == {"qa-architect", "Explore"}


def test_positive_session_id_set_when_unique(tmp_path):
    log = write_log(tmp_path, events_positive_looping())
    findings = detect(log)
    assert findings[0].session_id == "sess-1"


def test_positive_session_id_none_when_spread_across_sessions(tmp_path):
    events = events_positive_looping()
    events[1]["session_id"] = "sess-2"
    events[2]["session_id"] = "sess-3"
    log = write_log(tmp_path, events)
    findings = detect(log)
    assert findings[0].session_id is None
    assert findings[0].evidence["session_ids"] == ["sess-1", "sess-2", "sess-3"]


# -------- negative --------

def test_negative_two_spawns(tmp_path):
    log = write_log(tmp_path, events_negative_looping_too_few())
    assert detect(log) == []


def test_negative_different_subagent(tmp_path):
    log = write_log(tmp_path, events_negative_looping_different_subagent())
    # group sizes: 2 qa-architect (loop-core) + 1 Explore (loop-core)
    # both groups below threshold
    assert detect(log) == []


def test_negative_no_file_assignment(tmp_path):
    log = write_log(tmp_path, events_negative_looping_no_file_assignment())
    assert detect(log) == []


def test_negative_different_desc_prefix(tmp_path):
    log = write_log(tmp_path, events_negative_looping_different_desc())
    # SHA-256 of "alpha-task" vs "beta-task" vs "gamma-task" have distinct
    # first-8-hex prefixes → three single-event groups
    assert detect(log) == []


def test_negative_outside_window(tmp_path):
    events = [
        make_event(
            offset_minutes=0,
            subagent_type="qa-architect",
            has_file_assignment=True,
            desc_seed="loop-core",
        ),
        make_event(
            offset_minutes=10,
            subagent_type="qa-architect",
            has_file_assignment=True,
            desc_seed="loop-core",
        ),
        make_event(
            offset_minutes=45,  # beyond 30min from first
            subagent_type="qa-architect",
            has_file_assignment=True,
            desc_seed="loop-core",
        ),
    ]
    log = write_log(tmp_path, events)
    # best window size = 2 (either events 0+1 or 1+2 alone? 1→2 is 35min gap → 1 alone)
    assert detect(log) == []
