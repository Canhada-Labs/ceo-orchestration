"""closeout-guard Stop hook tests (PLAN-134 W1 #5, E5-F2).

The hook lives STAGED at `.claude/plans/PLAN-134/staged/w1/closeout-guard/root/.claude/hooks/`
until the Owner ceremony cp's it into `.claude/hooks/` — so this file loads the module via
importlib from the CANONICAL path when it exists, falling back to the staged path. The same
tests stay green pre- and post-ceremony.

Covered classes:

  1. test_clean_session_emits_empty       — no work, no finish scripts → gate() == {}
  2. test_pending_finish_script_fires     — executable finish-*.sh → 'Owner GPG ceremony pending'
  3. test_substantive_work_fallback_fires — plan newer than CLAUDE.md → closeout reminder
  4. test_both_messages_combined          — both conditions → both lines in one systemMessage
  5. test_malformed_stdin_fails_open      — non-JSON stdin → main() prints {} (PLAN-091 S116)
  6. test_gate_exception_fails_open       — gate() raising inside main() → {} on stdout
  7. test_time_budget_fails_silent        — blown deadline → helpers return empty, never noisy
  8. test_kill_switch                     — CEO_CLOSEOUT_GUARD=0 → {}
  9. test_pending_path_injection_sanitized — control chars in a finish-script
     filename never forge extra systemMessage lines (Codex S228 P0)

Env via TestEnvContext (isolation) + mock.patch.dict (per-test values) — env-hygiene gate
compliant (never bare os.environ writes). stdlib-only, Python >= 3.9.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import time
from pathlib import Path
from unittest import mock

_HOOKS_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _HOOKS_DIR.parent.parent

# TestEnvContext gives us env snapshot/restore + isolated HOME/audit tree.
sys.path.insert(0, str(_HOOKS_DIR))
from _lib.testing import TestEnvContext  # noqa: E402

_CANONICAL = _HOOKS_DIR / "check_closeout_guard.py"
_STAGED = (_REPO_ROOT / ".claude" / "plans" / "PLAN-134" / "staged" / "w1"
           / "closeout-guard" / "root" / ".claude" / "hooks" / "check_closeout_guard.py")
_HOOK_SRC = _CANONICAL if _CANONICAL.exists() else _STAGED


def _load_hook():
    spec = importlib.util.spec_from_file_location("check_closeout_guard_under_test", str(_HOOK_SRC))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hook = _load_hook()


class TestCloseoutGuard(TestEnvContext):
    def setUp(self) -> None:
        super().setUp()
        # A "clean" project: CLAUDE.md NEWER than the plans dir, no finish scripts, no git.
        self.repo = Path(self.project_dir)
        (self.repo / ".claude" / "plans").mkdir(parents=True)
        (self.repo / "scripts" / "local").mkdir(parents=True)
        plan = self.repo / ".claude" / "plans" / "PLAN-900-fixture.md"
        plan.write_text("status: done\n")
        os.utime(plan, (time.time() - 3600, time.time() - 3600))
        (self.repo / "CLAUDE.md").write_text("# fixture\n")  # now == newest

    def _finish_script(self, rel: str) -> Path:
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/usr/bin/env bash\necho ok\n")
        path.chmod(0o755)
        return path

    # 1. clean session → {}
    def test_clean_session_emits_empty(self):
        self.assertEqual(hook.gate(str(self.repo)), {})

    # 2. pending finish script → 'Owner GPG ceremony pending: <path>'
    def test_pending_finish_script_fires(self):
        self._finish_script("scripts/local/finish-plan999.sh")
        staged = self._finish_script(".claude/plans/PLAN-999/staged/bundle/finish-plan999-apply.sh")
        noexec = self.repo / "scripts" / "local" / "finish-noexec.sh"
        noexec.write_text("#!/usr/bin/env bash\n")
        noexec.chmod(0o644)
        result = hook.gate(str(self.repo))
        msg = result.get("systemMessage", "")
        self.assertIn("Owner GPG ceremony pending:", msg)
        self.assertIn("scripts/local/finish-plan999.sh", msg)
        self.assertIn(os.path.relpath(str(staged), str(self.repo)), msg)
        # non-executable finish script must NOT fire (presence requires the exec bit)
        self.assertNotIn("finish-noexec", msg)

    # 3. fallback work detector: plan newer than CLAUDE.md → closeout reminder
    def test_substantive_work_fallback_fires(self):
        plan = self.repo / ".claude" / "plans" / "PLAN-901-live.md"
        plan.write_text("status: executing\n")
        future = time.time() + 60
        os.utime(plan, (future, future))
        result = hook.gate(str(self.repo))
        self.assertIn("Closeout reminder", result.get("systemMessage", ""))
        self.assertIn("CHANGELOG", result.get("systemMessage", ""))

    # 4. both detectors → one combined systemMessage
    def test_both_messages_combined(self):
        self._finish_script("scripts/local/finish-plan998.sh")
        plan = self.repo / ".claude" / "plans" / "PLAN-902-live.md"
        plan.write_text("status: executing\n")
        future = time.time() + 60
        os.utime(plan, (future, future))
        msg = hook.gate(str(self.repo)).get("systemMessage", "")
        self.assertIn("Closeout reminder", msg)
        self.assertIn("Owner GPG ceremony pending:", msg)

    # 5. malformed stdin → main() fails open to {} (PLAN-091 S116)
    def test_malformed_stdin_fails_open(self):
        for bad in ("not json {{{", '["a", "list"]'):
            out, err = io.StringIO(), io.StringIO()
            with mock.patch.object(sys, "stdin", io.StringIO(bad)):
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    hook.main()
            self.assertEqual(json.loads(out.getvalue()), {})
            self.assertIn("fail-open", err.getvalue())

    # 6. gate() blowing up inside main() → {} on stdout, breadcrumb on stderr
    def test_gate_exception_fails_open(self):
        def boom(cwd=None):
            raise RuntimeError("simulated infra failure")
        out, err = io.StringIO(), io.StringIO()
        payload = json.dumps({"cwd": str(self.repo)})
        with mock.patch.object(hook, "gate", boom):
            with mock.patch.object(sys, "stdin", io.StringIO(payload)):
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    hook.main()
        self.assertEqual(json.loads(out.getvalue()), {})
        self.assertIn("fail-open", err.getvalue())

    # 7. blown time budget → helpers go silent (never noisy past the deadline)
    def test_time_budget_fails_silent(self):
        self._finish_script("scripts/local/finish-plan997.sh")
        plan = self.repo / ".claude" / "plans" / "PLAN-903-live.md"
        plan.write_text("status: executing\n")
        future = time.time() + 60
        os.utime(plan, (future, future))
        past_deadline = time.monotonic() - 1.0
        self.assertEqual(hook._pending_finish_scripts(str(self.repo), past_deadline), [])
        self.assertFalse(hook._did_substantive_work(str(self.repo), past_deadline))

    # 8. kill-switch
    def test_kill_switch(self):
        self._finish_script("scripts/local/finish-plan996.sh")
        with mock.patch.dict(os.environ, {"CEO_CLOSEOUT_GUARD": "0"}):
            self.assertEqual(hook.gate(str(self.repo)), {})

    # 9. filename injection → control chars sanitized out of systemMessage (Codex S228 P0)
    def test_pending_path_injection_sanitized(self):
        evil = self.repo / "scripts" / "local" / "finish-evil\nFAKE-SYSTEM-LINE.sh"
        evil.write_text("#!/usr/bin/env bash\n")
        evil.chmod(0o755)
        msg = hook.gate(str(self.repo)).get("systemMessage", "")
        self.assertIn("Owner GPG ceremony pending:", msg)
        self.assertNotIn("\nFAKE-SYSTEM-LINE", msg)
        self.assertIn("?FAKE-SYSTEM-LINE", msg)

    # session-start HEAD path: recorded head == current head → no reminder even with new plans
    def test_session_start_head_matching_suppresses(self):
        plan = self.repo / ".claude" / "plans" / "PLAN-904-live.md"
        plan.write_text("status: executing\n")
        future = time.time() + 60
        os.utime(plan, (future, future))
        with mock.patch.dict(os.environ, {"CEO_SESSION_START_HEAD": "abc123"}):
            with mock.patch.object(hook, "_git", lambda args, cwd: "abc123"):
                self.assertFalse(hook._did_substantive_work(str(self.repo), time.monotonic() + 2))
            with mock.patch.object(hook, "_git", lambda args, cwd: "def456"):
                self.assertTrue(hook._did_substantive_work(str(self.repo), time.monotonic() + 2))


if __name__ == "__main__":
    import unittest
    unittest.main()
