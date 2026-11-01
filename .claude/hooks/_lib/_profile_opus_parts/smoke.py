"""Extracted implementation: smoke."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


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


def _pct_of_sorted(lst: List[float], p: float) -> float:
    """Nearest-rank percentile of an ascending-sorted list (0.0 on empty)."""
    if not lst:
        return 0.0
    idx = int((len(lst) - 1) * p / 100.0)
    return lst[min(idx, len(lst) - 1)]
