"""PLAN-085 Wave E.3 — check_bash_safety canonical-path interceptor tests.

8 cases covering write-shape operator detection + fail-CLOSED parse failure.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS = REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))


class TestBashCanonicalInterceptor(unittest.TestCase):
    """E.3 v1 heuristic interceptor tests."""

    def test_redirect_to_canonical_blocked(self) -> None:
        """`echo > .claude/team.md` should be denied."""
        from check_bash_safety import decide_command
        d = decide_command("echo 'evil' > .claude/team.md")
        self.assertFalse(d.allow)
        self.assertIn("canonical", (d.reason or "").lower())

    def test_redirect_append_blocked(self) -> None:
        """`echo >> .claude/settings.json` should be denied."""
        from check_bash_safety import decide_command
        d = decide_command("echo 'X' >> .claude/settings.json")
        self.assertFalse(d.allow)

    def test_tee_to_canonical_blocked(self) -> None:
        """`echo X | tee .claude/team.md` should be denied."""
        from check_bash_safety import decide_command
        d = decide_command("tee .claude/team.md")
        self.assertFalse(d.allow)

    def test_tee_a_to_canonical_blocked(self) -> None:
        """`tee -a .claude/team.md` should be denied."""
        from check_bash_safety import decide_command
        d = decide_command("tee -a .claude/team.md")
        self.assertFalse(d.allow)

    def test_sed_inplace_canonical_blocked(self) -> None:
        """`sed -i 's/x/y/' .claude/adr/ADR-001-runtime-state-directory.md`."""
        from check_bash_safety import decide_command
        d = decide_command(
            "sed -i 's/X/Y/' .claude/adr/ADR-001-runtime-state-directory.md"
        )
        self.assertFalse(d.allow)

    def test_git_checkout_canonical_blocked(self) -> None:
        """`git checkout HEAD~1 -- .claude/team.md` should be denied."""
        from check_bash_safety import decide_command
        d = decide_command("git checkout HEAD~1 -- .claude/team.md")
        self.assertFalse(d.allow)

    def test_non_canonical_redirect_allowed(self) -> None:
        """`echo X > /tmp/foo.txt` should be allowed (non-canonical)."""
        from check_bash_safety import decide_command
        d = decide_command("echo X > /tmp/foo.txt")
        self.assertTrue(d.allow)

    def test_parse_failure_fails_closed(self) -> None:
        """Malformed quoting → shlex parse fails → DENY (not allow)."""
        from check_bash_safety import decide_command
        # Unterminated single quote forces shlex.split ValueError
        d = decide_command("echo 'unterminated > .claude/team.md")
        self.assertFalse(
            d.allow,
            msg="parse-failure must fail-CLOSED per R1 Sec-2",
        )
        self.assertIn("parse", (d.reason or "").lower())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
