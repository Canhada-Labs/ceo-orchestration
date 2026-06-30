"""PLAN-047 Phase 1 — tests for overpowered detector."""
from __future__ import annotations

from ..overpowered import detect
from .fixtures import (
    events_negative_overpowered_haiku,
    events_negative_overpowered_large_bucket,
    events_negative_overpowered_non_devops,
    events_negative_overpowered_null_model,
    events_positive_overpowered,
    make_event,
    write_log,
)


# -------- positive --------

def test_positive_opus_and_sonnet_on_devops(tmp_path):
    log = write_log(tmp_path, events_positive_overpowered())
    findings = detect(log)
    assert len(findings) == 1
    assert findings[0].detector == "overpowered"
    assert findings[0].severity == "info"
    assert findings[0].evidence["spawn_count"] == 2


def test_positive_model_breakdown(tmp_path):
    log = write_log(tmp_path, events_positive_overpowered())
    findings = detect(log)
    assert findings[0].evidence["model_counts"] == {
        "claude-opus-4-7": 1,
        "claude-sonnet-4-6": 1,
    }


def test_positive_bucket_breakdown(tmp_path):
    log = write_log(tmp_path, events_positive_overpowered())
    findings = detect(log)
    assert findings[0].evidence["bucket_counts"] == {"<256": 1, "<1024": 1}


def test_positive_estimated_wasted_tokens(tmp_path):
    events = [
        make_event(
            model="claude-opus-4-7",
            subagent_type="devops",
            prompt_len_bucket="<256",
            tokens_total=3000,
            desc_seed="op-a",
        ),
        make_event(
            model="claude-sonnet-4-6",
            subagent_type="devops",
            prompt_len_bucket="<1024",
            tokens_total=2500,
            offset_minutes=5,
            desc_seed="op-b",
        ),
    ]
    log = write_log(tmp_path, events)
    findings = detect(log)
    assert findings[0].estimated_wasted_tokens == 5500


def test_positive_two_sessions(tmp_path):
    a = events_positive_overpowered()
    b = [
        make_event(
            session_id="sess-dev2",
            model="claude-opus-4-7",
            subagent_type="devops",
            prompt_len_bucket="<256",
            desc_seed="op-s2",
        )
    ]
    log = write_log(tmp_path, a + b)
    findings = detect(log)
    assert len(findings) == 2


# -------- negative --------

def test_negative_haiku_on_devops_is_correct(tmp_path):
    log = write_log(tmp_path, events_negative_overpowered_haiku())
    assert detect(log) == []


def test_negative_non_devops_subagent(tmp_path):
    log = write_log(tmp_path, events_negative_overpowered_non_devops())
    assert detect(log) == []


def test_negative_large_prompt_bucket(tmp_path):
    log = write_log(tmp_path, events_negative_overpowered_large_bucket())
    assert detect(log) == []


def test_negative_null_model(tmp_path):
    log = write_log(tmp_path, events_negative_overpowered_null_model())
    assert detect(log) == []


def test_negative_devops_opus_large_bucket_ok(tmp_path):
    """Opus + devops is acceptable on LARGE prompts (complex infra work)."""
    events = [
        make_event(
            model="claude-opus-4-7",
            subagent_type="devops",
            prompt_len_bucket="<65536",
            desc_seed="op-big",
        )
    ]
    log = write_log(tmp_path, events)
    assert detect(log) == []
