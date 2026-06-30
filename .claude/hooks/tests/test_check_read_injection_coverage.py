"""In-process coverage uplift for check_read_injection.py.

PLAN-112-FOLLOWUP-coverage-doctrine-reconcile (S157) / ADR-139 Tier-1.

The subprocess-based suite in test_check_read_injection.py exercises the
happy paths but leaves the fail-open defensive `except` branches and a
handful of early returns uncovered (they are hard to trigger through a
subprocess). These tests import the hook in-process and drive `main()` +
helpers directly, forcing each defensive branch with surgical mocks.

Contract preserved throughout: the hook ALWAYS allows (rc 0) and NEVER
raises — every branch ends in `_emit_allow(...)`.
"""

from __future__ import annotations

import io
import json
import os
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

from _lib.testing import TestEnvContext  # noqa: E402

import check_read_injection as cri  # noqa: E402


class _Match:
    def __init__(self, snippet: str = "snip"):
        self.snippet = snippet


class _ScanResult:
    def __init__(self, matched, matches=None, family_counts=None,
                 bytes_scanned=0, truncated=False):
        self.matched = matched
        self.matches = matches or []
        self.family_counts = family_counts or {}
        self.bytes_scanned = bytes_scanned
        self.truncated = truncated


class _FakeScanner:
    """Stand-in for the lazily-imported scan_injection_mod."""

    def __init__(self, result=None, raise_exc=None):
        self._result = result
        self._raise = raise_exc

    def scan_path(self, p):  # noqa: D401
        if self._raise is not None:
            raise self._raise
        return self._result


class ReadInjectionInProcessTest(TestEnvContext):
    """Drive check_read_injection.main() in-process to cover defensive paths."""

    def _run_main(self, payload, env_overrides=None):
        """Call main() with `payload` on stdin; return (rc, parsed_stdout)."""
        stdin_data = json.dumps(payload) if isinstance(payload, (dict, list)) else str(payload)
        old_stdin, old_stdout = sys.stdin, sys.stdout
        sys.stdin = io.StringIO(stdin_data)
        sys.stdout = io.StringIO()
        try:
            rc = cri.main()
            out = sys.stdout.getvalue()
        finally:
            sys.stdin, sys.stdout = old_stdin, old_stdout
        return rc, json.loads(out)

    def setUp(self):
        super().setUp()
        # Ensure no stale fake scanner leaks across tests.
        sys.modules.pop("scan_injection_mod", None)
        self.addCleanup(lambda: sys.modules.pop("scan_injection_mod", None))

    # --- helper functions ------------------------------------------------

    def test_should_skip_suffix_and_prefix(self):
        self.assertTrue(cri._should_skip("notes/changes.patch"))
        self.assertTrue(cri._should_skip("a/b.diff"))
        self.assertTrue(cri._should_skip("vendor/lib.min.js"))
        self.assertTrue(cri._should_skip("x/node_modules/y.txt"))
        self.assertTrue(cri._should_skip("third_party/z"))
        self.assertFalse(cri._should_skip("src/main.py"))

    def test_emit_allow_variants(self):
        self.assertEqual(cri._emit_allow(), "{}")
        d = json.loads(cri._emit_allow("hello"))
        self.assertEqual(d["systemMessage"], "hello")

    def test_try_emit_audit_swallows_exception(self):
        # Force the import-or-call to raise; the helper must return None.
        with mock.patch("_lib.audit_emit.emit_injection_flag",
                        side_effect=RuntimeError("boom")):
            result = cri._try_emit_audit(
                source="x", family_counts={"f": 1}, match_count=1,
                bytes_scanned=10, snippet="s", truncated=False,
            )
        self.assertIsNone(result)

    # --- main() early returns -------------------------------------------

    def test_kill_switch_short_circuits(self):
        with mock.patch.dict(os.environ, {"CEO_READ_INJECTION_SCAN": "0"}):
            rc, out = self._run_main({"tool_input": {"file_path": "anything"}})
        self.assertEqual(rc, 0)
        self.assertNotIn("systemMessage", out)

    def test_parse_error_allows(self):
        rc, out = self._run_main("not-valid-json{{{")
        self.assertEqual(rc, 0)
        self.assertNotIn("systemMessage", out)

    def test_read_event_exception_allows(self):
        with mock.patch("_lib.adapters.claude.read_event",
                        side_effect=RuntimeError("adapter down")):
            rc, out = self._run_main({"tool_input": {"file_path": "x"}})
        self.assertEqual(rc, 0)
        self.assertNotIn("systemMessage", out)

    def test_missing_file_path_allows(self):
        rc, out = self._run_main({"tool_input": {}})
        self.assertEqual(rc, 0)
        self.assertNotIn("systemMessage", out)

    def test_skip_path_allows(self):
        rc, out = self._run_main(
            {"tool_input": {"file_path": "repo/node_modules/evil.txt"}})
        self.assertEqual(rc, 0)
        self.assertNotIn("systemMessage", out)

    def test_nonexistent_file_allows(self):
        rc, out = self._run_main(
            {"tool_input": {"file_path": "/tmp/does-not-exist-987654.txt"}})
        self.assertEqual(rc, 0)
        self.assertNotIn("systemMessage", out)

    def test_outside_repo_allows(self):
        # Real file that resolves OUTSIDE CLAUDE_PROJECT_DIR -> ValueError path.
        outside = Path(self.project_dir).parent / "outside-target.txt"
        outside.write_text("hello", encoding="utf-8")
        self.addCleanup(lambda: outside.unlink(missing_ok=True))
        with mock.patch.dict(os.environ,
                             {"CLAUDE_PROJECT_DIR": str(self.project_dir)}):
            rc, out = self._run_main(
                {"tool_input": {"file_path": str(outside)}})
        self.assertEqual(rc, 0)
        self.assertNotIn("systemMessage", out)

    def test_resolve_oserror_allows(self):
        # is_file() True but resolve() raises OSError -> fail-open except.
        target = Path(self.project_dir) / "real.txt"
        target.write_text("data", encoding="utf-8")
        with mock.patch.object(cri.Path, "resolve", side_effect=OSError("nope")):
            rc, out = self._run_main(
                {"tool_input": {"file_path": str(target)}})
        self.assertEqual(rc, 0)
        self.assertNotIn("systemMessage", out)

    # --- scanner-import / scan defensive branches -----------------------

    def _real_target(self):
        target = Path(self.project_dir) / "scan-me.txt"
        target.write_text("ordinary content", encoding="utf-8")
        return target

    def test_scanner_spec_none_allows(self):
        target = self._real_target()
        with mock.patch.dict(os.environ,
                             {"CLAUDE_PROJECT_DIR": str(self.project_dir)}), \
                mock.patch("importlib.util.spec_from_file_location",
                           return_value=None):
            rc, out = self._run_main(
                {"tool_input": {"file_path": str(target)}})
        self.assertEqual(rc, 0)
        self.assertNotIn("systemMessage", out)

    def test_scanner_import_raises_allows(self):
        target = self._real_target()
        with mock.patch.dict(os.environ,
                             {"CLAUDE_PROJECT_DIR": str(self.project_dir)}), \
                mock.patch("importlib.util.spec_from_file_location",
                           side_effect=ImportError("broken")):
            rc, out = self._run_main(
                {"tool_input": {"file_path": str(target)}})
        self.assertEqual(rc, 0)
        self.assertNotIn("systemMessage", out)

    def test_scan_path_raises_allows(self):
        target = self._real_target()
        sys.modules["scan_injection_mod"] = _FakeScanner(
            raise_exc=RuntimeError("scan blew up"))
        with mock.patch.dict(os.environ,
                             {"CLAUDE_PROJECT_DIR": str(self.project_dir)}):
            rc, out = self._run_main(
                {"tool_input": {"file_path": str(target)}})
        self.assertEqual(rc, 0)
        self.assertNotIn("systemMessage", out)

    def test_clean_result_allows(self):
        target = self._real_target()
        sys.modules["scan_injection_mod"] = _FakeScanner(
            result=_ScanResult(matched=False))
        with mock.patch.dict(os.environ,
                             {"CLAUDE_PROJECT_DIR": str(self.project_dir)}):
            rc, out = self._run_main(
                {"tool_input": {"file_path": str(target)}})
        self.assertEqual(rc, 0)
        self.assertNotIn("systemMessage", out)

    def test_matched_result_emits_system_message(self):
        target = self._real_target()
        sys.modules["scan_injection_mod"] = _FakeScanner(
            result=_ScanResult(
                matched=True,
                matches=[_Match("ignore previous")],
                family_counts={"direct_override": 2, "role_injection": 1},
                bytes_scanned=42,
                truncated=False,
            ))
        with mock.patch.dict(os.environ,
                             {"CLAUDE_PROJECT_DIR": str(self.project_dir)}):
            rc, out = self._run_main(
                {"tool_input": {"file_path": str(target)},
                 "session_id": "sess-1"})
        self.assertEqual(rc, 0)
        self.assertIn("systemMessage", out)
        self.assertIn("direct_override", out["systemMessage"])


if __name__ == "__main__":
    unittest.main()
