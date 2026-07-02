"""PLAN-085 Wave C.1 — live_adapter_allowlist runtime gate tests.

6 cases covering ADR-040 §6.3 fail-CLOSED matrix:

  1. test_allowlist_pass             — provider in list → activation_check returns None
  2. test_allowlist_deny             — provider not in list → DENY reason=not_in_allowlist
  3. test_missing_file_fails_closed  — .claude/settings.json absent → DENY allowlist_unreadable
  4. test_malformed_json_fails_closed — JSON parse error → DENY allowlist_unreadable
  5. test_empty_list_fails_closed    — [] → DENY reason=empty_allowlist
  6. test_schema_validation          — `live_adapter_allowlist: "claude"` (string not list) → DENY allowlist_unreadable

Discipline: stdlib-only, Python >= 3.9, from __future__ annotations,
typing.Optional/Union, TestEnvContext for env isolation.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_HOOKS = REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from _lib.testing import TestEnvContext  # noqa: E402


class _EmitCapture:
    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    def emit_live_adapter_blocked(self, **kw: Any) -> None:
        self.calls.append({"action": "live_adapter_blocked", **kw})


class TestLiveAdapterAllowlistRuntime(TestEnvContext):
    def setUp(self) -> None:
        super().setUp()
        import os
        os.environ["CEO_LIVE_CLAUDE"] = "1"
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-fixture-not-real"
        # Prevent credential-age check from interfering (no rotation log).
        # _check_credential_age fails-OPEN on missing file.
        self.settings = (
            self.project_dir / ".claude" / "settings.json"
        )
        self.settings.parent.mkdir(parents=True, exist_ok=True)

    def _write_settings(self, body: Any) -> None:
        if isinstance(body, str):
            self.settings.write_text(body, encoding="utf-8")
        else:
            self.settings.write_text(json.dumps(body), encoding="utf-8")

    def _make_adapter_and_capture(self) -> tuple:
        from _lib.adapters.live.claude import ClaudeLiveAdapter
        from _lib import audit_emit as _real
        capture = _EmitCapture()
        # `from _lib import audit_emit` returns the package attribute once
        # _lib.audit_emit has been imported anywhere (which testing.py
        # transitively triggers). Overriding sys.modules alone misses
        # the attribute lookup; overriding the real module's function
        # attribute guarantees the patched code sees the capture.
        self._restore_emits: Dict[str, Any] = {}
        for name in ("emit_live_adapter_blocked",):
            self._restore_emits[name] = getattr(_real, name, None)
            setattr(_real, name, getattr(capture, name))
        return ClaudeLiveAdapter(), capture

    def tearDown(self) -> None:
        try:
            from _lib import audit_emit as _real
            for name, orig in getattr(self, "_restore_emits", {}).items():
                if orig is None:
                    try:
                        delattr(_real, name)
                    except AttributeError:
                        pass
                else:
                    setattr(_real, name, orig)
        finally:
            super().tearDown()

    # ------------------------------------------------------------------
    # Cases 1-6
    # ------------------------------------------------------------------

    def test_allowlist_pass(self) -> None:
        self._write_settings({"live_adapter_allowlist": ["claude", "openai"]})
        adapter, capture = self._make_adapter_and_capture()
        result = adapter._activation_check()
        self.assertIsNone(result)
        # No block events emitted.
        self.assertEqual(
            [c for c in capture.calls if c["action"] == "live_adapter_blocked"],
            [],
        )

    def test_allowlist_deny(self) -> None:
        self._write_settings({"live_adapter_allowlist": ["gemini"]})
        adapter, capture = self._make_adapter_and_capture()
        result = adapter._activation_check()
        self.assertIsNotNone(result)
        self.assertIn("live_adapter_blocked", str(result))
        self.assertIn("not_in_allowlist", str(result))
        events = [
            c for c in capture.calls if c["action"] == "live_adapter_blocked"
        ]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["reason"], "not_in_allowlist")
        self.assertEqual(events[0]["provider"], "claude")

    def test_missing_file_fails_closed(self) -> None:
        # Ensure no settings.json exists.
        if self.settings.exists():
            self.settings.unlink()
        adapter, capture = self._make_adapter_and_capture()
        result = adapter._activation_check()
        self.assertIsNotNone(result)
        self.assertIn("allowlist_unreadable", str(result))
        events = [
            c for c in capture.calls if c["action"] == "live_adapter_blocked"
        ]
        self.assertEqual(events[0]["reason"], "allowlist_unreadable")

    def test_malformed_json_fails_closed(self) -> None:
        self._write_settings("this is { not json")
        adapter, capture = self._make_adapter_and_capture()
        result = adapter._activation_check()
        self.assertIn("allowlist_unreadable", str(result))

    def test_empty_list_fails_closed(self) -> None:
        self._write_settings({"live_adapter_allowlist": []})
        adapter, capture = self._make_adapter_and_capture()
        result = adapter._activation_check()
        self.assertIsNotNone(result)
        self.assertIn("empty_allowlist", str(result))
        events = [
            c for c in capture.calls if c["action"] == "live_adapter_blocked"
        ]
        self.assertEqual(events[0]["reason"], "empty_allowlist")

    def test_schema_validation(self) -> None:
        # `live_adapter_allowlist` is a string, not a list — schema mismatch.
        self._write_settings({"live_adapter_allowlist": "claude"})
        adapter, capture = self._make_adapter_and_capture()
        result = adapter._activation_check()
        self.assertIn("allowlist_unreadable", str(result))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
