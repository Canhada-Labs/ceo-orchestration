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

    # --- PLAN-152 economics-02: A2 unicode re-read gated + capped ---------

    def test_unicode_gate_default_off_skips_content_work(self):
        # Flag unset → _scan_read_unicode must NOT run (previously the
        # sanitize + a second uncapped full-file read ran on EVERY Read
        # for this default-OFF guard — the economics-02 hot-path cost).
        target = self._real_target()
        sys.modules["scan_injection_mod"] = _FakeScanner(
            result=_ScanResult(matched=False))
        with mock.patch.dict(os.environ,
                             {"CLAUDE_PROJECT_DIR": str(self.project_dir)}):
            os.environ.pop("CEO_UNICODE_HARDBLOCK", None)
            with mock.patch("_lib.trusted_env.get_trusted", return_value=None):
                with mock.patch.object(
                        cri, "_scan_read_unicode",
                        side_effect=AssertionError("A2 scan must not run "
                                                   "while the gate is off")):
                    rc, out = self._run_main(
                        {"tool_input": {"file_path": str(target)}})
        self.assertEqual(rc, 0)
        self.assertNotIn("systemMessage", out)

    def test_unicode_gate_enabled_scans_capped_content(self):
        # Flag set → the scan runs, and never sees more than the cap.
        target = self._real_target()
        sys.modules["scan_injection_mod"] = _FakeScanner(
            result=_ScanResult(matched=False))
        seen = {}

        def _rec(content, file_path, env=None):
            seen["len"] = len(content)
            return None

        with mock.patch.dict(os.environ,
                             {"CLAUDE_PROJECT_DIR": str(self.project_dir),
                              "CEO_UNICODE_HARDBLOCK": "1"}):
            with mock.patch("_lib.trusted_env.get_trusted", return_value=None):
                with mock.patch.object(cri, "_scan_read_unicode", _rec):
                    rc, _ = self._run_main(
                        {"tool_input": {"file_path": str(target)}})
        self.assertEqual(rc, 0)
        self.assertIn("len", seen)
        self.assertLessEqual(seen["len"], cri._UNICODE_SCAN_CAP_CHARS)

    def test_unicode_stream_covers_large_file_in_capped_chunks(self):
        # PLAN-152 round-2 (Codex release re-pass R1 finding 1): the armed
        # scan must cover the WHOLE file — the cap bounds each chunk, never
        # the total coverage. (Supersedes the "single capped scan" shape,
        # which fail-opened past the cap.)
        big = self.project_dir / "big.txt"
        total = cri._UNICODE_SCAN_CAP_CHARS + 4096
        big.write_text("a" * total, encoding="utf-8")
        sys.modules["scan_injection_mod"] = _FakeScanner(
            result=_ScanResult(matched=False))
        calls = []

        def _rec(content, file_path, env=None):
            calls.append(len(content))
            return None

        with mock.patch.dict(os.environ,
                             {"CLAUDE_PROJECT_DIR": str(self.project_dir),
                              "CEO_UNICODE_HARDBLOCK": "1"}):
            with mock.patch("_lib.trusted_env.get_trusted", return_value=None):
                with mock.patch.object(cri, "_scan_read_unicode", _rec):
                    rc, _ = self._run_main(
                        {"tool_input": {"file_path": str(big)}})
        self.assertEqual(rc, 0)
        self.assertEqual(sum(calls), total)
        self.assertTrue(
            all(n <= cri._UNICODE_SCAN_CAP_CHARS for n in calls))

    def test_unicode_hardblock_blocks_payload_past_cap(self):
        # Codex release re-pass R1 finding 1 regression: an invisible
        # payload placed AFTER the cap boundary must still block when the
        # operator armed the fail-closed guard (real helper, no scan mock).
        evil = self.project_dir / "evil.txt"
        evil.write_text(
            "a" * cri._UNICODE_SCAN_CAP_CHARS + "\u200b", encoding="utf-8")
        sys.modules["scan_injection_mod"] = _FakeScanner(
            result=_ScanResult(matched=False))
        with mock.patch.dict(os.environ,
                             {"CLAUDE_PROJECT_DIR": str(self.project_dir),
                              "CEO_UNICODE_HARDBLOCK": "1"}):
            with mock.patch("_lib.trusted_env.get_trusted", return_value=None):
                rc, out = self._run_main(
                    {"tool_input": {"file_path": str(evil)}})
        self.assertEqual(rc, 0)
        self.assertEqual(out.get("decision"), "block")

    def test_unicode_gate_helper_derivation(self):
        with mock.patch("_lib.trusted_env.get_trusted", return_value=None):
            self.assertFalse(cri._unicode_hardblock_enabled(env={}))
            self.assertFalse(cri._unicode_hardblock_enabled(
                env={"CEO_UNICODE_HARDBLOCK": "0"}))
            # Master kill wins over the armed flag.
            self.assertFalse(cri._unicode_hardblock_enabled(
                env={"CEO_UNICODE_HARDBLOCK": "1", "CEO_SOTA_DISABLE": "1"}))
            self.assertTrue(cri._unicode_hardblock_enabled(
                env={"CEO_UNICODE_HARDBLOCK": "1"}))
        # Trusted snapshot wins over the live env (mirror of the A1/§5b rule).
        with mock.patch("_lib.trusted_env.get_trusted", return_value="1"):
            self.assertTrue(cri._unicode_hardblock_enabled(env={}))
        with mock.patch("_lib.trusted_env.get_trusted", return_value="0"):
            self.assertFalse(cri._unicode_hardblock_enabled(
                env={"CEO_UNICODE_HARDBLOCK": "1"}))


if __name__ == "__main__":
    unittest.main()
