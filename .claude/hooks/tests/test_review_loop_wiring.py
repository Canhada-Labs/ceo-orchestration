"""E2-F1 wiring tests — codex_review_user_code CLEAN verdict approves review_loop's gate.

PLAN-134 W0 (REPORT-S225 E2-F1 [P1] [CONFIRMED]): `review_loop.mark_approved()` had ZERO
production callers, so the opt-in CEO_REVIEW_LOOP Stop-gate blocked 3x even after a completed
Codex review. The wiring lands in `codex_review_user_code.gate()` (Stop entry 2, runs BEFORE
review_loop at entry 3): a real CLEAN AUTO verdict calls `_approve_review_loop(cwd, sig0)`,
which recomputes review_loop's own `_diff_signature` and approves it ONLY if it still equals
the pre-review snapshot `sig0` (TOCTOU guard).

Covered classes:

  1. test_clean_codex_review_unblocks_review_loop — CLEAN → sig in approved_sigs → decide() {}
  2. test_dirty_verdict_does_not_approve          — findings → no approval, gate keeps blocking
  3. test_infra_skip_does_not_approve             — (True, None) infra skip → no approval
  4. test_risky_word_boundary                     — '# authored by' must NOT classify risky
  5. test_toctou_changed_worktree_not_approved    — worktree moved during Codex run → no approval

Env via TestEnvContext (isolation) + mock.patch.dict (per-test values) — env-hygiene gate
compliant (never bare os.environ writes). Hook modules exercised IN-PROCESS so the monkeypatch
of run_codex_review can never launch a real 120s Codex subprocess.

stdlib-only, Python >= 3.9.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict
from unittest import mock

import pytest

_HOOKS_DIR = Path(__file__).resolve().parent.parent

# TestEnvContext gives us env snapshot/restore + isolated HOME/audit tree.
sys.path.insert(0, str(_HOOKS_DIR))
from _lib.testing import TestEnvContext  # noqa: E402

# setUp runs `git init` in a temp repo; if git is absent the unguarded subprocess
# raises FileNotFoundError in setUp and ERRORs every test instead of skipping.
pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not on PATH")

import codex_review_user_code as crc  # noqa: E402
import review_loop  # noqa: E402


class ReviewLoopWiringBase(TestEnvContext):
    """Shared fixture: a tmp git repo with one committed file + a tmp review-loop state dir."""

    def setUp(self) -> None:
        super().setUp()
        self.repo = Path(tempfile.mkdtemp(prefix="rlw-repo-"))
        self.state_dir = Path(tempfile.mkdtemp(prefix="rlw-state-"))
        self.addCleanup(self._rm_tmp_dirs)
        self._git("init")
        self._git("config", "user.email", "test@local")
        self._git("config", "user.name", "Test User")
        self.app_file = self.repo / "app.py"
        self.app_file.write_text("# initial\n")
        self._git("add", "app.py")
        self._git("commit", "-m", "initial")

    def _rm_tmp_dirs(self) -> None:
        import shutil
        shutil.rmtree(str(self.repo), ignore_errors=True)
        shutil.rmtree(str(self.state_dir), ignore_errors=True)

    def _git(self, *args: str) -> None:
        subprocess.run(["git"] + list(args), cwd=str(self.repo), capture_output=True, check=True)

    def _env(self, **extra: str) -> Dict[str, str]:
        """Base env for both hooks: review_loop ON, shared state dir, AUTO Codex mode."""
        env = {
            "CEO_REVIEW_LOOP": "1",
            "CEO_REVIEW_LOOP_STATE": str(self.state_dir),
            "CEO_CODEX_USER_REVIEW": "1",
            "CEO_CODEX_USER_REVIEW_AUTO": "1",
        }
        env.update(extra)
        return env

    def _hook_input(self) -> Dict[str, object]:
        return {"cwd": str(self.repo), "_state_dir": str(self.state_dir)}

    def _approved_sigs(self) -> list:
        state = review_loop._load_state(review_loop.review_state_path(str(self.state_dir)))
        return list(state.get("approved_sigs", []))

    def _state_iters(self) -> int:
        state = review_loop._load_state(review_loop.review_state_path(str(self.state_dir)))
        return int(state.get("iters", 0) or 0)


class TestCleanReviewUnblocks(ReviewLoopWiringBase):
    def test_clean_codex_review_unblocks_review_loop(self) -> None:
        with mock.patch.dict(os.environ, self._env()):
            # (1) risky uncommitted diff → review_loop blocks at iter 1
            self.app_file.write_text("# auth secret token\n")
            r1 = review_loop.decide(self._hook_input())
            self.assertEqual(r1.get("decision"), "block", r1)
            self.assertIn("iter 1/3", r1.get("reason", ""))

            # (2) a CLEAN AUTO Codex review completes on the SAME worktree
            with mock.patch.object(crc, "run_codex_review", lambda diff, cwd: (True, "CLEAN")), \
                    mock.patch.object(crc, "risky_diff", lambda cwd: (["auth.py"], "+ auth\n")):
                out = crc.gate(str(self.repo))
            self.assertIn("CLEAN", json.dumps(out))

            # (3) review_loop's own signature for the current diff is now approved
            sig = review_loop._diff_signature(str(self.repo))
            self.assertTrue(sig, "fixture must produce a non-empty signature")
            self.assertIn(sig, self._approved_sigs())

            # (4) decide() unblocks WITHOUT consuming further iterations
            r2 = review_loop.decide(self._hook_input())
            self.assertEqual(r2, {}, r2)
            self.assertEqual(self._state_iters(), 1, "approval path must not advance the iter counter")


class TestDirtyVerdictDoesNotApprove(ReviewLoopWiringBase):
    def test_dirty_verdict_does_not_approve(self) -> None:
        with mock.patch.dict(os.environ, self._env()):
            self.app_file.write_text("# auth secret token\n")
            r1 = review_loop.decide(self._hook_input())
            self.assertEqual(r1.get("decision"), "block", r1)

            # Codex returns FINDINGS (not CLEAN) → no approval may be written
            with mock.patch.object(crc, "run_codex_review",
                                   lambda diff, cwd: (True, "- auth.py: timing-unsafe compare")), \
                    mock.patch.object(crc, "risky_diff", lambda cwd: (["auth.py"], "+ auth\n")):
                out = crc.gate(str(self.repo))
            self.assertIn("timing-unsafe", json.dumps(out))

            sig = review_loop._diff_signature(str(self.repo))
            self.assertNotIn(sig, self._approved_sigs())

            # the gate keeps blocking (iter 2)
            r2 = review_loop.decide(self._hook_input())
            self.assertEqual(r2.get("decision"), "block", r2)
            self.assertIn("iter 2/3", r2.get("reason", ""))


class TestInfraSkipDoesNotApprove(ReviewLoopWiringBase):
    def test_infra_skip_does_not_approve(self) -> None:
        with mock.patch.dict(os.environ, self._env()):
            self.app_file.write_text("# auth secret token\n")

            # infra skip: codex ran but produced no clean result → (True, None) → never mark_approved
            with mock.patch.object(crc, "run_codex_review", lambda diff, cwd: (True, None)), \
                    mock.patch.object(crc, "risky_diff", lambda cwd: (["auth.py"], "+ auth\n")):
                out = crc.gate(str(self.repo))
            self.assertIn("SKIPPED", json.dumps(out))

            self.assertEqual(self._approved_sigs(), [])
            self.assertFalse(
                os.path.exists(review_loop.review_state_path(str(self.state_dir))),
                "infra skip must not create review_loop state",
            )


class TestRiskyWordBoundary(ReviewLoopWiringBase):
    def test_risky_word_boundary(self) -> None:
        with mock.patch.dict(os.environ, self._env()):
            # 'authored' must NOT match the \bauth(?!or) pattern → no gate at all
            self.app_file.write_text("# authored by a contributor\n")
            r = review_loop.decide(self._hook_input())
            self.assertEqual(r, {}, r)

        # unit-level: boundary keeps real risk terms, drops prose lookalikes
        self.assertFalse(review_loop._risky("+ # authored by a contributor\n"))
        self.assertFalse(review_loop._risky("+ tokenizer = build()\n"))
        self.assertTrue(review_loop._risky("+ auth check\n"))
        self.assertTrue(review_loop._risky("+ refresh tokens rotated\n"))


class TestToctouChangedWorktreeNotApproved(ReviewLoopWiringBase):
    def test_toctou_changed_worktree_not_approved(self) -> None:
        with mock.patch.dict(os.environ, self._env()):
            self.app_file.write_text("# auth secret token\n")
            sig_before = review_loop._diff_signature(str(self.repo))

            # Codex "runs" and the worktree CHANGES underneath it → neither sig may be approved
            def _mutating_review(diff: str, cwd: str):
                self.app_file.write_text("# auth secret token MUTATED DURING REVIEW\n")
                return (True, "CLEAN")

            with mock.patch.object(crc, "run_codex_review", _mutating_review), \
                    mock.patch.object(crc, "risky_diff", lambda cwd: (["auth.py"], "+ auth\n")):
                crc.gate(str(self.repo))

            sig_after = review_loop._diff_signature(str(self.repo))
            self.assertNotEqual(sig_before, sig_after)
            approved = self._approved_sigs()
            self.assertNotIn(sig_before, approved)
            self.assertNotIn(sig_after, approved)


if __name__ == "__main__":
    import unittest
    unittest.main()
