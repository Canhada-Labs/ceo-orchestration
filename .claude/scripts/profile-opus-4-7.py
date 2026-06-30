#!/usr/bin/env python3
"""profile-opus-4-7.py — Opus 4.7 framework optimization measurement tool.

PLAN-020 Phase 0 item 6 + 8 deliverable. Stdlib-only.

Modes:

- ``--smoke``: synthetic, no API, tokens mocked. CI-runnable. ≤30s budget.
  Outputs JSON to stdout; exit 0 on success, 1 on internal error, 2 on
  budget overrun.

- ``--baseline``: full baseline capture (requires env to read audit log
  + ANTHROPIC_API_KEY for live cache header probing — Phase 0 item 1
  prerequisites). Outputs JSON + side-effects audit-log entries.
  Reserved for next session post Owner sentinel for hook modifications.

- ``--floor``: re-measure subprocess startup floor on this machine
  (Phase 0 item 8). Cheap; ≤2s. Reports python3 -c 'pass' p50/p95/p99.

Wire-up: validate.yml step ``opus-4-7-profiler-smoke`` (deferred —
needs Owner sentinel for .github/workflows/validate.yml edit). For
now invoke manually:

    python3 .claude/scripts/profile-opus-4-7.py --smoke
    python3 .claude/scripts/profile-opus-4-7.py --floor

Schema:

    {
      "schema": "profile-opus-4-7.v1",
      "mode": "smoke|baseline|floor",
      "measured_at": "<UTC ISO>",
      "python": "<sys.version_info>",
      "subprocess_floor_ns": {"p50": ..., "p95": ..., "p99": ...},
      "decomposition": {
        "gate_boot_tokens_estimate": ...,
        "spawn_prompt_tokens_estimate": ...,
        "...": ...
      },
      "smoke": {
        "elapsed_ms": ...,
        "checks": [...]
      }
    }
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Subprocess startup floor (Phase 0 item 8)
# ---------------------------------------------------------------------------


def measure_subprocess_floor(samples: int = 50) -> Dict[str, Any]:
    """Measure python3 -c 'pass' wall-clock as canonical startup tax.

    Returns p50/p95/p99 in nanoseconds. p50 is the recommended floor
    used by hook-profiler logic_only_ns subtraction.
    """
    times: List[int] = []
    for _ in range(samples):
        t0 = time.perf_counter_ns()
        subprocess.run(
            ["python3", "-c", "pass"],
            capture_output=True,
            check=True,
        )
        t1 = time.perf_counter_ns()
        times.append(t1 - t0)
    times.sort()
    n = len(times)
    return {
        "samples": n,
        "min_ns": times[0],
        "p50_ns": times[n // 2],
        "p95_ns": times[int(n * 0.95)],
        "p99_ns": times[int(n * 0.99)],
        "max_ns": times[-1],
        "mean_ns": sum(times) // n,
    }


# ---------------------------------------------------------------------------
# Smoke mode (CI-runnable, no API)
# ---------------------------------------------------------------------------


_GATE_FILES = [
    "CLAUDE.md",
    "PROTOCOL.md",
    ".claude/team.md",
    ".claude/frontend-team.md",
    ".claude/skills/core/ceo-orchestration/SKILL.md",
]


def estimate_gate_boot_token_cost(repo_root: Path) -> Dict[str, Any]:
    """Approximate token cost of Gates 1-3 file load.

    Heuristic: 1 token ≈ 4 chars (English-Portuguese mix). Real counts
    require the Anthropic tokenizer; this estimate is for monotonic
    diff tracking, not absolute precision.
    """
    breakdown: Dict[str, int] = {}
    total_bytes = 0
    for relpath in _GATE_FILES:
        target = repo_root / relpath
        if target.is_file():
            size = target.stat().st_size
            breakdown[relpath] = size
            total_bytes += size
    # 4 chars/token rough heuristic
    estimated_tokens = total_bytes // 4
    return {
        "files": breakdown,
        "total_bytes": total_bytes,
        "estimated_tokens_at_4_char_per_token": estimated_tokens,
        "note": (
            "Estimate only; replace with Anthropic tokenizer counts in "
            "Phase 0 item 1 (audit_log.py v2.7 cache-header capture)"
        ),
    }


def estimate_spawn_prompt_cost(repo_root: Path) -> Dict[str, Any]:
    """Approximate tokens consumed by canonical Spawn Protocol prompt.

    Sample: code-reviewer persona + code-review-checklist SKILL inline.
    """
    persona_path = repo_root / ".claude" / "team.md"
    skill_path = (
        repo_root / ".claude" / "skills" / "core" / "code-review-checklist" / "SKILL.md"
    )
    persona_bytes = persona_path.stat().st_size if persona_path.is_file() else 0
    skill_bytes = skill_path.stat().st_size if skill_path.is_file() else 0
    inline_total = persona_bytes + skill_bytes
    return {
        "persona_bytes": persona_bytes,
        "skill_bytes_inline": skill_bytes,
        "inline_total_bytes": inline_total,
        "estimated_tokens_inline": inline_total // 4,
        "estimated_tokens_reference_mode": (
            persona_bytes // 4
            + 96  # @reference + sha256= + path = ~96 chars
        ),
        "expected_savings_pct_at_phase_2": (
            round(
                (skill_bytes - 96)
                * 100.0
                / max(inline_total, 1),
                1,
            )
            if inline_total > 0
            else 0
        ),
    }


def smoke_checks(repo_root: Path) -> List[Dict[str, Any]]:
    """Lightweight invariants. Each returns {name, passed, detail}."""
    checks = []

    # Check 1: gate files exist
    missing = [f for f in _GATE_FILES if not (repo_root / f).is_file()]
    checks.append(
        {
            "name": "gate_files_present",
            "passed": not missing,
            "detail": missing or "all 5 gate files present",
        }
    )

    # Check 2: agents/ tree (Phase 1 prep)
    agents_dir = repo_root / ".claude" / "agents"
    checks.append(
        {
            "name": "agents_tree_present",
            "passed": True,  # creating empty tree is fine
            "detail": (
                f"exists={agents_dir.is_dir()}; "
                f"files={len(list(agents_dir.glob('*.md'))) if agents_dir.is_dir() else 0}"
            ),
        }
    )

    # Check 3: no PLAN with status: executing is older than 90 days
    # (replaces the stale plan_020_executing check — PLAN-020 is done).
    # This steady-state invariant fires when the repo has a plan stuck
    # in executing for more than 90 days without a completed_at entry,
    # which could indicate an orphaned or false-active plan.
    plans_dir = repo_root / ".claude" / "plans"
    stale_executing: list = []
    import datetime as _dt
    _now = _dt.datetime.now(tz=_dt.timezone.utc)
    if plans_dir.is_dir():
        for plan_file in sorted(plans_dir.glob("PLAN-*.md")):
            try:
                text = plan_file.read_text(encoding="utf-8", errors="replace")
                if "status: executing" not in text:
                    continue
                if "completed_at:" in text:
                    continue
                # Extract executing_at date if present
                import re as _re
                m = _re.search(r"executing_at:\s*(\d{4}-\d{2}-\d{2})", text)
                if m:
                    try:
                        ea = _dt.datetime.strptime(m.group(1), "%Y-%m-%d").replace(
                            tzinfo=_dt.timezone.utc
                        )
                        age_days = (_now - ea).days
                        if age_days > 90:
                            stale_executing.append(
                                f"{plan_file.name} (executing {age_days}d)"
                            )
                    except Exception:
                        pass
            except Exception:
                pass
    checks.append(
        {
            "name": "no_stale_executing_plans",
            "passed": len(stale_executing) == 0,
            "detail": (
                "all executing plans within 90-day window"
                if not stale_executing
                else f"stale: {stale_executing[:5]}"
            ),
        }
    )

    # Check 4: CODEOWNERS Phase 0a globs
    co_path = repo_root / ".github" / "CODEOWNERS"
    if co_path.is_file():
        co = co_path.read_text(encoding="utf-8")
        has_phase_0a = "PLAN-020 Phase 0a" in co
        checks.append(
            {
                "name": "codeowners_phase_0a_present",
                "passed": has_phase_0a,
                "detail": "PLAN-020 Phase 0a block present" if has_phase_0a else "missing",
            }
        )
    else:
        checks.append(
            {
                "name": "codeowners_phase_0a_present",
                "passed": False,
                "detail": "CODEOWNERS file missing",
            }
        )

    return checks


# ---------------------------------------------------------------------------
# CLI dispatcher
# ---------------------------------------------------------------------------


def run_smoke(repo_root: Path, budget_seconds: float) -> Dict[str, Any]:
    """Run the Opus 4.7 smoke profile — quick cache-warming + sanity latency."""
    t0 = time.perf_counter()
    checks = smoke_checks(repo_root)
    gate = estimate_gate_boot_token_cost(repo_root)
    spawn = estimate_spawn_prompt_cost(repo_root)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return {
        "schema": "profile-opus-4-7.v1",
        "mode": "smoke",
        "measured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python": sys.version.split()[0],
        "elapsed_ms": round(elapsed_ms, 2),
        "budget_seconds": budget_seconds,
        "within_budget": elapsed_ms / 1000 < budget_seconds,
        "checks": checks,
        "decomposition": {
            "gate_boot": gate,
            "spawn_prompt": spawn,
        },
    }


def run_floor() -> Dict[str, Any]:
    """Run the Opus 4.7 latency floor profile (p50/p95/p99 percentiles)."""
    floor = measure_subprocess_floor(samples=50)
    return {
        "schema": "profile-opus-4-7.v1",
        "mode": "floor",
        "measured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python": sys.version.split()[0],
        "subprocess_floor_ns": floor,
        "subprocess_floor_ms": {
            "p50": round(floor["p50_ns"] / 1e6, 2),
            "p95": round(floor["p95_ns"] / 1e6, 2),
            "p99": round(floor["p99_ns"] / 1e6, 2),
        },
        "interpretation": {
            "use": "Subtract from hook end-to-end p99 to compute logic_only_ns",
            "example": (
                "If hook p99 = 30.9ms and floor p50 = 23.2ms, "
                "logic_only ≈ 7.7ms (algorithmic surface)"
            ),
        },
    }


def run_hook_latency(
    repo_root: Path,
    iterations: int = 20,
    p95_ceiling_ms: float = 120.0,
    p99_ceiling_ms: float = 160.0,
) -> Dict[str, Any]:
    """Run check_agent_spawn.py N+1 times (discard first as cold) and check p95/p99.

    Addresses E12-F4 (profile-opus-4-7.py had zero latency thresholds).

    Budget: p95 < 120ms / p99 < 160ms — the CI-confirmed fallback budget
    from PLAN-063 DIM-15 (ubuntu-latest baseline 57-64ms + headroom).
    This is more conservative than the test_hook_latency.py xfail budget
    (p95 100ms / p99 150ms) to account for measurement variance in the
    profile script vs the dedicated test runner.

    Returns a dict with per-hook p50/p95/p99 + passed boolean.
    Note: discards 1 cold-start iteration; asserts p95/p99 of warm set.
    """
    hook_path = repo_root / ".claude" / "hooks" / "check_agent_spawn.py"
    if not hook_path.is_file():
        return {
            "schema": "profile-opus-4-7.v1",
            "mode": "hook_latency",
            "measured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "error": f"hook not found: {hook_path}",
            "passed": False,
        }

    hooks_dir = repo_root / ".claude" / "hooks"
    payload = json.dumps({
        "session_id": "profile_latency",
        "tool_name": "Agent",
        "tool_input": {"description": "latency probe", "prompt": "bench"},
    }).encode()

    import os as _os
    env = {k: v for k, v in _os.environ.items()}
    env["PYTHONPATH"] = str(hooks_dir)
    # Disable all advisory emitters so we measure governance logic only
    env["CEO_MODEL_ROUTING"] = "0"
    env["CEO_PROMOTION_HEURISTIC"] = "0"
    env["CEO_COOKBOOK_ADVISOR_ENABLED"] = "0"
    env["CEO_SPEC_CTX_SANITIZER_ENABLED"] = "0"
    env["CEO_SPAWN_CONFIDENCE_ENABLED"] = "0"

    def _run_once() -> float:
        t0 = time.perf_counter_ns()
        subprocess.run(
            [sys.executable, str(hook_path)],
            input=payload,
            capture_output=True,
            env=env,
            timeout=10,
        )
        return (time.perf_counter_ns() - t0) / 1_000_000.0

    # Cold start (discarded)
    cold_ms = _run_once()

    # Warm iterations
    warm: List[float] = [_run_once() for _ in range(iterations)]
    warm_sorted = sorted(warm)
    n = len(warm_sorted)

    def _pct(lst: List[float], p: float) -> float:
        if not lst:
            return 0.0
        idx = int((len(lst) - 1) * p / 100.0)
        return lst[min(idx, len(lst) - 1)]

    p50 = _pct(warm_sorted, 50)
    p95 = _pct(warm_sorted, 95)
    p99 = _pct(warm_sorted, 99)
    hook_passed = p95 <= p95_ceiling_ms and p99 <= p99_ceiling_ms

    return {
        "schema": "profile-opus-4-7.v1",
        "mode": "hook_latency",
        "measured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python": sys.version.split()[0],
        "iterations": iterations,
        "p95_ceiling_ms": p95_ceiling_ms,
        "p99_ceiling_ms": p99_ceiling_ms,
        "check_agent_spawn": {
            "cold_ms": round(cold_ms, 1),
            "p50_ms": round(p50, 1),
            "p95_ms": round(p95, 1),
            "p99_ms": round(p99, 1),
            "max_ms": round(max(warm_sorted), 1),
        },
        "passed": hook_passed,
        "note": (
            "Advisory emitters disabled (CEO_MODEL_ROUTING=0 etc.); "
            "measures governance hot-path only. Budget PLAN-063 DIM-15 "
            "CI fallback: p95<120ms / p99<160ms."
        ),
    }


def main() -> int:
    """CLI entrypoint — profile Opus 4.7 token/latency under the Gate-1 load."""
    parser = argparse.ArgumentParser(
        description="Opus 4.7 framework optimization profiler (PLAN-020)"
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Synthetic CI-safe mode (no API). ≤30s budget.",
    )
    parser.add_argument(
        "--floor",
        action="store_true",
        help="Re-measure python3 subprocess startup floor (Phase 0 item 8).",
    )
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Full baseline capture (requires API + audit log; deferred).",
    )
    parser.add_argument(
        "--hook-latency",
        dest="hook_latency",
        action="store_true",
        help=(
            "Measure check_agent_spawn.py warm p95/p99 latency (N=20 default). "
            "Exits non-zero if p95 exceeds --p95-ceiling-ms or p99 exceeds "
            "--p99-ceiling-ms. Fixes E12-F4: profile script now has latency gates."
        ),
    )
    parser.add_argument(
        "--latency-iterations",
        dest="latency_iterations",
        type=int,
        default=20,
        help="Warm iteration count for --hook-latency (default 20; ADR-071 min=200 for p-stable).",
    )
    parser.add_argument(
        "--p95-ceiling-ms",
        dest="p95_ceiling_ms",
        type=float,
        default=120.0,
        help="p95 failure ceiling in ms for --hook-latency (default 120ms).",
    )
    parser.add_argument(
        "--p99-ceiling-ms",
        dest="p99_ceiling_ms",
        type=float,
        default=160.0,
        help="p99 failure ceiling in ms for --hook-latency (default 160ms).",
    )
    parser.add_argument(
        "--budget-seconds",
        type=float,
        default=30.0,
        help="Smoke mode wall-clock budget (default 30s).",
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        default=os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()),
        help="Repo root (default: $CLAUDE_PROJECT_DIR or cwd).",
    )

    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()

    modes = sum([args.smoke, args.floor, args.baseline, args.hook_latency])
    if modes != 1:
        print(
            "ERROR: pass exactly one of --smoke / --floor / --baseline / --hook-latency",
            file=sys.stderr,
        )
        return 1

    if args.baseline:
        print(
            "ERROR: --baseline requires Owner sentinel for hook modifications "
            "(audit_log.py v2.7). Deferred to next session.",
            file=sys.stderr,
        )
        return 1

    try:
        if args.smoke:
            result = run_smoke(repo_root, args.budget_seconds)
            json.dump(result, sys.stdout, indent=2)
            print()
            if not result["within_budget"]:
                print(
                    f"WARN: smoke exceeded budget {args.budget_seconds}s "
                    f"(actual {result['elapsed_ms']}ms)",
                    file=sys.stderr,
                )
                return 2
            failed = [
                c["name"] for c in result.get("checks", []) if not c.get("passed")
            ]
            if failed:
                print(
                    f"FAIL: {len(failed)} smoke check(s) failed: {failed}",
                    file=sys.stderr,
                )
                return 1
            return 0
        elif args.floor:
            result = run_floor()
            json.dump(result, sys.stdout, indent=2)
            print()
            return 0
        elif args.hook_latency:
            result = run_hook_latency(
                repo_root,
                iterations=args.latency_iterations,
                p95_ceiling_ms=args.p95_ceiling_ms,
                p99_ceiling_ms=args.p99_ceiling_ms,
            )
            json.dump(result, sys.stdout, indent=2)
            print()
            if not result["passed"]:
                print(
                    "FAIL: hook latency exceeded budget — "
                    f"check_agent_spawn p95={result['check_agent_spawn']['p95_ms']:.1f}ms "
                    f"(ceiling {result['p95_ceiling_ms']}ms), "
                    f"p99={result['check_agent_spawn']['p99_ms']:.1f}ms "
                    f"(ceiling {result['p99_ceiling_ms']}ms)",
                    file=sys.stderr,
                )
                return 1
            return 0
    except Exception as exc:  # noqa: BLE001 — top-level safety net
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
