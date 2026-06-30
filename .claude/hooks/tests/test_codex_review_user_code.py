#!/usr/bin/env python3
"""Regression coverage for PLAN-128 Wave-1 #3 — codex_review_user_code.py.

The Stop-gate extends cross-model (Codex) review to the adopter's OWN code, but only
on a NEW risky diff. The in-file ``_selftest()`` covers the full matrix
(no-risky-silent / detect-only-default+dedupe / auto-skip-not-marked / auto-finding /
clean / block / kill-switch) with risky_diff + run_codex_review monkeypatched, so it
never shells out to git or codex. Stdlib only, Python >= 3.9.
"""
from __future__ import annotations

import json
import os

import codex_review_user_code as cr


def test_selftest_passes():
    cr._selftest()


def test_kill_switch_silent(monkeypatch, tmp_path):
    monkeypatch.setenv("CEO_CODEX_USER_REVIEW", "0")
    assert cr.gate(str(tmp_path)) == {}


def test_no_risky_files_is_silent(monkeypatch, tmp_path):
    monkeypatch.setattr(cr, "risky_diff", lambda cwd: ([], ""))
    os.makedirs(os.path.join(str(tmp_path), ".git"), exist_ok=True)
    assert cr.gate(str(tmp_path)) == {}


def test_detect_only_advises_then_dedupes(monkeypatch, tmp_path):
    monkeypatch.setattr(cr, "risky_diff", lambda cwd: (["src/auth/login.py"], "+ token == x\n"))

    def must_not_run(diff, cwd):
        raise AssertionError("Codex must not run in detect-only default mode")

    monkeypatch.setattr(cr, "run_codex_review", must_not_run)
    d = os.path.join(str(tmp_path), "repo")
    os.makedirs(os.path.join(d, ".git"), exist_ok=True)
    first = cr.gate(d)
    assert "RISKY DIFF" in json.dumps(first)
    assert cr.gate(d) == {}  # second call on the same diff dedupes
