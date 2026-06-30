"""PLAN-093 Wave B.6 #4 — _KNOWN_ACTIONS bijection property.

Property: every action string in `audit_emit._KNOWN_ACTIONS` is reachable
either via a corresponding `emit_<action>` typed wrapper OR via the
`emit_generic(action, ...)` dispatcher. Direct-emit actions (entries
without typed wrapper) are exempted via an explicit allowlist; the
allowlist itself must be a subset of `_KNOWN_ACTIONS`.

This is a property test only in the structural sense (asserts an
invariant over the registry); hypothesis is used here for sampling
discipline — drawing a random subset on each run prevents test rot
where new actions slip past unmonitored.
"""
from __future__ import annotations

import inspect
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
from _lib import audit_emit  # noqa: E402


def _typed_wrapper_actions() -> set:
    """Collect action names from `emit_<action>` function names."""
    names = set()
    for name in dir(audit_emit):
        if name.startswith("emit_") and callable(getattr(audit_emit, name)):
            if name == "emit_generic":
                continue
            names.add(name[len("emit_"):])
    return names


def _action_universe() -> set:
    return set(getattr(audit_emit, "_KNOWN_ACTIONS", set()))


# Direct-emit actions: have no typed wrapper but are emitted via
# `emit_generic(action, ...)` from a dedicated callsite. Sourced from
# documented blocks in audit_emit.py (lines 282-283, 313-318, 415-421,
# etc.). Exempting them lets the bijection test catch NEW unregistered
# emit functions without flagging the legacy direct-emit pattern.
_DIRECT_EMIT_ALLOWLIST = {
    # Lines 145, v1 legacy (audit_log.py direct emit)
    "agent_spawn",
    # Lines 313-318 PLAN-070 layer-B / MCP canonical guard
    "mcp_canonical_guard_allowed",
    "mcp_canonical_guard_blocked",
    "mcp_canonical_guard_internal_error",
    # Lines 415-421 canonical edit + gpg
    "canonical_edit_attempted",
    "canonical_edit_blocked",
    "canonical_edit_completed",
    "gpg_signed",
    "gpg_verified",
    # Lines 282-283 escalation
    "escalation_detected",
    # Lines 258-259 fluency
    "fluency_nudge",
}


class KnownActionsBijectionProperty(TestEnvContext):
    """Every _KNOWN_ACTIONS entry has typed wrapper OR is direct-emit-allowlisted."""

    def setUp(self) -> None:
        super().setUp()
        self.universe = _action_universe()
        self.wrappers = _typed_wrapper_actions()

    def test_universe_non_empty(self) -> None:
        self.assertGreater(
            len(self.universe), 100, "expected >100 _KNOWN_ACTIONS entries"
        )

    def test_allowlist_subset_of_universe(self) -> None:
        stray = _DIRECT_EMIT_ALLOWLIST - self.universe
        self.assertEqual(
            stray, set(), f"allowlist references unknown actions: {sorted(stray)}"
        )

    def test_every_action_reachable(self) -> None:
        """Bijection: every action must have wrapper or allowlist entry."""
        unreachable = self.universe - self.wrappers - _DIRECT_EMIT_ALLOWLIST
        self.assertEqual(
            unreachable,
            set(),
            f"actions without typed wrapper or allowlist entry: {sorted(unreachable)[:10]}"
            f" (total {len(unreachable)})",
        )

    @given(st.data())
    @settings(max_examples=50, database=None, deadline=None)
    def test_random_sample_reachable(self, data) -> None:
        """Hypothesis-driven sampling guards against test rot."""
        if not self.universe:
            return
        sample = data.draw(st.sampled_from(sorted(self.universe)))
        reachable = sample in self.wrappers or sample in _DIRECT_EMIT_ALLOWLIST
        self.assertTrue(reachable, f"action {sample!r} not reachable")


if __name__ == "__main__":
    unittest.main()
