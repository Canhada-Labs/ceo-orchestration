"""Tests for .claude/hooks/_lib/rag_events.py (PLAN-041 Phase 5 / ADR-062).

The emitters wrap `_lib.audit_emit.emit_generic`. Tests verify:
1. Each emitter calls emit_generic with the correct action name
2. Each emitter never raises, even on import failure
3. Field types are coerced correctly (int/str coercion for safety)
4. Fail-open: emit_generic ImportError → silent return

Note: until the arbitration-kernel batch registers the 5 action types
in audit_emit._KNOWN_ACTIONS, emit_generic silently drops unknown
actions. These tests verify the emitter CONTRACT (arguments reach
emit_generic), not the end-to-end log write. End-to-end is covered
post-registration by `test_audit_emit_coverage.py` extension.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_HOOKS_DIR = Path(__file__).resolve().parents[1]

from _lib import rag_events  # type: ignore  # noqa: E402


class _MockEmitter:
    def __init__(self):
        self.calls = []

    def __call__(self, *args, **kwargs):
        # Capture kwargs only (emit_generic takes action as kw + arbitrary **kw)
        self.calls.append(dict(kwargs))


class TestEmitRagQueryIssued(unittest.TestCase):
    def test_forwards_to_emit_generic_with_correct_action(self) -> None:
        mock = _MockEmitter()
        with patch("_lib.audit_emit.emit_generic", mock):
            rag_events.emit_rag_query_issued(
                method="rag.search",
                timeout_ms=5000,
                session_id="sess-1",
            )
        self.assertEqual(len(mock.calls), 1)
        call = mock.calls[0]
        self.assertEqual(call["action"], "rag_query_issued")
        self.assertEqual(call["method"], "rag.search")
        self.assertEqual(call["timeout_ms"], 5000)
        self.assertEqual(call["session_id"], "sess-1")
        self.assertIn("project", call)
        self.assertIn("bridge_version", call)

    def test_timeout_coerced_to_int(self) -> None:
        mock = _MockEmitter()
        with patch("_lib.audit_emit.emit_generic", mock):
            rag_events.emit_rag_query_issued(
                method="rag.search", timeout_ms=5000.7,  # type: ignore[arg-type]
            )
        self.assertEqual(mock.calls[0]["timeout_ms"], 5000)

    def test_never_raises_on_import_error(self) -> None:
        preserved = {}
        for k in list(sys.modules.keys()):
            if k == "_lib" or k.startswith("_lib."):
                preserved[k] = sys.modules[k]
                sys.modules[k] = None
        try:
            # Should not raise — fail-open
            rag_events.emit_rag_query_issued(method="x", timeout_ms=100)
        finally:
            for k, v in preserved.items():
                sys.modules[k] = v


class TestEmitRagQueryReturned(unittest.TestCase):
    def test_forwards_correctly(self) -> None:
        mock = _MockEmitter()
        with patch("_lib.audit_emit.emit_generic", mock):
            rag_events.emit_rag_query_returned(
                method="rag.search",
                chunks_returned=5,
                chunks_dropped=2,
            )
        self.assertEqual(mock.calls[0]["action"], "rag_query_returned")
        self.assertEqual(mock.calls[0]["chunks_returned"], 5)
        self.assertEqual(mock.calls[0]["chunks_dropped"], 2)

    def test_defaults(self) -> None:
        mock = _MockEmitter()
        with patch("_lib.audit_emit.emit_generic", mock):
            rag_events.emit_rag_query_returned(method="rag.health")
        self.assertEqual(mock.calls[0]["chunks_returned"], 0)
        self.assertEqual(mock.calls[0]["chunks_dropped"], 0)


class TestEmitRagQueryFallback(unittest.TestCase):
    def test_reason_required(self) -> None:
        mock = _MockEmitter()
        with patch("_lib.audit_emit.emit_generic", mock):
            rag_events.emit_rag_query_fallback(
                method="rag.search",
                reason="timeout",
            )
        self.assertEqual(mock.calls[0]["action"], "rag_query_fallback")
        self.assertEqual(mock.calls[0]["reason"], "timeout")

    def test_rpc_error_code_optional(self) -> None:
        mock = _MockEmitter()
        with patch("_lib.audit_emit.emit_generic", mock):
            rag_events.emit_rag_query_fallback(
                method="rag.search",
                reason="rpc_error",
                rpc_error_code=-32601,
            )
        self.assertEqual(mock.calls[0]["rpc_error_code"], -32601)

    def test_rpc_error_code_omitted_when_none(self) -> None:
        mock = _MockEmitter()
        with patch("_lib.audit_emit.emit_generic", mock):
            rag_events.emit_rag_query_fallback(
                method="rag.search",
                reason="socket_missing",
            )
        self.assertNotIn("rpc_error_code", mock.calls[0])


class TestEmitRagQueryRedacted(unittest.TestCase):
    def test_family_counts_coerced(self) -> None:
        mock = _MockEmitter()
        with patch("_lib.audit_emit.emit_generic", mock):
            rag_events.emit_rag_query_redacted(
                chunk_keys=["file", "snippet"],
                family_counts={"LLM01_prompt_injection": 2},
            )
        self.assertEqual(mock.calls[0]["action"], "rag_query_redacted")
        self.assertEqual(mock.calls[0]["family_counts"], {"LLM01_prompt_injection": 2})

    def test_handles_none_family_counts(self) -> None:
        mock = _MockEmitter()
        with patch("_lib.audit_emit.emit_generic", mock):
            rag_events.emit_rag_query_redacted(
                chunk_keys=[], family_counts={},
            )
        self.assertEqual(mock.calls[0]["family_counts"], {})


class TestEmitRagIndexRedacted(unittest.TestCase):
    def test_forwards_correctly(self) -> None:
        mock = _MockEmitter()
        with patch("_lib.audit_emit.emit_generic", mock):
            rag_events.emit_rag_index_redacted(
                file_path=".env.production",
                reason="LLM06_sensitive_info",
                family_counts={"LLM06_sensitive_info": 1},
            )
        self.assertEqual(mock.calls[0]["action"], "rag_index_redacted")
        self.assertEqual(mock.calls[0]["file_path"], ".env.production")
        self.assertEqual(mock.calls[0]["reason"], "LLM06_sensitive_info")

    def test_family_counts_none_defaults_empty(self) -> None:
        mock = _MockEmitter()
        with patch("_lib.audit_emit.emit_generic", mock):
            rag_events.emit_rag_index_redacted(
                file_path="x.py",
                reason="tag_character",
            )
        self.assertEqual(mock.calls[0]["family_counts"], {})


class TestEmitFailOpen(unittest.TestCase):
    """Every emitter must swallow exceptions silently."""

    def test_all_emitters_fail_open_on_missing_emit_generic(self) -> None:
        import _lib.audit_emit as ae

        saved = ae.emit_generic
        try:
            del ae.emit_generic
            # All five must not raise
            rag_events.emit_rag_query_issued(method="x", timeout_ms=1)
            rag_events.emit_rag_query_returned(method="x")
            rag_events.emit_rag_query_fallback(method="x", reason="r")
            rag_events.emit_rag_query_redacted(chunk_keys=[], family_counts={})
            rag_events.emit_rag_index_redacted(file_path="x", reason="r")
        finally:
            ae.emit_generic = saved

    def test_all_emitters_fail_open_on_emitter_raises(self) -> None:
        def boom(**kwargs):
            raise RuntimeError("synthetic")
        with patch("_lib.audit_emit.emit_generic", boom):
            rag_events.emit_rag_query_issued(method="x", timeout_ms=1)
            rag_events.emit_rag_query_returned(method="x")
            rag_events.emit_rag_query_fallback(method="x", reason="r")
            rag_events.emit_rag_query_redacted(chunk_keys=[], family_counts={})
            rag_events.emit_rag_index_redacted(file_path="x", reason="r")


if __name__ == "__main__":
    unittest.main()
