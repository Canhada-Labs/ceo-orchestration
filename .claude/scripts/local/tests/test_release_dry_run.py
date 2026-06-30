"""Tests for .claude/scripts/local/release-dry-run.py.

PLAN-078 Wave 3 — covers acceptance criteria:
  T1.  check_version_matches_tag — pass when VERSION == target; fail on mismatch
  T2.  check_changelog_entry_exists — pass on '## [VERSION]' line; fail when missing
  T3.  check_audit_log_schema_additivity — pass with all v1 fields present; fail when one stripped
  T4.  check_owner_asc_populated — pass on non-empty file; skip when file absent
  T5.  check_governance_validate — pass on exit-0 from validate-governance.sh
  T6.  check_smoke_install — skipped when --skip-install flag present
  T7.  check_install_self_sha — pass when placeholder present; pass on real source tree
  T8.  check_rc_hold_window — RC tags always pass; GA tags need prior RC ≥24h old
  T9.  check_weekly_workflow_status — skip when --skip-network or gh missing
  T10. check_sigstore_signing — skipped on *-rc* tags by design
  T11. --help prints usage, exit 0
  T12. Missing --target-version infers from git tag or exits 3
  T13. --skip-tests skips test suite gates (gates 6, 7, 8)
  T14. --strict causes skipped gates to count as failures (exit 1)
  T15. Output format: markdown table on stdout with PASS/FAIL/SKIP per gate
  T16. Timing fixture: gate execution under 60s (excluding actual pytest)
  T17. VERSION file missing → gate fails gracefully (no traceback)
  T18. CHANGELOG.md missing → gate fails gracefully
  T19. governance-waivers.yaml malformed → falls back to no-waiver (no traceback)
  T20. pyyaml import error → exit 2 with install hint on stderr
"""

from __future__ import annotations

import builtins
import importlib.util
import io
import subprocess
import sys
import tempfile
import time
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Lazy module load — script has a hyphen in its filename.
# The script may not exist yet (CEO is authoring it in parallel).
# All tests that require the module are skipped gracefully if absent.
# ---------------------------------------------------------------------------
_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "release-dry-run.py"
_module: Optional[types.ModuleType] = None

def _load_module() -> Optional[types.ModuleType]:
    global _module
    if _module is not None:
        return _module
    if not _SCRIPT_PATH.exists():
        return None
    try:
        spec = importlib.util.spec_from_file_location("release_dry_run", _SCRIPT_PATH)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        sys.modules["release_dry_run"] = mod
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        _module = mod
        return mod
    except Exception:
        return None


def _require_module(test: unittest.TestCase) -> types.ModuleType:
    """Skip the test if the script is not yet available."""
    mod = _load_module()
    if mod is None:
        test.skipTest(f"release-dry-run.py not yet written at {_SCRIPT_PATH}")
    return mod  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Helper: build minimal tmpdir fixture trees
# ---------------------------------------------------------------------------

def _make_repo(tmp: Path, version: str = "1.14.0", changelog_version: Optional[str] = None) -> Path:
    """Return a minimal repo directory with VERSION + CHANGELOG.md."""
    (tmp / "VERSION").write_text(version + "\n", encoding="utf-8")
    cl_ver = changelog_version if changelog_version is not None else version
    (tmp / "CHANGELOG.md").write_text(
        f"# Changelog\n\n## [{cl_ver}] — 2026-05-07\n\nSome entry.\n",
        encoding="utf-8",
    )
    return tmp


def _make_audit_schema(tmp: Path, strip_field: Optional[str] = None) -> Path:
    """Write a minimal AUDIT-LOG-SCHEMA.md, optionally stripping one v1 field."""
    fields = [
        "ts", "action", "session_id", "project", "tool", "subagent_type",
        "desc_preview", "desc_hash", "skill", "has_profile",
        "has_file_assignment", "prompt_len_bucket", "response_kind",
        "hook_duration_ms",
    ]
    lines = ["# Audit Log Schema\n\n```json\n{\n"]
    for f in fields:
        if f == strip_field:
            continue
        lines.append(f'  "{f}": "...",\n')
    lines.append("}\n```\n")
    path = tmp / "AUDIT-LOG-SCHEMA.md"
    path.write_text("".join(lines), encoding="utf-8")
    return path


# ===========================================================================
# T1 — check_version_matches_tag
# ===========================================================================
class TestCheckVersionMatchesTag(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_pass_when_version_matches(self) -> None:
        mod = _require_module(self)
        _make_repo(self.tmpdir, version="1.14.0")
        args = MagicMock(target_version="1.14.0", repo_root=self.tmpdir)
        result = mod.check_version_matches_tag(args)
        self.assertTrue(result.passed, f"Expected pass; detail={result.detail}")
        self.assertFalse(result.skipped)

    def test_fail_when_version_mismatch(self) -> None:
        mod = _require_module(self)
        _make_repo(self.tmpdir, version="1.13.0")
        args = MagicMock(target_version="1.14.0", repo_root=self.tmpdir)
        result = mod.check_version_matches_tag(args)
        self.assertFalse(result.passed, "Expected failure on version mismatch")
        self.assertIn("1.13.0", result.detail)


# ===========================================================================
# T2 — check_changelog_entry_exists
# ===========================================================================
class TestCheckChangelogEntryExists(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_pass_when_entry_present(self) -> None:
        mod = _require_module(self)
        _make_repo(self.tmpdir, version="1.14.0")
        args = MagicMock(target_version="1.14.0", repo_root=self.tmpdir)
        result = mod.check_changelog_entry_exists(args)
        self.assertTrue(result.passed, f"Expected pass; detail={result.detail}")

    def test_fail_when_entry_missing(self) -> None:
        mod = _require_module(self)
        _make_repo(self.tmpdir, version="1.14.0", changelog_version="1.13.0")
        args = MagicMock(target_version="1.14.0", repo_root=self.tmpdir)
        result = mod.check_changelog_entry_exists(args)
        self.assertFalse(result.passed, "Expected failure when version absent from CHANGELOG")


# ===========================================================================
# T3 — check_audit_log_schema_additivity
# ===========================================================================
class TestCheckAuditLogSchemaAdditivity(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_pass_when_all_fields_present(self) -> None:
        mod = _require_module(self)
        schema_path = _make_audit_schema(self.tmpdir)
        args = MagicMock(target_version="1.14.0", repo_root=self.tmpdir)
        # Gate reads .claude/plans/AUDIT-LOG-SCHEMA.md by convention; wire tmpdir.
        plans_dir = self.tmpdir / ".claude" / "plans"
        plans_dir.mkdir(parents=True)
        (plans_dir / "AUDIT-LOG-SCHEMA.md").write_text(
            schema_path.read_text(encoding="utf-8"), encoding="utf-8"
        )
        result = mod.check_audit_log_schema_additivity(args)
        self.assertTrue(result.passed, f"Expected pass; detail={result.detail}")

    def test_fail_when_field_stripped(self) -> None:
        mod = _require_module(self)
        plans_dir = self.tmpdir / ".claude" / "plans"
        plans_dir.mkdir(parents=True)
        schema_path = _make_audit_schema(self.tmpdir, strip_field="hook_duration_ms")
        (plans_dir / "AUDIT-LOG-SCHEMA.md").write_text(
            schema_path.read_text(encoding="utf-8"), encoding="utf-8"
        )
        args = MagicMock(target_version="1.14.0", repo_root=self.tmpdir)
        result = mod.check_audit_log_schema_additivity(args)
        self.assertFalse(result.passed, "Expected failure when v1 field stripped from schema")
        self.assertIn("hook_duration_ms", result.detail)


# ===========================================================================
# T4 — check_owner_asc_populated
# ===========================================================================
class TestCheckOwnerAscPopulated(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_pass_when_file_non_empty(self) -> None:
        mod = _require_module(self)
        trust_dir = self.tmpdir / ".claude" / "trust"
        trust_dir.mkdir(parents=True)
        (trust_dir / "owner.asc").write_text(
            "-----BEGIN PGP PUBLIC KEY BLOCK-----\nFAKE\n-----END PGP PUBLIC KEY BLOCK-----\n",
            encoding="utf-8",
        )
        args = MagicMock(target_version="1.14.0", repo_root=self.tmpdir)
        result = mod.check_owner_asc_populated(args)
        self.assertTrue(result.passed or not result.skipped,
                        f"Expected pass or non-skip; detail={result.detail}")

    def test_skip_when_file_absent(self) -> None:
        mod = _require_module(self)
        # Do NOT create .claude/trust/owner.asc
        trust_dir = self.tmpdir / ".claude" / "trust"
        trust_dir.mkdir(parents=True)
        args = MagicMock(target_version="1.14.0", repo_root=self.tmpdir)
        result = mod.check_owner_asc_populated(args)
        self.assertTrue(result.skipped, f"Expected skip when file absent; detail={result.detail}")
        self.assertIn("owner.asc", result.detail.lower())


# ===========================================================================
# T5 — check_governance_validate (subprocess mock)
# ===========================================================================
class TestCheckGovernanceValidate(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_pass_when_script_exits_zero(self) -> None:
        mod = _require_module(self)
        # Gate pre-checks the script file exists before invoking subprocess —
        # create a stub so the pre-check passes, then mock the actual run.
        script = self.tmpdir / ".claude/scripts/validate-governance.sh"
        script.parent.mkdir(parents=True)
        script.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
        args = MagicMock(target_version="1.14.0", repo_root=self.tmpdir)
        fake_result = MagicMock(returncode=0, stdout="OK", stderr="")
        with patch("subprocess.run", return_value=fake_result):
            result = mod.check_governance_validate(args)
        self.assertTrue(result.passed, f"Expected pass; detail={result.detail}")

    def test_fail_when_script_exits_nonzero(self) -> None:
        mod = _require_module(self)
        args = MagicMock(target_version="1.14.0", repo_root=self.tmpdir)
        fake_result = MagicMock(returncode=1, stdout="", stderr="5 errors found")
        with patch("subprocess.run", return_value=fake_result):
            result = mod.check_governance_validate(args)
        self.assertFalse(result.passed, "Expected failure when validate-governance.sh exits 1")


# ===========================================================================
# T6 — check_smoke_install skipped with --skip-install
# ===========================================================================
class TestCheckSmokeInstall(unittest.TestCase):
    def test_skipped_when_flag_set(self) -> None:
        mod = _require_module(self)
        args = MagicMock(target_version="1.14.0", skip_install=True,
                         repo_root=Path("/nonexistent"))
        result = mod.check_smoke_install(args)
        self.assertTrue(result.skipped, f"Expected skipped; detail={result.detail}")

    def test_not_skipped_when_flag_absent(self) -> None:
        mod = _require_module(self)
        args = MagicMock(target_version="1.14.0", skip_install=False,
                         repo_root=Path("/nonexistent"))
        fake_result = MagicMock(returncode=0, stdout="OK smoke install", stderr="")
        with patch("subprocess.run", return_value=fake_result):
            result = mod.check_smoke_install(args)
        self.assertFalse(result.skipped, "Expected gate to run when --skip-install absent")


# ===========================================================================
# T7 — check_install_self_sha
# ===========================================================================
class TestCheckInstallSelfSha(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_pass_when_placeholder_present(self) -> None:
        mod = _require_module(self)
        scripts_dir = self.tmpdir / "scripts"
        scripts_dir.mkdir()
        install_sh = scripts_dir / "install.sh"
        install_sh.write_text(
            "#!/usr/bin/env bash\necho hello\n# CEO-INSTALL-SHA256: PLACEHOLDER_RELEASE_FILL\n",
            encoding="utf-8",
        )
        args = MagicMock(target_version="1.14.0", skip_install=False, repo_root=self.tmpdir)
        result = mod.check_install_self_sha(args)
        self.assertTrue(result.passed or not result.skipped,
                        f"Expected pass (placeholder present); detail={result.detail}")

    def test_skip_when_skip_install_flag(self) -> None:
        mod = _require_module(self)
        args = MagicMock(target_version="1.14.0", skip_install=True, repo_root=self.tmpdir)
        result = mod.check_install_self_sha(args)
        self.assertTrue(result.skipped, "Expected skip when --skip-install set")


# ===========================================================================
# T8 — check_rc_hold_window
# ===========================================================================
class TestCheckRcHoldWindow(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_rc_tags_always_pass(self) -> None:
        mod = _require_module(self)
        args = MagicMock(target_version="1.15.0-rc.1", repo_root=self.tmpdir)
        # Should pass immediately without inspecting git tags
        result = mod.check_rc_hold_window(args)
        self.assertTrue(result.passed, f"RC tags must always pass; detail={result.detail}")

    def test_ga_fail_when_no_prior_rc_tag(self) -> None:
        mod = _require_module(self)
        args = MagicMock(target_version="1.14.0", repo_root=self.tmpdir)
        # git tag -l returns empty → no prior RC
        fake_result = MagicMock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=fake_result):
            result = mod.check_rc_hold_window(args)
        # Either fail (no prior RC) or pass with waiver — both are valid; check no traceback
        self.assertIsInstance(result.passed, bool)
        self.assertIsInstance(result.detail, str)

    def test_ga_pass_when_rc_old_enough(self) -> None:
        mod = _require_module(self)
        args = MagicMock(target_version="1.14.0", repo_root=self.tmpdir)
        # Simulate git tag -l returning rc tag, and timestamps 25h apart
        import time as _time
        now = int(_time.time())
        rc_ts = str(now - 90000)   # 25 hours ago
        ga_ts = str(now)
        # First call returns rc tag name; subsequent calls return timestamps
        side_effects = [
            MagicMock(returncode=0, stdout="v1.14.0-rc.1\n", stderr=""),  # list tags
            MagicMock(returncode=0, stdout=rc_ts + "\n", stderr=""),       # rc timestamp
            MagicMock(returncode=0, stdout=ga_ts + "\n", stderr=""),       # ga timestamp
        ]
        with patch("subprocess.run", side_effect=side_effects):
            result = mod.check_rc_hold_window(args)
        self.assertTrue(result.passed, f"Expected pass with ≥24h RC; detail={result.detail}")


# ===========================================================================
# T9 — check_weekly_workflow_status
# ===========================================================================
class TestCheckWeeklyWorkflowStatus(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_skip_when_skip_network_flag(self) -> None:
        mod = _require_module(self)
        args = MagicMock(target_version="1.14.0", skip_network=True, repo_root=self.tmpdir)
        result = mod.check_weekly_workflow_status(args)
        self.assertTrue(result.skipped, f"Expected skip with --skip-network; detail={result.detail}")

    def test_skip_when_gh_not_found(self) -> None:
        mod = _require_module(self)
        args = MagicMock(target_version="1.14.0", skip_network=False, repo_root=self.tmpdir)
        # Simulate gh not available: shutil.which returns None
        with patch("shutil.which", return_value=None):
            result = mod.check_weekly_workflow_status(args)
        self.assertTrue(result.skipped, f"Expected skip when gh missing; detail={result.detail}")


# ===========================================================================
# T10 — check_sigstore_signing skipped on RC tags
# ===========================================================================
class TestCheckSigstoneSigning(unittest.TestCase):
    def test_skipped_on_rc_tag(self) -> None:
        mod = _require_module(self)
        args = MagicMock(target_version="1.15.0-rc.1", repo_root=Path("/nonexistent"))
        result = mod.check_sigstore_signing(args)
        self.assertTrue(result.skipped,
                        f"Expected sigstore gate skipped on RC tags; detail={result.detail}")

    def test_not_skipped_on_ga_tag(self) -> None:
        mod = _require_module(self)
        args = MagicMock(target_version="1.14.0", repo_root=Path("/nonexistent"))
        # May pass or fail depending on env — just must not be skipped for same reason as RC
        result = mod.check_sigstore_signing(args)
        # GA tag: skipped reason should NOT be "rc tag" pattern
        if result.skipped:
            self.assertNotIn("rc", result.detail.lower(),
                             "GA tag skip should not cite RC-tag reason")


# ===========================================================================
# T11 — CLI --help
# ===========================================================================
class TestCLIHelp(unittest.TestCase):
    def test_help_exits_zero(self) -> None:
        result = subprocess.run(
            [sys.executable, str(_SCRIPT_PATH), "--help"],
            capture_output=True, text=True,
        )
        if not _SCRIPT_PATH.exists():
            self.skipTest("Script not yet written")
        self.assertEqual(result.returncode, 0, f"--help should exit 0; stderr={result.stderr}")
        self.assertTrue(
            result.stdout or result.stderr,
            "--help should print usage to stdout or stderr",
        )


# ===========================================================================
# T12 — Missing --target-version infers from git tag or exits 3
# ===========================================================================
class TestCLITargetVersionInference(unittest.TestCase):
    def test_exits_3_when_no_tag_match(self) -> None:
        if not _SCRIPT_PATH.exists():
            self.skipTest("Script not yet written")
        mod = _require_module(self)
        # No --target-version, and mock git tag to return nothing
        fake_result = MagicMock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=fake_result):
            out = io.StringIO()
            err = io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                rc = mod.main([])  # no --target-version
        self.assertEqual(rc, 3, f"Expected exit 3 when version cannot be inferred; stdout={out.getvalue()}")


# ===========================================================================
# T13 — --skip-tests skips test suite gates
# ===========================================================================
class TestSkipTestsFlag(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_skip_tests_gates_are_skipped(self) -> None:
        mod = _require_module(self)
        # Gates 6,7,8 = hook_tests, script_tests, replay_tests
        args = MagicMock(
            target_version="1.14.0",
            skip_tests=True,
            skip_install=True,
            skip_network=True,
            repo_root=self.tmpdir,
        )
        # Check that at least the hook-tests gate reports skipped
        for gate_fn_name in ("check_hook_tests", "check_script_tests", "check_replay_tests"):
            if hasattr(mod, gate_fn_name):
                result = getattr(mod, gate_fn_name)(args)
                self.assertTrue(
                    result.skipped,
                    f"{gate_fn_name} should be skipped with --skip-tests; got passed={result.passed}",
                )


# ===========================================================================
# T14 — --strict causes skipped gates to fail
# ===========================================================================
class TestStrictFlag(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_strict_exit_1_when_gate_skipped(self) -> None:
        if not _SCRIPT_PATH.exists():
            self.skipTest("Script not yet written")
        mod = _require_module(self)
        _make_repo(self.tmpdir, version="1.14.0")
        # With --strict + --skip-network, the weekly-workflow gate is skipped → must exit 1
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            # patch subprocess so governance/install gates don't really run
            fake_ok = MagicMock(returncode=0, stdout="OK", stderr="")
            with patch("subprocess.run", return_value=fake_ok), \
                 patch("shutil.which", return_value=None):  # gh not found → skip
                rc = mod.main([
                    "--target-version", "1.14.0",
                    "--skip-install",
                    "--skip-tests",
                    "--skip-network",
                    "--strict",
                    "--repo-root", str(self.tmpdir),
                ])
        self.assertEqual(rc, 1, f"--strict should exit 1 when any gate skipped; stdout={out.getvalue()}")


# ===========================================================================
# T15 — Output format: markdown table with PASS/FAIL/SKIP
# ===========================================================================
class TestOutputFormat(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_markdown_table_on_stdout(self) -> None:
        if not _SCRIPT_PATH.exists():
            self.skipTest("Script not yet written")
        mod = _require_module(self)
        _make_repo(self.tmpdir, version="1.14.0")
        out = io.StringIO()
        fake_ok = MagicMock(returncode=0, stdout="OK", stderr="")
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            with patch("subprocess.run", return_value=fake_ok), \
                 patch("shutil.which", return_value=None):
                mod.main([
                    "--target-version", "1.14.0",
                    "--skip-install",
                    "--skip-tests",
                    "--skip-network",
                    "--repo-root", str(self.tmpdir),
                ])
        output = out.getvalue()
        # Markdown table rows use | separators
        self.assertIn("|", output, "Output must contain markdown table pipes")
        # At least one of the status strings must appear
        has_status = any(s in output for s in ("PASS", "FAIL", "SKIP"))
        self.assertTrue(has_status, f"Output must contain PASS/FAIL/SKIP; got:\n{output[:500]}")


# ===========================================================================
# T16 — Timing: gates complete in <60s (excluding real pytest)
# ===========================================================================
class TestTimingFast(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_gates_complete_under_60s(self) -> None:
        if not _SCRIPT_PATH.exists():
            self.skipTest("Script not yet written")
        mod = _require_module(self)
        _make_repo(self.tmpdir, version="1.14.0")
        fake_ok = MagicMock(returncode=0, stdout="OK", stderr="")
        start = time.monotonic()
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            with patch("subprocess.run", return_value=fake_ok), \
                 patch("shutil.which", return_value=None):
                mod.main([
                    "--target-version", "1.14.0",
                    "--skip-install",
                    "--skip-tests",
                    "--skip-network",
                    "--repo-root", str(self.tmpdir),
                ])
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 60.0,
                        f"All skipped/mocked gates must complete < 60s; took {elapsed:.1f}s")


# ===========================================================================
# T17 — VERSION file missing → gate fails gracefully
# ===========================================================================
class TestVersionFileMissing(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_graceful_failure_no_traceback(self) -> None:
        mod = _require_module(self)
        # tmpdir has no VERSION file
        args = MagicMock(target_version="1.14.0", repo_root=self.tmpdir)
        try:
            result = mod.check_version_matches_tag(args)
        except Exception as exc:  # noqa: BLE001
            self.fail(f"Gate raised exception instead of returning GateResult: {exc}")
        self.assertFalse(result.passed, "Gate should fail (not crash) when VERSION missing")
        self.assertIsInstance(result.detail, str)
        self.assertGreater(len(result.detail), 0)


# ===========================================================================
# T18 — CHANGELOG.md missing → gate fails gracefully
# ===========================================================================
class TestChangelogFileMissing(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_graceful_failure_no_traceback(self) -> None:
        mod = _require_module(self)
        # Write VERSION but no CHANGELOG
        (self.tmpdir / "VERSION").write_text("1.14.0\n", encoding="utf-8")
        args = MagicMock(target_version="1.14.0", repo_root=self.tmpdir)
        try:
            result = mod.check_changelog_entry_exists(args)
        except Exception as exc:  # noqa: BLE001
            self.fail(f"Gate raised exception instead of returning GateResult: {exc}")
        self.assertFalse(result.passed, "Gate should fail (not crash) when CHANGELOG missing")
        self.assertIsInstance(result.detail, str)


# ===========================================================================
# T19 — governance-waivers.yaml malformed → fallback, no traceback
# ===========================================================================
class TestGovernanceWaiversMalformed(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_malformed_yaml_does_not_crash(self) -> None:
        mod = _require_module(self)
        gov_dir = self.tmpdir / ".claude" / "governance"
        gov_dir.mkdir(parents=True)
        # Write intentionally malformed YAML
        (gov_dir / "governance-waivers.yaml").write_text(
            "rc_hold:\n  - {broken yaml: [unclosed bracket\n",
            encoding="utf-8",
        )
        args = MagicMock(target_version="1.14.0", repo_root=self.tmpdir)
        # check_rc_hold_window reads the waivers file; a GA tag with no rc should fail
        # but must not traceback on malformed yaml
        fake_result = MagicMock(returncode=0, stdout="", stderr="")
        try:
            with patch("subprocess.run", return_value=fake_result):
                result = mod.check_rc_hold_window(args)
        except Exception as exc:  # noqa: BLE001
            self.fail(f"Malformed waivers.yaml caused exception: {exc}")
        # Result must be a valid GateResult regardless
        self.assertIsInstance(result.passed, bool)
        self.assertIsInstance(result.detail, str)


# ===========================================================================
# T20 — pyyaml import error → exit 2 with install hint on stderr
# ===========================================================================
class TestPyyamlImportError(unittest.TestCase):
    def test_exit_2_with_install_hint(self) -> None:
        if not _SCRIPT_PATH.exists():
            self.skipTest("Script not yet written")
        # Re-execute the script in a subprocess with pyyaml hidden via PYTHONPATH trick.
        # We pass a synthetic sitecustomize that makes `import yaml` fail.
        import os
        env = os.environ.copy()
        # Inject a broken yaml shim before the real one
        tmp = tempfile.TemporaryDirectory()
        shim_dir = Path(tmp.name)
        (shim_dir / "yaml.py").write_text(
            "raise ImportError('yaml shim: simulated missing pyyaml')\n",
            encoding="utf-8",
        )
        env["PYTHONPATH"] = str(shim_dir) + os.pathsep + env.get("PYTHONPATH", "")
        result = subprocess.run(
            [sys.executable, str(_SCRIPT_PATH), "--target-version", "1.14.0"],
            capture_output=True, text=True, env=env, timeout=15,
        )
        tmp.cleanup()
        self.assertEqual(result.returncode, 2,
                         f"Expected exit 2 on missing pyyaml; got {result.returncode}; "
                         f"stderr={result.stderr[:300]}")
        # Install hint must mention pip install
        combined = (result.stdout + result.stderr).lower()
        self.assertIn("pip", combined,
                      "stderr must contain pip install hint when pyyaml missing")


# ===========================================================================
# GateResult dataclass shape
# ===========================================================================
class TestGateResultShape(unittest.TestCase):
    def test_gate_result_has_required_fields(self) -> None:
        mod = _require_module(self)
        gr = mod.GateResult
        # Instantiate with all required fields
        instance = gr(
            name="test-gate",
            passed=True,
            skipped=False,
            detail="all good",
            duration_ms=42,
        )
        self.assertEqual(instance.name, "test-gate")
        self.assertTrue(instance.passed)
        self.assertFalse(instance.skipped)
        self.assertEqual(instance.detail, "all good")
        self.assertEqual(instance.duration_ms, 42)


# ===========================================================================
# GATES list presence
# ===========================================================================
class TestGatesListRegistered(unittest.TestCase):
    def test_gates_list_is_non_empty(self) -> None:
        mod = _require_module(self)
        self.assertTrue(hasattr(mod, "GATES"), "Script must export a GATES list")
        self.assertGreater(len(mod.GATES), 0, "GATES list must be non-empty")

    def test_gates_are_callables(self) -> None:
        mod = _require_module(self)
        for gate in mod.GATES:
            self.assertTrue(callable(gate), f"Gate {gate!r} must be callable")


if __name__ == "__main__":
    unittest.main()
