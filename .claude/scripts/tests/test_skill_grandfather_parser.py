"""Tests for .claude/scripts/skill_grandfather_parser.py

PLAN-051 Phase 1 A1 (Opção 2) — validates the grandfather parser
schema + the canonical grandfather.yaml file contents.

Run standalone:
  python3 -m pytest .claude/scripts/tests/test_skill_grandfather_parser.py -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

# Resolve relative to repo root; this test file lives in
# .claude/scripts/tests/, parser lives in .claude/scripts/.
_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent
sys.path.insert(0, str(_SCRIPTS))

import skill_grandfather_parser as sgp  # noqa: E402

_REPO_ROOT = _SCRIPTS.parent.parent
_CANONICAL_YAML = _REPO_ROOT / ".claude" / "skill-governance-grandfather.yaml"


class TestCanonicalRegistry(unittest.TestCase):
    """Validates the canonical grandfather.yaml file ships valid."""

    def test_canonical_file_exists(self):
        self.assertTrue(
            _CANONICAL_YAML.exists(),
            f"canonical grandfather file missing: {_CANONICAL_YAML}",
        )

    def test_canonical_parses_without_error(self):
        entries = sgp.parse_grandfather_file(_CANONICAL_YAML)
        self.assertIsInstance(entries, list)
        # Phase 1 A1 registry ships with 5 grandfathered skills.
        self.assertEqual(len(entries), 5, "expected 5 grandfathered entries")

    def test_canonical_validates(self):
        entries = sgp.parse_grandfather_file(_CANONICAL_YAML)
        errors = sgp.validate_registry(entries)
        self.assertEqual(
            errors,
            [],
            f"canonical registry has validation errors: {errors}",
        )

    def test_canonical_contains_expected_skills(self):
        expected = {
            "pre-plan-brainstorm",
            "terse-mode",
            "advanced-evaluation",
            "agent-evaluation",
            "agentic-actions-auditor",
        }
        entries = sgp.parse_grandfather_file(_CANONICAL_YAML)
        actual = {e.skill for e in entries}
        self.assertEqual(actual, expected)

    def test_canonical_reason_categories(self):
        entries = sgp.parse_grandfather_file(_CANONICAL_YAML)
        for e in entries:
            self.assertIn(
                e.reason,
                sgp.VALID_REASONS,
                f"skill {e.skill} has invalid reason {e.reason}",
            )

    def test_canonical_under_cap(self):
        entries = sgp.parse_grandfather_file(_CANONICAL_YAML)
        self.assertLessEqual(len(entries), sgp.MAX_GRANDFATHERED_ENTRIES)

    def test_is_grandfathered_true_for_registered(self):
        self.assertTrue(
            sgp.is_grandfathered("pre-plan-brainstorm", _CANONICAL_YAML)
        )
        self.assertTrue(
            sgp.is_grandfathered("terse-mode", _CANONICAL_YAML)
        )

    def test_is_grandfathered_false_for_unregistered(self):
        self.assertFalse(
            sgp.is_grandfathered(
                "architecture-decisions", _CANONICAL_YAML
            )
        )
        self.assertFalse(
            sgp.is_grandfathered("nonexistent-skill", _CANONICAL_YAML)
        )

    def test_get_reason_returns_category(self):
        reason = sgp.get_reason(
            "pre-plan-brainstorm", _CANONICAL_YAML
        )
        self.assertEqual(reason, "meta-skill-adjacent")

        reason = sgp.get_reason("terse-mode", _CANONICAL_YAML)
        self.assertEqual(reason, "slash-command-only")

        reason = sgp.get_reason(
            "advanced-evaluation", _CANONICAL_YAML
        )
        self.assertEqual(reason, "community-import")

    def test_get_reason_none_for_unknown(self):
        self.assertIsNone(
            sgp.get_reason("nonexistent-skill", _CANONICAL_YAML)
        )


class TestParserRobustness(unittest.TestCase):
    """Parser-level tests using synthetic fixtures (no canonical file)."""

    def _write_fixture(self, content: str) -> Path:
        """Write fixture to a temp file; caller owns cleanup."""
        tf = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        )
        tf.write(content)
        tf.close()
        return Path(tf.name)

    def test_empty_registry_is_valid(self):
        path = self._write_fixture("grandfathered:\n")
        try:
            entries = sgp.parse_grandfather_file(path)
            self.assertEqual(entries, [])
            self.assertEqual(sgp.validate_registry(entries), [])
        finally:
            path.unlink()

    def test_comments_ignored(self):
        content = """
# top comment
grandfathered:
  # inline comment
  - skill: foo-skill
    reason: meta-skill-adjacent
    justification: "test"
  # trailing comment
"""
        path = self._write_fixture(content)
        try:
            entries = sgp.parse_grandfather_file(path)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0].skill, "foo-skill")
        finally:
            path.unlink()

    def test_unknown_reason_fails_validation(self):
        content = """
grandfathered:
  - skill: foo
    reason: unknown-category
    justification: "test"
"""
        path = self._write_fixture(content)
        try:
            entries = sgp.parse_grandfather_file(path)
            errors = sgp.validate_registry(entries)
            self.assertTrue(any("unknown reason" in e for e in errors))
        finally:
            path.unlink()

    def test_duplicate_skill_fails_validation(self):
        content = """
grandfathered:
  - skill: foo
    reason: meta-skill-adjacent
    justification: "first"
  - skill: foo
    reason: slash-command-only
    justification: "duplicate"
"""
        path = self._write_fixture(content)
        try:
            entries = sgp.parse_grandfather_file(path)
            errors = sgp.validate_registry(entries)
            self.assertTrue(any("duplicate skill" in e for e in errors))
        finally:
            path.unlink()

    def test_empty_justification_fails_validation(self):
        content = """
grandfathered:
  - skill: foo
    reason: meta-skill-adjacent
    justification: ""
"""
        path = self._write_fixture(content)
        try:
            entries = sgp.parse_grandfather_file(path)
            errors = sgp.validate_registry(entries)
            self.assertTrue(
                any("empty justification" in e for e in errors)
            )
        finally:
            path.unlink()

    def test_cap_exceeded_fails_validation(self):
        lines = ["grandfathered:"]
        for i in range(sgp.MAX_GRANDFATHERED_ENTRIES + 1):
            lines.append(f"  - skill: skill-{i}")
            lines.append(f"    reason: meta-skill-adjacent")
            lines.append(f'    justification: "entry {i}"')
        path = self._write_fixture("\n".join(lines))
        try:
            entries = sgp.parse_grandfather_file(path)
            errors = sgp.validate_registry(entries)
            self.assertTrue(any("cap is" in e for e in errors))
        finally:
            path.unlink()

    def test_incomplete_entry_raises(self):
        content = """
grandfathered:
  - skill: foo
    reason: meta-skill-adjacent
  - skill: bar
    reason: slash-command-only
    justification: "ok"
"""
        path = self._write_fixture(content)
        try:
            with self.assertRaises(ValueError):
                sgp.parse_grandfather_file(path)
        finally:
            path.unlink()

    def test_unrecognized_line_raises(self):
        content = """
grandfathered:
  - skill: foo
    reason: meta-skill-adjacent
    justification: "ok"
    unknown_field: "bad"
"""
        path = self._write_fixture(content)
        try:
            with self.assertRaises(ValueError):
                sgp.parse_grandfather_file(path)
        finally:
            path.unlink()

    def test_file_not_found_raises(self):
        with self.assertRaises(FileNotFoundError):
            sgp.parse_grandfather_file(
                Path("/nonexistent/grandfather.yaml")
            )

    def test_list_grandfathered_returns_slugs(self):
        skills = sgp.list_grandfathered_skills(_CANONICAL_YAML)
        self.assertIsInstance(skills, list)
        self.assertIn("pre-plan-brainstorm", skills)

    def test_entry_to_dict(self):
        entry = sgp.GrandfatherEntry("foo", "meta-skill-adjacent", "test")
        d = entry.to_dict()
        self.assertEqual(
            d,
            {
                "skill": "foo",
                "reason": "meta-skill-adjacent",
                "justification": "test",
            },
        )


class TestCLIOutput(unittest.TestCase):
    """Tests the CLI mode used by validate-governance.sh."""

    def test_cli_emits_skill_reason_pairs(self):
        """Replicates shell consumer behavior."""
        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                str(_SCRIPTS / "skill_grandfather_parser.py"),
                str(_CANONICAL_YAML),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        lines = result.stdout.strip().split("\n")
        self.assertEqual(len(lines), 5)
        for line in lines:
            self.assertIn(":", line)
            skill, reason = line.split(":", 1)
            self.assertIn(reason, sgp.VALID_REASONS)

    def test_cli_missing_file_exits_2(self):
        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                str(_SCRIPTS / "skill_grandfather_parser.py"),
                "/nonexistent/file.yaml",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
