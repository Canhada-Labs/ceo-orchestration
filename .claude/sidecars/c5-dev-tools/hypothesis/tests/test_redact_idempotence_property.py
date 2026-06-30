"""PLAN-093 Wave B.6 #2 — redact idempotence property.

Property: `redact_secrets(redact_secrets(x)) == redact_secrets(x)` for any
text input within the 64KB cap.

Per `.claude/hooks/_lib/redact.py:8` the idempotence invariant is
documented. This property test exercises it under hypothesis-generated
inputs including unicode codepoints up to U+10FFFF.
"""
from __future__ import annotations

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
from _lib.redact import redact_secrets  # noqa: E402


class RedactIdempotenceProperty(TestEnvContext):
    """redact_secrets is idempotent: f(f(x)) == f(x)."""

    @given(
        st.text(
            alphabet=st.characters(max_codepoint=0x10FFFF, blacklist_categories=("Cs",)),
            min_size=0,
            max_size=4096,
        )
    )
    @settings(max_examples=200, database=None, deadline=None)
    def test_idempotent(self, text: str) -> None:
        once = redact_secrets(text, max_chars=0)
        twice = redact_secrets(once, max_chars=0)
        self.assertEqual(once, twice)

    @given(
        st.text(
            alphabet=st.characters(max_codepoint=0x10FFFF, blacklist_categories=("Cs",)),
            min_size=0,
            max_size=4096,
        )
    )
    @settings(max_examples=200, database=None, deadline=None)
    def test_bounded_growth(self, text: str) -> None:
        """redact(x) length never exceeds 2*len(x) (excluding truncation)."""
        out = redact_secrets(text, max_chars=0)
        self.assertLessEqual(len(out), max(1, len(text) * 2 + 64))


if __name__ == "__main__":
    unittest.main()
