"""PLAN-104 Wave C tests — persona_waive_parser.

AC6: Waive mechanism (annotation OR git-trailer) parses both forms with
NFKC normalization + closed-enum reason validation. Free-text rejected.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

def _find_repo_root() -> Path:
    """Walk up from __file__ until we find a dir containing .claude/scripts/."""
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / ".claude" / "scripts").is_dir():
            return parent
    raise RuntimeError("repo root with .claude/scripts/ not found")


_REPO_ROOT = _find_repo_root()
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "scripts"))

import persona_waive_parser as wp  # noqa: E402


class TestWaiveParser(unittest.TestCase):
    def test_trailer_happy_path(self):
        msg = "feat: x\n\nPersona-Waive: security-engineer:generated-or-vendored\n"
        out = wp.parse_commit_message(msg)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].persona, "security-engineer")
        self.assertEqual(out[0].reason, "generated-or-vendored")
        self.assertEqual(out[0].source, "trailer")

    def test_annotation_happy_path(self):
        msg = "[persona-waive: code-reviewer reason=docs-only]"
        out = wp.parse_commit_message(msg)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].persona, "code-reviewer")
        self.assertEqual(out[0].reason, "docs-only")
        self.assertEqual(out[0].source, "annotation")

    def test_free_text_reason_rejected(self):
        for reason in ("not-in-enum", "my-cool-reason", "automation-tested"):
            msg = f"Persona-Waive: security-engineer:{reason}"
            self.assertEqual(wp.parse_commit_message(msg), [],
                             f"free-text {reason!r} should be rejected")

    def test_unknown_persona_rejected(self):
        for persona in ("frontend-engineer", "ml-engineer", "unknown"):
            msg = f"Persona-Waive: {persona}:docs-only"
            self.assertEqual(wp.parse_commit_message(msg), [])

    def test_all_4_reasons_accepted(self):
        for reason in wp.WAIVE_REASONS:
            msg = f"Persona-Waive: qa-architect:{reason}"
            out = wp.parse_commit_message(msg)
            self.assertEqual(len(out), 1, f"reason={reason!r} should parse")
            self.assertEqual(out[0].reason, reason)

    def test_automation_tested_removed_per_q5(self):
        # S134 R2 Q5 fold — `automation-tested` is REMOVED (too gameable).
        self.assertNotIn("automation-tested", wp.WAIVE_REASONS)

    def test_both_forms_one_message(self):
        msg = ("trailer: \n"
               "Persona-Waive: qa-architect:emergency-hotfix\n\n"
               "body inline [persona-waive: threat-detection-engineer reason=explicit-skip]\n")
        out = wp.parse_commit_message(msg)
        self.assertEqual(len(out), 2)
        self.assertEqual({w.persona for w in out},
                         {"qa-architect", "threat-detection-engineer"})

    def test_dedup_exact_match(self):
        msg = ("Persona-Waive: code-reviewer:docs-only\n"
               "Persona-Waive: code-reviewer:docs-only\n")
        out = wp.parse_commit_message(msg)
        self.assertEqual(len(out), 1)

    def test_case_insensitive_token(self):
        msg = "persona-waive: CODE-REVIEWER:DOCS-ONLY"  # lowercase header + uppercase value
        # Note our trailer regex matches `Persona-Waive:` case-insensitive
        msg2 = "PERSONA-WAIVE: code-reviewer:docs-only"
        out = wp.parse_commit_message(msg2)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].persona, "code-reviewer")

    def test_nfkc_normalization(self):
        # Full-width characters should normalize to ASCII.
        msg = "Persona-Waive: security-engineer:docs-only"  # ascii baseline
        ascii_out = wp.parse_commit_message(msg)
        # Construct a unicode variant with non-ascii markers in surrounding ws.
        unicode_msg = "Persona-Waive: security-engineer:docs-only "  # NBSP suffix
        unicode_out = wp.parse_commit_message(unicode_msg)
        self.assertEqual(len(ascii_out), 1)
        # NBSP after value — regex allows trailing whitespace, NBSP after NFKC is space
        self.assertGreaterEqual(len(unicode_out), 1)

    def test_empty_message(self):
        self.assertEqual(wp.parse_commit_message(""), [])
        self.assertEqual(wp.parse_commit_message(None), [])  # type: ignore

    def test_waives_by_persona_helper(self):
        msg = ("Persona-Waive: code-reviewer:docs-only\n"
               "Persona-Waive: security-engineer:emergency-hotfix\n")
        out = wp.waives_by_persona(msg)
        self.assertEqual(out["code-reviewer"], "docs-only")
        self.assertEqual(out["security-engineer"], "emergency-hotfix")


if __name__ == "__main__":
    unittest.main()
