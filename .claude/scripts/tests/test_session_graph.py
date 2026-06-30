"""Unit tests for session-graph-build.py (PLAN-011 Phase 11).

Exercises:
- Deriving sessions from a fixture audit-log
- --since filter behavior (window bounded)
- Unknown plan = empty graph + exit 0
- CEO_SOTA_DISABLE early exit
- Encryption path (ciphertext detection; decryption round-trip via gpg)
- Plaintext fallback path (WARNING emitted)
- Reverse-map invariant (every session has source_event_refs)
- --all-active filters out status: done plans

All tests use TestEnvContext for HOME/CLAUDE_PROJECT_DIR isolation per the
project's test contract. No real audit-log is touched.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch


_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _SCRIPTS_DIR.parent.parent
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "session_graph_build", _SCRIPTS_DIR / "session-graph-build.py"
)
sgb = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(sgb)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_audit_lines(path: Path, events: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")


class SessionGraphTestBase(TestEnvContext):
    """Base — points CEO_AUDIT_LOG_PATH at a fixture + isolates HOME."""

    def setUp(self) -> None:
        super().setUp()
        self.plans_dir = self.project_dir / ".claude" / "plans"
        self.plans_dir.mkdir(parents=True, exist_ok=True)
        os.environ["CEO_PLANS_DIR"] = str(self.plans_dir)
        # The session graph default output dir goes under $HOME, which
        # TestEnvContext has already isolated.
        self.graph_dir = self.home_dir / ".claude" / "projects" / "test" / "session-graphs"
        os.environ["CEO_SESSION_GRAPH_DIR"] = str(self.graph_dir)
        os.environ["CEO_PROJECT_NAME"] = "test"

        # Write a sample plan file for PLAN-010
        self._write_plan(
            "PLAN-010",
            status="done",
            title="Sprint 10 Polish",
            body=(
                "## Phases\n"
                "- [x] Phase 1 — E2E harness\n"
                "- [x] Phase 8 — Closeout\n"
                "\n"
                "## Deferred to Sprint 11\n"
                "- Flip docs-freshness state 1→2\n"
                "- Flip perf-profile state 0→1\n"
                "\n"
                "## Owner action items\n"
                "- Tag v1.0.0-rc.1\n"
            ),
        )
        # Plan 011 — executing
        self._write_plan(
            "PLAN-011",
            status="executing",
            title="State-of-the-Art Orchestration",
            body=(
                "## Phases\n"
                "- [x] Phase 0 — State backend\n"
                "- [ ] Phase 11 — Session graph\n"
                "\n"
                "## Owner action items\n"
                "- Review canonical envelope\n"
            ),
        )

    def _write_plan(
        self, plan_id: str, *, status: str, title: str, body: str
    ) -> Path:
        num = plan_id.split("-")[1]
        p = self.plans_dir / f"PLAN-{num}-{plan_id.lower()}.md"
        p.write_text(
            "---\n"
            f"id: {plan_id}\n"
            f"title: {title}\n"
            f"status: {status}\n"
            "created: 2026-04-14\n"
            "owner: CEO\n"
            "depends_on: []\n"
            "---\n"
            "\n"
            "# " + title + "\n"
            "\n" + body,
            encoding="utf-8",
        )
        return p

    def _write_fixture_audit(self, plan_id: str = "PLAN-010") -> Path:
        now = datetime.now(timezone.utc)
        log = self.audit_dir / "audit-log.jsonl"
        events = [
            # Session A — spawn + debate
            {
                "action": "agent_spawn",
                "plan_id": plan_id,
                "session_id": "sess-A",
                "ts": _iso(now - timedelta(hours=3)),
            },
            {
                "action": "debate_event",
                "plan_id": plan_id,
                "session_id": "sess-A",
                "round": 1,
                "phase": "start",
                "agent": "vp-engineering",
                "ts": _iso(now - timedelta(hours=2, minutes=45)),
            },
            {
                "action": "debate_event",
                "plan_id": plan_id,
                "session_id": "sess-A",
                "round": 1,
                "phase": "consensus",
                "agent": "consensus",
                "consensus_adjustments_count": 6,
                "ts": _iso(now - timedelta(hours=2)),
            },
            # Session B — another spawn later
            {
                "action": "agent_spawn",
                "plan_id": plan_id,
                "session_id": "sess-B",
                "ts": _iso(now - timedelta(hours=1)),
            },
            {
                "action": "plan_transition",
                "plan_id": plan_id,
                "session_id": "sess-B",
                "from_status": "executing",
                "to_status": "done",
                "ts": _iso(now - timedelta(minutes=30)),
            },
            # Noise — different plan
            {
                "action": "agent_spawn",
                "plan_id": "PLAN-009",
                "session_id": "sess-X",
                "ts": _iso(now - timedelta(hours=2, minutes=30)),
            },
        ]
        _write_audit_lines(log, events)
        return log


class TestBuildGraphHappyPath(SessionGraphTestBase):
    def test_build_from_fixture(self) -> None:
        self._write_fixture_audit("PLAN-010")
        g = sgb.build_graph("PLAN-010", since=timedelta(days=30))
        self.assertEqual(g["plan_id"], "PLAN-010")
        self.assertEqual(g["schema_version"], sgb.GRAPH_SCHEMA_VERSION)
        self.assertEqual(g["plan_status"], "done")
        self.assertEqual(g["plan_title"], "Sprint 10 Polish")
        # 2 sessions derived from fixture
        self.assertEqual(g["session_count"], 2)
        sids = sorted(s["session_id"] for s in g["sessions"])
        self.assertEqual(sids, ["sess-A", "sess-B"])
        # Spawn counts
        by_sid = {s["session_id"]: s for s in g["sessions"]}
        self.assertEqual(by_sid["sess-A"]["spawn_count"], 1)
        self.assertEqual(by_sid["sess-A"]["debate_rounds"], [1])
        self.assertEqual(by_sid["sess-B"]["spawn_count"], 1)
        self.assertEqual(by_sid["sess-B"]["debate_rounds"], [])
        # Event count = 5 events scoped to PLAN-010 (not 6 — PLAN-009 excluded)
        self.assertEqual(g["event_count"], 5)

    def test_reverse_map_invariant(self) -> None:
        """Every session must have source_event_refs enumerating its events."""
        self._write_fixture_audit("PLAN-010")
        g = sgb.build_graph("PLAN-010", since=timedelta(days=30))
        for s in g["sessions"]:
            # source_event_refs is non-empty and each ref has (action, ts)
            self.assertGreater(len(s["source_event_refs"]), 0)
            for ref in s["source_event_refs"]:
                self.assertIn("action", ref)
                self.assertIn("ts", ref)
                # Reverse map: the referenced action is one of the known
                # audit-log actions (not an invented graph field).
                self.assertIn(ref["action"], sgb._audit_emit._KNOWN_ACTIONS)

    def test_last_phase_status_derived(self) -> None:
        self._write_fixture_audit("PLAN-010")
        g = sgb.build_graph("PLAN-010", since=timedelta(days=30))
        # PLAN-010 body has [x] Phase 1 and [x] Phase 8; no pending phases
        self.assertEqual(g["last_phase_status"], "Phase 8: done")

    def test_deferred_and_owner_actions_parsed(self) -> None:
        self._write_fixture_audit("PLAN-010")
        g = sgb.build_graph("PLAN-010", since=timedelta(days=30))
        self.assertEqual(len(g["deferred"]), 2)
        self.assertIn("Flip docs-freshness state 1→2", g["deferred"])
        self.assertEqual(len(g["owner_actions"]), 1)
        self.assertEqual(g["owner_actions"][0], "Tag v1.0.0-rc.1")


class TestBuildGraphSinceFilter(SessionGraphTestBase):
    def test_since_excludes_old_events(self) -> None:
        """Events older than --since must not be counted."""
        now = datetime.now(timezone.utc)
        log = self.audit_dir / "audit-log.jsonl"
        events = [
            {
                "action": "agent_spawn",
                "plan_id": "PLAN-010",
                "session_id": "fresh",
                "ts": _iso(now - timedelta(hours=1)),
            },
            {
                "action": "agent_spawn",
                "plan_id": "PLAN-010",
                "session_id": "stale",
                "ts": _iso(now - timedelta(days=45)),
            },
        ]
        _write_audit_lines(log, events)
        g = sgb.build_graph("PLAN-010", since=timedelta(days=30))
        self.assertEqual(g["session_count"], 1)
        self.assertEqual(g["sessions"][0]["session_id"], "fresh")

    def test_since_forever_includes_old(self) -> None:
        now = datetime.now(timezone.utc)
        log = self.audit_dir / "audit-log.jsonl"
        _write_audit_lines(
            log,
            [
                {
                    "action": "agent_spawn",
                    "plan_id": "PLAN-010",
                    "session_id": "ancient",
                    "ts": _iso(now - timedelta(days=400)),
                }
            ],
        )
        g = sgb.build_graph("PLAN-010", since=None)
        self.assertEqual(g["session_count"], 1)


class TestBuildGraphUnknownPlan(SessionGraphTestBase):
    def test_unknown_plan_returns_empty_graph(self) -> None:
        """Unknown plan = empty graph, no exception, no error."""
        self._write_fixture_audit("PLAN-010")
        g = sgb.build_graph("PLAN-999", since=timedelta(days=30))
        self.assertEqual(g["plan_id"], "PLAN-999")
        self.assertEqual(g["session_count"], 0)
        self.assertEqual(g["event_count"], 0)
        self.assertEqual(g["commit_count"], 0)
        # Plan status falls back to 'unknown' when plan file missing
        self.assertEqual(g["plan_status"], "unknown")


class TestSotaDisableKillSwitch(SessionGraphTestBase):
    def test_main_early_exits_when_disabled(self) -> None:
        self._write_fixture_audit("PLAN-010")
        os.environ["CEO_SOTA_DISABLE"] = "1"
        buf = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            rc = sgb.main(["--plan", "PLAN-010", "--no-encrypt"])
        self.assertEqual(rc, 0)
        self.assertEqual(buf.getvalue(), "")
        self.assertEqual(err.getvalue(), "")
        # Graph dir should NOT have been created
        self.assertFalse(self.graph_dir.exists())


class TestDoesNotDuplicateAuditVerbatim(SessionGraphTestBase):
    def test_sessions_reference_audit_rather_than_copy(self) -> None:
        """Sessions MUST carry source_event_refs (pointers) and MUST NOT
        embed full audit event payloads verbatim.

        This protects M3: the graph is derived, not a new source of truth.
        """
        self._write_fixture_audit("PLAN-010")
        g = sgb.build_graph("PLAN-010", since=timedelta(days=30))
        for s in g["sessions"]:
            # Each source ref is a lightweight pointer (action + ts), NOT a
            # full event payload. Assert there's no 'artifact_path', no
            # 'plan_id' duplication inside source_event_refs.
            for ref in s["source_event_refs"]:
                self.assertEqual(set(ref.keys()), {"action", "ts"})


class TestCliMain(SessionGraphTestBase):
    def test_plain_output(self) -> None:
        self._write_fixture_audit("PLAN-010")
        buf = io.StringIO()
        err = io.StringIO()
        out_path = self._tmp_root / "g.json"
        with redirect_stdout(buf), redirect_stderr(err):
            rc = sgb.main(
                ["--plan", "PLAN-010", "--no-encrypt", "--output", str(out_path)]
            )
        self.assertEqual(rc, 0, f"stderr: {err.getvalue()}")
        self.assertTrue(out_path.exists())
        # Output is a JSON file with expected shape
        loaded = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertEqual(loaded["plan_id"], "PLAN-010")
        self.assertIn("sessions", loaded)
        # Should have a WARNING about plaintext mode
        self.assertIn("PLAINTEXT", err.getvalue())

    def test_invalid_plan_id_rejected(self) -> None:
        buf = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            rc = sgb.main(["--plan", "not-a-plan", "--no-encrypt"])
        self.assertEqual(rc, 2)
        self.assertIn("PLAN-NNN", err.getvalue())

    def test_invalid_since_rejected(self) -> None:
        buf = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            rc = sgb.main(
                ["--plan", "PLAN-010", "--since", "bogus", "--no-encrypt"]
            )
        self.assertEqual(rc, 2)

    def test_all_active_filters_done_plans(self) -> None:
        """--all-active must include PLAN-011 (executing) and skip PLAN-010 (done)."""
        self._write_fixture_audit("PLAN-010")
        actives = sgb._active_plan_ids()
        self.assertIn("PLAN-011", actives)
        self.assertNotIn("PLAN-010", actives)


class TestEncryptionPath(SessionGraphTestBase):
    """Encryption path validation.

    If gpg is available AND we can set up a test key, we verify the
    output is ciphertext + decrypts round-trip. Otherwise we verify the
    plaintext-fallback path emits the required WARNING.
    """

    def test_no_key_plaintext_fallback_with_warning(self) -> None:
        """With no CEO_GPG_FINGERPRINT and no age recipient, encrypt
        flag must fall through to plaintext and emit a WARNING on stderr."""
        self._write_fixture_audit("PLAN-010")
        # Ensure no encryption-key hints in env
        os.environ.pop("CEO_GPG_FINGERPRINT", None)
        # Point age recipient at a non-existent file to force fallback
        os.environ["CEO_AGE_RECIPIENT_FILE"] = str(self._tmp_root / "no-such.txt")

        buf = io.StringIO()
        err = io.StringIO()
        out_target = self.home_dir / "tmp-out.json.age"
        with redirect_stdout(buf), redirect_stderr(err):
            rc = sgb.main(
                [
                    "--plan",
                    "PLAN-010",
                    "--output",
                    str(out_target),
                    "--encrypt",
                ]
            )
        self.assertEqual(rc, 0, f"stderr: {err.getvalue()}")
        stderr_text = err.getvalue()
        self.assertIn("no encryption key", stderr_text)
        self.assertIn("WARNING", stderr_text)
        # The fallback path writes a .plain.json sibling
        # (we use the suffix replacement rule)
        expected_plain = out_target.with_suffix(".plain.json")
        self.assertTrue(
            expected_plain.exists(),
            f"expected plaintext fallback at {expected_plain}; "
            f"got files: {list(out_target.parent.iterdir())}",
        )
        # And the file parses as JSON (not gibberish)
        loaded = json.loads(expected_plain.read_text(encoding="utf-8"))
        self.assertEqual(loaded["plan_id"], "PLAN-010")

    def test_ciphertext_round_trip_with_gpg(self) -> None:
        """If gpg is present, generate an ephemeral key, encrypt, verify
        the output is NOT parseable JSON (= ciphertext), then decrypt and
        verify round-trip matches the original graph."""
        if not shutil.which("gpg"):
            self.skipTest("gpg not available in this environment")

        self._write_fixture_audit("PLAN-010")
        gnupg_home = self._tmp_root / "gnupg"
        gnupg_home.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(gnupg_home, 0o700)
        except OSError:
            pass
        # Restore GNUPGHOME on teardown — TestEnvContext only snapshots CEO_*/
        # CLAUDE_*/HOME, so without this the var leaks pointing at the rmtree'd
        # temp dir into later sequential gpg subprocesses (order-dependent flake).
        self.addCleanup(
            lambda _g=os.environ.get("GNUPGHOME"):
            os.environ.__setitem__("GNUPGHOME", _g) if _g is not None
            else os.environ.pop("GNUPGHOME", None)
        )
        os.environ["GNUPGHOME"] = str(gnupg_home)

        # Generate an ephemeral unprotected key
        batch = (
            "%no-protection\n"
            "Key-Type: eddsa\n"
            "Key-Curve: ed25519\n"
            "Subkey-Type: ecdh\n"
            "Subkey-Curve: cv25519\n"
            "Name-Real: Test Key\n"
            "Name-Email: test@example.com\n"
            "Expire-Date: 0\n"
            "%commit\n"
        )
        try:
            subprocess.run(
                ["gpg", "--batch", "--gen-key"],
                input=batch,
                check=True,
                capture_output=True,
                timeout=30,
                text=True,
            )
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            self.skipTest("gpg key generation failed in this environment")

        # Discover the fingerprint
        try:
            proc = subprocess.run(
                ["gpg", "--with-colons", "--list-keys", "test@example.com"],
                check=True,
                capture_output=True,
                timeout=10,
                text=True,
            )
        except subprocess.SubprocessError:
            self.skipTest("gpg list-keys failed")
        fingerprint = ""
        for line in proc.stdout.splitlines():
            if line.startswith("fpr:"):
                fingerprint = line.split(":")[9]
                break
        if not fingerprint:
            self.skipTest("could not discover gpg fingerprint")
        os.environ["CEO_GPG_FINGERPRINT"] = fingerprint
        # Force age path unavailable
        os.environ["CEO_AGE_RECIPIENT_FILE"] = str(self._tmp_root / "no-age.txt")

        out_target = self.home_dir / "enc-out.json.gpg"
        buf = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            rc = sgb.main(
                ["--plan", "PLAN-010", "--output", str(out_target), "--encrypt"]
            )
        self.assertEqual(rc, 0, f"stderr: {err.getvalue()}")
        self.assertTrue(out_target.exists())

        # Raw bytes MUST NOT be valid JSON (= real ciphertext)
        raw = out_target.read_bytes()
        with self.assertRaises((json.JSONDecodeError, UnicodeDecodeError)):
            json.loads(raw.decode("utf-8"))

        # Decryption round-trip
        dec = subprocess.run(
            ["gpg", "--batch", "--yes", "--decrypt", str(out_target)],
            check=True,
            capture_output=True,
            timeout=30,
        )
        recovered = json.loads(dec.stdout.decode("utf-8"))
        self.assertEqual(recovered["plan_id"], "PLAN-010")
        self.assertIn("sessions", recovered)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
