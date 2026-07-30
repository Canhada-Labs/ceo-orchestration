"""Unit tests for `check_directory_added.py` (PLAN-163 T3.1, thread B1).

Covers the DirectoryAdded observer-WRITER: a notification-only,
post-facto hook that records session-added workspace roots into
`.claude/state/session-roots.json` for the PreToolUse write-guard
consumers.

STAGED with the PLAN-163 main-pack: green only once the pack is applied
(the hook module must exist at `.claude/hooks/check_directory_added.py`).

Covered behaviors:
- valid shape -> registry write (schema 1, session-scoped, canonical dir)
- re-add of the same directory dedups (refresh in place)
- prune-on-write TTL policy (dead transcript / >48h stale / live kept)
- unparseable `directory` field -> entry marked ``unparseable: true``
- kill-switch CEO_DIRECTORY_ADDED_GUARD=0 -> {} exit 0, no write
- infra failure (registry path unusable) -> breadcrumb + {} exit 0
- no-value-echo: audit fields are the CLOSED set with a hash prefix;
  the raw path never reaches the audit log
"""

from __future__ import annotations

import io
import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import check_directory_added as cda  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class DirectoryAddedHookTest(TestEnvContext):
    """Shared helpers: payload builder + main() stdin/stdout round-trip."""

    def setUp(self) -> None:
        super().setUp()
        self.registry_path = (
            self.project_dir / ".claude" / "state" / "session-roots.json"
        )
        self.added_dir = self.project_dir / "added-root"
        self.added_dir.mkdir(parents=True, exist_ok=True)
        self.transcript = self.home_dir / "transcript-current.jsonl"
        self.transcript.parent.mkdir(parents=True, exist_ok=True)
        self.transcript.write_text("{}\n", encoding="utf-8")

    def payload(self, **overrides: object) -> dict:
        base: dict = {
            "session_id": "sess-current",
            "transcript_path": str(self.transcript),
            "cwd": str(self.project_dir),
            "prompt_id": "p-1",
            "hook_event_name": "DirectoryAdded",
            "directory": str(self.added_dir),
            "source": "slash_command",
        }
        base.update(overrides)
        return base

    def run_main(self, stdin_text: str) -> "tuple[int, str, str]":
        stdin_orig, stdout_orig, stderr_orig = sys.stdin, sys.stdout, sys.stderr
        try:
            sys.stdin = io.StringIO(stdin_text)
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()
            rc = cda.main()
            out = sys.stdout.getvalue()
            err = sys.stderr.getvalue()
        finally:
            sys.stdin, sys.stdout, sys.stderr = stdin_orig, stdout_orig, stderr_orig
        return rc, out, err

    def run_main_payload(self, payload: dict) -> "tuple[int, str, str]":
        return self.run_main(json.dumps(payload))

    def read_registry(self) -> dict:
        return json.loads(self.registry_path.read_text(encoding="utf-8"))


class TestValidShapeWritesRegistry(DirectoryAddedHookTest):
    def test_valid_event_recorded(self) -> None:
        rc, out, _ = self.run_main_payload(self.payload())
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out.splitlines()[-1]), {})
        registry = self.read_registry()
        self.assertEqual(registry["schema"], 1)
        entry = registry["sessions"]["sess-current"]
        self.assertEqual(entry["transcript_path"], str(self.transcript))
        roots = entry["roots"]
        self.assertEqual(len(roots), 1)
        root = roots[0]
        self.assertEqual(root["directory"], os.path.realpath(str(self.added_dir)))
        self.assertEqual(root["source"], "slash_command")
        self.assertIn("ts", root)
        self.assertNotIn("unparseable", root)

    def test_re_add_same_directory_dedups(self) -> None:
        self.run_main_payload(self.payload())
        rc, _, _ = self.run_main_payload(
            self.payload(source="register_repo_root")
        )
        self.assertEqual(rc, 0)
        roots = self.read_registry()["sessions"]["sess-current"]["roots"]
        self.assertEqual(len(roots), 1)
        # Refresh-in-place: latest source wins.
        self.assertEqual(roots[0]["source"], "register_repo_root")

    def test_wrong_event_name_is_noop(self) -> None:
        rc, out, err = self.run_main_payload(
            self.payload(hook_event_name="Notification")
        )
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out.splitlines()[-1]), {})
        self.assertFalse(self.registry_path.exists())
        self.assertIn("unexpected hook_event_name", err)


class TestTtlPruneOnWrite(DirectoryAddedHookTest):
    def _seed(self, sessions: dict) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry_path.write_text(
            json.dumps({"schema": 1, "sessions": sessions}), encoding="utf-8"
        )

    def test_prunes_dead_transcript_and_stale_keeps_live(self) -> None:
        now = datetime.now(timezone.utc)
        fresh_ts = _iso(now - timedelta(minutes=5))
        stale_ts = _iso(now - timedelta(hours=72))
        live_transcript = self.home_dir / "transcript-live.jsonl"
        live_transcript.write_text("{}\n", encoding="utf-8")
        self._seed(
            {
                "sess-dead-transcript": {
                    "transcript_path": str(self.home_dir / "gone.jsonl"),
                    "roots": [
                        {"directory": "/x", "source": "slash_command", "ts": fresh_ts}
                    ],
                },
                "sess-stale": {
                    "transcript_path": "",
                    "roots": [
                        {"directory": "/y", "source": "slash_command", "ts": stale_ts}
                    ],
                },
                "sess-corrupt-ts": {
                    "transcript_path": "",
                    "roots": [
                        {"directory": "/z", "source": "slash_command", "ts": "bogus"}
                    ],
                },
                "sess-live": {
                    "transcript_path": str(live_transcript),
                    "roots": [
                        {"directory": "/w", "source": "slash_command", "ts": fresh_ts}
                    ],
                },
            }
        )
        rc, _, _ = self.run_main_payload(self.payload())
        self.assertEqual(rc, 0)
        sessions = self.read_registry()["sessions"]
        self.assertNotIn("sess-dead-transcript", sessions)
        self.assertNotIn("sess-stale", sessions)
        self.assertNotIn("sess-corrupt-ts", sessions)
        self.assertIn("sess-live", sessions)
        self.assertIn("sess-current", sessions)

    def test_current_session_never_pruned(self) -> None:
        now = datetime.now(timezone.utc)
        stale_ts = _iso(now - timedelta(hours=100))
        self._seed(
            {
                "sess-current": {
                    "transcript_path": "",
                    "roots": [
                        {
                            "directory": "/old",
                            "source": "slash_command",
                            "ts": stale_ts,
                        }
                    ],
                }
            }
        )
        rc, _, _ = self.run_main_payload(self.payload())
        self.assertEqual(rc, 0)
        roots = self.read_registry()["sessions"]["sess-current"]["roots"]
        dirs = {r["directory"] for r in roots}
        self.assertIn("/old", dirs)
        self.assertIn(os.path.realpath(str(self.added_dir)), dirs)


class TestUnparseableDirectory(DirectoryAddedHookTest):
    def test_non_string_directory_marks_unparseable(self) -> None:
        rc, out, err = self.run_main_payload(self.payload(directory=123))
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out.splitlines()[-1]), {})
        roots = self.read_registry()["sessions"]["sess-current"]["roots"]
        self.assertEqual(len(roots), 1)
        self.assertTrue(roots[0]["unparseable"])
        self.assertIn("did not canonicalize", err)

    def test_empty_string_directory_marks_unparseable(self) -> None:
        rc, _, _ = self.run_main_payload(self.payload(directory=""))
        self.assertEqual(rc, 0)
        roots = self.read_registry()["sessions"]["sess-current"]["roots"]
        self.assertTrue(roots[0]["unparseable"])

    def test_relative_directory_not_laundered_marks_unparseable(self) -> None:
        # R2-M1 (MED): a RELATIVE directory must NOT be laundered by
        # os.path.realpath into a CWD-relative absolute path that then
        # masquerades as a trustworthy root. It is recorded unparseable
        # so the consumer write-guard denies it fail-closed (M2).
        rel = "../evil"
        rc, out, err = self.run_main_payload(self.payload(directory=rel))
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out.splitlines()[-1]), {})
        roots = self.read_registry()["sessions"]["sess-current"]["roots"]
        self.assertEqual(len(roots), 1)
        self.assertTrue(roots[0]["unparseable"])
        # The stored directory is the RAW relative value, NOT an absolute
        # realpath resolution against the process CWD.
        self.assertEqual(roots[0]["directory"], rel)
        self.assertFalse(os.path.isabs(roots[0]["directory"]))
        self.assertNotEqual(roots[0]["directory"], os.path.realpath(rel))
        self.assertIn("did not canonicalize", err)

    def test_dot_relative_directory_marks_unparseable(self) -> None:
        rc, _, _ = self.run_main_payload(self.payload(directory="evil/sub"))
        self.assertEqual(rc, 0)
        roots = self.read_registry()["sessions"]["sess-current"]["roots"]
        self.assertTrue(roots[0]["unparseable"])
        self.assertEqual(roots[0]["directory"], "evil/sub")

    def test_absolute_directory_still_canonicalizes(self) -> None:
        # The absolute-path happy path is preserved: an absolute directory
        # canonicalizes normally and is NOT marked unparseable.
        rc, _, _ = self.run_main_payload(self.payload())
        self.assertEqual(rc, 0)
        root = self.read_registry()["sessions"]["sess-current"]["roots"][0]
        self.assertNotIn("unparseable", root)
        self.assertEqual(root["directory"], os.path.realpath(str(self.added_dir)))
        self.assertTrue(os.path.isabs(root["directory"]))

    def test_missing_directory_field_drops_event(self) -> None:
        payload = self.payload()
        del payload["directory"]
        rc, out, _ = self.run_main_payload(payload)
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out.splitlines()[-1]), {})
        self.assertFalse(self.registry_path.exists())


class TestKillSwitch(DirectoryAddedHookTest):
    def test_kill_switch_zero_disables_everything(self) -> None:
        with mock.patch.dict(os.environ, {"CEO_DIRECTORY_ADDED_GUARD": "0"}):
            rc, out, _ = self.run_main_payload(self.payload())
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out.splitlines()[-1]), {})
        self.assertFalse(self.registry_path.exists())

    def test_kill_switch_explicit_on_records(self) -> None:
        with mock.patch.dict(os.environ, {"CEO_DIRECTORY_ADDED_GUARD": "1"}):
            rc, _, _ = self.run_main_payload(self.payload())
        self.assertEqual(rc, 0)
        self.assertTrue(self.registry_path.exists())


class TestInfraFailOpen(DirectoryAddedHookTest):
    def test_registry_path_is_directory_fails_open(self) -> None:
        # A directory (with content) squatting the registry path makes
        # the atomic os.replace raise OSError — infra, not input.
        self.registry_path.mkdir(parents=True, exist_ok=True)
        (self.registry_path / "squatter").write_text("x", encoding="utf-8")
        rc, out, err = self.run_main_payload(self.payload())
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out.splitlines()[-1]), {})
        self.assertIn("fail-open", err)

    def test_stdin_garbage_fails_open_no_write(self) -> None:
        rc, out, err = self.run_main("this is {{{ not json")
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out.splitlines()[-1]), {})
        self.assertFalse(self.registry_path.exists())
        self.assertIn("parse error", err)

    def test_non_object_payload_fails_open(self) -> None:
        rc, out, _ = self.run_main(json.dumps(["not", "an", "object"]))
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out.splitlines()[-1]), {})
        self.assertFalse(self.registry_path.exists())

    def test_corrupt_registry_self_heals(self) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry_path.write_text("{corrupt json!!", encoding="utf-8")
        rc, _, err = self.run_main_payload(self.payload())
        self.assertEqual(rc, 0)
        self.assertIn("self-heal", err)
        registry = self.read_registry()
        self.assertEqual(registry["schema"], 1)
        self.assertIn("sess-current", registry["sessions"])


class TestNoValueEchoAudit(DirectoryAddedHookTest):
    def test_audit_fields_are_closed_set_with_hash_prefix(self) -> None:
        raw = str(self.added_dir)
        fields = cda._audit_fields(
            source="slash_command", directory_repr=raw, session_id="sess-current"
        )
        self.assertEqual(
            set(fields.keys()),
            {"source", "directory_hash_prefix", "session_id"},
        )
        import hashlib

        expected = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
        self.assertEqual(fields["directory_hash_prefix"], expected)
        self.assertEqual(len(fields["directory_hash_prefix"]), 12)
        # No field value carries the raw path.
        for value in fields.values():
            self.assertNotIn(raw, value)

    def test_typed_emitter_receives_closed_fields_only(self) -> None:
        from _lib import audit_emit_dispatch as dispatch

        captured: dict = {}

        def fake_emit(**kwargs: object) -> None:
            captured.update(kwargs)

        # B3-merge: patch the emitter name B3 actually registered (it is the
        # FIRST probe in the hook's fallback tuple). create=True keeps this
        # green pre-land too (the shim has no such attr until the pack
        # applies; the patched attr shadows PEP 562 __getattr__ either way).
        with mock.patch.object(
            dispatch, "emit_directory_added_recorded", fake_emit, create=True
        ):
            rc, _, _ = self.run_main_payload(self.payload())
        self.assertEqual(rc, 0)
        self.assertEqual(
            set(captured.keys()),
            {"source", "directory_hash_prefix", "session_id"},
        )
        raw_canonical = os.path.realpath(str(self.added_dir))
        for value in captured.values():
            self.assertNotIn(raw_canonical, str(value))

    def test_raw_path_never_reaches_audit_log(self) -> None:
        rc, _, _ = self.run_main_payload(self.payload())
        self.assertEqual(rc, 0)
        log = self.read_audit_log()
        self.assertNotIn(str(self.added_dir), log)
        self.assertNotIn(os.path.realpath(str(self.added_dir)), log)

    def test_missing_emitter_is_silent_noop(self) -> None:
        # hasattr on the dispatch shim raises->False for unregistered
        # names; the hook must not care. (B3 registers the real action.)
        rc, out, _ = self.run_main_payload(self.payload())
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out.splitlines()[-1]), {})
        self.assertTrue(self.registry_path.exists())


class TestConsumerDeniesRelativeUnparseableEntry(DirectoryAddedHookTest):
    """R2-M1 cross-check: the observer records a relative directory as
    unparseable, and the consumer write-guard denies external writes for
    that session fail-closed (M2). Without the fix the observer would have
    stored a laundered absolute path, the consumer's isabs test would pass,
    and the guard would silently mis-scope the boundary instead of denying.
    """

    def test_consumer_denies_after_relative_entry_recorded(self) -> None:
        # Observer records a relative directory (laundering suppressed).
        rc, _, _ = self.run_main_payload(self.payload(directory="../evil"))
        self.assertEqual(rc, 0)
        root = self.read_registry()["sessions"]["sess-current"]["roots"][0]
        self.assertTrue(root["unparseable"])

        import check_canonical_edit as cce

        external_target = "/nonexistent-external-r2m1/target.txt"
        reason = cce._session_roots_guard(
            [external_target],
            repo_root=self.project_dir,
            session_id="sess-current",
            env={},
        )
        self.assertIsNotNone(reason)
        self.assertIn("SESSION-ROOTS-WRITE-BLOCKED", reason)
        self.assertIn("session_root_unparseable", reason)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
