#!/usr/bin/env python3
"""runner.py — PLAN-133 C3 real-task reward benchmark runner (NIGHTLY/on-demand).

Runs a suite of ~10 real software-engineering tasks. For each task the runner:

  1. creates an isolated temp working directory,
  2. calls the task's ``setup(workdir)`` to lay down the starting files,
  3. drives the CEO orchestration ``repetitions`` times to attempt the
     ``instruction`` (**this spends real subscription quota** — it is NOT free
     and NOT $0; that is why this runner is a nightly/on-demand job, never a
     per-push CI step — it would blow the S220 17→12min push budget),
  4. runs the task's deterministic ``verify(workdir)`` after each attempt to get
     a scalar ``reward`` in ``[0, 1]``,
  5. aggregates the N per-attempt rewards with **worst-of-N** (reusing the C1
     aggregation contract) and flags the task ``flaky`` when its attempts
     disagree on the pass threshold.

## Safety / cost discipline (the C3 ACs)

- ``--skip-if-no-key``: exit 0 with ``SKIPPED`` when ``ANTHROPIC_API_KEY`` is
  unset, so the nightly job is a no-op rather than a failure on a runner that
  has no credentials. Without the flag and without a key, exit 2.
- **Per-run quota cap** (``--max-attempts`` × ``--max-tokens`` ceiling, plus an
  explicit ``--quota-cap-attempts`` hard ceiling on total task attempts). The
  runner refuses to start if the planned attempt budget exceeds the cap unless
  ``--allow-expensive`` is passed. This is the quota gate; cost is reported as
  attempts + tokens (cost == subscription quota, NOT dollars — S220/ADR-144).
- **serial**: tasks run one at a time (the orchestration itself fans out
  internally; running whole tasks in parallel would multiply peak quota draw and
  make the cap unenforceable). The runner never parallelizes tasks.
- **worst-of-N + flaky** reuse the C1 contract (see ``_load_c1_aggregation``):
  same ``CEO_BENCH_AGGREGATION`` env knob (default ``worst``), same flaky rule.

## Pluggable executor (hermetic testing)

The actual orchestration call lives behind an ``Executor`` protocol. The default
``OrchestrationExecutor`` shells out to the CEO loop; tests inject a fake
executor that mutates the workdir deterministically, so the entire runner —
setup, verify, aggregation, reporting, quota gate — is exercised with **zero API
calls and zero quota** in unit tests.

## Audit emit (fail-open, optional)

When the closed-enum ``eval_task_completed`` action is registered in
``_lib/audit_emit._KNOWN_ACTIONS`` (staged as a canonical edit in
``PLAN-133/staged/C3.proposal.md``), the runner emits one event per task with
int-only fields (reward in basis points, attempt count, flaky flag). Until that
canonical edit lands, ``emit_generic`` no-ops on the unknown action (breadcrumb
+ silent return) — so the runner is correct both before and after the GPG
ceremony, and never blocks on the audit layer.

## CLI

    python3 .claude/eval/runner.py [options]

      --repetitions N         attempts per task (default 1; >1 enables flaky)
      --max-tokens N          output-token ceiling per attempt (default 4000)
      --quota-cap-attempts N  hard ceiling on total attempts (default 30)
      --allow-expensive       bypass the quota cap
      --skip-if-no-key        exit 0 SKIPPED if ANTHROPIC_API_KEY unset
      --task ID               run only this task id (repeatable)
      --output-json PATH      write the full results JSON here
      --json                  print results JSON to stdout
      --timeout-s N           per-attempt orchestration timeout (default 600)
      --floor F               overall mean reward below F -> exit 1

Stdlib only. py>=3.9.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

_EVAL_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _EVAL_DIR.parent.parent
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_EVAL_DIR.parent) not in sys.path:
    # Make `.claude` importable so `eval.tasks` resolves as a package.
    sys.path.insert(0, str(_EVAL_DIR.parent))
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_REPETITIONS = 1
DEFAULT_MAX_TOKENS = 4000
DEFAULT_QUOTA_CAP_ATTEMPTS = 30
DEFAULT_TIMEOUT_S = 600
DEFAULT_AGGREGATION = "worst"

# Trial status taxonomy (harbor-style). A task is `pass` at or above the pass
# threshold, `fail` at or below the fail threshold, `partial` in between.
PASS_THRESHOLD = 0.99   # reward must be (essentially) perfect to PASS a real task
FAIL_THRESHOLD = 0.01   # reward at/below this is a clean FAIL


# ---------------------------------------------------------------------------
# C1 aggregation reuse (worst-of-N + flaky) — single source of truth
# ---------------------------------------------------------------------------


def _load_c1_aggregation() -> Tuple[Callable, Callable, Callable]:
    """Import the C1 aggregation helpers from run-skill-benchmark.py.

    Returns ``(aggregate_scores, detect_flaky, resolve_aggregation)``. The
    benchmark script is hyphenated so it is loaded via importlib by path. On any
    import failure the runner falls back to inline equivalents (fail-open) so a
    relocation of the C1 script never breaks the eval runner — but the C1 module
    is the canonical source when present (no second divergent worst-of-N rule).
    """
    rsb_path = _REPO_ROOT / ".claude" / "scripts" / "run-skill-benchmark.py"
    try:
        spec = importlib.util.spec_from_file_location("run_skill_benchmark_c3", str(rsb_path))
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.aggregate_scores, mod.detect_flaky, mod._resolve_aggregation
    except Exception:
        pass

    # Fallback (kept behavior-identical to C1).
    def _agg(scores: List[float], *, mode: str = DEFAULT_AGGREGATION) -> float:
        if not scores:
            return 0.0
        ordered = sorted(scores)
        if mode == "median":
            return ordered[len(ordered) // 2]
        return ordered[0]

    def _flaky(run_passed: List[bool]) -> bool:
        if len(run_passed) < 2:
            return False
        return any(run_passed) and not all(run_passed)

    def _resolve() -> str:
        raw = os.environ.get("CEO_BENCH_AGGREGATION", "").strip().lower()
        return raw if raw in ("worst", "median") else DEFAULT_AGGREGATION

    return _agg, _flaky, _resolve


aggregate_scores, detect_flaky, resolve_aggregation = _load_c1_aggregation()


# ---------------------------------------------------------------------------
# Executor protocol
# ---------------------------------------------------------------------------


class ExecutorResult:
    """Outcome of one orchestration attempt at a task.

    ``ok`` is whether the orchestration completed (NOT whether the task verified
    — verification is the runner's job). ``tokens`` / ``turns`` are advisory
    telemetry for the harbor-style cost row (best-effort; 0 if unknown).
    """

    __slots__ = ("ok", "tokens", "turns", "detail")

    def __init__(self, ok: bool, *, tokens: int = 0, turns: int = 0, detail: str = ""):
        self.ok = bool(ok)
        self.tokens = int(tokens)
        self.turns = int(turns)
        self.detail = str(detail)


class OrchestrationExecutor:
    """Default executor: drive the CEO orchestration against a task workdir.

    This is the ONLY place that spends real subscription quota. It shells out to
    the orchestration entrypoint with the task instruction and a working
    directory, with a hard timeout. The exact command is resolved from
    ``CEO_EVAL_EXEC_CMD`` (a shell template with ``{workdir}`` and ``{prompt_file}``
    placeholders) so an operator can wire it to ``claude -p`` / a headless CLI
    without this file hardcoding a launcher. When the env var is unset the
    executor returns a not-ok result with a clear breadcrumb (the runner then
    records the attempt as a failed orchestration, reward from verify == whatever
    the untouched setup tree scores). It NEVER fetches a URL and NEVER runs an
    aaif-goose binary (rite §2).
    """

    def __init__(self, *, timeout_s: int = DEFAULT_TIMEOUT_S, max_tokens: int = DEFAULT_MAX_TOKENS):
        self.timeout_s = int(timeout_s)
        self.max_tokens = int(max_tokens)

    def run(self, *, task: Dict[str, Any], workdir: Path) -> ExecutorResult:
        cmd_template = os.environ.get("CEO_EVAL_EXEC_CMD", "").strip()
        if not cmd_template:
            return ExecutorResult(
                False,
                detail="CEO_EVAL_EXEC_CMD unset — no orchestration launcher configured",
            )
        prompt_file = workdir / "_eval_instruction.txt"
        try:
            prompt_file.write_text(str(task.get("instruction", "")), encoding="utf-8")
        except Exception as e:
            return ExecutorResult(False, detail=f"could not write prompt: {e}")
        cmd = cmd_template.format(
            workdir=str(workdir),
            prompt_file=str(prompt_file),
            max_tokens=self.max_tokens,
        )
        try:
            proc = subprocess.run(  # noqa: S602 — operator-configured launcher, not user input
                cmd,
                shell=True,
                cwd=str(workdir),
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
            )
            return ExecutorResult(
                proc.returncode == 0,
                detail=(proc.stderr or "")[:200],
            )
        except subprocess.TimeoutExpired:
            return ExecutorResult(False, detail=f"timeout after {self.timeout_s}s")
        except Exception as e:  # pragma: no cover — defensive
            return ExecutorResult(False, detail=f"exec error: {e}")


# ---------------------------------------------------------------------------
# Core run logic
# ---------------------------------------------------------------------------


def _trial_status(reward: float) -> str:
    """Map a scalar reward to the harbor-style trial status."""
    if reward >= PASS_THRESHOLD:
        return "pass"
    if reward <= FAIL_THRESHOLD:
        return "fail"
    return "partial"


def run_one_task(
    task: Dict[str, Any],
    *,
    executor: Any,
    repetitions: int,
) -> Dict[str, Any]:
    """Run a single task ``repetitions`` times; aggregate worst-of-N + flaky.

    Returns a per-task result dict. Each attempt gets a fresh temp workdir (the
    task's setup re-runs), the executor attempts the instruction, and the task's
    deterministic verifier scores the tree. Never raises — a verifier or setup
    failure becomes a 0.0 attempt with an ``error`` breadcrumb.
    """
    # Late import so a partially-broken tasks package can't crash module import.
    from eval.tasks import clamp_reward  # type: ignore

    attempts: List[Dict[str, Any]] = []
    mode = resolve_aggregation()
    for rep in range(max(1, repetitions)):
        workdir = Path(tempfile.mkdtemp(prefix=f"ceo-eval-{task['id']}-"))
        attempt: Dict[str, Any] = {"rep": rep}
        try:
            task["setup"](workdir)
            ex = executor.run(task=task, workdir=workdir)
            attempt["orchestration_ok"] = ex.ok
            attempt["tokens"] = ex.tokens
            attempt["turns"] = ex.turns
            attempt["detail"] = ex.detail
            try:
                raw_reward = task["verify"](workdir)
            except Exception as e:  # verifier must be fail-safe, but double-guard
                raw_reward = 0.0
                attempt["verify_error"] = str(e)[:200]
            reward = clamp_reward(raw_reward)
            attempt["reward"] = reward
            attempt["passed"] = reward >= PASS_THRESHOLD
        except Exception as e:  # setup failure
            attempt["reward"] = 0.0
            attempt["passed"] = False
            attempt["error"] = str(e)[:200]
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
        attempts.append(attempt)

    rewards = [a.get("reward", 0.0) for a in attempts]
    run_passed = [bool(a.get("passed", False)) for a in attempts]
    aggregated = aggregate_scores(rewards, mode=mode)
    flaky = detect_flaky(run_passed)
    total_tokens = sum(int(a.get("tokens", 0)) for a in attempts)
    total_turns = sum(int(a.get("turns", 0)) for a in attempts)

    return {
        "id": task["id"],
        "title": task.get("title", ""),
        "category": task.get("category", ""),
        "difficulty": task.get("difficulty", ""),
        "reward": round(aggregated, 4),
        "aggregation": mode,
        "flaky": flaky,
        "status": _trial_status(aggregated),
        "attempts": len(attempts),
        "raw_rewards": [round(r, 4) for r in rewards],
        "tokens": total_tokens,
        "turns": total_turns,
        "per_attempt": attempts,
    }


def run_suite(
    tasks: List[Dict[str, Any]],
    *,
    executor: Any,
    repetitions: int,
) -> Dict[str, Any]:
    """Run the whole suite **serially** and assemble the aggregate result.

    Serial by contract (the C3 AC): tasks never run in parallel — the
    orchestration fans out internally and running whole tasks concurrently would
    multiply peak quota draw and defeat the cap.
    """
    per_task: List[Dict[str, Any]] = []
    for task in tasks:  # SERIAL — do not parallelize (C3 AC).
        per_task.append(run_one_task(task, executor=executor, repetitions=repetitions))

    rewards = [t["reward"] for t in per_task]
    mean_reward = round(sum(rewards) / len(rewards), 4) if rewards else 0.0
    status_counts = {"pass": 0, "partial": 0, "fail": 0}
    for t in per_task:
        status_counts[t["status"]] = status_counts.get(t["status"], 0) + 1
    flaky_count = sum(1 for t in per_task if t["flaky"])

    return {
        "suite": "plan-133-c3-real-tasks",
        "task_count": len(per_task),
        "repetitions": repetitions,
        "aggregation": resolve_aggregation(),
        "mean_reward": mean_reward,
        "status_counts": status_counts,
        "flaky_count": flaky_count,
        "total_tokens": sum(t["tokens"] for t in per_task),
        "total_turns": sum(t["turns"] for t in per_task),
        "tasks": per_task,
        "timestamp": _now_iso(),
    }


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Quota gate
# ---------------------------------------------------------------------------


def check_quota(
    n_tasks: int,
    repetitions: int,
    *,
    cap_attempts: int,
    allow_expensive: bool,
) -> Tuple[bool, str]:
    """Return ``(allowed, message)`` for the planned attempt budget.

    The budget is ``n_tasks * repetitions`` orchestration attempts. Each attempt
    is real subscription quota. The gate refuses to start when the budget
    exceeds ``cap_attempts`` unless ``allow_expensive`` is set. Cost is reported
    as ATTEMPTS (== quota draw), not dollars (S220/ADR-144 — cost is quota).
    """
    planned = n_tasks * max(1, repetitions)
    if planned > cap_attempts and not allow_expensive:
        return (
            False,
            (
                f"planned {planned} orchestration attempts "
                f"({n_tasks} tasks x {repetitions} reps) > quota cap {cap_attempts}. "
                f"Pass --allow-expensive to override (spends real subscription quota)."
            ),
        )
    return (True, f"planned {planned} attempts within cap {cap_attempts}")


# ---------------------------------------------------------------------------
# Audit emit (fail-open; no-op until the staged canonical action lands)
# ---------------------------------------------------------------------------


def emit_task_events(results: Dict[str, Any]) -> int:
    """Emit one ``eval_task_completed`` event per task. Fail-open; returns count.

    Int-only fields (reward in basis points, attempts, flaky as 0/1) so the
    no-float HMAC invariant holds. Uses ``emit_generic``; until the closed-enum
    action is registered (staged C3 canonical edit) every call is a silent
    no-op (unknown-action breadcrumb), so this is safe to call pre-ceremony.
    """
    try:
        from _lib.audit_emit import emit_generic  # type: ignore
    except Exception:
        return 0
    emitted = 0
    for t in results.get("tasks", []):
        try:
            emit_generic(
                "eval_task_completed",
                task_id=str(t.get("id", "")),
                reward_bps=max(0, min(1000, int(round(float(t.get("reward", 0.0)) * 1000)))),
                status=str(t.get("status", "")),
                attempts=int(t.get("attempts", 0)),
                flaky=1 if t.get("flaky") else 0,
                tokens=int(t.get("tokens", 0)),
                turns=int(t.get("turns", 0)),
            )
            emitted += 1
        except Exception:
            continue
    return emitted


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="runner.py",
        description="PLAN-133 C3 real-task reward benchmark (nightly/on-demand)",
    )
    p.add_argument("--repetitions", type=int, default=DEFAULT_REPETITIONS,
                   help="attempts per task (default 1; >1 enables flaky)")
    p.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    p.add_argument("--quota-cap-attempts", type=int, default=DEFAULT_QUOTA_CAP_ATTEMPTS,
                   help="hard ceiling on total orchestration attempts")
    p.add_argument("--allow-expensive", action="store_true",
                   help="bypass the quota cap (spends real subscription quota)")
    p.add_argument("--skip-if-no-key", action="store_true",
                   help="exit 0 SKIPPED if ANTHROPIC_API_KEY unset")
    p.add_argument("--task", action="append", default=None, dest="only_tasks",
                   help="run only this task id (repeatable)")
    p.add_argument("--output-json", default=None)
    p.add_argument("--json", dest="as_json", action="store_true")
    p.add_argument("--timeout-s", type=int, default=DEFAULT_TIMEOUT_S)
    p.add_argument("--floor", type=float, default=None,
                   help="overall mean reward below this fails the run (exit 1)")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # --skip-if-no-key gate (real quota requires a key).
    if not os.environ.get("ANTHROPIC_API_KEY"):
        if args.skip_if_no_key:
            print("SKIPPED: ANTHROPIC_API_KEY not set (nightly no-op)")
            return 0
        print(
            "ERROR: ANTHROPIC_API_KEY not set. This benchmark spends real "
            "subscription quota. Set the key or pass --skip-if-no-key.",
            file=sys.stderr,
        )
        return 2

    # Discover tasks.
    try:
        from eval.tasks import load_all_tasks  # type: ignore
    except Exception as e:
        print(f"ERROR: could not load task suite: {e}", file=sys.stderr)
        return 2
    tasks = load_all_tasks()
    if args.only_tasks:
        wanted = set(args.only_tasks)
        tasks = [t for t in tasks if t["id"] in wanted]
    if not tasks:
        print("ERROR: no tasks to run", file=sys.stderr)
        return 2

    # Quota gate.
    allowed, msg = check_quota(
        len(tasks), args.repetitions,
        cap_attempts=args.quota_cap_attempts,
        allow_expensive=args.allow_expensive,
    )
    print(f"[eval-runner] quota: {msg}", file=sys.stderr)
    if not allowed:
        print(f"ERROR: {msg}", file=sys.stderr)
        return 2

    executor = OrchestrationExecutor(timeout_s=args.timeout_s, max_tokens=args.max_tokens)

    t0 = time.monotonic()
    results = run_suite(tasks, executor=executor, repetitions=args.repetitions)
    results["duration_s"] = round(time.monotonic() - t0, 2)

    emit_task_events(results)

    # Render (delegate to reporter for the human view; JSON for machines).
    try:
        from eval.reporter import emit_markdown  # type: ignore
        print(emit_markdown(results))
    except Exception:
        # Reporter is best-effort; JSON still available.
        print(f"[eval-runner] mean_reward={results['mean_reward']} "
              f"{results['status_counts']}")
    if args.as_json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    if args.output_json:
        Path(args.output_json).write_text(
            json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    if args.floor is not None and results["mean_reward"] < args.floor:
        print(
            f"FLOOR: mean reward {results['mean_reward']} < floor {args.floor}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
