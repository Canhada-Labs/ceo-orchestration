#!/usr/bin/env python3
"""Tests for `.claude/scripts/check-function-length.py`.

Covers:
- function-LoC counter accuracy (def + body inclusive)
- justification detection (matching, length floor, multiple-comments)
- exclude flags (defaults + --exclude fragment)
- exit codes (advisory vs --strict)
- text + JSON output shapes
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List


_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "check-function-length.py"

# Reuse TestEnvContext from hooks/_lib so env-hygiene check stays green.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402


def _load_script_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "check_function_length", str(_SCRIPT_PATH))
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_function_length"] = module
    spec.loader.exec_module(module)
    return module


class TestFunctionLengthDetector(TestEnvContext):
    """Functional tests against synthetic Python files."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.mod = _load_script_module()

    def _write_tree(self, files: Dict[str, str]) -> Path:
        td = Path(tempfile.mkdtemp(prefix="ceo-flen-"))
        for rel, content in files.items():
            p = td / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        return td

    def test_counts_function_loc_inclusive_def_to_end(self) -> None:
        src = (
            "def short():\n"
            "    return 1\n"
            "\n"
            "def medium():\n"
            "    a = 1\n"
            "    b = 2\n"
            "    c = 3\n"
            "    return a + b + c\n"
        )
        root = self._write_tree({"src.py": src})
        records = self.mod._scan_file(root / "src.py")
        names = {r["function"]: r["loc"] for r in records}
        self.assertEqual(names["short"], 2)
        self.assertEqual(names["medium"], 5)

    def test_justification_detected_with_min_reason(self) -> None:
        src = (
            "def big():\n"
            "    # justified: needs full state-machine in one place\n"
            "    return 1\n"
        )
        root = self._write_tree({"src.py": src})
        recs = self.mod._scan_file(root / "src.py")
        self.assertTrue(recs[0]["justified"])

    def test_justification_too_short_not_accepted(self) -> None:
        src = (
            "def big():\n"
            "    # justified: x\n"
            "    return 1\n"
        )
        root = self._write_tree({"src.py": src})
        recs = self.mod._scan_file(root / "src.py")
        self.assertFalse(recs[0]["justified"])

    def test_excludes_default_path_fragments(self) -> None:
        src = "def f():\n    return 1\n"
        root = self._write_tree({
            "good.py": src,
            "PLAN-001/staged-code/bad.py": src,
            "PLAN-002/staged-wave-c/extra.py": src,
            "PLAN-003/audit-v2/staged-wave-c-bis/skip.py": src,
        })
        files = self.mod._walk_python_files(root)
        rel = sorted(p.relative_to(root).as_posix() for p in files)
        self.assertEqual(rel, ["good.py"])

    def test_excludes_extra_fragment_via_flag(self) -> None:
        src = "def f():\n    return 1\n"
        root = self._write_tree({
            "good.py": src,
            "vendor/third_party/util.py": src,
        })
        files = self.mod._walk_python_files(root,
                                            extra_excludes=["/vendor/"])
        rel = sorted(p.relative_to(root).as_posix() for p in files)
        self.assertEqual(rel, ["good.py"])

    def test_filter_violations_threshold(self) -> None:
        records = [
            {"file": "a.py", "function": "f1", "loc": 30, "justified": False,
             "line": 1, "end_line": 30},
            {"file": "a.py", "function": "f2", "loc": 60, "justified": False,
             "line": 1, "end_line": 60},
            {"file": "a.py", "function": "f3", "loc": 60, "justified": True,
             "line": 1, "end_line": 60},
        ]
        v = self.mod._filter_violations(records, threshold=50)
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0]["function"], "f2")

    def test_main_advisory_exit_zero_with_violations(self) -> None:
        src = "def big():\n" + "    x = 0\n" * 60 + "    return x\n"
        root = self._write_tree({"src.py": src})
        rc = self.mod.main([
            "--root", str(root),
            "--threshold", "50",
        ])
        self.assertEqual(rc, 0)

    def test_main_strict_exit_one_with_violations(self) -> None:
        src = "def big():\n" + "    x = 0\n" * 60 + "    return x\n"
        root = self._write_tree({"src.py": src})
        rc = self.mod.main([
            "--root", str(root),
            "--threshold", "50",
            "--strict",
        ])
        self.assertEqual(rc, 1)

    def test_main_strict_exit_zero_when_clean(self) -> None:
        src = "def small():\n    return 1\n"
        root = self._write_tree({"src.py": src})
        rc = self.mod.main([
            "--root", str(root),
            "--threshold", "50",
            "--strict",
        ])
        self.assertEqual(rc, 0)

    def test_main_root_must_be_directory(self) -> None:
        td = Path(tempfile.mkdtemp(prefix="ceo-flen-"))
        bogus = td / "does_not_exist"
        rc = self.mod.main(["--root", str(bogus)])
        self.assertEqual(rc, 2)

    def test_json_output_shape(self) -> None:
        import io
        from contextlib import redirect_stdout

        src = "def big():\n" + "    x = 0\n" * 60 + "    return x\n"
        root = self._write_tree({"src.py": src})
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.mod.main([
                "--root", str(root),
                "--threshold", "50",
                "--json",
            ])
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["threshold"], 50)
        self.assertGreaterEqual(payload["total_functions"], 1)
        self.assertEqual(payload["violations"], 1)
        self.assertEqual(payload["items"][0]["function"], "big")

    def test_async_function_also_counted(self) -> None:
        src = (
            "async def big():\n"
            + "    x = 0\n" * 60
            + "    return x\n"
        )
        root = self._write_tree({"src.py": src})
        recs = self.mod._scan_file(root / "src.py")
        names = {r["function"]: r["loc"] for r in recs}
        self.assertIn("big", names)
        self.assertGreater(names["big"], 50)

    def test_nested_function_scanned_independently(self) -> None:
        src = (
            "def outer():\n"
            + "    def inner():\n"
            + "        return 1\n"
            + "    return inner()\n"
        )
        root = self._write_tree({"src.py": src})
        recs = self.mod._scan_file(root / "src.py")
        names = {r["function"]: r["loc"] for r in recs}
        self.assertIn("outer", names)
        self.assertIn("inner", names)
        self.assertEqual(names["inner"], 2)

    def test_syntax_error_file_skipped_silently(self) -> None:
        src = "def f(:\n    return 1\n"  # invalid
        root = self._write_tree({"src.py": src})
        recs = self.mod._scan_file(root / "src.py")
        self.assertEqual(recs, [])


class TestGrandfatherList(TestEnvContext):
    """Coverage for `_load_grandfather` + grandfather-aware filtering
    (PLAN-044 audit-v2 P1 #11 closure / ADR-097)."""

    def setUp(self) -> None:
        super().setUp()
        self.mod = _load_script_module()

    def _write_tree(self, files: Dict[str, str]) -> Path:
        root = self.project_dir / "tree"
        root.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            p = root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        return root

    def _write_grandfather(self, entries: List[Dict[str, Any]]) -> Path:
        path = self.project_dir / "grandfather.yaml"
        lines = [
            "schema: function-length-grandfather/v1",
            'generated_at: "2026-04-29"',
            "adr: ADR-097",
            f"total_grandfathered: {len(entries)}",
            "",
            "functions:",
        ]
        for e in entries:
            lines.append(f"  - file: {e['file']}")
            lines.append(f"    function: {e['function']}")
            lines.append(f"    line: {e['line']}")
            lines.append(f"    end_line: {e.get('end_line', e['line'] + 50)}")
            lines.append(f"    loc: {e.get('loc', 60)}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def test_load_grandfather_reads_entries(self) -> None:
        # PLAN-063 DIM-07: _load_grandfather returns (v1_keys, v2_keys).
        # v1 schema input → v1_keys populated, v2_keys empty.
        gf = self._write_grandfather([
            {"file": "a.py", "function": "f1", "line": 10},
            {"file": "b/c.py", "function": "f2", "line": 20},
        ])
        v1_keys, v2_keys = self.mod._load_grandfather(gf)
        self.assertEqual(len(v1_keys), 2)
        self.assertEqual(len(v2_keys), 0)
        self.assertIn(("a.py", "f1", 10), v1_keys)
        self.assertIn(("b/c.py", "f2", 20), v1_keys)

    def test_load_grandfather_missing_file_returns_empty_set(self) -> None:
        v1_keys, v2_keys = self.mod._load_grandfather(
            self.project_dir / "missing.yaml"
        )
        self.assertEqual(v1_keys, set())
        self.assertEqual(v2_keys, set())

    def test_load_grandfather_skips_comments_and_blank_lines(self) -> None:
        path = self.project_dir / "with-comments.yaml"
        path.write_text(
            "# comment line\n"
            "\n"
            "schema: function-length-grandfather/v1\n"
            "functions:\n"
            "  - file: x.py\n"
            "    function: ff\n"
            "    line: 5\n"
            "    end_line: 60\n"
            "    loc: 56\n",
            encoding="utf-8",
        )
        v1_keys, v2_keys = self.mod._load_grandfather(path)
        self.assertEqual(v1_keys, {("x.py", "ff", 5)})
        self.assertEqual(v2_keys, set())

    def test_grandfathered_function_is_not_a_violation(self) -> None:
        """Existing >50-LoC function listed in grandfather → exempt."""
        src = (
            "def big_legacy():\n"
            + "    x = 0\n" * 60
            + "    return x\n"
        )
        root = self._write_tree({"legacy.py": src})
        recs = self.mod._scan_file(root / "legacy.py")
        # Without grandfather: 1 violation.
        viol_no_gf = self.mod._filter_violations(recs, threshold=50)
        self.assertEqual(len(viol_no_gf), 1)
        # With grandfather v1 (legacy line-keyed) including this exact
        # (file, function, line):
        gf_v1 = {(str(root / "legacy.py"), "big_legacy", recs[0]["line"])}
        viol_with_gf = self.mod._filter_violations(
            recs, threshold=50, grandfather_v1=gf_v1
        )
        self.assertEqual(len(viol_with_gf), 0)

    def test_new_function_not_in_grandfather_still_violates(self) -> None:
        """Function NOT in grandfather still flagged."""
        src = (
            "def new_legacy():\n"
            + "    y = 0\n" * 70
            + "    return y\n"
        )
        root = self._write_tree({"new.py": src})
        recs = self.mod._scan_file(root / "new.py")
        # Grandfather has DIFFERENT function name.
        gf_v1 = {(str(root / "new.py"), "old_legacy", 1)}
        viol = self.mod._filter_violations(
            recs, threshold=50, grandfather_v1=gf_v1
        )
        self.assertEqual(len(viol), 1)
        self.assertEqual(viol[0]["function"], "new_legacy")

    def test_justified_takes_precedence_over_grandfather(self) -> None:
        """A function with `# justified:` is exempt regardless of GF."""
        src = (
            "def big_with_just():\n"
            + "    # justified: cyclomatic complexity bound\n"
            + "    x = 0\n" * 60
            + "    return x\n"
        )
        root = self._write_tree({"both.py": src})
        recs = self.mod._scan_file(root / "both.py")
        viol = self.mod._filter_violations(
            recs, threshold=50, grandfather_v1=set()
        )
        self.assertEqual(len(viol), 0)

    # --- PLAN-063 DIM-07 — v2 (sha256-keyed) tests ----------------------

    def test_load_grandfather_v2_reads_sha256_entries(self) -> None:
        """v2 schema with sha256 field populates v2_keys (not v1_keys)."""
        path = self.project_dir / "v2.yaml"
        path.write_text(
            "schema: function-length-grandfather/v2\n"
            "functions:\n"
            "  - file: x.py\n"
            "    function: ff\n"
            "    line: 5\n"
            "    end_line: 60\n"
            "    loc: 56\n"
            "    sha256: deadbeef00000000000000000000000000000000000000000000000000000000\n",
            encoding="utf-8",
        )
        v1_keys, v2_keys = self.mod._load_grandfather(path)
        # v1 also populated because line is present (forward-compat).
        # v2 populated because sha256 is present.
        self.assertIn(
            ("x.py", "ff",
             "deadbeef00000000000000000000000000000000000000000000000000000000"),
            v2_keys,
        )

    def test_v2_grandfather_matches_by_sha256_after_line_shift(self) -> None:
        """v2 sha256 lookup is line-shift invariant."""
        # Original function at line 1.
        src_v1 = (
            "def big_legacy():\n"
            + "    x = 0\n" * 60
            + "    return x\n"
        )
        root = self._write_tree({"legacy.py": src_v1})
        recs_v1 = self.mod._scan_file(root / "legacy.py")
        sha = recs_v1[0]["sha256"]
        # Now shift the function down by 5 lines (unrelated edit above).
        src_v2 = "# preamble\n" * 5 + src_v1
        (root / "legacy.py").write_text(src_v2, encoding="utf-8")
        recs_v2 = self.mod._scan_file(root / "legacy.py")
        # v2 sha256 should be identical (body unchanged).
        self.assertEqual(recs_v2[0]["sha256"], sha)
        # v2-keyed grandfather still matches.
        gf_v2 = {(str(root / "legacy.py"), "big_legacy", sha)}
        viol = self.mod._filter_violations(
            recs_v2, threshold=50, grandfather_v2=gf_v2
        )
        self.assertEqual(len(viol), 0)

    def test_v1_grandfather_breaks_after_line_shift(self) -> None:
        """v1 line-keyed lookup fails after line shift (proves DIM-07)."""
        src_v1 = (
            "def legacy():\n"
            + "    x = 0\n" * 60
            + "    return x\n"
        )
        root = self._write_tree({"x.py": src_v1})
        recs_v1 = self.mod._scan_file(root / "x.py")
        original_line = recs_v1[0]["line"]
        # Shift function down by 5 lines.
        (root / "x.py").write_text(
            "# preamble\n" * 5 + src_v1, encoding="utf-8"
        )
        recs_v2 = self.mod._scan_file(root / "x.py")
        # v1 grandfather using OLD line — no longer matches.
        gf_v1 = {(str(root / "x.py"), "legacy", original_line)}
        viol = self.mod._filter_violations(
            recs_v2, threshold=50, grandfather_v1=gf_v1
        )
        # v1 line lookup fails — function appears as "new" violation.
        self.assertEqual(len(viol), 1)

    def test_v2_takes_precedence_over_v1(self) -> None:
        """When both v1 and v2 keys present, v2 sha256 match is preferred."""
        src = (
            "def big():\n"
            + "    x = 0\n" * 60
            + "    return x\n"
        )
        root = self._write_tree({"x.py": src})
        recs = self.mod._scan_file(root / "x.py")
        # v1 has a non-matching line; v2 has matching sha256.
        gf_v1 = {(str(root / "x.py"), "big", 9999)}
        gf_v2 = {(str(root / "x.py"), "big", recs[0]["sha256"])}
        viol = self.mod._filter_violations(
            recs, threshold=50,
            grandfather_v1=gf_v1, grandfather_v2=gf_v2,
        )
        self.assertEqual(len(viol), 0)  # v2 hit short-circuits

    def test_scan_emits_sha256_field(self) -> None:
        """_scan_file output includes a sha256 hex string per record."""
        src = (
            "def f():\n"
            + "    return 1\n"
        )
        root = self._write_tree({"x.py": src})
        recs = self.mod._scan_file(root / "x.py")
        self.assertEqual(len(recs), 1)
        sha = recs[0].get("sha256")
        self.assertIsNotNone(sha)
        self.assertEqual(len(sha), 64)
        # Hex characters only.
        int(sha, 16)  # raises if non-hex


class TestGrandfatherIntegration(TestEnvContext):
    """End-to-end: grandfather list applied via main(--grandfather=...)."""

    def setUp(self) -> None:
        super().setUp()
        self.mod = _load_script_module()

    def test_main_with_disabled_grandfather_flags_legacy(self) -> None:
        import io
        from contextlib import redirect_stdout

        src = (
            "def legacy():\n"
            + "    x = 0\n" * 60
            + "    return x\n"
        )
        root = self.project_dir / "src"
        root.mkdir()
        (root / "x.py").write_text(src, encoding="utf-8")
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.mod.main([
                "--root", str(root),
                "--threshold", "50",
                "--json",
                "--grandfather", "/dev/null",
            ])
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["violations"], 1)

    def test_main_with_grandfather_exempts_legacy(self) -> None:
        import io
        from contextlib import redirect_stdout

        src = (
            "def legacy():\n"
            + "    x = 0\n" * 60
            + "    return x\n"
        )
        root = self.project_dir / "src"
        root.mkdir()
        target = root / "x.py"
        target.write_text(src, encoding="utf-8")

        # Build grandfather entry for the function.
        recs = self.mod._scan_file(target)
        legacy_rec = recs[0]
        gf_path = self.project_dir / "gf.yaml"
        gf_path.write_text(
            "schema: function-length-grandfather/v1\n"
            "functions:\n"
            f"  - file: {legacy_rec['file']}\n"
            f"    function: legacy\n"
            f"    line: {legacy_rec['line']}\n"
            f"    end_line: {legacy_rec['end_line']}\n"
            f"    loc: {legacy_rec['loc']}\n",
            encoding="utf-8",
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.mod.main([
                "--root", str(root),
                "--threshold", "50",
                "--json",
                "--grandfather", str(gf_path),
            ])
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["violations"], 0)


if __name__ == "__main__":
    unittest.main()
