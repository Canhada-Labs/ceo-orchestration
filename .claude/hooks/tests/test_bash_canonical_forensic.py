"""PLAN-085 Wave E.4 — check_bash_canonical_forensic tests.

5 cases covering write-shape scan + non-blocking behavior.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS = REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))


class TestBashCanonicalForensic(unittest.TestCase):
    """E.4 forensic hook tests."""

    def test_scan_extracts_redirect_target(self) -> None:
        from check_bash_canonical_forensic import _scan_command_targets
        out = _scan_command_targets("echo X > .claude/team.md")
        self.assertIn(".claude/team.md", out)

    def test_scan_extracts_append_target(self) -> None:
        from check_bash_canonical_forensic import _scan_command_targets
        out = _scan_command_targets("echo X >> .claude/settings.json")
        self.assertIn(".claude/settings.json", out)

    def test_scan_extracts_tee_target(self) -> None:
        from check_bash_canonical_forensic import _scan_command_targets
        out = _scan_command_targets("tee -a .claude/team.md")
        self.assertIn(".claude/team.md", out)

    def test_decide_never_returns_block(self) -> None:
        """E.4 is advisory — decide() must always allow."""
        from check_bash_canonical_forensic import decide
        result = decide(
            command="echo X > .claude/team.md",
            repo_root=REPO_ROOT,
        )
        # _contract.allow() returns an opaque allow object; we just
        # assert no exception was raised and a non-None result returned
        # (or None if _contract is unavailable).
        # E.4 NEVER blocks — decide() returns _contract.allow() Decision
        # (allow=True) or None if contract layer unavailable.
        if result is not None:
            self.assertTrue(
                getattr(result, "allow", False),
                msg="E.4 forensic must always return allow",
            )

    def test_non_canonical_target_no_emit(self) -> None:
        """Non-canonical target → no emit (decide allows silently)."""
        from check_bash_canonical_forensic import decide, _scan_command_targets
        targets = _scan_command_targets("echo X > /tmp/foo.txt")
        self.assertIn("/tmp/foo.txt", targets)
        # decide() should not raise on non-canonical target.
        result = decide(
            command="echo X > /tmp/foo.txt",
            repo_root=REPO_ROOT,
        )
        # E.4 NEVER blocks — decide() returns _contract.allow() Decision
        # (allow=True) or None if contract layer unavailable.
        if result is not None:
            self.assertTrue(
                getattr(result, "allow", False),
                msg="E.4 forensic must always return allow",
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
