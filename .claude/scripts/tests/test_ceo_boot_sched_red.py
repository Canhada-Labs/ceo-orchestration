"""Tests for S292 — /ceo-boot 24th Tier-S check: ``scheduled_workflows_red``.

Closes the recurring "scheduled gate red for weeks, invisible" class (six
occurrences: Coverage S283; mutation-gate S290/S291; supply-chain-watch
S291; tournament + reality-ledger S292). S361 (PLAN-194 L2) rebuilt the
check after the S360 false red (2nd occurrence of two classes: the gh
endpoints that filter server-side answered OLD pages; the cure probe ran
out of a budget split across three constants). Covers:

- registry wiring (name present, 24 checks, override = the ONE budget);
- (c) ONE unfiltered call per scheduled workflow, in parallel, no server
  filter in the URL, detection AND cure out of the SAME response;
- (d) one budget constant: the old three are gone, every gh call's timeout
  derives from it;
- (e) cron-derived freshness guard: old data is YELLOW, never red —
  including the S360 STALE PAGE case (red under the pre-S361 design,
  green now: the control that did not exist before);
- (f) a red whose cure cannot be verified says so in the summary;
- RED when ≥1 scheduled workflow's newest COMPLETED scheduled run is fresh
  and concluded failure (also timed_out / startup_failure);
- NO DATA IS NEVER GREEN: gh missing / timeout / rc!=0 / unparseable /
  no scheduled run in the page → yellow;
- explicit operator disable (CEO_BOOT_SCHED_RED=0) → green "disabled";
- recommendations: red → "008-scheduled-red" HIGH in BOTH pipelines.

The gh subprocess is always mocked — no network in tests. Workflow files
are written to a temp dir patched over REPO_ROOT (never the live repo). The
clock of the freshness guard is pinned (``_sched_red_now``).

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
import threading
import unittest
from datetime import datetime, timedelta, timezone
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

DAILY_YML = "on:\n  schedule:\n    - cron: '7 3 * * *'\njobs: {}\n"
WEEKLY_YML = "on:\n  schedule:\n    - cron: '0 6 * * 1'\njobs: {}\n"
MONTHLY_YML = "on:\n  schedule:\n    - cron: '0 4 1 * *'\njobs: {}\n"
SCHEDULED_YML = DAILY_YML
PUSH_ONLY_YML = "on:\n  push:\n    branches: [main]\njobs: {}\n"

# Pinned clock for the freshness guard (the S360 measurement day).
NOW = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)


def _ts(days_ago: float) -> str:
    return (NOW - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row(name: str, conclusion: Optional[str], *, event: str = "schedule",
         status: str = "completed", days_ago: float = 0.5) -> Dict[str, Any]:
    return {
        "path": ".github/workflows/{0}".format(name),
        "event": event,
        "status": status,
        "conclusion": conclusion,
        "created_at": _ts(days_ago),
    }


def _completed(rc: int, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess(
        args=["gh"], returncode=rc, stdout=stdout, stderr=stderr
    )


def _url(args) -> str:
    return " ".join(str(a) for a in args)


def _wf_router(pages: Dict[str, Any], filtered: Optional[Dict[str, Any]] = None,
               calls: Optional[List[str]] = None):
    """side_effect routing by URL, thread-safe (calls run in parallel).

    ``pages`` maps a workflow basename to the rows of its UNFILTERED page
    (newest first) or to an exception (dead call). Any URL that carries a
    server-side filter (``event=``/``status=``) gets ``filtered`` instead —
    the S360 shape: filtered endpoints answered OLD pages. ``filtered``
    defaults to ``pages`` (same answer whatever the URL). The repo-wide
    ``actions/runs`` URL of the pre-S361 design is answered with the union
    of the filtered pages.
    """
    lock = threading.Lock()
    flt = pages if filtered is None else filtered

    def _run(args, **kwargs):
        url = _url(args)
        with lock:
            if calls is not None:
                calls.append(url)
        src = flt if ("event=" in url or "status=" in url) else pages
        if "/actions/workflows/" not in url:
            rows: List[Any] = []
            for v in src.values():
                if isinstance(v, list):
                    rows.extend(v)
            return _completed(0, json.dumps(rows))
        for name, rows in src.items():
            if "/actions/workflows/{0}/runs".format(name) in url:
                if isinstance(rows, BaseException):
                    raise rows
                return _completed(0, json.dumps(rows))
        return _completed(0, "[]")
    return _run


class _SchedRepo:
    """Temp repo-root with a .github/workflows tree, patched over REPO_ROOT.

    Also pins the freshness-guard clock (``create=True`` keeps the stale-page
    controls runnable against the pre-S361 module, where they fail by
    ASSERTION — the red→green proof).
    """

    def __init__(self, test: unittest.TestCase,
                 files: Optional[Dict[str, str]] = None) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        test.addCleanup(self._tmp.cleanup)
        root = Path(self._tmp.name)
        wf = root / ".github" / "workflows"
        wf.mkdir(parents=True)
        for name, text in (files or {}).items():
            (wf / name).write_text(text, encoding="utf-8")
        for target, value in (
            ("REPO_ROOT", root),
            ("_sched_red_now", lambda: NOW.timestamp()),
        ):
            p = mock.patch.object(_mod, target, value, create=True)
            p.start()
            test.addCleanup(p.stop)
        self.root = root


def _check(test: unittest.TestCase, files: Dict[str, str], pages: Dict[str, Any],
           filtered: Optional[Dict[str, Any]] = None,
           calls: Optional[List[str]] = None):
    _SchedRepo(test, files)
    with mock.patch.object(
        _mod.subprocess, "run",
        side_effect=_wf_router(pages, filtered, calls),
    ):
        return _mod.check_scheduled_workflows_red()


class TestRegistryWiring(TestEnvContext):
    def test_registry_has_24_checks(self):
        self.assertEqual(len(_mod.TIER_S_CHECKS), 24)

    def test_check_registered(self):
        names = [name for name, _ in _mod.TIER_S_CHECKS]
        self.assertIn(CHECK_NAME, names)

    def test_timeout_override_is_the_single_budget(self):
        self.assertEqual(
            _mod.PER_CHECK_TIMEOUT_OVERRIDES_S[CHECK_NAME],
            _mod.SCHED_RED_BUDGET_S,
        )
        self.assertLess(_mod.SCHED_RED_BUDGET_S, _mod.AGGREGATE_TIMEOUT_S)

    def test_callable_wired(self):
        fn = dict(_mod.TIER_S_CHECKS)[CHECK_NAME]
        self.assertIs(fn, _mod.check_scheduled_workflows_red)


class TestSingleBudget(TestEnvContext):
    """(d) ONE budget constant — the S360 three (3.5/3.8/4.0) are gone."""

    def test_the_three_old_constants_are_gone(self):
        for old in ("SCHED_RED_GH_TIMEOUT_S_DEFAULT",
                    "_SCHED_RED_CHECK_DEADLINE_S",
                    "_SCHED_RED_CURE_PROBE_MAX"):
            self.assertFalse(hasattr(_mod, old), old)

    def test_budget_default_and_env_clamp(self):
        self.assertEqual(_mod._sched_red_budget_s(), _mod.SCHED_RED_BUDGET_S)
        with mock.patch.dict(
            _mod.os.environ, {"CEO_BOOT_SCHED_RED_TIMEOUT_S": "99"}
        ):
            self.assertEqual(_mod._sched_red_budget_s(), 8.0)
        with mock.patch.dict(
            _mod.os.environ, {"CEO_BOOT_SCHED_RED_TIMEOUT_S": "junk"}
        ):
            self.assertEqual(_mod._sched_red_budget_s(),
                             _mod.SCHED_RED_BUDGET_S)

    def test_every_gh_timeout_derives_from_the_budget(self):
        _SchedRepo(self, {"a.yml": SCHEDULED_YML, "b.yml": SCHEDULED_YML})
        seen: List[float] = []
        lock = threading.Lock()

        def _run(args, **kwargs):
            with lock:
                seen.append(kwargs.get("timeout"))
            return _completed(0, json.dumps([]))
        with mock.patch.object(_mod.subprocess, "run", side_effect=_run):
            _mod.check_scheduled_workflows_red()
        self.assertEqual(len(seen), 2)
        for t in seen:
            self.assertIsNotNone(t)
            self.assertGreater(t, 0.0)
            self.assertLessEqual(t, _mod.SCHED_RED_BUDGET_S)


class TestScheduledDerivation(TestEnvContext):
    def test_scheduled_set_derived_from_disk(self):
        _SchedRepo(self, {
            "a-sched.yml": SCHEDULED_YML,
            "b-push.yml": PUSH_ONLY_YML,
            "c-sched.yaml": WEEKLY_YML,
        })
        got = _mod._scheduled_workflow_paths()
        self.assertEqual(got, [
            ".github/workflows/a-sched.yml",
            ".github/workflows/c-sched.yaml",
        ])
        self.assertEqual(
            _mod._scheduled_workflows()[".github/workflows/c-sched.yaml"],
            ["0 6 * * 1"],
        )

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


class TestCronPeriod(TestEnvContext):
    def test_periods(self):
        day = _mod._SCHED_RED_DAY_S
        self.assertEqual(_mod._sched_red_cron_period_s("7 3 * * *"), day)
        self.assertEqual(_mod._sched_red_cron_period_s("*/15 * * * *"), day)
        self.assertEqual(_mod._sched_red_cron_period_s("0 6 * * 1"), 7 * day)
        self.assertEqual(_mod._sched_red_cron_period_s("0 4 1 * *"), 31 * day)
        self.assertIsNone(_mod._sched_red_cron_period_s("@daily"))

    def test_most_frequent_cron_wins_and_fallback(self):
        day = _mod._SCHED_RED_DAY_S
        self.assertEqual(
            _mod._sched_red_period_s(["0 4 1 * *", "7 3 * * *"]), day)
        self.assertEqual(_mod._sched_red_period_s(["nonsense"]),
                         _mod._SCHED_RED_PERIOD_FALLBACK_S)


class TestRedPaths(TestEnvContext):
    FILES = {"tournament.yml": SCHEDULED_YML, "coverage.yml": SCHEDULED_YML}

    def _run(self, pages):
        return _check(self, dict(self.FILES), pages)

    def test_red_on_latest_failure(self):
        status, summary, detail = self._run({
            "tournament.yml": [_row("tournament.yml", "failure")],
            "coverage.yml": [_row("coverage.yml", "success")],
        })
        self.assertEqual(status, "red")
        self.assertIn("tournament.yml", summary)
        self.assertIn("no newer completed run", summary)
        self.assertEqual(detail["red"], [".github/workflows/tournament.yml"])
        # S291 doctrine: the instrument prints its inputs.
        self.assertIn(".github/workflows/coverage.yml", detail["scheduled"])

    def test_red_on_timed_out_and_startup_failure(self):
        for bad in ("timed_out", "startup_failure"):
            status, _, _ = self._run({
                "tournament.yml": [_row("tournament.yml", bad)],
                "coverage.yml": [_row("coverage.yml", "success")],
            })
            self.assertEqual(status, "red", bad)

    def test_latest_scheduled_run_wins_over_older_red(self):
        status, _, detail = self._run({
            "tournament.yml": [
                _row("tournament.yml", "success", days_ago=0.2),
                _row("tournament.yml", "failure", days_ago=1.2),
            ],
            "coverage.yml": [_row("coverage.yml", "success")],
        })
        self.assertEqual(status, "green")
        self.assertEqual(detail["red"], [])

    def test_in_progress_scheduled_run_skipped_until_completed(self):
        status, _, _ = self._run({
            "tournament.yml": [
                _row("tournament.yml", None, status="in_progress",
                     days_ago=0.1),
                _row("tournament.yml", "failure", days_ago=1.0),
            ],
            "coverage.yml": [_row("coverage.yml", "success")],
        })
        self.assertEqual(status, "red")

    def test_cancelled_is_not_red(self):
        status, _, _ = self._run({
            "tournament.yml": [_row("tournament.yml", "cancelled")],
            "coverage.yml": [_row("coverage.yml", "success")],
        })
        self.assertEqual(status, "green")


class TestOneUnfilteredCallPerWorkflow(TestEnvContext):
    """(c) one call per scheduled workflow, no server filter, in parallel."""

    FILES = {"tournament.yml": SCHEDULED_YML, "coverage.yml": SCHEDULED_YML,
             "mutation-gate.yml": WEEKLY_YML}

    def test_one_call_each_even_with_a_red_and_no_filter(self):
        calls: List[str] = []
        status, _, _ = _check(self, dict(self.FILES), {
            "tournament.yml": [_row("tournament.yml", "failure")],
            "coverage.yml": [_row("coverage.yml", "success")],
            "mutation-gate.yml": [_row("mutation-gate.yml", "success")],
        }, calls=calls)
        self.assertEqual(status, "red")
        # Detection AND cure out of the same answer: no second probe call.
        self.assertEqual(len(calls), 3)
        for name in self.FILES:
            self.assertEqual(
                sum("/actions/workflows/{0}/runs".format(name) in c
                    for c in calls), 1, name)
        for c in calls:
            self.assertNotIn("event=", c)
            self.assertNotIn("status=", c)
            self.assertNotIn("/actions/runs", c)  # no repo-wide window

    def test_calls_run_in_parallel(self):
        # A barrier only opens when ALL calls are in flight at once: a
        # sequential implementation breaks it and loses every workflow.
        names = sorted(self.FILES)
        barrier = threading.Barrier(len(names), timeout=3.0)
        _SchedRepo(self, dict(self.FILES))

        def _run(args, **kwargs):
            url = _url(args)
            barrier.wait()
            for n in names:
                if "/actions/workflows/{0}/runs".format(n) in url:
                    return _completed(0, json.dumps([_row(n, "success")]))
            return _completed(0, "[]")
        with mock.patch.dict(
            _mod.os.environ, {"CEO_BOOT_SCHED_RED_TIMEOUT_S": "6"}
        ), mock.patch.object(_mod.subprocess, "run", side_effect=_run):
            status, _, detail = _mod.check_scheduled_workflows_red()
        self.assertEqual(status, "green", detail)
        self.assertEqual(detail["no_data"], {})

    def test_deadline_turns_slow_calls_into_no_data(self):
        release = threading.Event()
        self.addCleanup(release.set)
        _SchedRepo(self, {"tournament.yml": SCHEDULED_YML})

        def _run(args, **kwargs):
            release.wait(5.0)
            return _completed(0, "[]")
        with mock.patch.dict(
            _mod.os.environ, {"CEO_BOOT_SCHED_RED_TIMEOUT_S": "0.5"}
        ), mock.patch.object(
            _mod.subprocess, "run", side_effect=_run,
        ), mock.patch.object(_mod, "_emit_ceo_boot_check_skipped_safe") as emit:
            status, summary, detail = _mod.check_scheduled_workflows_red()
        self.assertEqual(status, "yellow")
        self.assertIn("timeout", summary)
        self.assertEqual(
            detail["no_data"], {".github/workflows/tournament.yml": "deadline"})
        emit.assert_called_once()


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
        self.assertIn("gh CLI unavailable", summary)

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
        # gh succeeded but the page holds no scheduled run.
        status, summary, _ = _check(
            self, {"tournament.yml": SCHEDULED_YML}, {"tournament.yml": []})
        self.assertEqual(status, "yellow")
        self.assertIn("0/1", summary)

    def test_partial_coverage_yellow_lists_uncovered(self):
        status, summary, detail = _check(self, {
            "tournament.yml": SCHEDULED_YML,
            "monthly.yml": MONTHLY_YML,
        }, {
            "tournament.yml": [_row("tournament.yml", "success")],
            "monthly.yml": [],
        })
        self.assertEqual(status, "yellow")
        self.assertIn("monthly.yml", summary)
        self.assertEqual(
            detail["no_recent_scheduled_run"],
            [".github/workflows/monthly.yml"],
        )

    def test_busy_push_lane_burying_its_scheduled_run_is_yellow(self):
        # S360: a push-heavy workflow can push its scheduled run past the
        # page size. That is reported, never guessed (and never red; the
        # pre-S361 design trusted the filtered endpoint and read it red).
        n = getattr(_mod, "_SCHED_RED_PER_PAGE", 30)
        page = [_row("validate.yml", "failure", event="push", days_ago=0.01)
                for _ in range(n)]
        status, summary, detail = _check(
            self, {"validate.yml": DAILY_YML}, {"validate.yml": page})
        self.assertEqual(status, "yellow")
        self.assertIn("no scheduled run in the last {0} runs".format(n),
                      summary)
        self.assertEqual(detail["red"], [])


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
        status, summary, detail = _check(
            self, {"tournament.yml": SCHEDULED_YML},
            {"tournament.yml": [_row("tournament.yml", "success")]})
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


class TestCureFromTheSameResponse(TestEnvContext):
    """S293 cure semantics (newest completed newer run, any event), read
    from the SAME unfiltered page that carried the red — S361."""

    FILES = {"tournament.yml": SCHEDULED_YML, "coverage.yml": SCHEDULED_YML}
    GREEN_COVERAGE = [_row("coverage.yml", "success")]

    def _run(self, tournament_page):
        return _check(self, dict(self.FILES), {
            "tournament.yml": tournament_page,
            "coverage.yml": self.GREEN_COVERAGE,
        })

    def test_cured_by_newer_green_completed_run(self):
        status, summary, detail = self._run([
            _row("tournament.yml", "success", event="workflow_dispatch",
                 days_ago=0.2),
            _row("tournament.yml", "failure", days_ago=0.9),
        ])
        self.assertEqual(status, "green")
        self.assertEqual(detail["red"], [])
        self.assertEqual(
            detail["cured_pending_cron"],
            {".github/workflows/tournament.yml": "success"},
        )
        self.assertIn("cured", summary)

    def test_newer_red_run_does_not_cure(self):
        status, _, detail = self._run([
            _row("tournament.yml", "failure", event="push", days_ago=0.2),
            _row("tournament.yml", "failure", days_ago=0.9),
        ])
        self.assertEqual(status, "red")
        self.assertEqual(detail["cured_pending_cron"], {})

    def test_unverified_cure_is_said_in_the_summary(self):
        # (f) newer run still running: the cure cannot be concluded — the
        # red stays, and the SUMMARY says the cure was not verified.
        status, summary, detail = self._run([
            _row("tournament.yml", None, event="workflow_dispatch",
                 status="in_progress", days_ago=0.1),
            _row("tournament.yml", "failure", days_ago=0.9),
        ])
        self.assertEqual(status, "red")
        self.assertIn("cure NOT verified", summary)
        self.assertEqual(detail["cure_unverified"],
                         [".github/workflows/tournament.yml"])

    def test_answer_for_another_lane_never_decides(self):
        # A mis-scoped row neither reds nor cures the lane it was asked for.
        status, _, detail = self._run([
            _row("coverage.yml", "success", days_ago=0.1),
            _row("tournament.yml", "failure", days_ago=0.9),
        ])
        self.assertEqual(status, "red")
        self.assertEqual(detail["cured_pending_cron"], {})

    def test_unvouchable_basename_never_reaches_the_url(self):
        # Fail-closed on INPUT: the name never becomes a URL, and the lane
        # is reported without data — never "cured" by omission.
        calls: List[str] = []
        status, _, detail = _check(self, {
            "tour nament.yml": SCHEDULED_YML,
            "coverage.yml": SCHEDULED_YML,
        }, {"coverage.yml": self.GREEN_COVERAGE}, calls=calls)
        self.assertEqual(status, "yellow")
        self.assertIn(".github/workflows/tour nament.yml", detail["no_data"])
        self.assertNotIn("tour nament", " ".join(calls))


class TestStalePage(TestEnvContext):
    """(e) cron-derived freshness guard + the S360 STALE PAGE case.

    Red→green control: under the pre-S361 design these return RED (it read
    the server-filtered endpoints, which answered an OLD page, and had no
    freshness guard); now they return green / yellow, never red.
    """

    def test_s360_stale_filtered_page_with_fresh_green_elsewhere(self):
        # Filtered endpoints answer the OLD page (failures of 01/08 and
        # 03/08, newest run 05/09); the unfiltered listing answers today's
        # green scheduled runs. Measured S360 shape.
        old = {
            "tournament.yml": [_row("tournament.yml", "failure", days_ago=61)],
            "mutation-gate.yml": [
                _row("mutation-gate.yml", "failure", days_ago=59)],
        }
        fresh = {
            "tournament.yml": [_row("tournament.yml", "success", days_ago=0.3)],
            "mutation-gate.yml": [
                _row("mutation-gate.yml", "success", days_ago=3)],
        }
        status, summary, detail = _check(self, {
            "tournament.yml": MONTHLY_YML,
            "mutation-gate.yml": WEEKLY_YML,
        }, fresh, filtered=old)
        self.assertNotEqual(status, "red", summary)
        self.assertEqual(status, "green", summary)

    def test_stale_scheduled_failure_is_yellow_never_red(self):
        # Every endpoint answers the same OLD page: a weekly gate whose
        # newest scheduled run is 59 days old cannot vouch for today.
        old = {"mutation-gate.yml": [
            _row("mutation-gate.yml", "failure", days_ago=59)]}
        status, summary, detail = _check(
            self, {"mutation-gate.yml": WEEKLY_YML}, old)
        self.assertEqual(status, "yellow", summary)
        self.assertIn("stale", summary)
        self.assertIn("failure", summary)  # the old verdict is not hidden
        self.assertEqual(detail["red"], [])
        self.assertIn(".github/workflows/mutation-gate.yml", detail["stale"])

    def test_guard_follows_the_cron_period(self):
        # Monthly: 40 days is fresh (one firing may be pending) → red;
        # 70 days is beyond 2 periods → yellow.
        for days, expected in ((40, "red"), (70, "yellow")):
            status, summary, _ = _check(
                self, {"tournament.yml": MONTHLY_YML},
                {"tournament.yml": [
                    _row("tournament.yml", "failure", days_ago=days)]})
            self.assertEqual(status, expected, (days, summary))

    def test_undated_scheduled_run_is_stale(self):
        row = _row("tournament.yml", "failure")
        row["created_at"] = None
        status, _, detail = _check(
            self, {"tournament.yml": SCHEDULED_YML}, {"tournament.yml": [row]})
        self.assertEqual(status, "yellow")
        self.assertIn(".github/workflows/tournament.yml", detail["stale"])

    def test_stale_green_is_not_green(self):
        status, _, _ = _check(
            self, {"tournament.yml": SCHEDULED_YML},
            {"tournament.yml": [
                _row("tournament.yml", "success", days_ago=10)]})
        self.assertEqual(status, "yellow")


if __name__ == "__main__":
    unittest.main()
