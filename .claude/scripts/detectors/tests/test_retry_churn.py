"""PLAN-047 Phase 1 — tests for retry_churn detector."""
from __future__ import annotations

from ..retry_churn import detect
from .fixtures import (
    events_negative_retry_churn_different_bucket,
    events_negative_retry_churn_different_subagent,
    events_negative_retry_churn_over_window,
    events_negative_retry_churn_too_few,
    events_positive_retry_churn,
    make_event,
    write_log,
)


# -------- positive cases --------

def test_positive_three_spawns_within_window(tmp_path):
    log = write_log(tmp_path, events_positive_retry_churn())
    findings = detect(log)
    assert len(findings) == 1
    assert findings[0].detector == "retry_churn"
    assert findings[0].severity == "warning"
    assert findings[0].session_id == "sess-R"
    assert findings[0].evidence["spawn_count"] == 3
    assert findings[0].evidence["subagent_type"] == "code-reviewer"


def test_positive_emits_three_audit_spans(tmp_path):
    log = write_log(tmp_path, events_positive_retry_churn())
    findings = detect(log)
    assert len(findings[0].audit_spans) == 3


def test_positive_five_spawns_same_bucket(tmp_path):
    events = [
        make_event(
            offset_minutes=float(idx * 5),
            session_id="sess-X",
            subagent_type="Explore",
            skill="code-review-checklist",
            prompt_len_bucket="<4096",
            desc_seed=f"rc-{idx}",
        )
        for idx in range(5)
    ]
    log = write_log(tmp_path, events)
    findings = detect(log)
    assert len(findings) == 1
    assert findings[0].evidence["spawn_count"] == 5


def test_positive_two_groups_emit_two_findings(tmp_path):
    a = events_positive_retry_churn()
    b = [
        make_event(
            offset_minutes=float(idx * 5),
            session_id="sess-Y",
            subagent_type="qa-architect",
            skill="testing-strategy",
            prompt_len_bucket="<4096",
            desc_seed=f"rc-y-{idx}",
        )
        for idx in range(3)
    ]
    log = write_log(tmp_path, a + b)
    findings = detect(log)
    assert len(findings) == 2


def test_positive_recommendation_mentions_count_and_subagent(tmp_path):
    log = write_log(tmp_path, events_positive_retry_churn())
    findings = detect(log)
    assert "3 spawns" in findings[0].recommendation
    assert "code-reviewer" in findings[0].recommendation


# -------- negative cases --------

def test_negative_only_two_spawns(tmp_path):
    log = write_log(tmp_path, events_negative_retry_churn_too_few())
    assert detect(log) == []


def test_negative_different_subagent(tmp_path):
    log = write_log(tmp_path, events_negative_retry_churn_different_subagent())
    assert detect(log) == []


def test_negative_outside_window(tmp_path):
    log = write_log(tmp_path, events_negative_retry_churn_over_window())
    assert detect(log) == []


def test_negative_different_bucket(tmp_path):
    log = write_log(tmp_path, events_negative_retry_churn_different_bucket())
    assert detect(log) == []


def test_negative_missing_log_returns_empty(tmp_path):
    assert detect(tmp_path / "no-such-log.jsonl") == []
