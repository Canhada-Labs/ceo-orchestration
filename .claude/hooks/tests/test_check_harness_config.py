"""Tests for check_harness_config.py (PLAN-153 Wave E item 1 / ADR-173).

Covers:
- the runtime-resolution model (anchored vs cwd-relative, the
  ``_python-hook.sh`` dirname rule, silent fail-open dead rails);
- the fixture corpus under
  ``.claude/hooks/tests/fixtures/harness-config/`` in BOTH directions
  (planted violations go RED; the good fixture is green; the allowlisted
  no-op passes while the unlisted no-op fails);
- the behavioral positive-control replay, including the live replay of
  the three security-critical blocking hooks against this repo, the
  missing-fixture / tampered-fixture redden paths, and the
  ``CEO_SOTA_DISABLE`` skip.

STAGED with the module it asserts (PLAN-153 staging discipline): tests of
NEW behavior land together with the staged file.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import unittest
import unittest.mock as mock
from pathlib import Path

from _lib.testing import TestEnvContext  # noqa: E402

import check_harness_config as chc  # noqa: E402


def _real_repo_root() -> Path:
    """Walk up from this file until the real repo root (works from both
    the staged location and the landed .claude/hooks/tests/ location).

    Requires BOTH the hook file and `.git` — a PLAN staging mirror
    (.claude/plans/PLAN-NNN/staged/wave-X/.claude/hooks/...) can contain
    staged copies of the hooks but is never a git root."""
    d = Path(__file__).resolve().parent
    for candidate in [d, *d.parents]:
        if (
            (candidate / ".git").exists()
            and (candidate / ".claude" / "hooks" / "check_bash_safety.py").is_file()
        ):
            return candidate
    raise RuntimeError("real repo root not found from " + str(d))


_REPO = _real_repo_root()
_FIXTURES = _REPO / ".claude" / "hooks" / "tests" / "fixtures" / "harness-config"
_SETTINGS_FIXTURES = _FIXTURES / "settings"
_REPLAY_FIXTURES = _FIXTURES / "replay"


def _reds(findings):
    return [f for f in findings if f.severity == "RED"]


def _reds_for(findings, check_id):
    return [f for f in findings if f.severity == "RED" and f.check_id == check_id]


class _SyntheticTreeMixin:
    """Builds the minimal synthetic project tree the settings fixtures
    reference (shim + check_ok_hook.py)."""

    def _build_tree(self) -> Path:
        root = self.project_dir  # from TestEnvContext
        hooks = root / ".claude" / "hooks"
        hooks.mkdir(parents=True, exist_ok=True)
        (hooks / "_python-hook.sh").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
        (hooks / "check_ok_hook.py").write_text("# synthetic\n", encoding="utf-8")
        return root


class TestAnalyzeHookCommand(_SyntheticTreeMixin, TestEnvContext):
    def setUp(self):
        super().setUp()
        self.root = self._build_tree()

    def _run(self, command):
        return chc.analyze_hook_command(command, self.root, location="t")

    def test_anchored_shim_existing_script_green(self):
        f, noop = self._run(
            'bash "$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh" check_ok_hook.py'
        )
        self.assertEqual(_reds(f), [])
        self.assertFalse(noop)

    def test_relative_shim_is_red_s254_class(self):
        f, _ = self._run("bash .claude/hooks/_python-hook.sh check_ok_hook.py")
        reds = _reds_for(f, "runtime_resolution")
        self.assertTrue(reds)
        self.assertIn("cwd-relative", reds[0].message)

    def test_shim_arg_resolves_via_dirname_rule_missing_is_red(self):
        f, _ = self._run(
            'bash "$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh" check_missing.py'
        )
        reds = _reds_for(f, "runtime_resolution")
        self.assertTrue(reds)
        self.assertIn("fail-open", reds[0].message)

    def test_shim_without_script_arg_is_red(self):
        f, _ = self._run('bash "$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh"')
        self.assertTrue(_reds_for(f, "runtime_resolution"))

    def test_anchored_direct_py_green(self):
        f, _ = self._run('python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/check_ok_hook.py"')
        self.assertEqual(_reds(f), [])

    def test_relative_direct_py_is_red(self):
        f, _ = self._run("python3 .claude/hooks/check_ok_hook.py")
        self.assertTrue(_reds_for(f, "runtime_resolution"))

    def test_absolute_direct_py_green(self):
        target = self.root / ".claude" / "hooks" / "check_ok_hook.py"
        f, _ = self._run(f'python3 "{target}"')
        self.assertEqual(_reds(f), [])

    def test_anchored_direct_py_missing_is_red(self):
        f, _ = self._run('python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/gone.py"')
        self.assertTrue(_reds_for(f, "runtime_resolution"))

    def test_unparseable_command_fails_closed(self):
        f, _ = self._run("bash \"$CLAUDE_PROJECT_DIR/unterminated")
        reds = _reds_for(f, "runtime_resolution")
        self.assertTrue(reds)
        self.assertIn("not shell-parseable", reds[0].message)

    def test_empty_command_is_red(self):
        f, _ = self._run("   ")
        self.assertTrue(_reds_for(f, "runtime_resolution"))

    def test_echo_constant_is_noop_candidate(self):
        f, noop = self._run("echo '{\"decision\":\"allow\"}'")
        self.assertEqual(_reds(f), [])
        self.assertTrue(noop)

    def test_echo_referencing_script_is_not_noop(self):
        _, noop = self._run('echo "$CLAUDE_PROJECT_DIR/.claude/hooks/check_ok_hook.py"')
        self.assertFalse(noop)


class TestStaticOnFixtureCorpus(_SyntheticTreeMixin, TestEnvContext):
    def setUp(self):
        super().setUp()
        self.root = self._build_tree()

    def _static(self, fixture_name, **kwargs):
        kwargs.setdefault("include_exec_bit", False)
        return chc.run_static(
            self.root, [_SETTINGS_FIXTURES / fixture_name], **kwargs
        )

    def test_good_settings_zero_red(self):
        self.assertEqual(_reds(self._static("settings_good.json")), [])

    def test_planted_runtime_unresolvable_goes_red(self):
        reds = _reds_for(
            self._static("settings_runtime_unresolvable.json"), "runtime_resolution"
        )
        self.assertTrue(reds, "the S254 planted dead rail MUST redden the gate")

    def test_inline_secret_goes_red_without_echoing_value(self):
        findings = self._static("settings_inline_secret.json")
        reds = _reds_for(findings, "inline_secret")
        self.assertTrue(reds)
        for f in reds:
            self.assertNotIn("AKIA", f.message, "matched secret must not be echoed")

    def test_unlisted_noop_goes_red(self):
        reds = _reds_for(self._static("settings_noop_unlisted.json"), "noop_hook")
        self.assertTrue(reds)

    def test_annotated_noop_passes(self):
        findings = self._static("settings_noop_allowlisted.json")
        self.assertEqual(_reds_for(findings, "noop_hook"), [])
        self.assertEqual(_reds(findings), [])

    def test_allowlist_file_direction_passes(self):
        allow = self.root / "noop-allow.txt"
        allow.write_text(
            "# harness no-op allowlist (test)\nsynthetic unlisted no-op\n",
            encoding="utf-8",
        )
        findings = self._static(
            "settings_noop_unlisted.json", noop_allowlist_path=allow
        )
        self.assertEqual(_reds_for(findings, "noop_hook"), [])

    def test_missing_deny_baseline_goes_red(self):
        reds = _reds_for(self._static("settings_missing_deny.json"), "deny_baseline")
        # fixture keeps 1 of the baseline entries → all others must be flagged
        self.assertEqual(len(reds), len(chc.DENY_BASELINE) - 1)

    def test_deny_baseline_skipped_when_no_permissions_key(self):
        self.assertEqual(chc.check_deny_baseline({}, "x"), [])

    def test_malformed_settings_raises_value_error(self):
        bad = self.root / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        with self.assertRaises(ValueError):
            chc.run_static(self.root, [bad], include_exec_bit=False)


class TestLiveRepoStatic(TestEnvContext):
    """The gate must be green against the LIVE dogfood settings + template
    (otherwise landing this gate reds CI on day one)."""

    def test_live_settings_green(self):
        findings = chc.run_static(
            _REPO,
            [
                _REPO / ".claude" / "settings.json",
                _REPO / "templates" / "settings" / "settings.base.json",
            ],
            include_exec_bit=False,
        )
        self.assertEqual(
            _reds(findings),
            [],
            "live settings must pass: " + "; ".join(f.message for f in _reds(findings)),
        )


class TestReplay(TestEnvContext):
    def test_placeholder_substitution(self):
        doc = {"a": ["x {{PROJECT_DIR}}/y", {"b": "{{PROJECT_DIR}}"}], "n": 3}
        out = chc._substitute_placeholders(doc, Path("/repo"))
        self.assertEqual(out["a"][0], "x /repo/y")
        self.assertEqual(out["a"][1]["b"], "/repo")
        self.assertEqual(out["n"], 3)

    def test_is_block_shaped(self):
        self.assertTrue(chc._is_block_shaped({"decision": "block", "reason": "r"}))
        self.assertTrue(
            chc._is_block_shaped(
                {"hookSpecificOutput": {"permissionDecision": "deny"}}
            )
        )
        self.assertFalse(chc._is_block_shaped({"decision": "allow"}))
        self.assertFalse(chc._is_block_shaped({}))
        self.assertFalse(chc._is_block_shaped("block"))

    def test_missing_fixture_reddens_run(self):
        empty = self.project_dir / "empty-fixtures"
        empty.mkdir(parents=True, exist_ok=True)
        findings = chc.run_replay(_REPO, empty)
        reds = _reds_for(findings, "replay")
        self.assertEqual(len(reds), len(chc.REQUIRED_REPLAY_CONTROLS))
        for f in reds:
            self.assertIn("MISSING", f.message)

    def test_tampered_fixture_reddens_run(self):
        tampered_dir = self.project_dir / "tampered"
        tampered_dir.mkdir(parents=True, exist_ok=True)
        src = _REPLAY_FIXTURES / "bash_safety_destructive.json"
        doc = json.loads(src.read_text(encoding="utf-8"))
        doc["expect"] = "allow"  # tamper
        (tampered_dir / src.name).write_text(json.dumps(doc), encoding="utf-8")
        findings = chc.run_replay(
            _REPO,
            tampered_dir,
            controls=(("check_bash_safety.py", src.name),),
        )
        reds = _reds_for(findings, "replay")
        self.assertTrue(reds)
        self.assertIn("tampered", reds[0].message)

    def test_unparseable_fixture_reddens_run(self):
        bad_dir = self.project_dir / "badfix"
        bad_dir.mkdir(parents=True, exist_ok=True)
        (bad_dir / "bash_safety_destructive.json").write_text("{nope", encoding="utf-8")
        findings = chc.run_replay(
            _REPO,
            bad_dir,
            controls=(("check_bash_safety.py", "bash_safety_destructive.json"),),
        )
        reds = _reds_for(findings, "replay")
        self.assertTrue(reds)
        self.assertIn("fail-closed", reds[0].message)

    def test_sota_disable_skips_replay(self):
        with mock.patch.dict(os.environ, {"CEO_SOTA_DISABLE": "1"}):
            findings = chc.run_replay(_REPO, _REPLAY_FIXTURES)
        self.assertEqual(_reds(findings), [])
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].severity, "WARN")
        self.assertIn("skipped", findings[0].message)

    def test_live_positive_controls_all_block(self):
        """The centerpiece: replay the three planted violations against the
        real hooks in this repo; every one must be observed BLOCKING."""
        findings = chc.run_replay(_REPO, _REPLAY_FIXTURES)
        self.assertEqual(
            _reds(findings),
            [],
            "positive control failed: "
            + "; ".join(f"{f.location}: {f.message}" for f in _reds(findings)),
        )


class TestMainExitCodes(_SyntheticTreeMixin, TestEnvContext):
    def setUp(self):
        super().setUp()
        self.root = self._build_tree()

    def _main(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
            rc = chc.main(argv)
        return rc, buf.getvalue()

    def test_green_static_exit_0(self):
        rc, out = self._main(
            [
                "--static",
                "--no-exec-bit",
                "--repo-root",
                str(self.root),
                "--settings",
                str(_SETTINGS_FIXTURES / "settings_good.json"),
            ]
        )
        self.assertEqual(rc, 0)
        self.assertIn("OK", out)

    def test_red_static_exit_1(self):
        rc, out = self._main(
            [
                "--static",
                "--no-exec-bit",
                "--repo-root",
                str(self.root),
                "--settings",
                str(_SETTINGS_FIXTURES / "settings_runtime_unresolvable.json"),
            ]
        )
        self.assertEqual(rc, 1)
        self.assertIn("FAIL", out)

    def test_malformed_settings_exit_2(self):
        bad = self.root / "bad.json"
        bad.write_text("{oops", encoding="utf-8")
        rc, _ = self._main(
            [
                "--static",
                "--no-exec-bit",
                "--repo-root",
                str(self.root),
                "--settings",
                str(bad),
            ]
        )
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
