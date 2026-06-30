"""Unit tests for confidence_gate.py (PLAN-008 Phase 2, ADR-018).

Covers:
- Grammar extraction (quoting, code-block exemption)
- All 5 verifiers (path_exists, function_exists, sha_exists, test_passes, line_range)
- Report aggregation + exit codes
- CLI argument handling
- Fail-open audit emission
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Import target module
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SCRIPTS_DIR))

import confidence_gate as cg  # noqa: E402

# Use the audit-emit TestEnvContext for env isolation in CLI-level tests
_HOOKS_DIR = _SCRIPTS_DIR.parent / "hooks"
sys.path.insert(0, str(_HOOKS_DIR))
from _lib.testing import TestEnvContext  # noqa: E402


# ---------------------------------------------------------------------------
# Grammar extraction
# ---------------------------------------------------------------------------


class TestGrammarExtraction(unittest.TestCase):
    def _extract(self, text):
        """Helper: unpack just the claims list from the tuple return."""
        claims, _raw, _trunc = cg.extract_claims(text)
        return claims

    def test_raw_arg_extracted(self):
        claims = self._extract("See CLAIM:path_exists:src/auth.py for details.")
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].kind, "path_exists")
        self.assertEqual(claims[0].args, "src/auth.py")

    def test_quoted_arg_with_colons_extracted(self):
        text = "Test CLAIM:test_passes:`tests/foo.py::test_bar` passes."
        claims = self._extract(text)
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].kind, "test_passes")
        self.assertEqual(claims[0].args, "tests/foo.py::test_bar")

    def test_fenced_code_block_is_skipped(self):
        text = "before\n```\nCLAIM:path_exists:fake.py\n```\nafter"
        claims = self._extract(text)
        self.assertEqual(claims, [])

    def test_claims_before_and_after_code_block(self):
        text = (
            "CLAIM:path_exists:a.py\n"
            "```\n"
            "CLAIM:path_exists:inside.py\n"
            "```\n"
            "CLAIM:path_exists:b.py\n"
        )
        claims = self._extract(text)
        self.assertEqual(len(claims), 2)
        self.assertEqual(claims[0].args, "a.py")
        self.assertEqual(claims[1].args, "b.py")

    def test_multiple_claims_same_line(self):
        text = "CLAIM:path_exists:a.py and CLAIM:path_exists:b.py"
        claims = self._extract(text)
        self.assertEqual(len(claims), 2)

    def test_line_numbers_recorded(self):
        text = "line1\nCLAIM:path_exists:a.py\nline3\nCLAIM:sha_exists:abc1234"
        claims = self._extract(text)
        self.assertEqual(claims[0].line_num, 2)
        self.assertEqual(claims[1].line_num, 4)

    def test_raw_arg_cannot_contain_colon(self):
        # Without quoting, the ':' terminates the arg after kind:args;
        # extractor captures only the raw (colonless) arg form.
        text = "CLAIM:test_passes:tests/foo.py::test_bar"
        claims = self._extract(text)
        # raw form stops at first whitespace/colon/backtick
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].args, "tests/foo.py")  # truncated — this is why quoting exists

    def test_indented_fence_still_toggles(self):
        text = "  ```\nCLAIM:path_exists:x.py\n  ```\n"
        claims = self._extract(text)
        self.assertEqual(claims, [])

    def test_empty_input_zero_claims(self):
        self.assertEqual(self._extract(""), [])

    def test_no_claims_in_prose(self):
        text = "This is regular text without any claims."
        self.assertEqual(self._extract(text), [])


# ---------------------------------------------------------------------------
# Verifiers (use a temp repo root)
# ---------------------------------------------------------------------------


class TestVerifiers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        # create a sample file
        (self.root / "hello.py").write_text("def hello():\n    return 1\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_path_exists_pass(self):
        ok, _ = cg.verify_path_exists("hello.py", self.root)
        self.assertTrue(ok)

    def test_path_exists_fail(self):
        ok, detail = cg.verify_path_exists("nope.py", self.root)
        self.assertFalse(ok)
        self.assertIn("not found", detail)

    def test_function_exists_pass(self):
        ok, _ = cg.verify_function_exists("hello.py:hello", self.root)
        self.assertTrue(ok)

    def test_function_exists_fail(self):
        ok, _ = cg.verify_function_exists("hello.py:missing", self.root)
        self.assertFalse(ok)

    def test_function_exists_missing_separator(self):
        ok, detail = cg.verify_function_exists("hello.py", self.root)
        self.assertFalse(ok)
        self.assertIn("separator", detail)

    def test_function_exists_parse_error_returns_false(self):
        (self.root / "broken.py").write_text("def broken(:\n  oops\n")
        ok, _ = cg.verify_function_exists("broken.py:broken", self.root)
        self.assertFalse(ok)

    def test_sha_exists_rejects_non_sha(self):
        ok, detail = cg.verify_sha_exists("not-a-sha", self.root)
        self.assertFalse(ok)
        self.assertIn("not a valid SHA format", detail)

    def test_line_range_pass(self):
        (self.root / "long.py").write_text("\n".join(f"line{i}" for i in range(50)) + "\n")
        ok, _ = cg.verify_line_range("long.py:1-20", self.root)
        self.assertTrue(ok)

    def test_line_range_fail_file_too_short(self):
        (self.root / "short.py").write_text("a\nb\n")
        ok, detail = cg.verify_line_range("short.py:1-10", self.root)
        self.assertFalse(ok)
        self.assertIn("only 2 lines", detail)

    def test_line_range_missing_separator(self):
        ok, detail = cg.verify_line_range("short.py", self.root)
        self.assertFalse(ok)

    def test_line_range_malformed_range(self):
        ok, detail = cg.verify_line_range("short.py:foo-bar", self.root)
        self.assertFalse(ok)
        self.assertIn("malformed", detail)

    def test_line_range_invalid_bounds(self):
        (self.root / "x.py").write_text("a\n")
        ok, detail = cg.verify_line_range("x.py:5-3", self.root)
        self.assertFalse(ok)
        self.assertIn("invalid", detail)

    def test_unknown_kind_marked_unsupported(self):
        claim = cg.Claim(kind="does_not_exist", args="x", raw_token="CLAIM:does_not_exist:x", line_num=1)
        result = cg.verify_claim(claim, self.root)
        self.assertFalse(result.passed)
        self.assertFalse(result.kind_supported)


# ---------------------------------------------------------------------------
# Report + exit codes (debate consensus C4)
# ---------------------------------------------------------------------------


class TestReportAndExitCodes(unittest.TestCase):
    def _make_result(self, passed: bool, kind: str = "path_exists"):
        claim = cg.Claim(kind=kind, args="x", raw_token="CLAIM:x:y", line_num=1)
        return cg.VerificationResult(claim=claim, passed=passed)

    def test_exit_0_all_pass(self):
        r = cg.Report(results=[self._make_result(True), self._make_result(True)])
        self.assertEqual(r.exit_code(), 0)

    def test_exit_1_at_least_one_fail(self):
        r = cg.Report(results=[self._make_result(True), self._make_result(False)])
        self.assertEqual(r.exit_code(), 1)

    def test_exit_3_zero_claims(self):
        r = cg.Report(results=[])
        self.assertEqual(r.exit_code(), 3)

    def test_verifier_kind_counts_aggregates(self):
        r = cg.Report(results=[
            self._make_result(True, "path_exists"),
            self._make_result(False, "path_exists"),
            self._make_result(True, "sha_exists"),
        ])
        self.assertEqual(r.verifier_kind_counts, {"path_exists": 2, "sha_exists": 1})

    def test_counts_match(self):
        r = cg.Report(results=[
            self._make_result(True), self._make_result(True), self._make_result(False),
        ])
        self.assertEqual(r.claim_count, 3)
        self.assertEqual(r.pass_count, 2)
        self.assertEqual(r.fail_count, 1)


# ---------------------------------------------------------------------------
# CLI integration (with audit emission)
# ---------------------------------------------------------------------------


class TestCLI(TestEnvContext):
    def test_stdin_zero_claims_exits_3(self):
        with patch.object(sys, "stdin", io.StringIO("no claims here")):
            rc = cg.main(["--stdin", "--no-emit"])
        self.assertEqual(rc, 3)

    def test_file_input_pass_exits_0(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "real.py").write_text("print()\n")
            input_file = root / "output.txt"
            input_file.write_text("CLAIM:path_exists:real.py\n")
            rc = cg.main([
                "--input", str(input_file),
                "--repo-root", str(root),
                "--no-emit",
            ])
        self.assertEqual(rc, 0)

    def test_file_input_fail_exits_1(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            input_file = root / "out.txt"
            input_file.write_text("CLAIM:path_exists:missing.py\n")
            rc = cg.main([
                "--input", str(input_file),
                "--repo-root", str(root),
                "--no-emit",
            ])
        self.assertEqual(rc, 1)

    def test_missing_input_file_exits_2(self):
        rc = cg.main(["--input", "/nonexistent/file.txt", "--no-emit"])
        self.assertEqual(rc, 2)

    def test_json_output_parses(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "ok.py").write_text("x = 1\n")
            input_file = root / "out.txt"
            input_file.write_text("CLAIM:path_exists:ok.py\n")
            buf = io.StringIO()
            with patch.object(sys, "stdout", buf):
                cg.main([
                    "--input", str(input_file),
                    "--repo-root", str(root),
                    "--json", "--no-emit",
                ])
            parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["claim_count"], 1)
        self.assertEqual(parsed["pass_count"], 1)
        self.assertEqual(parsed["exit_code"], 0)

    def test_emit_writes_audit_event(self):
        """End-to-end: run CLI with audit emit enabled, verify event appears."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.py").write_text("pass\n")
            input_file = root / "out.txt"
            input_file.write_text("CLAIM:path_exists:a.py\n")
            cg.main([
                "--input", str(input_file),
                "--repo-root", str(root),
                "--agent-name", "Test Agent",
            ])
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        self.assertTrue(log.exists())
        entries = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]
        cg_events = [e for e in entries if e.get("action") == "confidence_gate"]
        self.assertEqual(len(cg_events), 1)
        self.assertEqual(cg_events[0]["claim_count"], 1)
        self.assertEqual(cg_events[0]["agent_name"], "Test Agent")


# ---------------------------------------------------------------------------
# PLAN-009 C1.0 — path scoping (_scoped_resolve), pytest argv lock,
# claim volume cap. +20 tests per plan.
# ---------------------------------------------------------------------------


class TestScopedResolve(unittest.TestCase):
    """PLAN-009 A2 / R-SEC2: verifier path scoping."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        (self.root / "sub").mkdir()
        (self.root / "sub" / "inside.py").write_text("x=1\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_relative_path_anchored_under_root(self):
        p = cg._scoped_resolve("sub/inside.py", self.root)
        self.assertEqual(p, self.root / "sub" / "inside.py")

    def test_relative_dotdot_within_root_allowed(self):
        # `sub/../sub/inside.py` resolves inside root
        p = cg._scoped_resolve("sub/../sub/inside.py", self.root)
        self.assertEqual(p, self.root / "sub" / "inside.py")

    def test_rejects_dotdot_escape(self):
        with self.assertRaises(ValueError) as cm:
            cg._scoped_resolve("../../etc/passwd", self.root)
        self.assertIn("escapes", str(cm.exception))

    def test_rejects_absolute_outside(self):
        with self.assertRaises(ValueError) as cm:
            cg._scoped_resolve("/etc/passwd", self.root)
        self.assertIn("escapes", str(cm.exception))

    def test_rejects_null_byte(self):
        with self.assertRaises(ValueError):
            cg._scoped_resolve("foo\x00bar", self.root)

    def test_rejects_empty(self):
        with self.assertRaises(ValueError):
            cg._scoped_resolve("", self.root)

    def test_absolute_inside_root_allowed(self):
        abs_path = str(self.root / "sub" / "inside.py")
        p = cg._scoped_resolve(abs_path, self.root)
        self.assertEqual(p, self.root / "sub" / "inside.py")

    def test_symlink_escape_rejected(self):
        # Create a symlink inside root pointing outside
        with tempfile.TemporaryDirectory() as outside:
            outside_root = Path(outside).resolve()
            (outside_root / "secret.txt").write_text("x")
            link = self.root / "linky"
            try:
                os.symlink(outside_root / "secret.txt", link)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks not supported on this FS")
            with self.assertRaises(ValueError):
                cg._scoped_resolve("linky", self.root)


class TestPathExistsScoping(unittest.TestCase):
    """verify_path_exists routes through _scoped_resolve."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        (self.root / "ok.py").write_text("x\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_rejects_absolute_outside_path(self):
        ok, detail = cg.verify_path_exists("/etc/passwd", self.root)
        self.assertFalse(ok)
        self.assertIn("rejected", detail)

    def test_rejects_dotdot_escape(self):
        ok, detail = cg.verify_path_exists("../../../etc/passwd", self.root)
        self.assertFalse(ok)
        self.assertIn("rejected", detail)


class TestPytestArgvLock(unittest.TestCase):
    """PLAN-009 A3: strict selector regex + locked argv."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        (self.root / "test_ok.py").write_text("def test_x():\n    assert True\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_selector_with_space_rejected(self):
        ok, detail = cg.verify_test_passes("test_ok.py::test x", self.root)
        self.assertFalse(ok)
        self.assertIn("malformed", detail)

    def test_selector_with_leading_dash_rejected(self):
        ok, detail = cg.verify_test_passes("-rf", self.root)
        self.assertFalse(ok)
        self.assertIn("malformed", detail)

    def test_selector_with_double_dash_rejected(self):
        ok, detail = cg.verify_test_passes("test_ok.py::--help", self.root)
        self.assertFalse(ok)
        self.assertIn("malformed", detail)

    def test_selector_with_equals_rejected(self):
        ok, detail = cg.verify_test_passes("test_ok.py=foo", self.root)
        self.assertFalse(ok)
        self.assertIn("malformed", detail)

    def test_selector_with_three_colons_rejected(self):
        # More than 2 `::name` segments
        ok, detail = cg.verify_test_passes(
            "test_ok.py::ClassA::test_x::extra", self.root
        )
        self.assertFalse(ok)
        self.assertIn("malformed", detail)

    def test_selector_outside_root_rejected(self):
        ok, detail = cg.verify_test_passes("../other/test_x.py", self.root)
        self.assertFalse(ok)
        # either malformed (regex-wise ../ with slashes OK) or rejected by scope
        self.assertTrue("rejected" in detail or "not found" in detail or "malformed" in detail)

    def test_valid_selector_matches_regex(self):
        # Just the regex part — do not actually invoke pytest subprocess in
        # unit tests. Direct regex check.
        self.assertIsNotNone(
            cg._PYTEST_SELECTOR_RE.fullmatch("tests/foo.py::test_bar")
        )
        self.assertIsNotNone(
            cg._PYTEST_SELECTOR_RE.fullmatch("tests/foo.py::TestX::test_y")
        )

    def test_parametrized_selector_allowed(self):
        # pytest parametrize syntax uses [brackets]
        self.assertIsNotNone(
            cg._PYTEST_SELECTOR_RE.fullmatch("tests/foo.py::test_x[case-1]")
        )


class TestClaimCap(unittest.TestCase):
    """PLAN-009 A12: CEO_CONFIDENCE_MAX_CLAIMS bound."""

    def test_under_cap_not_truncated(self):
        text = "\n".join(f"CLAIM:path_exists:f{i}.py" for i in range(5))
        claims, raw, trunc = cg.extract_claims(text, max_claims=200)
        self.assertEqual(len(claims), 5)
        self.assertEqual(raw, 5)
        self.assertFalse(trunc)

    def test_at_cap_not_truncated(self):
        text = "\n".join(f"CLAIM:path_exists:f{i}.py" for i in range(10))
        claims, raw, trunc = cg.extract_claims(text, max_claims=10)
        self.assertEqual(len(claims), 10)
        self.assertEqual(raw, 10)
        self.assertFalse(trunc)

    def test_over_cap_truncated_with_raw_count(self):
        text = "\n".join(f"CLAIM:path_exists:f{i}.py" for i in range(250))
        claims, raw, trunc = cg.extract_claims(text, max_claims=200)
        self.assertEqual(len(claims), 200)
        self.assertEqual(raw, 250)
        self.assertTrue(trunc)

    def test_env_var_override(self):
        text = "\n".join(f"CLAIM:path_exists:f{i}.py" for i in range(20))
        # Set env var to 5; extract_claims should read it when max_claims=None
        old = os.environ.get("CEO_CONFIDENCE_MAX_CLAIMS")
        os.environ["CEO_CONFIDENCE_MAX_CLAIMS"] = "5"
        try:
            claims, raw, trunc = cg.extract_claims(text)
        finally:
            if old is None:
                os.environ.pop("CEO_CONFIDENCE_MAX_CLAIMS", None)
            else:
                os.environ["CEO_CONFIDENCE_MAX_CLAIMS"] = old
        self.assertEqual(len(claims), 5)
        self.assertEqual(raw, 20)
        self.assertTrue(trunc)

    def test_invalid_env_var_falls_back_to_default(self):
        old = os.environ.get("CEO_CONFIDENCE_MAX_CLAIMS")
        os.environ["CEO_CONFIDENCE_MAX_CLAIMS"] = "garbage"
        try:
            self.assertEqual(cg._get_max_claims(), 200)
        finally:
            if old is None:
                os.environ.pop("CEO_CONFIDENCE_MAX_CLAIMS", None)
            else:
                os.environ["CEO_CONFIDENCE_MAX_CLAIMS"] = old

    def test_report_carries_truncated_flag(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            text = "\n".join(f"CLAIM:path_exists:f{i}.py" for i in range(15))
            old = os.environ.get("CEO_CONFIDENCE_MAX_CLAIMS")
            os.environ["CEO_CONFIDENCE_MAX_CLAIMS"] = "5"
            try:
                report = cg.verify_text(text, root)
            finally:
                if old is None:
                    os.environ.pop("CEO_CONFIDENCE_MAX_CLAIMS", None)
                else:
                    os.environ["CEO_CONFIDENCE_MAX_CLAIMS"] = old
            self.assertEqual(report.claim_count, 5)
            self.assertEqual(report.raw_claim_count, 15)
            self.assertTrue(report.truncated)


# ---------------------------------------------------------------------------
# PLAN-009 C1.2 — import_resolves kind (ADR-018 v1.1, syntactic-only).
# Zero importlib calls. +5 tests per plan.
# ---------------------------------------------------------------------------


class TestImportResolves(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        (self.root / "mymodule.py").write_text("x = 1\n")
        (self.root / "mypkg").mkdir()
        (self.root / "mypkg" / "__init__.py").write_text("y = 2\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_module_file_resolves(self):
        ok, detail = cg.verify_import_resolves("mymodule", self.root)
        self.assertTrue(ok)
        self.assertIn("module", detail)

    def test_package_init_resolves(self):
        ok, detail = cg.verify_import_resolves("mypkg", self.root)
        self.assertTrue(ok)
        self.assertIn("package", detail)

    def test_nonexistent_fails(self):
        ok, detail = cg.verify_import_resolves("nowhere", self.root)
        self.assertFalse(ok)
        self.assertIn("not found", detail)

    def test_relative_import_rejected(self):
        ok, detail = cg.verify_import_resolves(".mymodule", self.root)
        self.assertFalse(ok)
        self.assertIn("relative", detail)

    def test_filesystem_path_rejected(self):
        ok, detail = cg.verify_import_resolves("path/to/mod", self.root)
        self.assertFalse(ok)
        self.assertIn("filesystem", detail)

    def test_invalid_syntax_rejected(self):
        ok, detail = cg.verify_import_resolves("1bad", self.root)
        self.assertFalse(ok)
        self.assertIn("syntax invalid", detail)

    def test_block_list_os_rejected(self):
        ok, detail = cg.verify_import_resolves("os", self.root)
        self.assertFalse(ok)
        self.assertIn("block-listed", detail)

    def test_block_list_subprocess_rejected(self):
        ok, detail = cg.verify_import_resolves("subprocess.run", self.root)
        self.assertFalse(ok)
        self.assertIn("block-listed", detail)

    def test_dunder_rejected(self):
        ok, detail = cg.verify_import_resolves("__main__", self.root)
        self.assertFalse(ok)
        self.assertIn("block-listed", detail)

    def test_verifier_registered(self):
        self.assertIn("import_resolves", cg.KNOWN_KINDS)
        self.assertIn("import_resolves", cg.VERIFIERS)

    def test_no_importlib_usage(self):
        """Defense-in-depth: confirm no find_spec / import_module CALL sites.

        Check for call-site patterns (``name(``) rather than bare names,
        so docstring references explaining the RCE sink don't trigger
        false positives.
        """
        src = Path(cg.__file__).read_text(encoding="utf-8")
        self.assertNotIn("find_spec(", src)
        self.assertNotIn("import_module(", src)
        # Also confirm there's no `from importlib import util` or
        # `import importlib.util` statement.
        import re as _re
        self.assertFalse(
            _re.search(r"^\s*(?:from\s+importlib\b|import\s+importlib\b)", src, _re.MULTILINE),
            "importlib must not be imported",
        )


if __name__ == "__main__":
    unittest.main()
