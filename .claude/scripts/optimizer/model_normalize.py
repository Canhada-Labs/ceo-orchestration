"""PLAN-133 B2 — model-name normalization (alias/whitespace/case ONLY).

A from-scratch stdlib re-implementation of the Goose model-name-canonicalization
*mechanism* (rite §2 — nothing fetched or run from the aaif-goose fork). The single
purpose is to fold the handful of well-known *raw aliases* and *casing/whitespace*
variants of a Claude model id onto ONE canonical slug **without ever collapsing two
distinct model versions**.

LOAD-BEARING INVARIANT (PLAN-133 §B2 + §3.1):
    ``normalize_model_name`` MUST preserve the ``major.minor`` version token so the
    downstream version-aware consumers keep resolving:
      * ``measure_multiplier.MODEL_PRICING`` — ``opus-4-[01]`` (legacy/expensive)
        vs ``opus-4-(?:[2-9]|1\\d)`` (new/cheap) regex tiers (PLAN-128/wave1).
      * ``_lib.agent_frontmatter.VETO_FLOOR_MODEL`` — exact ``claude-opus-4-8``.
      * ``_lib.model_routing`` static floor slugs.
    Therefore ``opus-4-1`` and ``opus-4-8`` MUST normalize to DISTINCT ids. This is
    NOT fuzzy matching: we never substring-collapse ``opus-4-1`` into ``opus-4-8``
    (the exact bug Codex P1 #6 caught in PLAN-123 ``pricing.normalize_model``).

What it DOES (and only this):
  1. lower-case + strip surrounding whitespace + collapse internal whitespace runs.
  2. map a small closed set of vendor *raw aliases* (e.g. a trailing date-stamp
     ``-20251001`` on a known family) onto the canonical dateless slug — alias only,
     never a version change.
  3. strip a redundant leading ``anthropic/`` / ``claude-3-5-`` style vendor namespace
     prefix where it is purely cosmetic (the ``claude-`` prefix is KEPT — it is part
     of the canonical agent-frontmatter slug ``claude-opus-4-8``).

What it explicitly does NOT do:
  * It does NOT guess a price, a tier, or a family for an unknown id.
  * It does NOT drop, round, or bump the ``major.minor`` (or ``major.minor.patch``)
    version token.
  * It does NOT raise — an unrecognized id is returned in its case/whitespace-
    normalized form so callers can flag-and-zero-price it (the S220 "unknown model
    costs 0 + flagged, do not guess" fallback is preserved at the call sites).

Pure, deterministic, stdlib-only, py>=3.9. No I/O, no env reads, never raises.

This is the **non-canonical optimizer-package** home of the function so the
optimizer (``model_choice.py``) and ``set-quality-profile.sh`` can use it today.
The IDENTICAL function is STAGED as the canonical ``_lib/model_normalize.py`` (the
eventual shared home for hooks/_lib consumers) under
``.claude/plans/PLAN-133/staged/B2.proposal.md`` for the Owner-GPG ceremony; the
two bodies are kept byte-identical below the module docstring on purpose.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Closed alias map — RAW vendor id -> canonical slug. ALIAS ONLY: each entry maps
# a known cosmetic/date-stamped variant onto its dateless canonical slug WITHOUT
# changing the major.minor version. A date-stamp (``-YYYYMMDD``) is a release
# pin of the SAME version, so folding it is safe; bumping the version is NOT.
#
# Keys are stored already lower-cased; lookup lower-cases the input first.
# Add a new alias => add an exact row here (no fuzzy/substring matching).
# ---------------------------------------------------------------------------
_RAW_ALIASES = {
    # Date-stamped release pins -> dateless canonical (same major.minor).
    "claude-haiku-4-5-20251001": "claude-haiku-4-5",
    "claude-sonnet-4-6-20250930": "claude-sonnet-4-6",
    "claude-opus-4-8-20251101": "claude-opus-4-8",
    "claude-opus-4-1-20250805": "claude-opus-4-1",
    # Bare-family aliases (no ``claude-`` prefix) -> canonical prefixed slug.
    "haiku-4-5": "claude-haiku-4-5",
    "sonnet-4-6": "claude-sonnet-4-6",
    "opus-4-8": "claude-opus-4-8",
    "opus-4-1": "claude-opus-4-1",
    # The ``[1m]`` context-window suffix the harness appends to the live model id
    # is a packaging tag, not a version — fold it (same major.minor).
    "claude-opus-4-8[1m]": "claude-opus-4-8",
}

# A purely-cosmetic vendor namespace prefix that some ids carry. Stripped ONLY when
# it leaves a still-recognizable ``claude-`` slug behind; never applied blindly.
_VENDOR_PREFIX_RX = re.compile(r"^anthropic/")

# Whitespace run collapser (after strip).
_WS_RX = re.compile(r"\s+")


def normalize_model_name(model: str) -> str:
    """Canonicalize a Claude model id by alias/whitespace/case ONLY.

    Steps (in order):
      1. coerce to str, lower-case, strip, collapse internal whitespace.
      2. drop a cosmetic ``anthropic/`` vendor prefix.
      3. map a known raw alias (incl. a date-stamp or ``[1m]`` packaging tag) onto
         its dateless canonical slug.
    The ``major.minor`` version token is NEVER altered: ``opus-4-1`` and
    ``opus-4-8`` return DISTINCT ids. An unrecognized id is returned in its
    case/whitespace-normalized form (callers flag-and-zero-price it; we never
    guess). Never raises.

    Examples:
        ``"  Claude-Opus-4-8  "`` -> ``"claude-opus-4-8"``
        ``"claude-opus-4-8-20251101"`` -> ``"claude-opus-4-8"``
        ``"opus-4-1"`` -> ``"claude-opus-4-1"`` (NOT ``claude-opus-4-8``)
        ``"claude-opus-4-8[1m]"`` -> ``"claude-opus-4-8"``
        ``"anthropic/claude-sonnet-4-6"`` -> ``"claude-sonnet-4-6"``
        ``"some-future-model-9-9"`` -> ``"some-future-model-9-9"`` (passthrough)
    """
    try:
        m = _WS_RX.sub("", str(model or "").strip().lower())
        if not m:
            return ""
        # Drop a cosmetic ``anthropic/`` namespace prefix before alias lookup.
        m = _VENDOR_PREFIX_RX.sub("", m)
        # Exact alias fold (date-stamp / bare-family / ``[1m]`` tag). NEVER fuzzy.
        if m in _RAW_ALIASES:
            return _RAW_ALIASES[m]
        return m
    except Exception:
        # Total + deterministic; the only way here is a pathological ``__str__``.
        # Fail-open to a safe empty string (caller treats as unknown -> zero-price).
        return ""
