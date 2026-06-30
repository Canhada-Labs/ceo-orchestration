"""Tests for optimizer.codex_phase_gate — WS-3 Cross-LLM Codex phase-gate driver.

Covers (per WS3-T1+T2+T8):
  * passed / failed / deferred parse paths with a mocked codex_invoke,
  * malformed Codex output -> deferred (no raise),
  * CEO_CODEX_REVIEW=0 -> deferred + review_disabled_signal,
  * redaction stable + never leaks the raw thread id / summary,
  * ReDoS adversarial input completes fast (< 50 ms).

Mocked Codex throughout (injected callable) — ZERO real Codex / network.
"""

from __future__ import annotations

import time

import pytest

from optimizer import codex_phase_gate as PG
from optimizer._codex_redaction import (
    redact_thread_id,
    summary_hash,
)


def _review_on(monkeypatch):
    """Ensure CEO_CODEX_REVIEW is in its default (enabled) state."""
    monkeypatch.delenv("CEO_CODEX_REVIEW", raising=False)


# --- helpers: mocked Codex invokers -----------------------------------------

def _invoke_passed(payload, model):
    return {"status": "accept", "violations": 0, "thread_id": "019e7ebc-aaaa",
            "summary": "looks clean"}


def _invoke_failed(payload, model):
    return {"status": "block", "violations": 3, "thread_id": "019e7ebc-bbbb",
            "summary": "3 P0s found"}


def _invoke_deferred(payload, model):
    return {"status": "error", "reason": "codex unreachable"}


# --- T1: parse paths --------------------------------------------------------

def test_passed_parse_path(monkeypatch):
    _review_on(monkeypatch)
    r = PG.review_phase(1, "diff text", codex_invoke=_invoke_passed)
    assert r.review_status == PG.REVIEW_PASSED
    assert r.violations_found_count == 0
    assert r.phase_number == 1
    assert r.codex_model == "gpt-5-codex"
    assert r.review_disabled_signal is False
    assert r.duration_ms >= 0


def test_failed_parse_path(monkeypatch):
    _review_on(monkeypatch)
    r = PG.review_phase(2, "diff text", codex_invoke=_invoke_failed)
    assert r.review_status == PG.REVIEW_FAILED
    assert r.violations_found_count == 3


def test_deferred_parse_path(monkeypatch):
    _review_on(monkeypatch)
    r = PG.review_phase(3, "diff text", codex_invoke=_invoke_deferred)
    assert r.review_status == PG.REVIEW_DEFERRED
    assert r.violations_found_count == 0
    assert r.review_disabled_signal is False


def test_failed_with_zero_violations_normalised(monkeypatch):
    _review_on(monkeypatch)
    r = PG.review_phase(1, "x", codex_invoke=lambda p, m: {"status": "fail",
                                                           "violations": 0})
    # A failed verdict with zero reported violations is normalised to >=1.
    assert r.review_status == PG.REVIEW_FAILED
    assert r.violations_found_count == 1


def test_passed_forces_zero_violations(monkeypatch):
    _review_on(monkeypatch)
    r = PG.review_phase(1, "x", codex_invoke=lambda p, m: {"status": "passed",
                                                           "violations": 9})
    # "passed with 9 violations" is inconsistent: trust the verdict, zero count.
    assert r.review_status == PG.REVIEW_PASSED
    assert r.violations_found_count == 0


def test_bare_string_result(monkeypatch):
    _review_on(monkeypatch)
    r = PG.review_phase(1, "x", codex_invoke=lambda p, m: "ACCEPTED")
    assert r.review_status == PG.REVIEW_PASSED
    r2 = PG.review_phase(1, "x", codex_invoke=lambda p, m: "BLOCK")
    assert r2.review_status == PG.REVIEW_FAILED


def test_verdict_alias_field(monkeypatch):
    _review_on(monkeypatch)
    r = PG.review_phase(1, "x", codex_invoke=lambda p, m: {"verdict": "approved"})
    assert r.review_status == PG.REVIEW_PASSED


def test_custom_model_slug_forwarded(monkeypatch):
    _review_on(monkeypatch)
    r = PG.review_phase(1, "x", codex_invoke=_invoke_passed, codex_model="gpt-x")
    assert r.codex_model == "gpt-x"


def test_default_invoke_is_offline_deferred(monkeypatch):
    _review_on(monkeypatch)
    # No codex_invoke injected -> default no-op stub -> deferred, no network.
    r = PG.review_phase(1, "diff")
    assert r.review_status == PG.REVIEW_DEFERRED
    assert r.review_disabled_signal is False


# --- T1: malformed / hostile output -> deferred, never raises ---------------

@pytest.mark.parametrize("bad", [
    None,
    42,
    [1, 2, 3],
    {"status": object()},
    {"status": 12345},
    {"violations": "not-a-number"},
    {},
    {"status": "weird-unknown-verdict"},
])
def test_malformed_output_defers_no_raise(monkeypatch, bad):
    _review_on(monkeypatch)
    r = PG.review_phase(1, "x", codex_invoke=lambda p, m: bad)
    assert r.review_status in (PG.REVIEW_DEFERRED, PG.REVIEW_PASSED,
                               PG.REVIEW_FAILED)
    # the critical invariant: it returned a PhaseReview, never raised.
    assert isinstance(r, PG.PhaseReview)


def test_invoke_that_raises_defers(monkeypatch):
    _review_on(monkeypatch)

    def _boom(payload, model):
        raise RuntimeError("codex exploded")

    r = PG.review_phase(1, "x", codex_invoke=_boom)
    assert r.review_status == PG.REVIEW_DEFERRED
    assert r.review_disabled_signal is False


def test_bad_phase_number_coerced(monkeypatch):
    _review_on(monkeypatch)
    r = PG.review_phase("not-an-int", "x", codex_invoke=_invoke_passed)  # type: ignore[arg-type]
    assert isinstance(r.phase_number, int)
    assert r.phase_number == 0


def test_non_str_diff_does_not_raise(monkeypatch):
    _review_on(monkeypatch)
    r = PG.review_phase(1, None, codex_invoke=_invoke_passed)  # type: ignore[arg-type]
    assert isinstance(r, PG.PhaseReview)


def test_non_callable_invoke_falls_back(monkeypatch):
    _review_on(monkeypatch)
    r = PG.review_phase(1, "x", codex_invoke="not-callable")  # type: ignore[arg-type]
    assert r.review_status == PG.REVIEW_DEFERRED


# --- T8: CEO_CODEX_REVIEW kill-switch ---------------------------------------

def test_kill_switch_off_defers_and_signals(monkeypatch):
    monkeypatch.setenv("CEO_CODEX_REVIEW", "0")
    sentinel = {"called": False}

    def _tracking_invoke(payload, model):
        sentinel["called"] = True
        return _invoke_passed(payload, model)

    r = PG.review_phase(1, "x", codex_invoke=_tracking_invoke)
    assert r.review_status == PG.REVIEW_DEFERRED
    assert r.review_disabled_signal is True
    # short-circuit: the injected codex_invoke must NOT have been called.
    assert sentinel["called"] is False
    assert r.thread_id_redacted == "none"
    assert r.summary_hash == "none"


@pytest.mark.parametrize("off_val", ["0", "false", "off", "no", "FALSE", "Off"])
def test_kill_switch_off_values(monkeypatch, off_val):
    monkeypatch.setenv("CEO_CODEX_REVIEW", off_val)
    r = PG.review_phase(1, "x", codex_invoke=_invoke_passed)
    assert r.review_status == PG.REVIEW_DEFERRED
    assert r.review_disabled_signal is True


def test_default_posture_is_enabled(monkeypatch):
    _review_on(monkeypatch)
    r = PG.review_phase(1, "x", codex_invoke=_invoke_passed)
    # switch absent -> review ENABLED -> not disabled, real verdict.
    assert r.review_disabled_signal is False
    assert r.review_status == PG.REVIEW_PASSED


@pytest.mark.parametrize("on_val", ["1", "true", "on", "yes", ""])
def test_kill_switch_non_off_values_keep_enabled(monkeypatch, on_val):
    monkeypatch.setenv("CEO_CODEX_REVIEW", on_val)
    r = PG.review_phase(1, "x", codex_invoke=_invoke_passed)
    assert r.review_disabled_signal is False


# --- T2: redaction / hash purity --------------------------------------------

def test_thread_id_redaction_stable():
    raw = "019e7ebc-aaaa-bbbb-cccc"
    a = redact_thread_id(raw)
    b = redact_thread_id(raw)
    assert a == b                  # deterministic / stable
    assert raw not in a            # raw never leaks
    assert "019e7ebc" not in a     # not even the prefix
    assert len(a) == 16
    assert all(c in "0123456789abcdef" for c in a)


def test_thread_id_redaction_distinct():
    assert redact_thread_id("019e7ebc-aaaa") != redact_thread_id("019e7ebc-bbbb")


def test_thread_id_redaction_handles_noisy_line():
    redacted = redact_thread_id("thread id is wf_7247d2b1-deadbeef please")
    assert "wf_7247d2b1" not in redacted
    assert len(redacted) == 16


@pytest.mark.parametrize("empty", [None, "", "   ", 12345, [], {}])
def test_thread_id_redaction_empty_sentinel(empty):
    assert redact_thread_id(empty) == "none"  # type: ignore[arg-type]


def test_summary_hash_stable_and_opaque():
    text = "Codex says: leaked SECRET token sk-abcdef and prompt body here"
    a = summary_hash(text)
    b = summary_hash(text)
    assert a == b
    assert "SECRET" not in a
    assert "sk-abcdef" not in a
    assert "prompt" not in a
    assert len(a) == 16


@pytest.mark.parametrize("empty", [None, "", "   ", 99, []])
def test_summary_hash_empty_sentinel(empty):
    assert summary_hash(empty) == "none"  # type: ignore[arg-type]


def test_phase_review_never_carries_raw_codex_text(monkeypatch):
    _review_on(monkeypatch)
    secret_thread = "019e7ebc-SECRETTHREAD"
    secret_summary = "raw prompt body with API_KEY=sk-deadbeef leaked"

    def _leaky_invoke(payload, model):
        return {"status": "fail", "violations": 2,
                "thread_id": secret_thread, "summary": secret_summary}

    r = PG.review_phase(7, "diff", codex_invoke=_leaky_invoke)
    blob = repr(r)
    # NONE of the raw Codex text may appear anywhere in the returned tuple.
    assert "SECRETTHREAD" not in blob
    assert "sk-deadbeef" not in blob
    assert "API_KEY" not in blob
    assert "raw prompt body" not in blob
    # but the hashes ARE present and stable.
    assert r.thread_id_redacted == redact_thread_id(secret_thread)
    assert r.summary_hash == summary_hash(secret_summary)


# --- T2: ReDoS safety -------------------------------------------------------

def test_redos_adversarial_thread_id_fast():
    # An adversarial input designed to blow up a naive backtracking regex:
    # a long run of ambiguous chars + a trailing non-match. With bounded char
    # classes + explicit {m,n} this must stay linear.
    evil = ("a" * 50000) + "!" * 50000 + ("0a_-" * 20000)
    start = time.monotonic()
    out = redact_thread_id(evil)
    elapsed_ms = (time.monotonic() - start) * 1000.0
    assert elapsed_ms < 50.0, "redact_thread_id ReDoS: %.1fms" % elapsed_ms
    assert len(out) == 16


def test_redos_adversarial_summary_fast():
    evil = ("first " * 40000) + ("then " * 40000) + ("." * 40000)
    start = time.monotonic()
    out = summary_hash(evil)
    elapsed_ms = (time.monotonic() - start) * 1000.0
    assert elapsed_ms < 50.0, "summary_hash ReDoS: %.1fms" % elapsed_ms
    assert len(out) == 16


def test_review_phase_with_adversarial_codex_text_fast(monkeypatch):
    _review_on(monkeypatch)
    evil = "first" + ("a" * 100000) + "then"

    def _evil_invoke(payload, model):
        return {"status": "block", "violations": 1,
                "thread_id": evil, "summary": evil}

    start = time.monotonic()
    r = PG.review_phase(1, "x", codex_invoke=_evil_invoke)
    elapsed_ms = (time.monotonic() - start) * 1000.0
    assert elapsed_ms < 50.0, "review_phase ReDoS: %.1fms" % elapsed_ms
    assert r.review_status == PG.REVIEW_FAILED
