"""PLAN-046 Cluster 1.5 — terminal_compress tests.

Imports the staged scaffold from
``.claude/plans/PLAN-046/staged-code/terminal_compress.py``.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_SCAFFOLD = (
    _REPO_ROOT / "tests" / "fixtures" / "staged_scaffold"
    / "terminal_compress.py"
)


def _load_scaffold():
    spec = importlib.util.spec_from_file_location(
        "terminal_compress_staged", _SCAFFOLD
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_HOOKS_DIR = Path(__file__).resolve().parent.parent
from _lib.testing import TestEnvContext  # noqa: E402


class TerminalCompressTest(TestEnvContext):

    def setUp(self) -> None:
        super().setUp()
        self.mod = _load_scaffold()
        os.environ["CEO_TERMINAL_COMPRESS"] = "on"

    def test_ansi_escape_stripped(self) -> None:
        raw = "\x1b[31mRED\x1b[0m plain"
        out = self.mod.compress(raw)
        self.assertNotIn("\x1b", out)
        self.assertIn("RED", out)
        self.assertIn("plain", out)

    def test_trailing_whitespace_trimmed(self) -> None:
        raw = "line1   \nline2\t\nline3"
        out = self.mod.compress(raw)
        self.assertEqual(out, "line1\nline2\nline3")

    def test_repeated_blank_lines_collapsed(self) -> None:
        raw = "a\n\n\n\n\nb"
        out = self.mod.compress(raw)
        self.assertEqual(out.count("\n"), 2)

    def test_box_drawing_collapsed(self) -> None:
        raw = "name──────value"
        out = self.mod.compress(raw)
        self.assertNotIn("─", out)
        self.assertIn("name", out)
        self.assertIn("value", out)

    def test_prefix_group_collapse_ls_like(self) -> None:
        raw = "\n".join([
            "-rw-r--r--  1 u  staff    1 Apr 21  file1.py",
            "-rw-r--r--  1 u  staff    2 Apr 21  file2.py",
            "-rw-r--r--  1 u  staff    3 Apr 21  file3.py",
            "-rw-r--r--  1 u  staff    4 Apr 21  file4.py",
            "-rw-r--r--  1 u  staff    5 Apr 21  file5.py",
            "-rw-r--r--  1 u  staff    6 Apr 21  file6.py",
        ])
        out = self.mod.compress(raw)
        self.assertIn("file1.py", out)
        self.assertIn("file6.py", out)
        self.assertIn("elided", out)
        self.assertLess(len(out), len(raw))

    def test_prefix_collapse_disabled_via_env(self) -> None:
        os.environ["CEO_TERMINAL_COMPRESS_COLLAPSE"] = "off"
        raw = "\n".join([f"prefix----{i}" for i in range(6)])
        out = self.mod.compress(raw)
        self.assertNotIn("elided", out)

    def test_off_backend_passthrough(self) -> None:
        os.environ["CEO_TERMINAL_COMPRESS"] = "off"
        raw = "\x1b[31mRED\x1b[0m   trailing  "
        self.assertEqual(self.mod.compress(raw), raw)

    def test_empty_string_roundtrip(self) -> None:
        self.assertEqual(self.mod.compress(""), "")

    def test_type_error_on_non_string(self) -> None:
        with self.assertRaises(TypeError):
            self.mod.compress(b"bytes not str")  # type: ignore[arg-type]

    def test_single_line_untouched(self) -> None:
        raw = "hello world"
        self.assertEqual(self.mod.compress(raw), raw)

    def test_short_group_not_collapsed(self) -> None:
        raw = "\n".join(["prefix-one", "prefix-two", "prefix-three"])
        out = self.mod.compress(raw)
        self.assertNotIn("elided", out)

    def test_short_prefix_not_collapsed(self) -> None:
        raw = "\n".join([f"ab{i}" for i in range(6)])
        out = self.mod.compress(raw)
        self.assertNotIn("elided", out)

    def test_preserves_identifiers_after_strip(self) -> None:
        raw = "\x1b[2mPATH=/usr/local/bin\x1b[0m"
        out = self.mod.compress(raw)
        self.assertIn("PATH=/usr/local/bin", out)

    def test_ratio_computation(self) -> None:
        raw = "x" * 1000
        out = "x" * 500
        self.assertAlmostEqual(self.mod.ratio(raw, out), 0.5)
        self.assertEqual(self.mod.ratio("", ""), 0.0)

    def test_compression_reduces_typical_payload(self) -> None:
        """Real-world-ish input gets measurably smaller."""
        raw = "\n".join([
            f"\x1b[34m{i:03d}\x1b[0m  trailing{' ' * 10}"
            for i in range(20)
        ])
        out = self.mod.compress(raw)
        self.assertLess(len(out), len(raw))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
