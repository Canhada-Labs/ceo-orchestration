#!/usr/bin/env python3
"""Hook profiler — measures per-hook invocation latency.

PLAN-010 Phase 2. Measures cold-start + warm-steady latency for all six
active hooks under an isolated tempdir (so we never mutate the real
audit log at ~/.claude/projects/ceo-orchestration/).

Reports p50 / p95 / p99 / IQR in either JSON or Markdown table format.
Measure-only: no thresholds embedded; ADR-024 governs when-to-gate.

Usage:
    hook-profiler.py [--home <path>] [--project-dir <path>]
                     [--samples N] [--warmup N]
                     [--format json|table]
                     [--hook NAME]   # filter to one hook (tests)

Exit codes:
    0  measurement completed (always — advisory forever, per ADR-019 §1)
    2  usage/arg error (N < warmup+1; unknown hook; missing fixture)

stdlib only; Python 3.9 compatible.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"
FIXTURES_DIR = HOOKS_DIR / "tests" / "fixtures" / "hooks"

# All six active hooks. Order is the column order in table output.
ALL_HOOKS: List[str] = [
    "check_agent_spawn",
    "audit_log",
    "check_bash_safety",
    "check_plan_edit",
    "check_read_injection",
    "check_canonical_edit",
]

# Subprocess timeout — 5s matches the confidence-gate hook's subprocess
# timeout. A hook that blows 5s is already pathological; we surface that
# as a "timeout" row instead of skewing percentiles.
HOOK_TIMEOUT_SECONDS = 5.0


# ---------------------------------------------------------------------------
# Perf-P1-001: per-tool-call scenario model
# ---------------------------------------------------------------------------
# Each scenario represents one adopter-realistic tool invocation. The list of
# hooks in `hooks=` fires SEQUENTIALLY (matching how Claude Code chains its
# PreToolUse / PostToolUse gates for a single tool call). The scenario
# wall-clock is the SUM of those per-hook latencies — which is what the agent
# actually experiences when Claude Code issues the tool call.
#
# Weights are drawn from Owner's realistic-session estimate: in a typical
# 100-tool-call session, roughly 15% are Edits, 35% Reads, 20% Writes, 20%
# Bash, 5% agent spawns, plus 5% "other" tool calls that only trip the
# generic `audit_log` PostToolUse emit path.
#
# Rationale for `hooks` mapping (grounded in .claude/settings.json):
#   - spawn        → check_agent_spawn (Pre) + audit_log (Post)
#   - Bash         → check_bash_safety (Pre) + audit_log (Post)
#   - Edit         → check_plan_edit (Pre) + check_canonical_edit (Pre)
#                    + audit_log (Post)
#   - Write        → check_plan_edit (Pre) + check_canonical_edit (Pre)
#                    + audit_log (Post)
#   - Read         → check_read_injection (Pre) + audit_log (Post)
PER_TOOL_SCENARIOS: List[Dict[str, object]] = [
    {
        "scenario": "spawn",
        "weight": 5,
        "hooks": ["check_agent_spawn", "audit_log"],
    },
    {
        "scenario": "Bash",
        "weight": 20,
        "hooks": ["check_bash_safety", "audit_log"],
    },
    {
        "scenario": "Edit",
        "weight": 15,
        "hooks": ["check_plan_edit", "check_canonical_edit", "audit_log"],
    },
    {
        "scenario": "Write",
        "weight": 20,
        "hooks": ["check_plan_edit", "check_canonical_edit", "audit_log"],
    },
    {
        "scenario": "Read",
        "weight": 35,
        "hooks": ["check_read_injection", "audit_log"],
    },
    {
        "scenario": "other",
        "weight": 5,
        "hooks": ["audit_log"],
    },
]


def _load_fixture_payload(hook_name: str) -> str:
    """Read the canonical in.json fixture for a hook. Raises if missing."""
    fixture = FIXTURES_DIR / hook_name / "in.json"
    if not fixture.is_file():
        raise FileNotFoundError(
            f"missing fixture for hook {hook_name!r}: {fixture}"
        )
    # Keep as raw text; the hook reads stdin JSON.
    return fixture.read_text(encoding="utf-8")


def _build_env(home: Path, project_dir: Path) -> Dict[str, str]:
    """Isolated env for the profiled-hook subprocess.

    Uses an **allowlist** base (NOT ``os.environ.copy()``) so no parent-
    process variable can leak into the subprocess. PLAN-019 Phase 1
    P0-04 traced 24KB of audit writes leaking into the real log when
    the previous copy-then-override pattern inherited test-time
    ``CLAUDE_PROJECT_DIR`` from TestEnvContext-enabled siblings before
    the explicit override ran.

    Allowlisted parent vars (pass-through iff present):

    - ``PATH`` — subprocess needs ``python3``.
    - ``LANG`` / ``LC_ALL`` — locale for deterministic stringification.
    - ``GITHUB_STEP_SUMMARY`` — CI summary sink (main() writes to it).

    Forced values:

    - ``HOME`` = ``str(home)`` — audit writes anchor here.
    - ``CLAUDE_PROJECT_DIR`` = ``str(project_dir)`` — routes emits.
    - ``NO_COLOR`` = ``"1"`` — disables ANSI overhead.

    Explicitly omitted:

    - ``CEO_CONFIDENCE_ENFORCE`` / ``CEO_CONFIDENCE_BYPASS`` — parent
      gate state must not influence profiled hooks.
    - All other parent env (e.g. test-injected ``$CEO_*``,
      ``$GITHUB_*`` other than STEP_SUMMARY, user-specific overrides).
    """
    env: Dict[str, str] = {
        "HOME": str(home),
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "NO_COLOR": "1",
    }
    # Allowlisted pass-through — only if present in parent env.
    for key in ("PATH", "LANG", "LC_ALL", "GITHUB_STEP_SUMMARY"):
        val = os.environ.get(key)
        if val is not None:
            env[key] = val
    # Guarantee PATH has something so subprocess can find python3 even
    # if parent has a pathological empty env (e.g. minimal Docker).
    if "PATH" not in env:
        env["PATH"] = "/usr/bin:/bin"
    return env


def _invoke_hook(hook_path: Path, payload: str, env: Dict[str, str]) -> int:
    """Invoke a hook once; return elapsed nanoseconds.

    Uses perf_counter_ns (monotonic, highest resolution). Returns -1 on
    timeout or nonzero-exit-due-to-infrastructure (caller filters).
    """
    t0 = time.perf_counter_ns()
    try:
        subprocess.run(
            [sys.executable, str(hook_path)],
            input=payload.encode("utf-8"),
            capture_output=True,
            timeout=HOOK_TIMEOUT_SECONDS,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return -1
    t1 = time.perf_counter_ns()
    return t1 - t0


def _percentile(sorted_ns: List[int], pct: float) -> int:
    """Nearest-rank percentile on a pre-sorted list of ints.

    stdlib `statistics.quantiles(n=100)` gives interpolated values; for
    latency reporting, nearest-rank is the conventional choice (matches
    what perf tooling like hey/vegeta emit).
    """
    if not sorted_ns:
        return 0
    # pct in [0, 100]
    if pct <= 0:
        return sorted_ns[0]
    if pct >= 100:
        return sorted_ns[-1]
    # Nearest rank: index = ceil(pct/100 * N) - 1
    import math
    n = len(sorted_ns)
    idx = max(0, min(n - 1, math.ceil(pct / 100.0 * n) - 1))
    return sorted_ns[idx]


def profile_hook(
    hook_name: str,
    samples: int,
    warmup: int,
    home: Path,
    project_dir: Path,
) -> Dict[str, object]:
    """Profile a single hook. Returns a dict with cold + warm stats."""
    hook_path = HOOKS_DIR / f"{hook_name}.py"
    if not hook_path.is_file():
        raise FileNotFoundError(f"hook script missing: {hook_path}")

    payload = _load_fixture_payload(hook_name)
    env = _build_env(home, project_dir)

    timings: List[int] = []
    timeouts = 0
    for i in range(samples):
        ns = _invoke_hook(hook_path, payload, env)
        if ns < 0:
            timeouts += 1
            continue
        timings.append(ns)

    # Cold start = first successful sample. Warm = samples[warmup:].
    cold_ns: Optional[int] = timings[0] if timings else None
    warm_timings = timings[warmup:] if len(timings) > warmup else []
    warm_sorted = sorted(warm_timings)

    p50 = _percentile(warm_sorted, 50)
    p95 = _percentile(warm_sorted, 95)
    p99 = _percentile(warm_sorted, 99)
    q1 = _percentile(warm_sorted, 25)
    q3 = _percentile(warm_sorted, 75)

    return {
        "hook": hook_name,
        "samples_requested": samples,
        "samples_ok": len(timings),
        "warmup_discarded": min(warmup, len(timings)),
        "timeouts": timeouts,
        "cold_start_ns": cold_ns,
        "warm_count": len(warm_timings),
        "warm_p50_ns": p50,
        "warm_p95_ns": p95,
        "warm_p99_ns": p99,
        "warm_iqr_ns": max(0, q3 - q1),
        "warm_min_ns": warm_sorted[0] if warm_sorted else 0,
        "warm_max_ns": warm_sorted[-1] if warm_sorted else 0,
    }


def profile_per_tool_call(
    samples: int,
    warmup: int,
    home: Path,
    project_dir: Path,
    scenarios: Optional[List[Dict[str, object]]] = None,
) -> Dict[str, object]:
    """Profile the AGGREGATE per-tool-call wall-clock (Perf-P1-001).

    For each sample we pick one scenario weighted by its ``weight``,
    execute every hook in its ``hooks`` list sequentially, and sum the
    per-hook latencies to produce the scenario wall-clock. That's what
    the agent's tool call actually costs end-to-end.

    Returns a dict with:
        - ``per_scenario``: list of dicts, one per scenario, with
          p50/p95/p99/min/max on the scenario wall-clock.
        - ``aggregate``: p50/p95/p99/min/max across every sample,
          weighted by the scenario-weight already (since we sampled
          according to weights).

    Warmup: the first ``warmup`` samples (regardless of scenario) are
    discarded — this avoids the first-fork cold-start dominating the
    distribution. Warmup is a global counter, not per-scenario.
    """
    if scenarios is None:
        scenarios = PER_TOOL_SCENARIOS

    # Build weighted cycle so we deterministically hit the advertised
    # distribution at N samples rather than depending on RNG convergence.
    # Cycle = [scenario_idx * weight_i] concatenated; we step through
    # with a rotating index. This keeps tests deterministic and avoids
    # a dependency on `random` (which is stdlib-fine but less robust
    # against sample-size quirks at small N).
    weighted_indices: List[int] = []
    for idx, sc in enumerate(scenarios):
        weighted_indices.extend([idx] * int(sc["weight"]))
    if not weighted_indices:
        raise ValueError("per-tool-call: scenarios list has zero total weight")

    env = _build_env(home, project_dir)

    # Preload fixtures + hook paths once. Failures short-circuit the run
    # so we don't silently skip a scenario.
    fixture_cache: Dict[str, str] = {}
    hook_path_cache: Dict[str, Path] = {}
    all_hooks_needed = {h for sc in scenarios for h in sc["hooks"]}  # type: ignore[union-attr]
    for h in all_hooks_needed:
        hook_path = HOOKS_DIR / f"{h}.py"
        if not hook_path.is_file():
            raise FileNotFoundError(f"hook script missing: {hook_path}")
        hook_path_cache[h] = hook_path
        fixture_cache[h] = _load_fixture_payload(h)

    # Per-scenario wall-clock samples (in ns).
    per_scenario_timings: Dict[str, List[int]] = {
        str(sc["scenario"]): [] for sc in scenarios
    }
    aggregate_timings: List[int] = []
    timeouts = 0

    # Step through the weighted cycle. For N samples we cover ⌈N/len(cycle)⌉
    # rotations of the cycle; the tail is truncated — every caller asked
    # for exactly N measurements.
    cycle_len = len(weighted_indices)
    for i in range(samples):
        sc_idx = weighted_indices[i % cycle_len]
        sc = scenarios[sc_idx]
        sc_name = str(sc["scenario"])
        total_ns = 0
        bad = False
        for hook_name in sc["hooks"]:  # type: ignore[union-attr]
            ns = _invoke_hook(
                hook_path_cache[hook_name],
                fixture_cache[hook_name],
                env,
            )
            if ns < 0:
                bad = True
                break
            total_ns += ns
        if bad:
            timeouts += 1
            continue
        # Warmup is global: first `warmup` successful samples are dropped.
        # Successful-only so a flaky warmup stretch doesn't consume the
        # warmup budget.
        if i >= warmup:
            per_scenario_timings[sc_name].append(total_ns)
            aggregate_timings.append(total_ns)

    # Per-scenario summary
    per_scenario: List[Dict[str, object]] = []
    for sc in scenarios:
        name = str(sc["scenario"])
        timings = sorted(per_scenario_timings[name])
        per_scenario.append({
            "scenario": name,
            "weight": sc["weight"],
            "hooks": list(sc["hooks"]),  # type: ignore[arg-type]
            "n": len(timings),
            "p50_ns": _percentile(timings, 50),
            "p95_ns": _percentile(timings, 95),
            "p99_ns": _percentile(timings, 99),
            "min_ns": timings[0] if timings else 0,
            "max_ns": timings[-1] if timings else 0,
        })

    agg_sorted = sorted(aggregate_timings)
    aggregate = {
        "n": len(agg_sorted),
        "p50_ns": _percentile(agg_sorted, 50),
        "p95_ns": _percentile(agg_sorted, 95),
        "p99_ns": _percentile(agg_sorted, 99),
        "min_ns": agg_sorted[0] if agg_sorted else 0,
        "max_ns": agg_sorted[-1] if agg_sorted else 0,
    }

    return {
        "mode": "per-tool-call",
        "samples_requested": samples,
        "timeouts": timeouts,
        "warmup_discarded": warmup,
        "per_scenario": per_scenario,
        "aggregate": aggregate,
    }


def _ns_to_ms(ns: Optional[int]) -> str:
    if ns is None:
        return "n/a"
    return f"{ns / 1_000_000:.2f}"


def render_table(results: List[Dict[str, object]]) -> str:
    """Markdown table. Columns: hook, cold(ms), p50, p95, p99, IQR, N."""
    lines = []
    lines.append(
        "| Hook | Cold (ms) | Warm p50 (ms) | Warm p95 (ms) | Warm p99 (ms) | IQR (ms) | N |"
    )
    lines.append(
        "|------|-----------|---------------|---------------|---------------|----------|---|"
    )
    for r in results:
        lines.append(
            "| {hook} | {cold} | {p50} | {p95} | {p99} | {iqr} | {n} |".format(
                hook=r["hook"],
                cold=_ns_to_ms(r["cold_start_ns"]),
                p50=_ns_to_ms(r["warm_p50_ns"]),
                p95=_ns_to_ms(r["warm_p95_ns"]),
                p99=_ns_to_ms(r["warm_p99_ns"]),
                iqr=_ns_to_ms(r["warm_iqr_ns"]),
                n=r["warm_count"],
            )
        )
    return "\n".join(lines) + "\n"


def _render_per_tool_call_table(ptc: Dict[str, object]) -> str:
    """Markdown table for per-tool-call output (Perf-P1-001)."""
    lines = []
    lines.append("## Per-tool-call wall-clock (Perf-P1-001)\n")
    lines.append(
        "| Scenario | Weight | Hooks | N | p50 (ms) | p95 (ms) | p99 (ms) |"
    )
    lines.append(
        "|----------|--------|-------|---|----------|----------|----------|"
    )
    per_scenario = ptc.get("per_scenario") or []  # type: ignore[assignment]
    for sc in per_scenario:  # type: ignore[assignment]
        lines.append(
            "| {scen} | {w} | {hooks} | {n} | {p50} | {p95} | {p99} |".format(
                scen=sc["scenario"],
                w=sc["weight"],
                hooks=",".join(sc["hooks"]),  # type: ignore[arg-type]
                n=sc["n"],
                p50=_ns_to_ms(sc["p50_ns"]),
                p95=_ns_to_ms(sc["p95_ns"]),
                p99=_ns_to_ms(sc["p99_ns"]),
            )
        )
    agg = ptc.get("aggregate") or {}
    lines.append("")
    lines.append("| AGGREGATE (weighted) | — | — | {n} | {p50} | {p95} | {p99} |".format(
        n=agg.get("n", 0),
        p50=_ns_to_ms(agg.get("p50_ns")),
        p95=_ns_to_ms(agg.get("p95_ns")),
        p99=_ns_to_ms(agg.get("p99_ns")),
    ))
    lines.append("")
    return "\n".join(lines) + "\n"


def render_json(results: List[Dict[str, object]]) -> str:
    """Render profiler `results` as a stable-key JSON payload for CI consumption."""
    payload = {
        "schema": "hook-profiler.v1",
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python": sys.version.split()[0],
        "ci": bool(os.environ.get("GITHUB_ACTIONS")),
        "results": results,
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _emit_slo_advisory(
    label: str,
    p95_ns: int,
    warn_ms: float,
    error_ms: float,
) -> None:
    """Emit [SLO-WARN] / [SLO-ERROR] to stderr based on p95.

    ADR-019 §1: profiler is advisory-forever. This function NEVER
    changes the exit code. Log annotations only. Zero or negative
    thresholds are treated as "disabled" and skipped.

    Precedence: SLO-ERROR (if triggered) supersedes SLO-WARN — we
    emit the highest-severity annotation and skip the lower one to
    keep the stderr log clean for CI grepping.
    """
    if p95_ns <= 0:
        return
    p95_ms = p95_ns / 1_000_000.0
    if error_ms > 0 and p95_ms >= error_ms:
        sys.stderr.write(
            f"[SLO-ERROR] {label}: warm-p95={p95_ms:.2f}ms "
            f">= {error_ms:.2f}ms threshold (advisory; exit unchanged)\n"
        )
        return
    if warn_ms > 0 and p95_ms >= warn_ms:
        sys.stderr.write(
            f"[SLO-WARN] {label}: warm-p95={p95_ms:.2f}ms "
            f">= {warn_ms:.2f}ms threshold (advisory; exit unchanged)\n"
        )


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse hook-profiler CLI arguments into a Namespace."""
    p = argparse.ArgumentParser(
        description="Profile all six hooks under an isolated tempdir."
    )
    p.add_argument("--home", type=Path, default=None,
                   help="Isolated HOME (default: auto tempdir).")
    p.add_argument("--project-dir", type=Path, default=None,
                   help="Isolated CLAUDE_PROJECT_DIR (default: same as --home).")
    p.add_argument("--samples", type=int, default=1000,
                   help="Total samples per hook (default 1000, min warmup+1).")
    p.add_argument("--warmup", type=int, default=100,
                   help="Samples to discard as warm-up (default 100).")
    p.add_argument("--format", choices=("json", "table"), default="table",
                   help="Output format.")
    p.add_argument("--hook", default=None,
                   help="Profile a single hook (default: all six).")
    p.add_argument(
        "--mode",
        choices=("per-hook", "per-tool-call"),
        default="per-hook",
        help=(
            "per-hook (default): legacy per-hook percentiles. "
            "per-tool-call: simulate an adopter tool-call distribution "
            "(spawn/Bash/Edit/Write/Read/other) and report aggregate "
            "wall-clock — Perf-P1-001."
        ),
    )
    # PLAN-019 F-CHAOS-4: advisory SLO thresholds.
    # We never change the exit code (ADR-019 §1 keeps the profiler
    # advisory forever) — but we annotate the output so operators can
    # grep for `[SLO-WARN]` / `[SLO-ERROR]` on the profiler stderr in
    # CI logs. Threshold unit is MILLISECONDS and compared against the
    # warm-p95 (per-hook mode) or the per-tool-call p95 aggregate
    # (per-tool-call mode). Negative / zero disables the advisory.
    p.add_argument(
        "--slo-warn-ms", type=float, default=0.0,
        help=(
            "Advisory: emit [SLO-WARN] to stderr if warm-p95 >= this "
            "threshold (ms). Exit code is UNCHANGED — this is purely a "
            "log annotation so operators can grep. 0 (default) disables."
        ),
    )
    p.add_argument(
        "--slo-error-ms", type=float, default=0.0,
        help=(
            "Advisory: emit [SLO-ERROR] to stderr if warm-p95 >= this "
            "threshold (ms). Exit code is UNCHANGED (ADR-019 §1 keeps "
            "the profiler advisory forever). 0 (default) disables."
        ),
    )
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — profile hook latency + emit a summary report."""
    args = parse_args(argv)

    # N >= warmup + 1 is a usage error — debate C7 mandates rejection, not
    # silent clamp, so callers can't ship a 10-sample "baseline".
    min_samples = max(args.warmup + 1, 100)
    if args.samples < min_samples:
        sys.stderr.write(
            f"usage: --samples must be >= {min_samples} (got {args.samples}). "
            f"A meaningful baseline needs at least warmup+1 and >=100 total.\n"
        )
        return 2

    hooks: List[str]
    if args.hook is None:
        hooks = list(ALL_HOOKS)
    else:
        if args.hook not in ALL_HOOKS:
            sys.stderr.write(
                f"usage: --hook must be one of {ALL_HOOKS} (got {args.hook!r})\n"
            )
            return 2
        hooks = [args.hook]

    # Set up isolation. If caller didn't pass --home, use a tempdir so we
    # never touch the real ~/.claude/projects/ audit log (debate C7).
    if args.home is None:
        tmp = tempfile.mkdtemp(prefix="hook-profiler-")
        home = Path(tmp)
        cleanup = True
    else:
        home = args.home
        home.mkdir(parents=True, exist_ok=True)
        cleanup = False
    project_dir = args.project_dir if args.project_dir else home
    project_dir.mkdir(parents=True, exist_ok=True)

    try:
        # ── Perf-P1-001: per-tool-call mode branches out early.
        if args.mode == "per-tool-call":
            try:
                ptc = profile_per_tool_call(
                    args.samples, args.warmup, home, project_dir,
                )
            except FileNotFoundError as e:
                sys.stderr.write(f"per-tool-call: {e}\n")
                return 2
            if args.format == "json":
                payload = {
                    "schema": "hook-profiler.v1",
                    "measured_at": time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                    ),
                    "python": sys.version.split()[0],
                    "ci": bool(os.environ.get("GITHUB_ACTIONS")),
                    "per_tool_call": ptc,
                }
                sys.stdout.write(
                    json.dumps(payload, indent=2, sort_keys=True) + "\n"
                )
            else:
                sys.stdout.write(_render_per_tool_call_table(ptc))
            # F-CHAOS-4: advisory SLO annotation on per-tool-call p95.
            _emit_slo_advisory(
                label="per-tool-call.aggregate",
                p95_ns=int(ptc.get("aggregate", {}).get("p95_ns", 0) or 0),  # type: ignore[union-attr]
                warn_ms=args.slo_warn_ms,
                error_ms=args.slo_error_ms,
            )
            return 0

        results: List[Dict[str, object]] = []
        for h in hooks:
            try:
                r = profile_hook(h, args.samples, args.warmup, home, project_dir)
            except FileNotFoundError as e:
                sys.stderr.write(f"skip {h}: {e}\n")
                return 2
            results.append(r)

        if args.format == "json":
            sys.stdout.write(render_json(results))
        else:
            sys.stdout.write(render_table(results))

        # F-CHAOS-4: per-hook advisory SLO annotation.
        for r in results:
            _emit_slo_advisory(
                label=str(r["hook"]),
                p95_ns=int(r.get("warm_p95_ns") or 0),
                warn_ms=args.slo_warn_ms,
                error_ms=args.slo_error_ms,
            )

        # CI summary emission — paths-filter runner will pick this up.
        gh_summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if gh_summary:
            try:
                with open(gh_summary, "a", encoding="utf-8") as fh:
                    fh.write("## Hook profile (advisory — ADR-024 state 0)\n\n")
                    fh.write(render_table(results))
                    fh.write("\n")
            except OSError:
                # fail-open on summary write
                pass
        return 0
    finally:
        if cleanup:
            # Best-effort cleanup; tempdir teardown is not load-bearing.
            import shutil
            shutil.rmtree(home, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
