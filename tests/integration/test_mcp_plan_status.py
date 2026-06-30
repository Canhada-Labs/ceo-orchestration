"""Unit tests for PLAN-096 Wave B plan-status MCP handlers.

ACs exercised:
- AC3 (list_plans / get_plan / get_plan_acs / get_plan_dependencies exposed)
- AC-R-1 (read-only: only file reads, no writes)
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

import plan_status  # type: ignore[import-not-found]  # noqa: E402


# ---------------------------------------------------------------------------
# list_plans
# ---------------------------------------------------------------------------


def setup_function(_):
    plan_status._reset_cache()


def _project_fixture(tmp_path: Path) -> Path:
    """Create a minimal .claude/plans/ tree under tmp_path."""
    plans = tmp_path / ".claude" / "plans"
    plans.mkdir(parents=True)
    (plans / "PLAN-001-foo.md").write_text(
        "---\nid: PLAN-001\ntitle: foo\nstatus: done\ntarget_tag: v1.0.0\n"
        "depends_on: []\nexternal_wait: []\nrisk_tier: A\nowner: CEO\n---\nbody\n",
        encoding="utf-8",
    )
    (plans / "PLAN-002-bar.md").write_text(
        "---\nid: PLAN-002\ntitle: bar\nstatus: reviewed\ntarget_tag: v1.1.0\n"
        "depends_on: [PLAN-001]\nexternal_wait: []\n---\n\n## Acceptance criteria\n\n"
        "- **AC1**: first criterion\n"
        "- **AC2**: second criterion\n"
        "- **AC-R-1**: read-only criterion\n",
        encoding="utf-8",
    )
    (plans / "PLAN-003-baz.md").write_text(
        "---\nid: PLAN-003\nstatus: executing\ndepends_on:\n  - PLAN-001\n  - PLAN-002\n"
        "external_wait:\n  - external-event-x\n---\n",
        encoding="utf-8",
    )
    return tmp_path


def test_list_plans_returns_all_plans(tmp_path):
    p = _project_fixture(tmp_path)
    r = plan_status.handle_list_plans({}, {"project_dir": p})
    assert r["total"] == 3
    ids = {plan["id"] for plan in r["plans"]}
    assert ids == {"PLAN-001", "PLAN-002", "PLAN-003"}


def test_list_plans_filters_by_status(tmp_path):
    p = _project_fixture(tmp_path)
    r = plan_status.handle_list_plans({"status": "reviewed"}, {"project_dir": p})
    assert r["total"] == 1
    assert r["plans"][0]["id"] == "PLAN-002"


def test_list_plans_fail_open_when_missing_project_dir():
    r = plan_status.handle_list_plans({}, {})
    assert "warning" in r
    assert r["plans"] == []


# ---------------------------------------------------------------------------
# get_plan
# ---------------------------------------------------------------------------


def test_get_plan_returns_frontmatter(tmp_path):
    p = _project_fixture(tmp_path)
    r = plan_status.handle_get_plan({"plan_id": "PLAN-001"}, {"project_dir": p})
    plan = r["plan"]
    assert plan["status"] == "done"
    assert plan["target_tag"] == "v1.0.0"
    assert plan["risk_tier"] == "A"


def test_get_plan_returns_error_for_unknown(tmp_path):
    p = _project_fixture(tmp_path)
    r = plan_status.handle_get_plan({"plan_id": "PLAN-999"}, {"project_dir": p})
    assert "__error__" in r
    assert "plan_not_found" in r["__error__"]["message"]


def test_get_plan_returns_error_for_missing_plan_id(tmp_path):
    p = _project_fixture(tmp_path)
    r = plan_status.handle_get_plan({}, {"project_dir": p})
    assert "__error__" in r
    assert "missing_plan_id" in r["__error__"]["message"]


# ---------------------------------------------------------------------------
# get_plan_acs
# ---------------------------------------------------------------------------


def test_get_plan_acs_extracts_three_acs(tmp_path):
    p = _project_fixture(tmp_path)
    r = plan_status.handle_get_plan_acs({"plan_id": "PLAN-002"}, {"project_dir": p})
    assert r["total"] == 3
    ids = {ac["id"] for ac in r["acs"]}
    assert ids == {"AC1", "AC2", "AC-R-1"}


def test_get_plan_acs_returns_empty_when_no_section(tmp_path):
    p = _project_fixture(tmp_path)
    r = plan_status.handle_get_plan_acs({"plan_id": "PLAN-001"}, {"project_dir": p})
    assert r["total"] == 0


# ---------------------------------------------------------------------------
# get_plan_dependencies
# ---------------------------------------------------------------------------


def test_get_plan_dependencies_returns_lists(tmp_path):
    p = _project_fixture(tmp_path)
    r = plan_status.handle_get_plan_dependencies(
        {"plan_id": "PLAN-003"}, {"project_dir": p}
    )
    assert r["depends_on"] == ["PLAN-001", "PLAN-002"]
    assert r["external_wait"] == ["external-event-x"]


def test_get_plan_dependencies_returns_empty_for_no_deps(tmp_path):
    p = _project_fixture(tmp_path)
    r = plan_status.handle_get_plan_dependencies(
        {"plan_id": "PLAN-001"}, {"project_dir": p}
    )
    assert r["depends_on"] == []
    assert r["external_wait"] == []


# ---------------------------------------------------------------------------
# Dispatcher contract
# ---------------------------------------------------------------------------


def test_dispatch_registers_four_plan_methods():
    import dispatch  # type: ignore[import-not-found]
    expected = (
        "list_plans",
        "get_plan",
        "get_plan_acs",
        "get_plan_dependencies",
    )
    for method in expected:
        assert method in dispatch.HANDLERS, f"{method} missing"
        cls, _ = dispatch.HANDLERS[method]
        assert cls == "readonly"
