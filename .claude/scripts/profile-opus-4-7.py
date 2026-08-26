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


# ---------------------------------------------------------------------------
# ADR-163 Amendment (PLAN-169 S328) — runner-normalized SECOND KEY
# ---------------------------------------------------------------------------
#
# Evidence: `check_output_secrets` measured p95 361.4 / 424.8 / 229.1 ms on
# ubuntu-latest against the 180 ms hard ceiling while the ADR-163 contention
# pre-probe (`python3 -c pass`, the SPAWN floor) read UNCONTENDED at 7.76 ms
# and the same hook bytes measured 70-77 ms locally — and the immediately
# preceding commit PASSED 3.5 h earlier with ZERO files touched under the
# hook tree. `python3 -c pass` prices process CREATION; it is structurally
# blind to a runner that is slow-but-uncontended once execution starts.
#
# Cure: a SECOND key, relative, against an EXECUTION reference measured in
# the same run, round-robin-interleaved with the hook samples so both keys
# price the same scheduler window. The absolute ceiling STAYS (no third
# recalibration — "bump the number" already failed at ADR-163:291).
#
# PHASE 1 (this landing): labels are computed and PUBLISHED; exit codes stay
# byte-identical to today. K is not derivable — zero paired (hook, ref)
# samples exist anywhere. Phase 2 pins K_e per entry from an advisory window
# and is plumbed here (`--relative-k-source`) but INERT without that file.

# Closed set, DERIVED by every consumer (never recalled — the
# `feedback-closed-sets-must-be-derived-not-recalled` class).
_OUTCOME_LABELS: Tuple[str, ...] = (
    "pass",
    "advisory_slow_runner",
    "real_regression",
    "infrastructure_contended",
)

# label -> process exit code, PHASE 2 only. Phase 1 keeps today's 0/1.
_LABEL_EXIT_CLASS: Dict[str, int] = {
    "pass": 0,
    "advisory_slow_runner": 0,
    "real_regression": 1,
    "infrastructure_contended": 5,
}

# Aggregation precedence (strongest verdict first): a PROVEN regression on
# any entry outranks contention elsewhere, and contention outranks amnesty.
_LABEL_PRECEDENCE: Tuple[str, ...] = (
    "real_regression",
    "infrastructure_contended",
    "advisory_slow_runner",
    "pass",
)

# The COMPLETE set of report keys the second key may add. Declared here so
# the back-compat test can assert `set(new_report) - set(old_report)` is a
# subset of it: a future key added without registering it here turns that
# test RED instead of silently widening the report.
_SECOND_KEY_REPORT_KEYS: Tuple[str, ...] = (
    "phase",
    "verdict_label",
    "exit_class",
    "outcome_labels",
    "exec_reference",
    "relative_advisory",
    "strict_relative",
    "abs_backstop_ms",
    "ref_drift_max",
    "wall_budget_seconds",
    "wall_deadline_seconds",
    "wall_exceeded",
    "elapsed_seconds",
    "relative_warnings",
    "ref_source_sha256",
    "ref_samples_per_entry",
    "relative_note",
)
_SECOND_KEY_ENTRY_KEYS: Tuple[str, ...] = (
    "ref_p50_ms",
    "ref_p95_ms",
    "ref_samples",
    "ref_split_half_drift",
    "ref_valid",
    "ref_failed",
    "R_e",
    "K_e",
    "rel_ok",
    "verdict_label",
    "phase",
)

# Absolute backstop above which a slow runner still FAILS instead of being
# granted amnesty. OPEN QUESTION for the Owner: this number has no evidence
# behind it — it is a "what latency is unusable in a real session" judgment.
_ABS_BACKSTOP_MS = 600.0

# Reference samples per corpus entry (round-robin). The relative key gates on
# p50, where the ADR-163 nearest-rank index collapse cannot arise, so the
# n>=22 separation rule does not bind here; 40 is the adopted floor.
_REF_SAMPLES_PER_ENTRY = 40

# Split-half p50 drift above which the REFERENCE itself is untrustworthy:
# the machine moved mid-entry, so the ratio prices two different machines.
_REF_DRIFT_MAX = 1.5

# Self-cap fraction of --wall-budget-seconds. The cap fires BEFORE the
# workflow's `timeout 420`, so rc 124 becomes unreachable in practice.
_WALL_BUDGET_SAFETY_FRACTION = 0.9
# (rail round-1 P2 retired `_WALL_CHECK_EVERY`: the wall is checked on EVERY
# iteration and again before the reference lane, so there is no stride to
# name. A stride here is a defect, not a tuning knob — it made the 378s
# self-cap miss by up to ~300s, which is the rc124 the cap exists to avoid.)

# --- the frozen execution reference ----------------------------------------
# Three terms, source-pinned by sha256 in the report. Any edit changes that
# hash DELIBERATELY: a heavier reference silently LOOSENS the relative key.
_REF_EXEC_SOURCE = r'''#!/usr/bin/env python3
# Frozen EXECUTION reference — ADR-163 Amendment (PLAN-169 S328).
#
# THREE TERMS, in order:
#   1. cold stdlib imports (json / re / hashlib / pathlib) + a fixed
#      re.compile set   -- prices the interpreter + import machinery;
#   2. a fixed CPU-bound hashing loop        -- prices the core;
#   3. M x open/append/flock/fsync/rename    -- prices the filesystem.
#
# HARD CONTRACT: stdlib ONLY, and NOTHING from the framework's own hook
# tree. The regression class this gate exists to catch IS an eager
# framework import; a reference paying that same import would inflate
# numerator AND denominator and go blind to its own reason to exist. An
# anti-coupling test walks this source's AST and asserts it.
import os
import sys

try:
    import fcntl as _locker
except ImportError:  # pragma: no cover - non-POSIX
    _locker = None

# Term sizing is MEASURED, not guessed (local macOS, 2026-08-25, N=30):
# spawn floor 23.9ms; imports +6.4ms; these constants add ~+16ms of CPU and
# ~+5ms of locked IO, putting the reference at p50 ~46ms of which ~48% is
# EXECUTION. The first draft (4000/6) sat at 34ms / 30% execution — barely
# more than the spawn probe it replaces, which would leave the ratio nearly
# as blind as the probe. The corpus hooks are ~52-64ms at ~63% execution;
# the residual under-tracking is declared, not hidden.
_HASH_ROUNDS = 14000
_IO_CYCLES = 24
_PROBE = "ref-exec 2026-08-25 https://example.invalid token=abc12345"


def term_imports():
    import json
    import re
    import hashlib
    import pathlib

    pats = (
        re.compile(r"[A-Za-z0-9_]{8,}"),
        re.compile(r"(?i)\b(secret|token|key)\b"),
        re.compile(r"^\s*[-*]\s+"),
        re.compile(r"\d{4}-\d{2}-\d{2}"),
        re.compile(r"https?://\S+"),
    )
    blob = json.dumps({"probe": _PROBE, "rounds": _HASH_ROUNDS})
    hits = sum(1 for p in pats if p.search(blob))
    hits += len(pathlib.PurePosixPath("/a/b/c/d").parts)
    hits += len(hashlib.sha256(blob.encode("utf-8")).hexdigest())
    return hits


def term_cpu():
    import hashlib

    acc = hashlib.sha256(b"ceo-exec-reference-seed")
    for i in range(_HASH_ROUNDS):
        acc.update(acc.digest())
        acc.update(str(i).encode("ascii"))
    return acc.hexdigest()


def term_io(dirpath):
    if not os.path.isdir(dirpath):
        os.makedirs(dirpath, exist_ok=True)
    target = os.path.join(dirpath, "ref-exec.log")
    made = 0
    for i in range(_IO_CYCLES):
        staging = os.path.join(dirpath, "ref-exec.%d.part" % i)
        fh = open(staging, "a")
        try:
            if _locker is not None:
                _locker.flock(fh.fileno(), _locker.LOCK_EX)
            fh.write("ref-exec cycle %d\n" % i)
            fh.flush()
            os.fsync(fh.fileno())
            if _locker is not None:
                _locker.flock(fh.fileno(), _locker.LOCK_UN)
        finally:
            fh.close()
        os.replace(staging, target)
        made += 1
    return made


def main():
    dirpath = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    a = term_imports()
    b = term_cpu()
    c = term_io(dirpath)
    sys.stdout.write("%d %s %d\n" % (a, b[:8], c))
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


def ref_source_sha256() -> str:
    """sha256 of the frozen reference source text (report-pinned)."""
    return hashlib.sha256(_REF_EXEC_SOURCE.encode("utf-8")).hexdigest()


def _is_real_number(value: Any) -> bool:
    """True only for a finite, non-bool int/float (codex r1 F8 case list).

    ``True`` / ``"-1"`` / ``NaN`` / ``-Infinity`` / ``None`` all read False,
    exactly as the ADR-163 contention probe's parser treats them — the two
    parsers must not diverge.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def _split_half_drift(samples: List[float]) -> float:
    """Ratio between the p50 of the two TEMPORAL halves (>= 1.0).

    ``inf`` when undefined (too few samples, or a zero/negative half-median):
    an undefined drift reads as CONTENDED, never as permission to gate.
    """
    n = len(samples)
    if n < 4:
        return float("inf")
    half = n // 2
    first = _pct_of_sorted(sorted(samples[:half]), 50)
    second = _pct_of_sorted(sorted(samples[half:]), 50)
    lo, hi = (first, second) if first <= second else (second, first)
    if not _is_real_number(lo) or lo <= 0:
        return float("inf")
    return hi / lo


def _classify_entry(
    hook_p50: float,
    hook_p95: float,
    ref_p50: Any,
    ref_drift: Any,
    p95_ceiling_ms: float,
    k_e: Optional[float] = None,
    ref_measured: bool = True,
    wall_exceeded: bool = False,
    abs_backstop_ms: float = _ABS_BACKSTOP_MS,
    strict_relative: bool = False,
    ref_failed: bool = False,
) -> Tuple[str, Optional[bool], bool]:
    """PURE verdict function — returns ``(label, rel_ok, ref_valid)``.

    ``rel_ok`` is ``None`` whenever no K applies to this entry (phase 1, or a
    phase-2 file with no usable K for this name): the label then follows the
    ABSOLUTE key alone, which is exactly today's contract.

    ``strict_relative`` enables the ``abs_ok and not rel_ok`` cell (a clean
    regression that still fits under the fixed ceiling — the blind spot
    ADR-163:291 declares). Default OFF: it is a detection-floor product call
    for the Owner, implemented and unit-tested but not armed.
    """
    if wall_exceeded:
        return ("infrastructure_contended", None, False)

    ref_valid = True
    if ref_measured:
        if ref_failed:
            # rail round-1 P1. Checked FIRST and on its own: a failing
            # reference can still produce numbers that pass every shape test
            # below (a fast crash is a small, low-drift, perfectly finite
            # sample). Shape is not provenance — only the return code says
            # whether the process actually did the work.
            ref_valid = False
        elif not _is_real_number(ref_p50) or ref_p50 <= 0:
            ref_valid = False
        elif not _is_real_number(ref_drift) or ref_drift > _REF_DRIFT_MAX:
            ref_valid = False
        if not ref_valid:
            return ("infrastructure_contended", None, False)
    else:
        ref_valid = False

    abs_ok = hook_p95 <= p95_ceiling_ms

    rel_ok: Optional[bool] = None
    if k_e is not None and ref_measured and ref_valid:
        rel_ok = hook_p50 <= k_e * ref_p50

    if rel_ok is None:
        # Phase 1 for this entry: the absolute key is the only key.
        return ("pass" if abs_ok else "real_regression", None, ref_valid)

    if abs_ok:
        if rel_ok or not strict_relative:
            return ("pass", rel_ok, True)
        return ("real_regression", rel_ok, True)

    if rel_ok and hook_p95 <= abs_backstop_ms:
        return ("advisory_slow_runner", rel_ok, True)
    return ("real_regression", rel_ok, True)


def _aggregate_label(labels: List[str]) -> str:
    """Strongest verdict in the corpus, by _LABEL_PRECEDENCE."""
    for candidate in _LABEL_PRECEDENCE:
        if candidate in labels:
            return candidate
    return "pass"


def _load_relative_k_source(path: str) -> Tuple[Dict[str, float], List[str]]:
    """Parse the phase-2 K file -> ``({entry_name: K}, warnings)``.

    Every rejection is NAMED in ``warnings`` and degrades that entry (or the
    whole file) back to PHASE 1 — never to a silently wider gate. An
    ``admissibility_max_K`` that the K REACHES is a REJECTION (the cap is
    exclusive — equality already loses the positive control): the design's
    "an empty admissibility interval means the reference is mis-shaped"
    branch is mechanical here, so "widen K" cannot be reached by editing
    one number. Exception text is never echoed (it can carry a machine path).
    """
    warnings: List[str] = []
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {}, ["relative_k_source_unreadable: %s" % type(exc).__name__]
    if not isinstance(doc, dict):
        return {}, ["relative_k_source_malformed: top level is not an object"]
    entries = doc.get("entries")
    if not isinstance(entries, dict):
        return {}, [
            "relative_k_source_malformed: 'entries' missing or not an object"
        ]
    out: Dict[str, float] = {}
    for name, spec in sorted(entries.items()):
        if not isinstance(spec, dict):
            warnings.append("relative_k_invalid[%s]: entry is not an object" % name)
            continue
        k = spec.get("K")
        if not _is_real_number(k) or k <= 0:
            warnings.append(
                "relative_k_invalid[%s]: K=%r is not a finite positive JSON "
                "number" % (name, k)
            )
            continue
        cap = spec.get("admissibility_max_K")
        if cap is not None:
            if not _is_real_number(cap) or cap <= 0:
                warnings.append(
                    "relative_k_invalid[%s]: admissibility_max_K=%r is not a "
                    "finite positive JSON number" % (name, cap)
                )
                continue
            # rail round-3 P2 — the cap is EXCLUSIVE. `>` alone let K land
            # exactly ON it, and the guarantee the cap encodes ("the +150ms
            # positive control still fails at the worst observed reference")
            # needs `hook_p50 > K * ref_p50`, i.e. K STRICTLY below
            # (baseline+150)/max_ref — because the classifier's comparison is
            # inclusive. Measured with baseline 70 / worst ref 50 / cap 4.4:
            # K == cap gives `advisory_slow_runner` on the regressed sample,
            # K one epsilon below gives `real_regression`. Float pushes the
            # same way (4.4*50 == 220.00000000000003 > 220.0), so equality is
            # rejected rather than nudged with a tolerance.
            if k >= cap:
                warnings.append(
                    "relative_k_inadmissible[%s]: K=%s reaches "
                    "admissibility_max_K=%s (the cap is exclusive) — the "
                    "+150ms positive control would not fail at the worst "
                    "observed reference; entry stays on phase 1"
                    % (name, k, cap)
                )
                continue
        out[name] = float(k)
    return out, warnings


def _ref_schedule(iterations: int, n_ref: int) -> List[int]:
    """Round-robin plan: how many reference samples to take AFTER hook i.

    Even spread by construction (``round((i+1)*n_ref/iterations)`` cumulative),
    and the totals always land on exactly ``n_ref``. With more hook samples
    than reference samples this yields 0/1 per iteration; with fewer it takes
    several per iteration. The interleaving is the point: the S318 defect was
    a probe measured ONCE, outside the window that actually degraded.
    """
    if iterations <= 0 or n_ref <= 0:
        return []
    plan: List[int] = []
    taken = 0
    for i in range(iterations):
        want = int(round((i + 1) * float(n_ref) / iterations))
        want = min(want, n_ref)
        plan.append(max(0, want - taken))
        taken += plan[-1]
    if taken < n_ref:
        plan[-1] += n_ref - taken
    return plan


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
    iterations: int = 200,
    p95_ceiling_ms: float = 180.0,
    p99_ceiling_ms: float = 160.0,
    p99_advisory: bool = False,
    exec_reference: bool = False,
    relative_advisory: bool = False,
    relative_k_source: Optional[str] = None,
    wall_budget_seconds: float = 420.0,
    strict_relative: bool = False,
    sampler: Optional[Callable[[str, str, int], float]] = None,
) -> Dict[str, Any]:
    """Subprocess-profile the hook-latency corpus and gate p95/p99.

    ==== ADR-163 Amendment (PLAN-169 S328) — the SECOND KEY, phase 1 ====

    The gate has always had ONE key: ``hook_p95 <= p95_ceiling_ms``, an
    ABSOLUTE number. That key cannot tell "the hooks got slower" from "the
    runner got slower", and the ADR-163 contention pre-probe that was meant
    to separate them measures ``python3 -c pass`` — process CREATION, a few
    percent of a hook that imports the framework's ``_lib`` tree and takes a
    locked write. It is blind by construction to a runner that is slow but
    UNCONTENDED: 361/425/229 ms hook p95 against a 7.76 ms spawn probe, on
    hook bytes that measured 70-77 ms locally and PASSED 3.5 h earlier.

    This adds a SECOND, RELATIVE key measured in the same scheduler window:

    * ``--exec-reference`` samples ``ref_exec`` — a frozen, stdlib-only,
      3-term reference script (cold imports + fixed re.compile set; a fixed
      CPU hash loop; M x open/append/flock/fsync/rename on the same
      filesystem as the entry's audit dir) — ROUND-ROBIN interleaved inside
      each entry's own loop, ``_REF_SAMPLES_PER_ENTRY`` samples per entry.
      The reference imports NOTHING from the hook tree on purpose: the
      regression class this gate exists for IS an eager framework import,
      which would inflate numerator AND denominator.
    * ``--relative-advisory`` publishes ``R_e = hook_p50 / ref_p50`` and a
      ``verdict_label`` from the closed set ``_OUTCOME_LABELS``. p50 on BOTH
      sides — the ADR-163:258 median-on-shared-load doctrine.
    * ``--relative-k-source`` (PHASE 2, inert without the file) supplies
      ``K_e`` per entry and makes the relative key DECIDE the exit.

    **PHASE 1 IS WHAT SHIPS HERE: the exit codes are byte-identical to
    today.** Without a K there is no ``rel_ok``, so the label simply mirrors
    the absolute key (``pass`` / ``real_regression``), and even a broken
    reference (``infrastructure_contended``) leaves the exit alone. The
    labels exist to DERIVE K from >=10 green CI runs; K is not derivable
    today because zero paired (hook, reference) samples exist anywhere.

    Phase-2 truth table (only with a usable ``K_e`` for the entry):

    ======================  ========  =======  =========================
    abs_ok / rel_ok         p95<=600  label                       exit
    ======================  ========  =======  =========================
    True / True             -         pass                           0
    False / True            yes       advisory_slow_runner           0
    False / True            no        real_regression                1
    False / False           -         real_regression                1
    True / False            -         pass (strict_relative=False)    0
    reference invalid       -         infrastructure_contended       5
    ======================  ========  =======  =========================

    ``sampler(entry_name, kind, index) -> ms`` replaces ALL measurement when
    supplied (kind in ``{"cold", "warm", "ref"}``) and spawns no subprocess:
    the unit tests plant a +150 ms regression at the predicate level instead
    of betting on wall-clock luck.


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

    Budget: p95 < 180ms hard per corpus entry (ADR-163 S318 amendment —
    recalibrated from the 2026-07 value of 120ms with the 2026-08-20
    evidence: an unloaded ubuntu-latest runner measured the heaviest entry
    at p95 110.6ms, an 8% margin, while the local baseline stayed at
    70.6ms — the runner shifted, not the hooks). p99 < 160ms is HARD by
    default for back-compat; under ``p99_advisory=True`` (the CI gate's
    mode) a p99 breach is REPORTED per entry (``p99_within``) and echoed
    as a WARN by the CLI but never fails the gate — on a shared runner the
    extreme tail prices the runner, not the code (same evidence class as
    the ADR-163 PLAN-169 W2.2 amendment's median-on-CI decision).

    Returns a dict with per-hook p50/p95/p99 (``hooks``), the two observe
    controls (``controls``), the legacy top-level ``check_agent_spawn``
    block (back-compat), and an aggregate ``passed`` boolean.
    """
    hooks_dir = repo_root / ".claude" / "hooks"
    agent_spawn = hooks_dir / "check_agent_spawn.py"
    anti_overhead = hooks_dir / "check_anti_ceo_overhead.py"
    output_secrets = hooks_dir / "check_output_secrets.py"
    measured_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ADR-163 percentile precondition (PLAN-159 debate round-1 must-fix):
    # with the nearest-rank truncation in _pct_of_sorted (int((n-1)*p/100)),
    # p95 and p99 collapse onto the SAME order statistic for n < 22 — the
    # p99 ceiling becomes dead code and the gate keys on the 2nd-largest
    # sample (the S272/S273 load-flake class). A gate run on a collapsed
    # index is a defect state: fail LOUDLY instead of measuring.
    idx_p95 = int((iterations - 1) * 95 / 100.0)
    idx_p99 = int((iterations - 1) * 99 / 100.0)
    if idx_p95 == idx_p99:
        return {
            "schema": "profile-opus-4-7.v1",
            "mode": "hook_latency",
            "measured_at": measured_at,
            "error": (
                "percentile_indices_collapsed: iterations=%d puts p95 and "
                "p99 on the same order statistic (index %d); minimum is 22, "
                "gate standard is 200 (ADR-163)" % (iterations, idx_p95)
            ),
            "p95_ceiling_ms": p95_ceiling_ms,
            "p99_ceiling_ms": p99_ceiling_ms,
            "passed": False,
        }

    for required in (agent_spawn, anti_overhead, output_secrets):
        if not required.is_file():
            return {
                "schema": "profile-opus-4-7.v1",
                "mode": "hook_latency",
                "measured_at": measured_at,
                "error": f"hook not found: {required}",
                "passed": False,
            }

    # --- second-key wiring (ADR-163 Amendment PLAN-169 S328) ---------------
    # The whole relative machinery — reference sampling AND the wall self-cap
    # — is gated on the new flags, so a run without them is byte-identical to
    # today (report keys AND exit code), which is the back-compat contract.
    second_key = bool(exec_reference or relative_advisory or relative_k_source)
    relative_warnings: List[str] = []
    k_by_entry: Dict[str, float] = {}
    if relative_k_source:
        k_by_entry, relative_warnings = _load_relative_k_source(relative_k_source)
        if not exec_reference and k_by_entry:
            relative_warnings.append(
                "relative_k_source_ignored: --relative-k-source needs "
                "--exec-reference (no reference measured, so rel_ok is "
                "undefined); every entry stays on phase 1"
            )
            k_by_entry = {}
    ref_plan = _ref_schedule(iterations, _REF_SAMPLES_PER_ENTRY) if exec_reference else []
    t_gate_start = time.perf_counter()
    wall_deadline_s = _WALL_BUDGET_SAFETY_FRACTION * float(wall_budget_seconds)
    wall_exceeded = False

    def _wall_blown() -> bool:
        if not second_key:
            return False
        return (time.perf_counter() - t_gate_start) > wall_deadline_s

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
    # CLAUDE_PROJECT_DIR_NATIVE is the HIGHEST-PRECEDENCE runtime-state
    # carrier (runtime_paths): left in the inherited env it overrides both
    # HOME and CEO_AUDIT_LOG_DIR below, and every measured hook would append
    # to the LIVE HMAC chain instead of the per-entry throwaway dir — the
    # S321/S326 non-attributable-elos class. Scrubbing it is unconditional:
    # it is an isolation fix, not part of the second key, and it changes no
    # report key and no exit code.
    for scrubbed in (
        "CEO_LEARNING_OBSERVE",
        "CEO_SOTA_DISABLE",
        "CEO_TOOL_LIFECYCLE",
        "CEO_ANTI_OVERHEAD",
        "CLAUDE_SESSION_ID",
        "CLAUDE_PROJECT_DIR_NATIVE",
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

    # rail round-1 P2 — a K file may only name entries that EXIST. Without
    # this, one typo armed phase 2 for the whole run while applying K to
    # nothing: `any_enforced` keys on `bool(k_by_entry)`, so every entry
    # classified with `k_e=None` (label "pass" whenever the absolute key was
    # met, and — the actual hole — a run that phase 1 would exit 1 on could
    # aggregate to "pass" and exit 0). Rejecting the name keeps the loader's
    # stated contract: a rejection is NAMED and degrades to PHASE 1, never
    # to a silently wider gate.
    if k_by_entry:
        _known_names = {e["name"] for e in corpus}
        for _unknown in sorted(set(k_by_entry) - _known_names):
            relative_warnings.append(
                "relative_k_unknown_entry[%s]: not a corpus entry name; "
                "dropped (the run stays on phase 1 unless another K "
                "applies)" % _unknown
            )
            k_by_entry.pop(_unknown)

    for entry in corpus:
        if _wall_blown():
            wall_exceeded = True
            break
        entry_tmp = Path(tempfile.mkdtemp(prefix="ceo-hook-latency-"))
        try:
            env = dict(base_env)
            env["HOME"] = str(entry_tmp / "home")
            env["CEO_AUDIT_LOG_DIR"] = str(entry_tmp / "audit")
            env.update(entry["env_set"])
            (entry_tmp / "home").mkdir(parents=True, exist_ok=True)
            (entry_tmp / "audit").mkdir(parents=True, exist_ok=True)

            # Reference lane: its own dir, SIBLING of the audit dir (same
            # filesystem, which is the whole point of term 3) and never
            # inside it — the observe-rail positive control must keep
            # counting exactly the rows the hooks wrote. PYTHONPATH is
            # dropped so the reference cannot import the hook tree even by
            # accident (anti-coupling contract).
            ref_env = dict(env)
            ref_env.pop("PYTHONPATH", None)
            ref_dir = entry_tmp / "ref"
            ref_script = entry_tmp / "ref_exec.py"
            if exec_reference and sampler is None:
                ref_dir.mkdir(parents=True, exist_ok=True)
                ref_script.write_text(_REF_EXEC_SOURCE, encoding="utf-8")

            # Codex pair-rail S265 P2: a hook that exits non-zero (import
            # or runtime error) must FAIL the gate, not silently record a
            # small latency sample. Hooks always exit 0 by contract, so any
            # non-zero return is a real failure — capture it for seed AND
            # timed runs and fold it into entry_passed (the S254 vacuous-
            # green class this profiler exists to prevent).
            entry_hook_failed = False
            # rail round-1 P1 — the SAME rule as the line above, for the lane
            # that did not have it. The reference is a MEASUREMENT of how
            # fast this runner executes; a process that died on an import,
            # a missing dir or a permission is not a slow reference, it is
            # NO reference. Discarding its return code let a fast, repeatable
            # failure (~15ms, low split-half drift) present as a perfectly
            # healthy `ref_valid=true` — and a tiny ref_p50 is the worst
            # possible poison for phase 2, where K_e is pinned from
            # max(hook_p50/ref_p50): one broken run pins K enormous and buys
            # blanket amnesty forever after.
            entry_ref_failed = False

            def _run_once(tag: str, kind: str = "warm", index: int = 0) -> float:
                nonlocal entry_hook_failed
                if sampler is not None:
                    # Injected measurement: no subprocess at all (seed
                    # included). Unit tests plant regressions at the
                    # predicate level instead of via time.sleep.
                    return float(sampler(entry["name"], kind, index))
                tool_use_id = "profile-tu-" + tag
                if entry["seed"]:
                    # Unmeasured Pre stamp via the REAL record_pre carrier so
                    # the timed record_post run takes the paired path.
                    # ADR-163: a >10s stall is folded into the fail-closed
                    # sink instead of raising an opaque TimeoutExpired
                    # traceback (more subprocess calls at N=200 raise the
                    # cumulative odds of one stall on a contended runner).
                    try:
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
                    except subprocess.TimeoutExpired:
                        entry_hook_failed = True
                payload = entry["payload"](tool_use_id)
                t0 = time.perf_counter_ns()
                try:
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
                except subprocess.TimeoutExpired:
                    # ADR-163: stall == hook failure (fail-closed, clean
                    # report instead of an uncaught traceback); the ~10s
                    # elapsed sample also breaches the ceiling by itself.
                    entry_hook_failed = True
                return (time.perf_counter_ns() - t0) / 1_000_000.0

            def _run_ref(index: int) -> float:
                nonlocal entry_ref_failed
                if sampler is not None:
                    return float(sampler(entry["name"], "ref", index))
                t0 = time.perf_counter_ns()
                # INVERTED predicate. The rail found this same class twice —
                # round-1 P1 (return code discarded) and round-2 P2 (timeout
                # left unmarked) — which per the repo's own rule means the
                # ARCHITECTURE of the cure is wrong, not the round. So the
                # reference is DISTRUSTED by default and earns trust on
                # exactly one path: the process ran to completion and exited
                # 0. A branch added later that forgets to mark failure cannot
                # reintroduce the hole, because failure is what the variable
                # already says.
                #
                # Why neither shape check can stand in for this: a fast crash
                # is a small, finite, low-drift sample, and a MINORITY of 10s
                # stalls does not move a median — measured, 3 timeouts among
                # the 40 samples give ref_p50=50.0 and split-half drift=1.000
                # against a 1.5 ceiling, so the classifier answered `pass`
                # with `ref_valid=True` over three processes that never
                # completed. The median is what makes this gate robust to
                # runner noise (ADR-163:258); that robustness is exactly what
                # blinds it here. Statistics cannot answer "did the process
                # finish".
                completed_ok = False
                try:
                    res = subprocess.run(
                        [sys.executable, str(ref_script), str(ref_dir)],
                        capture_output=True,
                        env=ref_env,
                        cwd=str(entry_tmp),
                        timeout=10,
                    )
                    completed_ok = res.returncode == 0
                except subprocess.TimeoutExpired:
                    # A stalled reference is a contention signal, not a hook
                    # verdict; it reads as infrastructure_contended.
                    pass
                if not completed_ok:
                    entry_ref_failed = True
                return (time.perf_counter_ns() - t0) / 1_000_000.0

            cold_ms = _run_once("cold", "cold", 0)
            warm: List[float] = []
            ref_samples: List[float] = []
            # ROUND-ROBIN: the reference is sampled INSIDE the hook loop, so
            # both keys price the same scheduler window. The S318 defect was
            # a probe measured once, outside the window that degraded.
            for i in range(iterations):
                # rail round-1 P2 — checked EVERY iteration, not every tenth.
                # The self-cap exists to guarantee a structured wall-capped
                # result instead of the outer 420s timeout's rc124, and the
                # stride broke that guarantee on exactly the runner it was
                # written for: one iteration can spend 10s in the seed, 10s
                # in the hook and 10s in the reference, so a check passing
                # just under the 378s deadline could be followed by ~300s
                # unchecked. `_wall_blown()` is one perf_counter subtraction;
                # paying it 200 times instead of 20 costs microseconds and is
                # not measurable against a 180ms budget.
                if second_key and i and _wall_blown():
                    wall_exceeded = True
                    break
                warm.append(_run_once("%04d" % i, "warm", i))
                # Re-checked BEFORE the reference lane: with the hook sample
                # already paid, the remaining reference runs of this same
                # iteration are the last place the overshoot can still grow.
                if second_key and _wall_blown():
                    wall_exceeded = True
                    break
                for _ in range(ref_plan[i] if i < len(ref_plan) else 0):
                    ref_samples.append(_run_ref(len(ref_samples)))
            warm_sorted = sorted(warm)
            p50 = _pct_of_sorted(warm_sorted, 50)
            p95 = _pct_of_sorted(warm_sorted, 95)
            p99 = _pct_of_sorted(warm_sorted, 99)
            p99_within = p99 <= p99_ceiling_ms
            entry_passed = (
                p95 <= p95_ceiling_ms
                and (p99_advisory or p99_within)
                and not entry_hook_failed
            )
            all_within_budget = all_within_budget and entry_passed
            hooks_out[entry["name"]] = {
                "cold_ms": round(cold_ms, 1),
                "p50_ms": round(p50, 1),
                "p95_ms": round(p95, 1),
                "p99_ms": round(p99, 1),
                "max_ms": round(max(warm_sorted) if warm_sorted else 0.0, 1),
                "hook_failed": entry_hook_failed,
                "p99_within": p99_within,
                "passed": entry_passed,
            }

            if second_key:
                ref_sorted = sorted(ref_samples)
                ref_p50 = _pct_of_sorted(ref_sorted, 50) if ref_sorted else 0.0
                ref_p95 = _pct_of_sorted(ref_sorted, 95) if ref_sorted else 0.0
                ref_drift = (
                    _split_half_drift(ref_samples)
                    if exec_reference
                    else float("inf")
                )
                k_e = k_by_entry.get(entry["name"])
                label, rel_ok, ref_valid = _classify_entry(
                    hook_p50=p50,
                    hook_p95=p95,
                    ref_p50=ref_p50,
                    ref_drift=ref_drift,
                    p95_ceiling_ms=p95_ceiling_ms,
                    k_e=k_e,
                    ref_measured=exec_reference,
                    wall_exceeded=wall_exceeded,
                    strict_relative=strict_relative,
                    ref_failed=entry_ref_failed,
                )
                stats = hooks_out[entry["name"]]
                if exec_reference:
                    stats["ref_p50_ms"] = round(ref_p50, 1)
                    stats["ref_p95_ms"] = round(ref_p95, 1)
                    stats["ref_samples"] = len(ref_samples)
                    stats["ref_split_half_drift"] = (
                        round(ref_drift, 3) if math.isfinite(ref_drift) else None
                    )
                    stats["ref_valid"] = ref_valid
                    # Published so the exit-5 has a NAME: `ref_valid=false`
                    # alone cannot tell an operator whether the reference was
                    # mis-shaped, drifting, or simply never ran.
                    stats["ref_failed"] = entry_ref_failed
                if relative_advisory or relative_k_source:
                    stats["R_e"] = (
                        round(p50 / ref_p50, 3)
                        if (exec_reference and ref_valid and ref_p50 > 0)
                        else None
                    )
                    stats["K_e"] = k_e
                    stats["rel_ok"] = rel_ok
                    stats["verdict_label"] = label
                    # Phase is a property of the ENTRY's K, not of the
                    # outcome: an entry with a usable K whose reference came
                    # back broken is still phase 2 (its verdict is exit 5),
                    # while an entry absent from the K file is phase 1.
                    stats["phase"] = (
                        "2-enforcing" if k_e is not None else "1-advisory"
                    )
                    if k_e is None and relative_k_source:
                        relative_warnings.append(
                            "relative_k_missing[%s]: no usable K in the "
                            "source file; this entry stays on phase 1 (its "
                            "label follows the absolute key alone)"
                            % entry["name"]
                        )

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
        if wall_exceeded:
            # The self-cap fired mid-entry: stop measuring rather than run
            # into the workflow's `timeout 420` (rc 124, an opaque kill).
            break

    def _entry_field(name: str, key: str, default: Any = 0) -> Any:
        """Read a per-entry field, tolerating a WALL-CAP-truncated corpus."""
        block = hooks_out.get(name)
        if not isinstance(block, dict):
            return default
        return block.get(key, default)

    # ---- Observe-rail controls (anti-vacuity, S254 class) -------------------
    on_rows = _entry_field("check_output_secrets[observe=1]", "observe_rows")
    on_paired = _entry_field(
        "check_output_secrets[observe=1]", "observe_paired_rows"
    )
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
    off_rows = _entry_field("check_output_secrets[observe=unset]", "observe_rows")
    pre_rows = _entry_field("check_anti_ceo_overhead[observe=1]", "observe_rows")
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

    passed = (
        all_within_budget
        and positive_ok
        and negative_ok
        and not wall_exceeded
    )

    report: Dict[str, Any] = {
        "schema": "profile-opus-4-7.v1",
        "mode": "hook_latency",
        "measured_at": measured_at,
        "python": sys.version.split()[0],
        "iterations": iterations,
        "p95_ceiling_ms": p95_ceiling_ms,
        "p99_ceiling_ms": p99_ceiling_ms,
        "p99_advisory": p99_advisory,
        "observe_rail_present": observe_rail_present,
        "hooks": hooks_out,
        # Back-compat: legacy consumers read this top-level block.
        "check_agent_spawn": hooks_out.get("check_agent_spawn", {}),
        "controls": {
            "observe_positive_control": positive_control,
            "observe_negative_control": negative_control,
        },
        "passed": passed,
        "note": (
            "Advisory emitters disabled (CEO_MODEL_ROUTING=0 etc.); "
            "measures governance hot-path only. Budget ADR-163 S318 "
            "amendment: p95<%.0fms hard per corpus entry; p99<%.0fms %s. "
            "PLAN-154 constraint 8: observe-rail extended write path "
            "profiled in both states with anti-vacuity controls."
            % (
                p95_ceiling_ms,
                p99_ceiling_ms,
                "ADVISORY (reported, never gates)" if p99_advisory
                else "hard (back-compat default)",
            )
        ),
    }

    # ---- second key (ADR-163 Amendment PLAN-169 S328) ----------------------
    # Every key below is ADDITIVE and appears ONLY under the new flags: a run
    # without them returns the dict above verbatim, which is the back-compat
    # contract test (e) asserts byte-for-byte.
    if second_key:
        entry_labels = [
            hooks_out[name]["verdict_label"]
            for name in hooks_out
            if isinstance(hooks_out[name], dict)
            and "verdict_label" in hooks_out[name]
        ]
        # PHASE 2 is armed by the K FILE, not by the outcome: a run whose
        # reference came back broken must still exit 5, and a wall-capped run
        # with an EMPTY corpus must never aggregate to "pass".
        any_enforced = bool(k_by_entry)
        # rail round-4 P2 — the no-labels fallback follows the ABSOLUTE key
        # instead of asserting "pass".
        #
        # `--exec-reference` without `--relative-advisory` is a supported CLI
        # combination that stores no per-entry `verdict_label`, so this list
        # is empty. Hardcoding "pass" then published a document that
        # contradicted itself — measured, with every entry over p95:
        # `passed=false`, `exit_class=1`, `verdict_label="pass"`. A JSON
        # consumer reading the label got the opposite of the exit code.
        #
        # With no labels the absolute key is the only key that ran, which is
        # exactly what phase 1 means, so the label reports what it decided.
        aggregate = (
            _aggregate_label(entry_labels)
            if entry_labels
            else ("pass" if passed else "real_regression")
        )
        if wall_exceeded:
            aggregate = "infrastructure_contended"
        any_hook_failed = any(
            isinstance(block, dict) and block.get("hook_failed")
            for block in hooks_out.values()
        )
        # rail round-2 P2 — the HARD p99 ceiling survives phase 2, scoped to
        # the entries that are NOT under amnesty.
        #
        # `_classify_entry` keys the absolute half on p95 ALONE, so an entry
        # can meet p95 and the relative key while breaching p99 and still be
        # labelled "pass". Under phase 1 that run exits 1 (`entry_passed`
        # carries `p99_advisory or p99_within`); arming phase 2 silently
        # dropped the ceiling. That "pass" cell is the hole, and it is the
        # ONLY cell that closes here.
        #
        # The `advisory_slow_runner` cell is deliberately EXEMPT, and the
        # ordering of the two ceilings is why: p99 >= p95 always, while the
        # p99 ceiling (160ms) sits BELOW the p95 one (180ms). So every entry
        # that breaches p95 breaches p99 too — a blanket p99 term makes
        # amnesty unreachable and cancels this amendment outright. (Written
        # blanket first; the pre-existing amnesty test caught it.) On an
        # entry whose slowness the relative key has already attributed to
        # the runner, the p99 breach is the same runner, not a second
        # finding.
        hard_p99_breach = (not p99_advisory) and any(
            isinstance(block, dict)
            and block.get("p99_within") is False
            and block.get("verdict_label") == "pass"
            for block in hooks_out.values()
        )
        if any_enforced:
            # PHASE 2: the relative key DECIDES. Hook failures, the two
            # observe controls and a hard p99 breach stay hard failures
            # regardless of any label.
            if (
                (not positive_ok)
                or (not negative_ok)
                or any_hook_failed
                or hard_p99_breach
            ):
                exit_class = 1
            else:
                exit_class = _LABEL_EXIT_CLASS[aggregate]
        else:
            # PHASE 1: byte-identical to today's exit contract.
            exit_class = 0 if passed else 1
        report["phase"] = "2-enforcing" if any_enforced else "1-advisory"
        report["verdict_label"] = aggregate
        report["exit_class"] = exit_class
        report["outcome_labels"] = list(_OUTCOME_LABELS)
        report["exec_reference"] = exec_reference
        report["relative_advisory"] = relative_advisory
        report["strict_relative"] = strict_relative
        report["abs_backstop_ms"] = _ABS_BACKSTOP_MS
        report["ref_drift_max"] = _REF_DRIFT_MAX
        report["wall_budget_seconds"] = float(wall_budget_seconds)
        report["wall_deadline_seconds"] = round(wall_deadline_s, 1)
        report["wall_exceeded"] = wall_exceeded
        report["elapsed_seconds"] = round(time.perf_counter() - t_gate_start, 1)
        report["relative_warnings"] = relative_warnings
        if exec_reference:
            report["ref_source_sha256"] = ref_source_sha256()
            report["ref_samples_per_entry"] = _REF_SAMPLES_PER_ENTRY
        report["relative_note"] = (
            "ADR-163 Amendment (PLAN-169 S328) second key. PHASE 1: labels "
            "are PUBLISHED and the exit code is byte-identical to the "
            "absolute-key contract — K_e is not derivable until an advisory "
            "window supplies paired (hook, reference) samples. R_e = "
            "hook_p50/ref_p50; do NOT read a single run's R_e as K."
            if not any_enforced
            else "ADR-163 Amendment (PLAN-169 S328) second key. PHASE 2: "
            "rel_ok = hook_p50 <= K_e * ref_p50 DECIDES the exit "
            "(pass/advisory_slow_runner 0, real_regression 1, "
            "infrastructure_contended 5)."
        )
    return report


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
            "Measure warm p95/p99 latency of the hook corpus (N=200 default): "
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
        default=200,
        help="Warm iteration count for --hook-latency (default 200; ADR-163 percentile-stability standard, minimum 22).",
    )
    parser.add_argument(
        "--p95-ceiling-ms",
        dest="p95_ceiling_ms",
        type=float,
        default=180.0,
        help=(
            "p95 failure ceiling in ms for --hook-latency (default 180ms; "
            "ADR-163 S318 recalibration — was 120ms)."
        ),
    )
    parser.add_argument(
        "--p99-ceiling-ms",
        dest="p99_ceiling_ms",
        type=float,
        default=160.0,
        help="p99 ceiling in ms for --hook-latency (default 160ms).",
    )
    parser.add_argument(
        "--p99-advisory",
        dest="p99_advisory",
        action="store_true",
        help=(
            "Report p99 breaches per entry (p99_within=false + WARN on "
            "stderr) WITHOUT failing the gate (ADR-163 S318 amendment: on "
            "a shared runner the extreme tail prices the runner, not the "
            "code). Default off — p99 stays a hard ceiling for back-compat."
        ),
    )
    parser.add_argument(
        "--exec-reference",
        dest="exec_reference",
        action="store_true",
        help=(
            "ADR-163 Amendment (PLAN-169 S328): also sample a FROZEN, "
            "stdlib-only 3-term EXECUTION reference (cold imports + fixed "
            "re.compile set; fixed CPU hash loop; open/append/flock/fsync/"
            "rename on the audit dir's filesystem), round-robin-interleaved "
            "inside each corpus entry's own loop. Publishes ref_p50_ms / "
            "ref_p95_ms / ref_split_half_drift per entry and a global "
            "ref_source_sha256. The spawn probe (python3 -c pass) prices "
            "process CREATION and is blind to a slow-but-uncontended runner; "
            "this prices EXECUTION."
        ),
    )
    parser.add_argument(
        "--relative-advisory",
        dest="relative_advisory",
        action="store_true",
        help=(
            "Publish the runner-normalized second key per entry: R_e = "
            "hook_p50/ref_p50 and verdict_label in {pass, "
            "advisory_slow_runner, real_regression, "
            "infrastructure_contended}. PHASE 1 — the labels are "
            "INFORMATION used to derive K_e later; exit codes stay "
            "byte-identical to the absolute-key contract."
        ),
    )
    parser.add_argument(
        "--relative-k-source",
        dest="relative_k_source",
        type=str,
        default=None,
        help=(
            "PHASE 2 (inert without this file): JSON of the form "
            '{\"entries\": {\"<entry>\": {\"K\": <float>, '
            '\"admissibility_max_K\": <float>}}}. With a usable K_e the '
            "relative key DECIDES the exit (0 pass / 0 advisory_slow_runner "
            "/ 1 real_regression / 5 infrastructure_contended). An entry "
            "with no usable K stays on phase 1 and is WARNed about."
        ),
    )
    parser.add_argument(
        "--wall-budget-seconds",
        dest="wall_budget_seconds",
        type=float,
        default=420.0,
        help=(
            "Self-cap for --hook-latency when the second key is enabled "
            "(default 420s, matching the CI wrapper's `timeout 420`). "
            "Measurement stops at 0.9x this budget and the run is labelled "
            "infrastructure_contended, so the wrapper's opaque rc 124 stays "
            "unreachable. Inert without the second-key flags."
        ),
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
                p99_advisory=args.p99_advisory,
                exec_reference=args.exec_reference,
                relative_advisory=args.relative_advisory,
                relative_k_source=args.relative_k_source,
                wall_budget_seconds=args.wall_budget_seconds,
            )
            json.dump(result, sys.stdout, indent=2)
            print()
            # ADR-163 Amendment (PLAN-169 S328): every relative-key line goes
            # to STDERR. stdout carries the JSON report (the CI wrapper
            # redirects it to a file), so a `::warning::` written there would
            # be swallowed into the report instead of annotating the run —
            # the workflow's publish() step is the step-summary channel.
            for warn_line in result.get("relative_warnings", []) or []:
                print("WARN: %s" % warn_line, file=sys.stderr)
            advisory_entries = [
                name
                for name, stats in sorted(result.get("hooks", {}).items())
                if isinstance(stats, dict)
                and stats.get("verdict_label") == "advisory_slow_runner"
            ]
            if advisory_entries:
                print(
                    "::warning::hook latency AMNESTY (advisory_slow_runner) — "
                    + "; ".join(
                        "%s p50=%.1fms ref_p50=%.1fms R=%s K=%s"
                        % (
                            name,
                            result["hooks"][name].get("p50_ms", 0.0),
                            result["hooks"][name].get("ref_p50_ms", 0.0),
                            result["hooks"][name].get("R_e"),
                            result["hooks"][name].get("K_e"),
                        )
                        for name in advisory_entries
                    ),
                    file=sys.stderr,
                )
                print(
                    "SUMMARY: %d/%d corpus entries breached the absolute p95 "
                    "ceiling but held the relative key against the execution "
                    "reference measured in the SAME window — the runner "
                    "moved, not the hooks (ADR-163 Amendment PLAN-169 S328)."
                    % (len(advisory_entries), len(result.get("hooks", {}))),
                    file=sys.stderr,
                )
            if args.p99_advisory:
                # ADR-163 S318: advisory p99 — breaches are ECHOED so the
                # drift stays visible in the CI log / step summary, but the
                # exit code never keys on them.
                p99_breaches = [
                    f"{name} p99={stats['p99_ms']:.1f}ms"
                    for name, stats in sorted(result.get("hooks", {}).items())
                    if isinstance(stats, dict)
                    and stats.get("p99_within") is False
                ]
                if p99_breaches:
                    print(
                        "WARN: hook latency p99 advisory breach — "
                        + "; ".join(p99_breaches)
                        + f" (advisory ceiling p99<"
                        f"{result.get('p99_ceiling_ms')}ms; exit unchanged)",
                        file=sys.stderr,
                    )
            # PHASE 1 keeps `exit_class == (0 if passed else 1)` by
            # construction, so this reduces to today's contract; PHASE 2 is
            # the only state that can return 5.
            final_rc = result.get("exit_class")
            if not isinstance(final_rc, int) or isinstance(final_rc, bool):
                final_rc = 0 if result["passed"] else 1
            if final_rc != 0:
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
                p99_label = (
                    "p99 advisory"
                    if result.get("p99_advisory")
                    else f"p99<{result.get('p99_ceiling_ms')}ms"
                )
                verdict = result.get("verdict_label")
                print(
                    "FAIL: hook latency gate — "
                    + ("; ".join(failures) or result.get("error", "unknown"))
                    + f" (ceilings p95<{result.get('p95_ceiling_ms')}ms / "
                    f"{p99_label})"
                    + (f" [verdict={verdict} rc={final_rc}]" if verdict else ""),
                    file=sys.stderr,
                )
                return final_rc
            return 0
    except Exception as exc:  # noqa: BLE001 — top-level safety net
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
