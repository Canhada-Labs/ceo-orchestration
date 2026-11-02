"""GuardFall disabled-rail audit evidence, observed at the JSONL sink."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest import mock

from _subprocess_helpers import run_in_process_group
from _lib import audit_emit, bash_indirect_telemetry
from _lib.testing import TestEnvContext


class TestBashIndirectTelemetry(TestEnvContext):
    def _events(self):
        return [
            json.loads(row)
            for row in self.read_audit_log().splitlines()
            if row.strip()
        ]

    def test_real_payload_has_closed_names_without_env_values(self):
        with mock.patch.dict(os.environ, {"CEO_BASH_INDIRECT_GUARD": "0"}):
            bash_indirect_telemetry.disabled_once("CEO_BASH_INDIRECT_GUARD", "sid-1")

        events = self._events()
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["action"], "learning_rail_disabled")
        self.assertEqual(event["rail"], "bash_indirect")
        self.assertEqual(event["switch"], "CEO_BASH_INDIRECT_GUARD")
        self.assertEqual(event["hook"], "check_bash_safety")
        self.assertEqual(event["session_id"], "sid-1")
        self.assertEqual(event["event_schema"], "v2")
        self.assertNotIn("value", event)
        self.assertNotIn("command", event)
        self.assertNotIn("env_value", event)
        self.assertNotIn('"CEO_BASH_INDIRECT_GUARD": "0"', self.read_audit_log())

    def test_dedupe_across_processes_and_new_session(self):
        switch = "CEO_BASH_INDIRECT_GUARD"
        bash_indirect_telemetry.disabled_once(switch, "same-session")
        hooks_dir = str(Path(__file__).resolve().parents[1])
        script = (
            "import sys; sys.path.insert(0, sys.argv[1]); "
            "from _lib import bash_indirect_telemetry as t; "
            "t.disabled_once('CEO_BASH_INDIRECT_GUARD', 'same-session')"
        )
        result = run_in_process_group(
            [sys.executable, "-c", script, hooks_dir],
            env=os.environ.copy(), capture_output=True, text=True,
            check=False, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        bash_indirect_telemetry.disabled_once(switch, "same-session")
        self.assertEqual(len(self._events()), 1)

        bash_indirect_telemetry.disabled_once(switch, "new-session")
        self.assertEqual(len(self._events()), 2)
        self.assertEqual(
            {event["session_id"] for event in self._events()},
            {"same-session", "new-session"},
        )

    def test_two_switches_and_exact_schema_enums(self):
        switches = {
            "CEO_BASH_INDIRECT_GUARD",
            "CEO_BASH_INDIRECT_HEURISTICS",
        }
        self.assertEqual(switches, bash_indirect_telemetry._SWITCHES)
        self.assertIn("bash_indirect", audit_emit._LEARNING_RAIL_ENUM)
        self.assertTrue(switches <= audit_emit._LEARNING_SWITCH_ENUM)
        for switch in sorted(switches):
            bash_indirect_telemetry.disabled_once(switch, "same-session")

        events = self._events()
        self.assertEqual(len(events), 2)
        self.assertEqual({e["switch"] for e in events}, switches)
        self.assertEqual({e["rail"] for e in events}, {"bash_indirect"})

    def test_unknown_switch_is_silent_and_creates_no_marker(self):
        bash_indirect_telemetry.disabled_once("CEO_BASH_INDIRECT_GUARD_EVIL", "sid")
        bash_indirect_telemetry.disabled_once("../CEO_BASH_INDIRECT_GUARD", "sid")
        self.assertEqual(self._events(), [])
        self.assertFalse((self.audit_dir / "bash-indirect-disabled").exists())

    def test_bad_storage_is_fail_open_and_does_not_emit(self):
        bad_parent = self.audit_dir / "not-a-directory"
        bad_parent.write_text("x", encoding="utf-8")
        with mock.patch.object(audit_emit, "_log_family_dir", return_value=bad_parent):
            result = bash_indirect_telemetry.disabled_once(
                "CEO_BASH_INDIRECT_GUARD", "sid-bad"
            )
        self.assertIsNone(result)
        self.assertEqual(self._events(), [])

    def test_missing_session_id_is_silent(self):
        with mock.patch.dict(os.environ, {"CLAUDE_SESSION_ID": ""}):
            bash_indirect_telemetry.disabled_once("CEO_BASH_INDIRECT_GUARD")
        self.assertEqual(self._events(), [])
        self.assertFalse((self.audit_dir / "bash-indirect-disabled").exists())
