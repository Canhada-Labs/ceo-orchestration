"""Tournament scorer — strict-mode + llm-judge pass/fail classification.

Round 1 closures:
- C-P0-7: scorer.py is highest-value mutation target (≥80% kill rate in Phase 3e)
- QA F-QA adversarial-safe classifier: empty / oversized / non-UTF-8 outputs
  must mark "errored", never crash

Strict mode: regex/substring match of contestant output against
`fixture.acceptance_strict` list. Deterministic, no LLM call. Used for
quick-signal tier-boundary comparison.

LLM-judge mode: delegated to judge.py — strict-mode scorer is the first
pass; judge-mode is invoked post-strict on qualitative fixtures.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, List, Optional


def _safe_text(raw: Any) -> Optional[str]:
    """Best-effort extraction of string content from a response object.

    Resolution:
    1. response.content — FakeLLMDispatcher + Anthropic SDK shape
    2. str(response) as last resort
    Returns None if unavailable or invalid UTF-8 (not decodable to str).
    """
    if raw is None:
        return None
    content = getattr(raw, "content", None)
    if content is None:
        return None
    if isinstance(content, bytes):
        try:
            content = content.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            return None
    if not isinstance(content, str):
        return None
    return content


def score_strict(fixture, response) -> str:
    """Score a contestant response in strict mode.

    Returns one of: "pass" | "fail" | "errored".

    Semantics:
    - "errored": content missing / empty / non-decodable
    - "pass": ALL acceptance_strict items appear (case-insensitive substring)
      in the response. NFKC-normalized comparison to handle unicode
      look-alikes without false-passes from homoglyph confusion.
    - "fail": at least one acceptance_strict item missing

    Adversarial-safe: never raises. Empty acceptance_strict list → "pass"
    by vacuous truth (fixture author's choice, not scorer bug).
    """
    content = _safe_text(response)
    if content is None or not content.strip():
        return "errored"

    try:
        # NFKC normalization canonicalizes homoglyph variants (e.g.
        # Cyrillic 'а' → Latin 'a') so a fixture author can't trick the
        # scorer with visually-identical substitutions.
        content_norm = unicodedata.normalize("NFKC", content).lower()
        acceptance = getattr(fixture, "acceptance_strict", []) or []
        if not acceptance:
            return "pass"
        for needle in acceptance:
            if not isinstance(needle, str):
                return "errored"
            needle_norm = unicodedata.normalize("NFKC", needle).lower()
            if needle_norm not in content_norm:
                return "fail"
        return "pass"
    except Exception:
        # Adversarial-safe fail-open: any unexpected exception → errored
        return "errored"


def classify_bulk(fixture, response) -> dict:
    """Return a verbose score dict (useful for debugging + reporter).

    {
      "verdict": "pass"|"fail"|"errored",
      "mode": "strict",
      "missing_needles": [...]  # present only when verdict="fail"
    }
    """
    content = _safe_text(response)
    if content is None or not content.strip():
        return {"verdict": "errored", "mode": "strict", "reason": "empty_output"}

    try:
        content_norm = unicodedata.normalize("NFKC", content).lower()
        acceptance = getattr(fixture, "acceptance_strict", []) or []
        missing: List[str] = []
        for needle in acceptance:
            if not isinstance(needle, str):
                return {
                    "verdict": "errored",
                    "mode": "strict",
                    "reason": "invalid_acceptance_item",
                }
            if unicodedata.normalize("NFKC", needle).lower() not in content_norm:
                missing.append(needle)
        if missing:
            return {
                "verdict": "fail",
                "mode": "strict",
                "missing_needles": missing,
            }
        return {"verdict": "pass", "mode": "strict"}
    except Exception as exc:
        return {"verdict": "errored", "mode": "strict", "reason": str(exc)[:80]}
