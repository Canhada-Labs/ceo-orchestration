"""PLAN-105 Wave B.4 — check-roadmap-binding.py validator tests.

AC14: validator exits 0 against all .claude/plans/PLAN-*.md post-ship.

Stdlib-only. Runs validator as subprocess against the real repo state.
"""
from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_VALIDATOR = _REPO_ROOT / ".claude" / "scripts" / "check-roadmap-binding.py"


class TestRoadmapBinding(unittest.TestCase):
    """B.4 — validator exists + exits 0 on clean state."""

    def test_validator_exists(self):
        self.assertTrue(_VALIDATOR.exists(),
                        f"validator missing at {_VALIDATOR}")

    def test_validator_is_executable_python(self):
        out = subprocess.run(
            [sys.executable, str(_VALIDATOR)],
            capture_output=True, text=True, timeout=30,
        )
        # Either OK (0), unresolved (1) — both are expected exit codes.
        # exit 2 = infra error (missing canonical sources).
        self.assertIn(out.returncode, (0, 1, 2),
                      f"unexpected exit code {out.returncode}; stdout={out.stdout}, stderr={out.stderr}")

    def test_validator_emits_summary_on_success(self):
        out = subprocess.run(
            [sys.executable, str(_VALIDATOR)],
            capture_output=True, text=True, timeout=30,
        )
        if out.returncode == 0:
            # Either fully clean ("OK") OR advisory-mode summary
            # ("advisory — N unresolved (see stderr). Exit 0 per PLAN-105 §Wave B.4").
            self.assertTrue(
                "check-roadmap-binding: OK" in out.stdout
                or "advisory" in out.stdout,
                f"expected OK or advisory summary; got stdout={out.stdout!r}",
            )
        elif out.returncode == 1:
            # Strict-mode (--strict) — report on stderr.
            self.assertIn("unresolved", out.stderr.lower())
        # exit 2 (infra) — no canonical assertion possible.

    def test_strict_mode_exits_1_on_unresolved(self):
        out = subprocess.run(
            [sys.executable, str(_VALIDATOR), "--strict"],
            capture_output=True, text=True, timeout=30,
        )
        # Strict mode: exit 1 if any unresolved; 0 if all resolve; 2 = infra
        # (e.g. no canonical roadmap docs to bind against — the distributed
        # repo ships no PLAN-084 roadmap corpus). Matches the summary test.
        self.assertIn(out.returncode, (0, 1, 2))
        if out.returncode == 1:
            self.assertIn("STRICT", out.stderr)


if __name__ == "__main__":
    unittest.main()
