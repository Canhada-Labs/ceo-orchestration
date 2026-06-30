"""PLAN-090 Wave A.5 — persona_routing enforcing-mode matrix tests.

52-cell matrix (4 personas × 13 primitives):
- AUTO-01..AUTO-10 → enforcing post-AMEND-1
- SEMI-11..SEMI-13 → advisory (unchanged)

Uses TestEnvContext isolation so the live module's
_PRIMITIVE_DEFAULT_MODE constant is NOT mutated by tests.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))

from _lib.testing import TestEnvContext  # noqa: E402


_PERSONAS = ("vibecoder", "junior_dev", "skeptical_cto", "team_member")

_AUTO_PRIMITIVES = (
    "AUTO-01", "AUTO-02", "AUTO-03", "AUTO-04", "AUTO-05",
    "AUTO-06", "AUTO-07", "AUTO-08", "AUTO-09", "AUTO-10",
)
_SEMI_PRIMITIVES = ("SEMI-11", "SEMI-12", "SEMI-13")


class TestPersonaRoutingEnforcing(TestEnvContext):
    """52-cell persona × primitive matrix.

    Assertions:
    - AUTO-01..AUTO-10 ENFORCING for every persona (40 cells)
    - SEMI-11..SEMI-13 ADVISORY for every persona (12 cells)
    """

    def setUp(self) -> None:
        super().setUp()
        # Force-reload so test order does not depend on prior session emits.
        import importlib
        from _lib import persona_routing as _pr
        importlib.reload(_pr)
        self.persona_routing = _pr

    def test_auto_primitives_enforcing_all_personas(self) -> None:
        for persona in _PERSONAS:
            for primitive in _AUTO_PRIMITIVES:
                mode = self.persona_routing.get_mode(persona, primitive)
                self.assertEqual(
                    mode, "enforcing",
                    f"AUTO primitive {primitive} for persona {persona}: "
                    f"expected 'enforcing', got {mode!r}",
                )

    def test_semi_primitives_advisory_all_personas(self) -> None:
        for persona in _PERSONAS:
            for primitive in _SEMI_PRIMITIVES:
                mode = self.persona_routing.get_mode(persona, primitive)
                self.assertEqual(
                    mode, "advisory",
                    f"SEMI primitive {primitive} for persona {persona}: "
                    f"expected 'advisory', got {mode!r}",
                )

    def test_unknown_persona_falls_back_to_default(self) -> None:
        # Unknown personas resolve to defaults (no per-persona override yet).
        for primitive in _AUTO_PRIMITIVES:
            mode = self.persona_routing.get_mode("unknown_persona", primitive)
            self.assertEqual(mode, "enforcing", primitive)

    def test_unknown_primitive_returns_disabled(self) -> None:
        for persona in _PERSONAS:
            mode = self.persona_routing.get_mode(persona, "AUTO-99")
            self.assertEqual(mode, "disabled", persona)

    def test_known_primitives_count_is_thirteen(self) -> None:
        primitives = self.persona_routing.known_primitives()
        self.assertEqual(
            len(primitives), 13,
            f"expected 13 canonical primitives, got {len(primitives)}",
        )

    def test_personas_count_is_four(self) -> None:
        personas = self.persona_routing.known_personas()
        self.assertEqual(
            len(personas), 4,
            f"expected 4 personas, got {len(personas)}",
        )

    def test_kill_switch_restores_advisory_all_cells(self) -> None:
        os.environ["CEO_GODMODE_ENFORCING"] = "0"
        try:
            for persona in _PERSONAS:
                for primitive in _AUTO_PRIMITIVES + _SEMI_PRIMITIVES:
                    mode = self.persona_routing.get_mode(persona, primitive)
                    self.assertEqual(
                        mode, "advisory",
                        f"kill-switch must restore ADVISORY for "
                        f"{persona}/{primitive}, got {mode!r}",
                    )
        finally:
            os.environ.pop("CEO_GODMODE_ENFORCING", None)

    def test_is_enforcing_helper(self) -> None:
        # Default state (no kill-switch).
        self.assertTrue(self.persona_routing.is_enforcing(
            "vibecoder", "AUTO-01"))
        self.assertFalse(self.persona_routing.is_enforcing(
            "vibecoder", "SEMI-11"))
        self.assertFalse(self.persona_routing.is_enforcing(
            "vibecoder", "AUTO-99"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
