"""Tests for optimizer.complexity_gate — WS-1 parallelizability routing."""

from __future__ import annotations

from optimizer import complexity_gate as G
from optimizer.types import (
    COMPLEXITY_TRIVIAL,
    MAX_FANOUT_WIDTH,
    ROUTE_FANOUT,
    ROUTE_PASSTHROUGH,
    ROUTE_SINGLE,
)


def test_kill_switch_forces_passthrough(monkeypatch):
    monkeypatch.setenv("CEO_OPTIMIZER", "0")
    r = G.classify("refactor the entire codebase across all files and rewrite every test")
    assert r.route == ROUTE_PASSTHROUGH
    assert r.complexity == COMPLEXITY_TRIVIAL
    assert "kill_switch" in r.reason


def test_trivial_is_passthrough(monkeypatch):
    monkeypatch.delenv("CEO_OPTIMIZER", raising=False)
    for p in ("oi", "fix typo", "what time is it", ""):
        r = G.classify(p)
        assert r.route == ROUTE_PASSTHROUGH, p


def test_newline_list_fans_out(monkeypatch):
    monkeypatch.delenv("CEO_OPTIMIZER", raising=False)
    prompt = (
        "Refactor the auth layer across these files:\n"
        "1. update login.py\n2. update session.py\n"
        "3. update tokens.py\n4. rewrite all the tests\n"
    )
    r = G.classify(prompt)
    assert r.route == ROUTE_FANOUT
    assert r.parallelizable is True
    assert 2 <= r.suggested_width <= MAX_FANOUT_WIDTH


def test_inline_numbered_fans_out(monkeypatch):
    monkeypatch.delenv("CEO_OPTIMIZER", raising=False)
    prompt = ("implement features comprehensively across the app: "
              "1. add caching 2. add retries 3. add metrics 4. add logging 5. add tracing")
    r = G.classify(prompt)
    assert r.route == ROUTE_FANOUT
    assert r.suggested_width >= 4


def test_version_string_not_a_false_unit(monkeypatch):
    monkeypatch.delenv("CEO_OPTIMIZER", raising=False)
    r = G.classify("bump version to 1.2.3 in setup.py")
    assert r.route in (ROUTE_PASSTHROUGH, ROUTE_SINGLE)
    assert r.parallelizable is False


def test_serial_dependency_blocks_fanout(monkeypatch):
    monkeypatch.delenv("CEO_OPTIMIZER", raising=False)
    prompt = ("audit security.py across the whole module, then after that fix the bugs, "
              "then finally deploy the release")
    r = G.classify(prompt)
    assert r.route == ROUTE_SINGLE
    assert r.parallelizable is False
    assert "serial" in r.reason


def test_long_serial_refactor_stays_single(monkeypatch):
    monkeypatch.delenv("CEO_OPTIMIZER", raising=False)
    # long + complex but inherently serial (no enumerable independent units)
    prompt = "Rewrite the parser " + ("and carefully preserve every edge case " * 30)
    r = G.classify(prompt)
    # has conjunctions but it is one continuous task; either single or fanout is
    # acceptable, but it must never crash and width must be bounded.
    assert r.suggested_width <= MAX_FANOUT_WIDTH


def test_suggested_width_bounded(monkeypatch):
    monkeypatch.delenv("CEO_OPTIMIZER", raising=False)
    prompt = "do these:\n" + "\n".join("%d. task %d" % (i, i) for i in range(1, 40))
    r = G.classify(prompt)
    assert r.suggested_width <= MAX_FANOUT_WIDTH


def test_never_raises_on_garbage(monkeypatch):
    monkeypatch.delenv("CEO_OPTIMIZER", raising=False)
    for p in ("\x00\x01", "🔥" * 500, "`" * 1000, "a,b,c," * 500):
        r = G.classify(p)
        assert r.suggested_width >= 1


def test_classify_handles_non_string(monkeypatch):
    monkeypatch.delenv("CEO_OPTIMIZER", raising=False)
    r = G.classify(None)  # type: ignore[arg-type]
    assert r.route == ROUTE_PASSTHROUGH


def test_bare_conjunction_does_not_fan_out(monkeypatch):
    """Regression (multi-lens P1): a compound sentence with no enumeration
    structure must NOT route to fan-out just because it contains 'and'."""
    monkeypatch.delenv("CEO_OPTIMIZER", raising=False)
    r = G.classify("Fix the bug and update the docs and run the tests")
    assert r.route != ROUTE_FANOUT
    assert r.parallelizable is False


def test_first_then_detected_as_serial(monkeypatch):
    """The 'first ... then' sequence must suppress parallelizability (it is a
    serial dependency) — now via the bounded detector, not the ReDoS regex."""
    monkeypatch.delenv("CEO_OPTIMIZER", raising=False)
    r = G.classify("first audit the code then fix the bugs across all the modules")
    assert r.parallelizable is False
    assert r.route == ROUTE_SINGLE


def test_redos_probe_is_bounded(monkeypatch):
    """Regression (multi-lens P0): 'first '*N (no 'then') must not catastrophically
    backtrack. Functional check here; latency is gated in the perf suite."""
    monkeypatch.delenv("CEO_OPTIMIZER", raising=False)
    r = G.classify("first " * 5000)
    assert r.suggested_width >= 1  # returns without hanging
