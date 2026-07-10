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
import shutil
import subprocess
import sys
import tempfile
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


def _pct_of_sorted(lst: List[float], p: float) -> float:
    """Nearest-rank percentile of an ascending-sorted list (0.0 on empty)."""
    if not lst:
        return 0.0
    idx = int((len(lst) - 1) * p / 100.0)
    return lst[min(idx, len(lst) - 1)]


# Session id used by every hook-latency corpus payload. Kept alnum+underscore
# so tool_lifecycle._safe_session_component passes it through unchanged (the
# observe-rail controls below need to predict the on-disk store filename).
_LATENCY_SESSION_ID = "profile_latency"


def _latency_pre_payload(tool_use_id: str) -> bytes:
    """PreToolUse payload for check_anti_ceo_overhead.py (record_pre carrier)."""
    return json.dumps({
        "session_id": _LATENCY_SESSION_ID,
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_use_id": tool_use_id,
        "tool_input": {"command": "true"},
    }).encode()


def _latency_post_payload(tool_use_id: str) -> bytes:
    """PostToolUse payload for check_output_secrets.py (record_post host)."""
    return json.dumps({
        "session_id": _LATENCY_SESSION_ID,
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_use_id": tool_use_id,
        "duration_ms": 42,
        "tool_response": "profile latency probe output (benign, no secrets)",
    }).encode()


def run_hook_latency(
    repo_root: Path,
    iterations: int = 20,
    p95_ceiling_ms: float = 120.0,
    p99_ceiling_ms: float = 160.0,
) -> Dict[str, Any]:
    """Subprocess-profile the hook-latency corpus and gate p95/p99.

    Addresses E12-F4 (profile-opus-4-7.py had zero latency thresholds) and
    PLAN-154 binding constraint 8 / SENT-F MANIFEST open-issue 3 (the observe
    rail's extended write path must join this corpus).

    Corpus (each entry: N+1 runs, first discarded as cold, warm p95/p99
    asserted against the shared ceilings):

    1. ``check_agent_spawn``                      — original E12-F4 entry.
    2. ``check_anti_ceo_overhead[observe=unset]`` — PreToolUse record_pre
       carrier, observe rail structurally OFF (baseline).
    3. ``check_anti_ceo_overhead[observe=1]``     — same, CEO_LEARNING_OBSERVE=1.
       record_pre is contractually byte-identical (MF-SEC-5), so this state
       must sit at baseline; the run doubles as an MF-SEC-5 tripwire (no
       observation store may appear on the Pre side).
    4. ``check_output_secrets[observe=unset]``    — PostToolUse record_post
       host, observe OFF. Negative control: the per-entry isolated audit dir
       must contain NO ``*.observe.jsonl`` after the runs (A12 zero-delta).
    5. ``check_output_secrets[observe=1]``        — THE extended write path.
       Each timed run is pre-seeded (unmeasured check_anti_ceo_overhead run,
       same tool_use_id) so record_post takes the real paired path: pairing
       pop + eviction save + lifecycle emit + observe append. Positive
       control (anti-vacuity, S254 class): when the repo's tool_lifecycle.py
       ships the observe rail, the store MUST hold >= iterations rows, all
       ``"paired": true`` — otherwise the entry measured a no-op boolean and
       the gate FAILS rather than passing vacuously. On a tree without the
       rail (pre-PLAN-154 landing) the control is reported not-required and
       both states measure baseline parity.

    Isolation: every corpus entry gets its own throwaway HOME +
    CEO_AUDIT_LOG_DIR (never the real ``~/.claude``); CEO_SOTA_DISABLE /
    CEO_TOOL_LIFECYCLE / CEO_ANTI_OVERHEAD / CLAUDE_SESSION_ID are scrubbed
    from the inherited env so the measured state is deterministic.

    Budget: p95 < 120ms / p99 < 160ms per corpus entry — the CI-confirmed
    fallback budget from PLAN-063 DIM-15 (ubuntu-latest baseline 57-64ms +
    headroom). More conservative than the test_hook_latency.py xfail budget
    (p95 100ms / p99 150ms) to absorb profile-script measurement variance.

    Returns a dict with per-hook p50/p95/p99 (``hooks``), the two observe
    controls (``controls``), the legacy top-level ``check_agent_spawn``
    block (back-compat), and an aggregate ``passed`` boolean.
    """
    hooks_dir = repo_root / ".claude" / "hooks"
    agent_spawn = hooks_dir / "check_agent_spawn.py"
    anti_overhead = hooks_dir / "check_anti_ceo_overhead.py"
    output_secrets = hooks_dir / "check_output_secrets.py"
    measured_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for required in (agent_spawn, anti_overhead, output_secrets):
        if not required.is_file():
            return {
                "schema": "profile-opus-4-7.v1",
                "mode": "hook_latency",
                "measured_at": measured_at,
                "error": f"hook not found: {required}",
                "passed": False,
            }

    # Static rail detection: does this tree's tool_lifecycle ship the PLAN-154
    # observe rail? Drives whether the positive control is REQUIRED (post-
    # landing) or informational (pre-landing baseline-parity run).
    observe_rail_present = False
    try:
        observe_rail_present = "observation_store_path" in (
            hooks_dir / "_lib" / "tool_lifecycle.py"
        ).read_text(encoding="utf-8")
    except OSError:
        observe_rail_present = False

    base_env = {k: v for k, v in os.environ.items()}
    base_env["PYTHONPATH"] = str(hooks_dir)
    base_env["CLAUDE_PROJECT_DIR"] = str(repo_root)
    # Disable all advisory emitters so we measure governance logic only
    base_env["CEO_MODEL_ROUTING"] = "0"
    base_env["CEO_PROMOTION_HEURISTIC"] = "0"
    base_env["CEO_COOKBOOK_ADVISOR_ENABLED"] = "0"
    base_env["CEO_SPEC_CTX_SANITIZER_ENABLED"] = "0"
    base_env["CEO_SPAWN_CONFIDENCE_ENABLED"] = "0"
    # Deterministic corpus state: no inherited kill-switches / session id.
    for scrubbed in (
        "CEO_LEARNING_OBSERVE",
        "CEO_SOTA_DISABLE",
        "CEO_TOOL_LIFECYCLE",
        "CEO_ANTI_OVERHEAD",
        "CLAUDE_SESSION_ID",
    ):
        base_env.pop(scrubbed, None)

    def _spawn_payload(tool_use_id: str) -> bytes:  # noqa: ARG001 — uniform sig
        return json.dumps({
            "session_id": _LATENCY_SESSION_ID,
            "tool_name": "Agent",
            "tool_input": {"description": "latency probe", "prompt": "bench"},
        }).encode()

    corpus: List[Dict[str, Any]] = [
        {
            "name": "check_agent_spawn",
            "hook": agent_spawn,
            "payload": _spawn_payload,
            "env_set": {},
            "seed": False,
        },
        {
            "name": "check_anti_ceo_overhead[observe=unset]",
            "hook": anti_overhead,
            "payload": _latency_pre_payload,
            "env_set": {},
            "seed": False,
        },
        {
            "name": "check_anti_ceo_overhead[observe=1]",
            "hook": anti_overhead,
            "payload": _latency_pre_payload,
            "env_set": {"CEO_LEARNING_OBSERVE": "1"},
            "seed": False,
        },
        {
            "name": "check_output_secrets[observe=unset]",
            "hook": output_secrets,
            "payload": _latency_post_payload,
            "env_set": {},
            "seed": True,
        },
        {
            "name": "check_output_secrets[observe=1]",
            "hook": output_secrets,
            "payload": _latency_post_payload,
            "env_set": {"CEO_LEARNING_OBSERVE": "1"},
            "seed": True,
        },
    ]

    observe_store_name = _LATENCY_SESSION_ID + ".observe.jsonl"
    hooks_out: Dict[str, Dict[str, Any]] = {}
    all_within_budget = True

    for entry in corpus:
        entry_tmp = Path(tempfile.mkdtemp(prefix="ceo-hook-latency-"))
        try:
            env = dict(base_env)
            env["HOME"] = str(entry_tmp / "home")
            env["CEO_AUDIT_LOG_DIR"] = str(entry_tmp / "audit")
            env.update(entry["env_set"])
            (entry_tmp / "home").mkdir(parents=True, exist_ok=True)
            (entry_tmp / "audit").mkdir(parents=True, exist_ok=True)

            # Codex pair-rail S265 P2: a hook that exits non-zero (import
            # or runtime error) must FAIL the gate, not silently record a
            # small latency sample. Hooks always exit 0 by contract, so any
            # non-zero return is a real failure — capture it for seed AND
            # timed runs and fold it into entry_passed (the S254 vacuous-
            # green class this profiler exists to prevent).
            entry_hook_failed = False

            def _run_once(tag: str) -> float:
                nonlocal entry_hook_failed
                tool_use_id = "profile-tu-" + tag
                if entry["seed"]:
                    # Unmeasured Pre stamp via the REAL record_pre carrier so
                    # the timed record_post run takes the paired path.
                    seed_res = subprocess.run(
                        [sys.executable, str(anti_overhead)],
                        input=_latency_pre_payload(tool_use_id),
                        capture_output=True,
                        env=env,
                        cwd=str(repo_root),
                        timeout=10,
                    )
                    if seed_res.returncode != 0:
                        entry_hook_failed = True
                payload = entry["payload"](tool_use_id)
                t0 = time.perf_counter_ns()
                res = subprocess.run(
                    [sys.executable, str(entry["hook"])],
                    input=payload,
                    capture_output=True,
                    env=env,
                    cwd=str(repo_root),
                    timeout=10,
                )
                if res.returncode != 0:
                    entry_hook_failed = True
                return (time.perf_counter_ns() - t0) / 1_000_000.0

            cold_ms = _run_once("cold")
            warm = [_run_once("%04d" % i) for i in range(iterations)]
            warm_sorted = sorted(warm)
            p50 = _pct_of_sorted(warm_sorted, 50)
            p95 = _pct_of_sorted(warm_sorted, 95)
            p99 = _pct_of_sorted(warm_sorted, 99)
            entry_passed = (
                p95 <= p95_ceiling_ms
                and p99 <= p99_ceiling_ms
                and not entry_hook_failed
            )
            all_within_budget = all_within_budget and entry_passed
            hooks_out[entry["name"]] = {
                "cold_ms": round(cold_ms, 1),
                "p50_ms": round(p50, 1),
                "p95_ms": round(p95, 1),
                "p99_ms": round(p99, 1),
                "max_ms": round(max(warm_sorted), 1),
                "hook_failed": entry_hook_failed,
                "passed": entry_passed,
            }

            # Snapshot the entry's observation store BEFORE the tmpdir is
            # deleted (the controls below consume these snapshots).
            store = entry_tmp / "audit" / "tool-lifecycle" / observe_store_name
            if store.is_file():
                try:
                    rows = [
                        json.loads(line)
                        for line in store.read_text(
                            encoding="utf-8"
                        ).splitlines()
                        if line.strip()
                    ]
                except (OSError, json.JSONDecodeError):
                    rows = []
                hooks_out[entry["name"]]["observe_rows"] = len(rows)
                hooks_out[entry["name"]]["observe_paired_rows"] = sum(
                    1 for r in rows
                    if isinstance(r, dict) and r.get("paired") is True
                )
            else:
                hooks_out[entry["name"]]["observe_rows"] = 0
                hooks_out[entry["name"]]["observe_paired_rows"] = 0
        finally:
            shutil.rmtree(entry_tmp, ignore_errors=True)

    # ---- Observe-rail controls (anti-vacuity, S254 class) -------------------
    on_rows = hooks_out["check_output_secrets[observe=1]"]["observe_rows"]
    on_paired = hooks_out["check_output_secrets[observe=1]"][
        "observe_paired_rows"
    ]
    # Codex pair-rail S265 P3: every seeded run (cold + all warm) takes the
    # paired path, so EVERY observed row must be paired — requiring only
    # `on_paired >= iterations` let one unpaired warm row hide behind the
    # cold row's paired count (cold + 19 paired + 1 unpaired = 20). The
    # robust invariant is: no unpaired rows at all, and at least `iterations`
    # of them.
    positive_ok = (not observe_rail_present) or (
        on_rows >= iterations and on_paired == on_rows
    )
    positive_control = {
        "required": observe_rail_present,
        "rows": on_rows,
        "paired_rows": on_paired,
        "passed": positive_ok,
        "note": (
            "observe rail present: store must hold >= iterations paired rows "
            "or the observe=1 timing is a vacuous no-op measurement"
            if observe_rail_present
            else "observe rail not in this tree; both states are baseline "
            "parity runs (control arms automatically at PLAN-154 landing)"
        ),
    }
    off_rows = hooks_out["check_output_secrets[observe=unset]"]["observe_rows"]
    pre_rows = hooks_out["check_anti_ceo_overhead[observe=1]"]["observe_rows"]
    negative_ok = off_rows == 0 and pre_rows == 0
    negative_control = {
        "unset_store_rows": off_rows,
        "pre_side_store_rows": pre_rows,
        "passed": negative_ok,
        "note": (
            "A12 zero-delta: unset state writes nothing; MF-SEC-5: the "
            "record_pre carrier never writes the store even with observe=1"
        ),
    }

    passed = all_within_budget and positive_ok and negative_ok

    return {
        "schema": "profile-opus-4-7.v1",
        "mode": "hook_latency",
        "measured_at": measured_at,
        "python": sys.version.split()[0],
        "iterations": iterations,
        "p95_ceiling_ms": p95_ceiling_ms,
        "p99_ceiling_ms": p99_ceiling_ms,
        "observe_rail_present": observe_rail_present,
        "hooks": hooks_out,
        # Back-compat: legacy consumers read this top-level block.
        "check_agent_spawn": hooks_out["check_agent_spawn"],
        "controls": {
            "observe_positive_control": positive_control,
            "observe_negative_control": negative_control,
        },
        "passed": passed,
        "note": (
            "Advisory emitters disabled (CEO_MODEL_ROUTING=0 etc.); "
            "measures governance hot-path only. Budget PLAN-063 DIM-15 "
            "CI fallback: p95<120ms / p99<160ms per corpus entry. "
            "PLAN-154 constraint 8: observe-rail extended write path "
            "profiled in both states with anti-vacuity controls."
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
            "Measure warm p95/p99 latency of the hook corpus (N=20 default): "
            "check_agent_spawn + the PLAN-154 observe-rail host hooks "
            "(check_anti_ceo_overhead record_pre carrier, check_output_secrets "
            "record_post path) in BOTH CEO_LEARNING_OBSERVE states, with "
            "anti-vacuity store controls. Exits non-zero if any entry's p95 "
            "exceeds --p95-ceiling-ms / p99 exceeds --p99-ceiling-ms, or a "
            "control fails. Fixes E12-F4 + PLAN-154 constraint 8."
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
                failures: List[str] = []
                for hook_name, stats in sorted(
                    result.get("hooks", {}).items()
                ):
                    if not stats.get("passed", True):
                        failures.append(
                            f"{hook_name} p95={stats['p95_ms']:.1f}ms "
                            f"p99={stats['p99_ms']:.1f}ms"
                        )
                for ctrl_name, ctrl in sorted(
                    result.get("controls", {}).items()
                ):
                    if isinstance(ctrl, dict) and not ctrl.get("passed", True):
                        failures.append(f"control:{ctrl_name}")
                print(
                    "FAIL: hook latency gate — "
                    + ("; ".join(failures) or result.get("error", "unknown"))
                    + f" (ceilings p95<{result.get('p95_ceiling_ms')}ms / "
                    f"p99<{result.get('p99_ceiling_ms')}ms)",
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
