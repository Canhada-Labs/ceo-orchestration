"""Tests for check-tla-schema-drift.py — PLAN-014 Phase B.7.

8 unit tests covering:
1. Plan-lifecycle state extraction from PLAN-SCHEMA.md
2. Debate semantics extraction from DEBATE-SCHEMA.md
3. CFG property parsing
4. Drift detection for plan-lifecycle
5. Drift detection for debate-convergence
6. Missing file handling
7. Extra properties warning
8. Real repo smoke test (exit 0)
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Set

# Import the script under test
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "check_tla_schema_drift",
    str(_SCRIPTS_DIR / "check-tla-schema-drift.py"),
)
drift_checker = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(drift_checker)  # type: ignore[union-attr]


class TestExtractPlanLifecycleStates(unittest.TestCase):
    """Test _extract_plan_lifecycle_states."""

    def test_extracts_all_five_states(self) -> None:
        text = """
### State definitions

| Status | Meaning | Next allowed transitions |
|---|---|---|
| `draft` | Plan is being written. | `reviewed`, `abandoned` |
| `reviewed` | Owner accepted. | `executing`, `abandoned` |
| `executing` | Work in progress. | `done`, `abandoned` |
| `done` | Complete. | (terminal) |
| `abandoned` | Superseded. | (terminal) |
"""
        states = drift_checker._extract_plan_lifecycle_states(text)
        self.assertEqual(
            states,
            {"draft", "reviewed", "executing", "done", "abandoned"}
        )

    def test_ignores_non_status_backticks(self) -> None:
        text = "| `foobar` | not a real status |"
        states = drift_checker._extract_plan_lifecycle_states(text)
        self.assertEqual(states, set())


class TestExtractDebateSemantics(unittest.TestCase):
    """Test _extract_debate_semantics."""

    def test_finds_all_semantics(self) -> None:
        text = """
## 12. N-round formal semantics
MAX_ROUNDS = 5
Jaccard similarity threshold 0.7
Red Team contingent archetype
redact_secrets() applied
"""
        semantics = drift_checker._extract_debate_semantics(text)
        self.assertTrue(semantics["max_rounds"])
        self.assertTrue(semantics["jaccard"])
        self.assertTrue(semantics["red_team"])
        self.assertTrue(semantics["redaction"])

    def test_missing_semantics(self) -> None:
        text = "Nothing relevant here."
        semantics = drift_checker._extract_debate_semantics(text)
        self.assertFalse(semantics["max_rounds"])
        self.assertFalse(semantics["jaccard"])


class TestParseCfgProperties(unittest.TestCase):
    """Test _parse_cfg_properties."""

    def test_parses_invariants_and_properties(self) -> None:
        cfg = """\\* TLC config
SPECIFICATION Spec

CONSTANTS
  MaxSteps = 10

INVARIANTS
  TypeOK
  S3_MonotonicTimestamps

PROPERTIES
  S1_NoSkip
  S2_AbandonmentDocumented
  Auth_OwnerApproval

CHECK_DEADLOCK FALSE
"""
        props = drift_checker._parse_cfg_properties(cfg)
        self.assertEqual(
            props,
            {
                "TypeOK", "S3_MonotonicTimestamps",
                "S1_NoSkip", "S2_AbandonmentDocumented",
                "Auth_OwnerApproval",
            }
        )

    def test_ignores_comments(self) -> None:
        cfg = """
INVARIANTS
  \\* This is a comment
  TypeOK
"""
        props = drift_checker._parse_cfg_properties(cfg)
        self.assertEqual(props, {"TypeOK"})


class TestPlanLifecycleDrift(unittest.TestCase):
    """Test check_plan_lifecycle_drift."""

    def test_no_drift_with_valid_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Create PLAN-SCHEMA.md
            schema_dir = root / ".claude" / "plans"
            schema_dir.mkdir(parents=True)
            (schema_dir / "PLAN-SCHEMA.md").write_text(
                "| `draft` | x | `reviewed`, `abandoned` |\n"
                "| `reviewed` | x | `executing`, `abandoned` |\n"
                "| `executing` | x | `done`, `abandoned` |\n"
                "| `done` | x | (terminal) |\n"
                "| `abandoned` | x | (terminal) |\n",
                encoding="utf-8"
            )
            # Create plan-lifecycle.cfg with all expected properties
            fv_dir = root / "docs" / "formal-verification"
            fv_dir.mkdir(parents=True)
            cfg = "SPECIFICATION Spec\n\nINVARIANTS\n"
            for p in sorted(drift_checker.EXPECTED_PLAN_LIFECYCLE_PROPERTIES):
                cfg += f"  {p}\n"
            cfg += "\nCHECK_DEADLOCK FALSE\n"
            (fv_dir / "plan-lifecycle.cfg").write_text(cfg, encoding="utf-8")

            errors = drift_checker.check_plan_lifecycle_drift(root)
            self.assertEqual(errors, [])

    def test_missing_property(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            schema_dir = root / ".claude" / "plans"
            schema_dir.mkdir(parents=True)
            (schema_dir / "PLAN-SCHEMA.md").write_text(
                "| `draft` | x |\n| `reviewed` | x |\n"
                "| `executing` | x |\n| `done` | x |\n"
                "| `abandoned` | x |\n",
                encoding="utf-8"
            )
            fv_dir = root / "docs" / "formal-verification"
            fv_dir.mkdir(parents=True)
            # Missing Auth_OwnerApproval
            cfg = "INVARIANTS\n  TypeOK\n  S1_NoSkip\n"
            (fv_dir / "plan-lifecycle.cfg").write_text(cfg, encoding="utf-8")

            errors = drift_checker.check_plan_lifecycle_drift(root)
            self.assertTrue(len(errors) > 0)
            self.assertTrue(
                any("missing" in e.lower() for e in errors)
            )


class TestDebateConvergenceDrift(unittest.TestCase):
    """Test check_debate_convergence_drift."""

    def test_missing_cfg_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            schema_dir = root / ".claude" / "plans"
            schema_dir.mkdir(parents=True)
            (schema_dir / "DEBATE-SCHEMA.md").write_text(
                "MAX_ROUNDS Jaccard Red Team redact",
                encoding="utf-8"
            )
            # No .cfg file
            errors = drift_checker.check_debate_convergence_drift(root)
            self.assertTrue(len(errors) > 0)
            self.assertTrue(any("not found" in e for e in errors))


class TestExtraProperties(unittest.TestCase):
    """Test that extra properties trigger a warning."""

    def test_extra_property_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            schema_dir = root / ".claude" / "plans"
            schema_dir.mkdir(parents=True)
            (schema_dir / "PLAN-SCHEMA.md").write_text(
                "| `draft` | x |\n| `reviewed` | x |\n"
                "| `executing` | x |\n| `done` | x |\n"
                "| `abandoned` | x |\n",
                encoding="utf-8"
            )
            fv_dir = root / "docs" / "formal-verification"
            fv_dir.mkdir(parents=True)
            cfg = "INVARIANTS\n"
            for p in sorted(drift_checker.EXPECTED_PLAN_LIFECYCLE_PROPERTIES):
                cfg += f"  {p}\n"
            cfg += "  ExtraUnknownProperty\n"
            (fv_dir / "plan-lifecycle.cfg").write_text(cfg, encoding="utf-8")

            errors = drift_checker.check_plan_lifecycle_drift(root)
            self.assertTrue(
                any("extra" in e.lower() for e in errors)
            )


class TestRealRepoSmokeTest(unittest.TestCase):
    """Smoke test against the real repo — should exit 0 with no drift."""

    def test_real_repo_no_drift(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        # Only run if we're in the real repo
        schema = repo_root / ".claude" / "plans" / "PLAN-SCHEMA.md"
        if not schema.is_file():
            self.skipTest("Not in real repo")

        plan_errors = drift_checker.check_plan_lifecycle_drift(repo_root)
        debate_errors = drift_checker.check_debate_convergence_drift(repo_root)

        all_errors = plan_errors + debate_errors
        self.assertEqual(
            all_errors, [],
            f"Drift detected in real repo: {all_errors}"
        )


if __name__ == "__main__":
    unittest.main()
