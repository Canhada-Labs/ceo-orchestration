"""fu144 regression tests for root CLAUDE.md exclusion controls."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import claude_md_excludes as excludes  # noqa: E402
from _lib import effective_config as ec  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


class TestClaudeMdExcludesFu144(TestEnvContext):
    @staticmethod
    def _resolved(root: Path, layers: list) -> dict:
        return {"project_dir": str(root), "layers": layers}

    def test_fu144_staged_pattern_is_permitted_outside_staged_checkout(self) -> None:
        pattern = "**/.claude/plans/**/staged*/**/CLAUDE.md"
        with patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(self.project_dir)}):
            self.assertFalse(excludes.root_claude_md_excluded(
                [pattern], self.project_dir
            ))
            findings = ec.classify_tampering(self._resolved(self.project_dir, [{
                "name": "project", "data": {"claudeMdExcludes": [pattern]},
            }]), {})
        self.assertEqual(findings, [])

    def test_fu144_glob_matching_root_is_flagged_in_every_settings_layer(self) -> None:
        for layer_name in ("user", "project", "local", "managed"):
            with self.subTest(layer=layer_name), patch.dict(
                os.environ, {"CLAUDE_PROJECT_DIR": str(self.project_dir)}
            ):
                findings = ec.classify_tampering(self._resolved(self.project_dir, [{
                    "name": layer_name,
                    "data": {"claudeMdExcludes": ["**/CLAUDE.md"]},
                }]), {})
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0]["class"], ec.TAMPER_CLAUDE_MD_EXCLUDES_ROOT)
            self.assertEqual(findings[0]["layer"], layer_name)

    def test_fu144_staged_pattern_flags_a_nested_checkout_root(self) -> None:
        nested_root = self.project_dir / ".claude/plans/PLAN-194/staged-checkout"
        nested_root.mkdir(parents=True)
        pattern = "**/.claude/plans/**/staged*/**/CLAUDE.md"
        self.assertTrue(excludes.root_claude_md_excluded([pattern], nested_root))
        findings = ec.classify_tampering(self._resolved(nested_root, [{
            "name": "local", "data": {"claudeMdExcludes": [pattern]},
        }]), {})
        self.assertEqual(findings[0]["class"], ec.TAMPER_CLAUDE_MD_EXCLUDES_ROOT)

    def test_fu144_staged_pattern_matches_root_directly_under_staged_dir(self) -> None:
        nested_root = self.project_dir / ".claude/plans/PLAN-194/staged-checkout"
        nested_root.mkdir(parents=True)
        self.assertTrue(excludes.root_claude_md_excluded(
            ["**/.claude/plans/**/staged*/CLAUDE.md"], nested_root
        ))

    def test_fu144_relative_root_name_does_not_match_but_absolute_name_does(self) -> None:
        root = (self.project_dir / "CLAUDE.md").resolve()
        self.assertFalse(excludes.root_claude_md_excluded(["CLAUDE.md"], self.project_dir))
        self.assertTrue(excludes.root_claude_md_excluded([str(root)], self.project_dir))

    def test_fu144_loaded_root_requires_complete_observed_path_set(self) -> None:
        root = (self.project_dir / "CLAUDE.md").resolve()
        other = (self.project_dir / ".claude/instructions.md").resolve()
        self.assertEqual(
            excludes.root_instruction_load_state([other], self.project_dir),
            excludes.LOAD_STATE_ABSENT,
        )
        self.assertEqual(
            excludes.root_instruction_load_state([other, root], self.project_dir),
            excludes.LOAD_STATE_LOADED,
        )
        self.assertEqual(
            excludes.root_instruction_load_state([root, 7], self.project_dir),
            excludes.LOAD_STATE_UNOBSERVABLE,
        )
        self.assertEqual(
            excludes.root_instruction_load_state(iter([root]), self.project_dir),
            excludes.LOAD_STATE_UNOBSERVABLE,
        )
        self.assertEqual(
            excludes.root_instruction_load_state(None, self.project_dir),
            excludes.LOAD_STATE_UNOBSERVABLE,
        )
        self.assertEqual(
            excludes.root_instruction_load_state(["CLAUDE.md"], self.project_dir),
            excludes.LOAD_STATE_UNOBSERVABLE,
        )
