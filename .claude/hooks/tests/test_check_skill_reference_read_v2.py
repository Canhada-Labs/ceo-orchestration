"""PLAN-045 F-10-07 v2 — tests for check_skill_reference_read session-state
reconciliation.

v1 baseline (reference_postread_observed breadcrumb) already covered
in test_check_skill_reference_read.py. This file covers the v2
extension only:

- _tail_audit_log reads most recent N events
- _find_spawn_for_skill locates the claiming spawn by session_id
- _session_state_path respects env override + session_id sanitization
- _load_session_state + _append_session_state round-trip
- _reconcile_read: match / mismatch / stale / no-claim verdicts
- Kill-switch CEO_SKILL_READ_V2=0 short-circuits v2 path
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

_HOOKS_DIR = Path(__file__).resolve().parent.parent

import check_skill_reference_read as csrr  # noqa: E402


class TailAuditLogTests(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self._log = Path(self._td.name) / "audit-log.jsonl"

    def tearDown(self) -> None:
        self._td.cleanup()

    def test_missing_file_returns_empty(self) -> None:
        self.assertEqual(csrr._tail_audit_log(self._log, 10), [])

    def test_empty_file_returns_empty(self) -> None:
        self._log.write_text("")
        self.assertEqual(csrr._tail_audit_log(self._log, 10), [])

    def test_reads_valid_jsonl(self) -> None:
        events = [{"ts": f"t{i}", "action": "agent_spawn"} for i in range(5)]
        self._log.write_text(
            "\n".join(json.dumps(e) for e in events) + "\n"
        )
        out = csrr._tail_audit_log(self._log, 10)
        self.assertEqual(len(out), 5)

    def test_limit_honored(self) -> None:
        events = [{"ts": f"t{i}"} for i in range(100)]
        self._log.write_text(
            "\n".join(json.dumps(e) for e in events) + "\n"
        )
        out = csrr._tail_audit_log(self._log, 10)
        self.assertEqual(len(out), 10)
        # Last 10 events (indices 90-99)
        self.assertEqual(out[0]["ts"], "t90")
        self.assertEqual(out[-1]["ts"], "t99")

    def test_malformed_lines_skipped(self) -> None:
        self._log.write_text(
            '{"ok": 1}\n'
            "not-json\n"
            '{"ok": 2}\n'
        )
        out = csrr._tail_audit_log(self._log, 10)
        self.assertEqual(len(out), 2)


class FindSpawnForSkillTests(unittest.TestCase):
    def test_no_matching_session_returns_none(self) -> None:
        events = [
            {
                "action": "agent_spawn",
                "session_id": "other",
                "desc_preview": "@.claude/skills/core/foo/SKILL.md sha256=" + "a" * 64,
            },
        ]
        result = csrr._find_spawn_for_skill(
            events, session_id="mine",
            skill_path_rel=".claude/skills/core/foo/SKILL.md",
        )
        self.assertIsNone(result)

    def test_matching_session_returns_claim(self) -> None:
        events = [
            {
                "action": "agent_spawn",
                "session_id": "mine",
                "ts": "2026-04-20T12:00:00Z",
                "desc_preview": (
                    "spawn for code review @.claude/skills/core/bar/SKILL.md "
                    "sha256=" + "b" * 64
                ),
            },
        ]
        result = csrr._find_spawn_for_skill(
            events, session_id="mine",
            skill_path_rel=".claude/skills/core/bar/SKILL.md",
        )
        self.assertIsNotNone(result)
        claim, ts = result  # type: ignore[misc]
        self.assertEqual(claim, "b" * 64)
        self.assertEqual(ts, "2026-04-20T12:00:00Z")

    def test_most_recent_spawn_wins(self) -> None:
        sha_old = "a" * 64
        sha_new = "b" * 64
        events = [
            {
                "action": "agent_spawn",
                "session_id": "mine",
                "ts": "2026-04-20T12:00:00Z",
                "desc_preview": f"@.claude/skills/core/x/SKILL.md sha256={sha_old}",
            },
            {
                "action": "agent_spawn",
                "session_id": "mine",
                "ts": "2026-04-20T13:00:00Z",
                "desc_preview": f"@.claude/skills/core/x/SKILL.md sha256={sha_new}",
            },
        ]
        claim, _ = csrr._find_spawn_for_skill(  # type: ignore[misc]
            events, session_id="mine",
            skill_path_rel=".claude/skills/core/x/SKILL.md",
        )
        self.assertEqual(claim, sha_new)

    def test_non_spawn_events_ignored(self) -> None:
        events = [
            {
                "action": "lesson_write",  # not agent_spawn
                "session_id": "mine",
                "desc_preview": "@.claude/skills/core/x/SKILL.md sha256=" + "a" * 64,
            },
        ]
        result = csrr._find_spawn_for_skill(
            events, session_id="mine",
            skill_path_rel=".claude/skills/core/x/SKILL.md",
        )
        self.assertIsNone(result)


class SessionStatePathTests(unittest.TestCase):
    def test_env_override_respected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ, {"CEO_SKILL_READ_STATE_DIR": td}):
                p = csrr._session_state_path("session-abc")
            self.assertEqual(p.parent, Path(td))
            self.assertTrue(p.name.startswith("session-abc"))

    def test_session_id_sanitized(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ, {"CEO_SKILL_READ_STATE_DIR": td}):
                p = csrr._session_state_path("../../../etc/passwd")
            # Path separators stripped — the resolved file must stay
            # inside CEO_SKILL_READ_STATE_DIR (no traversal possible).
            self.assertNotIn("/", p.name)
            self.assertNotIn("\\", p.name)
            # Resolved parent IS the state dir (no .. climbing)
            self.assertEqual(p.parent.resolve(), Path(td).resolve())

    def test_empty_session_id_becomes_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ, {"CEO_SKILL_READ_STATE_DIR": td}):
                p = csrr._session_state_path("")
            self.assertEqual(p.name, "unknown.jsonl")


class SessionStateRoundTripTests(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self._state = Path(self._td.name) / "sess.jsonl"

    def tearDown(self) -> None:
        self._td.cleanup()

    def test_append_and_load_roundtrip(self) -> None:
        csrr._append_session_state(
            self._state,
            {"skill_path": "a/SKILL.md", "read_sha": "x", "verdict": "match"},
        )
        csrr._append_session_state(
            self._state,
            {"skill_path": "b/SKILL.md", "read_sha": "y", "verdict": "mismatch"},
        )
        records = csrr._load_session_state(self._state)
        self.assertEqual(len(records), 2)
        self.assertEqual(records["a/SKILL.md"]["verdict"], "match")
        self.assertEqual(records["b/SKILL.md"]["verdict"], "mismatch")

    def test_load_missing_returns_empty(self) -> None:
        records = csrr._load_session_state(self._state)
        self.assertEqual(records, {})

    def test_malformed_lines_skipped(self) -> None:
        self._state.parent.mkdir(parents=True, exist_ok=True)
        self._state.write_text(
            '{"skill_path": "a", "verdict": "match"}\n'
            "not-json\n"
            '{"skill_path": "b", "verdict": "match"}\n'
        )
        records = csrr._load_session_state(self._state)
        self.assertEqual(len(records), 2)


class ReconcileReadTests(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self._root = Path(self._td.name).resolve()
        # Create a real skills subtree + a SKILL.md
        self._skill_dir = self._root / ".claude" / "skills" / "core" / "test-skill"
        self._skill_dir.mkdir(parents=True, exist_ok=True)
        self._skill_path = self._skill_dir / "SKILL.md"
        self._skill_path.write_text("skill body content", encoding="utf-8")
        self._real_sha = hashlib.sha256(
            self._skill_path.read_bytes()
        ).hexdigest()
        # Audit log path override
        self._audit_log = self._root / "audit.jsonl"
        # State dir override
        self._state_dir = self._root / "state"
        self._env_patches = patch.dict(os.environ, {
            "CEO_AUDIT_LOG_PATH": str(self._audit_log),
            "CEO_SKILL_READ_STATE_DIR": str(self._state_dir),
        })
        self._env_patches.start()

    def tearDown(self) -> None:
        self._env_patches.stop()
        self._td.cleanup()

    def _write_spawn_event(
        self, *, session_id: str, claimed_sha: str, ts: str,
    ) -> None:
        entry = {
            "action": "agent_spawn",
            "session_id": session_id,
            "ts": ts,
            "desc_preview": (
                f"task @.claude/skills/core/test-skill/SKILL.md "
                f"sha256={claimed_sha}"
            ),
        }
        with open(self._audit_log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")

    def _reconciled_verdict(self) -> str:
        state_path = csrr._session_state_path("s1")
        records = csrr._load_session_state(state_path)
        key = ".claude/skills/core/test-skill/SKILL.md"
        return records.get(key, {}).get("verdict", "unknown")

    def test_match_verdict_written(self) -> None:
        now = datetime.now(timezone.utc)
        self._write_spawn_event(
            session_id="s1", claimed_sha=self._real_sha,
            ts=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        csrr._reconcile_read(
            file_path=str(self._skill_path),
            file_hash=self._real_sha,
            session_id="s1",
            repo_root=self._root,
            project_dir=str(self._root),
        )
        self.assertEqual(self._reconciled_verdict(), "match")

    def test_mismatch_verdict_written(self) -> None:
        fake_claim = "f" * 64
        now = datetime.now(timezone.utc)
        self._write_spawn_event(
            session_id="s1", claimed_sha=fake_claim,
            ts=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        csrr._reconcile_read(
            file_path=str(self._skill_path),
            file_hash=self._real_sha,  # real != claimed
            session_id="s1",
            repo_root=self._root,
            project_dir=str(self._root),
        )
        self.assertEqual(self._reconciled_verdict(), "mismatch")

    def test_stale_verdict_for_old_spawn(self) -> None:
        old_ts = datetime.now(timezone.utc) - timedelta(minutes=10)
        self._write_spawn_event(
            session_id="s1", claimed_sha=self._real_sha,  # match, but stale
            ts=old_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        csrr._reconcile_read(
            file_path=str(self._skill_path),
            file_hash=self._real_sha,
            session_id="s1",
            repo_root=self._root,
            project_dir=str(self._root),
        )
        self.assertEqual(self._reconciled_verdict(), "stale_spawn")

    def test_no_spawn_claim_found_recorded(self) -> None:
        # No spawn event in audit-log
        csrr._reconcile_read(
            file_path=str(self._skill_path),
            file_hash=self._real_sha,
            session_id="s1",
            repo_root=self._root,
            project_dir=str(self._root),
        )
        self.assertEqual(self._reconciled_verdict(), "no_spawn_claim_found")

    def test_dedupe_same_session_skill_pair(self) -> None:
        now = datetime.now(timezone.utc)
        self._write_spawn_event(
            session_id="s1", claimed_sha=self._real_sha,
            ts=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        # First reconcile
        csrr._reconcile_read(
            file_path=str(self._skill_path),
            file_hash=self._real_sha,
            session_id="s1",
            repo_root=self._root,
            project_dir=str(self._root),
        )
        # Second reconcile with a FAKE different hash — if dedupe works,
        # no new record is written (verdict stays "match").
        csrr._reconcile_read(
            file_path=str(self._skill_path),
            file_hash="different-hash",
            session_id="s1",
            repo_root=self._root,
            project_dir=str(self._root),
        )
        state_path = csrr._session_state_path("s1")
        records = csrr._load_session_state(state_path)
        # Load returns dict keyed by skill_path; last-write-wins via dict
        # semantics. But the second call short-circuits BEFORE append, so
        # only one record is in the file.
        with open(state_path, "r", encoding="utf-8") as fh:
            lines = [l for l in fh.read().splitlines() if l]
        self.assertEqual(len(lines), 1, f"expected 1 record, got {len(lines)}")


class KillSwitchTests(unittest.TestCase):
    """CEO_SKILL_READ_V2=0 disables v2, retains v1 baseline."""

    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self._root = Path(self._td.name).resolve()
        self._skill_dir = self._root / ".claude" / "skills" / "core" / "k"
        self._skill_dir.mkdir(parents=True, exist_ok=True)
        self._skill_path = self._skill_dir / "SKILL.md"
        self._skill_path.write_text("body", encoding="utf-8")

    def tearDown(self) -> None:
        self._td.cleanup()

    def test_kill_switch_skips_reconcile(self) -> None:
        reconcile_called = {"hit": False}

        original = csrr._reconcile_read

        def spy(*args, **kwargs):
            reconcile_called["hit"] = True
            return original(*args, **kwargs)

        with patch.dict(os.environ, {"CEO_SKILL_READ_V2": "0"}):
            with patch.object(csrr, "_reconcile_read", spy):
                csrr.decide(
                    file_path=str(self._skill_path),
                    repo_root=self._root,
                    project_dir=str(self._root),
                    session_id="s1",
                )
        self.assertFalse(
            reconcile_called["hit"],
            "kill-switch should prevent _reconcile_read call",
        )


if __name__ == "__main__":
    unittest.main()
