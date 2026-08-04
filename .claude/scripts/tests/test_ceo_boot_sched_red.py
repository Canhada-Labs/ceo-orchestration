"""Tests for S292 — /ceo-boot 24th Tier-S check: ``scheduled_workflows_red``.

Closes the recurring "scheduled gate red for weeks, invisible" class (six
occurrences: Coverage S283; mutation-gate S290/S291; supply-chain-watch
S291; tournament + reality-ledger S292). Covers:

- registry wiring (name present, 24 checks, timeout override);
- RED when ≥1 scheduled workflow's latest COMPLETED scheduled run concluded
  failure (also timed_out / startup_failure);
- newest-first semantics: an OLDER red behind a newer green must NOT fire
  (latest-run-wins), and in_progress runs are skipped until a completed one;
- NO DATA IS NEVER GREEN: gh missing (OSError) / timeout / rc!=0 /
  unparseable payload / zero window coverage → yellow;
- partial coverage (a scheduled workflow with no run inside the 100-run
  window) → yellow listing the uncovered names — never silently green;
- explicit operator disable (CEO_BOOT_SCHED_RED=0) → green "disabled";
- no scheduled workflows on disk → green;
- detail payload carries the INPUT LIST (S291 doctrine: the instrument
  prints its inputs);
- recommendations: red → "008-scheduled-red" HIGH in BOTH pipelines.

The gh subprocess is always mocked — no network in tests. Workflow files
are written to a temp dir patched over REPO_ROOT (never the live repo).

Env hygiene (PLAN-019 P1-QA-3): every test class subclasses TestEnvContext;
env mutation only via unittest.mock. Stdlib-only, Python >= 3.9. Runs under
pytest AND plain unittest.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "ceo-boot.py"

for _p in (
    str(REPO_ROOT / ".claude" / "hooks"),
    str(REPO_ROOT / ".claude" / "scripts"),
):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from _lib.testing import TestEnvContext  # noqa: E402


def _load_module():
    """Load ceo-boot.py under a unique module name (hyphen in filename)."""
    spec = importlib.util.spec_from_file_location("ceo_boot_sched_red", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_mod = _load_module()

CHECK_NAME = "scheduled_workflows_red"

SCHEDULED_YML = "on:\n  schedule:\n    - cron: '7 3 * * *'\njobs: {}\n"
PUSH_ONLY_YML = "on:\n  push:\n    branches: [main]\njobs: {}\n"


def _completed(rc: int, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(
        args=["gh"], returncode=rc, stdout=stdout, stderr=stderr
    )


def _runs_payload(rows: List[Dict[str, Any]]) -> str:
    return json.dumps(rows)


class _SchedRepo:
    """Temp repo-root with a .github/workflows tree, patched over REPO_ROOT."""

    def __init__(self, test: unittest.TestCase,
                 files: Optional[Dict[str, str]] = None) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        test.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        wf = root / ".github" / "workflows"
        wf.mkdir(parents=True)
        for name, text in (files or {}).items():
            (wf / name).write_text(text, encoding="utf-8")
        self._patch = mock.patch.object(_mod, "REPO_ROOT", root)
        self._patch.start()
        test.addCleanup(self._patch.stop)
        self.root = root


class TestRegistryWiring(TestEnvContext):
    def test_registry_has_24_checks(self):
        self.assertEqual(len(_mod.TIER_S_CHECKS), 24)

    def test_check_registered(self):
        names = [name for name, _ in _mod.TIER_S_CHECKS]
        self.assertIn(CHECK_NAME, names)

    def test_timeout_override_present(self):
        self.assertEqual(_mod.PER_CHECK_TIMEOUT_OVERRIDES_S[CHECK_NAME], 4.0)

    def test_callable_wired(self):
        fn = dict(_mod.TIER_S_CHECKS)[CHECK_NAME]
        self.assertIs(fn, _mod.check_scheduled_workflows_red)


class TestScheduledDerivation(TestEnvContext):
    def test_scheduled_set_derived_from_disk(self):
        _SchedRepo(self, {
            "a-sched.yml": SCHEDULED_YML,
            "b-push.yml": PUSH_ONLY_YML,
            "c-sched.yaml": SCHEDULED_YML,
        })
        got = _mod._scheduled_workflow_paths()
        self.assertEqual(got, [
            ".github/workflows/a-sched.yml",
            ".github/workflows/c-sched.yaml",
        ])

    def test_schedule_word_in_comment_does_not_count(self):
        # `schedule:` line alone is not enough — a `- cron:` line is
        # required too (guards against prose mentions).
        _SchedRepo(self, {
            "prose.yml": "on:\n  push: {}\n# schedule:\njobs: {}\n",
        })
        self.assertEqual(_mod._scheduled_workflow_paths(), [])

    def test_no_workflows_dir_green(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        with mock.patch.object(_mod, "REPO_ROOT", Path(tmp.name)):
            status, summary, detail = _mod.check_scheduled_workflows_red()
        self.assertEqual(status, "green")
        self.assertIn("no scheduled workflows", summary)


class TestRedPaths(TestEnvContext):
    def _run(self, payload_rows, files=None):
        _SchedRepo(self, files or {
            "tournament.yml": SCHEDULED_YML,
            "coverage.yml": SCHEDULED_YML,
        })
        with mock.patch.object(
            _mod.subprocess, "run",
            return_value=_completed(0, _runs_payload(payload_rows)),
        ):
            return _mod.check_scheduled_workflows_red()

    def test_red_on_latest_failure(self):
        status, summary, detail = self._run([
            {"path": ".github/workflows/tournament.yml",
             "status": "completed", "conclusion": "failure"},
            {"path": ".github/workflows/coverage.yml",
             "status": "completed", "conclusion": "success"},
        ])
        self.assertEqual(status, "red")
        self.assertIn("tournament.yml", summary)
        self.assertEqual(detail["red"], [".github/workflows/tournament.yml"])
        # S291 doctrine: the instrument prints its inputs.
        self.assertIn(".github/workflows/coverage.yml", detail["scheduled"])

    def test_red_on_timed_out_and_startup_failure(self):
        for bad in ("timed_out", "startup_failure"):
            status, _, _ = self._run([
                {"path": ".github/workflows/tournament.yml",
                 "status": "completed", "conclusion": bad},
                {"path": ".github/workflows/coverage.yml",
                 "status": "completed", "conclusion": "success"},
            ])
            self.assertEqual(status, "red", bad)

    def test_latest_run_wins_over_older_red(self):
        # Newest-first payload: green now, red before → NOT red.
        status, _, detail = self._run([
            {"path": ".github/workflows/tournament.yml",
             "status": "completed", "conclusion": "success"},
            {"path": ".github/workflows/tournament.yml",
             "status": "completed", "conclusion": "failure"},
            {"path": ".github/workflows/coverage.yml",
             "status": "completed", "conclusion": "success"},
        ])
        self.assertEqual(status, "green")
        self.assertEqual(detail["red"], [])

    def test_in_progress_run_skipped_until_completed(self):
        # in_progress (conclusion null) on top; the completed failure
        # behind it is the decision point.
        status, _, _ = self._run([
            {"path": ".github/workflows/tournament.yml",
             "status": "in_progress", "conclusion": None},
            {"path": ".github/workflows/tournament.yml",
             "status": "completed", "conclusion": "failure"},
            {"path": ".github/workflows/coverage.yml",
             "status": "completed", "conclusion": "success"},
        ])
        self.assertEqual(status, "red")

    def test_cancelled_is_not_red(self):
        status, _, _ = self._run([
            {"path": ".github/workflows/tournament.yml",
             "status": "completed", "conclusion": "cancelled"},
            {"path": ".github/workflows/coverage.yml",
             "status": "completed", "conclusion": "success"},
        ])
        self.assertEqual(status, "green")


class TestNoDataNeverGreen(TestEnvContext):
    def _repo(self):
        _SchedRepo(self, {"tournament.yml": SCHEDULED_YML})

    def test_gh_missing_yellow(self):
        self._repo()
        with mock.patch.object(
            _mod.subprocess, "run", side_effect=FileNotFoundError("gh")
        ):
            status, summary, _ = _mod.check_scheduled_workflows_red()
        self.assertEqual(status, "yellow")
        self.assertIn("no data", summary)

    def test_gh_timeout_yellow_and_skip_emit(self):
        self._repo()
        with mock.patch.object(
            _mod.subprocess, "run",
            side_effect=subprocess.TimeoutExpired(cmd="gh", timeout=3.5),
        ), mock.patch.object(
            _mod, "_emit_ceo_boot_check_skipped_safe"
        ) as emit:
            status, summary, _ = _mod.check_scheduled_workflows_red()
        self.assertEqual(status, "yellow")
        self.assertIn("timeout", summary)
        emit.assert_called_once()
        self.assertEqual(
            emit.call_args.kwargs.get("check_name"), CHECK_NAME
        )

    def test_gh_nonzero_rc_yellow(self):
        self._repo()
        with mock.patch.object(
            _mod.subprocess, "run",
            return_value=_completed(4, "", "HTTP 403: rate limited"),
        ):
            status, summary, _ = _mod.check_scheduled_workflows_red()
        self.assertEqual(status, "yellow")
        self.assertIn("rc=4", summary)

    def test_unparseable_payload_yellow(self):
        self._repo()
        with mock.patch.object(
            _mod.subprocess, "run", return_value=_completed(0, "not json"),
        ):
            status, summary, _ = _mod.check_scheduled_workflows_red()
        self.assertEqual(status, "yellow")
        self.assertIn("unparseable", summary)

    def test_non_list_payload_yellow(self):
        self._repo()
        with mock.patch.object(
            _mod.subprocess, "run", return_value=_completed(0, "{}"),
        ):
            status, summary, _ = _mod.check_scheduled_workflows_red()
        self.assertEqual(status, "yellow")

    def test_zero_coverage_yellow(self):
        # gh succeeded but no scheduled run matched any local workflow.
        self._repo()
        with mock.patch.object(
            _mod.subprocess, "run", return_value=_completed(0, "[]"),
        ):
            status, summary, _ = _mod.check_scheduled_workflows_red()
        self.assertEqual(status, "yellow")
        self.assertIn("0/1", summary)

    def test_partial_coverage_yellow_lists_uncovered(self):
        _SchedRepo(self, {
            "tournament.yml": SCHEDULED_YML,
            "monthly.yml": SCHEDULED_YML,
        })
        with mock.patch.object(
            _mod.subprocess, "run",
            return_value=_completed(0, _runs_payload([
                {"path": ".github/workflows/tournament.yml",
                 "status": "completed", "conclusion": "success"},
            ])),
        ):
            status, summary, detail = _mod.check_scheduled_workflows_red()
        self.assertEqual(status, "yellow")
        self.assertIn("monthly.yml", summary)
        self.assertEqual(
            detail["no_recent_scheduled_run"],
            [".github/workflows/monthly.yml"],
        )


class TestDisableAndGreen(TestEnvContext):
    def test_explicit_disable_green(self):
        _SchedRepo(self, {"tournament.yml": SCHEDULED_YML})
        with mock.patch.dict(
            _mod.os.environ, {"CEO_BOOT_SCHED_RED": "0"}
        ), mock.patch.object(_mod.subprocess, "run") as run:
            status, summary, detail = _mod.check_scheduled_workflows_red()
        self.assertEqual(status, "green")
        self.assertTrue(detail.get("disabled"))
        run.assert_not_called()  # structurally off — no network

    def test_all_green_green(self):
        _SchedRepo(self, {"tournament.yml": SCHEDULED_YML})
        with mock.patch.object(
            _mod.subprocess, "run",
            return_value=_completed(0, _runs_payload([
                {"path": ".github/workflows/tournament.yml",
                 "status": "completed", "conclusion": "success"},
            ])),
        ):
            status, summary, detail = _mod.check_scheduled_workflows_red()
        self.assertEqual(status, "green")
        self.assertEqual(summary, "1/1 scheduled workflows green at latest run")
        self.assertEqual(detail["latest"], {
            ".github/workflows/tournament.yml": "success",
        })


class TestRecommendations(TestEnvContext):
    def _ck(self, name, status="green", summary="ok", detail=None):
        return _mod.CheckResult(name, status, summary, 1.0, detail)

    def test_red_fires_008_high_in_both_pipelines(self):
        results = [self._ck(name) for name, _ in _mod.TIER_S_CHECKS]
        results = [
            self._ck(CHECK_NAME, "red",
                     "1 scheduled workflow(s) red at latest run: x.yml")
            if r.name == CHECK_NAME else r
            for r in results
        ]
        recs = _mod._make_recommendations(results)
        self.assertTrue(any("Scheduled workflow(s) red" in r for r in recs))
        triples = _mod._recommendations_with_severity(results)
        match = [t for t in triples if t[0] == "008-scheduled-red"]
        self.assertEqual(len(match), 1)
        self.assertEqual(match[0][2], "high")
        # Mirror discipline: identical text in both pipelines.
        self.assertIn(match[0][1], recs)

    def test_yellow_does_not_fire_008(self):
        results = [self._ck(name) for name, _ in _mod.TIER_S_CHECKS]
        results = [
            self._ck(CHECK_NAME, "yellow", "no data — gh unavailable")
            if r.name == CHECK_NAME else r
            for r in results
        ]
        triples = _mod._recommendations_with_severity(results)
        self.assertFalse(any(t[0] == "008-scheduled-red" for t in triples))


class TestCureDetection(TestEnvContext):
    """S293 — red scheduled lane + NEWER green completed run = cured.

    The scheduled lane can only turn green at its next cron firing (a
    monthly workflow would keep the boot red for a month after the fix
    landed and was dispatch-validated). Cure semantics: for red paths ONLY,
    consult the newest COMPLETED run across ALL events; green there means
    the red was surfaced AND fixed — the opposite of the invisible-red
    class. Fail-visible: a dead probe keeps the path red.
    """

    FILES = {
        "tournament.yml": SCHEDULED_YML,
        "coverage.yml": SCHEDULED_YML,
    }

    RED_SCHED = [
        {"path": ".github/workflows/tournament.yml",
         "status": "completed", "conclusion": "failure"},
        {"path": ".github/workflows/coverage.yml",
         "status": "completed", "conclusion": "success"},
    ]

    def test_cured_by_newer_green_completed_run(self):
        _SchedRepo(self, dict(self.FILES))
        probe = [{"path": ".github/workflows/tournament.yml",
                  "status": "completed", "conclusion": "success"}]
        with mock.patch.object(
            _mod.subprocess, "run",
            side_effect=[_completed(0, _runs_payload(self.RED_SCHED)),
                         _completed(0, _runs_payload(probe))],
        ) as m:
            status, summary, detail = _mod.check_scheduled_workflows_red()
        self.assertEqual(status, "green")
        self.assertEqual(detail["red"], [])
        self.assertEqual(
            detail["cured_pending_cron"],
            {".github/workflows/tournament.yml": "success"},
        )
        self.assertIn("cured", summary)
        self.assertEqual(m.call_count, 2)

    def test_probe_red_stays_red(self):
        _SchedRepo(self, dict(self.FILES))
        probe = [{"path": ".github/workflows/tournament.yml",
                  "status": "completed", "conclusion": "failure"}]
        with mock.patch.object(
            _mod.subprocess, "run",
            side_effect=[_completed(0, _runs_payload(self.RED_SCHED)),
                         _completed(0, _runs_payload(probe))],
        ):
            status, _, detail = _mod.check_scheduled_workflows_red()
        self.assertEqual(status, "red")
        self.assertEqual(detail["cured_pending_cron"], {})
        self.assertEqual(
            detail["red"], [".github/workflows/tournament.yml"])

    def test_probe_failure_keeps_red_fail_visible(self):
        # A dead cure-probe must under-cure, never under-report.
        _SchedRepo(self, dict(self.FILES))
        with mock.patch.object(
            _mod.subprocess, "run",
            side_effect=[_completed(0, _runs_payload(self.RED_SCHED)),
                         subprocess.TimeoutExpired(cmd="gh", timeout=3.5)],
        ):
            status, _, detail = _mod.check_scheduled_workflows_red()
        self.assertEqual(status, "red")
        self.assertEqual(detail["cured_pending_cron"], {})

    def test_probe_in_progress_rows_do_not_cure(self):
        # per_page window with only a non-completed row for the path ->
        # no completed conclusion -> stays red (server-side status filter
        # is not trusted).
        _SchedRepo(self, dict(self.FILES))
        probe = [{"path": ".github/workflows/tournament.yml",
                  "status": "in_progress", "conclusion": None}]
        with mock.patch.object(
            _mod.subprocess, "run",
            side_effect=[_completed(0, _runs_payload(self.RED_SCHED)),
                         _completed(0, _runs_payload(probe))],
        ):
            status, _, _ = _mod.check_scheduled_workflows_red()
        self.assertEqual(status, "red")

    def test_steady_state_green_makes_no_extra_calls(self):
        # Zero reds -> the cure probe must not fire at all.
        _SchedRepo(self, dict(self.FILES))
        green = [
            {"path": ".github/workflows/tournament.yml",
             "status": "completed", "conclusion": "success"},
            {"path": ".github/workflows/coverage.yml",
             "status": "completed", "conclusion": "success"},
        ]
        with mock.patch.object(
            _mod.subprocess, "run",
            return_value=_completed(0, _runs_payload(green)),
        ) as m:
            status, summary, _ = _mod.check_scheduled_workflows_red()
        self.assertEqual(status, "green")
        self.assertNotIn("cured", summary)
        self.assertEqual(m.call_count, 1)


if __name__ == "__main__":
    unittest.main()
