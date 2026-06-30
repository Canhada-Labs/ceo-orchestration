"""TDD emission contract for the NEW audit action ``codex_review_invoked`` (WS-3).

These tests pin the contract the LATER GPG ceremony (WS3-T4) must satisfy when it
registers ``codex_review_invoked`` in the canonical KERNEL
``.claude/hooks/_lib/audit_emit.py``:

  * the action is registered in ``_KNOWN_ACTIONS`` (so ``safe_emit`` stops being a
    silent no-op and the event actually persists),
  * its Sec MF-3 deny-by-default allowlist
    (``_OPTIMIZER_ALLOWLISTS["codex_review_invoked"]``) admits exactly the
    PhaseReview-shaped fields and DENIES everything else (raw Codex text, the
    ``tokens_*`` side channel, the ``review_disabled_signal`` bool),
  * the ``emit_generic`` scrub drops an out-of-spec key AND leaves a breadcrumb,
  * the redacted ``PhaseReview`` from ``optimizer.codex_phase_gate`` maps cleanly
    onto that allowlist (every forwarded field is admitted; nothing leaks).

The action is NOT registered yet (that is WS3-T4-GPG), so EVERY test is
``@pytest.mark.skip``-guarded — the suite stays GREEN now (all skipped == green)
and the tests activate the moment ``codex_review_invoked`` lands. We use ``skip``
deliberately, NOT ``xfail(strict=True)`` (avoid the xpass-strict flake trap:
[[feedback-xpass-strict-flake-trap]] — an action that registers early would flip
a strict xfail to a hard xpass failure; skip just turns green).

Mocked / pure throughout — ZERO real Codex, ZERO network, ZERO paid LLM call.
"""

from __future__ import annotations

import pytest

from optimizer import codex_phase_gate as PG

# The canonical audit module. Importable via the repo conftest sys.path seed
# (`.claude/hooks` is on sys.path), so `from _lib import audit_emit` resolves.
from _lib import audit_emit  # type: ignore[import]


_ACTION = "codex_review_invoked"
_SKIP_REASON = (
    "awaiting WS3-T4-GPG codex_review_invoked registration in audit_emit.py"
)

# The 9 per-action fields the allowlist must admit, on top of the
# `_OPTIMIZER_ENVELOPE` ("action", "session_id"). Kept in the test as the
# independent source of truth the WS3-T4 registration is checked against.
# The 7 original PhaseReview-shaped fields + the 2 PLAN-132 / ADR-145
# branch-binding fields (review_source, target_ref_hash) added in S221.
_EXPECTED_PER_ACTION_FIELDS = frozenset({
    "phase_number",
    "review_status",
    "summary_hash",
    "thread_id_redacted",
    "codex_model",
    "duration_ms",
    "violations_found_count",
    "review_source",      # PLAN-132 / ADR-145 (S221) — branch-binding provenance
    "target_ref_hash",    # PLAN-132 / ADR-145 (S221) — branch-binding provenance
})


# --- registration -----------------------------------------------------------

def test_action_is_registered():
    """WS3-T4 must add ``codex_review_invoked`` to ``_KNOWN_ACTIONS``."""
    assert _ACTION in audit_emit._KNOWN_ACTIONS


def test_disabled_sibling_is_already_registered():
    """``codex_review_disabled`` (S190) is reused as-is, not re-added."""
    assert "codex_review_disabled" in audit_emit._KNOWN_ACTIONS


# --- allowlist shape (Sec MF-3 deny-by-default) -----------------------------

def test_allowlist_entry_exists():
    """WS3-T4 must add an ``_OPTIMIZER_ALLOWLISTS`` entry for the action."""
    assert _ACTION in audit_emit._OPTIMIZER_ALLOWLISTS


def test_allowlist_admits_envelope_and_per_action_fields():
    """The allowlist == envelope ("action", "session_id") + the 9 per-action fields."""
    allow = audit_emit._OPTIMIZER_ALLOWLISTS[_ACTION]
    expected = frozenset(audit_emit._OPTIMIZER_ENVELOPE) | _EXPECTED_PER_ACTION_FIELDS
    assert allow == expected


def test_allowlist_denies_token_side_channel():
    """tokens_* must NOT be allowlisted (Codex 019e7ebc P1 token side-channel)."""
    allow = audit_emit._OPTIMIZER_ALLOWLISTS[_ACTION]
    assert "tokens_in" not in allow
    assert "tokens_out" not in allow
    assert "tokens_total" not in allow


def test_allowlist_denies_disabled_signal_bool():
    """review_disabled_signal (a bool) must NOT cross into this action."""
    allow = audit_emit._OPTIMIZER_ALLOWLISTS[_ACTION]
    assert "review_disabled_signal" not in allow


def test_allowlist_denies_raw_codex_text_fields():
    """No raw Codex text (summary / thread_id / prompt / diff) is allowlisted."""
    allow = audit_emit._OPTIMIZER_ALLOWLISTS[_ACTION]
    for forbidden in ("summary", "thread_id", "thread", "review", "prompt",
                      "diff", "diff_or_summary", "verdict", "reason"):
        assert forbidden not in allow, forbidden


# --- scrub behavior (the real _scrub_ceo_boot_event boundary) ---------------

def test_scrub_drops_out_of_spec_keys():
    """An out-of-spec field is stripped; in-spec fields survive."""
    allow = audit_emit._OPTIMIZER_ALLOWLISTS[_ACTION]
    event = {
        "action": _ACTION,
        "session_id": "sess-1",
        "phase_number": 2,
        "review_status": "passed",
        # out-of-spec — MUST be dropped:
        "summary": "raw codex text that must never persist",
        "tokens_total": 12345,
        "review_disabled_signal": False,
    }
    cleaned, dropped = audit_emit._scrub_ceo_boot_event(event, allow)
    assert "summary" not in cleaned
    assert "tokens_total" not in cleaned
    assert "review_disabled_signal" not in cleaned
    assert set(dropped) == {"summary", "tokens_total", "review_disabled_signal"}
    # in-spec fields are preserved verbatim
    assert cleaned["phase_number"] == 2
    assert cleaned["review_status"] == "passed"
    assert cleaned["session_id"] == "sess-1"


def test_emit_generic_scrubs_and_breadcrumbs_on_drop(monkeypatch):
    """emit_generic must route the action through the scrub and breadcrumb a drop.

    We capture _breadcrumb and _write_event so the test is pure (no real audit
    log write). A forbidden field must be dropped AND breadcrumbed; in-spec
    fields reach _write_event.
    """
    crumbs = []
    written = {}
    monkeypatch.setattr(audit_emit, "_breadcrumb", lambda m: crumbs.append(m))
    monkeypatch.setattr(audit_emit, "_write_event", lambda ev: written.update(ev))

    audit_emit.emit_generic(
        _ACTION,
        session_id="sess-2",
        review_status="failed",
        violations_found_count=3,
        summary="raw codex text — must be dropped",   # forbidden
    )

    # the forbidden field never reached _write_event
    assert "summary" not in written
    # in-spec fields did
    assert written.get("review_status") == "failed"
    assert written.get("violations_found_count") == 3
    # a breadcrumb names the dropped field
    assert any("summary" in c for c in crumbs), crumbs


# --- PhaseReview -> allowlist mapping (the driver feeds this action) ---------

def test_phase_review_fields_are_all_admitted(monkeypatch):
    """Every PhaseReview field the caller forwards is admitted by the allowlist.

    The driver returns an audit-safe PhaseReview; the caller forwards its
    fields MINUS review_disabled_signal (which routes codex_review_disabled
    instead). Those forwarded keys must all be in the allowlist — nothing the
    driver emits gets silently scrubbed.
    """
    monkeypatch.delenv("CEO_CODEX_REVIEW", raising=False)

    def _invoke_failed(payload, model):
        return {"status": "block", "violations": 2,
                "thread_id": "019e7ebc-cccc", "summary": "2 P0s"}

    review = PG.review_phase(7, "diff body", codex_invoke=_invoke_failed)
    allow = audit_emit._OPTIMIZER_ALLOWLISTS[_ACTION]

    forwarded = {
        "phase_number": review.phase_number,
        "review_status": review.review_status,
        "thread_id_redacted": review.thread_id_redacted,
        "violations_found_count": review.violations_found_count,
        "summary_hash": review.summary_hash,
        "codex_model": review.codex_model,
        "duration_ms": review.duration_ms,
    }
    for key in forwarded:
        assert key in allow, key
    # and the bool is intentionally NOT forwarded
    assert "review_disabled_signal" not in forwarded


def test_redacted_fields_carry_no_raw_codex_text(monkeypatch):
    """The redacted PhaseReview never carries the raw thread id / summary text."""
    monkeypatch.delenv("CEO_CODEX_REVIEW", raising=False)
    raw_thread = "019e7ebc-secret-thread-id"
    raw_summary = "VERY secret codex review prose that must never persist"

    def _invoke(payload, model):
        return {"status": "accept", "violations": 0,
                "thread_id": raw_thread, "summary": raw_summary}

    review = PG.review_phase(1, "diff", codex_invoke=_invoke)
    # the redacted forms are hashes/sentinels, never the raw strings
    assert raw_thread not in review.thread_id_redacted
    assert raw_summary not in review.summary_hash


# --- kill-switch routing (the disabled sibling, NOT this action) ------------

def test_killswitch_off_routes_disabled_not_invoked(monkeypatch):
    """CEO_CODEX_REVIEW=0 -> review_disabled_signal True; caller emits the
    *disabled* action, NOT codex_review_invoked (no invocation occurred)."""
    monkeypatch.setenv("CEO_CODEX_REVIEW", "0")
    review = PG.review_phase(3, "diff", codex_invoke=lambda p, m: {"status": "accept"})
    assert review.review_disabled_signal is True
    assert review.review_status == PG.REVIEW_DEFERRED
    # both actions exist once WS3-T4 lands; the disabled one is the right sink here
    assert "codex_review_disabled" in audit_emit._KNOWN_ACTIONS
    assert _ACTION in audit_emit._KNOWN_ACTIONS
