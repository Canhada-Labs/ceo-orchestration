"""Unit tests for log-friction.sh (PLAN-015 Phase 0.4).

Tests invoke the bash script via subprocess with a per-test tempfile
workdir. Assertions cover:

  * success path (first invocation creates header; second appends)
  * missing required args (severity / category / message)
  * bad enums (severity / category)
  * message validation (too short / too long / embedded newline / CR)
  * pipe-escaping in markdown cell
  * --help prints usage + exit 0
  * --file override (absolute + relative)
  * infra error (unwritable parent)

Test style follows existing repo pattern (see test_check_contamination.py):
- unittest.TestCase
- tempfile.mkdtemp per test
- subprocess.run with capture_output=True, text=True, check=False
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

_SCRIPT = (
    Path(__file__).resolve().parent.parent / "log-friction.sh"
).resolve()


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    """Invoke the bash script with the given args in the given cwd."""
    return subprocess.run(
        ["bash", str(_SCRIPT), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


class LogFrictionTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="log-friction-test-")).resolve()
        self.default_path = self.root / ".claude" / "plans" / "PLAN-015" / "frictions.md"

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


# ----------------------------------------------------------------------
# 1. Success path
# ----------------------------------------------------------------------


class TestSuccessPath(LogFrictionTestBase):

    def test_first_invocation_creates_file_with_header_and_row(self) -> None:
        proc = run(
            "--severity", "P0",
            "--category", "install",
            "--message", "install.sh failed on macOS 14.5",
            cwd=self.root,
        )
        self.assertEqual(proc.returncode, 0, msg=f"stderr={proc.stderr!r}")
        self.assertTrue(self.default_path.exists(), msg="frictions.md not created")

        content = self.default_path.read_text(encoding="utf-8")
        self.assertIn("# Frictions log — PLAN-015", content)
        self.assertIn("| Timestamp (UTC) | Severity | Category | Message |", content)
        self.assertIn("|-----------------|----------|----------|---------|", content)
        self.assertIn("| P0 | install | install.sh failed on macOS 14.5 |", content)

        # stdout confirmation: severity + category + message
        self.assertIn("P0", proc.stdout)
        self.assertIn("install", proc.stdout)
        self.assertIn("install.sh failed on macOS 14.5", proc.stdout)

    def test_second_invocation_appends_without_reheader(self) -> None:
        r1 = run(
            "--severity", "P1",
            "--category", "hook",
            "--message", "first entry",
            cwd=self.root,
        )
        self.assertEqual(r1.returncode, 0)
        r2 = run(
            "--severity", "P2",
            "--category", "docs",
            "--message", "second entry",
            cwd=self.root,
        )
        self.assertEqual(r2.returncode, 0)

        content = self.default_path.read_text(encoding="utf-8")
        # Header appears exactly once.
        self.assertEqual(
            content.count("# Frictions log — PLAN-015"), 1,
            msg="header duplicated on re-invocation",
        )
        # Both rows present.
        self.assertIn("| P1 | hook | first entry |", content)
        self.assertIn("| P2 | docs | second entry |", content)
        # Two data rows under the header separator.
        rows = [ln for ln in content.splitlines() if ln.startswith("| 20")]
        self.assertEqual(len(rows), 2)


# ----------------------------------------------------------------------
# 2. Missing args
# ----------------------------------------------------------------------


class TestMissingArgs(LogFrictionTestBase):

    def test_missing_severity(self) -> None:
        proc = run(
            "--category", "install",
            "--message", "some message",
            cwd=self.root,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("severity", proc.stderr.lower())
        self.assertFalse(self.default_path.exists())

    def test_missing_category(self) -> None:
        proc = run(
            "--severity", "P0",
            "--message", "some message",
            cwd=self.root,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("category", proc.stderr.lower())
        self.assertFalse(self.default_path.exists())

    def test_missing_message(self) -> None:
        proc = run(
            "--severity", "P0",
            "--category", "install",
            cwd=self.root,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("message", proc.stderr.lower())
        self.assertFalse(self.default_path.exists())


# ----------------------------------------------------------------------
# 3. Bad enums
# ----------------------------------------------------------------------


class TestBadEnums(LogFrictionTestBase):

    def test_bad_severity_enum(self) -> None:
        proc = run(
            "--severity", "P4",
            "--category", "install",
            "--message", "valid message",
            cwd=self.root,
        )
        self.assertEqual(proc.returncode, 1)
        # Error should suggest valid values.
        self.assertIn("P4", proc.stderr)
        self.assertIn("P0", proc.stderr)
        self.assertIn("P3", proc.stderr)
        self.assertFalse(self.default_path.exists())

    def test_bad_category_enum(self) -> None:
        proc = run(
            "--severity", "P1",
            "--category", "nonsense",
            "--message", "valid message",
            cwd=self.root,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("nonsense", proc.stderr)
        # Should list at least one valid category.
        self.assertIn("install", proc.stderr)
        self.assertFalse(self.default_path.exists())


# ----------------------------------------------------------------------
# 4. Message validation
# ----------------------------------------------------------------------


class TestMessageValidation(LogFrictionTestBase):

    def test_message_too_short(self) -> None:
        proc = run(
            "--severity", "P3",
            "--category", "ux",
            "--message", "hi",   # 2 chars
            cwd=self.root,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("short", proc.stderr.lower())
        self.assertFalse(self.default_path.exists())

    def test_message_too_long(self) -> None:
        too_long = "x" * 600
        proc = run(
            "--severity", "P3",
            "--category", "ux",
            "--message", too_long,
            cwd=self.root,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("long", proc.stderr.lower())
        self.assertFalse(self.default_path.exists())

    def test_message_with_embedded_newline_rejected(self) -> None:
        proc = run(
            "--severity", "P1",
            "--category", "hook",
            "--message", "line1\nline2",
            cwd=self.root,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("newline", proc.stderr.lower())
        self.assertFalse(self.default_path.exists())

    def test_message_with_carriage_return_rejected(self) -> None:
        proc = run(
            "--severity", "P1",
            "--category", "hook",
            "--message", "line1\rline2",
            cwd=self.root,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("carriage", proc.stderr.lower())
        self.assertFalse(self.default_path.exists())


# ----------------------------------------------------------------------
# 5. Pipe-escaping
# ----------------------------------------------------------------------


class TestPipeEscaping(LogFrictionTestBase):

    def test_pipe_in_message_escaped_in_file_not_in_stdout(self) -> None:
        msg = "col_a=1|col_b=2|col_c=3"
        proc = run(
            "--severity", "P2",
            "--category", "other",
            "--message", msg,
            cwd=self.root,
        )
        self.assertEqual(proc.returncode, 0, msg=f"stderr={proc.stderr!r}")

        # In the file: pipes are backslash-escaped.
        file_content = self.default_path.read_text(encoding="utf-8")
        self.assertIn(r"col_a=1\|col_b=2\|col_c=3", file_content)
        # Raw unescaped pipes inside a data cell would break the column
        # boundary — make sure the exact unescaped triple-pipe sequence
        # does not appear as a cell value.
        self.assertNotIn("| col_a=1|col_b=2|col_c=3 |", file_content)

        # In stdout: the original message is preserved un-escaped.
        self.assertIn("col_a=1|col_b=2|col_c=3", proc.stdout)
        self.assertNotIn(r"col_a=1\|col_b=2", proc.stdout)


# ----------------------------------------------------------------------
# 6. --help
# ----------------------------------------------------------------------


class TestHelp(LogFrictionTestBase):

    def test_help_long_flag(self) -> None:
        proc = run("--help", cwd=self.root)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Usage", proc.stdout)
        self.assertIn("--severity", proc.stdout)
        self.assertIn("--category", proc.stdout)
        self.assertIn("--message", proc.stdout)
        # No file side-effect.
        self.assertFalse(self.default_path.exists())

    def test_help_short_flag(self) -> None:
        proc = run("-h", cwd=self.root)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Usage", proc.stdout)
        self.assertFalse(self.default_path.exists())


# ----------------------------------------------------------------------
# 7. --file override
# ----------------------------------------------------------------------


class TestFileOverride(LogFrictionTestBase):

    def test_custom_absolute_file_path(self) -> None:
        custom = self.root / "custom" / "somewhere" / "frictions.md"
        proc = run(
            "--severity", "P0",
            "--category", "spawn",
            "--message", "spawn hook fired twice",
            "--file", str(custom),
            cwd=self.root,
        )
        self.assertEqual(proc.returncode, 0, msg=f"stderr={proc.stderr!r}")
        self.assertTrue(custom.exists())
        self.assertFalse(
            self.default_path.exists(),
            msg="default path should NOT be written when --file used",
        )
        content = custom.read_text(encoding="utf-8")
        self.assertIn("| P0 | spawn | spawn hook fired twice |", content)

    def test_custom_relative_file_path_resolves_from_cwd(self) -> None:
        # Run from root with a relative --file path — must resolve to root.
        rel = "logs/frictions.md"
        proc = run(
            "--severity", "P3",
            "--category", "governance",
            "--message", "small governance nit",
            "--file", rel,
            cwd=self.root,
        )
        self.assertEqual(proc.returncode, 0, msg=f"stderr={proc.stderr!r}")
        self.assertTrue((self.root / "logs" / "frictions.md").exists())


# ----------------------------------------------------------------------
# 8. Infra error
# ----------------------------------------------------------------------


class TestInfraError(LogFrictionTestBase):

    def test_unwritable_parent_returns_exit_2(self) -> None:
        # Create a read-only parent and try to write inside it.
        locked_parent = self.root / "locked"
        locked_parent.mkdir()
        os.chmod(locked_parent, 0o500)  # r-x------ (no write)

        target = locked_parent / "sub" / "frictions.md"
        try:
            proc = run(
                "--severity", "P0",
                "--category", "install",
                "--message", "should fail to write",
                "--file", str(target),
                cwd=self.root,
            )
            # Root may bypass permissions (CI containers run as root).
            # In that case, exit 0 is legitimate; skip the assertion.
            if os.geteuid() == 0:
                self.skipTest("running as root bypasses chmod restrictions")
            self.assertEqual(proc.returncode, 2, msg=f"stderr={proc.stderr!r}")
            self.assertIn("infra error", proc.stderr.lower())
        finally:
            # Restore perms so tearDown can rmtree.
            os.chmod(locked_parent, 0o700)


# ----------------------------------------------------------------------
# 9. Edge cases — additional safety margin
# ----------------------------------------------------------------------


class TestEdgeCases(LogFrictionTestBase):

    def test_message_at_exact_min_length_accepted(self) -> None:
        proc = run(
            "--severity", "P3",
            "--category", "ux",
            "--message", "abc",  # exactly 3 chars
            cwd=self.root,
        )
        self.assertEqual(proc.returncode, 0, msg=f"stderr={proc.stderr!r}")
        self.assertTrue(self.default_path.exists())

    def test_message_at_exact_max_length_accepted(self) -> None:
        msg = "y" * 500
        proc = run(
            "--severity", "P2",
            "--category", "performance",
            "--message", msg,
            cwd=self.root,
        )
        self.assertEqual(proc.returncode, 0, msg=f"stderr={proc.stderr!r}")
        content = self.default_path.read_text(encoding="utf-8")
        self.assertIn(msg, content)

    def test_equals_form_of_flags_works(self) -> None:
        # --severity=P0 style (single arg with =) must also be accepted.
        proc = run(
            "--severity=P0",
            "--category=install",
            "--message=smoke via equals form",
            cwd=self.root,
        )
        self.assertEqual(proc.returncode, 0, msg=f"stderr={proc.stderr!r}")
        content = self.default_path.read_text(encoding="utf-8")
        self.assertIn("| P0 | install | smoke via equals form |", content)

    def test_unknown_flag_returns_exit_1(self) -> None:
        proc = run(
            "--severity", "P0",
            "--category", "install",
            "--message", "valid message",
            "--bogus", "whatever",
            cwd=self.root,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("--bogus", proc.stderr)
        self.assertFalse(self.default_path.exists())

    def test_timestamp_is_iso8601_utc(self) -> None:
        import re
        proc = run(
            "--severity", "P0",
            "--category", "install",
            "--message", "timestamp shape check",
            cwd=self.root,
        )
        self.assertEqual(proc.returncode, 0)
        # First token of stdout is the ISO timestamp.
        first = proc.stdout.split()[0]
        self.assertRegex(
            first,
            re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"),
        )


if __name__ == "__main__":
    unittest.main()
