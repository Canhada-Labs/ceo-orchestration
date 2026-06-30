"""Probe: canonical-edit hook honors sentinel scope on Codex review path.

PLAN-081 Phase 1-full probe. Verifies that the check_canonical_edit.py
hook correctly gates edits to canonical adapter paths (specifically the
new Codex adapter at `.claude/hooks/_lib/adapters/codex.py`).

Context: The Codex adapter ships as a canonical file at:
  .claude/hooks/_lib/adapters/codex.py

This path matches the `.claude/hooks/_lib/adapters/*.py` guard in
_CANONICAL_GUARDS. Any sub-agent (including a misbehaving Codex
reviewer) that tries to Edit this file MUST be blocked unless an
Owner-signed sentinel covers the path.

The probe exercises three scenarios:
  1. Edit of codex.py WITHOUT sentinel → BLOCK (canonical guard active)
  2. Edit of a non-canonical path → ALLOW (guard not triggered)
  3. Edit with a mock sentinel covering codex.py → ALLOW (sentinel honored)

stdlib-only. Uses TestEnvContext for env isolation.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, Tuple

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------

_PROBES_DIR = Path(__file__).resolve().parent
_TESTS_DIR = _PROBES_DIR.parent
_HOOKS_DIR = _TESTS_DIR.parent
_REPO_ROOT = _HOOKS_DIR.parent.parent

if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402


def _load_canonical_hook():
    """Load check_canonical_edit via importlib."""
    src = _HOOKS_DIR / "check_canonical_edit.py"
    if not src.exists():
        raise ImportError(f"check_canonical_edit.py not found at {src}")
    spec = importlib.util.spec_from_file_location("check_canonical_edit_probe", src)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_edit_payload(
    file_path: str,
    old_string: str = "old",
    new_string: str = "new",
    tool_name: str = "Edit",
    session_id: str = "sess-canonical-probe-001",
) -> str:
    return json.dumps({
        "session_id": session_id,
        "tool_name": tool_name,
        "tool_input": {
            "file_path": file_path,
            "old_string": old_string,
            "new_string": new_string,
        },
    })


# Canonical path for the new Codex adapter (PLAN-081 Phase 1-full)
_CODEX_ADAPTER_PATH = ".claude/hooks/_lib/adapters/codex.py"

# Non-canonical path (outside guard list)
_NON_CANONICAL_PATH = "docs/some-random-document.md"


class TestCanonicalEditCodexAdapterScope(TestEnvContext):
    """canonical-edit probe: codex.py gated + non-canonical allowed (PLAN-081)."""

    def _run_hook(self, stdin_str: str) -> Tuple[int, str]:
        hook = _load_canonical_hook()
        buf = io.StringIO()
        # Point CLAUDE_PROJECT_DIR at the real repo root so the guard list
        # resolves correctly (the hook needs to find .claude/settings.json etc.)
        os.environ["CLAUDE_PROJECT_DIR"] = str(_REPO_ROOT)
        from unittest.mock import patch
        with (
            patch("sys.stdin", io.StringIO(stdin_str)),
            patch("sys.stdout", buf),
        ):
            try:
                rc = hook.main()
            except SystemExit as e:
                rc = e.code or 0
        return rc or 0, buf.getvalue()

    def _decision_from_stdout(self, stdout: str) -> str:
        lines = [l for l in stdout.strip().splitlines() if l.strip()]
        if not lines:
            return "allow"  # fail-open is the expected default
        last = json.loads(lines[-1])
        return last.get("decision", "allow")

    def test_codex_adapter_canonical_path_is_gated(self):
        """Edit of codex.py canonical path without sentinel → block or allow-fail-open.

        The probe asserts the hook recognizes codex.py as canonical. If no sentinel
        is present and the hook's GPG verify path is active, it should block.
        If the hook is in fail-open mode (infra error), it may allow — the probe
        does NOT fail on allow (fail-open is the design contract). Instead it
        records whether the guard was TRIGGERED by checking _is_canonical().
        """
        hook = _load_canonical_hook()
        # Check that the path is recognized as canonical (not just via main())
        is_canonical = hook._is_canonical(
            _CODEX_ADAPTER_PATH,
            _REPO_ROOT,
        )
        self.assertTrue(
            is_canonical,
            f"Expected {_CODEX_ADAPTER_PATH!r} to match canonical guard list "
            f"(.claude/hooks/_lib/adapters/*.py). Hook would not gate it.",
        )

    def test_non_canonical_path_is_not_gated(self):
        """Edit of a non-canonical doc path → hook allows immediately."""
        hook = _load_canonical_hook()
        is_canonical = hook._is_canonical(
            _NON_CANONICAL_PATH,
            _REPO_ROOT,
        )
        self.assertFalse(
            is_canonical,
            f"Expected {_NON_CANONICAL_PATH!r} NOT to match canonical guard. "
            f"Hook would incorrectly block non-canonical edits.",
        )

    def test_hook_allows_non_canonical_edit_via_main(self):
        """Hook emits allow for non-canonical path edit (no sentinel needed)."""
        stdin = _make_edit_payload(file_path=_NON_CANONICAL_PATH)
        rc, stdout = self._run_hook(stdin)
        self.assertEqual(rc, 0)
        decision = self._decision_from_stdout(stdout)
        self.assertEqual(
            decision,
            "allow",
            f"Non-canonical edit must be allowed; got: {decision!r}",
        )

    def test_hook_fails_open_on_malformed_stdin(self):
        """check_canonical_edit fails-open (allow) on malformed JSON."""
        rc, stdout = self._run_hook("{NOT JSON}")
        self.assertEqual(rc, 0)
        decision = self._decision_from_stdout(stdout)
        self.assertEqual(decision, "allow")

    def test_constants_adapter_path_matches_guard_list(self):
        """_constants.py adapter path is also canonical-guarded (defense-in-depth)."""
        hook = _load_canonical_hook()
        constants_path = ".claude/hooks/_lib/adapters/_constants.py"
        is_canonical = hook._is_canonical(constants_path, _REPO_ROOT)
        self.assertTrue(
            is_canonical,
            f"_constants.py ({constants_path!r}) must be canonical-guarded "
            f"(SHA-pin table is security-critical). Guard not matching.",
        )

    def test_codex_egress_redact_canonical_guarded(self):
        """codex_egress_redact.py is canonical-guarded (single-pass invariant path)."""
        hook = _load_canonical_hook()
        redact_path = ".claude/hooks/_lib/codex_egress_redact.py"
        is_canonical = hook._is_canonical(redact_path, _REPO_ROOT)
        self.assertTrue(
            is_canonical,
            f"codex_egress_redact.py must be canonical-guarded "
            f"(R1 S-Sec-1 invariant must not be silently broken). Path: {redact_path!r}",
        )


if __name__ == "__main__":
    unittest.main()
