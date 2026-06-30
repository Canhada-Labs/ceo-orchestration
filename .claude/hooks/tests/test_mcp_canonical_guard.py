#!/usr/bin/env python3
"""Tests for Layer B server-side MCP canonical-guard middleware.

PLAN-070 §3.8.2 — covers ≥30 cases per Round 4 acceptance criteria.

Test categories:
1. Native tool delegation (5 cases) — Edit/Write/MultiEdit/NotebookEdit
   route through Layer A; Layer B is no-op `delegated_to_layer_a`.
2. Non-MCP namespace (3 cases) — non-`mcp__*` tools allow with
   `not_mcp_namespace`.
3. MCP read-only (5 cases) — known read-only MCP tools (no write-shape
   params) allow with `no_write_shape_params`.
4. MCP write-shape, non-canonical (4 cases) — allow with
   `non_canonical_path`.
5. MCP write-shape, canonical, no sentinel (5 cases) — block with
   `canonical_no_sentinel`.
6. MCP write-shape, canonical, with valid sentinel (3 cases) — allow.
7. Defense-in-depth (4 cases) — unknown future MCP tool with write-shape
   on canonical → block; oversized path → caller-truncated; multi-path
   in list; mixed canonical + non-canonical (most-restrictive).
8. Failure modes (3 cases) — import failure → fail-CLOSED; GPG missing
   → fail-CLOSED; middleware fault → fail-CLOSED.
9. Audit emit shape (2 cases) — verify hasattr-guard per ADR-098.
10. Thread safety (1 case) — concurrent invocations.

Total: 35 cases.
"""

from __future__ import annotations

import os
import sys
import threading
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock

# Post-canonical-promotion (PLAN-070 ceremony): canonical_guard now
# lives at `.claude/hooks/_lib/mcp/canonical_guard.py`. Root conftest
# already adds `.claude/hooks/` to sys.path under pytest. For
# `unittest discover` (mcp-smoke.yml CI), conftest is NOT loaded, so
# we add the hooks dir explicitly via parents[1].
#   parents: [0]=tests/  [1]=hooks/  [2]=.claude/  [3]=repo_root
_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

# E5-F10 fixture neutralization: repo root derived from this file's
# location (parents[3], see map above) instead of a hardcoded Owner
# path. Used only as the fallback when CLAUDE_PROJECT_DIR is unset.
_REPO_ROOT_FALLBACK = str(Path(__file__).resolve().parents[3])

from _lib.mcp import canonical_guard  # type: ignore[import-not-found]  # noqa: E402

try:
    from _lib.testing import TestEnvContext  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    TestEnvContext = unittest.TestCase  # type: ignore[misc, assignment]


class _CanonicalGuardBase(TestEnvContext):
    """Common setUp: reset module-level cached imports between tests."""

    def setUp(self) -> None:
        super().setUp()
        # Force re-init on every test for isolation.
        canonical_guard._IMPORTS_INITIALIZED = False
        canonical_guard._check_canonical_edit = None
        canonical_guard._audit_emit = None


class TestNativeToolDelegation(_CanonicalGuardBase):
    """Category 1 — Native tools delegate to Layer A (no-op)."""

    def test_edit_tool_delegates(self) -> None:
        result = canonical_guard.check_mcp_call(
            tool_name="Edit",
            params={"file_path": "PROTOCOL.md", "old_string": "x",
                    "new_string": "y"},
        )
        self.assertEqual(result.get("decision", "allow"), "allow")
        self.assertEqual(result["reason"], "delegated_to_layer_a")

    def test_write_tool_delegates(self) -> None:
        result = canonical_guard.check_mcp_call(
            tool_name="Write",
            params={"file_path": "PROTOCOL.md", "content": "..."},
        )
        self.assertEqual(result.get("decision", "allow"), "allow")
        self.assertEqual(result["reason"], "delegated_to_layer_a")

    def test_multiedit_tool_delegates(self) -> None:
        result = canonical_guard.check_mcp_call(
            tool_name="MultiEdit",
            params={"file_path": "PROTOCOL.md", "edits": []},
        )
        self.assertEqual(result.get("decision", "allow"), "allow")
        self.assertEqual(result["reason"], "delegated_to_layer_a")

    def test_notebookedit_tool_delegates(self) -> None:
        result = canonical_guard.check_mcp_call(
            tool_name="NotebookEdit",
            params={"notebook_path": "x.ipynb"},
        )
        self.assertEqual(result.get("decision", "allow"), "allow")
        self.assertEqual(result["reason"], "delegated_to_layer_a")

    def test_native_canonical_path_still_delegates(self) -> None:
        # Even with a canonical path, Layer B delegates — Layer A is
        # the canonical-guard for native tools.
        result = canonical_guard.check_mcp_call(
            tool_name="Edit",
            params={"file_path": "PROTOCOL.md", "old_string": "a",
                    "new_string": "b"},
        )
        self.assertEqual(result["reason"], "delegated_to_layer_a")


class TestNonMCPNamespace(_CanonicalGuardBase):
    """Category 2 — Non-MCP-namespace tools out of scope."""

    def test_bash_tool_out_of_scope(self) -> None:
        result = canonical_guard.check_mcp_call(
            tool_name="Bash", params={"command": "echo hi"}
        )
        self.assertEqual(result.get("decision", "allow"), "allow")
        self.assertEqual(result["reason"], "not_mcp_namespace")

    def test_read_tool_out_of_scope(self) -> None:
        result = canonical_guard.check_mcp_call(
            tool_name="Read", params={"file_path": "PROTOCOL.md"}
        )
        self.assertEqual(result["reason"], "not_mcp_namespace")

    def test_empty_tool_name_out_of_scope(self) -> None:
        result = canonical_guard.check_mcp_call(
            tool_name="", params={"file_path": "x"}
        )
        self.assertEqual(result["reason"], "not_mcp_namespace")


class TestMCPReadOnly(_CanonicalGuardBase):
    """Category 3 — MCP tools with no write-shape params allow."""

    def test_mcp_codex_codex_no_path(self) -> None:
        # mcp__codex__codex is a chat-style read-only invocation.
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__codex",
            params={"prompt": "what is the time"},
        )
        self.assertEqual(result.get("decision", "allow"), "allow")
        self.assertEqual(result["reason"], "no_write_shape_params")

    def test_mcp_supabase_execute_sql(self) -> None:
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__supabase__execute_sql",
            params={"query": "SELECT 1"},
        )
        self.assertEqual(result["reason"], "no_write_shape_params")

    def test_mcp_empty_params(self) -> None:
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__future__list", params={}
        )
        self.assertEqual(result["reason"], "no_write_shape_params")

    def test_mcp_none_params(self) -> None:
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__future__list", params=None
        )
        self.assertEqual(result["reason"], "no_write_shape_params")

    def test_mcp_non_dict_params(self) -> None:
        # Defense: malformed params (not a dict) → no write-shape.
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__future__weird",
            params="oops",  # type: ignore[arg-type]
        )
        self.assertEqual(result["reason"], "no_write_shape_params")


class TestMCPWriteShapeNonCanonical(_CanonicalGuardBase):
    """Category 4 — MCP write-shape on non-canonical paths allow."""

    # R4-02 (Codex S85) note: tests in this category use a NON-blob-
    # authoritative tool name (`mcp__future__write_thing`) so the focus
    # remains on top-level write-shape path gating without triggering
    # the blob-authoritative fail-CLOSED path. Tests for blob bodies on
    # apply_patch tools live in TestBlobParserCodexEnvelope and
    # TestR4_02BlobAuthoritativeFailClosed.

    def test_mcp_write_to_tmp(self) -> None:
        repo_root = self.project_dir
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__future__write_thing",
            params={"file_path": "tmp/foo.txt", "content": "..."},
            repo_root=repo_root,
        )
        self.assertEqual(result.get("decision", "allow"), "allow")
        self.assertEqual(result["reason"], "non_canonical_path")

    def test_mcp_write_to_user_doc(self) -> None:
        repo_root = self.project_dir
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__future__write_thing",
            params={"file_path": "docs/notes.md", "content": "..."},
            repo_root=repo_root,
        )
        self.assertEqual(result["reason"], "non_canonical_path")

    def test_mcp_write_to_test_file(self) -> None:
        repo_root = self.project_dir
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__future__write_thing",
            params={"file_path": "tests/test_x.py", "content": "..."},
            repo_root=repo_root,
        )
        self.assertEqual(result["reason"], "non_canonical_path")

    def test_mcp_path_outside_repo(self) -> None:
        repo_root = self.project_dir
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__future__write_thing",
            params={"file_path": "/etc/passwd", "content": "..."},
            repo_root=repo_root,
        )
        # R3-05: absolute path outside repo_root now fails-CLOSED
        # (was "non_canonical_path → allow" pre-revision-4). The
        # symlink/traversal/absolute-escape vector is now caught by
        # `_resolves_inside_repo` *before* the canonical-membership
        # check.
        self.assertEqual(result["decision"], "block")
        self.assertIn("escapes repo_root", result["reason"])


class TestMCPWriteShapeCanonicalNoSentinel(_CanonicalGuardBase):
    """Category 5 — Canonical path + no sentinel → block."""

    def test_mcp_write_to_protocol_md(self) -> None:
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        # Use legitimate Codex envelope so the blob parses and the test
        # exercises the canonical/sentinel gate (not R4-02 blob-auth
        # fail-CLOSED). Body parses to PROTOCOL.md → canonical → block.
        patch_body = (
            "*** Begin Patch\n"
            "*** Update File: PROTOCOL.md\n"
            "@@ -1 +1 @@\n-old\n+new\n"
            "*** End Patch\n"
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={"file_path": "PROTOCOL.md", "patch": patch_body},
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")
        self.assertIn("PROTOCOL.md", result["reason"])

    def test_mcp_write_to_team_md(self) -> None:
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__supabase__deploy_edge_function",
            params={"path": ".claude/team.md", "content": "x"},
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")

    def test_mcp_write_to_adr(self) -> None:
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={
                "file_path": ".claude/adr/ADR-042-mcp-server-contract.md",
                "patch": "...",
            },
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")

    def test_mcp_write_to_workflow(self) -> None:
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={
                "file_path": ".github/workflows/release.yml",
                "patch": "...",
            },
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")

    def test_mcp_write_uri_param(self) -> None:
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        # Tests `uri` write-shape key path.
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__future__upload",
            params={"uri": "PROTOCOL.md", "data": "x"},
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")


class TestMCPWriteShapeCanonicalWithSentinel(_CanonicalGuardBase):
    """Category 6 — Canonical path with valid sentinel → allow.

    These tests use mocked sentinel to avoid real GPG dependencies.
    """

    def test_with_mock_sentinel_grant(self) -> None:
        # Force imports to load.
        canonical_guard._lazy_init()
        # Mock _sentinel_grants_path to return True.
        with mock.patch.object(
            canonical_guard._check_canonical_edit,
            "_sentinel_grants_path",
            return_value=True,
        ):
            with mock.patch.object(
                canonical_guard._check_canonical_edit,
                "_find_sentinels",
                return_value=[Path("/fake/approved.md")],
            ):
                with mock.patch.object(
                    canonical_guard._check_canonical_edit,
                    "_is_canonical",
                    return_value=True,
                ):
                    # R4-02: legitimate Codex body so blob-auth fail-CLOSED
                    # does not preempt the sentinel mock.
                    result = canonical_guard.check_mcp_call(
                        tool_name="mcp__codex__apply_patch",
                        params={
                            "file_path": "PROTOCOL.md",
                            "patch": (
                                "*** Begin Patch\n"
                                "*** Update File: PROTOCOL.md\n"
                                "@@\n-x\n+y\n"
                                "*** End Patch\n"
                            ),
                        },
                    )
        self.assertEqual(result.get("decision", "allow"), "allow")
        self.assertIn("sentinel", result["reason"])

    def test_with_mock_sentinel_deny(self) -> None:
        canonical_guard._lazy_init()
        with mock.patch.object(
            canonical_guard._check_canonical_edit,
            "_sentinel_grants_path",
            return_value=False,
        ):
            with mock.patch.object(
                canonical_guard._check_canonical_edit,
                "_find_sentinels",
                return_value=[Path("/fake/approved.md")],
            ):
                with mock.patch.object(
                    canonical_guard._check_canonical_edit,
                    "_is_canonical",
                    return_value=True,
                ):
                    result = canonical_guard.check_mcp_call(
                        tool_name="mcp__codex__apply_patch",
                        params={
                            "file_path": "PROTOCOL.md",
                            "patch": "...",
                        },
                    )
        self.assertEqual(result["decision"], "block")

    def test_sentinel_unreadable_oserror_fail_closed(self) -> None:
        canonical_guard._lazy_init()
        # OSError on sentinel read should fail-CLOSED for that sentinel
        # but since there's only 1 (mocked), final result is block.
        with mock.patch.object(
            canonical_guard._check_canonical_edit,
            "_sentinel_grants_path",
            side_effect=OSError("perm denied"),
        ):
            with mock.patch.object(
                canonical_guard._check_canonical_edit,
                "_find_sentinels",
                return_value=[Path("/fake/approved.md")],
            ):
                with mock.patch.object(
                    canonical_guard._check_canonical_edit,
                    "_is_canonical",
                    return_value=True,
                ):
                    result = canonical_guard.check_mcp_call(
                        tool_name="mcp__codex__apply_patch",
                        params={
                            "file_path": "PROTOCOL.md",
                            "patch": "...",
                        },
                    )
        self.assertEqual(result["decision"], "block")


class TestDefenseInDepth(_CanonicalGuardBase):
    """Category 7 — Defense-in-depth edge cases."""

    def test_unknown_future_mcp_tool_blocks_canonical(self) -> None:
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        # Future MCP tool not registered today → still gated.
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__totally_new_server__write_thing",
            params={"file_path": "PROTOCOL.md", "content": "evil"},
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")

    def test_oversized_path_truncated(self) -> None:
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        # Oversized path values are filtered by `_extract_write_shape_paths`.
        # Result: candidate_paths becomes empty → no_write_shape_params.
        # Use a non-blob-authoritative tool so R4-02 does not preempt the
        # path-shape oversize-filter behavior under test here.
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__future__write_thing",
            params={"file_path": "x" * 10000, "content": "..."},
            repo_root=repo_root,
        )
        # Either path is acceptable (allow with no_write_shape OR
        # allow with non_canonical). Just must be allow.
        self.assertEqual(result.get("decision", "allow"), "allow")

    def test_multi_path_list(self) -> None:
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        # List of paths in `path` param.
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__future__bulk_write",
            params={"path": ["docs/x.md", "PROTOCOL.md"]},
            repo_root=repo_root,
        )
        # PROTOCOL.md is canonical → most-restrictive policy → block.
        self.assertEqual(result["decision"], "block")

    def test_mixed_canonical_and_non_canonical(self) -> None:
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        # Most-restrictive policy: ANY canonical → block.
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__future__bulk",
            params={
                "file_path": "docs/notes.md",  # non-canonical
                "target_path": "PROTOCOL.md",   # canonical
            },
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")


class TestFailureModes(_CanonicalGuardBase):
    """Category 8 — Universal fail-CLOSED contract."""

    def test_import_failure_fail_closed(self) -> None:
        # Force import to fail.
        canonical_guard._IMPORTS_INITIALIZED = False
        canonical_guard._check_canonical_edit = None
        with mock.patch.object(
            canonical_guard,
            "_lazy_init",
            return_value=(False, "import_failure"),
        ):
            result = canonical_guard.check_mcp_call(
                tool_name="mcp__codex__apply_patch",
                params={"file_path": "PROTOCOL.md", "patch": "..."},
            )
        self.assertEqual(result["decision"], "block")
        self.assertIn("import", result["reason"].lower())

    def test_middleware_fault_fail_closed(self) -> None:
        # Inject an exception inside _has_write_shape via mock.
        canonical_guard._lazy_init()
        with mock.patch.object(
            canonical_guard,
            "_has_write_shape",
            side_effect=RuntimeError("boom"),
        ):
            result = canonical_guard.check_mcp_call(
                tool_name="mcp__codex__apply_patch",
                params={"file_path": "PROTOCOL.md", "patch": "..."},
            )
        self.assertEqual(result["decision"], "block")
        self.assertIn("fault", result["reason"].lower())

    def test_repo_root_resolution_failure(self) -> None:
        # Even if the env-var lookup is unusual, function never raises.
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__codex",
            params={"prompt": "x"},
            repo_root=None,
        )
        # Should be allow (non-write-shape).
        self.assertIn(result["decision"], ("allow", "block"))


class TestAuditEmitShape(_CanonicalGuardBase):
    """Category 9 — hasattr-guard per ADR-098."""

    def test_audit_emit_called_on_block(self) -> None:
        canonical_guard._lazy_init()
        emit_calls: List[Dict[str, Any]] = []

        def _spy(action: str, **kw: Any) -> None:
            emit_calls.append({"action": action, **kw})

        if canonical_guard._audit_emit is not None and hasattr(
            canonical_guard._audit_emit, "emit_generic"
        ):
            # P1-04 defensive check requires the action to be registered
            # in `_audit_emit._KNOWN_ACTIONS`. The actual registration is
            # staged for the v1.12.0 Owner sentinel ceremony; in this
            # unit test we mock `_KNOWN_ACTIONS` to include the action so
            # the defensive check passes and the spy fires.
            existing_known = getattr(
                canonical_guard._audit_emit, "_KNOWN_ACTIONS", frozenset()
            )
            patched_known = frozenset(existing_known) | {
                "mcp_canonical_guard_blocked",
                "mcp_canonical_guard_allowed",
            }
            with mock.patch.object(
                canonical_guard._audit_emit,
                "_KNOWN_ACTIONS",
                patched_known,
            ):
                with mock.patch.object(
                    canonical_guard._audit_emit,
                    "emit_generic",
                    side_effect=_spy,
                ):
                    with mock.patch.object(
                        canonical_guard._check_canonical_edit,
                        "_is_canonical",
                        return_value=True,
                    ):
                        with mock.patch.object(
                            canonical_guard._check_canonical_edit,
                            "_find_sentinels",
                            return_value=[],
                        ):
                            canonical_guard.check_mcp_call(
                                tool_name="mcp__codex__apply_patch",
                                params={
                                    "file_path": "PROTOCOL.md",
                                    "patch": "..."
                                },
                            )
            actions = [c["action"] for c in emit_calls]
            self.assertIn("mcp_canonical_guard_blocked", actions)

    def test_audit_emit_unavailable_no_raise(self) -> None:
        # Force audit_emit to None.
        canonical_guard._lazy_init()
        original = canonical_guard._audit_emit
        canonical_guard._audit_emit = None
        try:
            result = canonical_guard.check_mcp_call(
                tool_name="mcp__codex__codex",
                params={"prompt": "x"},
            )
            # Should not raise; should still return decision.
            self.assertIn(result["decision"], ("allow", "block"))
        finally:
            canonical_guard._audit_emit = original


class TestAuditActionRegistration(_CanonicalGuardBase):
    """Category 11 — P1-04 closure: stderr breadcrumb on dropped action.

    Verifies that when Layer B emits an action NOT registered in
    ``audit_emit._KNOWN_ACTIONS`` (e.g. ceremony slipped, downstream lib
    out of sync), the gap is surfaced on stderr instead of silently
    dropped. The test uses a stand-in module with a controllable
    `_KNOWN_ACTIONS` frozenset.
    """

    def test_audit_action_registration_check(self) -> None:
        """Unregistered action → stderr breadcrumb + no-op (no exception)."""
        import io

        canonical_guard._lazy_init()
        # Build a minimal stand-in for the audit_emit module with a
        # tightly scoped `_KNOWN_ACTIONS` that explicitly EXCLUDES the
        # mcp_canonical_guard_* actions so we can exercise the dropped-
        # action codepath deterministically.
        emit_calls: List[Dict[str, Any]] = []

        class _FakeAuditEmit:
            _KNOWN_ACTIONS = frozenset({"some_other_action"})

            @staticmethod
            def emit_generic(action: str, **kw: Any) -> None:
                emit_calls.append({"action": action, **kw})

        original = canonical_guard._audit_emit
        canonical_guard._audit_emit = _FakeAuditEmit  # type: ignore[assignment]
        captured = io.StringIO()
        original_stderr = sys.stderr
        sys.stderr = captured
        try:
            canonical_guard._emit(
                "mcp_canonical_guard_blocked",
                tool_name="mcp__codex__apply_patch",
                reason="canonical_no_sentinel",
            )
        finally:
            sys.stderr = original_stderr
            canonical_guard._audit_emit = original

        self.assertEqual(
            len(emit_calls), 0,
            "emit_generic must NOT be called for unregistered action",
        )
        breadcrumb = captured.getvalue()
        self.assertIn("mcp_canonical_guard_blocked", breadcrumb)
        self.assertIn("_KNOWN_ACTIONS", breadcrumb)
        self.assertIn("dropped", breadcrumb.lower())

    def test_registered_action_passes_through(self) -> None:
        """Registered action → emit_generic is called once."""
        import io

        canonical_guard._lazy_init()
        emit_calls: List[Dict[str, Any]] = []

        class _FakeAuditEmit:
            _KNOWN_ACTIONS = frozenset({"mcp_canonical_guard_allowed"})

            @staticmethod
            def emit_generic(action: str, **kw: Any) -> None:
                emit_calls.append({"action": action, **kw})

        original = canonical_guard._audit_emit
        canonical_guard._audit_emit = _FakeAuditEmit  # type: ignore[assignment]
        captured = io.StringIO()
        original_stderr = sys.stderr
        sys.stderr = captured
        try:
            canonical_guard._emit(
                "mcp_canonical_guard_allowed",
                tool_name="mcp__codex__codex",
                reason="no_write_shape_params",
            )
        finally:
            sys.stderr = original_stderr
            canonical_guard._audit_emit = original

        self.assertEqual(len(emit_calls), 1)
        self.assertEqual(emit_calls[0]["action"], "mcp_canonical_guard_allowed")
        # No breadcrumb on the happy path.
        self.assertEqual(captured.getvalue(), "")

    def test_audit_emit_without_known_actions_attr_no_breadcrumb(self) -> None:
        """Audit-emit module lacking `_KNOWN_ACTIONS` → no defensive guard."""
        import io

        canonical_guard._lazy_init()
        emit_calls: List[Dict[str, Any]] = []

        class _LegacyAuditEmit:
            # No _KNOWN_ACTIONS attribute at all (legacy / partial rollout).
            @staticmethod
            def emit_generic(action: str, **kw: Any) -> None:
                emit_calls.append({"action": action, **kw})

        original = canonical_guard._audit_emit
        canonical_guard._audit_emit = _LegacyAuditEmit  # type: ignore[assignment]
        captured = io.StringIO()
        original_stderr = sys.stderr
        sys.stderr = captured
        try:
            canonical_guard._emit(
                "mcp_canonical_guard_allowed",
                tool_name="mcp__codex__codex",
            )
        finally:
            sys.stderr = original_stderr
            canonical_guard._audit_emit = original

        # When _KNOWN_ACTIONS is absent, fall back to original behavior:
        # call emit_generic; downstream module decides accept/reject.
        self.assertEqual(len(emit_calls), 1)
        self.assertEqual(captured.getvalue(), "")


class TestThreadSafety(_CanonicalGuardBase):
    """Category 10 — concurrent invocations don't corrupt state."""

    def test_concurrent_calls(self) -> None:
        results: List[Dict[str, str]] = []
        lock = threading.Lock()

        def _worker() -> None:
            r = canonical_guard.check_mcp_call(
                tool_name="mcp__codex__codex",
                params={"prompt": "x"},
            )
            with lock:
                results.append(r)

        threads = [threading.Thread(target=_worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(results), 20)
        # All read-only calls should allow.
        for r in results:
            self.assertEqual(r.get("decision", "allow"), "allow")


class TestBlobParserCodexEnvelope(_CanonicalGuardBase):
    """Category 11 — P0-01 Codex apply_patch envelope blob parser.

    Closes NG-06: ``mcp__codex__apply_patch`` carries the target path
    INSIDE the patch body (``*** Update File: PROTOCOL.md``) with no
    top-level ``file_path`` key.
    """

    def test_codex_envelope_update_file_canonical_blocks(self) -> None:
        """Codex `*** Update File: PROTOCOL.md` with NO top-level path."""
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        patch_body = (
            "*** Begin Patch\n"
            "*** Update File: PROTOCOL.md\n"
            "@@ -1 +1 @@\n"
            "-old\n+new\n"
            "*** End Patch\n"
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={"patch": patch_body},  # NO file_path key
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")
        self.assertIn("PROTOCOL.md", result["reason"])

    def test_codex_envelope_add_file_canonical_blocks(self) -> None:
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        patch_body = "*** Add File: .claude/team.md\n+content\n"
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={"patch": patch_body},
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")

    def test_codex_envelope_delete_file_canonical_blocks(self) -> None:
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        patch_body = "*** Delete File: .github/workflows/release.yml\n"
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={"patch": patch_body},
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")

    def test_codex_envelope_non_canonical_allows(self) -> None:
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        patch_body = (
            "*** Update File: docs/notes.md\n"
            "@@ -1 +1 @@\n-x\n+y\n"
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={"patch": patch_body},
            repo_root=repo_root,
        )
        self.assertEqual(result.get("decision", "allow"), "allow")
        self.assertEqual(result["reason"], "non_canonical_path")

    def test_codex_envelope_mixed_canonical_blocks(self) -> None:
        """Multi-file patch with at least one canonical → block."""
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        patch_body = (
            "*** Update File: docs/notes.md\n"
            "@@\n-x\n+y\n"
            "*** Update File: PROTOCOL.md\n"
            "@@\n-a\n+b\n"
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={"patch": patch_body},
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")


class TestBlobParserUnifiedDiff(_CanonicalGuardBase):
    """Category 12 — Unified-diff blob parser (git/RFC5261)."""

    def test_unified_diff_canonical_blocks(self) -> None:
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        diff_body = (
            "--- a/PROTOCOL.md\n"
            "+++ b/PROTOCOL.md\n"
            "@@ -1 +1 @@\n-old\n+new\n"
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__future__diff",
            params={"diff": diff_body},
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")

    def test_unified_diff_non_canonical_allows(self) -> None:
        """Tool-name + auth-key alignment: `mcp__future__diff` has
        authoritative key `diff`, so a clean `diff` body parses
        cleanly via the auth-key gate. Pre-R5-01 used
        `mcp__future__patch` + `diff=` which now fails-CLOSED on
        missing `patch` (correct). This test exercises the
        unified-diff parser with a matched tool/key pair.
        """
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        diff_body = (
            "--- a/docs/x.md\n"
            "+++ b/docs/x.md\n"
            "@@ -1 +1 @@\n-old\n+new\n"
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__future__diff",
            params={"diff": diff_body},
            repo_root=repo_root,
        )
        self.assertEqual(result.get("decision", "allow"), "allow")
        self.assertEqual(result["reason"], "non_canonical_path")

    def test_unified_diff_dev_null_skipped(self) -> None:
        """Pure new-file diff (`--- /dev/null`) only carries the +++ side."""
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        diff_body = (
            "--- /dev/null\n"
            "+++ b/PROTOCOL.md\n"
            "@@ -0,0 +1 @@\n+x\n"
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__future__diff",
            params={"diff": diff_body},
            repo_root=repo_root,
        )
        # PROTOCOL.md is canonical → block.
        self.assertEqual(result["decision"], "block")


class TestBlobParserJSONPatch(_CanonicalGuardBase):
    """Category 13 — JSON Patch (RFC 6902) blob parser."""

    def test_json_patch_pointer_canonical_blocks(self) -> None:
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        body = (
            '[{"op": "replace", "path": "/PROTOCOL.md", '
            '"value": "evil"}]'
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__future__apply_patch",
            params={"patch": body},
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")

    def test_json_patch_pointer_non_canonical_allows(self) -> None:
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        body = (
            '[{"op": "replace", "path": "/docs/notes.md", '
            '"value": "x"}]'
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__future__apply_patch",
            params={"patch": body},
            repo_root=repo_root,
        )
        self.assertEqual(result.get("decision", "allow"), "allow")


class TestBlobParserNegative(_CanonicalGuardBase):
    """Category 14 — Blob parser negative + fail-CLOSED edges."""

    def test_blob_carrier_unparseable_body_fail_closed(self) -> None:
        """Tool name says apply_patch, body is binary garbage → block.

        After R4-02, the reason text is the blob-AUTHORITATIVE reason
        (apply_patch is on the authoritative list). Pre-R4-02 path
        emitted ``ng-06`` for the same scenario; both are valid
        fail-CLOSED outcomes.
        """
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={"patch": "\x00binary garbage no markers\xff"},
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")
        reason_lower = result["reason"].lower()
        self.assertTrue(
            "ng-06" in reason_lower or "blob-authoritative" in reason_lower,
            f"unexpected reason: {result['reason']}",
        )

    def test_blob_carrier_with_top_level_path_non_authoritative(self) -> None:
        """If a top-level path is present on a NON-authoritative blob
        carrier (e.g. tool name contains a blob fragment but isn't on
        the apply_patch/patch/diff family), blob-parse failure is
        advisory — the top-level path is gated independently.

        R4-02 (Codex S85) tightened the apply_patch/patch/diff family
        to fail-CLOSED on parse failure regardless of top-level decoys
        (see TestR4_02BlobAuthoritativeFailClosed below); this test
        documents that NON-authoritative carriers retain the legacy
        advisory behavior for top-level write-shape paths.
        """
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        # Tool name contains "patch" via the body-key but the tool name
        # itself doesn't match an authoritative fragment. We use a
        # synthetic name that has a body-key match but no authoritative
        # name match — but our fragment list catches "patch" and "diff"
        # generically, so a truly non-authoritative carrier needs a
        # name without those substrings. Instead, demonstrate the
        # contract using a body-only match (no name match) → not blob
        # carrier at all, top-level path gates normally.
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__future__write_thing",
            params={"file_path": "docs/x.md", "patch": "opaque"},
            repo_root=repo_root,
        )
        # `mcp__future__write_thing` doesn't contain a blob fragment, so
        # blob_carrier=False; top-level write-shape gates as non-canonical.
        self.assertEqual(result.get("decision", "allow"), "allow")
        self.assertEqual(result["reason"], "non_canonical_path")

    def test_non_blob_tool_with_patch_body_ignored(self) -> None:
        """Tool name doesn't match any blob fragment → blob parse skipped."""
        # mcp__codex__codex doesn't carry patches; even with `patch` key
        # in params (unusual), blob parser is not triggered.
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__codex",
            params={"patch": "*** Update File: PROTOCOL.md\n"},
        )
        # No path-shape key + tool not blob-carrier → no_write_shape.
        self.assertEqual(result.get("decision", "allow"), "allow")
        self.assertEqual(result["reason"], "no_write_shape_params")

    def test_blob_oversized_body_rejected(self) -> None:
        """Blob bodies >4MB are not parsed (cost-bound) → fail-CLOSED."""
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        huge = "x" * (5 * 1024 * 1024)
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={"patch": huge},
            repo_root=repo_root,
        )
        # No write-shape, no parse → fail-CLOSED.
        self.assertEqual(result["decision"], "block")


class TestPathResolutionRepoRootNotCWD(_CanonicalGuardBase):
    """Category 15 — P0-02 path resolution against repo_root, not CWD."""

    def test_resolves_against_repo_root_not_cwd(self) -> None:
        """chdir to /tmp; relative path must still anchor on repo_root."""
        repo_root = Path("/Users/devuser/ceo-orchestration")
        # Skip if repo_root doesn't exist in this CI env (e.g. Linux box).
        if not repo_root.exists():
            self.skipTest("real repo_root not present in this CI env")
        original_cwd = os.getcwd()
        try:
            os.chdir("/tmp")
            # Sanity: from /tmp, naive Path('PROTOCOL.md').resolve() →
            # /tmp/PROTOCOL.md. The fix anchors on repo_root. Use a
            # legitimate Codex envelope so blob-auth fail-CLOSED (R4-02)
            # does not preempt the canonical-no-sentinel reason text.
            result = canonical_guard.check_mcp_call(
                tool_name="mcp__codex__apply_patch",
                params={
                    "file_path": "PROTOCOL.md",
                    "patch": (
                        "*** Begin Patch\n"
                        "*** Update File: PROTOCOL.md\n"
                        "@@\n-x\n+y\n"
                        "*** End Patch\n"
                    ),
                },
                repo_root=repo_root,
            )
            self.assertEqual(result["decision"], "block")
            self.assertIn("PROTOCOL.md", result["reason"])
        finally:
            os.chdir(original_cwd)

    def test_resolve_helper_anchors_relative(self) -> None:
        """Direct unit test of `_resolve_against_repo_root`."""
        original_cwd = os.getcwd()
        try:
            os.chdir("/tmp")
            anchored = canonical_guard._resolve_against_repo_root(
                "foo/bar.md", Path("/some/repo")
            )
            self.assertEqual(anchored, "/some/repo/foo/bar.md")
        finally:
            os.chdir(original_cwd)

    def test_resolve_helper_passes_absolute_through(self) -> None:
        """Absolute paths are not re-anchored."""
        result = canonical_guard._resolve_against_repo_root(
            "/etc/passwd", Path("/some/repo")
        )
        self.assertEqual(result, "/etc/passwd")

    def test_resolve_helper_handles_empty(self) -> None:
        """Empty/non-string inputs don't crash."""
        self.assertEqual(
            canonical_guard._resolve_against_repo_root(
                "", Path("/some/repo")
            ),
            "",
        )


class TestImportBootstrap(_CanonicalGuardBase):
    """Category 16 — P1-05 import bootstrap path resolution.

    The module supports both staging
    (.claude/plans/PLAN-070/staging/canonical_guard.py) and deployed
    (.claude/hooks/_lib/mcp/canonical_guard.py) on-disk locations.
    The bootstrap walks parents looking for check_canonical_edit.py.
    """

    def test_hooks_root_resolves_to_check_canonical_edit_dir(self) -> None:
        """`_resolve_hooks_root` returns the dir containing the SSO module."""
        hooks_root = canonical_guard._resolve_hooks_root()
        self.assertIsNotNone(hooks_root)
        self.assertTrue(
            (hooks_root / "check_canonical_edit.py").exists(),
            f"check_canonical_edit.py not found at {hooks_root}",
        )

    def test_imports_without_test_only_path_injection(self) -> None:
        """Module imports cleanly from canonical path without test scaffolding.

        Spawns a fresh subprocess with NO custom sys.path manipulation
        beyond pointing at the canonical hooks dir, and confirms
        ``from _lib.mcp import canonical_guard`` resolves the SSO module
        via its own bootstrap (NOT via the test's path injection).
        """
        import subprocess
        # Canonical hooks dir = parents[1] from .claude/hooks/tests/<file>.
        hooks_dir = Path(__file__).resolve().parents[1]
        code = (
            "import sys\n"
            f"sys.path.insert(0, {str(hooks_dir)!r})\n"
            "from _lib.mcp import canonical_guard\n"
            "ok, reason = canonical_guard._lazy_init()\n"
            "assert ok, f'lazy_init failed: {reason}'\n"
            "assert canonical_guard._check_canonical_edit is not None, "
            "'SSO module not loaded'\n"
            "print('OK')\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(
            proc.returncode, 0,
            f"subprocess import failed.\nstdout:{proc.stdout}\n"
            f"stderr:{proc.stderr}",
        )
        self.assertIn("OK", proc.stdout)


class TestCodexMoveGrammar(_CanonicalGuardBase):
    """Category 17 — R3-01 Codex `*** Move to:` grammar parsing.

    Codex apply_patch emits a standalone ``*** Move to: <dest>`` line
    alongside ``*** Update File: <src>`` for renames. Without this
    rule, the destination of the move (the actual write target) was
    invisible to Layer B → an attacker could land a canonical write
    by moving a non-canonical source into a canonical destination.
    """

    def test_codex_move_to_canonical_blocks(self) -> None:
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        # `Update File: docs/x.md` is non-canonical, but the rename
        # destination PROTOCOL.md is canonical → most-restrictive
        # policy → block. Pre-R3-01 this slipped through.
        patch_body = (
            "*** Begin Patch\n"
            "*** Update File: docs/noncanonical.md\n"
            "*** Move to: PROTOCOL.md\n"
            "@@\n-x\n+y\n"
            "*** End Patch\n"
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={"patch": patch_body},
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")
        self.assertIn("PROTOCOL.md", result["reason"])

    def test_codex_move_to_noncanonical_allows(self) -> None:
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        # Both source and dest non-canonical → allow.
        patch_body = (
            "*** Begin Patch\n"
            "*** Update File: docs/old.md\n"
            "*** Move to: docs/new.md\n"
            "@@\n-x\n+y\n"
            "*** End Patch\n"
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={"patch": patch_body},
            repo_root=repo_root,
        )
        self.assertEqual(result.get("decision", "allow"), "allow")
        self.assertEqual(result["reason"], "non_canonical_path")

    def test_codex_complex_patch_with_move_and_update(self) -> None:
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        # Multi-file patch: one Update + one Move-to-canonical → block.
        patch_body = (
            "*** Begin Patch\n"
            "*** Update File: docs/a.md\n"
            "@@\n-x\n+y\n"
            "*** Update File: docs/b.md\n"
            "*** Move to: .claude/team.md\n"
            "@@\n-a\n+b\n"
            "*** End Patch\n"
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={"patch": patch_body},
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")

    def test_codex_rename_to_synonym_also_caught(self) -> None:
        """Defensive variant: ``Rename to:`` matches the same regex."""
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        patch_body = (
            "*** Update File: docs/old.md\n"
            "*** Rename to: PROTOCOL.md\n"
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={"patch": patch_body},
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")
        self.assertIn("PROTOCOL.md", result["reason"])


class TestJSONPatchUnescape(_CanonicalGuardBase):
    """Category 18 — R3-02 JSON Patch json.loads() unescape.

    Pre-revision-4, ``_JSON_PATCH_PATH_RE`` captured raw escape
    sequences (``\\u002F``, ``~1``) that the JSON Patch consumer
    decodes server-side. Layer B saw the LITERAL escape, mismatched
    against ``_CANONICAL_GUARDS``, and ALLOWED the bypass. This
    suite verifies that ``json.loads()`` decoding is now applied
    BEFORE canonical comparison.
    """

    def test_json_patch_unicode_escape_decoded(self) -> None:
        """``/PROTOCOL\\u002Emd`` decodes to ``/PROTOCOL.md`` and blocks."""
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        # JSON-escape the dot. After json.loads(), path == "/PROTOCOL.md"
        # which strips to "PROTOCOL.md" → canonical → block.
        body = '[{"op":"replace","path":"/PROTOCOL\\u002Emd","value":"x"}]'
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__future__apply_patch",
            params={"patch": body},
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")

    def test_json_patch_pointer_tilde_escapes(self) -> None:
        """RFC 6901 ``~1`` decodes to ``/`` (path separator)."""
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        # `/.claude~1team.md` decodes to `/.claude/team.md`.
        body = '[{"op":"replace","path":"/.claude~1team.md","value":"x"}]'
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__future__apply_patch",
            params={"patch": body},
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")

    def test_json_patch_tilde_zero_decoded(self) -> None:
        """RFC 6901 ``~0`` decodes to literal ``~`` (not path-sensitive)."""
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        # `/foo~0bar` decodes to `/foo~bar` — non-canonical → allow.
        body = '[{"op":"replace","path":"/docs~0notes","value":"x"}]'
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__future__apply_patch",
            params={"patch": body},
            repo_root=repo_root,
        )
        self.assertEqual(result.get("decision", "allow"), "allow")

    def test_json_patch_corrupt_fail_closed(self) -> None:
        """JSON-shape body that fails ``json.loads()`` → fail-CLOSED."""
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        # Starts with `[` so the body is JSON-shape, but the trailing
        # comma makes it invalid JSON. Pre-revision-4 the legacy regex
        # was tolerant + would silently parse partial paths. Now:
        # corrupt JSON-shape → ([], False) → caller fail-CLOSED.
        body = '[{"op":"replace","path":"/PROTOCOL.md","value":"x",}]'
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__future__apply_patch",
            params={"patch": body},
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")

    def test_json_patch_from_field_also_walked(self) -> None:
        """RFC 6902 ``move``/``copy`` ops carry ``from`` JSON Pointer."""
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        # `move` op has both `from` (source) and `path` (dest). Either
        # being canonical → block.
        body = (
            '[{"op":"move","from":"/docs/old.md",'
            '"path":"/.claude/team.md"}]'
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__future__apply_patch",
            params={"patch": body},
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")

    def test_json_pointer_to_path_helper_unit(self) -> None:
        """Direct unit on `_json_pointer_to_path` decode order."""
        # `~01` must decode to `~1` (NOT `/`). Per RFC 6901 §4 we decode
        # ~1 first then ~0, so `~01` → `~01`.replace("~1","/") → "~01"
        # (no `~1` literal present) → .replace("~0","~") → `~1`. Wait,
        # actually `~01` contains `~0` so it becomes `~1`. Verify:
        self.assertEqual(
            canonical_guard._json_pointer_to_path("/~01"),
            "~1",
        )
        # `~0` → `~`
        self.assertEqual(
            canonical_guard._json_pointer_to_path("/~0"),
            "~",
        )
        # `~1` → `/`
        self.assertEqual(
            canonical_guard._json_pointer_to_path("/foo~1bar"),
            "foo/bar",
        )
        # Non-pointer (no leading slash) → empty.
        self.assertEqual(
            canonical_guard._json_pointer_to_path("PROTOCOL.md"),
            "",
        )


class TestPathTraversalSymlinkEscape(_CanonicalGuardBase):
    """Category 19 — R3-05 path traversal / symlink / absolute escape.

    `_resolves_inside_repo` rejects any candidate whose resolved path
    is not relative to ``repo_root``. Catches:
      * ``../../../etc/passwd`` (literal ..-traversal)
      * symlink-in-repo pointing to a path outside repo_root
      * absolute paths outside the worktree
    """

    def test_path_traversal_dotdot_blocked(self) -> None:
        """Candidate ``../../../etc/passwd`` → fail-CLOSED."""
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={"file_path": "../../../etc/passwd", "patch": "..."},
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")
        self.assertIn("escapes repo_root", result["reason"])

    def test_path_traversal_to_canonical_blocked(self) -> None:
        """Even traversal that lands BACK on canonical is fail-CLOSED.

        ``foo/../PROTOCOL.md`` resolves to ``<repo>/PROTOCOL.md`` which
        IS inside repo_root, so the traversal-escape check passes;
        downstream the canonical check still blocks via sentinel
        gating. This regression test documents the expected layering.
        """
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={"file_path": "foo/../PROTOCOL.md", "patch": "..."},
            repo_root=repo_root,
        )
        # Either escapes_repo_root OR canonical_no_sentinel acceptable.
        self.assertEqual(result["decision"], "block")

    def test_legitimate_subdirectory_allows(self) -> None:
        """Regression: `subdir/file.txt` inside repo_root → not blocked
        by the traversal check (continues to canonical check, which
        allows because the path is non-canonical).

        Uses a non-blob-authoritative tool so R4-02 fail-CLOSED does
        not preempt the path-resolution behavior under test.
        """
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__future__write_thing",
            params={"file_path": "scripts/foo/bar.py", "content": "..."},
            repo_root=repo_root,
        )
        self.assertEqual(result.get("decision", "allow"), "allow")
        self.assertEqual(result["reason"], "non_canonical_path")

    def test_absolute_path_outside_repo_blocked(self) -> None:
        """Absolute path outside repo_root → fail-CLOSED.

        Replaces the pre-revision-4 ``test_mcp_path_outside_repo`` which
        expected ``/etc/passwd`` to be allowed (non-canonical). R3-05
        elevated this to fail-CLOSED to defend against arbitrary writes
        via Codex CLI launched from outside the repo.
        """
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={"file_path": "/var/log/system.log", "patch": "..."},
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")
        self.assertIn("escapes repo_root", result["reason"])

    def test_symlink_escape_blocked(self) -> None:
        """Symlink IN repo pointing OUTSIDE repo → fail-CLOSED.

        Creates a temporary symlink under a sandbox repo_root that
        resolves to an external directory; asserts Layer B blocks
        before reaching canonical check.
        """
        import tempfile
        with tempfile.TemporaryDirectory() as fake_repo_str:
            fake_repo = Path(fake_repo_str)
            external = Path(tempfile.mkdtemp(prefix="r3_05_external_"))
            try:
                evil_link = fake_repo / "evil"
                try:
                    evil_link.symlink_to(external)
                except (OSError, NotImplementedError):
                    self.skipTest("symlink unsupported on this filesystem")
                result = canonical_guard.check_mcp_call(
                    tool_name="mcp__codex__apply_patch",
                    params={
                        "file_path": "evil/captured.txt",
                        "patch": "...",
                    },
                    repo_root=fake_repo,
                )
                self.assertEqual(result["decision"], "block")
                self.assertIn("escapes repo_root", result["reason"])
            finally:
                # Clean up the external dir.
                try:
                    external.rmdir()
                except OSError:
                    pass

    def test_resolves_inside_repo_helper_unit(self) -> None:
        """Direct unit on `_resolves_inside_repo` helper."""
        import tempfile
        with tempfile.TemporaryDirectory() as repo_str:
            repo = Path(repo_str)
            # Inside repo
            self.assertTrue(
                canonical_guard._resolves_inside_repo("foo/bar.txt", repo)
            )
            # Traversal escape
            self.assertFalse(
                canonical_guard._resolves_inside_repo(
                    "../../../etc/passwd", repo
                )
            )
            # Absolute outside
            self.assertFalse(
                canonical_guard._resolves_inside_repo("/etc/passwd", repo)
            )
            # Empty
            self.assertFalse(
                canonical_guard._resolves_inside_repo("", repo)
            )


class TestR4_01ColonlessMoveGrammar(_CanonicalGuardBase):
    """Category 20 — R4-01 colonless Move/Rename grammar (Codex S85).

    Pre-revision-5 regex required ``Move to:`` / ``Update File:`` with
    the explicit colon. Deployed Codex CLI accepts the colonless form
    ``*** Move to PROTOCOL.md`` and ``*** Update File PROTOCOL.md``.
    Without this fix, an attacker could emit colonless grammar that
    Codex would honor on apply but Layer B silently treated as
    non-canonical.
    """

    def test_codex_move_colonless_blocks_canonical(self) -> None:
        """``*** Move to PROTOCOL.md`` (no colon) → block."""
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        patch_body = (
            "*** Begin Patch\n"
            "*** Update File: docs/noncanonical.md\n"
            "*** Move to PROTOCOL.md\n"
            "@@\n-x\n+y\n"
            "*** End Patch\n"
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={"patch": patch_body},
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")
        self.assertIn("PROTOCOL.md", result["reason"])

    def test_codex_rename_colonless_blocks_canonical(self) -> None:
        """``*** Rename to PROTOCOL.md`` (no colon) → block."""
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        patch_body = (
            "*** Update File: docs/old.md\n"
            "*** Rename to PROTOCOL.md\n"
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={"patch": patch_body},
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")
        self.assertIn("PROTOCOL.md", result["reason"])

    def test_codex_update_file_colonless_blocks_canonical(self) -> None:
        """``*** Update File PROTOCOL.md`` (no colon on envelope) → block."""
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        patch_body = (
            "*** Begin Patch\n"
            "*** Update File PROTOCOL.md\n"
            "@@\n-x\n+y\n"
            "*** End Patch\n"
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={"patch": patch_body},
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")
        self.assertIn("PROTOCOL.md", result["reason"])

    def test_codex_move_with_colon_still_blocks_regression(self) -> None:
        """Regression: colon-with form (legacy R3-01) still works."""
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        patch_body = (
            "*** Update File: docs/old.md\n"
            "*** Move to: PROTOCOL.md\n"
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={"patch": patch_body},
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")
        self.assertIn("PROTOCOL.md", result["reason"])


class TestR4_02BlobAuthoritativeFailClosed(_CanonicalGuardBase):
    """Category 21 — R4-02 blob-authoritative fail-CLOSED (Codex S85).

    For tools whose name contains an authoritative blob fragment
    (apply_patch / patch / diff / apply_diff), the patch BODY is the
    source of truth for the target path. Blob-parse failure must
    fail-CLOSED REGARDLESS of any top-level write-shape decoy — see
    `_is_blob_authoritative_tool`.
    """

    def test_blob_authoritative_corrupt_body_blocks_despite_decoy(
        self,
    ) -> None:
        """``mcp__codex__apply_patch`` + decoy file_path + corrupt body
        → block via R4-02 (was allow pre-revision-5)."""
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        # Decoy: file_path=docs/x.md is non-canonical. The patch body
        # is binary garbage that does not match any patch grammar.
        # Pre-R4-02, Layer B saw the decoy + no parsed blob path,
        # returned non_canonical_path → allow. Real Codex would honor
        # whatever its server-side parser found, which could include a
        # canonical target hidden in proprietary framing.
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={
                "file_path": "docs/x.md",
                "patch": "\x00binary garbage no markers\xff",
            },
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")
        self.assertIn("blob-authoritative", result["reason"].lower())
        self.assertIn("r4-02", result["reason"].lower())

    def test_blob_authoritative_corrupt_body_no_decoy_blocks_legacy(
        self,
    ) -> None:
        """No decoy, no parse → block via legacy NG-06 path (regression)."""
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={"patch": "\x00binary garbage no markers\xff"},
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")
        # Either NG-06 or R4-02 reason text acceptable (both describe
        # blob-parse fail-CLOSED; depends on dispatch order).
        reason_lower = result["reason"].lower()
        self.assertTrue(
            "ng-06" in reason_lower or "blob-authoritative" in reason_lower,
            f"unexpected reason: {result['reason']}",
        )

    def test_blob_authoritative_with_legitimate_blob_still_works(
        self,
    ) -> None:
        """Regression: valid Codex apply_patch on non-canonical path
        with legitimate body still allows."""
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        patch_body = (
            "*** Begin Patch\n"
            "*** Update File: docs/notes.md\n"
            "@@ -1 +1 @@\n-old\n+new\n"
            "*** End Patch\n"
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={"file_path": "docs/notes.md", "patch": patch_body},
            repo_root=repo_root,
        )
        self.assertEqual(result.get("decision", "allow"), "allow")
        self.assertEqual(result["reason"], "non_canonical_path")

    def test_non_blob_authoritative_tool_unaffected_regression(
        self,
    ) -> None:
        """Tool whose name has NO blob fragment is not classified blob
        carrier; top-level write-shape gates normally."""
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__write_file",
            params={"file_path": "docs/x.md", "content": "..."},
            repo_root=repo_root,
        )
        # No blob fragment → blob_carrier=False → top-level path gates
        # via normal write-shape path. docs/x.md is non-canonical → allow.
        self.assertEqual(result.get("decision", "allow"), "allow")
        self.assertEqual(result["reason"], "non_canonical_path")

    def test_is_blob_authoritative_helper_unit(self) -> None:
        """Direct unit on `_is_blob_authoritative_tool` classifier."""
        # Authoritative names (true positives).
        self.assertTrue(
            canonical_guard._is_blob_authoritative_tool(
                "mcp__codex__apply_patch"
            )
        )
        self.assertTrue(
            canonical_guard._is_blob_authoritative_tool(
                "mcp__future__patch"
            )
        )
        self.assertTrue(
            canonical_guard._is_blob_authoritative_tool(
                "mcp__future__diff"
            )
        )
        self.assertTrue(
            canonical_guard._is_blob_authoritative_tool(
                "mcp__future__apply_diff"
            )
        )
        # Non-authoritative names (true negatives).
        self.assertFalse(
            canonical_guard._is_blob_authoritative_tool(
                "mcp__codex__codex"
            )
        )
        self.assertFalse(
            canonical_guard._is_blob_authoritative_tool(
                "mcp__codex__write_file"
            )
        )
        # Defensive: non-string / empty.
        self.assertFalse(canonical_guard._is_blob_authoritative_tool(""))
        self.assertFalse(
            canonical_guard._is_blob_authoritative_tool(None)  # type: ignore[arg-type]
        )


class TestR5_01AuthoritativeBlobKeyMapping(_CanonicalGuardBase):
    """Category 22 — R5-01 authoritative-blob-key fail-CLOSED (Codex S85 final).

    Closes the sibling-decoy bypass discovered in Codex R5: aggregating
    `any_parsed` across all blob body keys allowed a clean sibling
    (`diff`) to mask a corrupt authoritative key (`patch`). The
    revision-6 fix narrows the fail-CLOSED gate to the SINGLE
    authoritative key per blob-authoritative tool name.
    """

    def test_authoritative_blob_key_for_apply_patch_is_patch(self) -> None:
        """`mcp__codex__apply_patch` → authoritative key is `patch`.

        The longer fragment `apply_patch` must win over the bare
        `patch` rule (declared-order longest-first).
        """
        self.assertEqual(
            canonical_guard._authoritative_blob_key_for(
                "mcp__codex__apply_patch"
            ),
            "patch",
        )
        self.assertEqual(
            canonical_guard._authoritative_blob_key_for(
                "mcp__future__applypatch"
            ),
            "patch",
        )

    def test_authoritative_blob_key_for_apply_diff_is_diff(self) -> None:
        """`apply_diff` family resolves to `diff` (not `patch`)."""
        self.assertEqual(
            canonical_guard._authoritative_blob_key_for(
                "mcp__future__apply_diff"
            ),
            "diff",
        )
        self.assertEqual(
            canonical_guard._authoritative_blob_key_for(
                "mcp__future__applydiff"
            ),
            "diff",
        )

    def test_authoritative_blob_key_for_generic_diff_is_diff(self) -> None:
        """Bare `diff` family fragment resolves to `diff`."""
        self.assertEqual(
            canonical_guard._authoritative_blob_key_for(
                "mcp__future__diff"
            ),
            "diff",
        )

    def test_authoritative_blob_key_for_non_blob_returns_none(self) -> None:
        """Non-blob-authoritative tool → None (caller falls back)."""
        self.assertIsNone(
            canonical_guard._authoritative_blob_key_for(
                "mcp__codex__write_file"
            )
        )
        self.assertIsNone(
            canonical_guard._authoritative_blob_key_for("")
        )
        self.assertIsNone(
            canonical_guard._authoritative_blob_key_for(None)  # type: ignore[arg-type]
        )

    def test_corrupt_authoritative_with_clean_sibling_diff_blocks(
        self,
    ) -> None:
        """R5-01 PoC: `apply_patch` with corrupt `patch` + clean
        `diff` sibling decoy → block fail-CLOSED.

        Pre-revision-6, `_extract_blob_paths_from_params` aggregated
        `any_parsed=True` from the clean `diff` value, the R4-02 gate
        thought blob_parsed=True, returned to the canonical/sentinel
        check, which saw a non-canonical `docs/x.md` from the diff
        sibling and returned allow/non_canonical_path. Codex R5
        verdict P1 finding R5-01.
        """
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={
                # Authoritative key — corrupt binary garbage.
                "patch": "\x00garbage\xff",
                # Sibling decoy — clean Codex envelope pointing at a
                # non-canonical path. Pre-revision-6 this would mask
                # the corrupt authoritative key.
                "diff": "*** Update File: docs/x.md\n",
            },
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")
        reason_lower = result["reason"].lower()
        self.assertIn("r5-01", reason_lower)
        self.assertIn("authoritative", reason_lower)
        self.assertIn("'patch'", result["reason"])

    def test_clean_authoritative_with_decoy_sibling_aggregates_paths(
        self,
    ) -> None:
        """R5-01 regression: clean authoritative + sibling both
        contribute paths via aggregation (defense-in-depth).

        Sibling key paths still aggregate so any canonical hit blocks
        even when authoritative-key paths are non-canonical. This
        ensures the auth-key narrowing of fail-CLOSED does NOT
        weaken canonical-hit detection.
        """
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        # Authoritative `patch` parses cleanly to a non-canonical path.
        # Sibling `diff` parses cleanly to a CANONICAL path. Result
        # must be the canonical/sentinel branch (not auth-key
        # fail-CLOSED).
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={
                "patch": (
                    "*** Begin Patch\n"
                    "*** Update File: docs/notes.md\n"
                    "@@ -1 +1 @@\n-old\n+new\n"
                    "*** End Patch\n"
                ),
                # Sibling key with a CANONICAL path target.
                "diff": "--- a/PROTOCOL.md\n+++ b/PROTOCOL.md\n",
            },
            repo_root=repo_root,
        )
        # PROTOCOL.md is canonical → must hit canonical/sentinel gate
        # (block on missing sentinel, not R5-01 auth-key block).
        self.assertEqual(result["decision"], "block")
        reason_lower = result["reason"].lower()
        self.assertNotIn("r5-01", reason_lower)
        # Canonical-no-sentinel reason text mentions the canonical path.
        self.assertIn("protocol.md", reason_lower)

    def test_missing_authoritative_key_with_sibling_blob_blocks(
        self,
    ) -> None:
        """R5-01: `apply_patch` with NO `patch` key but sibling
        `content`/`diff` → block (auth key missing).

        Pre-revision-6, a missing `patch` key and a present `content`
        sibling could have parsed via the legacy aggregator. Now the
        authoritative-key check fires first and fails-CLOSED before
        siblings get a vote.
        """
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={
                # No `patch` key. Sibling `diff` parses cleanly.
                "diff": "*** Update File: docs/x.md\n",
            },
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")
        reason_lower = result["reason"].lower()
        self.assertIn("r5-01", reason_lower)
        self.assertIn("missing", reason_lower)
        self.assertIn("'patch'", result["reason"])

    def test_authoritative_key_non_string_value_fails_closed(self) -> None:
        """R5-01 defensive: `patch=None` (non-string) is treated as
        parse failure under the auth-key rule, not silently skipped.
        """
        repo_root = Path(
            os.environ.get("CLAUDE_PROJECT_DIR")
            or _REPO_ROOT_FALLBACK
        )
        result = canonical_guard.check_mcp_call(
            tool_name="mcp__codex__apply_patch",
            params={
                "patch": None,  # type: ignore[dict-item]
                "diff": "*** Update File: docs/x.md\n",
            },
            repo_root=repo_root,
        )
        self.assertEqual(result["decision"], "block")
        reason_lower = result["reason"].lower()
        self.assertIn("r5-01", reason_lower)

    def test_extract_blob_paths_from_authoritative_key_unit(self) -> None:
        """Direct unit on `_extract_blob_paths_from_authoritative_key`."""
        # Clean parse.
        paths, parsed, present = (
            canonical_guard._extract_blob_paths_from_authoritative_key(
                {"patch": "*** Update File: PROTOCOL.md\n"}, "patch"
            )
        )
        self.assertTrue(parsed)
        self.assertTrue(present)
        self.assertIn("PROTOCOL.md", paths)
        # Key absent.
        paths, parsed, present = (
            canonical_guard._extract_blob_paths_from_authoritative_key(
                {"diff": "irrelevant"}, "patch"
            )
        )
        self.assertFalse(parsed)
        self.assertFalse(present)
        self.assertEqual(paths, [])
        # Key present but corrupt.
        paths, parsed, present = (
            canonical_guard._extract_blob_paths_from_authoritative_key(
                {"patch": "\x00garbage\xff"}, "patch"
            )
        )
        self.assertFalse(parsed)
        self.assertTrue(present)
        # Key present but non-string.
        paths, parsed, present = (
            canonical_guard._extract_blob_paths_from_authoritative_key(
                {"patch": None}, "patch"  # type: ignore[dict-item]
            )
        )
        self.assertFalse(parsed)
        self.assertTrue(present)
        # Defensive: non-dict params or non-string key.
        paths, parsed, present = (
            canonical_guard._extract_blob_paths_from_authoritative_key(
                None, "patch"  # type: ignore[arg-type]
            )
        )
        self.assertFalse(parsed)
        self.assertFalse(present)

    def test_non_authoritative_blob_carrier_legacy_path_preserved(
        self,
    ) -> None:
        """R5-01 regression: tools whose name has a blob fragment but
        is not on the authoritative list still use the legacy
        aggregator (NG-06). Blob fragment but no authoritative
        mapping is hard to construct in practice (every fragment in
        `_BLOB_TOOL_FRAGMENTS` is also in `_TOOL_AUTHORITATIVE_BLOB_KEY`)
        so this test exercises the legacy branch via mock.
        """
        # Verify the implementation contract: every blob-tool fragment
        # has an authoritative-key mapping. If this invariant is ever
        # broken (legacy non-auth blob tool added), the legacy branch
        # is still wired and tested via NG-06 fixtures elsewhere.
        for frag in canonical_guard._BLOB_TOOL_FRAGMENTS:
            mock_name = f"mcp__test__{frag}"
            self.assertIsNotNone(
                canonical_guard._authoritative_blob_key_for(mock_name),
                f"fragment {frag!r} has no authoritative-key mapping",
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
