"""Integration tests for replay-session.py capture + replay-fixture handlers.

PLAN-069 Phase 1. Covers:
- Section H : Capture mode CLI gates + atomic write + round-trip
- Section I : Replay-fixture mode CLI gates + tampered-fixture rejections
- R9 fix   : dry_run spawn_copy redaction (Round 1 P0-SEC-01 regression)

Mirrors the existing test_replay_session.py pattern: explicit env snapshot
+ inline restore (project files predate TestEnvContext rollout under
.claude/scripts/replay/tests/, where no conftest.py exists yet — the
top docstring of test_replay_session.py explicitly notes "inline bootstrap
to avoid touching .claude/**/conftest.py canonical-edit guarded").

Stdlib only. Python 3.9-compatible.
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
from typing import Any, Dict, List


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


class _CaptureBase(unittest.TestCase):
    """Shared isolated-environment setup (mirrors test_replay_session.py)."""

    def setUp(self) -> None:
        super().setUp()
        # NOTE: macOS tempfile.mkdtemp returns /var/... which resolves
        # through a symlink chain to /private/var/... — and replay-session.py's
        # `_resolve_under_project` walks parents and refuses any symlink in
        # the chain (P1-SEC-04 TOCTOU guard). We resolve to the canonical
        # path BEFORE using so CLAUDE_PROJECT_DIR matches what argparse sees.
        self.tmp = Path(tempfile.mkdtemp(prefix="ceo-replay-capture-test-")).resolve()
        self.project_dir = self.tmp / "project"
        self.home_dir = self.tmp / "home"
        self.audit_dir = self.home_dir / ".claude" / "projects" / "test"
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        # Output area
        self.out_dir = self.project_dir / "state" / "fixtures"
        self.out_dir.mkdir(parents=True, exist_ok=True)

        # Snapshot env
        self._env_snap = {}
        for k in ("CEO_AUDIT_LOG_PATH", "CEO_AUDIT_LOG_DIR", "CEO_AUDIT_LOG_ERR",
                  "CEO_AUDIT_LOG_LOCK", "CLAUDE_PROJECT_DIR", "HOME",
                  "CEO_LIVE_ADAPTER_STUB", "CEO_OTEL_DISABLED"):
            self._env_snap[k] = os.environ.get(k)
        os.environ["HOME"] = str(self.home_dir)
        os.environ["CLAUDE_PROJECT_DIR"] = str(self.project_dir)
        self.audit_log = self.audit_dir / "audit-log.jsonl"
        os.environ["CEO_AUDIT_LOG_PATH"] = str(self.audit_log)
        os.environ["CEO_AUDIT_LOG_DIR"] = str(self.audit_dir)
        os.environ["CEO_AUDIT_LOG_ERR"] = str(self.audit_dir / "audit-log.errors")
        os.environ["CEO_AUDIT_LOG_LOCK"] = str(self.audit_dir / "audit-log.lock")

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

    def _owner(self) -> str:
        return self.mod._current_user()

    def write_audit(self, events: List[Dict[str, Any]]) -> None:
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

    def _seed_one_spawn(self, *, owner: str = "", with_os_path: bool = True):
        """Write a single agent_spawn event for PLAN-069."""
        owner = owner or self._owner()
        ev: Dict[str, Any] = {
            "ts": "2026-05-03T10:00:00Z",
            "action": "agent_spawn",
            "plan_id": "PLAN-069",
            "session_id": "sid-capture-1",
            "user": owner,
            "skill": "qa-architect",
            "subagent_type": "Principal QA Architect",
            "spawn_ordinal": 0,
            "spawn_id": 1,
            "payload_hash": "deadbeefcafebabe",
            "desc_hash": "feedfacefeedface",
        }
        if with_os_path:
            ev["desc_preview"] = "build at /Users/devuser/ceo-orch/x.py"
            ev["project"] = "/Users/devuser/ceo-orchestration"
        else:
            ev["desc_preview"] = "build something benign"
            ev["project"] = "/usr/local/share/proj"
        self.write_audit([ev])


# ---------------------------------------------------------------------------
# Section H — Capture mode integration
# ---------------------------------------------------------------------------


class TestCaptureMode(_CaptureBase):
    """Round 1 conditions #1 / #2 / #3 / #6 wired through CLI surface."""

    def test_h_01_capture_without_redact_pii_exit_16(self):
        """Round 1 Cond #2: --mode=capture without --redact-pii => EXIT_USAGE."""
        self._seed_one_spawn()
        out_path = self.out_dir / "fixture.jsonl"
        code, _, _ = self.run_main([
            "--plan", "PLAN-069", "--mode", "capture",
            "--out", str(out_path), "--json",
        ])
        self.assertEqual(code, 16)

    def test_h_02_redact_pii_skip_rejected(self):
        """Round 1 Cond #2: only literal 'enforced' accepted."""
        self._seed_one_spawn()
        out_path = self.out_dir / "fixture.jsonl"
        code, _, _ = self.run_main([
            "--plan", "PLAN-069", "--mode", "capture",
            "--redact-pii", "skip",
            "--out", str(out_path), "--json",
        ])
        self.assertEqual(code, 16)

    def test_h_03_redact_pii_enforced_accepted(self):
        """Round 1 Cond #2: literal 'enforced' is the ONE accepted token."""
        self._seed_one_spawn()
        out_path = self.out_dir / "fixture.jsonl"
        code, out, err = self.run_main([
            "--plan", "PLAN-069", "--mode", "capture",
            "--redact-pii", "enforced",
            "--out", str(out_path), "--json",
        ])
        self.assertEqual(code, 0, f"out={out}, err={err}")
        self.assertTrue(out_path.is_file())

    def test_h_04_allow_live_in_capture_exit_16(self):
        """Round 1 P0-SEC-04: --allow-live in capture-mode => EXIT_USAGE."""
        self._seed_one_spawn()
        out_path = self.out_dir / "fixture.jsonl"
        code, _, _ = self.run_main([
            "--plan", "PLAN-069", "--mode", "capture",
            "--redact-pii", "enforced",
            "--out", str(out_path), "--allow-live",
            "--json",
        ])
        self.assertEqual(code, 16)

    def test_h_05_owner_confirm_in_capture_exit_16(self):
        """Round 1 P0-SEC-04: --owner-confirm in capture-mode => EXIT_USAGE."""
        self._seed_one_spawn()
        out_path = self.out_dir / "fixture.jsonl"
        code, _, _ = self.run_main([
            "--plan", "PLAN-069", "--mode", "capture",
            "--redact-pii", "enforced",
            "--out", str(out_path), "--owner-confirm",
            "--json",
        ])
        self.assertEqual(code, 16)

    def test_h_06_out_outside_project_dir_exit_16(self):
        """P1-SEC-04: --out resolving outside CLAUDE_PROJECT_DIR => EXIT_USAGE."""
        self._seed_one_spawn()
        # Path OUTSIDE the project: use a sibling dir under tmp
        outside = self.tmp / "elsewhere" / "fixture.jsonl"
        outside.parent.mkdir(parents=True, exist_ok=True)
        code, _, _ = self.run_main([
            "--plan", "PLAN-069", "--mode", "capture",
            "--redact-pii", "enforced",
            "--out", str(outside), "--json",
        ])
        self.assertEqual(code, 16)

    def test_h_07_out_via_symlink_rejected(self):
        """P1-SEC-04: symlink in --out path is rejected => EXIT_USAGE."""
        self._seed_one_spawn()
        # Create a symlink inside project_dir pointing somewhere else
        outside_dir = self.tmp / "outside-target"
        outside_dir.mkdir(parents=True, exist_ok=True)
        link = self.project_dir / "linked-fixtures"
        try:
            link.symlink_to(outside_dir)
        except OSError:
            self.skipTest("symlink creation not supported on this platform")
        out_path = link / "fixture.jsonl"
        code, _, _ = self.run_main([
            "--plan", "PLAN-069", "--mode", "capture",
            "--redact-pii", "enforced",
            "--out", str(out_path), "--json",
        ])
        self.assertEqual(code, 16)

    def test_h_08_audit_log_outside_projects_dir_exit_16(self):
        """P1-SEC-02: --audit-log outside .claude/projects/ in capture => EXIT_USAGE."""
        self._seed_one_spawn()
        # An audit-log path inside project but NOT under .claude/projects
        bad_log = self.project_dir / "state" / "stray-audit.jsonl"
        bad_log.parent.mkdir(parents=True, exist_ok=True)
        bad_log.write_text(
            json.dumps({"action": "agent_spawn", "plan_id": "PLAN-069",
                        "session_id": "s1", "ts": "2026-05-03T10:00:00Z",
                        "user": self._owner(), "skill": "x"}) + "\n",
            encoding="utf-8",
        )
        out_path = self.out_dir / "fixture.jsonl"
        code, _, _ = self.run_main([
            "--plan", "PLAN-069", "--mode", "capture",
            "--redact-pii", "enforced",
            "--out", str(out_path),
            "--audit-log", str(bad_log),
            "--json",
        ])
        self.assertEqual(code, 16)

    def test_h_08b_ceo_audit_log_path_env_var_bypass_blocked(self):
        """P1-SEC-02 / Codex S81 P2#3: CEO_AUDIT_LOG_PATH env var pointing
        outside .claude/projects/ MUST be rejected with EXIT_USAGE in capture
        mode, even when --audit-log flag is absent.

        Pre-fix repro: setting CEO_AUDIT_LOG_PATH to an outside path and
        omitting --audit-log let the capture proceed because the validator
        only looked at args.audit_log. _default_audit_log() then read the
        env var unguarded, defeating the projects/ scope enforcement.
        """
        # Build outside-project audit-log path
        outside_audit_dir = self.tmp / "outside-project"
        outside_audit_dir.mkdir(parents=True, exist_ok=True)
        outside_log = outside_audit_dir / "audit-log.jsonl"
        outside_log.write_text(
            json.dumps({
                "action": "agent_spawn", "plan_id": "PLAN-069",
                "session_id": "sid-bypass", "ts": "2026-05-03T10:00:00Z",
                "user": self._owner(), "skill": "x",
                "spawn_ordinal": 0, "spawn_id": 1,
                "desc_preview": "outside path leak attempt",
            }) + "\n",
            encoding="utf-8",
        )
        # Override env-var to outside path; --audit-log flag intentionally omitted
        os.environ["CEO_AUDIT_LOG_PATH"] = str(outside_log)
        out_path = self.out_dir / "fixture-bypass-attempt.jsonl"
        code, _, _ = self.run_main([
            "--plan", "PLAN-069", "--mode", "capture",
            "--redact-pii", "enforced",
            "--out", str(out_path),
            "--json",
        ])
        self.assertEqual(code, 16, "env-var bypass MUST be rejected EXIT_USAGE=16")
        # Fixture MUST NOT have been written (fail before any FS write)
        self.assertFalse(out_path.exists(),
                         "outside-project capture wrote fixture despite EXIT_USAGE")

    def test_h_09_successful_capture_writes_valid_fixture(self):
        """Round 1 Cond #6: written fixture passes verify_fixture_meta.

        We assert the canonical ``/Users/devuser/`` PATH SHAPE is gone
        from event bodies (this is what R9 + Round 1 Cond #1 actually
        cover). The bare scalar ``"user": "devuser"`` field is NOT
        a path and NOT covered by ``_strip_os_username``; documenting
        that gap below.

        REGRESSION MARKER (production gap): bare username scalar fields
        like ``user``/``owner``/``as_user`` survive redaction. PLAN-069
        Phase 1 scope is path-shaped leaks. Free-form username field
        redaction belongs to a future ``user_field`` family in
        pii_patterns. CEO triage required if this is in scope.
        """
        self._seed_one_spawn()
        out_path = self.out_dir / "fixture.jsonl"
        code, out, _ = self.run_main([
            "--plan", "PLAN-069", "--mode", "capture",
            "--redact-pii", "enforced",
            "--out", str(out_path), "--json",
        ])
        self.assertEqual(code, 0)
        lines = out_path.read_text(encoding="utf-8").strip().splitlines()
        self.assertGreaterEqual(len(lines), 2, "expected meta + ≥1 event")
        meta = json.loads(lines[0])
        self.assertTrue(meta.get("_meta"))
        spec = importlib.util.spec_from_file_location(
            "rrl",
            str(REPO_ROOT / ".claude" / "hooks" / "_lib" / "replay_redact.py"),
        )
        rrl = importlib.util.module_from_spec(spec)  # type: ignore
        sys.modules[spec.name] = rrl  # type: ignore
        spec.loader.exec_module(rrl)  # type: ignore
        ok, reason = rrl.verify_fixture_meta(meta)
        self.assertTrue(ok, f"verify failed: {reason}")
        # Round 1 Cond #1: PATH SHAPE redacted (canonical leak vector)
        body = "\n".join(lines[1:])
        self.assertNotIn("/Users/devuser/", body,
                         "OS path leaked through redaction")
        self.assertIn("[REDACTED:OS_PATH]", body)

    def test_h_10_round_trip_capture_then_replay_fixture(self):
        """Capture writes fixture; replay-fixture reads it cleanly => exit 0."""
        self._seed_one_spawn()
        out_path = self.out_dir / "round-trip.jsonl"
        code, _, _ = self.run_main([
            "--plan", "PLAN-069", "--mode", "capture",
            "--redact-pii", "enforced",
            "--out", str(out_path), "--quiet",
        ])
        self.assertEqual(code, 0)
        # Replay it back
        code2, out2, err2 = self.run_main([
            "--plan", "PLAN-069", "--mode", "replay-fixture",
            "--fixture", str(out_path), "--json",
        ])
        self.assertEqual(code2, 0, f"out={out2}, err={err2}")

    def test_h_11_r9_dry_run_redacts_spawn_copy_os_path(self):
        """Round 1 P0-SEC-01 R9 fix: dry_run state/replay-out spawn_copy
        MUST contain [REDACTED:OS_PATH] for any /Users/... input field.

        Regression test for replay-session.py:354 + :477 raw-write of
        spawn dict to per-run JSON artifact.
        """
        owner = self._owner()
        self.write_audit([{
            "ts": "2026-05-03T10:00:00Z",
            "action": "agent_spawn",
            "plan_id": "PLAN-069", "session_id": "sid-r9", "user": owner,
            "skill": "x", "spawn_id": 1, "spawn_ordinal": 0,
            "desc_preview": "boot at /Users/devuser/ceo-orch/foo.py",
            "project": "/Users/devuser/ceo-orchestration",
        }])
        code, _, _ = self.run_main([
            "--plan", "PLAN-069", "--json", "--quiet",
        ])
        self.assertEqual(code, 0)
        # state/replay-out/<replay_id>/spawn-0000.json
        out_root = self.project_dir / "state" / "replay-out"
        self.assertTrue(out_root.is_dir())
        # find the per-run subdir + spawn-0000.json
        spawn_files = list(out_root.glob("*/spawn-0000.json"))
        self.assertEqual(len(spawn_files), 1, f"got {spawn_files}")
        artifact = json.loads(spawn_files[0].read_text(encoding="utf-8"))
        spawn_copy = artifact["spawn_copy"]
        # Round 1 P0-SEC-01: verify devuser NOT present, REDACTED token present
        flat = json.dumps(spawn_copy, ensure_ascii=False)
        # Round 1 P0-SEC-01: PATH SHAPE redacted (the leak Round 1 surfaced
        # was `/Users/.../...` path values, NOT bare-username scalars; see
        # test_h_09 docstring for the bare-username gap regression marker).
        self.assertNotIn("/Users/devuser/", flat,
                         "R9 LEAK — OS path present in spawn_copy")
        self.assertIn("[REDACTED:OS_PATH]", flat,
                      "R9 fix — OS_PATH token absent from spawn_copy")


# ---------------------------------------------------------------------------
# Section I — Replay-fixture mode integration
# ---------------------------------------------------------------------------


class TestReplayFixtureMode(_CaptureBase):
    """Replay-fixture trust-boundary CLI gates."""

    def _make_valid_fixture(self) -> Path:
        """Capture a valid fixture for use in tampering tests."""
        self._seed_one_spawn()
        out_path = self.out_dir / "valid.jsonl"
        code, _, _ = self.run_main([
            "--plan", "PLAN-069", "--mode", "capture",
            "--redact-pii", "enforced",
            "--out", str(out_path), "--quiet",
        ])
        self.assertEqual(code, 0)
        return out_path

    def test_i_01_missing_fixture_arg_exit_16(self):
        """--mode=replay-fixture without --fixture => EXIT_USAGE."""
        code, _, _ = self.run_main([
            "--plan", "PLAN-069", "--mode", "replay-fixture", "--json",
        ])
        self.assertEqual(code, 16)

    def test_i_02_missing_fixture_file_exit_7(self):
        """Resolved-but-not-existing fixture => EXIT_MISSING_INPUT (7)."""
        ghost = self.project_dir / "state" / "fixtures" / "ghost.jsonl"
        code, _, _ = self.run_main([
            "--plan", "PLAN-069", "--mode", "replay-fixture",
            "--fixture", str(ghost), "--json",
        ])
        self.assertEqual(code, 7)

    def test_i_03_empty_fixture_exit_18(self):
        """Empty file => EXIT_FIXTURE_INVALID."""
        empty = self.out_dir / "empty.jsonl"
        empty.write_text("", encoding="utf-8")
        code, _, _ = self.run_main([
            "--plan", "PLAN-069", "--mode", "replay-fixture",
            "--fixture", str(empty), "--json",
        ])
        self.assertEqual(code, 18)

    def test_i_04_tampered_content_hash_exit_18(self):
        """Round 1 Cond #6: P1-SEC-01 fixture-forgery defense.

        Tamper an event line so recomputed content_sha != captured_by_hash.
        """
        valid = self._make_valid_fixture()
        # Mutate one event line (preserve JSON validity)
        lines = valid.read_text(encoding="utf-8").splitlines()
        self.assertGreaterEqual(len(lines), 2)
        ev = json.loads(lines[1])
        ev["desc_preview"] = "[TAMPERED]"
        lines[1] = json.dumps(ev, ensure_ascii=False, sort_keys=True)
        tampered = self.out_dir / "tampered.jsonl"
        tampered.write_text("\n".join(lines) + "\n", encoding="utf-8")
        code, _, _ = self.run_main([
            "--plan", "PLAN-069", "--mode", "replay-fixture",
            "--fixture", str(tampered), "--json",
        ])
        self.assertEqual(code, 18)

    def test_i_05_schema_newer_than_supported_exit_18(self):
        """Round 1 Cond #6: schema-version-not-newer => EXIT_FIXTURE_INVALID."""
        valid = self._make_valid_fixture()
        lines = valid.read_text(encoding="utf-8").splitlines()
        meta = json.loads(lines[0])
        meta["schema"] = "v9.99"
        lines[0] = json.dumps(meta, ensure_ascii=False, sort_keys=True)
        bumped = self.out_dir / "bumped-schema.jsonl"
        bumped.write_text("\n".join(lines) + "\n", encoding="utf-8")
        code, _, _ = self.run_main([
            "--plan", "PLAN-069", "--mode", "replay-fixture",
            "--fixture", str(bumped), "--json",
        ])
        self.assertEqual(code, 18)

    def test_i_06_post_load_defense_leak_exit_19(self):
        """Round 1 Cond #6: tampered fixture with raw sk-... post-redaction
        => EXIT_FIXTURE_DEFENSE_LEAK.

        We hand-build a fixture (bypassing the captured_by_hash gate by
        recomputing it after we inject the leak) so the test isolates the
        post-load family-flag scan rather than the content-hash gate.
        """
        spec = importlib.util.spec_from_file_location(
            "rrl",
            str(REPO_ROOT / ".claude" / "hooks" / "_lib" / "replay_redact.py"),
        )
        rrl = importlib.util.module_from_spec(spec)  # type: ignore
        sys.modules[spec.name] = rrl  # type: ignore
        spec.loader.exec_module(rrl)  # type: ignore

        # 1 leak event with raw sk-... (post-redaction tamper)
        ev = {"action": "agent_spawn",
              "leaked": "sk-ant-api03-" + "a" * 40,
              "_synthetic": True}
        ev_line = rrl.serialize_event(ev)
        nonce = rrl.new_fixture_salt()
        content_sha = rrl.fixture_content_sha256([ev_line])
        meta = rrl.build_meta(
            nonce=nonce,
            captured_at_iso="2026-05-03T00:00:00Z",
            plan_id="PLAN-069",
            original_session_id="sid-tamper",
            event_count=1,
            pre_meta_content_sha256=content_sha,
        )
        leak_path = self.out_dir / "leak.jsonl"
        leak_path.write_text(
            rrl.serialize_event(meta) + "\n" + ev_line + "\n",
            encoding="utf-8",
        )
        code, out, _ = self.run_main([
            "--plan", "PLAN-069", "--mode", "replay-fixture",
            "--fixture", str(leak_path), "--json",
        ])
        self.assertEqual(code, 19)
        payload = json.loads(out)
        self.assertGreaterEqual(len(payload.get("leaks_post_load", [])), 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
