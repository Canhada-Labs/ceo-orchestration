"""Tests for optimizer.fanout — WS-2(b)(c) decompose + budget + rate governors."""

from __future__ import annotations

from optimizer import fanout as F
from optimizer.types import (
    COMPLEXITY_COMPLEX,
    GateResult,
    MAX_FANOUT_WIDTH,
    ROUTE_FANOUT,
    ROUTE_SINGLE,
)

FANOUT_PROMPT = (
    "do these things:\n1. add caching\n2. add retries\n3. add metrics\n4. add logging\n"
)


def _fanout_gate(width=4):
    return GateResult(route=ROUTE_FANOUT, complexity=COMPLEXITY_COMPLEX,
                      parallelizable=True, suggested_width=width, reason="x")


def test_plan_none_when_not_fanout(monkeypatch):
    monkeypatch.delenv("CEO_FANOUT", raising=False)
    g = GateResult(route=ROUTE_SINGLE, complexity=COMPLEXITY_COMPLEX,
                   parallelizable=False, suggested_width=1, reason="x")
    assert F.plan(FANOUT_PROMPT, g) is None


def test_plan_none_when_fanout_disabled(monkeypatch):
    monkeypatch.setenv("CEO_FANOUT", "0")
    assert F.plan(FANOUT_PROMPT, _fanout_gate()) is None


def test_plan_returns_plan(monkeypatch):
    monkeypatch.delenv("CEO_FANOUT", raising=False)
    monkeypatch.delenv("CEO_RATE_PRESSURE", raising=False)
    p = F.plan(FANOUT_PROMPT, _fanout_gate(4))
    assert p is not None
    assert 1 <= len(p.subtasks) <= MAX_FANOUT_WIDTH
    assert p.suggested_width >= 1
    for st in p.subtasks:
        assert st.est_tokens_in >= 1


def test_decompose_bounded():
    items = F.decompose("\n".join("%d. task %d" % (i, i) for i in range(1, 40)), 50)
    assert len(items) <= MAX_FANOUT_WIDTH
    items2 = F.decompose("a single sentence with no enumeration at all here", 4)
    assert len(items2) >= 1


def test_decompose_inline_no_preamble_keeps_first(monkeypatch):
    """Regression (multi-lens P1): an inline numbered list with NO preamble must
    not lose its first item to the preamble-drop off-by-one."""
    items = F.decompose("1. add caching 2. add retries 3. add metrics", 8)
    labels = [i.label for i in items]
    assert len(items) == 3, labels
    assert any("caching" in l for l in labels), labels


def test_subtask_carries_real_model_telemetry(monkeypatch):
    """Regression (multi-lens P1): SubTask must carry the real ModelChoice
    confidence (not a discarded zero) so the audit log has signal."""
    monkeypatch.delenv("CEO_FANOUT", raising=False)
    monkeypatch.delenv("CEO_MODEL_ROUTING", raising=False)
    p = F.plan(FANOUT_PROMPT, _fanout_gate(4))
    assert p is not None
    assert all(st.confidence_basis_points > 0 for st in p.subtasks)


def test_width_governor_budget_shrinks(monkeypatch):
    monkeypatch.setenv("CEO_FANOUT_BUDGET_TOKENS", "1000")
    governed, capped, budget = F.width_governor(requested_width=8, est_total_tokens_in=100000)
    assert governed < 8
    assert budget is True
    assert capped is True


def test_width_governor_no_shrink_under_budget(monkeypatch):
    monkeypatch.delenv("CEO_FANOUT_BUDGET_TOKENS", raising=False)
    governed, capped, budget = F.width_governor(requested_width=4, est_total_tokens_in=10)
    assert governed == 4
    assert budget is False
    assert capped is False


def test_rate_backoff_on_pressure(monkeypatch):
    monkeypatch.setenv("CEO_RATE_PRESSURE", "1")
    final, backoff = F.rate_backoff(governed_width=8, est_tokens_per_task=10)
    assert final < 8
    assert backoff is True


def test_rate_backoff_on_itpm_ceiling(monkeypatch):
    monkeypatch.delenv("CEO_RATE_PRESSURE", raising=False)
    monkeypatch.setenv("CEO_ITPM_CEILING", "10000")
    # width 8 * 50000 per task = 400000 >> 10000 ceiling -> must back off to 1
    final, backoff = F.rate_backoff(governed_width=8, est_tokens_per_task=50000)
    assert final == 1
    assert backoff is True


def test_rate_backoff_no_change_when_headroom(monkeypatch):
    monkeypatch.delenv("CEO_RATE_PRESSURE", raising=False)
    monkeypatch.setenv("CEO_ITPM_CEILING", "50000000")
    monkeypatch.setenv("CEO_OTPM_CEILING", "20000000")
    final, backoff = F.rate_backoff(governed_width=4, est_tokens_per_task=100)
    assert final == 4
    assert backoff is False


def test_recent_429_pressure_override(monkeypatch):
    monkeypatch.setenv("CEO_RATE_PRESSURE", "1")
    assert F.recent_429_pressure() is True
    monkeypatch.setenv("CEO_RATE_PRESSURE", "0")
    assert F.recent_429_pressure() is False


def test_recent_429_pressure_failopen(monkeypatch):
    monkeypatch.delenv("CEO_RATE_PRESSURE", raising=False)
    monkeypatch.setenv("CEO_AUDIT_LOG_DIR", "/nonexistent/path/xyz")
    # no log file -> fail-open False, never raises
    assert F.recent_429_pressure() is False


def test_governors_failopen_on_bad_input():
    """Fail-open regression (Codex 019e7ebc P1): a non-int input must yield a
    safe literal from the except path, never re-raise."""
    gw = F.width_governor(requested_width="x", est_total_tokens_in="y")  # type: ignore[arg-type]
    assert gw == (1, True, True)
    rb = F.rate_backoff(governed_width="x", est_tokens_per_task=None)  # type: ignore[arg-type]
    assert rb == (1, True)
