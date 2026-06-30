"""PLAN-046 Cluster 1.4 — code_nav_bridge tests."""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_SCRIPT = _REPO_ROOT / ".claude" / "scripts" / "mcp" / "code_nav_bridge.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("code_nav_bridge", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    # Register in sys.modules before exec so @dataclass introspection
    # resolves `cls.__module__` without hitting NoneType in
    # dataclasses.py:660 on Python 3.9.
    sys.modules["code_nav_bridge"] = mod
    spec.loader.exec_module(mod)
    return mod


_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
from _lib.testing import TestEnvContext  # noqa: E402


class _FixtureBase(TestEnvContext):
    """Shared fixture setup: tmp project with sample Python + TypeScript files."""

    def setUp(self) -> None:
        super().setUp()
        self.mod = _load_module()
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: _rmtree(self.tmp))

        # Python sample
        (self.tmp / "src").mkdir()
        (self.tmp / "src" / "a.py").write_text(
            "def foo():\n    return 1\n\n"
            "class Bar:\n    def baz(self):\n        foo()\n        return 2\n",
            encoding="utf-8",
        )
        (self.tmp / "src" / "b.py").write_text(
            "from .a import foo\n\n"
            "def quux():\n    return foo() + 1\n",
            encoding="utf-8",
        )
        # TypeScript sample
        (self.tmp / "src" / "c.ts").write_text(
            "export function helper() { return 42; }\n"
            "export class Widget {\n  render() { return helper(); }\n}\n",
            encoding="utf-8",
        )
        # Ignored dir (node_modules)
        (self.tmp / "node_modules").mkdir()
        (self.tmp / "node_modules" / "junk.js").write_text(
            "function junk() {}\n", encoding="utf-8"
        )

        self.bridge = self.mod.CodeNavBridge(self.tmp, backend="stdlib")


class CodeNavRegexScanTest(_FixtureBase):

    def test_scan_python_captures_def_and_class(self) -> None:
        syms = self.mod._scan_file_stdlib(self.tmp / "src" / "a.py")
        names = [s.name for s in syms]
        self.assertIn("foo", names)
        self.assertIn("Bar", names)
        self.assertIn("baz", names)

    def test_scan_typescript_captures_export_shapes(self) -> None:
        syms = self.mod._scan_file_stdlib(self.tmp / "src" / "c.ts")
        names = [s.name for s in syms]
        self.assertIn("helper", names)
        self.assertIn("Widget", names)

    def test_scan_returns_empty_on_missing_file(self) -> None:
        syms = self.mod._scan_file_stdlib(self.tmp / "does-not-exist.py")
        self.assertEqual(syms, [])

    def test_kind_normalize_known_values(self) -> None:
        self.assertEqual(self.mod._kind_normalize("def"), "function")
        self.assertEqual(self.mod._kind_normalize("async def"), "function")
        self.assertEqual(self.mod._kind_normalize("class"), "class")
        self.assertEqual(self.mod._kind_normalize("interface"), "interface")
        self.assertEqual(self.mod._kind_normalize("anythingelse"), "unknown")

    def test_scan_records_line_numbers(self) -> None:
        syms = self.mod._scan_file_stdlib(self.tmp / "src" / "a.py")
        by_name = {s.name: s for s in syms}
        self.assertEqual(by_name["foo"].location.line, 1)
        self.assertEqual(by_name["Bar"].location.line, 4)


class CodeNavBridgeQueryTest(_FixtureBase):

    def test_find_definition_finds_python_symbol(self) -> None:
        locs = self.bridge.find_definition("foo")
        self.assertTrue(any("a.py" in l.path for l in locs))

    def test_find_definition_finds_typescript_symbol(self) -> None:
        locs = self.bridge.find_definition("helper")
        self.assertTrue(any("c.ts" in l.path for l in locs))

    def test_find_definition_empty_for_unknown(self) -> None:
        self.assertEqual(self.bridge.find_definition("does_not_exist"), [])

    def test_find_definition_empty_for_empty_query(self) -> None:
        self.assertEqual(self.bridge.find_definition(""), [])

    def test_find_references_includes_call_sites(self) -> None:
        refs = self.bridge.find_references("foo")
        # At least 3 references: a.py def, a.py call inside Bar.baz, b.py import/call
        self.assertGreaterEqual(len(refs), 3)

    def test_find_references_empty_for_empty_query(self) -> None:
        self.assertEqual(self.bridge.find_references(""), [])

    def test_list_symbols_returns_file_symbols(self) -> None:
        syms = self.bridge.list_symbols("src/a.py")
        names = [s.name for s in syms]
        self.assertIn("foo", names)
        self.assertIn("Bar", names)

    def test_list_symbols_rejects_escape_path(self) -> None:
        self.assertEqual(self.bridge.list_symbols("../../etc/passwd"), [])

    def test_list_symbols_empty_for_missing_file(self) -> None:
        self.assertEqual(self.bridge.list_symbols("src/missing.py"), [])

    def test_iter_source_files_skips_node_modules(self) -> None:
        paths = self.bridge._iter_source_files()
        pathstrs = [str(p) for p in paths]
        self.assertTrue(all("node_modules" not in ps for ps in pathstrs))

    def test_unknown_backend_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.mod.CodeNavBridge(self.tmp, backend="galaxy-brain")

    def test_cache_is_populated_after_scan(self) -> None:
        self.bridge.list_symbols("src/a.py")
        self.assertTrue(any(
            "a.py" in k for k in self.bridge._cache_scan.keys()
        ))


class DataClassTest(_FixtureBase):

    def test_location_as_dict(self) -> None:
        loc = self.mod.Location(path="x.py", line=3, col=2)
        self.assertEqual(
            loc.as_dict(), {"path": "x.py", "line": 3, "col": 2},
        )

    def test_symbol_as_dict(self) -> None:
        sym = self.mod.Symbol(
            name="foo", kind="function",
            location=self.mod.Location(path="a.py", line=1, col=0),
        )
        d = sym.as_dict()
        self.assertEqual(d["name"], "foo")
        self.assertEqual(d["kind"], "function")
        self.assertEqual(d["location"]["line"], 1)


class TreeSitterFallbackTest(_FixtureBase):

    def test_tree_sitter_backend_falls_back_to_stdlib(self) -> None:
        """When tree-sitter is absent, _scan_tree_sitter uses stdlib scan."""
        bridge = self.mod.CodeNavBridge(self.tmp, backend="tree_sitter")
        syms = bridge.list_symbols("src/a.py")
        names = [s.name for s in syms]
        self.assertIn("foo", names)


def _rmtree(path: Path) -> None:
    import shutil
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
