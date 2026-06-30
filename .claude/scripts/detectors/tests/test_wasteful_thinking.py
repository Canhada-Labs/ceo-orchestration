"""PLAN-047 Phase 1 — tests for wasteful_thinking detector."""
from __future__ import annotations

from ..wasteful_thinking import detect
from .fixtures import (
    events_negative_wasteful_thinking_haiku,
    events_negative_wasteful_thinking_large_bucket,
    events_negative_wasteful_thinking_non_opus,
    events_negative_wasteful_thinking_veto_subagent,
    events_positive_wasteful_thinking,
    make_event,
    write_log,
)


# -------- positive --------

def test_positive_two_offending_same_session(tmp_path):
    log = write_log(tmp_path, events_positive_wasteful_thinking())
    findings = detect(log)
    assert len(findings) == 1
    assert findings[0].detector == "wasteful_thinking"
    assert findings[0].severity == "info"
    assert findings[0].evidence["spawn_count"] == 2


def test_positive_subagent_breakdown_in_evidence(tmp_path):
    log = write_log(tmp_path, events_positive_wasteful_thinking())
    findings = detect(log)
    counts = findings[0].evidence["subagent_counts"]
    assert counts == {"Explore": 1, "general-purpose": 1}


def test_positive_two_sessions_two_findings(tmp_path):
    a = events_positive_wasteful_thinking()
    b = [
        make_event(
            session_id="sess-2",
            model="claude-opus-4-7",
            prompt_len_bucket="<256",
            subagent_type="Explore",
            desc_seed="wt-sess2",
        )
    ]
    log = write_log(tmp_path, a + b)
    findings = detect(log)
    assert len(findings) == 2
    assert {finding.session_id for finding in findings} == {"sess-1", "sess-2"}


def test_positive_bucket_counts_captured(tmp_path):
    log = write_log(tmp_path, events_positive_wasteful_thinking())
    findings = detect(log)
    assert findings[0].evidence["bucket_counts"] == {"<256": 1, "<1024": 1}


def test_positive_estimated_wasted_tokens(tmp_path):
    events = [
        make_event(
            model="claude-opus-4-7",
            prompt_len_bucket="<256",
            subagent_type="Explore",
            tokens_total=5000,
            desc_seed="wtk-a",
        ),
        make_event(
            model="claude-opus-4-7",
            prompt_len_bucket="<1024",
            subagent_type="Explore",
            tokens_total=7000,
            offset_minutes=1,
            desc_seed="wtk-b",
        ),
    ]
    log = write_log(tmp_path, events)
    findings = detect(log)
    assert findings[0].estimated_wasted_tokens == 12000


# -------- negative --------

def test_negative_large_bucket(tmp_path):
    log = write_log(tmp_path, events_negative_wasteful_thinking_large_bucket())
    assert detect(log) == []


def test_negative_veto_subagent(tmp_path):
    log = write_log(tmp_path, events_negative_wasteful_thinking_veto_subagent())
    assert detect(log) == []


def test_negative_sonnet_model(tmp_path):
    log = write_log(tmp_path, events_negative_wasteful_thinking_non_opus())
    assert detect(log) == []


def test_negative_haiku_model(tmp_path):
    log = write_log(tmp_path, events_negative_wasteful_thinking_haiku())
    assert detect(log) == []


def test_negative_missing_subagent_type(tmp_path):
    events = [
        make_event(
            model="claude-opus-4-7",
            prompt_len_bucket="<256",
            subagent_type="",
            desc_seed="empty-sa",
        )
    ]
    log = write_log(tmp_path, events)
    assert detect(log) == []
