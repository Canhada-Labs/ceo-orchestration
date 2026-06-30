"""Tests for optimizer.model_normalize — PLAN-133 B2.

`normalize_model_name` is alias/whitespace/case canonicalization ONLY and MUST
preserve the major.minor version token (no fuzzy version collapse). The
load-bearing invariant tested here is ``opus-4-1`` != ``opus-4-8``.

These tests use no env, no IO, no TestEnvContext (the function is pure and never
reads env or HOME), so they are hermetic by construction.
"""

from __future__ import annotations

import pytest

from optimizer.model_normalize import normalize_model_name


# ---------------------------------------------------------------------------
# Core invariant: version preservation (the AC's named test).
# ---------------------------------------------------------------------------
def test_opus_4_1_and_4_8_normalize_distinct():
    """The load-bearing B2 invariant: distinct major.minor must stay distinct.

    A fuzzy substring normalizer (PLAN-123 Codex P1 #6 bug) would collapse
    ``opus-4-1`` into ``opus-4-8`` and underbill ~3x. ours must not."""
    a = normalize_model_name("opus-4-1")
    b = normalize_model_name("opus-4-8")
    assert a != b
    assert a == "claude-opus-4-1"
    assert b == "claude-opus-4-8"


def test_legacy_vs_new_opus_tier_token_preserved():
    """opus-4-0 / opus-4-1 (legacy/expensive) vs opus-4-2+ (new/cheap) must keep
    their major.minor so measure_multiplier.MODEL_PRICING resolves the right
    tier regex (opus-4-[01] vs opus-4-(?:[2-9]|1\\d))."""
    assert normalize_model_name("claude-opus-4-0") == "claude-opus-4-0"
    assert normalize_model_name("claude-opus-4-1") == "claude-opus-4-1"
    assert normalize_model_name("claude-opus-4-2") == "claude-opus-4-2"
    # No two of these collapse onto each other.
    ids = {
        normalize_model_name(x)
        for x in ("opus-4-0", "opus-4-1", "opus-4-2", "opus-4-7", "opus-4-8")
    }
    assert len(ids) == 5


# ---------------------------------------------------------------------------
# The 6-pin tier sweep (reference-agent-model-tier-change-web): every model id
# the framework pins across agents/_dispatch/set-quality-profile/tests resolves
# to its canonical slug, and the three VETO-floor + profile families round-trip.
# ---------------------------------------------------------------------------
# (canonical slug, [raw variants that must all fold onto it])
_SWEEP = [
    (
        "claude-opus-4-8",
        [
            "claude-opus-4-8",
            "Claude-Opus-4-8",
            "  claude-opus-4-8  ",
            "opus-4-8",
            "claude-opus-4-8-20251101",
            "claude-opus-4-8[1m]",
            "anthropic/claude-opus-4-8",
        ],
    ),
    (
        "claude-sonnet-4-6",
        [
            "claude-sonnet-4-6",
            "CLAUDE-SONNET-4-6",
            "sonnet-4-6",
            "claude-sonnet-4-6-20250930",
            "anthropic/claude-sonnet-4-6",
        ],
    ),
    (
        "claude-haiku-4-5",
        [
            "claude-haiku-4-5",
            "haiku-4-5",
            "claude-haiku-4-5-20251001",
            "  Claude-Haiku-4-5 ",
        ],
    ),
]


@pytest.mark.parametrize("canonical,variants", _SWEEP)
def test_six_pin_family_sweep(canonical, variants):
    for raw in variants:
        assert normalize_model_name(raw) == canonical, (raw, canonical)


def test_sweep_families_are_mutually_distinct():
    canon = {c for c, _ in _SWEEP}
    assert len(canon) == len(_SWEEP)  # no family collides with another


# ---------------------------------------------------------------------------
# Case / whitespace folding.
# ---------------------------------------------------------------------------
def test_case_and_whitespace_folding():
    assert normalize_model_name("  CLAUDE-OPUS-4-8  ") == "claude-opus-4-8"
    assert normalize_model_name("claude opus 4 8") == "claudeopus48"  # ws collapsed
    assert normalize_model_name("\tclaude-sonnet-4-6\n") == "claude-sonnet-4-6"


def test_vendor_prefix_stripped_but_claude_prefix_kept():
    assert normalize_model_name("anthropic/claude-opus-4-8") == "claude-opus-4-8"
    # the canonical agent-frontmatter slug carries the claude- prefix; keep it.
    assert normalize_model_name("claude-opus-4-8") == "claude-opus-4-8"


def test_one_m_packaging_tag_folded():
    # the harness live id ``claude-opus-4-8[1m]`` is a packaging tag, not a version.
    assert normalize_model_name("claude-opus-4-8[1m]") == "claude-opus-4-8"
    # but it must not fold a DIFFERENT version's tag onto 4-8.
    assert normalize_model_name("claude-opus-4-1") == "claude-opus-4-1"


# ---------------------------------------------------------------------------
# Unknown / passthrough — never guess, never raise.
# ---------------------------------------------------------------------------
def test_unknown_model_passthrough_normalized_form():
    # unrecognized id returns case/whitespace-normalized, version token intact.
    assert normalize_model_name("Some-Future-Model-9-9") == "some-future-model-9-9"
    assert normalize_model_name("gpt-5") == "gpt-5"  # we don't price it; we don't mangle it


def test_blank_and_none_safe():
    assert normalize_model_name("") == ""
    assert normalize_model_name("   ") == ""
    assert normalize_model_name(None) == ""  # type: ignore[arg-type]


def test_never_raises_on_pathological_input():
    class Bad:
        def __str__(self):  # noqa: D401
            raise RuntimeError("boom")

    # fail-open to empty string; never propagate.
    assert normalize_model_name(Bad()) == ""  # type: ignore[arg-type]


def test_idempotent():
    for raw in ("opus-4-1", "claude-opus-4-8-20251101", "anthropic/claude-sonnet-4-6"):
        once = normalize_model_name(raw)
        assert normalize_model_name(once) == once


def test_date_stamp_folds_to_same_version_not_a_bump():
    # a date-stamped 4-1 pin folds to 4-1, NOT 4-8.
    assert normalize_model_name("claude-opus-4-1-20250805") == "claude-opus-4-1"
    assert normalize_model_name("claude-opus-4-1-20250805") != "claude-opus-4-8"
