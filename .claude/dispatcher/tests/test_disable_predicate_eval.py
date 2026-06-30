from __future__ import annotations

import json
import time
from collections import namedtuple
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List

import pytest

from disable_predicate_eval import (
    DEFAULT_AUDIT_TAIL_N,
    MAX_AUDIT_TAIL_N,
    evaluate_predicate,
    _resolve_tail_n,
)

# ---------------------------------------------------------------------------
# Synthetic Predicate NamedTuple
# ---------------------------------------------------------------------------

_SynPred = namedtuple(
    "_SynPred",
    ["id", "type", "metric", "operator", "value", "window_minutes", "window_days"],
)


def _pred(
    *,
    pid: str = "test",
    ptype: str = "duration_threshold",
    metric: str = "codex_outage_minutes",
    operator: str = ">",
    value: float = 5,
    window_minutes: int = 60,
    window_days: int = None,
) -> _SynPred:
    """Convenience factory for synthetic predicates."""
    return _SynPred(
        id=pid,
        type=ptype,
        metric=metric,
        operator=operator,
        value=value,
        window_minutes=window_minutes,
        window_days=window_days,
    )


# ---------------------------------------------------------------------------
# Fixed epoch for deterministic time-window assertions
# ---------------------------------------------------------------------------

_NOW: float = 1_700_000_000.0  # 2023-11-14 22:13:20 UTC


def _ts(offset_s: float = 0.0) -> float:
    """Return Unix epoch relative to _NOW."""
    return _NOW + offset_s


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rec(action: str, ts: float, **extra: Any) -> str:
    """Return a single JSON audit-log line."""
    r: Dict[str, Any] = {"action": action, "ts": ts}
    r.update(extra)
    return json.dumps(r)


def _write(path: Path, lines: List[str]) -> None:
    """Write audit-log lines, one per line, to path."""
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# duration_threshold: codex_outage_minutes
# ---------------------------------------------------------------------------


def test_duration_6_events_fires_gt_5(tmp_path: Path):
    """6 codex_unavailable events in a 60-min window fires a '> 5' duration predicate."""
    lines = [_rec("pair_rail_codex_unavailable", _ts(-i * 60)) for i in range(6)]
    log = tmp_path / "a.jsonl"
    _write(log, lines)
    assert evaluate_predicate(_pred(), audit_log_path=log, now_ts=_NOW) is True


def test_duration_5_events_does_not_fire_gt_5(tmp_path: Path):
    """Exactly 5 events does NOT fire a strictly-greater-than-5 predicate."""
    lines = [_rec("pair_rail_codex_unavailable", _ts(-i * 60)) for i in range(5)]
    log = tmp_path / "a.jsonl"
    _write(log, lines)
    assert evaluate_predicate(_pred(), audit_log_path=log, now_ts=_NOW) is False


def test_duration_events_outside_window_excluded(tmp_path: Path):
    """Events older than window_minutes must be excluded from the duration sum."""
    inside = [_rec("pair_rail_codex_unavailable", _ts(-i * 60)) for i in range(3)]
    outside = [_rec("pair_rail_codex_unavailable", _ts(-7200 - i * 60)) for i in range(6)]
    log = tmp_path / "a.jsonl"
    _write(log, outside + inside)
    # Only 3 inside window — < 5 threshold, must NOT fire
    assert evaluate_predicate(_pred(), audit_log_path=log, now_ts=_NOW) is False


# ---------------------------------------------------------------------------
# numeric_threshold: codex_latency_p95_s
# ---------------------------------------------------------------------------


def test_latency_p95_fires_with_12_samples_above_60(tmp_path: Path):
    """12 samples [1..10, 70, 80]: nearest-rank p95 ~= 80, fires '> 60'."""
    samples = list(range(1, 11)) + [70, 80]
    lines = [
        _rec("dispatcher_route", _ts(-i * 10), wall_clock_s=float(v))
        for i, v in enumerate(samples)
    ]
    log = tmp_path / "a.jsonl"
    _write(log, lines)
    pred = _pred(ptype="numeric_threshold", metric="codex_latency_p95_s", operator=">", value=60, window_minutes=30)
    assert evaluate_predicate(pred, audit_log_path=log, now_ts=_NOW) is True


def test_latency_p95_fewer_than_10_samples_returns_false(tmp_path: Path):
    """Fewer than 10 samples: p95 returns 0.0 (insufficient evidence), does NOT fire."""
    lines = [
        _rec("dispatcher_route", _ts(-i * 10), wall_clock_s=80.0)
        for i in range(9)
    ]
    log = tmp_path / "a.jsonl"
    _write(log, lines)
    pred = _pred(ptype="numeric_threshold", metric="codex_latency_p95_s", operator=">", value=60, window_minutes=30)
    assert evaluate_predicate(pred, audit_log_path=log, now_ts=_NOW) is False


# ---------------------------------------------------------------------------
# numeric_threshold: fp_rate_30d
# ---------------------------------------------------------------------------


def test_fp_rate_fires_when_3_of_6_case_b_labeled_fp(tmp_path: Path):
    """6 Case-B events, 3 labeled 'fp': rate=0.5, fires '> 0.30'."""
    lines = (
        [_rec("pair_rail_case_emit", _ts(-i * 3600), case="B", label="fp") for i in range(3)]
        + [_rec("pair_rail_case_emit", _ts(-(i + 3) * 3600), case="B") for i in range(3)]
    )
    log = tmp_path / "a.jsonl"
    _write(log, lines)
    pred = _pred(ptype="numeric_threshold", metric="fp_rate_30d", operator=">", value=0.30, window_minutes=None, window_days=30)
    assert evaluate_predicate(pred, audit_log_path=log, now_ts=_NOW) is True


def test_fp_rate_insufficient_denominator_does_not_fire(tmp_path: Path):
    """Fewer than 5 Case-B events: fp_rate returns 0.0, does NOT fire '> 0.30'."""
    lines = [
        _rec("pair_rail_case_emit", _ts(-i * 3600), case="B", label="fp")
        for i in range(4)
    ]
    log = tmp_path / "a.jsonl"
    _write(log, lines)
    pred = _pred(ptype="numeric_threshold", metric="fp_rate_30d", operator=">", value=0.30, window_minutes=None, window_days=30)
    assert evaluate_predicate(pred, audit_log_path=log, now_ts=_NOW) is False


# ---------------------------------------------------------------------------
# numeric_threshold: disagreement_rate_30d
# ---------------------------------------------------------------------------


def test_disagreement_rate_insufficient_denominator_does_not_fire(tmp_path: Path):
    """Fewer than 5 cases A-E: rate=0.0, does NOT fire '> 0.40'."""
    lines = [_rec("pair_rail_case_emit", _ts(-i * 3600), case="E") for i in range(4)]
    log = tmp_path / "a.jsonl"
    _write(log, lines)
    pred = _pred(ptype="numeric_threshold", metric="disagreement_rate_30d", operator=">", value=0.40, window_minutes=None, window_days=30)
    assert evaluate_predicate(pred, audit_log_path=log, now_ts=_NOW) is False


def test_disagreement_rate_fires_with_3_of_6_cases_E(tmp_path: Path):
    """6 cases with 3 case=E: rate=0.5, fires '> 0.40'."""
    lines = (
        [_rec("pair_rail_case_emit", _ts(-i * 3600), case="E") for i in range(3)]
        + [_rec("pair_rail_case_emit", _ts(-(i + 3) * 3600), case="A") for i in range(3)]
    )
    log = tmp_path / "a.jsonl"
    _write(log, lines)
    pred = _pred(ptype="numeric_threshold", metric="disagreement_rate_30d", operator=">", value=0.40, window_minutes=None, window_days=30)
    assert evaluate_predicate(pred, audit_log_path=log, now_ts=_NOW) is True


# ---------------------------------------------------------------------------
# numeric_threshold: u7_rubric_gap_pp (latest_field_value)
# ---------------------------------------------------------------------------


def test_u7_rubric_gap_pp_uses_most_recent_record(tmp_path: Path):
    """u7_rubric_gap_pp reads the latest record's rubric_gap_pp field (8.0 > 5 fires)."""
    lines = [
        _rec("pair_rail_promotion_emit", _ts(-3600), rubric_gap_pp=3.0),
        _rec("pair_rail_promotion_emit", _ts(-1800), rubric_gap_pp=8.0),
    ]
    log = tmp_path / "a.jsonl"
    _write(log, lines)
    pred = _pred(ptype="numeric_threshold", metric="u7_rubric_gap_pp", operator=">", value=5, window_minutes=None, window_days=None)
    assert evaluate_predicate(pred, audit_log_path=log, now_ts=_NOW) is True


# ---------------------------------------------------------------------------
# boolean: u2_breaches_count
# ---------------------------------------------------------------------------


def test_boolean_fires_with_one_breach_event(tmp_path: Path):
    """One codex_writeguard_block event in window fires the boolean '> 0' predicate."""
    lines = [_rec("codex_writeguard_block", _ts(-300))]
    log = tmp_path / "a.jsonl"
    _write(log, lines)
    pred = _pred(ptype="boolean", metric="u2_breaches_count", operator=">", value=0, window_minutes=60)
    assert evaluate_predicate(pred, audit_log_path=log, now_ts=_NOW) is True


def test_boolean_does_not_fire_with_no_breach_events(tmp_path: Path):
    """Empty log for u2_breaches_count: boolean returns 0.0, does NOT fire."""
    log = tmp_path / "a.jsonl"
    log.write_text("", encoding="utf-8")
    pred = _pred(ptype="boolean", metric="u2_breaches_count", operator=">", value=0, window_minutes=60)
    assert evaluate_predicate(pred, audit_log_path=log, now_ts=_NOW) is False


# ---------------------------------------------------------------------------
# All operator branches
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "operator,value,count,expected",
    [
        (">", 5, 6, True),
        (">", 5, 5, False),
        (">=", 5, 5, True),
        (">=", 5, 4, False),
        ("<", 5, 4, True),
        ("<", 5, 5, False),
        ("<=", 5, 5, True),
        ("<=", 5, 6, False),
        ("==", 5, 5, True),
        ("==", 5, 4, False),
    ],
)
def test_operator_branch(
    tmp_path: Path, operator: str, value: float, count: int, expected: bool
):
    """Verify correct Boolean result for each operator with a duration_threshold predicate."""
    lines = [
        _rec("pair_rail_codex_unavailable", _ts(-i * 30))
        for i in range(count)
    ]
    log = tmp_path / f"op-{operator.replace('>', 'gt').replace('<', 'lt').replace('=', 'eq')}-{count}.jsonl"
    _write(log, lines)
    pred = _pred(operator=operator, value=value, window_minutes=60)
    assert evaluate_predicate(pred, audit_log_path=log, now_ts=_NOW) is expected


# ---------------------------------------------------------------------------
# Fail-OPEN: missing / malformed audit-log inputs
# ---------------------------------------------------------------------------


def test_fail_open_nonexistent_log_returns_false(tmp_path: Path):
    """A nonexistent audit-log path must return False without raising (fail-OPEN)."""
    assert evaluate_predicate(
        _pred(), audit_log_path=tmp_path / "no-file.jsonl", now_ts=_NOW
    ) is False


def test_fail_open_malformed_json_line_skipped(tmp_path: Path):
    """Malformed JSON lines in the log are silently skipped; no exception raised."""
    log = tmp_path / "a.jsonl"
    _write(log, ["NOT JSON", _rec("pair_rail_codex_unavailable", _ts(-60)), "{broken"])
    # Only 1 valid event, does NOT cross > 5 threshold
    assert evaluate_predicate(_pred(), audit_log_path=log, now_ts=_NOW) is False


def test_fail_open_record_missing_action_field_skipped(tmp_path: Path):
    """Records missing the 'action' field are silently skipped."""
    log = tmp_path / "a.jsonl"
    _write(log, [
        json.dumps({"ts": _ts(-60)}),              # no action
        _rec("pair_rail_codex_unavailable", _ts(-120)),
    ])
    assert evaluate_predicate(_pred(), audit_log_path=log, now_ts=_NOW) is False


def test_fail_open_predicate_missing_operator_returns_false(tmp_path: Path):
    """A predicate with operator=None must return False without raising."""
    log = tmp_path / "a.jsonl"
    log.write_text("", encoding="utf-8")
    NoPred = namedtuple("NoPred", ["id", "type", "metric", "operator", "value", "window_minutes", "window_days"])
    bad = NoPred(id="x", type="duration_threshold", metric="codex_outage_minutes",
                 operator=None, value=5, window_minutes=60, window_days=None)
    assert evaluate_predicate(bad, audit_log_path=log, now_ts=_NOW) is False


# ---------------------------------------------------------------------------
# Budget / tail_n control
# ---------------------------------------------------------------------------


def test_timeout_ms_zero_returns_false(tmp_path: Path):
    """timeout_ms=0 exhausts the budget before reading any records -> returns False."""
    lines = [_rec("pair_rail_codex_unavailable", _ts(-i * 60)) for i in range(10)]
    log = tmp_path / "a.jsonl"
    _write(log, lines)
    assert evaluate_predicate(_pred(), audit_log_path=log, timeout_ms=0, now_ts=_NOW) is False


def test_tail_n_zero_returns_false(tmp_path: Path):
    """tail_n=0 means no records are considered -> returns False."""
    lines = [_rec("pair_rail_codex_unavailable", _ts(-i * 60)) for i in range(10)]
    log = tmp_path / "a.jsonl"
    _write(log, lines)
    assert evaluate_predicate(_pred(), audit_log_path=log, tail_n=0, now_ts=_NOW) is False


def test_env_override_tail_n_honored(tmp_path: Path, monkeypatch):
    """CEO_PAIR_RAIL_AUDIT_TAIL_N=200 is honored and results are still correct."""
    monkeypatch.setenv("CEO_PAIR_RAIL_AUDIT_TAIL_N", "200")
    lines = [_rec("pair_rail_codex_unavailable", _ts(-i * 60)) for i in range(6)]
    log = tmp_path / "a.jsonl"
    _write(log, lines)
    assert evaluate_predicate(_pred(), audit_log_path=log, now_ts=_NOW) is True


def test_env_override_tail_n_clamped_to_max(monkeypatch):
    """CEO_PAIR_RAIL_AUDIT_TAIL_N above MAX_AUDIT_TAIL_N is clamped to MAX_AUDIT_TAIL_N."""
    monkeypatch.setenv("CEO_PAIR_RAIL_AUDIT_TAIL_N", str(MAX_AUDIT_TAIL_N + 1_000_000))
    assert _resolve_tail_n() == MAX_AUDIT_TAIL_N


# ---------------------------------------------------------------------------
# Performance: bounded tail-scan on a 50k-line log
# ---------------------------------------------------------------------------


def test_bounded_tail_scan_50k_records_under_100ms(tmp_path: Path):
    """A 50k-record log evaluated with tail_n=10000 must complete in < 100ms."""
    log = tmp_path / "big.jsonl"
    chunks: List[str] = []
    for i in range(50_000):
        if i % 5 == 0:
            chunks.append(_rec("pair_rail_codex_unavailable", _ts(-i * 0.1)))
        else:
            chunks.append(_rec("other_action", _ts(-i * 0.1)))
    log.write_text("\n".join(chunks) + "\n", encoding="utf-8")

    pred = _pred()
    t0 = time.monotonic()
    evaluate_predicate(pred, audit_log_path=log, tail_n=10_000, now_ts=_NOW)
    elapsed_ms = (time.monotonic() - t0) * 1000.0
    assert elapsed_ms < 100.0, f"eval took {elapsed_ms:.1f}ms, budget is 100ms"


# ---------------------------------------------------------------------------
# ts coercion variants
# ---------------------------------------------------------------------------


def _single_outage_log(path: Path, ts_value: Any) -> None:
    """Write one pair_rail_codex_unavailable record with the given ts value."""
    path.write_text(json.dumps({"action": "pair_rail_codex_unavailable", "ts": ts_value}) + "\n")


def test_ts_coercion_iso8601_z_suffix(tmp_path: Path):
    """ISO 8601 string with Z suffix is parsed as UTC and accepted."""
    dt = datetime.fromtimestamp(_NOW, tz=timezone.utc)
    iso_z = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    log = tmp_path / "a.jsonl"
    _single_outage_log(log, iso_z)
    # 1 event inside 5-min window, >= 1 fires
    pred = _pred(operator=">=", value=1, window_minutes=5)
    assert evaluate_predicate(pred, audit_log_path=log, now_ts=_NOW + 1.0) is True


def test_ts_coercion_iso8601_timezone_offset(tmp_path: Path):
    """ISO 8601 string with timezone offset (+/-HH:MM) is parsed correctly."""
    dt = datetime.fromtimestamp(_NOW, tz=timezone(timedelta(hours=-3)))
    iso_tz = dt.isoformat()  # includes -03:00 offset
    log = tmp_path / "a.jsonl"
    _single_outage_log(log, iso_tz)
    pred = _pred(operator=">=", value=1, window_minutes=5)
    assert evaluate_predicate(pred, audit_log_path=log, now_ts=_NOW + 1.0) is True


def test_ts_coercion_int_epoch(tmp_path: Path):
    """Integer Unix epoch ts is accepted without error."""
    log = tmp_path / "a.jsonl"
    _single_outage_log(log, int(_NOW))
    pred = _pred(operator=">=", value=1, window_minutes=5)
    assert evaluate_predicate(pred, audit_log_path=log, now_ts=_NOW + 1.0) is True


def test_ts_coercion_float_epoch(tmp_path: Path):
    """Float Unix epoch ts is accepted without error."""
    log = tmp_path / "a.jsonl"
    _single_outage_log(log, float(_NOW))
    pred = _pred(operator=">=", value=1, window_minutes=5)
    assert evaluate_predicate(pred, audit_log_path=log, now_ts=_NOW + 1.0) is True


def test_ts_coercion_malformed_string_drops_record(tmp_path: Path):
    """A record with ts='NOT-A-DATE' is silently dropped; evaluator continues without raising."""
    log = tmp_path / "a.jsonl"
    lines = [
        json.dumps({"action": "pair_rail_codex_unavailable", "ts": "NOT-A-DATE"}),
        _rec("pair_rail_codex_unavailable", _ts(-60)),  # 1 valid
    ]
    _write(log, lines)
    # 1 valid event -> < 5 threshold, does NOT fire
    assert evaluate_predicate(_pred(), audit_log_path=log, now_ts=_NOW) is False
