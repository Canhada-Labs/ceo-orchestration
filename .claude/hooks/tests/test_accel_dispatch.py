#!/usr/bin/env python3
"""Regression coverage for PLAN-128 Wave-1 #4 — accel_dispatch.py.

The single-process accelerator dispatcher merges the after-edit verify (#1) feedback
under ONE interpreter (latency-tax reduction). Runs the in-file ``_selftest()``
(single-process merge / clean-silent / H6-continueOnBlock-propagation / fail-open)
under pytest + a fail-open smoke. Stdlib only, Python >= 3.9.

PLAN-135 W2 H6 (STAGED, layered on the LIVE base): adds coverage that the dispatcher
propagates `continueOnBlock` through the block merge — emitted only when EVERY
blocking check opted in (a single hard-block check is never silently downgraded into
a continue). STAGED-ONLY per the COUPLING RULE (imports the staged hooks).
"""
from __future__ import annotations

import json

import accel_dispatch


def test_selftest_passes():
    accel_dispatch._selftest()


def test_empty_input_is_fail_open_silent():
    assert accel_dispatch.dispatch({}) == {}


def test_syntax_error_propagates_through_dispatcher(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text("def f(:\n")
    out = accel_dispatch.dispatch({"tool_input": {"file_path": str(bad)}, "cwd": str(tmp_path)})
    assert "AFTER-EDIT VERIFY" in json.dumps(out)


def test_failing_check_never_wedges_dispatch(monkeypatch):
    def boom(_hi):
        raise RuntimeError("checker blew up")

    monkeypatch.setattr(accel_dispatch, "CHECKS", [boom])
    assert accel_dispatch.dispatch({"tool_input": {"file_path": "x.py"}}) == {}


# ---- PLAN-135 W2 H6 — continueOnBlock propagation through the merge ----

def test_continue_on_block_propagates_when_sole_block(monkeypatch, tmp_path):
    """#1's continueOnBlock=True flows through the dispatcher when it is the only
    blocking check (unanimous opt-in)."""
    monkeypatch.setenv("CEO_VERIFY_AFTER_EDIT_BLOCK", "1")
    monkeypatch.delenv("CEO_VERIFY_AFTER_EDIT_NO_CONTINUE", raising=False)
    bad = tmp_path / "bad.py"
    bad.write_text("def f(x):\n    return x +\n")
    out = accel_dispatch.dispatch({"tool_input": {"file_path": str(bad)}, "cwd": str(tmp_path)})
    assert out.get("decision") == "block"
    assert out.get("continueOnBlock") is True


def test_legacy_hard_block_propagates_without_continue(monkeypatch, tmp_path):
    monkeypatch.setenv("CEO_VERIFY_AFTER_EDIT_BLOCK", "1")
    monkeypatch.setenv("CEO_VERIFY_AFTER_EDIT_NO_CONTINUE", "1")
    bad = tmp_path / "bad.py"
    bad.write_text("def f(x):\n    return x +\n")
    out = accel_dispatch.dispatch({"tool_input": {"file_path": str(bad)}, "cwd": str(tmp_path)})
    assert out.get("decision") == "block"
    assert "continueOnBlock" not in out


def test_mixed_block_votes_fail_to_hard_stop(monkeypatch, tmp_path):
    """If one blocking check opts into continueOnBlock and another does NOT, the merge
    must NOT downgrade to a continue (fail toward the stronger gate)."""
    def continuing(_hi):
        return {"decision": "block", "reason": "soft", "continueOnBlock": True}

    def hard(_hi):
        return {"decision": "block", "reason": "hard"}

    monkeypatch.setattr(accel_dispatch, "CHECKS", [continuing, hard])
    out = accel_dispatch.dispatch({"tool_input": {"file_path": str(tmp_path / "x.py")},
                                   "cwd": str(tmp_path)})
    assert out.get("decision") == "block"
    assert "continueOnBlock" not in out
    assert "soft" in out["reason"] and "hard" in out["reason"]


def test_unanimous_continue_votes_keep_the_turn(monkeypatch, tmp_path):
    def continuing_a(_hi):
        return {"decision": "block", "reason": "a", "continueOnBlock": True}

    def continuing_b(_hi):
        return {"decision": "block", "reason": "b", "continueOnBlock": True}

    monkeypatch.setattr(accel_dispatch, "CHECKS", [continuing_a, continuing_b])
    out = accel_dispatch.dispatch({"tool_input": {"file_path": str(tmp_path / "x.py")},
                                   "cwd": str(tmp_path)})
    assert out.get("decision") == "block"
    assert out.get("continueOnBlock") is True
