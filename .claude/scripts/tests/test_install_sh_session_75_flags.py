"""install.sh flag-parser tests for Session 75 Codex Finding 5 closure
(refined by Session 76 audit-v3 / Codex DIM-19).

Verifies:
- `--strict-placeholders` is a recognized flag (was advertised in
  docs/READINESS-STATUS.md but parser rejected it).
- `--verify` is a recognized flag.
- `--verify-sigstore` is RESTORED as a deprecated alias for `--verify`
  (Session 76 audit-v3 / DIM-19 closure). Owner D2 lock keeps the
  sigstore backend out of scope, but SemVer policy demanded the alias.
  Parser MUST accept the flag, emit a stderr deprecation warning, and
  behave identically to `--verify`. Removal scheduled for v2.0.0.
- `--dry-run` does NOT create the target directory on disk
  (prior code mkdir'd despite "no files modified" promise).
- Unknown flags still exit 2 (LSB CLI usage error convention).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

INSTALL_SH = REPO_ROOT / "scripts" / "install.sh"


def _run_install(args, env=None, timeout=30):
    return subprocess.run(
        ["bash", str(INSTALL_SH), *args],
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


class InstallShSession75FlagsTest(TestEnvContext):
    def test_strict_placeholders_flag_accepted(self) -> None:
        """--strict-placeholders is a recognized flag (Finding 5)."""
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            result = _run_install([
                "--dry-run", "--strict-placeholders",
                "--target", str(target),
            ])
            # Dry-run must exit 0; --strict-placeholders is recognized.
            self.assertEqual(
                result.returncode, 0,
                msg=f"stdout={result.stdout!r} stderr={result.stderr!r}",
            )

    def test_verify_flag_accepted(self) -> None:
        """--verify is a recognized flag (Finding 5)."""
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            result = _run_install([
                "--dry-run", "--verify",
                "--target", str(target),
            ])
            self.assertEqual(
                result.returncode, 0,
                msg=f"stdout={result.stdout!r} stderr={result.stderr!r}",
            )

    def test_verify_sigstore_flag_accepted_as_deprecated_alias(self) -> None:
        """--verify-sigstore is a DEPRECATED ALIAS for --verify (Session 76
        audit-v3 / Codex DIM-19 closure).

        SemVer policy in SPEC/v1/install-cli.md §Deprecation requires that
        any flag removal ship with a deprecated alias + stderr warning + a
        90-day window before MAJOR removal. Session 75 removed
        `--verify-sigstore` in a patch release without an alias; Session 76
        restores the alias. Owner D2 (sigstore backend out of scope)
        remains in force — the alias delegates to `--verify` semantics
        without re-introducing the sigstore backend.

        Pre-Session-76 this test asserted exit 2 (unknown flag). Now it
        asserts exit 0 (accepted) AND a stderr deprecation warning.
        """
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            result = _run_install([
                "--dry-run", "--verify-sigstore",
                "--target", str(target),
            ])
            # Dry-run with a recognized flag must exit 0.
            self.assertEqual(
                result.returncode, 0,
                msg=(
                    f"expected exit 0 (alias accepted). "
                    f"stdout={result.stdout!r} stderr={result.stderr!r}"
                ),
            )
            self.assertIn(
                "deprecated", result.stderr.lower(),
                msg=(
                    f"expected stderr deprecation warning. "
                    f"stderr={result.stderr!r}"
                ),
            )

    def test_dry_run_does_not_create_target_dir(self) -> None:
        """--dry-run with non-existent target MUST NOT create it (Finding 5)."""
        with TemporaryDirectory() as td:
            target = Path(td) / "fresh-target-that-does-not-exist"
            self.assertFalse(target.exists(), "test setup invariant")
            result = _run_install([
                "--dry-run",
                "--target", str(target),
            ])
            # Dry-run must succeed
            self.assertEqual(
                result.returncode, 0,
                msg=f"stdout={result.stdout!r} stderr={result.stderr!r}",
            )
            # Target must NOT exist after dry-run
            self.assertFalse(
                target.exists(),
                f"--dry-run created target dir {target} despite 'no files modified' promise. "
                f"stdout={result.stdout!r} stderr={result.stderr!r}",
            )

    def test_unknown_flag_exits_2(self) -> None:
        """Unknown flag continues to exit 2 (LSB convention preserved)."""
        with TemporaryDirectory() as td:
            target = Path(td) / "target"
            target.mkdir()
            result = _run_install([
                "--dry-run", "--definitely-not-a-real-flag",
                "--target", str(target),
            ])
            self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
