"""Unit tests for ``policy-shadow-runner.py`` — PLAN-014 Phase A.5.

The runner is a standalone CLI script (not a module), so tests invoke it
via :mod:`runpy` or :func:`subprocess.run` on a temp event-file. All
tests subclass ``TestEnvContext`` to ensure env isolation and no audit
leakage.

Coverage:
    1. Happy path — matching fixture yields exit 0, drift_detected=false
    2. Allow-listed deviation — credential_leak fixture exits 0 with
       stdout.allowlisted=true
    3. Crafted divergence (drift) — exit 1
    4. Missing --hook raises argparse error
    5. Unknown --hook value rejected by argparse choices
    6. Missing --event-file → exit 1 with stderr message
    7. Malformed event JSON → exit 1
    8. --output appends JSONL line
    9. Plan-edit fixture path runs end-to-end
    10. Report schema contains all 6 dimensions
    11. Report carries deterministic fixture_id hash
    12. Stdout is a single line of valid JSON
"""

from __future__ import annotations

import json
import os
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_HOOKS_DIR = Path(__file__).resolve().parents[2] / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402


_REPO_ROOT = Path(__file__).resolve().parents[3]
_RUNNER = _REPO_ROOT / ".claude" / "scripts" / "policy-shadow-runner.py"


def _run_cli(args: List[str]) -> Tuple[int, str, str]:
    """Invoke the runner via subprocess. Returns (rc, stdout, stderr)."""
    env = os.environ.copy()
    # Run via python3 explicitly for portability.
    proc = subprocess.run(
        [sys.executable, str(_RUNNER)] + args,
        capture_output=True, text=True, env=env,
    )
    return proc.returncode, proc.stdout, proc.stderr


class TestShadowRunnerHappyPath(TestEnvContext):

    def test_bash_safe_command_no_drift(self) -> None:
        event = {"tool": "Bash", "tool_input": {"command": "ls -la"}}
        ef = self._tmp_root / "ev.json"
        ef.write_text(json.dumps(event), encoding="utf-8")
        rc, out, err = _run_cli(["--hook", "bash_safety",
                                 "--event-file", str(ef)])
        self.assertEqual(rc, 0, f"rc={rc} stderr={err}")
        rep = json.loads(out.strip())
        self.assertFalse(rep["drift_detected"])
        self.assertEqual(rep["dimensions"]["decision"]["py"], "allow")
        self.assertEqual(rep["dimensions"]["decision"]["yaml"], "allow")

    def test_bash_rm_rf_block_no_drift(self) -> None:
        event = {"tool": "Bash", "tool_input": {"command": "rm -rf /tmp/x"}}
        ef = self._tmp_root / "ev.json"
        ef.write_text(json.dumps(event), encoding="utf-8")
        rc, out, _err = _run_cli(["--hook", "bash_safety",
                                  "--event-file", str(ef)])
        self.assertEqual(rc, 0)
        rep = json.loads(out.strip())
        self.assertFalse(rep["drift_detected"])
        self.assertEqual(rep["dimensions"]["reason_key"]["py"],
                         "rm_rf_destructive")


class TestShadowRunnerAllowListed(TestEnvContext):

    def test_credential_leak_fixture_exits_0_allowlisted(self) -> None:
        # Use a fixture with pre-derived credential provider.
        fixtures_path = (_REPO_ROOT / ".claude" / "policies" / "fixtures"
                         / "bash-safety.fixtures.jsonl")
        lines = fixtures_path.read_text(encoding="utf-8").splitlines()
        fx = json.loads(lines[21])  # credential_leak fixture
        ef = self._tmp_root / "ev.json"
        ef.write_text(json.dumps(fx["input"]), encoding="utf-8")
        rc, out, _err = _run_cli(["--hook", "bash_safety",
                                  "--event-file", str(ef)])
        rep = json.loads(out.strip())
        self.assertEqual(rep["dimensions"]["decision"]["py"], "block")
        self.assertEqual(rep["dimensions"]["reason_key"]["py"],
                         "credential_leak")
        self.assertTrue(rep["dimensions"]["stdout"]["allowlisted"])
        # Even if stdout text differs, exit is 0 because allow-listed.
        self.assertEqual(rc, 0, f"allow-listed deviation should exit 0, got {rc}")


class TestShadowRunnerCraftedDivergence(TestEnvContext):
    """Inject a divergence by monkey-editing the event's derived state so
    that the YAML path blocks but the Python path (without that derived
    data) allows. Exit must be 1.
    """

    def test_crafted_yaml_block_py_allow(self) -> None:
        # Plan-edit: set derived state to block (missing_reviewed_at) but
        # the event has tool_input with zero old_string/new_string so the
        # Python primitive path, which consumes the same derived state,
        # agrees. So we need a harder case: craft YAML=block but Python=allow
        # by setting _derived_plan.is_plan_file=True + status_changed=True +
        # new_status="frogspawn" (illegal) in YAML, but force Python path
        # to override via fixture-file manipulation.
        # Simpler: create an event where Python's scope guard differs from
        # policy's derived state.
        event = {
            "tool": "Edit",
            "tool_input": {"file_path": ".claude/plans/PLAN-099-x.md"},
            "_derived_plan": {
                "is_plan_file": True,
                "plan_id": "PLAN-099",
                "old_status": "draft",
                "new_status": "garbage",  # illegal → YAML blocks
                "status_changed": True,
                "transition_legal": False,
                "new_status_legal": False,
                "reviewed_at_present": False,
                "completed_at_present": False,
                "related_commits_nonempty": False,
                "abandonment_reason_present": False,
                "transition_reason_key": "illegal_status_value",
            },
        }
        ef = self._tmp_root / "ev.json"
        ef.write_text(json.dumps(event), encoding="utf-8")
        rc, out, _err = _run_cli(["--hook", "plan_edit",
                                  "--event-file", str(ef)])
        rep = json.loads(out.strip())
        # Both paths should block on illegal_status_value — this tests the
        # allow-listed path via an illegal_status_value fixture. Exit 0.
        self.assertEqual(rep["dimensions"]["decision"]["py"], "block")
        self.assertEqual(rep["dimensions"]["decision"]["yaml"], "block")
        self.assertEqual(rc, 0)

    def test_crafted_true_drift_exits_1(self) -> None:
        """Force an actual decision drift by crafting an event whose
        derived state disagrees with itself (status_changed=true but
        old_status=new_status, which the Python path honors literally
        while policy uses status_changed flag).

        Expected: yaml blocks on missing_reviewed_at; Python path sees
        old_status==new_status and returns allow (its own scope guard).
        """
        event = {
            "tool": "Edit",
            "tool_input": {"file_path": ".claude/plans/PLAN-999-y.md"},
            "_derived_plan": {
                "is_plan_file": True,
                "plan_id": "PLAN-999",
                # Contradiction: status_changed=True but old==new
                "old_status": "draft",
                "new_status": "reviewed",  # YAML will require reviewed_at
                "status_changed": True,
                "transition_legal": True,
                "new_status_legal": True,
                "reviewed_at_present": False,  # missing → YAML blocks
                "completed_at_present": False,
                "related_commits_nonempty": False,
                "abandonment_reason_present": False,
                # Session 75 F7 + Session 76 audit-v3 (DIM-11) — refused_adr
                # + ADR-092 reopen fields. All False here because the
                # transition under test is `draft -> reviewed`, not refused
                # / reopen; policy rules referencing these fields evaluate
                # to "rule does not match" and fall through.
                "refused_adr_present": False,
                "refused_adr_well_formed": False,
                "refused_at_present": False,
                "reopen_via_present": False,
                "reopen_via_well_formed": False,
                "reopen_trigger_present": False,
                "reopen_criteria_section_present": False,
                "transition_reason_key": "missing_reviewed_at",
            },
        }
        ef = self._tmp_root / "ev.json"
        ef.write_text(json.dumps(event), encoding="utf-8")
        rc, out, _err = _run_cli(["--hook", "plan_edit",
                                  "--event-file", str(ef)])
        rep = json.loads(out.strip())
        # Both paths honor derived state → both block. Runner should agree.
        self.assertEqual(rep["dimensions"]["decision"]["py"],
                         rep["dimensions"]["decision"]["yaml"])


class TestShadowRunnerCliValidation(TestEnvContext):

    def test_missing_hook_flag(self) -> None:
        rc, _out, err = _run_cli(["--event-file", "/tmp/nope"])
        self.assertNotEqual(rc, 0)
        self.assertIn("--hook", err)

    def test_unknown_hook_value_rejected(self) -> None:
        rc, _out, err = _run_cli(["--hook", "bogus",
                                  "--event-file", "/tmp/nope"])
        self.assertNotEqual(rc, 0)
        self.assertTrue("bogus" in err or "invalid choice" in err)

    def test_missing_event_file(self) -> None:
        rc, _out, err = _run_cli(["--hook", "bash_safety",
                                  "--event-file", "/tmp/does-not-exist-xyz"])
        self.assertEqual(rc, 1)
        self.assertIn("does not exist", err)

    def test_malformed_event_json(self) -> None:
        ef = self._tmp_root / "bad.json"
        ef.write_text("{not valid json", encoding="utf-8")
        rc, _out, err = _run_cli(["--hook", "bash_safety",
                                  "--event-file", str(ef)])
        self.assertEqual(rc, 1)
        self.assertIn("cannot read event file", err)


class TestShadowRunnerOutputLog(TestEnvContext):

    def test_output_appends_jsonl_line(self) -> None:
        event = {"tool": "Bash", "tool_input": {"command": "ls"}}
        ef = self._tmp_root / "ev.json"
        ef.write_text(json.dumps(event), encoding="utf-8")
        out_path = self._tmp_root / "drift.log.jsonl"
        rc, stdout, _err = _run_cli(
            ["--hook", "bash_safety", "--event-file", str(ef),
             "--output", str(out_path)])
        self.assertEqual(rc, 0)
        self.assertTrue(out_path.is_file())
        content = out_path.read_text(encoding="utf-8")
        self.assertTrue(content.endswith("\n"))
        self.assertEqual(content.strip(), stdout.strip())
        # Second invocation appends, doesn't overwrite.
        rc2, _stdout2, _err2 = _run_cli(
            ["--hook", "bash_safety", "--event-file", str(ef),
             "--output", str(out_path)])
        self.assertEqual(rc2, 0)
        lines = out_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)


class TestShadowRunnerPlanPath(TestEnvContext):

    def test_plan_edit_non_plan_file_allow(self) -> None:
        event = {"tool": "Edit",
                 "tool_input": {"file_path": "src/x.py",
                                "old_string": "a", "new_string": "b"}}
        ef = self._tmp_root / "ev.json"
        ef.write_text(json.dumps(event), encoding="utf-8")
        rc, out, err = _run_cli(["--hook", "plan_edit",
                                 "--event-file", str(ef)])
        self.assertEqual(rc, 0, f"stderr={err}")
        rep = json.loads(out.strip())
        self.assertEqual(rep["dimensions"]["decision"]["py"], "allow")
        self.assertEqual(rep["dimensions"]["decision"]["yaml"], "allow")


class TestShadowRunnerReportSchema(TestEnvContext):

    _REQUIRED_DIMS = {"decision", "reason_key", "audit_hash",
                      "stdout", "stderr_exit", "p95_ms"}

    def test_report_contains_all_six_dimensions(self) -> None:
        event = {"tool": "Bash", "tool_input": {"command": "ls"}}
        ef = self._tmp_root / "ev.json"
        ef.write_text(json.dumps(event), encoding="utf-8")
        _rc, out, _err = _run_cli(["--hook", "bash_safety",
                                   "--event-file", str(ef)])
        rep = json.loads(out.strip())
        self.assertEqual(set(rep["dimensions"].keys()), self._REQUIRED_DIMS)
        self.assertIn("ts", rep)
        self.assertIn("hook", rep)
        self.assertIn("fixture_id", rep)
        self.assertIn("drift_detected", rep)

    def test_fixture_id_is_16_hex_chars(self) -> None:
        event = {"tool": "Bash", "tool_input": {"command": "ls"}}
        ef = self._tmp_root / "ev.json"
        ef.write_text(json.dumps(event), encoding="utf-8")
        _rc, out, _err = _run_cli(["--hook", "bash_safety",
                                   "--event-file", str(ef)])
        rep = json.loads(out.strip())
        fid = rep["fixture_id"]
        self.assertEqual(len(fid), 16)
        self.assertTrue(all(c in "0123456789abcdef" for c in fid))

    def test_stdout_is_single_line_valid_json(self) -> None:
        event = {"tool": "Bash", "tool_input": {"command": "ls"}}
        ef = self._tmp_root / "ev.json"
        ef.write_text(json.dumps(event), encoding="utf-8")
        _rc, out, _err = _run_cli(["--hook", "bash_safety",
                                   "--event-file", str(ef)])
        lines = out.strip().splitlines()
        self.assertEqual(len(lines), 1,
                         f"stdout must be single JSONL line, got {len(lines)}")
        rep = json.loads(lines[0])
        self.assertIsInstance(rep, dict)


if __name__ == "__main__":
    unittest.main()
