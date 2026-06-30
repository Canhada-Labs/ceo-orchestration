"""PLAN-047 Phase 1 — tests for weak_model detector."""
from __future__ import annotations

from ..weak_model import detect
from .fixtures import (
    events_negative_weak_model_haiku_on_non_veto,
    events_negative_weak_model_null_model,
    events_negative_weak_model_opus_on_veto,
    events_negative_weak_model_sonnet_on_veto,
    events_positive_weak_model,
    make_event,
    write_log,
)


# -------- positive --------

def test_positive_haiku_on_code_reviewer_and_security(tmp_path):
    log = write_log(tmp_path, events_positive_weak_model())
    findings = detect(log)
    assert len(findings) == 1
    assert findings[0].detector == "weak_model"
    assert findings[0].severity == "warning"
    assert findings[0].evidence["spawn_count"] == 2


def test_positive_only_code_reviewer(tmp_path):
    events = [
        make_event(
            model="claude-haiku-4-5",
            subagent_type="code-reviewer",
            desc_seed="wm-single",
        )
    ]
    log = write_log(tmp_path, events)
    findings = detect(log)
    assert len(findings) == 1
    assert findings[0].evidence["subagent_counts"] == {"code-reviewer": 1}


def test_positive_two_sessions_two_findings(tmp_path):
    a = events_positive_weak_model()
    b = [
        make_event(
            session_id="sess-other",
            model="claude-haiku-4-5",
            subagent_type="security-engineer",
            desc_seed="wm-other",
        )
    ]
    log = write_log(tmp_path, a + b)
    findings = detect(log)
    sids = {finding.session_id for finding in findings}
    assert sids == {"sess-1", "sess-other"}


def test_positive_recommendation_mentions_expected_opus(tmp_path):
    log = write_log(tmp_path, events_positive_weak_model())
    findings = detect(log)
    assert "Opus" in findings[0].recommendation


def test_positive_audit_spans_populated(tmp_path):
    log = write_log(tmp_path, events_positive_weak_model())
    findings = detect(log)
    assert len(findings[0].audit_spans) == 2


# -------- negative --------

def test_negative_opus_on_veto_is_correct(tmp_path):
    log = write_log(tmp_path, events_negative_weak_model_opus_on_veto())
    assert detect(log) == []


def test_negative_haiku_on_non_veto_is_fine(tmp_path):
    log = write_log(tmp_path, events_negative_weak_model_haiku_on_non_veto())
    assert detect(log) == []


def test_negative_sonnet_on_veto_is_not_our_concern(tmp_path):
    log = write_log(tmp_path, events_negative_weak_model_sonnet_on_veto())
    # sonnet-on-veto is a governance concern but weak_model specifically
    # detects Haiku. Sonnet-on-VETO would be flagged by a different
    # detector (not in this sprint).
    assert detect(log) == []


def test_negative_null_model_does_not_trigger(tmp_path):
    log = write_log(tmp_path, events_negative_weak_model_null_model())
    assert detect(log) == []


def test_negative_non_agent_spawn_actions_ignored(tmp_path):
    events = [
        make_event(
            action="tool_use",  # not agent_spawn
            model="claude-haiku-4-5",
            subagent_type="code-reviewer",
            desc_seed="not-spawn",
        )
    ]
    log = write_log(tmp_path, events)
    assert detect(log) == []
