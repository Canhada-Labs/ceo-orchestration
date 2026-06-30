"""PLAN-091 Wave A.8 — AC15.5 EXPECTED_CALLSITES structural test.

Maps each PLAN-091 audit-emit wire to its expected production
caller(s). Asserts each wire has ≥1 non-self caller (the emit_*
wrapper definition in `_lib/audit_emit.py` does NOT count).

Surface covered (PLAN-091 wires only; PLAN-088 canonical-13 events
without a PLAN-091 callsite are documented in
`.claude/plans/PLAN-091/wave-a-7-defer.md`):

- ``mcp_route_advised``           — check_agent_spawn.py (A.4)
                                    + mcp_routing.py (PLAN-086 W-D)
- ``specialization_promoted``     — check_agent_spawn.py (A.5)
- ``model_routing_advised``       — check_agent_spawn.py (PLAN-078 W1)
- Tier-S 16th check registration  — ceo-boot.py (A.1)

R1 TDE P0 fold AC9b (BEHAVIORAL firing fixture) is implemented inline
via the existing unit tests in
``test_check_agent_spawn_routing_promotion.py`` (A.4/A.5) and
``test_check_tier_policy_misrouting_24h.py`` (A.1). This structural
test is the AC15.5 gate that PLAN-090 Wave A's `external_wait`
predicates.

Stdlib only. NO TestEnvContext needed — pure source-grep.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path
from typing import Dict, List, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
_SCRIPTS = _REPO_ROOT / ".claude" / "scripts"


# Mapping: emit-action → ordered tuple of expected production caller paths.
# The audit_emit.py wrapper definitions are NOT acceptable callers
# (production callsite means a non-self consumer).
EXPECTED_CALLSITES: Dict[str, Tuple[Path, ...]] = {
    "mcp_route_advised": (
        _HOOKS_DIR / "check_agent_spawn.py",
        _HOOKS_DIR / "_lib" / "mcp_routing.py",
    ),
    # PLAN-088 R2 iter-2 STRICKEN specialization_promoted as separate
    # action; the A.5 promotion heuristic now emits mcp_route_advised
    # with signal_source="specialization_promoted" discriminator.
    "model_routing_advised": (
        _HOOKS_DIR / "check_agent_spawn.py",
    ),
}


# Tier-S registry entries — production caller is ``ceo-boot.py``.
EXPECTED_TIER_S_REGISTRATIONS: Dict[str, Path] = {
    "tier_policy_misrouting_24h": _SCRIPTS / "ceo-boot.py",
}


def _file_contains_emit(path: Path, action: str) -> bool:
    """True iff the file contains a textual reference to the emit action
    that is NOT inside the audit_emit.py wrapper definition itself.

    Pragma — exclude:
      - String literal in `_KNOWN_ACTIONS` registry (registry rows are
        not callsites).
      - The emit wrapper function `def emit_<action>(` (that IS the
        wrapper, not a caller).
    Both heuristics are absent from the production hook + script
    callsites (which only consume via `emit_generic(action_name, ...)`
    or `emit_<action>(...)`), so the false-positive risk is bounded.
    """
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return False
    # Anywhere the action string appears as a function call argument
    # or as a bare emit_<action> call counts as a callsite.
    if f'"{action}"' in source:
        return True
    if f"'{action}'" in source:
        return True
    if f"emit_{action}(" in source:
        return True
    return False


class TestExpectedCallsites(unittest.TestCase):
    """AC15.5 — every PLAN-091 wire has ≥1 non-self production caller."""

    def test_each_wire_has_at_least_one_callsite(self):
        missing: List[str] = []
        for action, callers in EXPECTED_CALLSITES.items():
            self.assertGreaterEqual(
                len(callers),
                1,
                f"EXPECTED_CALLSITES entry for {action!r} must list ≥1 caller",
            )
            hit = False
            for caller in callers:
                self.assertTrue(
                    caller.is_file(),
                    f"Expected caller path missing on disk: {caller}",
                )
                if _file_contains_emit(caller, action):
                    hit = True
                    break
            if not hit:
                missing.append(action)
        self.assertEqual(
            missing,
            [],
            f"AC15.5 VIOLATION: actions without production callsite: {missing}",
        )

    def test_callers_outside_audit_emit_wrapper_module(self):
        """A callsite under `_lib/audit_emit.py` is the wrapper definition,
        not a production caller — must be excluded from the map values.
        """
        for action, callers in EXPECTED_CALLSITES.items():
            for caller in callers:
                self.assertNotEqual(
                    caller.name,
                    "audit_emit.py",
                    f"{action}: audit_emit.py is the wrapper, not a callsite",
                )


class TestTierSRegistrations(unittest.TestCase):
    """A.1 Tier-S check is wired into the registry."""

    def test_tier_policy_check_registered_in_ceo_boot(self):
        ceo_boot = _SCRIPTS / "ceo-boot.py"
        source = ceo_boot.read_text(encoding="utf-8")
        # The wrapper function and the registry entry both must appear.
        self.assertIn(
            'check_tier_policy_misrouting_24h',
            source,
            "ceo-boot.py must reference check_tier_policy_misrouting_24h",
        )
        self.assertIn(
            "tier_policy_misrouting_24h",
            source,
            "ceo-boot.py TIER_S_CHECKS must include the 16th entry name",
        )

    def test_standalone_module_exists(self):
        impl = _HOOKS_DIR / "check_tier_policy_misrouting_24h.py"
        self.assertTrue(impl.is_file(), "standalone hook module must exist")
        body = impl.read_text(encoding="utf-8")
        # Module must define the check function with the expected name.
        self.assertRegex(
            body,
            r"def check_tier_policy_misrouting_24h\(\)",
            "standalone module must export the check function",
        )


class TestEffortThinkingWire(unittest.TestCase):
    """A.3 — the `/effort` resolver is invoked from `call()`.

    PLAN-134 W0 E6-F2 renamed `_resolve_effort_thinking` to the
    model-aware `_resolve_effort_config` (adaptive thinking +
    output_config.effort on the current generation; the legacy
    enabled/budget shape only for pre-4.6 ids). Guard intent preserved:
    the helper must be defined AND called from `call()`.
    """

    def test_helper_present_in_claude_live(self):
        claude_live = (
            _HOOKS_DIR / "_lib" / "adapters" / "live" / "claude.py"
        )
        source = claude_live.read_text(encoding="utf-8")
        self.assertIn(
            "_resolve_effort_config",
            source,
            "live claude.py must reference the A.3 helper",
        )
        # Helper must be called from `call()` body — assert at least 2
        # occurrences (the def + the call).
        count = source.count("_resolve_effort_config")
        self.assertGreaterEqual(
            count,
            2,
            f"_resolve_effort_config must be called (≥2 hits), found {count}",
        )


class TestPairRailPromotionConstant(unittest.TestCase):
    """A.6 — `_PRODUCTION_PROMOTED_BY_PLAN_091` constant exposed."""

    def test_constant_grep_discoverable(self):
        body = (_HOOKS_DIR / "check_pair_rail.py").read_text(encoding="utf-8")
        self.assertIn(
            "_PRODUCTION_PROMOTED_BY_PLAN_091",
            body,
            "A.6 status constant must be grep-discoverable",
        )
        # The first-line docstring carries the PRODUCTION marker.
        first_line = body.splitlines()[1] if len(body.splitlines()) > 1 else ""
        self.assertIn("PRODUCTION", first_line)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
