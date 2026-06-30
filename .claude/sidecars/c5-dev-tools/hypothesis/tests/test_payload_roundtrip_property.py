"""PLAN-093 Wave B.6 #1 — payload encode/decode roundtrip invariant.

Property: `parse_text(text)` never raises for any string input; for any
valid JSON-object input, the resulting `HookPayload` preserves the
`session_id` / `cwd` / `transcript_path` string fields verbatim.

Per ADR-131 §C5.1 + ADR-126 §Part 5: this test lives under the C5
hypothesis sidecar; framework hooks/scripts never import hypothesis.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import pytest

# Graceful skip when the C5 hypothesis sidecar isn't installed. A bare
# top-level `from hypothesis import ...` raises ModuleNotFoundError at
# COLLECTION time, which makes pytest exit with the collection-error code
# (2) for the whole run. `importorskip` turns that into a clean module-level
# SKIP instead, so a run without the sidecar reports SKIPPED, not ERROR.
# When hypothesis IS present this is a no-op and the tests run in full.
pytest.importorskip("hypothesis")

from hypothesis import given, settings, strategies as st  # noqa: E402

_REPO = Path(__file__).resolve().parent.parent.parent.parent.parent
_HOOKS = _REPO / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from _lib.testing import TestEnvContext  # noqa: E402
from _lib.payload import parse_text  # noqa: E402


class PayloadRoundtripProperty(TestEnvContext):
    """parse_text is total over str; valid JSON preserves string fields."""

    @given(st.text())
    @settings(max_examples=200, database=None, deadline=None)
    def test_parse_text_total_over_str(self, text: str) -> None:
        """parse_text never raises for any text input (HookPayload.raw_error
        set on malformed JSON; fields fall back to defaults)."""
        payload = parse_text(text)
        self.assertIsNotNone(payload)

    @given(
        session_id=st.text(),
        cwd=st.text(),
        transcript_path=st.text(),
    )
    @settings(max_examples=200, database=None, deadline=None)
    def test_string_field_roundtrip(
        self, session_id: str, cwd: str, transcript_path: str
    ) -> None:
        """For a well-formed JSON object, the public string fields survive
        parse with byte-level equivalence."""
        obj = {
            "session_id": session_id,
            "cwd": cwd,
            "transcript_path": transcript_path,
        }
        text = json.dumps(obj, ensure_ascii=False)
        payload = parse_text(text)
        self.assertEqual(getattr(payload, "session_id", ""), session_id)
        self.assertEqual(getattr(payload, "cwd", ""), cwd)
        self.assertEqual(getattr(payload, "transcript_path", ""), transcript_path)


if __name__ == "__main__":
    unittest.main()
