"""PLAN-047 Phase 1 — tests for tool_cascade detector."""
from __future__ import annotations

from ..tool_cascade import detect
from .fixtures import (
    events_negative_tool_cascade_large_tokens,
    events_negative_tool_cascade_multi_session,
    events_negative_tool_cascade_non_object,
    events_negative_tool_cascade_too_few,
    events_positive_tool_cascade,
    make_event,
    write_log,
)


# -------- positive --------

def test_positive_five_spawn_cascade(tmp_path):
    log = write_log(tmp_path, events_positive_tool_cascade())
    findings = detect(log)
    assert len(findings) == 1
    assert findings[0].detector == "tool_cascade"
    assert findings[0].evidence["run_length"] == 5


def test_positive_ten_spawn_cascade(tmp_path):
    events = [
        make_event(
            offset_minutes=float(idx),
            session_id="sess-TC2",
            subagent_type="Explore",
            tokens_out=200,
            desc_seed=f"big-{idx}",
        )
        for idx in range(10)
    ]
    log = write_log(tmp_path, events)
    findings = detect(log)
    assert len(findings) == 1
    assert findings[0].evidence["run_length"] == 10


def test_positive_two_separate_runs(tmp_path):
    run_a = [
        make_event(
            offset_minutes=float(idx),
            session_id="sess-split",
            tokens_out=100,
            desc_seed=f"a-{idx}",
        )
        for idx in range(6)
    ]
    break_event = make_event(
        offset_minutes=7.0,
        session_id="sess-split",
        tokens_out=5000,
        desc_seed="break",
    )
    run_b = [
        make_event(
            offset_minutes=float(8 + idx),
            session_id="sess-split",
            tokens_out=150,
            desc_seed=f"b-{idx}",
        )
        for idx in range(5)
    ]
    log = write_log(tmp_path, run_a + [break_event] + run_b)
    findings = detect(log)
    assert len(findings) == 2
    assert findings[0].evidence["run_length"] == 6
    assert findings[1].evidence["run_length"] == 5


def test_positive_counts_estimated_wasted_tokens(tmp_path):
    events = [
        make_event(
            offset_minutes=float(idx),
            session_id="sess-cost",
            tokens_out=100,
            tokens_total=1000,
            desc_seed=f"c-{idx}",
        )
        for idx in range(5)
    ]
    log = write_log(tmp_path, events)
    findings = detect(log)
    assert findings[0].estimated_wasted_tokens == 5000


def test_positive_recommendation_mentions_session(tmp_path):
    log = write_log(tmp_path, events_positive_tool_cascade())
    findings = detect(log)
    assert "sess-TC" in findings[0].recommendation


# -------- negative --------

def test_negative_four_spawns_below_threshold(tmp_path):
    log = write_log(tmp_path, events_negative_tool_cascade_too_few())
    assert detect(log) == []


def test_negative_multi_session_fragmented(tmp_path):
    log = write_log(tmp_path, events_negative_tool_cascade_multi_session())
    # broken into 2 sub-runs of 2 events each per session → no ≥5 run
    assert detect(log) == []


def test_negative_large_tokens_disqualify(tmp_path):
    log = write_log(tmp_path, events_negative_tool_cascade_large_tokens())
    assert detect(log) == []


def test_negative_non_object_response_kind(tmp_path):
    log = write_log(tmp_path, events_negative_tool_cascade_non_object())
    assert detect(log) == []


def test_negative_null_tokens_out(tmp_path):
    events = [
        make_event(
            offset_minutes=float(idx),
            session_id="sess-null",
            tokens_out=None,
            desc_seed=f"n-{idx}",
        )
        for idx in range(8)
    ]
    log = write_log(tmp_path, events)
    assert detect(log) == []
