"""Regression tests for ``.claude/scripts/generate-adr-index.py``.

PLAN-113 Phase B W3 (doc/ADR-index reconcile). Guards the AMEND/suffixed-ID
parsing fixes: the index must (a) read AMEND files with very large YAML
frontmatter (no fixed-window truncation), (b) keep distinct display labels
for ``ADR-049a`` / ``ADR-019-AMEND-1`` instead of collapsing to the base id,
(c) strip a leading ``ADR-NNN[...]:`` echo from titles, (d) read status from a
below-heading embedded frontmatter block, and (e) sort base-before-AMEND.

Stdlib-only; Python >= 3.9. Subclasses ``TestEnvContext`` per CLAUDE.md §5 /
the test-env-hygiene mandate (no bare ``unittest.TestCase``).
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPT_ROOT / "hooks"))

from _lib.testing import TestEnvContext  # noqa: E402


def _load_module():
    """Load the hyphenated generator script as a module."""
    spec = importlib.util.spec_from_file_location(
        "generate_adr_index", SCRIPT_ROOT / "scripts" / "generate-adr-index.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


gen = _load_module()


class TestDisplayIdAndSort(TestEnvContext):
    def test_display_id_base(self) -> None:
        self.assertEqual(
            gen._display_id_from_filename("ADR-007-foo.md"), "ADR-007"
        )

    def test_display_id_a_suffix(self) -> None:
        self.assertEqual(
            gen._display_id_from_filename("ADR-049a-worktree.md"), "ADR-049a"
        )

    def test_display_id_amend(self) -> None:
        self.assertEqual(
            gen._display_id_from_filename("ADR-019-AMEND-2-foo.md"),
            "ADR-019-AMEND-2",
        )

    def test_display_id_non_adr(self) -> None:
        self.assertIsNone(gen._display_id_from_filename("README.md"))

    def test_sort_base_before_a_before_amend(self) -> None:
        names = [
            "ADR-049-AMEND-1-x.md",
            "ADR-049a-worktree.md",
            "ADR-049-base.md",
        ]
        ordered = sorted(names, key=lambda n: gen._sort_key_from_filename(n))
        self.assertEqual(
            ordered,
            ["ADR-049-base.md", "ADR-049a-worktree.md", "ADR-049-AMEND-1-x.md"],
        )

    def test_sort_amend_numeric(self) -> None:
        names = ["ADR-055-AMEND-2-y.md", "ADR-055-AMEND-1-x.md"]
        ordered = sorted(names, key=lambda n: gen._sort_key_from_filename(n))
        self.assertEqual(
            ordered, ["ADR-055-AMEND-1-x.md", "ADR-055-AMEND-2-y.md"]
        )


class TestParseAdr(TestEnvContext):
    def _write(self, d: Path, name: str, body: str) -> Path:
        p = d / name
        p.write_text(body, encoding="utf-8")
        return p

    def test_large_frontmatter_not_truncated(self) -> None:
        """A multi-KB frontmatter block must still yield title + status."""
        with tempfile.TemporaryDirectory() as td:
            big = "filler: " + ("x" * 4000) + "\n"
            body = (
                "---\n"
                "id: ADR-055-AMEND-1\n"
                "title: ADR-055 amendment — spool writer\n"
                "status: ACCEPTED\n"
                + big
                + "---\n\n# body\n"
            )
            p = self._write(Path(td), "ADR-055-AMEND-1-spool.md", body)
            adr_id, title, status = gen._parse_adr(p)
            self.assertEqual(adr_id, "ADR-055-AMEND-1")
            self.assertEqual(status, "ACCEPTED")
            # leading "ADR-055 " echo stripped from the title column
            self.assertNotIn("ADR-055", title)
            self.assertIn("spool writer", title)

    def test_markdown_heading_amend_title_clean(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            body = (
                "# ADR-019-AMEND-1: Confidence-gate per-class block-mode\n\n"
                "**Status:** ACCEPTED\n"
            )
            p = self._write(Path(td), "ADR-019-AMEND-1-cg.md", body)
            adr_id, title, status = gen._parse_adr(p)
            self.assertEqual(adr_id, "ADR-019-AMEND-1")
            self.assertEqual(status, "ACCEPTED")
            self.assertEqual(title, "Confidence-gate per-class block-mode")

    def test_heading_then_embedded_frontmatter_status(self) -> None:
        """`# ADR-NNN-AMEND-N` heading first, then a `---` YAML block."""
        with tempfile.TemporaryDirectory() as td:
            body = (
                "# ADR-042-AMEND-1 — Read-only MCP tools expansion\n\n"
                "---\n"
                "adr_id: ADR-042-AMEND-1\n"
                "title: Read-only MCP tools expansion\n"
                "status: ACCEPTED\n"
                "---\n"
            )
            p = self._write(Path(td), "ADR-042-AMEND-1-mcp.md", body)
            adr_id, title, status = gen._parse_adr(p)
            self.assertEqual(adr_id, "ADR-042-AMEND-1")
            self.assertEqual(status, "ACCEPTED")

    def test_em_dash_heading_separator(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            body = "# ADR-104-AMEND-1 — AEK Calibration\n\n**Status:** PROPOSED\n"
            p = self._write(Path(td), "ADR-104-AMEND-1-aek.md", body)
            adr_id, title, status = gen._parse_adr(p)
            self.assertEqual(adr_id, "ADR-104-AMEND-1")
            self.assertEqual(title, "AEK Calibration")
            self.assertEqual(status, "PROPOSED")


if __name__ == "__main__":
    unittest.main()
