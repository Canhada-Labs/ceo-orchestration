#!/usr/bin/env python3
"""Regression coverage for PLAN-128 Wave-1 #3 — codex_review_user_code.py.

The Stop-gate extends cross-model (Codex) review to the adopter's OWN code, but only
on a NEW risky diff. The in-file ``_selftest()`` covers the full matrix
(no-risky-silent / detect-only-default+dedupe / auto-skip-not-marked / auto-finding /
clean / block / kill-switch) with risky_diff + run_codex_review monkeypatched, so it
never shells out to git or codex. Stdlib only, Python >= 3.9.

Env hygiene (codex r4 F9, completed by r5 F9): FULL isolation via the
AGENTS.md-mandated ``TestEnvContext`` (``_lib/testing.py``) — an autouse
fixture below runs every test inside its setUp/tearDown, which snapshots
and restores HOME / CLAUDE_PROJECT_DIR / all CEO_* + CLAUDE_* vars /
cwd / sys.path and points HOME + the audit-log env at an isolated tmp
tree (so no emit can ever touch the real user profile).
``mock.patch.dict(os.environ, ...)`` context managers remain for the
specific CEO_* vars a test sets (never bare ``monkeypatch.setenv``);
attribute monkeypatching (setattr) stays on the pytest fixture.
``TestEnvContext`` is a ``unittest.TestCase`` (NOT a context manager), so
the fixture drives its setUp/tearDown explicitly — the supported way to
reuse it from pytest function-style tests.
"""
from __future__ import annotations

import json
import os
from unittest import mock

import pytest

import codex_review_user_code as cr
from _lib.testing import TestEnvContext


@pytest.fixture(autouse=True)
def _isolated_env():
    """codex r5 F9 — wrap EVERY test body in TestEnvContext isolation.

    mock.patch.dict alone restores only the keys a test touches; it
    leaves HOME, CLAUDE_PROJECT_DIR, inherited parent-shell CEO_* vars
    and sys.path pointing at the real environment. TestEnvContext.setUp
    snapshots all of that state, strips disruptive inherited overrides
    (CEO_KERNEL_OVERRIDE / CEO_QUIET_MODE / CEO_SOTA_DISABLE / ...),
    rehomes HOME + audit-log env into a per-test tmp tree, and tearDown
    restores everything exactly. Instantiating the TestCase directly and
    driving setUp/tearDown is the supported reuse path for pytest
    function-style tests (the default 'runTest' methodName is tolerated
    by unittest since 3.2).
    """
    env = TestEnvContext()
    env.setUp()
    try:
        yield env
    finally:
        env.tearDown()


def test_selftest_passes():
    cr._selftest()


def test_kill_switch_silent(tmp_path):
    with mock.patch.dict(os.environ, {"CEO_CODEX_USER_REVIEW": "0"}, clear=False):
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


# ---------------------------------------------------------------------------
# PLAN-161 W2 C5 — strict bounded verdict parser (r2 F2 + r3 F3 + r4 F1)
# ---------------------------------------------------------------------------


def test_parse_verdict_clean_variants():
    assert cr.parse_verdict("CLEAN") == "clean"
    assert cr.parse_verdict("clean") == "clean"
    assert cr.parse_verdict("  Clean \n") == "clean"


def test_parse_verdict_wellformed_findings():
    assert cr.parse_verdict("- login.py: timing-unsafe compare") == "findings"
    two = "- a.py: bug one\n- b.py: bug two\n"
    assert cr.parse_verdict(two) == "findings"
    # indented finding lines are still the pinned shape after strip
    assert cr.parse_verdict("  - a.py: x\n\n  - b.py: y") == "findings"


def test_parse_verdict_malformed_is_none():
    # anything not CLEAN and not the '- <file>: <issue>' grammar
    assert cr.parse_verdict("") is None
    assert cr.parse_verdict("   \n \n") is None
    assert cr.parse_verdict(None) is None
    assert cr.parse_verdict(123) is None  # type: ignore[arg-type]
    assert cr.parse_verdict("LGTM, ship it") is None
    assert cr.parse_verdict("- a.py missing colon-space separator") is None
    assert cr.parse_verdict("a.py: missing dash prefix") is None
    assert cr.parse_verdict("- a.py: ok\nplus a stray prose line") is None
    # CLEAN embedded in prose is NOT clean
    assert cr.parse_verdict("Everything is CLEAN here") is None


def test_parse_verdict_bounds():
    over_chars = "- a.py: " + "x" * cr.VERDICT_MAX_CHARS
    assert cr.parse_verdict(over_chars) is None
    over_lines = "\n".join(
        "- f%d.py: issue" % i for i in range(cr.VERDICT_MAX_LINES + 1)
    )
    assert cr.parse_verdict(over_lines) is None
    at_lines = "\n".join(
        "- f%d.py: issue" % i for i in range(cr.VERDICT_MAX_LINES)
    )
    assert cr.parse_verdict(at_lines) == "findings"


# ---------------------------------------------------------------------------
# PLAN-161 W2 C5 — typed codex_review_verdict emit per outcome
# ---------------------------------------------------------------------------


def _capture_telemetry(monkeypatch):
    calls = []

    def fake(cwd, diff, outcome, session_id):
        calls.append({"diff": diff, "outcome": outcome, "session_id": session_id})

    monkeypatch.setattr(cr, "_emit_verdict_telemetry", fake)
    return calls


def _risky(monkeypatch, diff="+ token == x\n"):
    monkeypatch.setattr(cr, "risky_diff", lambda cwd: (["src/auth/login.py"], diff))


def _repo(tmp_path, name="r"):
    d = os.path.join(str(tmp_path), name)
    os.makedirs(os.path.join(d, ".git"), exist_ok=True)
    return d


def test_detect_only_emits_detected_only_once(monkeypatch, tmp_path):
    calls = _capture_telemetry(monkeypatch)
    _risky(monkeypatch)
    d = _repo(tmp_path)
    cr.gate(d, session_id="sessA")
    assert [c["outcome"] for c in calls] == ["detected_only"]
    assert calls[0]["session_id"] == "sessA"
    cr.gate(d, session_id="sessA")  # deduped advisory → no second emit
    assert len(calls) == 1


def test_no_risky_diff_emits_nothing(monkeypatch, tmp_path):
    calls = _capture_telemetry(monkeypatch)
    monkeypatch.setattr(cr, "risky_diff", lambda cwd: ([], ""))
    d = _repo(tmp_path)
    assert cr.gate(d) == {}
    assert calls == []


def test_auto_infra_skip_emits_skipped_failopen_and_not_marked(monkeypatch, tmp_path):
    calls = _capture_telemetry(monkeypatch)
    _risky(monkeypatch)
    d = _repo(tmp_path)
    with mock.patch.dict(os.environ, {"CEO_CODEX_USER_REVIEW_AUTO": "1"}, clear=False):
        monkeypatch.setattr(cr, "run_codex_review", lambda diff, cwd: (True, None))
        assert "SKIPPED" in json.dumps(cr.gate(d, session_id="s1"))
        assert [c["outcome"] for c in calls] == ["skipped_failopen"]
        # not marked reviewed → a later real run still reviews + emits
        monkeypatch.setattr(cr, "run_codex_review", lambda diff, cwd: (True, "CLEAN"))
        assert "CLEAN" in json.dumps(cr.gate(d, session_id="s1"))
        assert [c["outcome"] for c in calls] == ["skipped_failopen", "clean"]


def test_auto_codex_missing_emits_skipped_failopen(monkeypatch, tmp_path):
    calls = _capture_telemetry(monkeypatch)
    _risky(monkeypatch)
    d = _repo(tmp_path)
    monkeypatch.setattr(cr, "run_codex_review", lambda diff, cwd: (False, None))
    with mock.patch.dict(os.environ, {"CEO_CODEX_USER_REVIEW_AUTO": "1"}, clear=False):
        assert "Codex CLI not found" in json.dumps(cr.gate(d))
    assert [c["outcome"] for c in calls] == ["skipped_failopen"]


def test_auto_malformed_verdict_is_skipped_failopen_never_healthy(monkeypatch, tmp_path):
    calls = _capture_telemetry(monkeypatch)
    _risky(monkeypatch)
    d = _repo(tmp_path)
    with mock.patch.dict(os.environ, {"CEO_CODEX_USER_REVIEW_AUTO": "1"}, clear=False):
        monkeypatch.setattr(
            cr, "run_codex_review", lambda diff, cwd: (True, "free-prose junk verdict")
        )
        r = cr.gate(d, session_id="s2")
        # fail-open UX unchanged: advisory still surfaces the output
        assert "junk verdict" in json.dumps(r)
        assert [c["outcome"] for c in calls] == ["skipped_failopen"]
        # MALFORMED did NOT mark the diff reviewed → the next Stop re-reviews
        monkeypatch.setattr(
            cr, "run_codex_review",
            lambda diff, cwd: (True, "- login.py: timing-unsafe compare"),
        )
        assert "timing-unsafe" in json.dumps(cr.gate(d, session_id="s2"))
        assert [c["outcome"] for c in calls] == ["skipped_failopen", "findings"]
        # a PARSED outcome marks reviewed → same diff now dedupes entirely
        assert cr.gate(d, session_id="s2") == {}
        assert len(calls) == 2


def test_auto_clean_emits_clean(monkeypatch, tmp_path):
    calls = _capture_telemetry(monkeypatch)
    _risky(monkeypatch)
    d = _repo(tmp_path)
    monkeypatch.setattr(cr, "run_codex_review", lambda diff, cwd: (True, "CLEAN"))
    with mock.patch.dict(os.environ, {"CEO_CODEX_USER_REVIEW_AUTO": "1"}, clear=False):
        assert "CLEAN" in json.dumps(cr.gate(d, session_id="s3"))
    assert calls == [
        {"diff": "+ token == x\n", "outcome": "clean", "session_id": "s3"}
    ]


# ---------------------------------------------------------------------------
# PLAN-161 W2 C5 — telemetry dedupe by (diff_sha256, outcome), separate from
# the review-status dedupe
# ---------------------------------------------------------------------------


def _capture_typed_emit(monkeypatch):
    """Patch the REAL audit_emit emitter (no sys.modules rebind — CI-safe)."""
    import sys as _sys

    _clib = os.path.join(
        os.path.dirname(os.path.abspath(cr.__file__)), "_lib"
    )
    if _clib not in _sys.path:
        _sys.path.insert(0, _clib)
    import audit_emit as ae

    emitted = []
    monkeypatch.setattr(
        ae,
        "emit_codex_review_verdict",
        lambda **kw: emitted.append(kw),
        raising=False,
    )
    return emitted


def test_telemetry_dedupe_same_pair_no_reemit(monkeypatch, tmp_path):
    emitted = _capture_typed_emit(monkeypatch)
    d = _repo(tmp_path)
    cr._emit_verdict_telemetry(d, "+ x\n", "skipped_failopen", "sA")
    cr._emit_verdict_telemetry(d, "+ x\n", "skipped_failopen", "sA")
    assert len(emitted) == 1
    assert emitted[0]["outcome"] == "skipped_failopen"
    assert emitted[0]["diff_sha256"] == cr._h("+ x\n")
    assert emitted[0]["session_id"] == "sA"


def test_telemetry_dedupe_distinct_outcome_reemits(monkeypatch, tmp_path):
    emitted = _capture_typed_emit(monkeypatch)
    d = _repo(tmp_path)
    cr._emit_verdict_telemetry(d, "+ x\n", "skipped_failopen", "sA")
    cr._emit_verdict_telemetry(d, "+ x\n", "clean", "sA")     # new outcome → emit
    cr._emit_verdict_telemetry(d, "+ y\n", "clean", "sA")     # new diff → emit
    cr._emit_verdict_telemetry(d, "+ x\n", "clean", "sB")     # same pair → NO emit
    assert [(e["outcome"], e["diff_sha256"]) for e in emitted] == [
        ("skipped_failopen", cr._h("+ x\n")),
        ("clean", cr._h("+ x\n")),
        ("clean", cr._h("+ y\n")),
    ]


def test_telemetry_state_separate_from_review_state(monkeypatch, tmp_path):
    _capture_typed_emit(monkeypatch)
    d = _repo(tmp_path)
    cr._emit_verdict_telemetry(d, "+ x\n", "clean", "")
    assert os.path.exists(cr._telemetry_path(d))
    assert cr._telemetry_path(d) != cr._state_path(d)
    # review-status state untouched by the telemetry write
    assert cr._status(d, "+ x\n") == ""


# ---------------------------------------------------------------------------
# PLAN-161 W2 C5 — session threading main() → gate()
# ---------------------------------------------------------------------------


def test_main_threads_session_id_from_stdin_event(monkeypatch, tmp_path, capsys):
    import io

    seen = {}

    def fake_gate(cwd, session_id=""):
        seen["cwd"] = cwd
        seen["session_id"] = session_id
        return {}

    monkeypatch.setattr(cr, "gate", fake_gate)
    monkeypatch.setattr(
        cr.sys, "stdin",
        io.StringIO(json.dumps({"cwd": str(tmp_path), "session_id": "sess-evt"})),
    )
    cr.main()
    assert seen == {"cwd": str(tmp_path), "session_id": "sess-evt"}
    assert capsys.readouterr().out.strip() == "{}"


def test_main_session_id_env_fallback(monkeypatch, tmp_path, capsys):
    import io

    seen = {}

    def fake_gate(cwd, session_id=""):
        seen["session_id"] = session_id
        return {}

    monkeypatch.setattr(cr, "gate", fake_gate)
    monkeypatch.setattr(
        cr.sys, "stdin", io.StringIO(json.dumps({"cwd": str(tmp_path)}))
    )
    with mock.patch.dict(os.environ, {"CLAUDE_SESSION_ID": "sess-env"}, clear=False):
        cr.main()
    assert seen["session_id"] == "sess-env"
