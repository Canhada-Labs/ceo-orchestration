"""test_ceo_boot_plan_082.py — PLAN-082 Codex Items A+D regression tests.

Codex MCP ThreadID `019e175b…` verdict:
- Item A: `check_governance_validate` must dispatch
  `validate-governance.sh --fast --json` (delegating to
  `validate_governance_fast.py`), parse JSON, use `rc != 0` as red truth.
- Item D: `hook_test_baseline` dropped from Tier-S; replaced with
  `hook_live_smoke` — live hook smoke (settings.json parse + file
  existence + py_compile) instead of cache-file dependency.

Tests guard against regression of:
- The 6th-option Codex catch: `stdout.count("ERROR")` underclassified
  failures (script emits `FAIL:` in some sections without literal "ERROR").
  This file ensures the new code never reintroduces the substring heuristic.
- Cache dependency reintroduction: `hook_live_smoke` must not require
  `.claude/cache/hook-tests.json` to exist.

Stdlib only.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_ceo_boot = _load_module("ceo_boot_p82", REPO_ROOT / ".claude" / "scripts" / "ceo-boot.py")
_fast = _load_module(
    "validate_governance_fast_p82",
    REPO_ROOT / ".claude" / "scripts" / "validate_governance_fast.py",
)


class TestFastValidatorContract(TestEnvContext):
    """Codex Item A: --fast --json profile contract."""

    def test_fast_profile_returns_keys(self):
        result = _fast.run(REPO_ROOT)
        for key in ("profile", "rc", "duration_ms", "errors", "warnings", "checks_run"):
            self.assertIn(key, result)

    def test_fast_profile_label(self):
        result = _fast.run(REPO_ROOT)
        self.assertEqual(result["profile"], "fast")

    def test_fast_profile_under_2s_budget(self):
        result = _fast.run(REPO_ROOT)
        self.assertLess(result["duration_ms"], 2000)

    def test_fast_profile_runs_all_checks(self):
        result = _fast.run(REPO_ROOT)
        expected = {
            "settings_json", "required_files", "active_hooks", "python_shim",
            "plan_schema",
            # PLAN-112-FOLLOWUP-plan-093-followup-collision W3 (S155) —
            # frontmatter id-uniqueness guard.
            "plan_id_uniqueness",
            # S213 — frontmatter status: presence + legality guard (mirrors
            # validate-governance.sh §1 item 4). Closes the PLAN-128-executing
            # body-only-status blind-spot.
            "plan_frontmatter_status",
            # S213 — frontmatter id: presence guard (mirrors validate-
            # governance.sh §1 item 5). Closes the id-less-plan gap that the
            # fail-soft uniqueness check left open.
            "plan_id_presence",
            # PLAN-134 W1 (S228) — PLAN-SCHEMA §13 Check:-per-execution-unit
            # gate (doctrine V0). Prospective: created >= 2026-06-12 only.
            "plan_vcheck_declarations",
        }
        self.assertEqual(set(result["checks_run"]), expected)

    def test_fast_profile_rc_matches_errors(self):
        result = _fast.run(REPO_ROOT)
        if result["errors"]:
            self.assertEqual(result["rc"], 1)
        else:
            self.assertEqual(result["rc"], 0)

    def test_fast_profile_via_bash_wrapper(self):
        proc = subprocess.run(
            ["bash", str(REPO_ROOT / ".claude" / "scripts" / "validate-governance.sh"),
             "--fast", "--json"],
            capture_output=True, text=True, timeout=5.0, cwd=str(REPO_ROOT),
        )
        # Wrapper must exec the Python helper; stdout = single JSON line.
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["profile"], "fast")
        # rc == returncode (Codex 6th-option truth).
        self.assertEqual(payload["rc"], proc.returncode)

    def test_fast_extract_handles_shim_invocation(self):
        """Settings.json hooks use `_python-hook.sh <basename>.py` patterns."""
        fake_settings = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {"command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_foo.py"},
                        ],
                    }
                ]
            }
        }
        paths = _fast._extract_hook_paths(fake_settings)
        self.assertEqual(paths, [".claude/hooks/check_foo.py"])

    def test_fast_extract_handles_direct_path(self):
        fake_settings = {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {"command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/check_bar.py\""},
                        ],
                    }
                ]
            }
        }
        paths = _fast._extract_hook_paths(fake_settings)
        self.assertEqual(paths, [".claude/hooks/check_bar.py"])

    def test_fast_extract_deduplicates(self):
        fake_settings = {
            "hooks": {
                "A": [{"hooks": [{"command": "bash _python-hook.sh check_x.py"}]}],
                "B": [{"hooks": [{"command": "bash _python-hook.sh check_x.py"}]}],
            }
        }
        paths = _fast._extract_hook_paths(fake_settings)
        self.assertEqual(paths, [".claude/hooks/check_x.py"])

    def test_fast_extract_strips_env_var_prefix(self):
        self.assertEqual(
            _fast._normalize_hook_ref("${CLAUDE_PROJECT_DIR}/.claude/hooks/x.py"),
            ".claude/hooks/x.py",
        )
        self.assertEqual(
            _fast._normalize_hook_ref("$CLAUDE_PROJECT_DIR/.claude/hooks/y.py"),
            ".claude/hooks/y.py",
        )


class TestCheckGovernanceValidate(TestEnvContext):
    """Codex Item A: ceo-boot check uses fast --json + rc!=0 truth."""

    def test_real_check_returns_green_on_clean_repo(self):
        status, summary, detail = _ceo_boot.check_governance_validate()
        # On clean repo, fast profile passes.
        self.assertEqual(status, "green")
        self.assertEqual(detail["rc"], 0)
        self.assertEqual(detail["profile"], "fast")

    def test_check_summary_says_fast(self):
        status, summary, detail = _ceo_boot.check_governance_validate()
        self.assertIn("fast", summary.lower())

    def test_check_detail_includes_profile_key(self):
        status, summary, detail = _ceo_boot.check_governance_validate()
        self.assertEqual(detail.get("profile"), "fast")

    def test_no_stdout_error_count_heuristic(self):
        """Codex 6th-option guard: function must use rc != 0 as truth, NOT
        substring count of 'ERROR' in stdout. The docstring may mention the
        old heuristic to explain why it was removed; we scan only the
        executable body (stripped of triple-quoted strings)."""
        import ast
        src = (REPO_ROOT / ".claude" / "scripts" / "ceo-boot.py").read_text()
        tree = ast.parse(src)
        target = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "check_governance_validate":
                target = node
                break
        self.assertIsNotNone(target, "check_governance_validate not found in AST")
        # Drop the leading docstring node, then unparse the remaining body.
        body = list(target.body)
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            body = body[1:]
        synth = ast.Module(body=body, type_ignores=[])
        body_src = ast.unparse(synth)
        self.assertNotIn("stdout.count", body_src,
                         "Codex 6th-option regression — substring heuristic must stay removed")
        self.assertNotIn("err_count", body_src,
                         "Codex 6th-option regression — old err_count variable returned")


class TestCheckHookLiveSmoke(TestEnvContext):
    """Codex Item D: hook_live_smoke replaces hook_test_baseline."""

    def test_returns_green_on_clean_repo(self):
        status, summary, detail = _ceo_boot.check_hook_live_smoke()
        self.assertEqual(status, "green")
        self.assertGreater(detail["checked"], 0)
        self.assertGreaterEqual(detail["total"], detail["checked"])

    def test_summary_mentions_hook_count(self):
        status, summary, detail = _ceo_boot.check_hook_live_smoke()
        self.assertIn("smoke-pass", summary)

    def test_does_not_require_cache_file(self):
        """Cache file may be entirely absent — check still works (Codex DROP).

        Regression guard: previous impl read `.claude/cache/hook-tests.json`
        and went yellow if missing. New impl never touches that path.
        """
        # Just call the check — it should not raise + should not return yellow
        # due to cache-missing. Clean repo has no cache file (verified).
        cache = REPO_ROOT / ".claude" / "cache" / "hook-tests.json"
        self.assertFalse(cache.exists(), "Test precondition: cache file absent")
        status, summary, detail = _ceo_boot.check_hook_live_smoke()
        self.assertNotEqual(status, "yellow",
                            f"hook_live_smoke must not yellow on missing cache; got {status}: {summary}")

    def test_backward_compat_alias(self):
        # Old function name preserved as alias for any external test imports.
        self.assertIs(_ceo_boot.check_hook_test_baseline, _ceo_boot.check_hook_live_smoke)

    def test_registry_uses_new_name(self):
        names = [name for name, _ in _ceo_boot.TIER_S_CHECKS]
        self.assertIn("hook_live_smoke", names)
        self.assertNotIn("hook_test_baseline", names)


class TestPlanSchemaCheck(TestEnvContext):
    """Verify fast profile catches PLAN-SCHEMA §1 violations as it should."""

    def test_known_governance_files_allowed(self):
        # Build a synthetic plan dir and verify the fast profile accepts
        # the known governance filenames.
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".claude" / "plans").mkdir(parents=True)
            for f in ("README.md", "PLAN-SCHEMA.md", "AUDIT-LOG-SCHEMA.md",
                     "DEBATE-SCHEMA.md", "PLAN-001-foo.md", "PLAN-099-bar-baz.md"):
                (tdp / ".claude" / "plans" / f).write_text("stub")
            (tdp / ".claude" / "plans" / "PLAN-042").mkdir()
            (tdp / ".claude" / "plans" / "examples").mkdir()
            (tdp / ".claude" / "plans" / "archive").mkdir()
            errors: list = []
            _fast._check_plan_schema(tdp, errors)
            self.assertEqual(errors, [])

    def test_invalid_subdir_caught(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".claude" / "plans" / "RANDOM").mkdir(parents=True)
            errors: list = []
            _fast._check_plan_schema(tdp, errors)
            self.assertTrue(
                any("plan_schema_subdir:RANDOM" in e for e in errors),
                f"Expected subdir error; got {errors}"
            )

    def test_invalid_filename_caught(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".claude" / "plans").mkdir(parents=True)
            (tdp / ".claude" / "plans" / "not-a-plan.md").write_text("x")
            errors: list = []
            _fast._check_plan_schema(tdp, errors)
            self.assertTrue(
                any("plan_schema_filename:not-a-plan.md" in e for e in errors),
                f"Expected filename error; got {errors}"
            )

    def test_sprint_filename_accepted(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".claude" / "plans").mkdir(parents=True)
            (tdp / ".claude" / "plans" / "SPRINT-30-ROADMAP.md").write_text("x")
            errors: list = []
            _fast._check_plan_schema(tdp, errors)
            self.assertEqual(errors, [])

    # PLAN-SCHEMA.md §1.4 — followup plan naming, mirrors ADR-NNN-AMEND-M.
    def test_followup_filename_accepted(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".claude" / "plans").mkdir(parents=True)
            (tdp / ".claude" / "plans" /
             "PLAN-094-FOLLOWUP-residual-perf-burndown.md").write_text("x")
            errors: list = []
            _fast._check_plan_schema(tdp, errors)
            self.assertEqual(errors, [], f"FOLLOWUP filename rejected: {errors}")

    def test_followup_subdir_accepted(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".claude" / "plans" / "PLAN-094-FOLLOWUP").mkdir(parents=True)
            errors: list = []
            _fast._check_plan_schema(tdp, errors)
            self.assertEqual(errors, [], f"FOLLOWUP subdir rejected: {errors}")

    def test_followup_only_blessed_suffix(self):
        """Other uppercase suffixes must remain rejected."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".claude" / "plans" / "PLAN-094-RANDOM").mkdir(parents=True)
            (tdp / ".claude" / "plans").mkdir(parents=True, exist_ok=True)
            (tdp / ".claude" / "plans" /
             "PLAN-094-AMEND-1-bogus.md").write_text("x")
            errors: list = []
            _fast._check_plan_schema(tdp, errors)
            self.assertTrue(
                any("plan_schema_subdir:PLAN-094-RANDOM" in e for e in errors),
                f"PLAN-094-RANDOM subdir should be rejected; got {errors}",
            )
            self.assertTrue(
                any("plan_schema_filename:PLAN-094-AMEND-1-bogus.md" in e
                    for e in errors),
                f"AMEND-1 filename should be rejected (AMEND is ADR-only); "
                f"got {errors}",
            )


class TestSettingsJsonCheck(TestEnvContext):
    def test_missing_settings_is_warning_not_error(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            errors: list = []
            warnings: list = []
            data = _fast._check_settings_json(tdp, errors, warnings)
            self.assertEqual(data, {})
            self.assertEqual(errors, [])
            self.assertTrue(any("settings_json:missing" in w for w in warnings))

    def test_invalid_json_is_error(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            (tdp / ".claude").mkdir()
            (tdp / ".claude" / "settings.json").write_text("{not json")
            errors: list = []
            warnings: list = []
            _fast._check_settings_json(tdp, errors, warnings)
            self.assertTrue(any("settings_json:parse_fail" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
