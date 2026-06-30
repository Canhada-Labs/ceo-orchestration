"""Unit + integration tests for PLAN-096 Wave A audit_query MCP handlers.

Tests focus on the handler-direct contract (in-process); the full
stdio subprocess path is covered by ``test_mcp_server_integration.py``.

ACs exercised:
- AC1 (method count matches source enumeration ± documented exclusions)
- AC-R-1 (read-only invariant — forged-write attempts denied)
- AC-T-2 (transport mode lock surfaced via subset.md, asserted here)
- AC6 (mcp_handler_invoked path stays compatible)
"""

from __future__ import annotations

import argparse
import importlib.util
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
# from earlier tests that import the scripts-dir ``audit-query.py``
# under the same ``audit_query`` module name (see
# ``.claude/scripts/tests/test_audit_query.py``). Without this, the
# MCP handler tests resolve to the scripts-dir module instead of the
# real handler at ``.claude/scripts/mcp-server/handlers/audit_query.py``.
import importlib.util as _ilu  # noqa: E402

_h_spec = _ilu.spec_from_file_location(
    "audit_query_mcp_handler", str(_HANDLERS / "audit_query.py")
)
assert _h_spec is not None and _h_spec.loader is not None
h_audit_query = _ilu.module_from_spec(_h_spec)
_h_spec.loader.exec_module(h_audit_query)  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# AC1 — method count contract
# ---------------------------------------------------------------------------


def _enumerate_source_subcommands() -> list:
    """Mirror PLAN-096/wave-a-mcp-subset.md §1 enumeration."""
    spec = importlib.util.spec_from_file_location(
        "_aq", str(_REPO_ROOT / ".claude" / "scripts" / "audit-query.py")
    )
    assert spec is not None and spec.loader is not None
    aq = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(aq)
    shared = aq._build_shared_parser()
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")
    for fn in (
        aq._add_v1_subparsers,
        aq._add_v2_subparsers,
        aq._add_sprint8_9_subparsers,
        aq._add_plan015_subparsers,
        aq._add_plan080_subparsers,
        aq._add_plan081_subparsers,
    ):
        fn(sub, shared)
    return sorted(sub.choices.keys())


def test_method_count_matches_source():
    """AC1 — exposed methods + documented exclusions equals source count."""
    source = _enumerate_source_subcommands()
    exposed = set(h_audit_query.ALLOWED_SUBCOMMANDS.keys())
    # Source uses dashes ("by-skill"); MCP exposure uses underscores.
    source_underscored = {c.replace("-", "_") for c in source}
    excluded = source_underscored - exposed
    assert excluded == {"label"}, (
        f"Unexpected exclusion delta: {excluded}; expected {{'label'}}. "
        "Update wave-a-mcp-subset.md §3 if intentional."
    )
    assert len(exposed) + len(excluded) == len(source)


def test_method_count_is_27():
    """AC1 — locked subset is exactly 27 methods."""
    assert len(h_audit_query.ALLOWED_SUBCOMMANDS) == 27
    assert len(h_audit_query.HANDLERS) == 27


def test_every_method_is_audit_query_namespace():
    """AC1 — every exposed method lives under audit_query.* namespace."""
    for method_name in h_audit_query.HANDLERS:
        assert method_name.startswith("audit_query."), method_name


def test_label_excluded_from_handlers():
    """AC1 + AC-R-1 — label sub-command is NOT exposed (it writes)."""
    assert "label" not in h_audit_query.ALLOWED_SUBCOMMANDS
    assert "audit_query.label" not in h_audit_query.HANDLERS


# ---------------------------------------------------------------------------
# AC-R-1 — read-only invariant forged-write probe
# ---------------------------------------------------------------------------


_FORGED_PARAM_SETS = [
    {"label": "malicious"},
    {"--label": "malicious"},
    {"write": True},
    {"append": "/tmp/foo"},
    {"output_path": "/tmp/foo"},
    {"store": "evil"},
    {"patch": "diff"},
]


@pytest.mark.parametrize("forged", _FORGED_PARAM_SETS)
def test_ac_r_1_forged_write_rejected_on_summary(forged, tmp_path):
    """AC-R-1 — every forged-write param is rejected before disk touch."""
    ctx = {"project_dir": tmp_path}
    r = h_audit_query.HANDLERS["audit_query.summary"](forged, ctx)
    assert "__error__" in r, f"Expected __error__ for forged={forged}, got {r}"
    assert r["__error__"]["code"] == -32602
    assert "read_only_violation" in r["__error__"]["message"]


def test_ac_r_1_probe_runs_against_every_handler(tmp_path):
    """AC-R-1 — exercise the probe across all 27 handlers."""
    ctx = {"project_dir": tmp_path}
    failures = []
    for method_name, handler in h_audit_query.HANDLERS.items():
        r = handler({"label": "malicious"}, ctx)
        if "__error__" not in r:
            failures.append(method_name)
    assert not failures, (
        f"{len(failures)} handlers leaked past forged-write probe: {failures}"
    )


# ---------------------------------------------------------------------------
# AC6 — handler returns JSON-serializable envelope
# ---------------------------------------------------------------------------


def test_summary_returns_dict_envelope():
    """The summary handler returns an envelope with subcommand + data."""
    ctx = {"project_dir": _REPO_ROOT}
    r = h_audit_query.HANDLERS["audit_query.summary"]({}, ctx)
    assert "subcommand" in r
    assert r["subcommand"] == "summary"
    assert "data" in r or "warning" in r


def test_fail_open_on_missing_project_dir():
    """Handler does not raise when project_dir missing — returns warning."""
    r = h_audit_query.HANDLERS["audit_query.summary"]({}, {})
    assert "warning" in r
    assert r["warning"] == "project_dir_missing"


def test_fail_open_on_missing_audit_query_script(tmp_path):
    """Handler degrades gracefully when audit-query.py is absent."""
    h_audit_query._reset_module_cache()
    ctx = {"project_dir": tmp_path}
    r = h_audit_query.HANDLERS["audit_query.summary"]({}, ctx)
    assert "warning" in r
    assert "missing" in r["warning"] or "load_failed" in r["warning"]


# ---------------------------------------------------------------------------
# Dispatcher registration contract
# ---------------------------------------------------------------------------


def test_dispatch_registers_all_audit_query_methods():
    """dispatch.HANDLERS contains the 27 audit_query methods under audit_read class."""
    import dispatch  # type: ignore[import-not-found]
    for method_name in h_audit_query.HANDLERS:
        assert method_name in dispatch.HANDLERS, f"{method_name} missing from dispatch.HANDLERS"
        cls, fn = dispatch.HANDLERS[method_name]
        assert cls == "audit_read", f"{method_name} routed to wrong class: {cls}"
        assert callable(fn)


def test_rate_limit_classifies_audit_query_methods():
    """rate_limit.HANDLER_CLASS maps every audit_query method to audit_read."""
    import rate_limit  # type: ignore[import-not-found]
    for method_name in h_audit_query.HANDLERS:
        assert rate_limit.handler_to_class(method_name) == "audit_read", method_name


def test_audit_read_class_has_default_limits():
    """audit_read class is registered with default rpm/burst."""
    import rate_limit  # type: ignore[import-not-found]
    assert "audit_read" in rate_limit.DEFAULT_LIMITS
    rpm, burst = rate_limit.DEFAULT_LIMITS["audit_read"]
    assert rpm == 30
    assert burst == 5
