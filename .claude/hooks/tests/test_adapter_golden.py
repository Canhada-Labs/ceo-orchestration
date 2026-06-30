"""Cross-adapter golden-fixture conformance tests.

Sprint 5 Phase 4. Locks the adapter contract via byte-exact fixtures so
adding a new IDE adapter (Gemini CLI, Codex CLI, etc.) is a
fixture-comparison exercise — not a guessing game about field naming.

## Fixture layout

    tests/fixtures/normalized/<scenario>.json
        Canonical NormalizedEvent serialization (asdict()) for the
        scenario. Adapter-agnostic.

    tests/fixtures/adapters/<adapter>/in/<scenario>.json
        Wire-shape input (stdin payload) the adapter receives in this
        scenario. Bytes-identical to what the IDE actually sends.

    tests/fixtures/adapters/<adapter>/out/<decision_key>.json
        Wire-shape output (stdout JSON) the adapter writes for a given
        Decision. Decision keys are stable identifiers (`allow`,
        `block_with_reason`, etc.).

A new adapter passes the suite when:
1. Its `read_event(stdin)` parses every `<scenario>.json` under
   `adapters/<adapter>/in/` into a NormalizedEvent that round-trips to
   the same dict as the canonical `normalized/<scenario>.json`.
2. Its `write_decision(decision)` produces output byte-equivalent to
   the corresponding `adapters/<adapter>/out/<decision_key>.json`.

ADR-012 codifies this contract.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict

# Make _lib importable
_HOOKS_DIR = Path(__file__).resolve().parent.parent

from _lib import contract  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


_FIXTURES_ROOT = Path(__file__).resolve().parent / "fixtures"
_NORMALIZED_DIR = _FIXTURES_ROOT / "normalized"
_ADAPTERS_DIR = _FIXTURES_ROOT / "adapters"


def _load_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def _normalized_to_dict(ev: contract.NormalizedEvent) -> Dict[str, Any]:
    """Convert NormalizedEvent to plain dict (ignores `raw_payload`)."""
    d = asdict(ev)
    # raw_payload is adapter-implementation-detail; not part of contract
    d.pop("raw_payload", None)
    return d


class GoldenFixturesTest(TestEnvContext):
    """Verify every shipping adapter conforms to the wire-shape contract."""

    def test_known_adapters_have_in_fixtures(self):
        """Every KNOWN_ADAPTER must ship an `in/` fixture directory."""
        for name in contract.KNOWN_ADAPTERS:
            in_dir = _ADAPTERS_DIR / name / "in"
            self.assertTrue(
                in_dir.is_dir(),
                f"missing {in_dir} — adapter '{name}' has no input fixtures",
            )

    def test_known_adapters_have_out_fixtures(self):
        """Every KNOWN_ADAPTER must ship an `out/` fixture directory."""
        for name in contract.KNOWN_ADAPTERS:
            out_dir = _ADAPTERS_DIR / name / "out"
            self.assertTrue(
                out_dir.is_dir(),
                f"missing {out_dir} — adapter '{name}' has no output fixtures",
            )

    def test_normalized_fixtures_present(self):
        """Each scenario in `in/` must have a matching `normalized/` file."""
        for name in contract.KNOWN_ADAPTERS:
            in_dir = _ADAPTERS_DIR / name / "in"
            for in_file in sorted(in_dir.glob("*.json")):
                norm_file = _NORMALIZED_DIR / in_file.name
                self.assertTrue(
                    norm_file.is_file(),
                    f"missing canonical {norm_file} for adapter scenario "
                    f"{name}/in/{in_file.name}",
                )

    def test_claude_in_fixtures_round_trip_to_normalized(self):
        """For each `claude/in/<scenario>.json`, parse with the claude
        adapter and verify the resulting NormalizedEvent matches the
        canonical `normalized/<scenario>.json`."""
        from _lib.adapters import claude as claude_adapter
        import io

        in_dir = _ADAPTERS_DIR / "claude" / "in"
        for in_file in sorted(in_dir.glob("*.json")):
            with self.subTest(scenario=in_file.name):
                raw = in_file.read_text(encoding="utf-8")
                # PLAN-006 Phase 1 pre-work (ADR-014, R-SB1): the phase
                # parameter is now explicit. Derive it from the fixture's
                # normalized counterpart to keep fixtures self-describing.
                expected_for_phase = _load_json(_NORMALIZED_DIR / in_file.name)
                phase = expected_for_phase.get("phase", "PreToolUse")
                ev = claude_adapter.read_event(io.StringIO(raw), phase=phase)
                self.assertIsNone(
                    ev.parse_error,
                    f"adapter parse_error for {in_file.name}: {ev.parse_error}",
                )

                actual = _normalized_to_dict(ev)
                expected = _load_json(_NORMALIZED_DIR / in_file.name)
                expected.pop("raw_payload", None)

                # `project` is env-dependent (CLAUDE_PROJECT_DIR); compare
                # against whatever the adapter resolved at parse time.
                expected["project"] = actual["project"]

                self.assertEqual(
                    actual,
                    expected,
                    f"mismatch for adapter=claude scenario={in_file.name}",
                )

    def test_claude_write_decision_allow(self):
        """A vanilla allow Decision serializes to the canonical allow fixture."""
        from _lib.adapters import claude as claude_adapter

        out = claude_adapter.write_decision(contract.allow())
        expected = (_ADAPTERS_DIR / "claude" / "out" / "allow.json").read_text(
            encoding="utf-8"
        ).rstrip("\n")
        self.assertEqual(out, expected)

    def test_claude_write_decision_block_with_reason(self):
        """A block Decision with reason+systemMessage matches the fixture."""
        from _lib.adapters import claude as claude_adapter

        out = claude_adapter.write_decision(
            contract.block(
                reason="missing_skill_content",
                system_message="Spawn blocked: prompt has no ## SKILL CONTENT section",
            )
        )
        expected = (_ADAPTERS_DIR / "claude" / "out" / "block_with_reason.json").read_text(
            encoding="utf-8"
        ).rstrip("\n")
        self.assertEqual(out, expected)


class ResolveAdapterTest(TestEnvContext):
    """Sprint 5: CEO_HOOK_ADAPTER env-var dispatch."""

    def test_resolve_adapter_default(self):
        os.environ.pop("CEO_HOOK_ADAPTER", None)
        self.assertEqual(contract.resolve_adapter(), "claude")

    def test_resolve_adapter_known(self):
        os.environ["CEO_HOOK_ADAPTER"] = "claude"
        self.assertEqual(contract.resolve_adapter(), "claude")

    def test_resolve_adapter_unknown_falls_back(self):
        # PLAN-006 added gemini to KNOWN_ADAPTERS (Sprint 6 Phase 2a).
        # PLAN-081 Phase 1-full added "codex" to KNOWN_ADAPTERS (2026-05-09).
        # Pick a name that stays unknown to keep this test future-proof.
        os.environ["CEO_HOOK_ADAPTER"] = "vertex-ai-fictional"
        self.assertEqual(contract.resolve_adapter(), "claude")

    def test_resolve_adapter_empty_falls_back(self):
        os.environ["CEO_HOOK_ADAPTER"] = ""
        self.assertEqual(contract.resolve_adapter(), "claude")

    def test_resolve_adapter_explicit_env_override(self):
        # Pass env explicitly (no os.environ mutation)
        env = {"CEO_HOOK_ADAPTER": "claude"}
        self.assertEqual(contract.resolve_adapter(env=env), "claude")
        env = {}
        self.assertEqual(contract.resolve_adapter(env=env), "claude")

    def test_load_adapter_returns_claude_module(self):
        os.environ.pop("CEO_HOOK_ADAPTER", None)
        mod = contract.load_adapter()
        self.assertTrue(hasattr(mod, "read_event"))
        self.assertTrue(hasattr(mod, "write_decision"))


if __name__ == "__main__":
    unittest.main()
