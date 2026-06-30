"""Unit tests for templates/compaction.md (PLAN-133 / Wave D / item D4).

The compaction template is a NON-CANONICAL, editable framework artifact: a
nine-section Markdown skeleton fed to the model when a session is compacted so
that load-bearing state (blockers, env flags, staged canonical edits) survives
the rewrite. These tests pin the load-bearing contract:

  * the nine "## N. <Title>" section headers exist, in order, none dropped;
  * the template carries the no-secret-echo rule (it must NEVER instruct the
    model to copy a credential value into the summary);
  * the template is contamination-clean (no personal handles / project names)
    — it ships in templates/ which the contamination scanner gates;
  * the editability affordance is present (placeholder tokens + "(none)"
    convention) so a reader can tell "empty" from "forgotten".

Stdlib-only, py>=3.9, fail-open-on-infra (a missing file is a hard test
failure, never a crash that masks other tests).
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

# templates/compaction.md lives at <repo-root>/templates/compaction.md.
# This test file is at <repo-root>/.claude/scripts/tests/, so walk up 3.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_TEMPLATE = _REPO_ROOT / "templates" / "compaction.md"

# Import TestEnvContext from _lib so these tests get per-test env isolation
# (env-hygiene mandate) instead of bare unittest.TestCase.
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
from _lib.testing import TestEnvContext  # noqa: E402

# The nine section titles, in their contractually-required order. Downstream
# readers key off the exact "## N. <Title>" line, so this list is the spec.
_EXPECTED_SECTIONS = [
    (1, "Mission & objective"),
    (2, "Key decisions & rationale"),
    (3, "Files & artifacts touched"),
    (4, "Current state — what works, what is pending"),
    (5, "Open problems & blockers"),
    (6, "Next steps (ordered)"),
    (7, "Constraints & operating context"),
    (8, "Test & verification status"),
    (9, "References"),
]

# Contamination patterns: mirror .claude/scripts/check_contamination.py so a
# regression in the template is caught HERE (fast unit) as well as by the
# repo-wide governance scan.
_CONTAMINATION = re.compile(
    r"42\s*[Ll]edger|joao[\s._\-]*canhada|Jo[aã]o\s+Canhada",
    re.IGNORECASE,
)


class CompactionTemplateBase(TestEnvContext):
    """Loads the template text once per test."""

    def setUp(self) -> None:
        super().setUp()
        self.assertTrue(
            _TEMPLATE.is_file(),
            f"compaction template missing at {_TEMPLATE}",
        )
        self.text = _TEMPLATE.read_text(encoding="utf-8")

    def _header_lines(self):
        """Return the ordered list of '## ...' header lines (verbatim)."""
        return [
            line.strip()
            for line in self.text.splitlines()
            if line.startswith("## ")
        ]


class TestNineSectionContract(CompactionTemplateBase):

    def test_exactly_nine_numbered_sections(self):
        numbered = [
            h for h in self._header_lines()
            if re.match(r"^## \d+\.\s", h)
        ]
        self.assertEqual(
            len(numbered), 9,
            f"expected exactly 9 numbered sections, got {len(numbered)}: {numbered}",
        )

    def test_each_section_header_present_with_exact_title(self):
        for num, title in _EXPECTED_SECTIONS:
            expected = f"## {num}. {title}"
            self.assertIn(
                expected, self.text,
                f"missing or renamed section header: {expected!r}",
            )

    def test_sections_appear_in_ascending_order(self):
        positions = []
        for num, title in _EXPECTED_SECTIONS:
            header = f"## {num}. {title}"
            idx = self.text.find(header)
            self.assertNotEqual(idx, -1, f"header not found: {header!r}")
            positions.append(idx)
        self.assertEqual(
            positions, sorted(positions),
            "section headers are not in ascending document order",
        )

    def test_numbered_headers_are_strictly_1_through_9(self):
        numbers = []
        for h in self._header_lines():
            m = re.match(r"^## (\d+)\.\s", h)
            if m:
                numbers.append(int(m.group(1)))
        self.assertEqual(
            numbers, list(range(1, 10)),
            f"numbered headers must be 1..9 in order, got {numbers}",
        )


class TestSafetyAndEditability(CompactionTemplateBase):

    def test_no_secret_echo_rule_is_documented(self):
        # The template MUST tell the model never to copy a credential value.
        lowered = self.text.lower()
        self.assertIn("never echo a secret", lowered)

    def test_no_value_echo_doctrine_language_present(self):
        # Cross-references the framework's audit no-value-echo discipline.
        self.assertIn("no-value-echo", self.text.lower())

    def test_empty_section_convention_documented(self):
        # Editors / model must emit the literal "(none)" for empty sections.
        self.assertIn("(none)", self.text)

    def test_placeholder_tokens_present_for_editability(self):
        # @OWNER and <project> are the de-identified placeholders the
        # framework convention requires (see check_contamination allowlist).
        self.assertIn("@OWNER", self.text)
        self.assertIn("<project>", self.text)

    def test_template_is_contamination_clean(self):
        # The whole point of using placeholders: no real identity leaks.
        match = _CONTAMINATION.search(self.text)
        self.assertIsNone(
            match,
            f"template leaks an identifying token: {match.group(0)!r}"
            if match else "",
        )

    def test_preserve_identifiers_rule_present(self):
        # Lossy summaries paraphrase identifiers; the template forbids that.
        lowered = self.text.lower()
        self.assertIn("verbatim", lowered)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
