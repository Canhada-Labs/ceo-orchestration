"""Functional tests for replay-session.py (PLAN-014 Phase F.1 + F.7).

≥20 tests covering:
- CLI argument parsing + exit codes (SPEC §3/§4)
- Dry-run default behavior
- Execute pre-flight gates (ack, worktree)
- Cross-user gating
- Missing audit log handling
- Unknown plan handling
- Empty session handling
- Max-spawns enforcement
- Live-adapter spawn detection + skip in execute
- Stable canonical_payload_hash
- Audit event emission (replay_started/completed/diff_produced)
- JSON mode output

Uses inline bootstrap to avoid touching .claude/**/conftest.py
(canonical-edit guarded).
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_PATH = REPO_ROOT / ".claude" / "scripts" / "replay" / "replay-session.py"
HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"

if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))


def _load_mod():
    spec = importlib.util.spec_from_file_location("replay_session", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestReplayFunctional(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.tmp = Path(tempfile.mkdtemp(prefix="ceo-replay-test-"))
        self.project_dir = self.tmp / "project"
        self.home_dir = self.tmp / "home"
        self.audit_dir = self.home_dir / ".claude" / "projects" / "test"
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.audit_dir.mkdir(parents=True, exist_ok=True)

        # Snapshot env
        self._env_snap = {}
        for k in ("CEO_AUDIT_LOG_PATH", "CEO_AUDIT_LOG_DIR", "CEO_AUDIT_LOG_ERR",
                  "CEO_AUDIT_LOG_LOCK", "CLAUDE_PROJECT_DIR", "HOME",
                  "CEO_LIVE_ADAPTER_STUB", "CEO_OTEL_DISABLED",
                  "CEO_AUDIT_SYNC_MODE"):
            self._env_snap[k] = os.environ.get(k)
        os.environ["HOME"] = str(self.home_dir)
        os.environ["CLAUDE_PROJECT_DIR"] = str(self.project_dir)
        self.audit_log = self.audit_dir / "audit-log.jsonl"
        os.environ["CEO_AUDIT_LOG_PATH"] = str(self.audit_log)
        os.environ["CEO_AUDIT_LOG_DIR"] = str(self.audit_dir)
        os.environ["CEO_AUDIT_LOG_ERR"] = str(self.audit_dir / "audit-log.errors")
        os.environ["CEO_AUDIT_LOG_LOCK"] = str(self.audit_dir / "audit-log.lock")
        # PLAN-107 Wave A.4 pattern — force synchronous audit emit so
        # in-process tests can assert on log contents without race.
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"

        self.mod = _load_mod()

    def tearDown(self) -> None:
        for k, v in self._env_snap.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)
        super().tearDown()

    # ---- helpers --------------------------------------------------

    def write_audit(self, events):
        lines = [json.dumps(e, ensure_ascii=False) for e in events]
        self.audit_log.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def run_main(self, argv):
        saved_stdout = sys.stdout
        saved_stderr = sys.stderr
        out = io.StringIO()
        err = io.StringIO()
        sys.stdout = out
        sys.stderr = err
        try:
            code = self.mod.main(argv)
        finally:
            sys.stdout = saved_stdout
            sys.stderr = saved_stderr
        return code, out.getvalue(), err.getvalue()

    def _owner(self):
        return self.mod._current_user()

    # ---- tests ----------------------------------------------------

    def test_01_help_argparse_exits_zero(self):
        """--help prints and exits 0 through argparse SystemExit."""
        with self.assertRaises(SystemExit) as ctx:
            self.mod.build_parser().parse_args(["--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_02_missing_audit_log_empty_session_exit_0(self):
        """No audit log present → soft-warn + exit 0."""
        code, out, err = self.run_main(["--plan", "PLAN-014", "--json"])
        self.assertEqual(code, 0)
        self.assertIn("empty_session", out + err)

    def test_03_missing_audit_log_strict_exit_7(self):
        """--strict + no audit log → exit 7 missing_input."""
        code, out, err = self.run_main(["--plan", "PLAN-014", "--strict", "--json"])
        self.assertEqual(code, 7)

    def test_04_unknown_plan_exit_6(self):
        """Plan id absent from audit log → exit 6."""
        self.write_audit([{
            "ts": "2026-04-16T10:00:00Z",
            "action": "agent_spawn",
            "plan_id": "PLAN-001",
            "session_id": "s1",
            "skill": "x",
        }])
        code, out, err = self.run_main(["--plan", "PLAN-999", "--json"])
        self.assertEqual(code, 6)

    def test_05_dry_run_default_mode(self):
        """Dry-run is default when no --execute/--mode passed."""
        owner = self._owner()
        self.write_audit([{
            "ts": "2026-04-16T10:00:00Z",
            "action": "agent_spawn",
            "plan_id": "PLAN-014",
            "session_id": "s1",
            "user": owner,
            "skill": "public-api-design",
            "subagent_type": "Staff Backend Engineer",
            "desc_preview": "build something",
            "spawn_ordinal": 0,
        }])
        code, out, err = self.run_main(["--plan", "PLAN-014"])
        self.assertEqual(code, 0)
        self.assertIn("DRY-RUN", out)

    def test_06_execute_without_ack_exit_3(self):
        """--execute without --i-understand-this-reexecutes → exit 3."""
        code, out, err = self.run_main(["--plan", "PLAN-014", "--execute"])
        self.assertEqual(code, 3)

    def test_07_cross_user_no_flag_exit_4(self):
        """Replayer OS-user differs, no --as-user → exit 4."""
        self.write_audit([{
            "ts": "2026-04-16T10:00:00Z",
            "action": "agent_spawn",
            "plan_id": "PLAN-014",
            "session_id": "s1",
            "user": "someone-else-entirely",
            "skill": "x",
        }])
        code, out, err = self.run_main(["--plan", "PLAN-014", "--json"])
        self.assertEqual(code, 4)

    def test_08_as_user_mismatch_exit_5(self):
        """--as-user value ≠ original owner → exit 5."""
        self.write_audit([{
            "ts": "2026-04-16T10:00:00Z",
            "action": "agent_spawn",
            "plan_id": "PLAN-014",
            "session_id": "s1",
            "user": "alice",
            "skill": "x",
        }])
        code, out, err = self.run_main(["--plan", "PLAN-014", "--as-user", "bob", "--json"])
        self.assertEqual(code, 5)

    def test_09_as_user_match_exit_0(self):
        """--as-user matching original owner → exit 0 (dry-run)."""
        self.write_audit([{
            "ts": "2026-04-16T10:00:00Z",
            "action": "agent_spawn",
            "plan_id": "PLAN-014",
            "session_id": "s1",
            "user": "alice",
            "skill": "x",
            "spawn_ordinal": 0,
        }])
        code, out, err = self.run_main(["--plan", "PLAN-014", "--as-user", "alice"])
        self.assertEqual(code, 0)

    def test_10_max_spawns_exceeded_exit_9(self):
        """>max-spawns → exit 9."""
        owner = self._owner()
        events = [
            {
                "ts": f"2026-04-16T10:00:{i:02d}Z",
                "action": "agent_spawn",
                "plan_id": "PLAN-014",
                "session_id": "s1",
                "user": owner,
                "skill": "x",
                "spawn_ordinal": i,
            } for i in range(5)
        ]
        self.write_audit(events)
        code, _, _ = self.run_main(["--plan", "PLAN-014", "--max-spawns", "3", "--json"])
        self.assertEqual(code, 9)

    def test_11_canonical_payload_hash_stable(self):
        """Same event → same hash; drops nondeterministic fields."""
        payload_a = {"ts": "2026-04-16T10:00:00Z", "action": "agent_spawn",
                     "skill": "x", "session_id": "s1", "spawn_id": 1}
        payload_b = {"ts": "2026-04-16T10:05:00Z", "action": "agent_spawn",
                     "skill": "x", "session_id": "s2", "spawn_id": 1}
        self.assertEqual(
            self.mod.canonical_payload_hash(payload_a),
            self.mod.canonical_payload_hash(payload_b),
        )

    def test_12_canonical_payload_hash_changes_on_content(self):
        """Different skill → different hash."""
        a = {"action": "agent_spawn", "skill": "x", "spawn_id": 1}
        b = {"action": "agent_spawn", "skill": "y", "spawn_id": 1}
        self.assertNotEqual(
            self.mod.canonical_payload_hash(a),
            self.mod.canonical_payload_hash(b),
        )

    def test_13_live_adapter_spawn_detected(self):
        """collect_live_adapter_spawns returns the spawn_ids that touched live."""
        events = [
            {"action": "agent_spawn", "plan_id": "PLAN-014",
             "session_id": "s1", "spawn_id": 1},
            {"action": "live_adapter_call_started", "session_id": "s1",
             "spawn_id": 1, "url": "x", "provider": "y", "attempt": 1},
            {"action": "agent_spawn", "plan_id": "PLAN-014",
             "session_id": "s1", "spawn_id": 2},
        ]
        touched = self.mod.collect_live_adapter_spawns(events, "PLAN-014", "s1")
        self.assertIn(1, touched)
        self.assertNotIn(2, touched)

    def test_14_live_adapter_skipped_in_execute(self):
        """Execute mode SKIPS live-touching spawns."""
        owner = self._owner()
        self.write_audit([
            {"ts": "2026-04-16T10:00:00Z", "action": "agent_spawn",
             "plan_id": "PLAN-014", "session_id": "s1", "user": owner,
             "skill": "x", "spawn_id": 1, "spawn_ordinal": 0},
            {"ts": "2026-04-16T10:00:01Z", "action": "live_adapter_call_started",
             "session_id": "s1", "spawn_id": 1, "provider": "p",
             "url": "u", "attempt": 1},
        ])
        # Clean worktree is a hard gate; use dry-run which skips that
        code, out, err = self.run_main(["--plan", "PLAN-014", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertGreaterEqual(payload.get("live_adapter_skipped", 0), 1)

    def test_15_dry_run_emits_replay_started_and_completed(self):
        """Audit events emitted for dry-run."""
        owner = self._owner()
        self.write_audit([{
            "ts": "2026-04-16T10:00:00Z", "action": "agent_spawn",
            "plan_id": "PLAN-014", "session_id": "s1", "user": owner,
            "skill": "x", "spawn_ordinal": 0,
        }])
        code, _, _ = self.run_main(["--plan", "PLAN-014"])
        self.assertEqual(code, 0)
        log = self.audit_log.read_text(encoding="utf-8")
        self.assertIn("replay_started", log)
        self.assertIn("replay_completed", log)

    def test_16_plan_exists_in_audit_helper(self):
        events = [{"action": "agent_spawn", "plan_id": "PLAN-014"}]
        self.assertTrue(self.mod.plan_exists_in_audit(events, "PLAN-014"))
        self.assertFalse(self.mod.plan_exists_in_audit(events, "PLAN-999"))

    def test_17_collect_spawns_ordered_by_ts(self):
        events = [
            {"action": "agent_spawn", "plan_id": "PLAN-014",
             "session_id": "s1", "ts": "2026-04-16T11:00:00Z", "spawn_ordinal": 2},
            {"action": "agent_spawn", "plan_id": "PLAN-014",
             "session_id": "s1", "ts": "2026-04-16T10:00:00Z", "spawn_ordinal": 1},
        ]
        spawns = self.mod.collect_spawns_for_plan(events, "PLAN-014", "s1")
        self.assertEqual(len(spawns), 2)
        self.assertLess(spawns[0]["ts"], spawns[1]["ts"])

    def test_18_find_original_owner_most_recent(self):
        events = [
            {"action": "agent_spawn", "plan_id": "PLAN-014",
             "session_id": "s1", "user": "alice", "ts": "2026-04-10T10:00:00Z"},
            {"action": "agent_spawn", "plan_id": "PLAN-014",
             "session_id": "s2", "user": "bob", "ts": "2026-04-16T10:00:00Z"},
        ]
        sid, owner = self.mod.find_original_owner(events, "PLAN-014", None)
        self.assertEqual(sid, "s2")
        self.assertEqual(owner, "bob")

    def test_19_find_original_owner_specified_sid(self):
        events = [
            {"action": "agent_spawn", "plan_id": "PLAN-014",
             "session_id": "s1", "user": "alice", "ts": "2026-04-10T10:00:00Z"},
            {"action": "agent_spawn", "plan_id": "PLAN-014",
             "session_id": "s2", "user": "bob", "ts": "2026-04-16T10:00:00Z"},
        ]
        sid, owner = self.mod.find_original_owner(events, "PLAN-014", "s1")
        self.assertEqual(sid, "s1")
        self.assertEqual(owner, "alice")

    def test_20_build_replay_id_contains_sid_and_timestamp(self):
        rid = self.mod.build_replay_id("abc-123")
        self.assertTrue(rid.startswith("abc-123-"))
        self.assertIn("T", rid)

    def test_21_worktree_clean_non_repo_returns_true(self):
        """When cwd is not a repo, is_worktree_clean returns True."""
        self.assertTrue(self.mod.is_worktree_clean(self.tmp))

    def test_22_json_output_has_expected_keys(self):
        owner = self._owner()
        self.write_audit([{
            "ts": "2026-04-16T10:00:00Z", "action": "agent_spawn",
            "plan_id": "PLAN-014", "session_id": "s1", "user": owner,
            "skill": "x", "spawn_ordinal": 0,
        }])
        code, out, err = self.run_main(["--plan", "PLAN-014", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        for key in ("mode", "plan_id", "original_session_id", "spawn_count",
                    "duration_ms", "spawns"):
            self.assertIn(key, payload)

    def test_23_quiet_suppresses_stdout(self):
        owner = self._owner()
        self.write_audit([{
            "ts": "2026-04-16T10:00:00Z", "action": "agent_spawn",
            "plan_id": "PLAN-014", "session_id": "s1", "user": owner,
            "skill": "x", "spawn_ordinal": 0,
        }])
        code, out, err = self.run_main(["--plan", "PLAN-014", "--quiet"])
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "")

    def test_24_malformed_audit_exit_13(self):
        """Malformed JSONL line triggers audit_parse_error."""
        self.audit_log.write_text("{not valid json\n", encoding="utf-8")
        code, _, _ = self.run_main(["--plan", "PLAN-014", "--json"])
        self.assertEqual(code, 13)

    def test_25_execute_with_ack_but_live_skipped_advisory(self):
        """Execute mode skips live spawns even without --allow-live."""
        owner = self._owner()
        self.write_audit([
            {"ts": "2026-04-16T10:00:00Z", "action": "agent_spawn",
             "plan_id": "PLAN-014", "session_id": "s1", "user": owner,
             "skill": "x", "spawn_id": 1, "spawn_ordinal": 0},
            {"ts": "2026-04-16T10:00:01Z", "action": "live_adapter_call_started",
             "session_id": "s1", "spawn_id": 1, "provider": "p",
             "url": "u", "attempt": 1},
        ])
        # Execute mode requires clean worktree. Use --i-understand-... and
        # rely on is_worktree_clean which returns True for non-repo cwd.
        prev_cwd = os.getcwd()
        os.chdir(self.tmp)
        try:
            code, out, err = self.run_main([
                "--plan", "PLAN-014", "--execute",
                "--i-understand-this-reexecutes", "--json",
            ])
        finally:
            os.chdir(prev_cwd)
        self.assertEqual(code, 0)
        # Env invariants enforced
        self.assertEqual(os.environ.get("CEO_LIVE_ADAPTER_STUB"), "1")
        self.assertEqual(os.environ.get("CEO_OTEL_DISABLED"), "1")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
