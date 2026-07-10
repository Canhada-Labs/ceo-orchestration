"""PLAN-155 Wave 4 — Codex audit-chain end-to-end replay (SENT-CX-B / ADR-161).

Certifying artifact for the Wave-4 exit criteria: a RECORDED end-to-end Codex
session (SessionStart -> >=5 tool calls -> Stop, captured live from codex-cli
0.139.0 — see `fixtures/adapters/codex/session/codex_session_e2e.json` `_meta`)
replays through the REAL `audit_log.py` under `CEO_HOOK_ADAPTER=codex` as
SUBPROCESSES (not in-process import — the S254 dead-gate lesson: an in-process
call would stay green through a silently-dead adapter), yielding an HMAC audit
log that `audit-verify-chain.py` accepts (exit 0).

The completeness query IS the test (debate A13): the per-tool appends
(`codex_tool_recorded`) and the turn-level backstop (`codex_turn_ended`) are
COUNTABLE SEPARATELY from the same log slice by their distinct action names —
so a partial-interception turn (per-tool rows dropped) is never conflated with
a per-tool append.

Isolation: `TestEnvContext` pins HOME + the audit dir + a TEST-scoped HMAC key
(generated under the temp audit dir; the real `$HOME`/`$CLAUDE_PROJECT_DIR` are
never touched). Env is mutated only through `TestEnvContext`'s snapshot/restore
and `os.environ` inside the isolated tree (per CLAUDE.md hook-test isolation).

Landing-order dependency (MANIFEST-A): this test rides the Wave-4 commit but
depends on the Wave-1 host adapter (`_lib/adapters/codex.py` host mode) already
being landed — in CI Wave 1 lands first, so the on-disk adapter classifies the
codex wire correctly. If the host adapter is ABSENT (dead-gate class), the
count assertions FAIL loudly rather than skip (anti-vacuity, debate A4).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from collections import Counter
from pathlib import Path

# Make `.claude/hooks/` importable so `_lib` resolves (TestEnvContext lives in
# `_lib/testing.py`). This test file sits in `.claude/hooks/tests/`.
_TESTS_DIR = Path(__file__).resolve().parent
_HOOKS_DIR = _TESTS_DIR.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

_AUDIT_LOG_HOOK = _HOOKS_DIR / "audit_log.py"
_VERIFY_CHAIN = _HOOKS_DIR.parent / "scripts" / "audit-verify-chain.py"
_FIXTURE = (
    _TESTS_DIR
    / "fixtures"
    / "adapters"
    / "codex"
    / "session"
    / "codex_session_e2e.json"
)


class CodexAuditChainReplayTests(TestEnvContext):
    """Replay a recorded codex session and assert a verify-chain-green log."""

    def _load_events(self):
        with open(_FIXTURE, encoding="utf-8") as f:
            fixture = json.load(f)
        return fixture["events"]

    def _subprocess_env(self):
        """Env for the hook subprocess: the isolated tree + codex adapter.

        `TestEnvContext.setUp` has already pointed HOME + CEO_AUDIT_LOG_* at the
        temp tree in `os.environ` and set CEO_AUDIT_SYNC_MODE=1. We add the
        codex adapter selector so the hook takes the Wave-4 codex path.
        """
        env = dict(os.environ)
        env["CEO_HOOK_ADAPTER"] = "codex"
        env["CEO_AUDIT_SYNC_MODE"] = "1"
        return env

    def _replay(self, events):
        """Feed each recorded envelope to audit_log.py as a subprocess."""
        env = self._subprocess_env()
        for ev in events:
            proc = subprocess.run(
                [sys.executable, str(_AUDIT_LOG_HOOK)],
                input=json.dumps(ev),
                text=True,
                capture_output=True,
                env=env,
            )
            # Fail-open contract: the audit hook exits 0 on every path and is
            # silent on stdout (composable with other PostToolUse hooks).
            self.assertEqual(
                proc.returncode, 0,
                f"audit_log.py must exit 0 (fail-open) on a codex "
                f"{ev.get('hook_event_name')} envelope; got rc={proc.returncode} "
                f"stderr={proc.stderr[:400]!r}",
            )
            self.assertEqual(
                proc.stdout, "",
                f"audit_log.py must be silent on stdout; got {proc.stdout[:200]!r}",
            )

    def _read_log_rows(self):
        log_path = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        self.assertTrue(
            log_path.is_file(),
            f"no audit log written at {log_path} — the codex append path "
            f"produced nothing (dead-gate class). Check the Wave-1 host "
            f"adapter is present on disk.",
        )
        rows = []
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    def test_fixture_shape_is_the_recorded_session(self):
        """Guard the fixture is the SessionStart -> >=5 calls -> Stop shape."""
        events = self._load_events()
        names = [e.get("hook_event_name") for e in events]
        self.assertEqual(names[0], "SessionStart", "fixture must open on SessionStart")
        self.assertEqual(names[-1], "Stop", "fixture must close on Stop")
        post = [n for n in names if n == "PostToolUse"]
        self.assertGreaterEqual(
            len(post), 5,
            f"fixture must carry >=5 tool calls (Wave-4 exit criteria); got {len(post)}",
        )
        # One coherent recorded codex session id.
        sids = {e.get("session_id") for e in events}
        self.assertEqual(len(sids), 1, f"fixture must be one session; got {sids}")

    def test_verify_chain_green_over_replayed_codex_session(self):
        """audit-verify-chain.py exits 0 over the replayed codex session."""
        self._replay(self._load_events())
        rows = self._read_log_rows()

        # Every appended row is HMAC-bearing (chain-covered, not a null-hmac gap).
        self.assertTrue(
            all(r.get("hmac") for r in rows),
            "every codex audit row must carry a non-null hmac (chain-covered)",
        )

        proc = subprocess.run(
            [sys.executable, str(_VERIFY_CHAIN),
             "--log-file", os.environ["CEO_AUDIT_LOG_PATH"]],
            text=True,
            capture_output=True,
            env=dict(os.environ),
        )
        self.assertEqual(
            proc.returncode, 0,
            f"audit-verify-chain.py must exit 0 over the codex session chain; "
            f"got rc={proc.returncode}\nstdout={proc.stdout[:600]}\n"
            f"stderr={proc.stderr[:600]}",
        )

    def test_per_tool_and_turn_level_appends_are_countable_separately(self):
        """The completeness query IS the test (debate A13).

        From the SAME log slice, the per-tool rail (`codex_tool_recorded`) and
        the turn-level backstop (`codex_turn_ended`) partition by DISTINCT
        action names — so a completeness analysis can tell them apart. Neither
        collides with the claude-only `agent_spawn` rail.
        """
        events = self._load_events()
        self._replay(events)
        rows = self._read_log_rows()
        counts = Counter(r["action"] for r in rows)

        expected_tool_calls = sum(
            1 for e in events if e.get("hook_event_name") == "PostToolUse"
        )

        # (A) per-tool append: one codex_tool_recorded per PostToolUse.
        self.assertEqual(
            counts.get("codex_tool_recorded", 0), expected_tool_calls,
            f"per-tool rail count mismatch: expected {expected_tool_calls} "
            f"codex_tool_recorded rows, got {counts.get('codex_tool_recorded', 0)}. "
            f"Full action histogram: {dict(counts)}",
        )

        # (B) turn-level backstop: one codex_turn_ended for the closing Stop,
        #     carrying the DISTINCT action + the source enum + harness tag.
        turn_rows = [r for r in rows if r["action"] == "codex_turn_ended"]
        self.assertEqual(
            len(turn_rows), 1,
            f"expected exactly 1 codex_turn_ended (Stop backstop); "
            f"histogram: {dict(counts)}",
        )
        turn = turn_rows[0]
        self.assertEqual(turn.get("harness"), "codex")
        self.assertIn(
            turn.get("source"), ("stop", "subagent_stop", "notify", "wrapper"),
            f"codex_turn_ended.source must be a closed-enum value; got "
            f"{turn.get('source')!r}",
        )

        # The two rails are DISTINCT actions (never conflated) and neither is
        # the claude-only agent_spawn record.
        self.assertNotEqual("codex_tool_recorded", "codex_turn_ended")
        self.assertNotIn(
            "agent_spawn", counts,
            "the codex audit path must NOT emit the claude-only agent_spawn "
            "action (rail separation)",
        )

        # Per-tool rows are metadata-only: closed tool-name enum, no command
        # bytes / patch body / paths leaked onto the wire.
        for r in rows:
            if r["action"] == "codex_tool_recorded":
                self.assertEqual(r.get("harness"), "codex")
                self.assertIn(
                    r.get("tool_name_enum"),
                    ("Bash", "Edit", "Write", "Task", "Read", "MultiEdit",
                     "NotebookEdit", "Glob", "Grep", "WebFetch", "WebSearch",
                     "mcp_other", "other"),
                    f"tool_name_enum must be closed-enum; got "
                    f"{r.get('tool_name_enum')!r}",
                )
                # No raw command/patch body fields on the metadata-only wire.
                for forbidden in ("command", "tool_input", "tool_response",
                                  "file_path", "prompt"):
                    self.assertNotIn(
                        forbidden, r,
                        f"codex_tool_recorded row must not carry {forbidden!r} "
                        f"(Sec MF-3 metadata-only)",
                    )

    def test_boot_bracket_row_present(self):
        """The recorded SessionStart replays to a session_start boot row.

        Under codex the boot bracket reuses the existing `session_start` action
        (audit_log's codex path routes a SessionStart wire to
        `emit_session_start`); production codex routes SessionStart to
        SessionStart.py, so there is no double-count in the wild.
        """
        self._replay(self._load_events())
        rows = self._read_log_rows()
        counts = Counter(r["action"] for r in rows)
        self.assertGreaterEqual(
            counts.get("session_start", 0), 1,
            f"expected a session_start boot row from the recorded SessionStart; "
            f"histogram: {dict(counts)}",
        )


if __name__ == "__main__":
    unittest.main()
