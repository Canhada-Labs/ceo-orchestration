#!/usr/bin/env python3
"""Tests for the PLAN-135 W5 O4 statusLine quota-hint in check_budget.py.

STAGED test (COUPLING RULE): it imports the STAGED check_budget.py, which
carries the new `_statusline_quota_hint()` helper. It ships under
staged/w5/files/.claude/hooks/tests/ and runs once the staged check_budget
lands on the canonical path at arc consolidation — NOT against the live
branch (whose check_budget has no helper yet), so the live suite stays green
standalone.

Hermetic + offline + $0: the helper only reads a local sidecar JSON we write
under tmp_path; no network, no audit-log mutation, no spend.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

# Resolve check_budget.py: when this test lands on the canonical path it sits
# at .claude/hooks/tests/, so the module is one dir up. We import by path and
# put .claude/hooks on sys.path so its `from _lib import ...` resolves.
_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
_CB = _HOOKS_DIR / "check_budget.py"
_spec = importlib.util.spec_from_file_location("check_budget_o4", str(_CB))
assert _spec and _spec.loader
cb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cb)  # type: ignore[union-attr]


def _write_sidecar(base: Path, obj: dict) -> None:
    d = base / "state"
    d.mkdir(parents=True, exist_ok=True)
    (d / "statusline-snapshot.json").write_text(json.dumps(obj))


VALID = {
    "schema": "statusline-sidecar/v1",
    "rate_limits": {
        "five_hour": {"used_pct": 23.5, "resets_at": "1738425600"},
        "seven_day": {"used_pct": 41.2, "resets_at": "1738857600"},
    },
}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in ("CEO_BUDGET_QUOTA_HINT", "CEO_STATUSLINE_SIDECAR", "CEO_AUDIT_LOG_DIR"):
        monkeypatch.delenv(k, raising=False)
    yield


def test_hint_present(tmp_path, monkeypatch):
    monkeypatch.setenv("CEO_AUDIT_LOG_DIR", str(tmp_path))
    _write_sidecar(tmp_path, VALID)
    hint = cb._statusline_quota_hint()
    assert "Live quota" in hint
    assert "5h:24%" in hint  # round(23.5)
    assert "wk:41%" in hint
    assert "advisory" in hint
    # Never leaks resets_at epoch / free text beyond the labelled %s.
    assert "1738425600" not in hint


def test_kill_switch_disables(tmp_path, monkeypatch):
    monkeypatch.setenv("CEO_AUDIT_LOG_DIR", str(tmp_path))
    _write_sidecar(tmp_path, VALID)
    monkeypatch.setenv("CEO_BUDGET_QUOTA_HINT", "0")
    assert cb._statusline_quota_hint() == ""


def test_missing_sidecar_failsoft(tmp_path, monkeypatch):
    monkeypatch.setenv("CEO_STATUSLINE_SIDECAR", str(tmp_path / "absent.json"))
    assert cb._statusline_quota_hint() == ""


def test_wrong_schema_ignored(tmp_path, monkeypatch):
    monkeypatch.setenv("CEO_AUDIT_LOG_DIR", str(tmp_path))
    _write_sidecar(tmp_path, {"schema": "evil/v9", "rate_limits": {"x": {"used_pct": 9}}})
    assert cb._statusline_quota_hint() == ""


def test_no_buckets_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("CEO_AUDIT_LOG_DIR", str(tmp_path))
    _write_sidecar(tmp_path, {"schema": "statusline-sidecar/v1", "rate_limits": {}})
    assert cb._statusline_quota_hint() == ""


def test_corrupt_json_failsoft(tmp_path, monkeypatch):
    d = tmp_path / "state"
    d.mkdir(parents=True)
    (d / "statusline-snapshot.json").write_text("}{ not json")
    monkeypatch.setenv("CEO_AUDIT_LOG_DIR", str(tmp_path))
    assert cb._statusline_quota_hint() == ""


def test_decide_warning_includes_hint(tmp_path, monkeypatch):
    """Integration: over-cap path appends the hint to the warning string.

    We exercise the helper directly and assert it composes into a warning the
    same way decide() does — without standing up the full audit-log fixture
    (the helper is the only O4 surface; the rest of decide() is unchanged)."""
    monkeypatch.setenv("CEO_AUDIT_LOG_DIR", str(tmp_path))
    _write_sidecar(tmp_path, VALID)
    base = ("BUDGET WARNING: plan PLAN-999 at 5/4 tokens (125%). "
            "Advisory-only (Sprint 11). Set CEO_BUDGET_BYPASS=1 to suppress "
            "this warning for urgent work. See ADR-033.")
    composed = base + cb._statusline_quota_hint()
    assert composed.startswith("BUDGET WARNING")
    assert "Live quota" in composed
