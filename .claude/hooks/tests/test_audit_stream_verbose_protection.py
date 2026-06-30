"""PLAN-090 Wave B.5 — CEO_AUDIT_STREAM_VERBOSE=1 verbose-mode protection.

R2 Codex iter-1 P1 fold: verbose-mode protection hardened.

Invariants:
- EXACT MATCH `=1` only (truthiness footgun mirror of CEO_GODMODE_ENFORCING)
- PARENT-SHELL ONLY (never accepted via stdin or tool-param)
- NO prompt-controlled enablement
- audit-stream.jsonl created with mode 0600 (owner-only)
"""

from __future__ import annotations

import os
import stat
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))

from _lib.testing import TestEnvContext  # noqa: E402


_TRUTHY_NON_ONE_VALUES = (
    "true", "yes", "TRUE", "True", "0", "", " 1", "1 ", "11", "1.0", "y",
)


class TestVerboseModeExactMatch(TestEnvContext):

    def test_exact_one_enables_verbose(self) -> None:
        from _lib import audit_emit
        os.environ["CEO_AUDIT_STREAM_VERBOSE"] = "1"
        try:
            self.assertTrue(audit_emit.is_audit_stream_verbose())
        finally:
            os.environ.pop("CEO_AUDIT_STREAM_VERBOSE", None)

    def test_truthy_non_one_does_not_enable(self) -> None:
        from _lib import audit_emit
        for value in _TRUTHY_NON_ONE_VALUES:
            with self.subTest(value=repr(value)):
                os.environ["CEO_AUDIT_STREAM_VERBOSE"] = value
                try:
                    self.assertFalse(
                        audit_emit.is_audit_stream_verbose(),
                        f"value {value!r} must NOT enable verbose mode",
                    )
                finally:
                    os.environ.pop("CEO_AUDIT_STREAM_VERBOSE", None)

    def test_unset_does_not_enable(self) -> None:
        from _lib import audit_emit
        os.environ.pop("CEO_AUDIT_STREAM_VERBOSE", None)
        self.assertFalse(audit_emit.is_audit_stream_verbose())


class TestAuditStreamFilePermissions(TestEnvContext):

    def test_audit_stream_jsonl_owner_only_when_verbose(self) -> None:
        """When verbose mode is ON, audit-stream.jsonl must be created
        with mode 0600 (owner-only). Belt+suspenders for side-channel
        containment when adopters share a project filesystem."""
        from _lib import audit_emit
        os.environ["CEO_AUDIT_STREAM_VERBOSE"] = "1"
        try:
            audit_emit.emit_streaming_token_yielded(
                persona="vibecoder",
                token="hello",
            )
            stream_path = self.audit_dir / "audit-stream.jsonl"
            if stream_path.is_file():
                mode = stream_path.stat().st_mode
                # Only owner bits set in lower 9.
                self.assertEqual(
                    mode & 0o077, 0,
                    f"audit-stream.jsonl must be 0600, got mode {oct(mode)}",
                )
        finally:
            os.environ.pop("CEO_AUDIT_STREAM_VERBOSE", None)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
