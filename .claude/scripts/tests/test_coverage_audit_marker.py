"""PLAN-138 Wave A — coverage-audit Pass #2 inline-marker trigger.

The ``coverage-audit`` skill is a read-only doc contract; its Pass #2
(Ambiguity) flags a LIVE ``[NEEDS CLARIFICATION: <question>]`` marker at
HIGH severity (PLAN-SCHEMA §14). The deterministic predicate behind that
trigger is the shared ``live_clarification_markers`` helper in
``check-staleness.py`` (single source of truth for the code-span +
PLAN-SCHEMA exclusion shared by the staleness + validate-governance
advisories). This test asserts:

- the Ambiguity trigger FIRES on a bare-marker fixture,
- it does NOT fire on a backticked / fenced example,
- the SKILL.md documents the new HIGH-severity marker trigger.

Reads repo files + calls a pure function — touches no env, no network.
Stdlib-only unittest, env-isolated via ``TestEnvContext`` (env-hygiene
gate compliance: no bare ``os.environ[...]=``, no bare ``TestCase``).
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

# Make ``_lib.testing`` (TestEnvContext) importable for env-isolation.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

_STALENESS = _REPO_ROOT / ".claude" / "scripts" / "check-staleness.py"
_COVERAGE_SKILL = (
    _REPO_ROOT / ".claude" / "skills" / "core" / "coverage-audit" / "SKILL.md"
)


def _load_marker_fn():
    """Load the shared ``live_clarification_markers`` helper by path
    (``check-staleness.py`` is not importable by module name — hyphen)."""
    spec = importlib.util.spec_from_file_location(
        "check_staleness_marker", _STALENESS
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod.live_clarification_markers


class TestCoverageAuditMarker(TestEnvContext):
    """Pass #2 Ambiguity inline-marker trigger (PLAN-138 Wave A)."""

    def setUp(self) -> None:
        super().setUp()
        self.live_markers = _load_marker_fn()

    def test_ambiguity_trigger_fires_on_bare_marker(self) -> None:
        """A bare LIVE marker outside code spans is flagged (count >= 1)."""
        fixture = (
            "- [ ] AC1 [US1] [src/x.py] wire the export "
            "[NEEDS CLARIFICATION: which serialization format?]\n"
        )
        self.assertGreaterEqual(self.live_markers(fixture), 1)

    def test_no_trigger_on_backticked_example(self) -> None:
        """A backtick-wrapped example is documentation, not a finding."""
        fixture = "the token `[NEEDS CLARIFICATION: x?]` is just documentation\n"
        self.assertEqual(self.live_markers(fixture), 0)

    def test_no_trigger_on_fenced_example(self) -> None:
        """A marker inside a fenced code block is EXEMPT."""
        fixture = "```\n[NEEDS CLARIFICATION: y?]\n```\n"
        self.assertEqual(self.live_markers(fixture), 0)

    def test_non_actionable_token_not_flagged(self) -> None:
        """The bare prefix without colon+question+bracket is not LIVE."""
        self.assertEqual(self.live_markers("see [NEEDS CLARIFICATION] later"), 0)

    def test_definition_file_excluded(self) -> None:
        """PLAN-SCHEMA.md (definition file) never self-trips."""
        self.assertEqual(
            self.live_markers("[NEEDS CLARIFICATION: z?]", is_definition_file=True),
            0,
        )

    def test_garbage_input_fails_open(self) -> None:
        """Binary/garbage degrades to zero — never raises."""
        self.assertEqual(self.live_markers("\x00\xff\xfe binary \x00"), 0)

    def test_multiple_markers_counted(self) -> None:
        """Two distinct bare markers count as two."""
        fixture = (
            "[NEEDS CLARIFICATION: a?] and also [NEEDS CLARIFICATION: b?]\n"
        )
        self.assertEqual(self.live_markers(fixture), 2)

    def test_skill_documents_high_severity_marker_trigger(self) -> None:
        """coverage-audit SKILL.md documents the Pass #2 HIGH marker rule."""
        text = _COVERAGE_SKILL.read_text(encoding="utf-8")
        self.assertIn("NEEDS CLARIFICATION", text)
        # The trigger must be tied to Pass #2 / Ambiguity at HIGH severity.
        self.assertIn("HIGH", text)
        self.assertIn("PLAN-SCHEMA", text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
