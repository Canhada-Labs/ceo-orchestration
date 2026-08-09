"""PLAN-169 W2.3 — inject-agent-context.sh EXACT resolution ladder tests.

The pre-W2.3 matcher used awk ``index()`` substring search and delivered
"Government Cybersecurity Engineer" for "Security Engineer" in live use
(the PLAN-169 debate, ledger C.1). The ladder under test:

    1. EXACT persona-heading match (component equality, never substring)
    2. explicit core-archetype -> .claude/agents/<slug>.md table
       (slugs not derivable: "DevOps Engineer" -> devops.md)
    3. SKILL-MAP-row-only role -> synthesized profile, labeled
    4. unknown name -> hard error exit 3 (fail-closed, never a warning)

Plus the [codex r12-P2] grammar extension: real roster names carry "/"
and "&" ("UI/UX Lead", "Accessibility & i18n Engineer") and must pass
input validation (old charset rejected them with exit 2).
"""

from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "inject-agent-context.sh"


def _run(*args, env_extra=None):
    # repass-r2 round-4 part-d P1: forwarding the ambient environment let
    # the script (which shells into lessons.py --emit-consumer) touch the
    # operator's REAL $HOME/CEO_* state from a test. Sanitized env: fresh
    # HOME in a tempdir, CEO_*/CLAUDE_* stripped, only the plumbing kept.
    import tempfile
    home = tempfile.mkdtemp(prefix="inject-test-home-")
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("CEO_", "CLAUDE_"))
        and k not in ("HOME",)
    }
    env["HOME"] = home
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )


class ExactResolutionLadderTest(unittest.TestCase):

    def test_security_engineer_never_resolves_by_substring(self):
        # The C.1 defect: "security engineer" is a SUBSTRING of
        # "cybersecurity engineer". Exact/component matching must never
        # deliver a Government/Cyber-prefixed persona for this name.
        result = _run("Security Engineer", "audit")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("## AGENT PROFILE", result.stdout)
        self.assertNotIn("Government Cybersecurity", result.stdout)
        self.assertNotIn("Cybersecurity Engineer", result.stdout)

    def test_devops_engineer_resolves_via_native_table(self):
        # team.md has no per-persona headings for DevOps Engineer; the
        # explicit table must route to .claude/agents/devops.md (rung 2).
        result = _run("DevOps Engineer", "ci work")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(".claude/agents/devops.md", result.stdout)

    def test_vp_engineering_gets_synthesized_profile(self):
        # "VP Engineering" exists ONLY as a SKILL MAP row — no persona
        # section, no agents/ file. Rung 3 synthesizes from the row and
        # says so explicitly.
        result = _run("VP Engineering", "design review")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("SYNTHESIZED FROM THE SKILL MAP ROW", result.stdout)
        self.assertIn("architecture-decisions", result.stdout)

    def test_unknown_name_fails_closed_exit_3(self):
        result = _run("Fictitious Nonexistent Person", "anything")
        self.assertEqual(result.returncode, 3)
        self.assertIn("resolves to NOTHING", result.stderr)

    def test_grammar_accepts_slash_and_ampersand_names(self):
        # Roster-real names must pass INPUT validation (not exit 2). They
        # may still fail RESOLUTION (exit 3) in a backend-only checkout —
        # both outcomes are fine; the grammar rejection is not.
        # repass-r2 round-4 part-d P2: "anything but 2" also accepted an
        # unrelated crash (rc=1). Constrain to the documented outcomes:
        # 0 = resolved, 3 = resolution failure (backend-only checkout).
        for name in ("UI/UX Lead", "Accessibility & i18n Engineer"):
            result = _run(name, "frontend work")
            self.assertIn(
                result.returncode, (0, 3),
                f"unexpected rc={result.returncode} for roster-real name "
                f"{name!r} (0=resolved, 3=resolution-miss; 2=grammar reject "
                f"is the defect, anything else is a crash): {result.stderr}",
            )

    def test_grammar_still_rejects_metacharacters(self):
        for bad in ("$(rm x)", "a;b", "a|b", "../etc", "a\nb"):
            result = _run(bad, "x")
            self.assertEqual(result.returncode, 2, f"accepted {bad!r}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
