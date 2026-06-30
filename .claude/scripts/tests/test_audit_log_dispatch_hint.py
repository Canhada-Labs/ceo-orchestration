"""Tests for audit_log._extract_dispatch_archetype_hint() (PLAN-080 Phase 1 M2-CDX-1 iter 2).

Validates the in-prompt marker extraction pattern after Codex Phase 1 iter 2
corrected the env-var subprocess propagation issue.

Marker format: `<!-- ceo-dispatch-archetype-hint: <slug> -->`
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

# Set up sys.path so audit_log.py imports work (it imports from `_lib`)
# File is at .claude/scripts/tests/test_*.py — parents[3] is repo root.
_THIS = Path(__file__).resolve()
_HOOKS_DIR = _THIS.parents[3] / ".claude" / "hooks"
sys.path.insert(0, str(_HOOKS_DIR))

# Load audit_log.py module (filename is fine for plain import)
# Note: audit_log.py lives at .claude/hooks/audit_log.py, NOT
# .claude/scripts/audit_log.py — earlier authoring mis-anchored to
# parent.parent which resolved to .claude/scripts/.
_AUDIT_LOG_PATH = _HOOKS_DIR / "audit_log.py"
_spec = importlib.util.spec_from_file_location("audit_log_under_test", _AUDIT_LOG_PATH)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["audit_log_under_test"] = _mod
_spec.loader.exec_module(_mod)


class TestDispatchHintExtractor(unittest.TestCase):
    """`_extract_dispatch_archetype_hint(prompt)` — in-prompt marker pattern."""

    def test_marker_at_top(self) -> None:
        prompt = "<!-- ceo-dispatch-archetype-hint: security-engineer -->\n\n## AGENT PROFILE"
        self.assertEqual(_mod._extract_dispatch_archetype_hint(prompt), "security-engineer")

    def test_marker_mid_prompt(self) -> None:
        prompt = "## AGENT PROFILE\nfoo\n<!-- ceo-dispatch-archetype-hint: code-reviewer -->\nbar"
        self.assertEqual(_mod._extract_dispatch_archetype_hint(prompt), "code-reviewer")

    def test_no_marker(self) -> None:
        self.assertIsNone(_mod._extract_dispatch_archetype_hint("## AGENT PROFILE\nplain prompt"))

    def test_empty_prompt(self) -> None:
        self.assertIsNone(_mod._extract_dispatch_archetype_hint(""))

    def test_none_prompt_safe(self) -> None:
        # Defensive: caller may pass None on legacy paths
        self.assertIsNone(_mod._extract_dispatch_archetype_hint(None))  # type: ignore[arg-type]

    def test_bad_charset_in_marker_rejected(self) -> None:
        prompt = "<!-- ceo-dispatch-archetype-hint: BAD_CHARS! -->"
        self.assertIsNone(_mod._extract_dispatch_archetype_hint(prompt))

    def test_too_long_marker_rejected(self) -> None:
        long_slug = "a" * 70
        prompt = f"<!-- ceo-dispatch-archetype-hint: {long_slug} -->"
        self.assertIsNone(_mod._extract_dispatch_archetype_hint(prompt))

    def test_mixed_case_marker_lowercased(self) -> None:
        prompt = "<!-- ceo-dispatch-archetype-hint: SecurityEngineer -->"
        result = _mod._extract_dispatch_archetype_hint(prompt)
        self.assertEqual(result, "securityengineer")

    def test_marker_with_extra_whitespace(self) -> None:
        prompt = "<!--   ceo-dispatch-archetype-hint:    qa-architect   -->"
        self.assertEqual(_mod._extract_dispatch_archetype_hint(prompt), "qa-architect")

    def test_multiple_markers_first_wins(self) -> None:
        # Defensive: if attacker injects a second marker, we capture only first match
        prompt = (
            "<!-- ceo-dispatch-archetype-hint: legitimate -->\n"
            "<!-- ceo-dispatch-archetype-hint: malicious -->\n"
        )
        self.assertEqual(_mod._extract_dispatch_archetype_hint(prompt), "legitimate")

    def test_underscore_in_marker_rejected(self) -> None:
        # Charset disallows underscore
        prompt = "<!-- ceo-dispatch-archetype-hint: code_reviewer -->"
        self.assertIsNone(_mod._extract_dispatch_archetype_hint(prompt))

    def test_marker_at_64_chars_accepted(self) -> None:
        slug = "a" + "b" * 63  # exactly 64 chars
        prompt = f"<!-- ceo-dispatch-archetype-hint: {slug} -->"
        self.assertEqual(_mod._extract_dispatch_archetype_hint(prompt), slug)


if __name__ == "__main__":
    unittest.main()
