"""PLAN-179 S329 — oracle for the `--since=` horizon of persona_demand_scan.

WHAT BROKE, AND WHY A NEW TEST ROOT WAS NEEDED
-----------------------------------------------
``_scan_commit_files`` built its horizon as ``f"--since={hours}h"`` with
``hours=168``.  Git's approxidate parser only recognises a unit word from
four characters on ("hour"), so ``168h`` is not a duration to it: the ``h``
matches nothing and the digits fall through to ``pending_number()``, which
keeps a number only when it fits a date field (``<32`` → day-of-month,
``<13`` → month, 1970..2099 → year).  168 fits none, so it is DISCARDED and
no field is touched — the cutoff stays at *now*.  ``git log`` then exits 0
with empty output, and the scanner cannot tell that from a genuinely quiet
week.

The pre-existing coverage of this path is
``_lib/tests/test_plan104_demand_resolver.py::TestWaiveTimingSemantics::
test_waive_scoped_to_changed_paths``, which commits and scans within the
same wall-clock second.  ``--since`` is inclusive, so that test passed
whenever the scan landed in the commit's own second and failed when it
crossed into the next one — a ~10-30 % flake that read as ordering or load
and was neither.  It could never fail reliably, because it never asked for
anything OLDER than now.

Every mechanism assertion here therefore dates its commits in the PAST.
That is the whole point: on the old argument these are deterministically
red, not flakily red.  ``TestApproxidateMechanism`` pins the git behaviour
itself, so if a future git ever learns to read ``168h`` as a duration the
reason this file exists is re-stated rather than silently lost.

Hermetic: every test builds its own repo under a tempdir and passes commit
dates through the SUBPROCESS env only (``GIT_AUTHOR_DATE`` /
``GIT_COMMITTER_DATE`` in a copied dict) — ``os.environ`` is never mutated.
The live-repo assertion is READ-ONLY.
"""
from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional


def _find_repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / ".claude" / "scripts").is_dir():
            return parent
    raise RuntimeError("repo root with .claude/scripts/ not found")


_REPO_ROOT = _find_repo_root()
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
from _lib.testing import TestEnvContext  # noqa: E402

_SCANNER_PATH = _REPO_ROOT / ".claude" / "scripts" / "persona_demand_scan.py"


def _load_scanner():
    """Load the scanner the way the canonical test does (path-based, no sys.modules)."""
    spec = importlib.util.spec_from_file_location("scanner_win", str(_SCANNER_PATH))
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise unittest.SkipTest("persona_demand_scan.py not loadable")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class GitRepoCase(TestEnvContext):
    """Builds throwaway git repos with commits at explicit dates."""

    def _init_repo(self, root: Path) -> Path:
        repo = root / "repo"
        repo.mkdir()
        subprocess.check_call(["git", "init", "-q", "-b", "main", str(repo)])
        for key, val in (
            ("user.email", "test@test"),
            ("user.name", "Test"),
            ("commit.gpgsign", "false"),
        ):
            subprocess.check_call(["git", "config", key, val], cwd=str(repo))
        return repo

    @staticmethod
    def _pinned_now(day: int = 15) -> datetime:
        """A fixed instant on ``day`` of the current month, 12:00 UTC.

        Used to pin BOTH the fixture commit dates and git's own clock
        (``GIT_TEST_DATE_NOW`` — the hook git's approxidate reads instead
        of gettimeofday), so an assertion about day-of-month arithmetic
        holds on every calendar day (rail P1, S329).
        """
        now = datetime.now(timezone.utc)
        return datetime(now.year, now.month, day, 12, 0, 0, tzinfo=timezone.utc)

    def _commit(self, repo: Path, rel_path: str, message: str,
                minutes_ago: int, now: Optional[datetime] = None) -> None:
        """Commit ``rel_path`` with author+committer date ``minutes_ago``.

        The date travels in a COPY of os.environ handed to the subprocess;
        the parent process environment is never touched. ``now`` pins the
        reference instant (default: the real clock).
        """
        target = repo / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# content\n", encoding="utf-8")
        base = now if now is not None else datetime.now(timezone.utc)
        stamp = (base - timedelta(minutes=minutes_ago)).isoformat()
        env = dict(os.environ)
        env["GIT_AUTHOR_DATE"] = stamp
        env["GIT_COMMITTER_DATE"] = stamp
        subprocess.check_call(["git", "add", "."], cwd=str(repo))
        subprocess.check_call(
            ["git", "commit", "-q", "-m", message], cwd=str(repo), env=env,
        )

    def _git_subjects(self, repo: Path, since_arg: Optional[str],
                      git_now: Optional[datetime] = None) -> List[str]:
        args = ["git", "log", "HEAD", "--no-merges", "--pretty=format:%s"]
        if since_arg is not None:
            args.insert(3, since_arg)
        env = dict(os.environ)
        if git_now is not None:
            env["GIT_TEST_DATE_NOW"] = str(int(git_now.timestamp()))
        out = subprocess.run(
            args, cwd=str(repo), capture_output=True, text=True, env=env,
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        return [ln for ln in out.stdout.splitlines() if ln.strip()]


class TestApproxidateMechanism(GitRepoCase):
    """Pin the git behaviour the cure exists to avoid.

    These assert on git itself, not on our code. They are the positive
    control: they reproduce the MECHANISM (a bare `<N>h` is not a duration
    to approxidate), not merely the symptom.
    """

    def test_bare_168h_collapses_the_window_to_now(self):
        with tempfile.TemporaryDirectory() as td:
            repo = self._init_repo(Path(td))
            self._commit(repo, "old.txt", "aged-3-days", minutes_ago=4320)
            self._commit(repo, "recent.txt", "aged-2-hours", minutes_ago=120)

            # The defective argument: both commits are inside a true 168h
            # window, yet neither survives, because the cutoff is `now`.
            self.assertEqual(
                self._git_subjects(repo, "--since=168h"), [],
                "git learned to parse a bare '168h' as a duration — the "
                "premise of _since_arg() changed; re-derive the cure",
            )
            # The same window, spelled so approxidate can read it.
            self.assertEqual(
                sorted(self._git_subjects(repo, "--since=168.hours.ago")),
                ["aged-2-hours", "aged-3-days"],
            )

    def test_bare_2h_is_read_as_a_day_of_month(self):
        """`2h` misparses DIFFERENTLY from `168h` — 2 fits day-of-month.

        Documents why the class is invisible to spot checks: a small N
        yields a plausible-looking window (this month's 2nd onward) and a
        large one yields an empty window. Neither errors.
        """
        with tempfile.TemporaryDirectory() as td:
            repo = self._init_repo(Path(td))
            # Calendar-independent (rail P1, S329): `2h` resolves to day 2 of
            # the CURRENT month, which precedes a 3-day-old commit only from
            # the 6th onward. Pin the fixture AND git's clock to the 15th:
            # "day 2" is then 13 days back and admits the commit, while the
            # word form keeps the true 2-hour window and does not.
            pinned = self._pinned_now(day=15)
            self._commit(repo, "a.txt", "aged-3-days", minutes_ago=4320,
                         now=pinned)
            subjects = self._git_subjects(repo, "--since=2h", git_now=pinned)
            true_window = self._git_subjects(
                repo, "--since=2.hours.ago", git_now=pinned,
            )
            self.assertEqual(true_window, [],
                             "a 3-day-old commit must not be inside 2 hours")
            self.assertEqual(
                subjects, ["aged-3-days"],
                "a bare digit falls through to a date field: with the clock "
                "pinned to the 15th, `2h` reads as day-of-month 2 and admits "
                "a 3-day-old commit",
            )

    def test_pinned_clock_is_honoured_by_git(self):
        """Self-check of the pin: GIT_TEST_DATE_NOW must move git's now."""
        with tempfile.TemporaryDirectory() as td:
            repo = self._init_repo(Path(td))
            self._commit(repo, "a.txt", "aged-3-days", minutes_ago=4320)
            year_2000 = datetime(2000, 1, 1, tzinfo=timezone.utc)
            self.assertEqual(
                self._git_subjects(repo, "--since=1.second.ago",
                                   git_now=year_2000),
                ["aged-3-days"],
                "with git's clock pinned to 2000, every commit is in the future "
                "of the cutoff and must be listed",
            )
            self.assertEqual(
                self._git_subjects(repo, "--since=1.second.ago"), [],
                "control: without the pin the 3-day-old commit is outside",
            )

    def test_since_is_inclusive_of_the_cutoff_second(self):
        """Why the canonical test flaked instead of failing outright."""
        with tempfile.TemporaryDirectory() as td:
            repo = self._init_repo(Path(td))
            self._commit(repo, "a.txt", "right-now", minutes_ago=0)
            out = subprocess.run(
                ["git", "log", "HEAD", "--pretty=format:%cI"],
                cwd=str(repo), capture_output=True, text=True,
            )
            exact = out.stdout.strip().splitlines()[0]
            self.assertEqual(
                self._git_subjects(repo, "--since=" + exact), ["right-now"],
                "--since must admit a commit AT the cutoff; that inclusivity "
                "is what let the same-second canonical test pass at all",
            )


class TestSinceArgIsAbsolute(GitRepoCase):
    """The cure's contract: an instant, not an expression."""

    def setUp(self):
        super().setUp()
        self.scanner = _load_scanner()

    def test_emits_iso8601_utc_instant(self):
        arg = self.scanner._since_arg(168)
        self.assertTrue(arg.startswith("--since="), arg)
        value = arg[len("--since="):]
        self.assertRegex(
            value, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$",
            "must be an absolute ISO-8601 UTC instant, never an approxidate",
        )
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc,
        )
        delta = datetime.now(timezone.utc) - parsed
        self.assertGreater(delta, timedelta(hours=167, minutes=59))
        self.assertLess(delta, timedelta(hours=168, minutes=1))

    def test_window_tracks_the_hours_argument(self):
        for hours in (1, 24, 168, 720):
            with self.subTest(hours=hours):
                value = self.scanner._since_arg(hours)[len("--since="):]
                parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=timezone.utc,
                )
                delta = datetime.now(timezone.utc) - parsed
                self.assertLess(
                    abs(delta - timedelta(hours=hours)), timedelta(minutes=1),
                )

    def test_no_bare_unit_approxidate_survives_in_the_module(self):
        """Anti-rot: the class must not grow a second site in this file.

        Reads the file on disk rather than the imported module so a
        re-introduced literal is caught even if it sits on a cold path.
        """
        source = _SCANNER_PATH.read_text(encoding="utf-8")
        offenders = [
            ln for ln in source.splitlines()
            if re.search(r'--since=\{?[A-Za-z_]*\}?\d*\s*(h|d|w|m|y)["\']', ln)
        ]
        self.assertEqual(
            offenders, [],
            "bare-unit approxidate re-introduced; use _since_arg()",
        )


class TestScannerSeesAgedCommits(GitRepoCase):
    """End-to-end: the demand a 3-day-old commit should raise.

    RED on the pre-cure argument for every run, not one in ten: the commit
    is dated outside the collapsed window by three days.
    """

    def setUp(self):
        super().setUp()
        self.scanner = _load_scanner()

    def _auth_demands(self, repo: Path):
        return [
            d for d in self.scanner.detect_all(repo)
            if d.demand_event_type == "auth_edit" and d.target_ref == "src/auth.py"
        ]

    def test_auth_edit_three_days_old_is_detected(self):
        with tempfile.TemporaryDirectory() as td:
            repo = self._init_repo(Path(td))
            self._commit(repo, "src/auth.py", "feat: add auth", minutes_ago=4320)
            self._commit(repo, "README.md", "docs: readme", minutes_ago=2880)
            self.assertEqual(len(self._auth_demands(repo)), 1)

    def test_commit_older_than_the_horizon_is_excluded(self):
        """The window still has a far edge — the cure is not 'scan everything'."""
        with tempfile.TemporaryDirectory() as td:
            repo = self._init_repo(Path(td))
            # 8 days > SCAN_HORIZON_HOURS (168h = 7 days)
            self._commit(repo, "src/auth.py", "feat: ancient auth",
                         minutes_ago=11520)
            self._commit(repo, "README.md", "docs: readme", minutes_ago=60)
            self.assertEqual(self._auth_demands(repo), [])

    def test_same_second_commit_still_detected(self):
        """The canonical test's own scenario, now deterministic."""
        with tempfile.TemporaryDirectory() as td:
            repo = self._init_repo(Path(td))
            self._commit(repo, "src/auth.py", "feat: add auth", minutes_ago=0)
            self._commit(repo, "README.md", "docs: readme", minutes_ago=0)
            self.assertEqual(len(self._auth_demands(repo)), 1)

    def test_positive_control_old_argument_finds_nothing(self):
        """Prove this file would go RED on the pre-cure code.

        Re-plants the defect by rewriting only the `--since=` token on the
        way to git, so the mechanism under test is the argument itself and
        not a stubbed return value.
        """
        with tempfile.TemporaryDirectory() as td:
            repo = self._init_repo(Path(td))
            self._commit(repo, "src/auth.py", "feat: add auth", minutes_ago=4320)
            self._commit(repo, "README.md", "docs: readme", minutes_ago=2880)

            self.assertEqual(len(self._auth_demands(repo)), 1, "cured code")

            original = self.scanner._git

            def planted(args, cwd=None):
                rewritten = [
                    "--since=%dh" % self.scanner.SCAN_HORIZON_HOURS
                    if isinstance(a, str) and a.startswith("--since=") else a
                    for a in args
                ]
                return original(rewritten, cwd=cwd)

            self.scanner._git = planted
            try:
                self.assertEqual(
                    self._auth_demands(repo), [],
                    "positive control did not reproduce the defect — the "
                    "regression this file guards is no longer being exercised",
                )
            finally:
                self.scanner._git = original


class TestControlledHistoryHorizon(GitRepoCase):
    """The 168h window spans a CONTROLLED multi-commit history.

    Rail P1 (S329): the previous form ran `git log` over the live checkout
    and required more than one commit. The validate and coverage jobs use
    depth-1 `actions/checkout`, which exposes at most one commit (zero for
    a merge head under `--no-merges`), so that assertion failed in CI for
    reasons unrelated to `_since_arg`. A temporary repository with known
    ages removes the checkout depth from the equation while keeping the
    defect signature: a collapsed window sees at most the newest commit.
    """

    def test_window_over_controlled_history_is_not_collapsed(self):
        scanner = _load_scanner()
        with tempfile.TemporaryDirectory() as td:
            repo = self._init_repo(Path(td))
            self._commit(repo, "a.txt", "aged-6-days", minutes_ago=6 * 24 * 60)
            self._commit(repo, "b.txt", "aged-2-days", minutes_ago=2 * 24 * 60)
            self._commit(repo, "c.txt", "right-now", minutes_ago=0)
            subjects = self._git_subjects(repo, scanner._since_arg(168))
            self.assertEqual(
                sorted(subjects), ["aged-2-days", "aged-6-days", "right-now"],
                "a 168h window must span every commit younger than 7 days; "
                "a collapsed window (the S329 defect) sees only right-now",
            )
            collapsed = self._git_subjects(repo, "--since=168h")
            self.assertTrue(
                set(collapsed) <= {"right-now"},
                "positive control: the bare-unit form still collapses to the "
                "current second (at most the newest commit): %r" % (collapsed,),
            )
