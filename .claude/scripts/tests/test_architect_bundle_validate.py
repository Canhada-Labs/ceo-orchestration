"""Tests for architect-bundle-validate.py.

Sprint 5 Phase 7 (ADR-010). Verifies the Architect bundle validator
catches common failure modes: missing files, low persona/pitfall/skill
count, real-name leaks, paid-tier marketing language.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SCRIPTS))

_SCRIPT = _SCRIPTS / "architect-bundle-validate.py"
_spec = importlib.util.spec_from_file_location("architect_bundle_validate", _SCRIPT)
abv = importlib.util.module_from_spec(_spec)
sys.modules["architect_bundle_validate"] = abv
_spec.loader.exec_module(abv)


class BundleValidatorTest(unittest.TestCase):

    def setUp(self):
        # Create a tempdir mimicking .claude/plans/PLAN-099/architect/round-1/
        self.tmp = Path(tempfile.mkdtemp(prefix="architect-bundle-test-"))
        self.bundle = self.tmp / ".claude" / "plans" / "PLAN-099" / "architect" / "round-1"
        self.bundle.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_valid_bundle(self):
        # Personas (5 sections) — no real names
        team = (
            "# Test Squad\n\n"
            "### 1. Composite Persona One — Lead\n\nBackground.\n\n"
            "### 2. Composite Persona Two — VETO\n\nBackground.\n\n"
            "### 3. Composite Persona Three — Engineer\n\nBackground.\n\n"
            "### 4. Composite Persona Four — Reviewer\n\nBackground.\n\n"
            "### 5. Composite Persona Five — QA\n\nBackground.\n"
        )
        (self.bundle / "team.draft.md").write_text(team, encoding="utf-8")

        # 10 pitfalls
        pitfalls = "pitfalls:\n"
        for i in range(10):
            pitfalls += f"  - id: TEST-{i:03d}\n"
            pitfalls += f"    rule: \"Rule {i}\"\n"
            pitfalls += "    whenToUse: \"x\"\n"
            pitfalls += "    agents: [Composite Persona One]\n"
        (self.bundle / "pitfalls.draft.yaml").write_text(pitfalls, encoding="utf-8")

        # 3 skills
        skills = (
            "## Proposed skills\n\n"
            "- `skill-one` — first skill\n"
            "- `skill-two` — second skill\n"
            "- `skill-three` — third skill\n"
        )
        (self.bundle / "skill-selection.draft.md").write_text(skills, encoding="utf-8")

        # Personas (alt prose form)
        (self.bundle / "personas.draft.md").write_text(
            "# Personas prose\n\n## Composite Persona One\n\n...\n",
            encoding="utf-8",
        )

        # Rationale
        (self.bundle / "rationale.md").write_text(
            "# Rationale\n\nA new domain warrants a squad because...\n",
            encoding="utf-8",
        )

    def test_valid_bundle_passes(self):
        self._write_valid_bundle()
        passed, reasons = abv.validate(self.bundle)
        self.assertTrue(passed, f"expected pass, got reasons: {reasons}")

    def test_missing_required_file_fails(self):
        self._write_valid_bundle()
        (self.bundle / "rationale.md").unlink()
        passed, reasons = abv.validate(self.bundle)
        self.assertFalse(passed)
        self.assertTrue(any("missing required files" in r for r in reasons))

    def test_too_few_personas_fails(self):
        self._write_valid_bundle()
        (self.bundle / "team.draft.md").write_text(
            "# squad\n\n### only one persona\n",
            encoding="utf-8",
        )
        passed, reasons = abv.validate(self.bundle)
        self.assertFalse(passed)
        self.assertTrue(any("personas" in r for r in reasons))

    def test_too_few_pitfalls_fails(self):
        self._write_valid_bundle()
        (self.bundle / "pitfalls.draft.yaml").write_text(
            "pitfalls:\n  - id: ONE\n    rule: a\n",
            encoding="utf-8",
        )
        passed, reasons = abv.validate(self.bundle)
        self.assertFalse(passed)
        self.assertTrue(any("pitfalls" in r for r in reasons))

    def test_too_few_skills_fails(self):
        self._write_valid_bundle()
        (self.bundle / "skill-selection.draft.md").write_text(
            "- `only-skill` — alone\n",
            encoding="utf-8",
        )
        passed, reasons = abv.validate(self.bundle)
        self.assertFalse(passed)
        self.assertTrue(any("skills" in r for r in reasons))

    def test_real_name_in_personas_fails(self):
        self._write_valid_bundle()
        # Inject a real name from the deny-list
        existing = (self.bundle / "team.draft.md").read_text(encoding="utf-8")
        (self.bundle / "team.draft.md").write_text(
            existing + "\n\nNote: contributed by Sam Altman.\n",
            encoding="utf-8",
        )
        passed, reasons = abv.validate(self.bundle)
        self.assertFalse(passed)
        self.assertTrue(any("real-person name" in r for r in reasons))

    def test_paid_tier_phrase_fails(self):
        self._write_valid_bundle()
        existing = (self.bundle / "rationale.md").read_text(encoding="utf-8")
        (self.bundle / "rationale.md").write_text(
            existing + "\n\nUpgrade to pro for full features.\n",
            encoding="utf-8",
        )
        passed, reasons = abv.validate(self.bundle)
        self.assertFalse(passed)
        self.assertTrue(any("paid-tier" in r for r in reasons))

    def test_bundle_dir_naming_required(self):
        # Use a tempdir that does NOT match the PLAN-NNN/architect/round-N pattern
        bad_dir = self.tmp / "bad" / "place"
        bad_dir.mkdir(parents=True, exist_ok=True)
        # Copy required files into bad_dir from a valid bundle
        self._write_valid_bundle()
        for f in abv._REQUIRED_FILES:
            shutil.copy(self.bundle / f, bad_dir / f)
        passed, reasons = abv.validate(bad_dir)
        self.assertFalse(passed)
        self.assertTrue(any("bundle dir does not match" in r for r in reasons))


if __name__ == "__main__":
    unittest.main()
