"""Tests for `_lib.injection_salt` (PLAN-058 Round-23).

Verifies the per-installation salt module that backs the
``UserPromptSubmit.prompt_sha`` identifier-privacy hardening.

## Coverage matrix

| # | Property                                              | Test                                              |
|---|-------------------------------------------------------|---------------------------------------------------|
| 1 | First call generates salt + persists to disk          | test_first_call_generates_and_persists            |
| 2 | File mode is 0o600 after first call                   | test_persisted_salt_file_mode_is_0o600            |
| 3 | Subsequent calls return cached bytes (no disk I/O)    | test_subsequent_calls_use_cache                   |
| 4 | Salt is exactly 32 bytes                              | test_salt_is_32_bytes                             |
| 5 | Two fresh installations produce different salts       | test_independent_installations_produce_different_salts |
| 6 | Pre-existing well-formed salt file is reused          | test_existing_salt_file_is_reused                 |
| 7 | Corrupt salt (wrong size) triggers regeneration       | test_corrupt_size_triggers_regeneration           |
| 8 | Fail-open: returns b"" when dir cannot be created     | test_fail_open_when_dir_unwritable                |
| 9 | Fail-open: returns b"" when file cannot be written    | test_fail_open_when_file_unwritable               |
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Iterator
from unittest import mock


_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))


def _import_module():
    """Reimport injection_salt fresh to reset module cache."""
    if "_lib.injection_salt" in sys.modules:
        del sys.modules["_lib.injection_salt"]
    from _lib import injection_salt  # type: ignore
    return injection_salt


class _IsolatedHomeMixin(unittest.TestCase):
    """Provides a temp HOME to isolate `~/.claude/projects/...` writes."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._fake_home = Path(self._tmp.name)
        self._home_patch = mock.patch.dict(
            os.environ, {"HOME": str(self._fake_home)}, clear=False
        )
        self._home_patch.start()
        self.salt_mod = _import_module()
        self.salt_mod.reset_cache_for_test()

    def tearDown(self) -> None:
        self.salt_mod.reset_cache_for_test()
        self._home_patch.stop()
        self._tmp.cleanup()

    def _expected_salt_path(self) -> Path:
        return (
            self._fake_home
            / ".claude"
            / "projects"
            / "ceo-orchestration"
            / ".salt"
        )


class TestSaltGeneration(_IsolatedHomeMixin):

    def test_first_call_generates_and_persists(self) -> None:
        path = self._expected_salt_path()
        self.assertFalse(path.exists(), "salt file should not exist pre-call")

        salt = self.salt_mod.get_instance_salt()

        self.assertEqual(len(salt), 32, "salt must be 32 bytes")
        self.assertTrue(path.exists(), "salt file must be persisted")
        self.assertEqual(path.read_bytes(), salt, "on-disk bytes match returned")

    def test_persisted_salt_file_mode_is_0o600(self) -> None:
        self.salt_mod.get_instance_salt()
        path = self._expected_salt_path()
        mode = path.stat().st_mode & 0o777
        self.assertEqual(mode, 0o600, f"salt file mode should be 0o600, got 0o{mode:o}")

    def test_salt_is_32_bytes(self) -> None:
        salt = self.salt_mod.get_instance_salt()
        self.assertEqual(len(salt), 32)

    def test_independent_installations_produce_different_salts(self) -> None:
        # First installation
        salt_a = self.salt_mod.get_instance_salt()

        # Tear down + bring up a second isolated HOME
        self.salt_mod.reset_cache_for_test()
        self._home_patch.stop()
        with tempfile.TemporaryDirectory() as tmp_b:
            with mock.patch.dict(
                os.environ, {"HOME": str(tmp_b)}, clear=False
            ):
                self.salt_mod.reset_cache_for_test()
                salt_b = self.salt_mod.get_instance_salt()
        # restore the original HOME patch for tearDown
        self._home_patch = mock.patch.dict(
            os.environ, {"HOME": str(self._fake_home)}, clear=False
        )
        self._home_patch.start()

        self.assertNotEqual(
            salt_a, salt_b,
            "two fresh installations must produce different salts"
        )


class TestSaltCaching(_IsolatedHomeMixin):

    def test_subsequent_calls_use_cache(self) -> None:
        salt_first = self.salt_mod.get_instance_salt()

        # Delete the on-disk file: cached value must still be returned
        path = self._expected_salt_path()
        path.unlink()
        self.assertFalse(path.exists())

        salt_second = self.salt_mod.get_instance_salt()
        self.assertEqual(
            salt_first, salt_second,
            "cached salt must be returned even if file is deleted"
        )
        self.assertFalse(
            path.exists(),
            "cache hit must NOT touch the filesystem"
        )

    def test_existing_salt_file_is_reused(self) -> None:
        # Pre-create a valid salt file
        path = self._expected_salt_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        prepared = b"\xaa" * 32
        path.write_bytes(prepared)

        salt = self.salt_mod.get_instance_salt()
        self.assertEqual(salt, prepared, "pre-existing salt must be reused")


class TestSaltCorruption(_IsolatedHomeMixin):

    def test_corrupt_size_triggers_regeneration(self) -> None:
        # Pre-create a corrupt (wrong-size) salt file
        path = self._expected_salt_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"too-short")
        self.assertEqual(len(path.read_bytes()), 9)

        salt = self.salt_mod.get_instance_salt()

        self.assertEqual(len(salt), 32, "regenerated salt must be 32 bytes")
        self.assertEqual(
            path.read_bytes(), salt,
            "regenerated salt must overwrite corrupt file"
        )


class TestFailOpen(_IsolatedHomeMixin):

    def test_fail_open_when_dir_unwritable(self) -> None:
        # Force mkdir to raise OSError
        with mock.patch(
            "pathlib.Path.mkdir", side_effect=OSError("perm denied")
        ):
            salt = self.salt_mod.get_instance_salt()
        self.assertEqual(salt, b"", "must return empty bytes on dir failure")

    def test_fail_open_when_file_unwritable(self) -> None:
        # Allow mkdir to succeed but force write_bytes to fail
        path = self._expected_salt_path()
        # First ensure parent exists so the test isolates the write failure
        path.parent.mkdir(parents=True, exist_ok=True)
        with mock.patch(
            "pathlib.Path.write_bytes", side_effect=OSError("disk full")
        ):
            salt = self.salt_mod.get_instance_salt()
        self.assertEqual(salt, b"", "must return empty bytes on write failure")


if __name__ == "__main__":
    unittest.main()
