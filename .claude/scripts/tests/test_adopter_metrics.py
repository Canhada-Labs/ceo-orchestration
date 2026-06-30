"""Unit tests for adopter-metrics.py — PLAN-015 Phase 0.1.

Scripts-level tests follow the test_check_staleness.py pattern: a
module imported via importlib.util.spec_from_file_location (since the
file name has a hyphen), tempfile-based isolation per test, and
deterministic time via --now.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import stat
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# --- Dynamic import of the hyphenated script --------------------------------

_SCRIPT = Path(__file__).resolve().parent.parent / "adopter-metrics.py"
_spec = importlib.util.spec_from_file_location("adopter_metrics", _SCRIPT)
adopter_metrics = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(adopter_metrics)


# --- Test helpers -----------------------------------------------------------


_FIXED_NOW = "2026-04-17T12:00:00Z"


def _iso(days_ago: int, now_iso: str = _FIXED_NOW) -> str:
    """Return an ISO-8601 Z-suffixed timestamp `days_ago` days before now_iso."""
    now = datetime.fromisoformat(now_iso.replace("Z", "+00:00"))
    ts = now - timedelta(days=days_ago)
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_audit_log(path: Path, entries: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def _make_skill_tree(root: Path, names: List[str]) -> None:
    """Create SKILL.md files under root/.../<name>/SKILL.md."""
    root.mkdir(parents=True, exist_ok=True)
    for name in names:
        d = root / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(f"# {name}\n")


class _TempDirCase(unittest.TestCase):
    """Base class: each test gets a fresh tmp dir with a baseline skills
    dir + audit-log path pre-set."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="adopter-metrics-test-"))
        self.baseline_dir = self.tmp / "framework" / "skills"
        self.target_skills_dir = self.tmp / "target" / "skills"
        self.audit_log = self.tmp / "audit-log.jsonl"
        self.output_dir = self.tmp / "out"
        _make_skill_tree(
            self.baseline_dir,
            ["writing-tests", "api-design", "observability-and-ops"],
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run_cli(self, extra_args: List[str]) -> tuple:
        """Invoke main() with the given extra args; return (rc, stdout, stderr)."""
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        argv = [
            "--adopter-name",
            "testadopter",
            "--audit-log",
            str(self.audit_log),
            "--skills-baseline",
            str(self.baseline_dir),
            "--now",
            _FIXED_NOW,
        ] + extra_args
        with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(
            stderr_buf
        ):
            rc = adopter_metrics.main(argv)
        return rc, stdout_buf.getvalue(), stderr_buf.getvalue()


# --- Category 1: CLI argument parsing ---------------------------------------


class TestCLIArgs(_TempDirCase):
    def test_missing_adopter_name_exits_non_zero(self):
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(
            stderr_buf
        ):
            # Argparse calls sys.exit(2) on missing required; our main
            # catches SystemExit and maps to non-zero.
            rc = adopter_metrics.main(
                [
                    "--audit-log",
                    str(self.audit_log),
                    "--skills-baseline",
                    str(self.baseline_dir),
                ]
            )
        self.assertNotEqual(rc, 0)

    def test_bad_window_choice(self):
        _write_audit_log(self.audit_log, [])
        rc, _out, _err = self._run_cli(["--window", "99d"])
        self.assertNotEqual(rc, 0)

    def test_missing_audit_log_file_still_exit_0(self):
        # Absent file is valid (empty report). Exit 0.
        rc, out, _err = self._run_cli(["--window", "7d"])
        self.assertEqual(rc, 0)
        self.assertIn("Sessions | 0", out)

    def test_missing_skills_baseline_exits_1(self):
        _write_audit_log(self.audit_log, [])
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        argv = [
            "--adopter-name",
            "testadopter",
            "--audit-log",
            str(self.audit_log),
            "--skills-baseline",
            str(self.tmp / "does-not-exist"),
            "--now",
            _FIXED_NOW,
        ]
        with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(
            stderr_buf
        ):
            rc = adopter_metrics.main(argv)
        self.assertEqual(rc, 1)
        self.assertIn("skills-baseline", stderr_buf.getvalue())


# --- Category 2: Empty audit log --------------------------------------------


class TestEmptyLog(_TempDirCase):
    def test_absent_file_produces_zeroes(self):
        rc, out, _err = self._run_cli([])
        self.assertEqual(rc, 0)
        self.assertIn("Sessions | 0", out)
        self.assertIn("Spawns | 0", out)
        self.assertIn("N/A%", out)  # veto rate null → N/A

    def test_empty_file_produces_zeroes(self):
        self.audit_log.write_text("")
        rc, out, _err = self._run_cli([])
        self.assertEqual(rc, 0)
        self.assertIn("Sessions | 0", out)
        self.assertIn("Spawns | 0", out)


# --- Category 3: Window filtering -------------------------------------------


class TestWindowFiltering(_TempDirCase):
    def test_events_outside_7d_excluded(self):
        _write_audit_log(
            self.audit_log,
            [
                {"action": "agent_spawn", "ts": _iso(10), "session_id": "old"},
                {"action": "agent_spawn", "ts": _iso(3), "session_id": "recent"},
            ],
        )
        rc, out, _err = self._run_cli(["--window", "7d"])
        self.assertEqual(rc, 0)
        self.assertIn("Spawns | 1", out)

    def test_all_window_returns_everything(self):
        _write_audit_log(
            self.audit_log,
            [
                {"action": "agent_spawn", "ts": _iso(60), "session_id": "s1"},
                {"action": "agent_spawn", "ts": _iso(3), "session_id": "s2"},
            ],
        )
        rc, out, _err = self._run_cli(["--window", "all"])
        self.assertEqual(rc, 0)
        self.assertIn("Spawns | 2", out)

    def test_now_override_deterministic(self):
        # With --now set 2026-04-10, an event on 2026-04-05 is within 7d;
        # with --now set 2026-04-20, the same event is outside 7d.
        event = {"action": "agent_spawn", "ts": "2026-04-05T10:00:00Z", "session_id": "x"}
        _write_audit_log(self.audit_log, [event])
        stdout_near = io.StringIO()
        with contextlib.redirect_stdout(stdout_near):
            rc = adopter_metrics.main(
                [
                    "--adopter-name",
                    "t",
                    "--audit-log",
                    str(self.audit_log),
                    "--skills-baseline",
                    str(self.baseline_dir),
                    "--now",
                    "2026-04-10T10:00:00Z",
                ]
            )
        self.assertEqual(rc, 0)
        self.assertIn("Spawns | 1", stdout_near.getvalue())
        stdout_far = io.StringIO()
        with contextlib.redirect_stdout(stdout_far):
            rc2 = adopter_metrics.main(
                [
                    "--adopter-name",
                    "t",
                    "--audit-log",
                    str(self.audit_log),
                    "--skills-baseline",
                    str(self.baseline_dir),
                    "--now",
                    "2026-04-20T10:00:00Z",
                ]
            )
        self.assertEqual(rc2, 0)
        self.assertIn("Spawns | 0", stdout_far.getvalue())


# --- Category 4: Sessions count ---------------------------------------------


class TestSessions(_TempDirCase):
    def test_distinct_session_ids_counted(self):
        _write_audit_log(
            self.audit_log,
            [
                {"action": "agent_spawn", "ts": _iso(1), "session_id": "a"},
                {"action": "agent_spawn", "ts": _iso(1), "session_id": "a"},
                {"action": "agent_spawn", "ts": _iso(1), "session_id": "b"},
            ],
        )
        rc, out, _err = self._run_cli([])
        self.assertEqual(rc, 0)
        self.assertIn("Sessions | 2", out)

    def test_missing_session_id_bucketed_as_unknown(self):
        _write_audit_log(
            self.audit_log,
            [
                {"action": "agent_spawn", "ts": _iso(1), "session_id": "a"},
                {"action": "agent_spawn", "ts": _iso(1)},  # no session_id
                {"action": "agent_spawn", "ts": _iso(1)},  # no session_id
            ],
        )
        rc, out, _err = self._run_cli([])
        self.assertEqual(rc, 0)
        # 1 distinct + 1 "unknown" bucket = 2 sessions
        self.assertIn("Sessions | 2", out)


# --- Category 5: Spawns total -----------------------------------------------


class TestSpawns(_TempDirCase):
    def test_only_agent_spawn_counted(self):
        _write_audit_log(
            self.audit_log,
            [
                {"action": "agent_spawn", "ts": _iso(1), "session_id": "s"},
                {"action": "agent_spawn", "ts": _iso(1), "session_id": "s"},
                {"action": "plan_transition", "ts": _iso(1), "to_status": "done"},
            ],
        )
        rc, out, _err = self._run_cli([])
        self.assertEqual(rc, 0)
        self.assertIn("Spawns | 2", out)

    def test_other_actions_excluded(self):
        _write_audit_log(
            self.audit_log,
            [
                {"action": "benchmark_run", "ts": _iso(1), "session_id": "s"},
                {"action": "debate_event", "ts": _iso(1), "session_id": "s"},
            ],
        )
        rc, out, _err = self._run_cli([])
        self.assertEqual(rc, 0)
        self.assertIn("Spawns | 0", out)


# --- Category 6: Veto rate --------------------------------------------------


class TestVetoRate(_TempDirCase):
    def test_normal_ratio(self):
        # 1 veto + 3 spawns → 1 / (3+1) = 25%
        entries = [
            {"action": "agent_spawn", "ts": _iso(1), "session_id": "s"},
            {"action": "agent_spawn", "ts": _iso(1), "session_id": "s"},
            {"action": "agent_spawn", "ts": _iso(1), "session_id": "s"},
            {"action": "veto_triggered", "ts": _iso(1), "session_id": "s"},
        ]
        _write_audit_log(self.audit_log, entries)
        rc, out, _err = self._run_cli([])
        self.assertEqual(rc, 0)
        self.assertIn("25.0%", out)
        self.assertIn("(1 / 4)", out)

    def test_zero_denom_null_na(self):
        _write_audit_log(self.audit_log, [])
        rc, out, _err = self._run_cli([])
        self.assertEqual(rc, 0)
        self.assertIn("Veto rate | N/A%", out)

    def test_only_spawns_no_vetoes_zero_pct(self):
        _write_audit_log(
            self.audit_log,
            [{"action": "agent_spawn", "ts": _iso(1), "session_id": "s"}],
        )
        rc, out, _err = self._run_cli([])
        self.assertEqual(rc, 0)
        self.assertIn("Veto rate | 0.0%", out)


# --- Category 7: Task completion --------------------------------------------


class TestTaskCompletion(_TempDirCase):
    def test_done_counted(self):
        _write_audit_log(
            self.audit_log,
            [
                {"action": "plan_transition", "ts": _iso(1), "to_status": "done"},
                {"action": "plan_transition", "ts": _iso(1), "to_status": "done"},
            ],
        )
        rc, out, _err = self._run_cli([])
        self.assertEqual(rc, 0)
        self.assertIn("Task completion | 100.0%", out)

    def test_abandoned_counted(self):
        _write_audit_log(
            self.audit_log,
            [
                {"action": "plan_transition", "ts": _iso(1), "to_status": "done"},
                {"action": "plan_transition", "ts": _iso(1), "to_status": "abandoned"},
            ],
        )
        rc, out, _err = self._run_cli([])
        self.assertEqual(rc, 0)
        self.assertIn("Task completion | 50.0%", out)

    def test_other_statuses_ignored(self):
        # Only reviewed/executing → denominator 0 → N/A
        _write_audit_log(
            self.audit_log,
            [
                {"action": "plan_transition", "ts": _iso(1), "to_status": "reviewed"},
                {"action": "plan_transition", "ts": _iso(1), "to_status": "executing"},
            ],
        )
        rc, out, _err = self._run_cli([])
        self.assertEqual(rc, 0)
        self.assertIn("Task completion | N/A%", out)


# --- Category 8: Tokens actual vs predicted ---------------------------------


class TestTokens(_TempDirCase):
    def test_actual_aggregated_tokens_total(self):
        _write_audit_log(
            self.audit_log,
            [
                {"action": "agent_spawn", "ts": _iso(1), "tokens_total": 5000, "session_id": "s"},
                {"action": "agent_spawn", "ts": _iso(1), "tokens_total": 7000, "session_id": "s"},
            ],
        )
        rc, out, _err = self._run_cli([])
        self.assertEqual(rc, 0)
        # actual = 12000, predicted = N/A (no prediction_queried event)
        self.assertIn("12000 / N/A", out)

    def test_predicted_from_bucket_midpoint(self):
        # bucket "100k-140k" → midpoint = (100+140)/2 * 1000 = 120000
        _write_audit_log(
            self.audit_log,
            [
                {
                    "action": "agent_spawn",
                    "ts": _iso(1),
                    "tokens_total": 100000,
                    "session_id": "s",
                },
                {
                    "action": "prediction_queried",
                    "ts": _iso(1),
                    "bucket_range": "100k-140k",
                    "confidence": "medium",
                    "plan_id": "PLAN-099",
                },
            ],
        )
        rc, out, _err = self._run_cli([])
        self.assertEqual(rc, 0)
        self.assertIn("100000 / 120000", out)

    def test_no_prediction_ratio_na(self):
        _write_audit_log(
            self.audit_log,
            [
                {"action": "agent_spawn", "ts": _iso(1), "tokens_total": 1000, "session_id": "s"},
            ],
        )
        rc, out, _err = self._run_cli([])
        self.assertEqual(rc, 0)
        # Ratio null because no prediction_queried
        self.assertIn("1000 / N/A (N/A)", out)


# --- Category 9: Custom skills ----------------------------------------------


class TestCustomSkills(_TempDirCase):
    def test_target_only_skills_counted(self):
        _make_skill_tree(self.target_skills_dir, ["custom-one", "custom-two"])
        _write_audit_log(self.audit_log, [])
        rc, out, _err = self._run_cli(
            ["--target-skills-dir", str(self.target_skills_dir)]
        )
        self.assertEqual(rc, 0)
        self.assertIn("Custom skills | 2", out)
        self.assertIn("custom-one", out)
        self.assertIn("custom-two", out)

    def test_same_name_as_baseline_not_counted(self):
        _make_skill_tree(self.target_skills_dir, ["writing-tests", "custom-only"])
        _write_audit_log(self.audit_log, [])
        rc, out, _err = self._run_cli(
            ["--target-skills-dir", str(self.target_skills_dir)]
        )
        self.assertEqual(rc, 0)
        # writing-tests is baseline → excluded; only custom-only counts
        self.assertIn("Custom skills | 1", out)
        self.assertIn("custom-only", out)

    def test_nested_subdirs_walked(self):
        # Baseline with domains/fintech/skills/<skill>/SKILL.md
        nested_baseline = self.tmp / "nested-baseline"
        nested_fintech = nested_baseline / "domains" / "fintech" / "skills"
        _make_skill_tree(
            nested_fintech,
            ["trading-execution", "financial-display"],
        )
        (nested_baseline / "core" / "writing-tests").mkdir(parents=True)
        (
            nested_baseline / "core" / "writing-tests" / "SKILL.md"
        ).write_text("# writing-tests")
        _make_skill_tree(
            self.target_skills_dir,
            ["trading-execution", "adopter-unique"],
        )
        _write_audit_log(self.audit_log, [])
        stdout_buf = io.StringIO()
        with contextlib.redirect_stdout(stdout_buf):
            rc = adopter_metrics.main(
                [
                    "--adopter-name",
                    "t",
                    "--audit-log",
                    str(self.audit_log),
                    "--skills-baseline",
                    str(nested_baseline),
                    "--target-skills-dir",
                    str(self.target_skills_dir),
                    "--now",
                    _FIXED_NOW,
                ]
            )
        self.assertEqual(rc, 0)
        out = stdout_buf.getvalue()
        # trading-execution IS in baseline (nested); only adopter-unique remains
        self.assertIn("Custom skills | 1", out)
        self.assertIn("adopter-unique", out)


# --- Category 10: ADRs activated --------------------------------------------


class TestADRs(_TempDirCase):
    def test_adr_in_desc_preview_counted(self):
        _write_audit_log(
            self.audit_log,
            [
                {
                    "action": "agent_spawn",
                    "ts": _iso(1),
                    "session_id": "s",
                    "desc_preview": "applying ADR-045 policy rules",
                },
            ],
        )
        rc, out, _err = self._run_cli([])
        self.assertEqual(rc, 0)
        self.assertIn("ADRs activated | 1 distinct / 1 mentions", out)
        self.assertIn("- ADR-045", out)

    def test_same_adr_n_times_counted_as_1_distinct_n_mentions(self):
        _write_audit_log(
            self.audit_log,
            [
                {
                    "action": "agent_spawn",
                    "ts": _iso(1),
                    "session_id": "s",
                    "desc_preview": "ADR-045 ADR-045 both fire",
                },
                {
                    "action": "veto_triggered",
                    "ts": _iso(1),
                    "session_id": "s",
                    "reason_preview": "violation of ADR-045 constraint",
                },
            ],
        )
        rc, out, _err = self._run_cli([])
        self.assertEqual(rc, 0)
        self.assertIn("1 distinct / 3 mentions", out)

    def test_adr_regex_boundary(self):
        # ADR-9999 (4 digits) and ADR-12 (2 digits) must NOT match.
        # ADR-045 and ADR-023 (exactly 3 digits) MUST match.
        _write_audit_log(
            self.audit_log,
            [
                {
                    "action": "agent_spawn",
                    "ts": _iso(1),
                    "session_id": "s",
                    "desc_preview": "ADR-9999 wrong / ADR-12 wrong / ADR-045 right / ADR-023 right",
                },
            ],
        )
        rc, out, _err = self._run_cli([])
        self.assertEqual(rc, 0)
        self.assertIn("2 distinct / 2 mentions", out)
        self.assertIn("- ADR-023", out)
        self.assertIn("- ADR-045", out)
        self.assertNotIn("ADR-9999", out.split("## Notes")[0])


# --- Category 11: Markdown output -------------------------------------------


class TestMarkdownOutput(_TempDirCase):
    def test_output_written_to_path(self):
        _write_audit_log(self.audit_log, [])
        out_path = self.output_dir / "week-1.md"
        rc, _out, _err = self._run_cli(["--output", str(out_path)])
        self.assertEqual(rc, 0)
        self.assertTrue(out_path.is_file())
        content = out_path.read_text(encoding="utf-8")
        self.assertIn("# Adopter metrics", content)
        self.assertIn("testadopter", content)

    def test_parent_dir_auto_created(self):
        _write_audit_log(self.audit_log, [])
        deep = self.tmp / "a" / "b" / "c" / "report.md"
        rc, _out, _err = self._run_cli(["--output", str(deep)])
        self.assertEqual(rc, 0)
        self.assertTrue(deep.is_file())


# --- Category 12: JSON output -----------------------------------------------


class TestJSONOutput(_TempDirCase):
    def test_json_emits_valid_json(self):
        _write_audit_log(
            self.audit_log,
            [
                {"action": "agent_spawn", "ts": _iso(1), "session_id": "s"},
            ],
        )
        rc, out, _err = self._run_cli(["--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertEqual(payload["adopter_name"], "testadopter")
        self.assertEqual(payload["metrics"]["spawns_total"], 1)
        self.assertEqual(payload["metrics"]["sessions_count"], 1)


# --- Category 13: Malformed audit-log tolerance -----------------------------


class TestMalformedLog(_TempDirCase):
    def test_bad_json_lines_skipped_with_stderr_warning(self):
        # Mix valid and invalid lines.
        good = {"action": "agent_spawn", "ts": _iso(1), "session_id": "s"}
        self.audit_log.parent.mkdir(parents=True, exist_ok=True)
        with open(self.audit_log, "w", encoding="utf-8") as f:
            f.write(json.dumps(good) + "\n")
            f.write("{ this is not json\n")
            f.write(json.dumps(good) + "\n")
        rc, out, err = self._run_cli([])
        self.assertEqual(rc, 0)
        self.assertIn("Spawns | 2", out)
        self.assertIn("skipping malformed JSONL", err)

    def test_non_dict_entries_ignored(self):
        self.audit_log.parent.mkdir(parents=True, exist_ok=True)
        with open(self.audit_log, "w", encoding="utf-8") as f:
            f.write(json.dumps([1, 2, 3]) + "\n")  # list, not dict
            f.write(json.dumps("string") + "\n")  # str, not dict
            f.write(
                json.dumps(
                    {"action": "agent_spawn", "ts": _iso(1), "session_id": "s"}
                )
                + "\n"
            )
        rc, out, _err = self._run_cli([])
        self.assertEqual(rc, 0)
        self.assertIn("Spawns | 1", out)


# --- Category 14: Edge cases ------------------------------------------------


class TestEdgeCases(_TempDirCase):
    def test_event_exactly_at_window_boundary_included(self):
        # 7d window; event exactly 7 days ago → included (inclusive lower)
        exact = {
            "action": "agent_spawn",
            "ts": _iso(7),
            "session_id": "boundary",
        }
        _write_audit_log(self.audit_log, [exact])
        rc, out, _err = self._run_cli(["--window", "7d"])
        self.assertEqual(rc, 0)
        self.assertIn("Spawns | 1", out)

    def test_future_dated_event_excluded(self):
        # Event dated 3 days AFTER now. PLAN-025 F-scripts-001 — future-
        # dated events are malformed (real events have past timestamps);
        # they are now EXCLUDED from all windows (previous behaviour was
        # clamp-to-end which caused double-counting across windows).
        now_dt = datetime.fromisoformat(_FIXED_NOW.replace("Z", "+00:00"))
        future_ts = (now_dt + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
        _write_audit_log(
            self.audit_log,
            [
                {"action": "agent_spawn", "ts": future_ts, "session_id": "futuro"},
            ],
        )
        rc, out, _err = self._run_cli(["--window", "7d"])
        self.assertEqual(rc, 0)
        # Future-dated event is EXCLUDED (no longer inflates counts)
        self.assertIn("Spawns | 0", out)

    def test_14d_window_picks_up_10d_events(self):
        _write_audit_log(
            self.audit_log,
            [
                {"action": "agent_spawn", "ts": _iso(10), "session_id": "s"},
            ],
        )
        rc, out, _err = self._run_cli(["--window", "14d"])
        self.assertEqual(rc, 0)
        self.assertIn("Spawns | 1", out)


# --- Category 15: Bucket midpoint parser (unit tests on helper) --------------


class TestBucketMidpoint(unittest.TestCase):
    def test_valid_bucket(self):
        self.assertEqual(adopter_metrics._bucket_midpoint("100k-140k"), 120000)

    def test_unknown_bucket_is_none(self):
        self.assertIsNone(adopter_metrics._bucket_midpoint("unknown"))

    def test_malformed_bucket_is_none(self):
        self.assertIsNone(adopter_metrics._bucket_midpoint("garbage"))

    def test_inverted_bounds_is_none(self):
        self.assertIsNone(adopter_metrics._bucket_midpoint("200k-100k"))


# --- Category 16: ISO parser ------------------------------------------------


class TestISOParser(unittest.TestCase):
    def test_z_suffix_parses(self):
        dt = adopter_metrics._parse_iso("2026-04-17T12:00:00Z")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.tzinfo, timezone.utc)

    def test_explicit_offset(self):
        dt = adopter_metrics._parse_iso("2026-04-17T12:00:00+00:00")
        self.assertIsNotNone(dt)

    def test_malformed_returns_none(self):
        self.assertIsNone(adopter_metrics._parse_iso("garbage"))

    def test_empty_returns_none(self):
        self.assertIsNone(adopter_metrics._parse_iso(""))


if __name__ == "__main__":
    unittest.main()
