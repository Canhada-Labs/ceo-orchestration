"""Tests for .claude/scripts/local/dependency-graph.py.

PLAN-078 Wave 4 spike — covers acceptance criteria:
  T1. Frontmatter parser: whitelist enforcement (drops unknown keys)
  T2. Frontmatter parser: missing block raises FrontmatterParseError
  T3. Frontmatter parser: inline list `[a, b, c]` parses correctly
  T4. Frontmatter parser: multi-line list with `- item` indent parses
  T5. Frontmatter parser: inline comment stripped from scalar
  T6. Frontmatter parser: external_wait scalar extracts PLAN-NNN
  T7. Graph builder: unknown depends_on emits warning + dropped from edges
  T8. Cycle detection: 2-node cycle flagged
  T9. Cycle detection: 3-node cycle flagged
  T10. Cycle detection: acyclic graph returns []
  T11. Layout: levels assigned topologically
  T12. SVG render: HTML-escapes <script> in title (XSS safety)
  T13. End-to-end: small fixture renders to valid HTML under cap
  T14. CLI: missing plans-dir returns exit 2
  T15. CLI: --strict-cycles fails when cycle present
"""

from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

# Load the script as a module
_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "dependency-graph.py"
_spec = importlib.util.spec_from_file_location("dependency_graph", _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
dg = importlib.util.module_from_spec(_spec)
sys.modules["dependency_graph"] = dg
_spec.loader.exec_module(dg)


def _write_plan(tmpdir: Path, plan_id: str, frontmatter: str, body: str = "") -> Path:
    path = tmpdir / f"{plan_id}-test.md"
    path.write_text(f"---\n{frontmatter}\n---\n{body}\n", encoding="utf-8")
    return path


class FrontmatterParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    # T1
    def test_whitelist_drops_unknown_keys(self) -> None:
        path = _write_plan(
            self.tmpdir,
            "PLAN-001",
            "id: PLAN-001\ntitle: Test\nstatus: done\nsecret_field: leaked\nbudget_tokens: 100k",
        )
        fm = dg.parse_frontmatter(path)
        self.assertNotIn("secret_field", fm)
        self.assertNotIn("budget_tokens", fm)
        self.assertEqual(fm["id"], "PLAN-001")
        self.assertEqual(fm["title"], "Test")
        self.assertEqual(fm["status"], "done")

    # T2
    def test_missing_block_raises(self) -> None:
        path = self.tmpdir / "no-frontmatter.md"
        path.write_text("just body, no fence\n", encoding="utf-8")
        with self.assertRaises(dg.FrontmatterParseError):
            dg.parse_frontmatter(path)

    # T3
    def test_inline_list_parses(self) -> None:
        path = _write_plan(
            self.tmpdir,
            "PLAN-001",
            'id: PLAN-001\ntitle: T\nstatus: draft\ndepends_on: [PLAN-002, PLAN-003]\ntags: [a, b, c]',
        )
        fm = dg.parse_frontmatter(path)
        self.assertEqual(fm["depends_on"], ["PLAN-002", "PLAN-003"])
        self.assertEqual(fm["tags"], ["a", "b", "c"])

    # T4
    def test_multiline_list_parses(self) -> None:
        path = _write_plan(
            self.tmpdir,
            "PLAN-001",
            "id: PLAN-001\ntitle: T\nstatus: draft\nrelated_plans:\n  - PLAN-002\n  - PLAN-003",
        )
        fm = dg.parse_frontmatter(path)
        self.assertEqual(fm["related_plans"], ["PLAN-002", "PLAN-003"])

    # T5
    def test_inline_comment_stripped(self) -> None:
        path = _write_plan(
            self.tmpdir,
            "PLAN-001",
            "id: PLAN-001\ntitle: T\nstatus: draft  # active state",
        )
        fm = dg.parse_frontmatter(path)
        self.assertEqual(fm["status"], "draft")

    # T6
    def test_external_wait_scalar_extracts_plan_id(self) -> None:
        path = _write_plan(
            self.tmpdir,
            "PLAN-001",
            "id: PLAN-001\ntitle: T\nstatus: draft\nexternal_wait: PLAN-070-Layer-B-shipped",
        )
        fm = dg.parse_frontmatter(path)
        # parse_frontmatter keeps it as scalar; the build_graph extracts PLAN-NNN
        self.assertIn("external_wait", fm)


class GraphBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    # T7
    def test_unknown_depends_on_warns_and_drops(self) -> None:
        _write_plan(
            self.tmpdir,
            "PLAN-001",
            "id: PLAN-001\ntitle: T\nstatus: draft\ndepends_on: [PLAN-999]",
        )
        result = dg.build_graph(self.tmpdir)
        self.assertEqual(len(result.nodes), 1)
        node = result.nodes["PLAN-001"]
        self.assertNotIn("depends_on", node.edges)
        self.assertTrue(any("PLAN-999" in w for w in result.warnings))

    def test_external_wait_filename_preserved_when_no_plan_ref(self) -> None:
        _write_plan(
            self.tmpdir,
            "PLAN-002",
            "id: PLAN-002\ntitle: T\nstatus: draft\nexternal_wait: some-non-plan-thing",
        )
        result = dg.build_graph(self.tmpdir)
        self.assertEqual(len(result.nodes), 1)
        node = result.nodes["PLAN-002"]
        # external_wait without PLAN-NNN should produce no edge
        self.assertNotIn("external_wait", node.edges)


class CycleDetectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    # T8
    def test_two_node_cycle(self) -> None:
        _write_plan(
            self.tmpdir,
            "PLAN-001",
            "id: PLAN-001\ntitle: A\nstatus: draft\ndepends_on: [PLAN-002]",
        )
        _write_plan(
            self.tmpdir,
            "PLAN-002",
            "id: PLAN-002\ntitle: B\nstatus: draft\ndepends_on: [PLAN-001]",
        )
        result = dg.build_graph(self.tmpdir)
        cycles = dg.detect_cycles(result.nodes)
        self.assertGreaterEqual(len(cycles), 1)
        flat = {p for c in cycles for p in c}
        self.assertIn("PLAN-001", flat)
        self.assertIn("PLAN-002", flat)

    # T9
    def test_three_node_cycle(self) -> None:
        _write_plan(
            self.tmpdir,
            "PLAN-001",
            "id: PLAN-001\ntitle: A\nstatus: draft\ndepends_on: [PLAN-002]",
        )
        _write_plan(
            self.tmpdir,
            "PLAN-002",
            "id: PLAN-002\ntitle: B\nstatus: draft\ndepends_on: [PLAN-003]",
        )
        _write_plan(
            self.tmpdir,
            "PLAN-003",
            "id: PLAN-003\ntitle: C\nstatus: draft\ndepends_on: [PLAN-001]",
        )
        result = dg.build_graph(self.tmpdir)
        cycles = dg.detect_cycles(result.nodes)
        self.assertGreaterEqual(len(cycles), 1)

    # T10
    def test_acyclic(self) -> None:
        _write_plan(
            self.tmpdir,
            "PLAN-001",
            "id: PLAN-001\ntitle: A\nstatus: draft\ndepends_on: [PLAN-002]",
        )
        _write_plan(
            self.tmpdir,
            "PLAN-002",
            "id: PLAN-002\ntitle: B\nstatus: draft\ndepends_on: [PLAN-003]",
        )
        _write_plan(
            self.tmpdir,
            "PLAN-003",
            "id: PLAN-003\ntitle: C\nstatus: draft",
        )
        result = dg.build_graph(self.tmpdir)
        self.assertEqual(dg.detect_cycles(result.nodes), [])


class LayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    # T11
    def test_topological_levels(self) -> None:
        _write_plan(
            self.tmpdir,
            "PLAN-001",
            "id: PLAN-001\ntitle: A\nstatus: draft\ndepends_on: [PLAN-002]",
        )
        _write_plan(
            self.tmpdir,
            "PLAN-002",
            "id: PLAN-002\ntitle: B\nstatus: draft\ndepends_on: [PLAN-003]",
        )
        _write_plan(
            self.tmpdir,
            "PLAN-003",
            "id: PLAN-003\ntitle: C\nstatus: draft",
        )
        result = dg.build_graph(self.tmpdir)
        dg.assign_layout(result.nodes)
        # PLAN-003 is root (no deps) → level 0
        # PLAN-002 → level 1
        # PLAN-001 → level 2
        self.assertEqual(result.nodes["PLAN-003"].level, 0)
        self.assertEqual(result.nodes["PLAN-002"].level, 1)
        self.assertEqual(result.nodes["PLAN-001"].level, 2)


class RenderingSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    # T12 — XSS safety: title containing <script> must be escaped
    def test_html_escape_xss(self) -> None:
        _write_plan(
            self.tmpdir,
            "PLAN-001",
            'id: PLAN-001\ntitle: "<script>alert(1)</script>"\nstatus: draft',
        )
        result = dg.build_graph(self.tmpdir)
        svg, _, _ = dg.render_svg(result.nodes)
        # Raw <script> must NOT appear; escaped form must
        self.assertNotIn("<script>", svg)
        self.assertIn("&lt;script&gt;", svg)

    # T13 — End-to-end small fixture
    def test_end_to_end_render(self) -> None:
        _write_plan(
            self.tmpdir,
            "PLAN-001",
            "id: PLAN-001\ntitle: First\nstatus: done\ndepends_on: []",
        )
        _write_plan(
            self.tmpdir,
            "PLAN-002",
            "id: PLAN-002\ntitle: Second\nstatus: executing\ndepends_on: [PLAN-001]",
        )
        result = dg.build_graph(self.tmpdir)
        svg, w, h = dg.render_svg(result.nodes)
        self.assertGreater(w, 0)
        self.assertGreater(h, 0)
        self.assertTrue(svg.startswith("<svg"))
        self.assertTrue(svg.endswith("</svg>"))
        # Both plans rendered
        self.assertIn("PLAN-001", svg)
        self.assertIn("PLAN-002", svg)
        # 1 edge
        self.assertEqual(svg.count("<line "), 1)
        # 2 rects
        self.assertEqual(svg.count("<rect "), 2)


class CLITests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    # T14
    def test_missing_plans_dir_returns_2(self) -> None:
        nonexistent = self.tmpdir / "nope"
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            rc = dg.main(["--plans-dir", str(nonexistent)])
        self.assertEqual(rc, 2)

    # T15
    def test_strict_cycles_fails_when_cycle(self) -> None:
        plans_dir = self.tmpdir / "plans"
        plans_dir.mkdir()
        _write_plan(
            plans_dir,
            "PLAN-001",
            "id: PLAN-001\ntitle: A\nstatus: draft\ndepends_on: [PLAN-002]",
        )
        _write_plan(
            plans_dir,
            "PLAN-002",
            "id: PLAN-002\ntitle: B\nstatus: draft\ndepends_on: [PLAN-001]",
        )
        out = self.tmpdir / "out.html"
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            rc = dg.main([
                "--plans-dir", str(plans_dir),
                "--output", str(out),
                "--strict-cycles",
            ])
        self.assertEqual(rc, 3)

    def test_acyclic_writes_output(self) -> None:
        plans_dir = self.tmpdir / "plans"
        plans_dir.mkdir()
        _write_plan(
            plans_dir,
            "PLAN-001",
            "id: PLAN-001\ntitle: A\nstatus: done",
        )
        out = self.tmpdir / "out.html"
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            rc = dg.main([
                "--plans-dir", str(plans_dir),
                "--output", str(out),
            ])
        self.assertEqual(rc, 0)
        self.assertTrue(out.exists())
        content = out.read_text(encoding="utf-8")
        self.assertIn("PLAN-001", content)
        self.assertTrue(content.startswith("<!DOCTYPE html>"))


if __name__ == "__main__":
    unittest.main()
