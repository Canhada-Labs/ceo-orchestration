"""
Unit tests for .claude/scripts/check-docs-freshness.py.
PLAN-010 Phase 3. Stdlib-only, Python >= 3.9.
"""

from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "check-docs-freshness.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "docs_freshness"


def _load():
    spec = importlib.util.spec_from_file_location("check_docs_freshness", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CDF = _load()


def _scan_fixture(name: str):
    """Scan a single fixture file with fixture dir as root. Returns list."""
    path = FIXTURES / name
    return CDF.scan_file(path, FIXTURES, allowlist=[])


class TestFixtures(unittest.TestCase):
    def test_link_in_table_detects_broken(self):
        broken = _scan_fixture("link_in_table.md")
        targets = [b["target"] for b in broken]
        self.assertIn("does_not_exist.md", targets)
        self.assertNotIn("real_target.md", targets)

    def test_link_in_fenced_code_ignored(self):
        broken = _scan_fixture("link_in_fenced_code.md")
        targets = [b["target"] for b in broken]
        for ignored in ("this_should_be_ignored.md", "also_ignored.md", "also_ignored_tilde.md"):
            self.assertNotIn(ignored, targets, f"fenced link {ignored} must be skipped")

    def test_link_in_inline_code_ignored(self):
        broken = _scan_fixture("link_in_inline_code.md")
        targets = [b["target"] for b in broken]
        self.assertNotIn("should_be_ignored.md", targets)
        self.assertNotIn("also_ignored.md", targets)

    def test_link_in_frontmatter_ignored(self):
        # frontmatter is stripped; `phantom_from_frontmatter.md` is not a link anyway
        broken = _scan_fixture("link_in_frontmatter.md")
        targets = [b["target"] for b in broken]
        self.assertNotIn("phantom_from_frontmatter.md", targets)
        # real link resolves
        self.assertNotIn("real_target.md", targets)

    def test_link_in_html_comment_ignored(self):
        broken = _scan_fixture("link_in_html_comment.md")
        targets = [b["target"] for b in broken]
        self.assertNotIn("inside_comment_ignored.md", targets)
        self.assertNotIn("also_hidden_ignored.md", targets)

    def test_link_relative_parent_detects_broken_only(self):
        broken = _scan_fixture("link_relative_parent.md")
        targets = [b["target"] for b in broken]
        self.assertIn("../nonexistent_dir/nothing.md", targets)
        self.assertNotIn("./real_target.md", targets)
        self.assertNotIn("../docs_freshness/real_target.md", targets)

    def test_link_anchor_only_ignored(self):
        broken = _scan_fixture("link_anchor_only.md")
        self.assertEqual(broken, [])

    def test_link_url_encoded_resolves(self):
        broken = _scan_fixture("link_url_encoded.md")
        targets = [b["target"] for b in broken]
        # with%20space.md exists; sub%2Fdir.md should resolve to sub/dir.md (exists)
        self.assertNotIn("with%20space.md", targets)
        self.assertNotIn("sub%2Fdir.md", targets)

    def test_link_broken_detected(self):
        broken = _scan_fixture("link_broken.md")
        targets = [b["target"] for b in broken]
        self.assertIn("definitely_missing_file.md", targets)
        self.assertIn("missing_two.md", targets)
        self.assertEqual(len(broken), 2)

    def test_link_external_url_ignored(self):
        broken = _scan_fixture("link_external_url.md")
        targets = [b["target"] for b in broken]
        for ignored in (
            "https://anthropic.com",
            "http://example.com/path",
            "mailto:foo@example.com",
            "ftp://ftp.example.com/file",
            "javascript:void(0)",
        ):
            self.assertNotIn(ignored, targets)


class TestHelpers(unittest.TestCase):
    def test_classify_target(self):
        self.assertEqual(CDF.classify_target("https://x.com"), "external")
        self.assertEqual(CDF.classify_target("mailto:a@b.c"), "external")
        self.assertEqual(CDF.classify_target("#section"), "anchor")
        self.assertEqual(CDF.classify_target("foo.md"), "local")
        self.assertEqual(CDF.classify_target(""), "empty")
        self.assertEqual(CDF.classify_target("<./foo.md>"), "local")

    def test_strip_frontmatter_preserves_line_numbers(self):
        text = "---\nid: X\n---\nHello\n"
        body, lead = CDF.strip_frontmatter(text)
        self.assertEqual(lead, 3)
        # 4 lines after split; first 3 blanked
        self.assertEqual(body.splitlines()[0], "")
        self.assertEqual(body.splitlines()[3], "Hello")

    def test_mask_inline_code_preserves_length(self):
        line = "a `foo bar` b"
        masked = CDF.mask_inline_code(line)
        self.assertEqual(len(masked), len(line))
        self.assertNotIn("foo", masked)
        self.assertIn("a ", masked)
        self.assertTrue(masked.endswith(" b"))

    def test_mask_inline_code_double_backtick(self):
        line = "x ``a ` b`` y"
        masked = CDF.mask_inline_code(line)
        self.assertEqual(len(masked), len(line))
        self.assertNotIn("a ` b", masked)

    def test_allowlist_exact_match(self):
        self.assertTrue(CDF.is_allowlisted("foo.md", ["foo.md"]))
        self.assertFalse(CDF.is_allowlisted("bar.md", ["foo.md"]))
        # fragment stripped before compare
        self.assertTrue(CDF.is_allowlisted("foo.md#section", ["foo.md"]))


class TestCLI(unittest.TestCase):
    def test_json_output_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs" / "a.md").write_text("[x](missing.md)\n", encoding="utf-8")
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = CDF.main(
                    [
                        "--root",
                        str(root),
                        "--format",
                        "json",
                        "--glob",
                        "docs/**/*.md",
                    ]
                )
            self.assertEqual(rc, 1)
            payload = json.loads(buf.getvalue())
            self.assertIn("scanned_files", payload)
            self.assertIn("broken_count", payload)
            self.assertIn("broken", payload)
            self.assertEqual(payload["broken_count"], 1)
            entry = payload["broken"][0]
            for k in ("file", "line", "col", "target", "resolved"):
                self.assertIn(k, entry)

    def test_exit_code_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs" / "a.md").write_text("no links here\n", encoding="utf-8")
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = CDF.main(
                    ["--root", str(root), "--format", "text", "--glob", "docs/**/*.md"]
                )
            self.assertEqual(rc, 0)

    def test_allowlist_honored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs" / "a.md").write_text("[x](missing.md)\n", encoding="utf-8")
            allow = root / "allow.txt"
            allow.write_text("# owner: @test\nmissing.md\n", encoding="utf-8")
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = CDF.main(
                    [
                        "--root",
                        str(root),
                        "--allowlist",
                        str(allow),
                        "--format",
                        "text",
                        "--glob",
                        "docs/**/*.md",
                    ]
                )
            self.assertEqual(rc, 0)


class TestRepoIntegration(unittest.TestCase):
    """Scan a small real slice of the repo to ensure the scanner survives
    real-world markdown without blowing up."""

    def test_claude_md_scannable(self):
        repo_root = Path(__file__).resolve().parents[3]
        claude_md = repo_root / "CLAUDE.md"
        self.assertTrue(claude_md.exists())
        # Just verify it does not raise.
        broken = CDF.scan_file(claude_md, repo_root, allowlist=[])
        self.assertIsInstance(broken, list)


if __name__ == "__main__":
    unittest.main()
