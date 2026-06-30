"""PLAN-133 C3 — unit tests for the real-task reward benchmark.

NON-canonical test file. Lives under ``.claude/scripts/tests/`` so it rides the
existing scripts conftest (audit-dir isolation + sys.path seeding) and the
pinned ``testpaths`` — no new ``conftest.py`` is introduced (``.claude/**/
conftest.py`` is canonical-guarded, so a new eval conftest would require the
Owner-GPG ceremony; we avoid it entirely).

ALL tests run with a FAKE executor — **zero API calls, zero subscription quota**.
The whole runner pipeline (discover → setup → verify → worst-of-N → flaky →
quota gate → report) is exercised hermetically.

Env hygiene per [[feedback-test-canonicality-and-env-hygiene-for-new-tests]]:
``TestEnvContext`` for isolation + ``mock.patch.dict`` for env (never bare
``os.environ[...] =``).
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Resolve the eval package + modules by path (the eval dir is `.claude/eval`).
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent          # .claude/scripts
_CLAUDE_DIR = _SCRIPTS_DIR.parent                              # .claude
_HOOKS_DIR = _CLAUDE_DIR / "hooks"
_EVAL_DIR = _CLAUDE_DIR / "eval"
for _p in (str(_CLAUDE_DIR), str(_HOOKS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from _lib.testing import TestEnvContext  # noqa: E402


def _load(modname: str, relpath: str):
    spec = importlib.util.spec_from_file_location(modname, str(_EVAL_DIR / relpath))
    assert spec and spec.loader, f"could not load {relpath}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    spec.loader.exec_module(mod)
    return mod


# The runner imports `eval.tasks` and `eval.reporter` as a package; ensure the
# `eval` package resolves from `.claude/eval`. We import the package first.
import eval as _eval_pkg  # noqa: E402  (resolves to .claude/eval via sys.path)
import eval.tasks as tasks_pkg  # noqa: E402
runner = _load("eval.runner", "runner.py")
reporter = _load("eval.reporter", "reporter.py")


# ---------------------------------------------------------------------------
# Fake executors (zero quota)
# ---------------------------------------------------------------------------


class _NoopExecutor:
    """Does nothing to the workdir — the untouched setup tree is verified."""

    def run(self, *, task, workdir):
        return runner.ExecutorResult(True, tokens=10, turns=1, detail="noop")


class _SolvingExecutor:
    """Writes the golden solution per task id so the verifier scores ~1.0."""

    def __init__(self, solutions):
        self.solutions = solutions

    def run(self, *, task, workdir):
        files = self.solutions.get(task["id"], {})
        for rel, content in files.items():
            (Path(workdir) / rel).write_text(content, encoding="utf-8")
        return runner.ExecutorResult(True, tokens=123, turns=3, detail="solved")


class _FlakyExecutor:
    """Solves on even reps, leaves broken on odd reps → forces disagreement."""

    def __init__(self, solutions):
        self.solutions = solutions
        self._calls = {}

    def run(self, *, task, workdir):
        n = self._calls.get(task["id"], 0)
        self._calls[task["id"]] = n + 1
        if n % 2 == 0:
            for rel, content in self.solutions.get(task["id"], {}).items():
                (Path(workdir) / rel).write_text(content, encoding="utf-8")
        return runner.ExecutorResult(True, tokens=5, turns=1)


# Golden solutions keyed by task id (the minimal correct file).
GOLDEN = {
    "t01-fix-off-by-one": {
        "solution.py": "def sum_to_n(n):\n    return n * (n + 1) // 2\n"
    },
    "t02-implement-fizzbuzz": {
        "solution.py": (
            "def fizzbuzz(n):\n"
            "    out=[]\n"
            "    for i in range(1,n+1):\n"
            "        if i%15==0: out.append('FizzBuzz')\n"
            "        elif i%3==0: out.append('Fizz')\n"
            "        elif i%5==0: out.append('Buzz')\n"
            "        else: out.append(str(i))\n"
            "    return out\n"
        )
    },
    "t03-json-config-parse": {
        "solution.py": (
            "import json\n"
            "DEFAULTS={'host':'localhost','port':8080,'debug':False}\n"
            "def load_config(path):\n"
            "    cfg=dict(DEFAULTS)\n"
            "    try:\n"
            "        with open(path) as f: cfg.update(json.load(f))\n"
            "    except Exception: pass\n"
            "    return cfg\n"
        )
    },
    "t04-refactor-dedupe": {
        "solution.py": (
            "def _check(*vals):\n"
            "    if any(v<0 for v in vals): raise ValueError('negative')\n"
            "def area_rectangle(w,h):\n"
            "    _check(w,h); return w*h\n"
            "def area_square(s):\n"
            "    _check(s); return s*s\n"
        )
    },
    "t05-add-unit-test": {
        "test_solution.py": (
            "def test_basic():\n"
            "    assert parse_csv_line('a, b ,c') == ['a','b','c']\n"
            "def test_empty():\n"
            "    assert parse_csv_line('') == []\n"
        )
    },
    "t06-palindrome": {
        "solution.py": (
            "def is_palindrome(s):\n"
            "    t=[c.lower() for c in s if c.isalnum()]\n"
            "    return t==t[::-1]\n"
        )
    },
    "t07-sql-param-fix": {
        "solution.py": (
            "def build_query(user_id):\n"
            "    return ('SELECT * FROM users WHERE id = %s', (user_id,))\n"
        )
    },
    "t08-word-count": {
        "solution.py": (
            "import re\n"
            "def word_count(text):\n"
            "    d={}\n"
            "    for w in re.findall(r'[a-z0-9]+', text.lower()):\n"
            "        d[w]=d.get(w,0)+1\n"
            "    return d\n"
        )
    },
    "t09-readme-doc": {
        "README.md": (
            "# calc\n\nA tiny calculator module.\n\n## Usage\n\n```python\n"
            "from calc import add, subtract, multiply\n```\n\n"
            "Functions: add, subtract, multiply.\n"
        )
    },
    "t10-binary-search": {
        "solution.py": (
            "def binary_search(arr,target):\n"
            "    lo,hi=0,len(arr)-1\n"
            "    while lo<=hi:\n"
            "        mid=(lo+hi)//2\n"
            "        if arr[mid]==target: return mid\n"
            "        if arr[mid]<target: lo=mid+1\n"
            "        else: hi=mid-1\n"
            "    return -1\n"
        )
    },
}


# ---------------------------------------------------------------------------
# Task suite: discovery + schema + verifier correctness
# ---------------------------------------------------------------------------


class TestTaskSuite(TestEnvContext):
    def test_at_least_ten_tasks_discovered(self):
        all_tasks = tasks_pkg.load_all_tasks()
        self.assertGreaterEqual(len(all_tasks), 10, "C3 AC: >=10 real tasks")

    def test_every_task_validates(self):
        for t in tasks_pkg.load_all_tasks():
            errs = tasks_pkg.validate_task(t, source=t.get("id", "?"))
            self.assertEqual(errs, [], f"task {t.get('id')} invalid: {errs}")

    def test_task_ids_unique_and_sorted(self):
        ids = [t["id"] for t in tasks_pkg.load_all_tasks()]
        self.assertEqual(len(ids), len(set(ids)), "task ids must be unique")
        self.assertEqual(ids, sorted(ids), "load_all_tasks must return sorted")

    def test_golden_solution_scores_full_reward(self):
        # Every shipped task must be solvable to reward 1.0 by its golden file
        # (proves the verifier is satisfiable, not impossible).
        for t in tasks_pkg.load_all_tasks():
            with tempfile.TemporaryDirectory() as d:
                wd = Path(d)
                t["setup"](wd)
                for rel, content in GOLDEN.get(t["id"], {}).items():
                    (wd / rel).write_text(content, encoding="utf-8")
                reward = tasks_pkg.clamp_reward(t["verify"](wd))
                self.assertGreaterEqual(
                    reward, 0.99, f"golden {t['id']} scored {reward}, expected ~1.0"
                )

    def test_untouched_setup_scores_below_full(self):
        # The starting (buggy/stub) tree must NOT already pass — otherwise the
        # task measures nothing (the PLAN-128 0/0/0 trap).
        for t in tasks_pkg.load_all_tasks():
            with tempfile.TemporaryDirectory() as d:
                wd = Path(d)
                t["setup"](wd)
                reward = tasks_pkg.clamp_reward(t["verify"](wd))
                self.assertLess(
                    reward, 0.99, f"untouched {t['id']} already scored {reward}"
                )

    def test_verifier_failsafe_on_empty_workdir(self):
        # A verifier must never raise on a missing tree — it returns a reward.
        for t in tasks_pkg.load_all_tasks():
            with tempfile.TemporaryDirectory() as d:
                reward = tasks_pkg.clamp_reward(t["verify"](Path(d)))
                self.assertGreaterEqual(reward, 0.0)
                self.assertLessEqual(reward, 1.0)

    def test_clamp_reward_bounds(self):
        self.assertEqual(tasks_pkg.clamp_reward(2.0), 1.0)
        self.assertEqual(tasks_pkg.clamp_reward(-1.0), 0.0)
        self.assertEqual(tasks_pkg.clamp_reward("x"), 0.0)
        self.assertEqual(tasks_pkg.clamp_reward(float("nan")), 0.0)
        self.assertEqual(tasks_pkg.clamp_reward(float("inf")), 0.0)
        self.assertEqual(tasks_pkg.clamp_reward(0.5), 0.5)

    def test_validate_task_rejects_bad_shapes(self):
        self.assertTrue(tasks_pkg.validate_task({}, source="x"))
        self.assertTrue(tasks_pkg.validate_task("not a dict", source="x"))
        bad = {"id": "", "title": "t", "category": "bugfix",
               "difficulty": "easy", "instruction": "i",
               "setup": lambda w: None, "verify": lambda w: 0.0}
        self.assertTrue(tasks_pkg.validate_task(bad))  # empty id
        bad2 = dict(bad, id="ok", category="nonsense")
        self.assertTrue(tasks_pkg.validate_task(bad2))  # bad category


# ---------------------------------------------------------------------------
# Runner: worst-of-N + flaky reuse, serial, quota gate
# ---------------------------------------------------------------------------


class TestRunnerAggregation(TestEnvContext):
    def test_solving_executor_passes_all(self):
        all_tasks = tasks_pkg.load_all_tasks()
        results = runner.run_suite(
            all_tasks, executor=_SolvingExecutor(GOLDEN), repetitions=1
        )
        self.assertEqual(results["task_count"], len(all_tasks))
        self.assertEqual(results["status_counts"]["pass"], len(all_tasks))
        self.assertEqual(results["mean_reward"], 1.0)
        self.assertEqual(results["flaky_count"], 0)

    def test_noop_executor_does_not_pass(self):
        all_tasks = tasks_pkg.load_all_tasks()
        results = runner.run_suite(
            all_tasks, executor=_NoopExecutor(), repetitions=1
        )
        # Untouched trees must not all PASS.
        self.assertLess(results["status_counts"]["pass"], len(all_tasks))

    def test_worst_of_n_takes_minimum(self):
        # Flaky executor: rep0 solves, rep1 broken → worst-of-2 == broken reward.
        with mock.patch.dict("os.environ", {"CEO_BENCH_AGGREGATION": "worst"}):
            one = [t for t in tasks_pkg.load_all_tasks() if t["id"] == "t01-fix-off-by-one"]
            results = runner.run_suite(
                one, executor=_FlakyExecutor(GOLDEN), repetitions=2
            )
            task = results["tasks"][0]
            # worst of {1.0, 0.0} == 0.0
            self.assertEqual(task["reward"], 0.0)
            self.assertEqual(task["aggregation"], "worst")

    def test_flaky_flag_on_disagreement(self):
        with mock.patch.dict("os.environ", {"CEO_BENCH_AGGREGATION": "worst"}):
            one = [t for t in tasks_pkg.load_all_tasks() if t["id"] == "t01-fix-off-by-one"]
            results = runner.run_suite(
                one, executor=_FlakyExecutor(GOLDEN), repetitions=2
            )
            self.assertTrue(results["tasks"][0]["flaky"], "reps disagree → flaky")
            self.assertEqual(results["flaky_count"], 1)

    def test_median_escape_hatch(self):
        # 3 reps: solve, broken, solve → median == solved reward (1.0) but worst == 0.
        class _Pattern:
            def __init__(self, sols):
                self.sols = sols
                self.n = 0

            def run(self, *, task, workdir):
                solve = self.n in (0, 2)
                self.n += 1
                if solve:
                    for rel, c in self.sols.get(task["id"], {}).items():
                        (Path(workdir) / rel).write_text(c, encoding="utf-8")
                return runner.ExecutorResult(True)

        one = [t for t in tasks_pkg.load_all_tasks() if t["id"] == "t01-fix-off-by-one"]
        with mock.patch.dict("os.environ", {"CEO_BENCH_AGGREGATION": "median"}):
            res = runner.run_suite(one, executor=_Pattern(GOLDEN), repetitions=3)
            self.assertEqual(res["tasks"][0]["reward"], 1.0)
        with mock.patch.dict("os.environ", {"CEO_BENCH_AGGREGATION": "worst"}):
            res2 = runner.run_suite(one, executor=_Pattern(GOLDEN), repetitions=3)
            self.assertEqual(res2["tasks"][0]["reward"], 0.0)

    def test_bad_aggregation_env_fails_open_to_worst(self):
        with mock.patch.dict("os.environ", {"CEO_BENCH_AGGREGATION": "garbage"}):
            self.assertEqual(runner.resolve_aggregation(), "worst")

    def test_serial_no_thread_or_process_pool(self):
        # The runner must run tasks serially — assert it never spins a pool.
        with mock.patch("concurrent.futures.ThreadPoolExecutor") as tpe, \
             mock.patch("concurrent.futures.ProcessPoolExecutor") as ppe:
            runner.run_suite(
                tasks_pkg.load_all_tasks(), executor=_NoopExecutor(), repetitions=1
            )
            tpe.assert_not_called()
            ppe.assert_not_called()

    def test_trial_status_taxonomy(self):
        self.assertEqual(runner._trial_status(1.0), "pass")
        self.assertEqual(runner._trial_status(0.0), "fail")
        self.assertEqual(runner._trial_status(0.5), "partial")


class TestQuotaGate(TestEnvContext):
    def test_quota_cap_blocks_oversized_budget(self):
        allowed, msg = runner.check_quota(
            10, 5, cap_attempts=30, allow_expensive=False
        )
        self.assertFalse(allowed)
        self.assertIn("quota cap", msg)

    def test_quota_cap_allows_within_budget(self):
        allowed, _ = runner.check_quota(
            10, 2, cap_attempts=30, allow_expensive=False
        )
        self.assertTrue(allowed)

    def test_allow_expensive_overrides_cap(self):
        allowed, _ = runner.check_quota(
            100, 100, cap_attempts=30, allow_expensive=True
        )
        self.assertTrue(allowed)


# ---------------------------------------------------------------------------
# CLI: --skip-if-no-key, key gate, hermeticity
# ---------------------------------------------------------------------------


class TestRunnerCLI(TestEnvContext):
    def test_skip_if_no_key_exits_zero(self):
        env = {k: v for k, v in __import__("os").environ.items()
               if k != "ANTHROPIC_API_KEY"}
        with mock.patch.dict("os.environ", env, clear=True):
            rc = runner.main(["--skip-if-no-key"])
            self.assertEqual(rc, 0)

    def test_no_key_no_skip_exits_two(self):
        env = {k: v for k, v in __import__("os").environ.items()
               if k != "ANTHROPIC_API_KEY"}
        with mock.patch.dict("os.environ", env, clear=True):
            rc = runner.main([])
            self.assertEqual(rc, 2)

    def test_quota_cap_blocks_in_cli(self):
        # With a key present but a tiny cap, the planned budget exceeds it.
        with mock.patch.dict("os.environ", {"ANTHROPIC_API_KEY": "x"}):
            rc = runner.main(["--quota-cap-attempts", "1", "--repetitions", "5"])
            self.assertEqual(rc, 2)

    def test_no_anthropic_client_constructed_in_full_run(self):
        # HERMETICITY (mirrors the C5 AC): the runner pipeline must construct no
        # Anthropic client. We assert `anthropic` is never imported by the run.
        import builtins
        real_import = builtins.__import__
        offenders = []

        def _guard(name, *a, **k):
            if name == "anthropic" or name.startswith("anthropic."):
                offenders.append(name)
            return real_import(name, *a, **k)

        with mock.patch("builtins.__import__", side_effect=_guard):
            runner.run_suite(
                tasks_pkg.load_all_tasks(), executor=_NoopExecutor(), repetitions=1
            )
        self.assertEqual(offenders, [], f"runner imported anthropic: {offenders}")


class TestDefaultExecutorIsInert(TestEnvContext):
    def test_default_executor_noops_without_launcher(self):
        # OrchestrationExecutor must NOT spawn anything when CEO_EVAL_EXEC_CMD
        # is unset — it returns a not-ok result, never a subprocess (rite §2).
        env = {k: v for k, v in __import__("os").environ.items()
               if k != "CEO_EVAL_EXEC_CMD"}
        with mock.patch.dict("os.environ", env, clear=True), \
             mock.patch("subprocess.run") as sp:
            ex = runner.OrchestrationExecutor()
            with tempfile.TemporaryDirectory() as d:
                res = ex.run(task={"instruction": "x"}, workdir=Path(d))
            self.assertFalse(res.ok)
            sp.assert_not_called()


# ---------------------------------------------------------------------------
# Reporter
# ---------------------------------------------------------------------------


class TestReporter(TestEnvContext):
    def _sample(self):
        return runner.run_suite(
            tasks_pkg.load_all_tasks(), executor=_SolvingExecutor(GOLDEN), repetitions=1
        )

    def test_markdown_has_harbor_columns(self):
        md = reporter.emit_markdown(self._sample())
        for col in ("Reward", "Status", "Attempts", "Tokens", "Turns", "Flaky"):
            self.assertIn(col, md)
        self.assertIn("Quota (cost)", md)  # cost == quota, not dollars
        self.assertIn("Mean reward", md)

    def test_markdown_deterministic(self):
        s = self._sample()
        self.assertEqual(reporter.emit_markdown(s), reporter.emit_markdown(s))

    def test_reporter_json_roundtrip(self):
        s = self._sample()
        import json
        self.assertEqual(json.loads(reporter.emit_json(s))["task_count"], s["task_count"])

    def test_reporter_no_anthropic_import(self):
        import builtins
        real_import = builtins.__import__
        offenders = []

        def _guard(name, *a, **k):
            if name == "anthropic" or name.startswith("anthropic."):
                offenders.append(name)
            return real_import(name, *a, **k)

        with mock.patch("builtins.__import__", side_effect=_guard):
            reporter.emit_markdown(self._sample())
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
