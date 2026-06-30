#!/usr/bin/env python3
"""Regression coverage for PLAN-128 Wave-1 #2 — route.py risk/cost router.

Runs the module's in-file ``_selftest()`` (risky-path / risky-content / large-diff /
trivial / test / dominance) under pytest + a few direct assertions on the public
classify()/needs_codex_review() API. Stdlib only, Python >= 3.9.
"""
from __future__ import annotations

import route


def test_selftest_passes():
    route._selftest()


def test_risky_path_dominates_triviality():
    assert route.classify("docs/auth.md")["tier"] == "risky"


def test_trivial_doc():
    assert route.classify("README.md")["tier"] == "trivial"


def test_ordinary_source_is_medium():
    assert route.classify("src/util/format.py")["tier"] == "medium"


def test_large_diff_is_risky():
    big = "".join("+ line %d\n" % i for i in range(route.LARGE_DIFF_LINES + 5))
    assert route.classify("src/util.py", big)["tier"] == "risky"


def test_needs_codex_review_gate():
    assert route.needs_codex_review("src/payments/charge.py") is True
    assert route.needs_codex_review("src/util/helpers.py") is False
