"""Unit tests for PLAN-096 Wave C debate-status MCP handler.

ACs exercised:
- AC4 (get_debate_state exposed; snapshot-only post-sentinel; mid-debate
  does NOT leak vote-text body)
- AC-R-1 (read-only path)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_MCP_SERVER = _REPO_ROOT / ".claude" / "scripts" / "mcp-server"
_HANDLERS = _MCP_SERVER / "handlers"

for _p in (_MCP_SERVER, _HANDLERS):
    sp = str(_p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

import get_debate_state  # type: ignore[import-not-found]  # noqa: E402


def setup_function(_):
    get_debate_state._reset_cache()


def _make_plan_with_debate(tmp_path: Path, plan_id_nnn: str, *, sealed: bool, approved: bool) -> Path:
    """Seed a .claude/plans/PLAN-NNN-slug/debates/round-1/ fixture."""
    plan_dir = tmp_path / ".claude" / "plans" / f"PLAN-{plan_id_nnn}-fixture"
    debates = plan_dir / "debates" / "round-1"
    debates.mkdir(parents=True)
    (debates / "code-reviewer-vote.md").write_text("vote body code", encoding="utf-8")
    (debates / "code-reviewer-vote.md.asc").write_text("---BEGIN PGP---", encoding="utf-8")
    (debates / "security-engineer-vote.md").write_text("vote body sec", encoding="utf-8")
    # security-engineer NOT signed → emulate in-flight
    if sealed:
        (debates / "verdict.md.asc").write_text("---BEGIN PGP---", encoding="utf-8")
    if approved:
        (debates / "approved.md.asc").write_text("---BEGIN PGP---", encoding="utf-8")
    return tmp_path


def test_no_debate_state_when_directory_absent(tmp_path):
    plans = tmp_path / ".claude" / "plans"
    plans.mkdir(parents=True)
    (plans / "PLAN-007-x.md").write_text(
        "---\nid: PLAN-007\nstatus: draft\n---\n", encoding="utf-8"
    )
    r = get_debate_state.handle({"plan_id": "PLAN-007"}, {"project_dir": tmp_path})
    assert r["state"] == "no_debate"
    assert r["rounds"] == []


def test_in_flight_state_when_no_sentinel(tmp_path):
    p = _make_plan_with_debate(tmp_path, "008", sealed=False, approved=False)
    r = get_debate_state.handle({"plan_id": "PLAN-008"}, {"project_dir": p})
    assert r["state"] == "in_flight"
    assert r["current_round"] == 1
    assert len(r["rounds"]) == 1
    round1 = r["rounds"][0]
    assert round1["vote_count"] == 2
    # Vote text body NOT leaked (only metadata).
    for vote in round1["votes"]:
        assert set(vote.keys()).issubset({"archetype", "signed"})


def test_sealed_state_when_verdict_signed(tmp_path):
    p = _make_plan_with_debate(tmp_path, "009", sealed=True, approved=False)
    r = get_debate_state.handle({"plan_id": "PLAN-009"}, {"project_dir": p})
    assert r["state"] == "sealed"
    assert r["sealed"] is True


def test_approved_state_when_owner_signed(tmp_path):
    p = _make_plan_with_debate(tmp_path, "010", sealed=True, approved=True)
    r = get_debate_state.handle({"plan_id": "PLAN-010"}, {"project_dir": p})
    assert r["state"] == "approved"
    assert r["approved"] is True


def test_invalid_plan_id_returns_error(tmp_path):
    r = get_debate_state.handle({"plan_id": "garbage"}, {"project_dir": tmp_path})
    assert "__error__" in r
    assert "missing_or_invalid_plan_id" in r["__error__"]["message"]


def test_dispatch_registers_debate_state_under_debate_read():
    import dispatch, rate_limit  # type: ignore[import-not-found]
    assert "get_debate_state" in dispatch.HANDLERS
    cls, _ = dispatch.HANDLERS["get_debate_state"]
    assert cls == "debate_read"
    assert rate_limit.handler_to_class("get_debate_state") == "debate_read"


def test_debate_read_class_default_limits():
    import rate_limit  # type: ignore[import-not-found]
    rpm, burst = rate_limit.DEFAULT_LIMITS["debate_read"]
    assert rpm == 10
    assert burst == 3
