"""PLAN-045 Wave 2 P0-08 — _lib.audit_rotation shared primitive tests.

Exercises the extracted rotation primitive that both audit_log.py
and audit_emit.py will call. Includes:
- Happy-path rotation when size > threshold
- No rotation when size <= threshold
- No rotation when file absent
- Collision handling (monthly-slug + counter suffix)
- Cross-device-safe rename (os.replace, not os.rename)
- Max-collision safety valve
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_HOOKS = Path(__file__).resolve().parent.parent

from _lib.audit_rotation import rotate_if_needed  # noqa: E402


class TestRotateIfNeeded(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmp.name)
        self.log = self.tmpdir / "audit-log.jsonl"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_missing_file_returns_none(self) -> None:
        result = rotate_if_needed(
            self.log, threshold_bytes=100, month_slug="2026-04"
        )
        self.assertIsNone(result)

    def test_under_threshold_returns_none(self) -> None:
        self.log.write_text("x" * 50)
        result = rotate_if_needed(
            self.log, threshold_bytes=100, month_slug="2026-04"
        )
        self.assertIsNone(result)
        self.assertTrue(self.log.is_file())

    def test_at_threshold_returns_none(self) -> None:
        # threshold is INCLUSIVE upper bound — no rotation at exactly N.
        self.log.write_text("x" * 100)
        result = rotate_if_needed(
            self.log, threshold_bytes=100, month_slug="2026-04"
        )
        self.assertIsNone(result)

    def test_over_threshold_rotates(self) -> None:
        self.log.write_text("y" * 500)
        result = rotate_if_needed(
            self.log, threshold_bytes=100, month_slug="2026-04"
        )
        self.assertIsNotNone(result)
        assert result is not None  # narrow for mypy
        self.assertEqual(result.name, "audit-log-2026-04.jsonl")
        self.assertTrue(result.is_file())
        # Original log path no longer exists (it was renamed).
        self.assertFalse(self.log.exists())
        # Content preserved.
        self.assertEqual(result.read_text(), "y" * 500)

    def test_collision_suffix(self) -> None:
        # First rotation claims audit-log-2026-04.jsonl.
        self.log.write_text("a" * 500)
        first = rotate_if_needed(
            self.log, threshold_bytes=100, month_slug="2026-04"
        )
        self.assertEqual(first.name, "audit-log-2026-04.jsonl")

        # Write again + rotate — second rotation within same month
        # must land at audit-log-2026-04-1.jsonl.
        self.log.write_text("b" * 500)
        second = rotate_if_needed(
            self.log, threshold_bytes=100, month_slug="2026-04"
        )
        self.assertIsNotNone(second)
        self.assertEqual(second.name, "audit-log-2026-04-1.jsonl")
        self.assertEqual(second.read_text(), "b" * 500)

        # Third
        self.log.write_text("c" * 500)
        third = rotate_if_needed(
            self.log, threshold_bytes=100, month_slug="2026-04"
        )
        self.assertEqual(third.name, "audit-log-2026-04-2.jsonl")

    def test_different_month_slug_no_collision(self) -> None:
        self.log.write_text("a" * 500)
        rotate_if_needed(
            self.log, threshold_bytes=100, month_slug="2026-04"
        )
        self.log.write_text("b" * 500)
        second = rotate_if_needed(
            self.log, threshold_bytes=100, month_slug="2026-05"
        )
        self.assertIsNotNone(second)
        self.assertEqual(second.name, "audit-log-2026-05.jsonl")

    def test_max_collisions_safety_valve(self) -> None:
        # Seed 5 existing rotations.
        for i in range(5):
            if i == 0:
                (self.tmpdir / "audit-log-2026-04.jsonl").write_text("x")
            else:
                (self.tmpdir / f"audit-log-2026-04-{i}.jsonl").write_text("x")
        self.log.write_text("y" * 500)
        result = rotate_if_needed(
            self.log, threshold_bytes=100, month_slug="2026-04",
            max_collisions=3,  # tight valve — should exhaust
        )
        self.assertIsNone(result)
        # Original file untouched on failure.
        self.assertTrue(self.log.is_file())

    def test_stat_osrror_returns_none(self) -> None:
        self.log.write_text("y" * 500)
        # Patch Path.stat to raise.
        with mock.patch.object(
            Path, "stat",
            side_effect=PermissionError("denied"),
        ):
            result = rotate_if_needed(
                self.log, threshold_bytes=100, month_slug="2026-04"
            )
        self.assertIsNone(result)

    def test_rename_osrror_returns_none(self) -> None:
        self.log.write_text("y" * 500)
        with mock.patch("os.replace", side_effect=OSError("EROFS")):
            result = rotate_if_needed(
                self.log, threshold_bytes=100, month_slug="2026-04"
            )
        self.assertIsNone(result)
        # Original still present (rename failed).
        self.assertTrue(self.log.is_file())

    def test_custom_stem_preserved(self) -> None:
        custom = self.tmpdir / "my-audit.jsonl"
        custom.write_text("z" * 500)
        result = rotate_if_needed(
            custom, threshold_bytes=100, month_slug="2026-04"
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "my-audit-2026-04.jsonl")


if __name__ == "__main__":
    unittest.main()
