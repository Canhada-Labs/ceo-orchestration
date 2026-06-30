"""PLAN-093 Wave B.6 #3 — canonical_guard.check_mcp_call total function.

Property: `check_mcp_call(tool_name, params, repo_root)` returns a dict
with `decision` + `reason` keys for ANY input shape. Never raises (per
`.claude/hooks/_lib/mcp/canonical_guard.py:1076` universal fail-CLOSED).
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
from _lib.mcp.canonical_guard import check_mcp_call  # noqa: E402


_DECISIONS = {"allow", "block"}


class CanonicalGuardSymmetryProperty(TestEnvContext):
    """check_mcp_call is total: every call returns a well-formed dict."""

    @given(
        tool_name=st.one_of(st.text(min_size=0, max_size=256), st.none()),
        params=st.one_of(
            st.none(),
            st.dictionaries(
                keys=st.text(min_size=0, max_size=64),
                values=st.one_of(
                    st.text(min_size=0, max_size=128),
                    st.integers(),
                    st.booleans(),
                    st.none(),
                ),
                max_size=8,
            ),
        ),
    )
    @settings(max_examples=200, database=None, deadline=None)
    def test_total_function(self, tool_name, params) -> None:
        result = check_mcp_call(tool_name, params, None)
        self.assertIsInstance(result, dict)
        self.assertIn("decision", result)
        self.assertIn("reason", result)
        self.assertIn(result["decision"], _DECISIONS)
        self.assertIsInstance(result["reason"], str)


if __name__ == "__main__":
    unittest.main()
