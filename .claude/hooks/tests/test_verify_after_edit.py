#!/usr/bin/env python3
"""Regression coverage for PLAN-128 Wave-1 #1 — verify_after_edit.py.

The module ships a comprehensive in-file ``_selftest()`` (clean-silent / surface /
path-escape / dash / kill / block / continueOnBlock-default / no-continue-revert /
non-source / missing / infra-noise-classifier); this wrapper runs it under pytest so
the after-edit verify loop is in the regression suite + contributes to the repo
coverage floor. `.claude/hooks/` is on sys.path via the tests/ conftest. Stdlib only,
Python >= 3.9.

PLAN-135 W2 H6 (STAGED, layered on the LIVE base): adds the `continueOnBlock`
(Claude Code 2.1.139) coverage — the hard-block opt-in now defaults to feeding the
rejection reason back and CONTINUING the turn (self-repair), with a revert switch
(CEO_VERIFY_AFTER_EDIT_NO_CONTINUE=1) to the legacy hard stop. STAGED-ONLY per the
COUPLING RULE: it imports the staged hook (which carries the H6 output field); the
live branch keeps its un-augmented copy and stays green standalone.
"""
from __future__ import annotations

import json

import verify_after_edit


def test_selftest_passes():
    verify_after_edit._selftest()


def test_infra_noise_is_not_a_finding():
    assert verify_after_edit._is_real_finding("No module named pyflakes", "bad.py") is False
    assert verify_after_edit._is_real_finding("bad.py:2: undefined name 'q'", "bad.py") is True


def test_missing_file_is_silent(tmp_path):
    out = verify_after_edit.verify(
        {"tool_input": {"file_path": "/nope/does_not_exist.py"}, "cwd": str(tmp_path)}
    )
    assert out == {}


def test_kill_switch(monkeypatch, tmp_path):
    monkeypatch.setenv("CEO_VERIFY_AFTER_EDIT", "0")
    bad = tmp_path / "bad.py"
    bad.write_text("def f(:\n")
    assert verify_after_edit.verify({"tool_input": {"file_path": str(bad)}, "cwd": str(tmp_path)}) == {}


def test_non_source_file_silent(tmp_path):
    note = tmp_path / "note.txt"
    note.write_text("hello")
    assert json.dumps(verify_after_edit.verify(
        {"tool_input": {"file_path": str(note)}, "cwd": str(tmp_path)})) == "{}"


# ---- PLAN-135 W2 H6 — continueOnBlock (self-repair instead of ending the turn) ----

def test_block_defaults_to_continue_on_block(monkeypatch, tmp_path):
    """With the hard-block opt-in on, a finding blocks BUT sets continueOnBlock=True
    (top-level field per Claude Code 2.1.139) so the turn keeps going for self-repair."""
    monkeypatch.setenv("CEO_VERIFY_AFTER_EDIT_BLOCK", "1")
    monkeypatch.delenv("CEO_VERIFY_AFTER_EDIT_NO_CONTINUE", raising=False)
    bad = tmp_path / "bad.py"
    bad.write_text("def f(x):\n    return x +\n")
    out = verify_after_edit.verify({"tool_input": {"file_path": str(bad)}, "cwd": str(tmp_path)})
    assert out.get("decision") == "block"
    assert out.get("continueOnBlock") is True
    assert "AFTER-EDIT VERIFY" in out.get("reason", "")


def test_no_continue_switch_restores_legacy_hard_block(monkeypatch, tmp_path):
    """CEO_VERIFY_AFTER_EDIT_NO_CONTINUE=1 reverts to the legacy turn-ending hard
    block — the continueOnBlock key must be absent (not just False)."""
    monkeypatch.setenv("CEO_VERIFY_AFTER_EDIT_BLOCK", "1")
    monkeypatch.setenv("CEO_VERIFY_AFTER_EDIT_NO_CONTINUE", "1")
    bad = tmp_path / "bad.py"
    bad.write_text("def f(x):\n    return x +\n")
    out = verify_after_edit.verify({"tool_input": {"file_path": str(bad)}, "cwd": str(tmp_path)})
    assert out.get("decision") == "block"
    assert "continueOnBlock" not in out


def test_advisory_path_never_emits_continue_on_block(tmp_path):
    """Without the block opt-in, a finding rides additionalContext (which never ends
    the turn), so continueOnBlock is meaningless and must NOT appear."""
    bad = tmp_path / "bad.py"
    bad.write_text("def f(x):\n    return x +\n")
    out = verify_after_edit.verify({"tool_input": {"file_path": str(bad)}, "cwd": str(tmp_path)})
    assert "decision" not in out
    assert "continueOnBlock" not in out
    assert "additionalContext" in out.get("hookSpecificOutput", {})


def test_clean_file_no_block_no_continue(tmp_path):
    """A clean file is silent even with the block opt-in on — no decision, no flag."""
    import os
    os.environ.pop("CEO_VERIFY_AFTER_EDIT", None)
    good = tmp_path / "ok.py"
    good.write_text("x = 1\n")
    out = verify_after_edit.verify({"tool_input": {"file_path": str(good)}, "cwd": str(tmp_path)})
    assert out == {}
