#!/usr/bin/env python3
"""Regression coverage for PLAN-128 Wave-1 #5 — adequacy_gate.py (temp-copy-safe Via Canhada gate).

The module ships a comprehensive in-file ``_selftest()`` (temp-copy-safe / strong-silent / weak-flag /
baseline-red-silent / no-test-advisory / opt-in / vendored-engine); this wrapper runs it under pytest so
the adequacy gate is in the regression suite + contributes to the repo coverage floor. It also adds an
end-to-end test through the REAL pytest subprocess runner to prove the production path never writes the
changed file. `.claude/hooks/` is on sys.path via the tests/ conftest. Stdlib only, Python >= 3.9.

WIRING NOTE: this file lands at `.claude/hooks/tests/test_adequacy_gate.py` alongside
`.claude/hooks/adequacy_gate.py` in the same Owner-GPG ceremony (see PLAN-128/wave1/WIRING.md).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

# Self-bootstrap the module dir onto sys.path (rite QA P1) so plain `pytest` collects this without a
# conftest. Resolves to PLAN-128/wave1/ in staging and to .claude/hooks/ once landed by the WIRING ceremony
# (where the hooks conftest also covers it) — correct in both locations.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import adequacy_gate  # noqa: E402


def test_selftest_passes():
    adequacy_gate._selftest()


def test_vendored_engine_yields_valid_mutants():
    muts = adequacy_gate.gen_mutants("def f(x):\n    return x + 1\n")
    assert muts, "expected at least one mutant"
    assert all(isinstance(m, str) for m in muts)
    assert "def f(x):\n    return x + 1\n" not in muts, "no-op mutant must be filtered"


def test_opt_in_silent_without_env(monkeypatch, tmp_path):
    monkeypatch.delenv("CEO_ADEQUACY_GATE", raising=False)
    src = tmp_path / "m.py"
    src.write_text("def g(x):\n    return x * 2\n")
    assert adequacy_gate.gate({"tool_input": {"file_path": str(src)}, "cwd": str(tmp_path)}) == {}


def test_real_file_never_written_strong_tests(tmp_path):
    """Production path through real pytest: strong tests → silent, and the changed file is byte-identical."""
    src = tmp_path / "calc.py"
    body = "def price(x):\n    return x * 9 // 10\n"
    src.write_text(body)
    (tmp_path / "test_calc.py").write_text(
        "from calc import price\n"
        "def test_price():\n"
        "    assert price(100) == 90\n"
        "    assert price(50) == 45\n"
        "    assert price(200) == 180\n"
        "    assert price(0) == 0\n"
    )
    r = adequacy_gate.adequacy(str(src), str(tmp_path))
    assert src.read_text() == body, "temp-copy-safe: the real file must be untouched"
    assert "weakly constrain" not in json.dumps(r), ("strong tests should not flag", r)


def test_weak_tests_flag_and_file_untouched(tmp_path):
    src = tmp_path / "calc.py"
    body = "def price(x):\n    return x * 9 // 10\n"
    src.write_text(body)
    (tmp_path / "test_calc.py").write_text(
        "from calc import price\n"
        "def test_is_int():\n"
        "    assert isinstance(price(100), int)\n"
    )
    r = adequacy_gate.adequacy(str(src), str(tmp_path))
    assert src.read_text() == body, "temp-copy-safe: the real file must be untouched"
    assert "weakly constrain" in json.dumps(r), ("weak tests should flag", r)


def test_no_sandbox_leak(tmp_path):
    src = tmp_path / "calc.py"
    src.write_text("def price(x):\n    return x * 9 // 10\n")
    (tmp_path / "test_calc.py").write_text(
        "from calc import price\ndef test_x():\n    assert price(10) == 9\n"
    )
    adequacy_gate.adequacy(str(src), str(tmp_path))
    leaks = [d for d in os.listdir(tempfile.gettempdir()) if d.startswith("ceo-adequacy-")]
    assert not leaks, ("sandbox dirs must be cleaned up", leaks)
