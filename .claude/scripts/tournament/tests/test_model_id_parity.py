"""PLAN-045 Wave 2 P0-05 — tournament model-ID parity with tier_policy_cli.

Closes PLAN-044 F-12-02 / P0-05: tournament/runner.py and reporter.py
referenced ``claude-haiku-4-5`` (short form) while
tier_policy_cli/_types.py (formerly tier_policy/_types.py — renamed
PLAN-076 fork (f) for Python-importable underscore form) required the
full versioned ID ``claude-haiku-4-5-20251001``. Mismatch caused
tier_policy_cli.learn.py to silently drop Haiku rows — learned policy
for 1/3 of dispatchable models could never emerge.

This regression test anchors the two sources: every model string in
tournament's DEFAULT_MODELS + PRICING_USD_PER_M keys must appear in
tier_policy_cli's VALID_MODEL_IDS tuple.

Path-of-record note: this test points to ``tier_policy_cli/_types.py``
(NOT ``_lib/tier_policy/_types.py``). The two layers expose
DIFFERENT model-ID forms (scripts: full-versioned ``claude-haiku-4-5-
20251001`` + ``VALID_MODEL_IDS`` tuple; ``_lib``: short form
``claude-haiku-4-5`` + enum, no ``VALID_MODEL_IDS`` symbol). Codex
MCP cross-LLM gate review (PLAN-076 fork (f) call #1) flagged the
distinction as a path-correctness blocker.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[4]
_TIER = _REPO / ".claude" / "scripts" / "tier_policy_cli" / "_types.py"
_RUNNER = _REPO / ".claude" / "scripts" / "tournament" / "runner.py"
_REPORTER = _REPO / ".claude" / "scripts" / "tournament" / "reporter.py"


def _extract_valid_model_ids() -> set:
    """Read tier_policy_cli/_types.py and extract VALID_MODEL_IDS tuple.

    Uses regex to avoid executing the module (which depends on
    dataclasses registration in sys.modules that breaks under
    importlib.util loading from a one-shot spec).
    """
    import re
    text = _TIER.read_text(encoding="utf-8")
    m = re.search(
        r'VALID_MODEL_IDS[^=]*=\s*\(([^)]+)\)',
        text,
        flags=re.DOTALL,
    )
    if not m:
        return set()
    body = m.group(1)
    return {
        s.strip().strip('"').strip("'")
        for s in body.split(",")
        if s.strip()
    }


def _extract_runner_models() -> tuple:
    """Extract DEFAULT_MODELS + PRICING_USD_PER_M from runner.py."""
    import re
    text = _RUNNER.read_text(encoding="utf-8")
    dm = re.search(
        r'DEFAULT_MODELS\s*=\s*\(([^)]+)\)', text, flags=re.DOTALL
    )
    default_models = {
        s.strip().strip('"').strip("'")
        for s in (dm.group(1).split(",") if dm else [])
        if s.strip()
    }
    # Pricing keys
    pricing_keys: set = set()
    for mm in re.finditer(r'"(claude-[a-z0-9-]+)"\s*:\s*\{', text):
        pricing_keys.add(mm.group(1))
    return default_models, pricing_keys


class TestModelIdParity(unittest.TestCase):
    """Assert tournament model IDs match tier_policy VALID_MODEL_IDS."""

    def setUp(self) -> None:
        self.valid = _extract_valid_model_ids()
        self.default_models, self.pricing_keys = _extract_runner_models()

    def test_valid_model_ids_non_empty(self) -> None:
        self.assertGreater(
            len(self.valid), 0,
            "VALID_MODEL_IDS extraction returned empty set",
        )

    def test_default_models_all_in_valid_model_ids(self) -> None:
        for m in self.default_models:
            self.assertIn(
                m, self.valid,
                f"tournament DEFAULT_MODELS contains {m!r} which is not "
                f"in tier_policy VALID_MODEL_IDS={self.valid}",
            )

    def test_pricing_keys_all_in_valid_model_ids(self) -> None:
        for m in self.pricing_keys:
            self.assertIn(
                m, self.valid,
                f"tournament PRICING_USD_PER_M contains key {m!r} which "
                f"is not in tier_policy VALID_MODEL_IDS={self.valid}",
            )

    def test_reporter_constants_match_valid_model_ids(self) -> None:
        text = _REPORTER.read_text(encoding="utf-8")
        for literal in (
            "claude-opus-4-8",
            "claude-sonnet-4-6",
            "claude-haiku-4-5-20251001",
        ):
            self.assertIn(
                f'"{literal}"', text, f"missing literal {literal}"
            )
            self.assertIn(literal, self.valid)

    def test_short_haiku_id_absent_from_tournament(self) -> None:
        """The short ``claude-haiku-4-5`` (no suffix) must not appear in
        tournament source files. Guards against accidental regression."""
        import re
        pat = re.compile(r"claude-haiku-4-5(?!-)")
        for path in (_RUNNER, _REPORTER):
            text = path.read_text(encoding="utf-8")
            matches = pat.findall(text)
            self.assertEqual(
                matches, [],
                f"short Haiku ID found in {path.name}: {matches}",
            )


if __name__ == "__main__":
    unittest.main()
