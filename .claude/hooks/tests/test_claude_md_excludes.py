"""fu144 regression tests for root CLAUDE.md exclusion controls."""

from __future__ import annotations

import contextlib
import io
import os
import sys
import json
from pathlib import Path
from unittest.mock import patch

_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import claude_md_excludes as excludes  # noqa: E402
from _lib import effective_config as ec  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402
import check_harness_config as harness  # noqa: E402


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

    def test_fu144_shipped_setting_excludes_staged_contract_not_root(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        settings = json.loads((repo_root / ".claude/settings.json").read_text())
        patterns = settings["claudeMdExcludes"]
        staged = self.project_dir / ".claude/plans/PLAN-194/staged-contract"
        staged.mkdir(parents=True)
        self.assertFalse(excludes.root_claude_md_excluded(patterns, repo_root))
        self.assertTrue(excludes.root_claude_md_excluded(patterns, staged))

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


class TestRootInstructionRuntimeWiring(TestEnvContext):
    """The production CLI reports only what a complete observed list proves."""

    def _report(self, evidence=None):
        args = [
            "--static", "--no-exec-bit", "--repo-root", str(self.project_dir),
            "--settings", str(self.project_dir / "absent-settings.json"),
        ]
        if evidence is not None:
            args.extend(("--instruction-load-evidence", str(evidence)))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = harness.main(args)
        assert rc == 0
        return out.getvalue()

    def _snapshot(self, name, value):
        path = self.project_dir / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_runtime_report_loaded_from_complete_snapshot(self):
        root = str((self.project_dir / "CLAUDE.md").resolve())
        evidence = self._snapshot("loaded.json", {
            "complete": True, "loaded_instruction_paths": [root],
        })
        report = self._report(evidence)
        self.assertIn("[WARN] root_instruction_load @ runtime", report)
        self.assertIn("snapshot reports root_loaded (operator-supplied snapshot; completeness unverified)", report)

    def test_runtime_report_absent_from_complete_snapshot(self):
        other = str((self.project_dir / "other.md").resolve())
        evidence = self._snapshot("absent.json", {
            "complete": True, "loaded_instruction_paths": [other],
        })
        report = self._report(evidence)
        self.assertIn("snapshot reports root_absent (operator-supplied snapshot; completeness unverified)", report)

    def test_runtime_rejects_partial_snapshot_as_proof(self):
        root = str((self.project_dir / "CLAUDE.md").resolve())
        evidence = self._snapshot("partial.json", {
            "complete": False, "loaded_instruction_paths": [root],
        })
        report = self._report(evidence)
        self.assertIn("root_load_unobservable (incomplete or malformed path list)", report)
        self.assertNotIn("root_loaded", report)

    def test_runtime_rejects_invalid_entries_as_proof(self):
        root = str((self.project_dir / "CLAUDE.md").resolve())
        evidence = self._snapshot("invalid.json", {
            "complete": True, "loaded_instruction_paths": [root, "CLAUDE.md"],
        })
        report = self._report(evidence)
        self.assertIn("root_load_unobservable (operator-supplied snapshot; completeness unverified)", report)
        self.assertNotIn("root_loaded", report)

    def test_runtime_without_observed_source_is_unobservable(self):
        report = self._report()
        self.assertIn("root_load_unobservable (no complete observed path list)", report)
        self.assertNotIn("root_absent", report)
        self.assertNotIn("root_loaded", report)

    def test_runtime_malformed_json_is_unobservable(self):
        evidence = self.project_dir / "broken.json"
        evidence.write_text("{invalid", encoding="utf-8")
        report = self._report(evidence)
        self.assertIn("root_load_unobservable (unreadable or invalid path list)", report)
