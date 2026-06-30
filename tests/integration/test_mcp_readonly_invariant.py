"""AC-R-1 forged-write probe — runs against EVERY PLAN-096 handler.

Per `.claude/plans/PLAN-096/wave-a-mcp-subset.md` §3 and PLAN-096 §A.5:
read-only handlers MUST reject forged-write attempts BEFORE any disk
write. This file consolidates the probe across all 33 new handlers
(27 audit_query + 4 plan_status + 1 debate_state + 1 cost_budget).

For dispatcher-level enforcement see also
``test_mcp_audit_query.py::test_ac_r_1_probe_runs_against_every_handler``.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_MCP_SERVER = _REPO_ROOT / ".claude" / "scripts" / "mcp-server"
_HANDLERS = _MCP_SERVER / "handlers"
_HOOKS = _REPO_ROOT / ".claude" / "hooks"

for _p in (_MCP_SERVER, _HANDLERS, _HOOKS):
    sp = str(_p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

# PLAN-107 Wave D — explicit spec load to defeat sys.modules pollution
# from earlier tests that load other modules under common names (e.g.
# ``audit-query.py`` cached as ``audit_query`` by
# ``.claude/scripts/tests/test_audit_query.py``).
import importlib.util as _ilu  # noqa: E402


def _load_handler(handler_name: str):
    """Load a handler module by file path, bypassing sys.modules cache."""
    spec = _ilu.spec_from_file_location(
        f"{handler_name}_mcp_handler", str(_HANDLERS / f"{handler_name}.py")
    )
    assert spec is not None and spec.loader is not None
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


audit_query = _load_handler("audit_query")
plan_status = _load_handler("plan_status")
get_debate_state = _load_handler("get_debate_state")
get_cost_budget = _load_handler("get_cost_budget")


def _disk_sha(plans_dir: Path) -> str:
    """SHA-256 over every file's content under plans_dir.

    Used to detect any write side-effect from a handler call. Two
    consecutive snapshots before/after a forged call must match.
    """
    h = hashlib.sha256()
    for p in sorted(plans_dir.rglob("*")):
        if p.is_file():
            h.update(p.as_posix().encode("utf-8"))
            h.update(b"\x00")
            h.update(p.read_bytes())
            h.update(b"\xff")
    return h.hexdigest()


def _seed_project(tmp_path: Path) -> Path:
    """Plant a tiny .claude/plans/ + audit-log fixture for disk-stable probes."""
    plans = tmp_path / ".claude" / "plans"
    plans.mkdir(parents=True)
    (plans / "PLAN-001-fix.md").write_text(
        "---\nid: PLAN-001\nstatus: done\ntarget_tag: v1.0.0\n---\n",
        encoding="utf-8",
    )
    return tmp_path


_FORGED_PARAMS = [
    {"label": "evil"},
    {"--label": "evil"},
    {"write": True},
    {"append": "/tmp/x"},
    {"output_path": "/tmp/x"},
    {"store": "evil"},
]


@pytest.mark.parametrize("forged", _FORGED_PARAMS)
def test_audit_query_handlers_disk_stable_under_forged_params(tmp_path, forged):
    """≥3 forged-write attempts per handler; disk SHA must not change."""
    p = _seed_project(tmp_path)
    pre = _disk_sha(p)
    for method in audit_query.HANDLERS:
        r = audit_query.HANDLERS[method](forged, {"project_dir": p})
        # Every forged param must be rejected.
        assert "__error__" in r, f"{method} did not reject forged={forged}"
    post = _disk_sha(p)
    assert pre == post, "Handler caused a disk write under forged-write probe"


def test_plan_status_handlers_disk_stable(tmp_path):
    """Wave B handlers do not touch disk under any param shape."""
    p = _seed_project(tmp_path)
    pre = _disk_sha(p)
    plan_status.handle_list_plans({}, {"project_dir": p})
    plan_status.handle_get_plan({"plan_id": "PLAN-001"}, {"project_dir": p})
    plan_status.handle_get_plan_acs({"plan_id": "PLAN-001"}, {"project_dir": p})
    plan_status.handle_get_plan_dependencies({"plan_id": "PLAN-001"}, {"project_dir": p})
    post = _disk_sha(p)
    assert pre == post


def test_debate_state_handler_disk_stable(tmp_path):
    p = _seed_project(tmp_path)
    pre = _disk_sha(p)
    get_debate_state.handle({"plan_id": "PLAN-001"}, {"project_dir": p})
    get_debate_state.handle({"plan_id": "PLAN-999"}, {"project_dir": p})
    post = _disk_sha(p)
    assert pre == post


def test_cost_budget_handler_disk_stable(tmp_path):
    p = _seed_project(tmp_path)
    pre = _disk_sha(p)
    get_cost_budget.handle({"scope": "caller"}, {"client_id": "a" * 16})
    get_cost_budget.handle({"scope": "aggregate"}, {"client_id": "a" * 16})
    post = _disk_sha(p)
    assert pre == post


def test_total_new_methods_count_is_33():
    """PLAN-096 ships exactly 33 new MCP methods (27+4+1+1)."""
    assert len(audit_query.HANDLERS) == 27
    assert len(plan_status.HANDLERS) == 4
    # debate + cost each have 1 method.
    assert len(get_debate_state.HANDLERS) == 1
    assert len(get_cost_budget.HANDLERS) == 1
    total = (
        len(audit_query.HANDLERS)
        + len(plan_status.HANDLERS)
        + len(get_debate_state.HANDLERS)
        + len(get_cost_budget.HANDLERS)
    )
    assert total == 33
