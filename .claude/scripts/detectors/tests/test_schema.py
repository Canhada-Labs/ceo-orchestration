"""PLAN-047 Phase 1 — tests for detectors.schema."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from ..schema import (
    Finding,
    emit_findings,
    is_agent_spawn,
    iter_events,
    parse_ts,
)


def test_finding_round_trip_json():
    finding = Finding(
        detector="retry_churn",
        severity="warning",
        session_id="sess-1",
        evidence={"count": 3},
        recommendation="Investigate",
        audit_spans=["a", "b", "c"],
        estimated_wasted_tokens=42,
    )
    line = finding.to_json_line()
    restored = json.loads(line)
    assert restored["detector"] == "retry_churn"
    assert restored["evidence"] == {"count": 3}
    assert restored["audit_spans"] == ["a", "b", "c"]
    assert restored["estimated_wasted_tokens"] == 42


def test_finding_defaults_are_isolated():
    """Mutating one Finding's evidence must not leak into another."""
    a = Finding(detector="x")
    b = Finding(detector="y")
    a.evidence["k"] = 1
    assert "k" not in b.evidence
    assert b.audit_spans == []


def test_emit_findings_stdout(capsys):
    findings = [Finding(detector="retry_churn"), Finding(detector="looping")]
    emit_findings(findings)
    captured = capsys.readouterr()
    lines = [line for line in captured.out.splitlines() if line]
    assert len(lines) == 2
    assert json.loads(lines[0])["detector"] == "retry_churn"
    assert json.loads(lines[1])["detector"] == "looping"


def test_emit_findings_append_to_path(tmp_path):
    out = tmp_path / "findings.jsonl"
    out.write_text('{"detector": "existing"}\n', encoding="utf-8")
    emit_findings([Finding(detector="retry_churn")], output_path=str(out))
    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["detector"] == "existing"
    assert json.loads(lines[1])["detector"] == "retry_churn"


def test_iter_events_missing_file_is_empty(tmp_path):
    path = tmp_path / "missing.jsonl"
    events = list(iter_events(path))
    assert events == []


def test_iter_events_skips_blank_and_invalid(tmp_path):
    path = tmp_path / "log.jsonl"
    path.write_text(
        "\n".join(
            [
                "",
                '{"action": "agent_spawn", "ts": "2026-04-21T10:00:00Z"}',
                "not valid json",
                "   ",
                '{"action": "tool_use", "ts": "2026-04-21T10:01:00Z"}',
            ]
        ),
        encoding="utf-8",
    )
    events = list(iter_events(path))
    assert len(events) == 2
    assert events[0]["action"] == "agent_spawn"
    assert events[1]["action"] == "tool_use"


def test_parse_ts_z_suffix_and_iso_offset():
    a = parse_ts({"ts": "2026-04-21T10:00:00Z"})
    b = parse_ts({"ts": "2026-04-21T10:00:00+00:00"})
    assert a == b
    assert a.tzinfo is not None
    assert a.tzinfo.utcoffset(None) == timezone.utc.utcoffset(None)


def test_parse_ts_invalid_returns_none():
    assert parse_ts({}) is None
    assert parse_ts({"ts": ""}) is None
    assert parse_ts({"ts": "not-a-date"}) is None
    assert parse_ts({"ts": 12345}) is None


def test_is_agent_spawn_filters():
    assert is_agent_spawn({"action": "agent_spawn"})
    assert not is_agent_spawn({"action": "tool_use"})
    assert not is_agent_spawn({})
