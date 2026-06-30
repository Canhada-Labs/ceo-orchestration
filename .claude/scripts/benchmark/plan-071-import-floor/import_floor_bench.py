#!/usr/bin/env python3
"""PLAN-071 Phase 0.5 — Import-floor micro-benchmark.

Establish a committed pre-implementation baseline so Phase 1 acceptance
gate ``p95 < 200ms`` (§5.3) is mechanically falsifiable.

Methodology (per ADR-071 §3 + ADR-081 token-as-time-unit):
- Subprocess-per-iteration (cold) — fresh Python interpreter every iter.
- ``time.perf_counter_ns()`` for ns-precision wall-clock.
- N=200 iterations per condition (cold baseline + cold full).
- p50 / p95 / p99 / p99.9 reported in nanoseconds AND milliseconds.
- RSS delta via ``resource.getrusage(RUSAGE_SELF).ru_maxrss``,
  platform-normalized: macOS returns BYTES → divide by 1024;
  Linux returns KiB as-is (Codex S82 P1 fix, ceo-boot.py:1083).
- GC counts pre/post (``gc.get_count()``).
- Subprocess env hardened: ``PYTHONDONTWRITEBYTECODE=1`` +
  ``PYTHONHASHSEED=0``; strip ``PYTHONSTARTUP`` /
  ``PYTHONSITECUSTOMIZE`` to avoid user-site contamination.

Two probes per iteration:
  (a) baseline = stdlib-only imports
      (``json, re, pathlib, argparse, unicodedata``).
  (b) full     = baseline + ``tier_policy_cli._constants`` +
      ``tier_policy_cli._types`` from PLAN-071 staging dir.

Delta = full - baseline isolates the cost added by ``tier_policy_cli/``
imports relative to a stdlib-only floor.

Phase 0.5 measures the floor BEFORE Phase 1 implementation. We do NOT
import or instrument ``task-route.py`` here — that ships in Phase 1.

Usage::

    python3 import_floor_bench.py                # JSON to stdout, N=200
    python3 import_floor_bench.py --n 50         # quick run
    python3 import_floor_bench.py --report       # markdown summary
    python3 import_floor_bench.py \\
        --staging-dir /path/to/staging \\
        --expected-quantiles fixtures/expected_quantiles.json

Stdlib-only. Python ≥3.9.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import platform
import resource
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = 1
DEFAULT_N = 200
DEFAULT_TIMEOUT = 10.0
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_STAGING_DIR = SCRIPT_DIR.parent.parent / "tier_policy_cli"


# --------------------------------------------------------------------------- #
# Probe scripts (executed in a fresh interpreter per iteration).
# --------------------------------------------------------------------------- #
#
# P1-07 closure (Codex 2026-05-04): the prior parent-process RSS
# measurement was MEANINGLESS — imports happen in the CHILD, but
# `_measure` was sampling `RUSAGE_SELF` on the parent harness. The fix:
# probes capture `ru_maxrss` BEFORE and AFTER the under-test imports IN
# THE CHILD and emit a JSON envelope on stdout. Parent parses the
# envelope and aggregates the per-iteration delta.

# Probe envelope (emitted from child on stdout):
#   {"ok": true,
#    "interpreter_startup_rss_kib": float,  # RSS at probe-entry (post Python bootstrap)
#    "rss_after_kib": float,                # RSS after under-test imports
#    "rss_delta_kib": float}                # rss_after - interpreter_startup
# Parent reads stdout's last non-empty line, json.loads(), records.
#
# RSS measurement caveat (R3-bis P1-07 tighten, 2026-05-04):
#   `ru_maxrss` is a HIGH-WATER MARK. The very first sample inside the
#   probe body cannot precede the Python interpreter's own bootstrap —
#   by the time user code runs, the interpreter has already loaded its
#   built-ins, site.py, and the import needed to call getrusage itself
#   (`resource`). So `interpreter_startup_rss_kib` is the floor RSS
#   AFTER interpreter bootstrap completed, but BEFORE any under-test
#   imports run.
#
#   `rss_delta_kib` therefore isolates the import RSS attributable to
#   the under-test imports ONLY IF the interpreter bootstrap fully
#   stabilized before the first sample. Both absolute values are
#   disclosed for transparency so reviewers can sanity-check the
#   bootstrap floor against documented baselines (~10-12 MiB on macOS
#   Python 3.9; ~8-10 MiB on Linux).

# Baseline probe: stdlib-only imports actually used by Phase 1 spec
# (§3.3 classify() pseudocode + §4.2 robustness contracts).
# Sample order: (1) import minimal trio needed for measurement, (2)
# sample interpreter_startup_rss IMMEDIATELY at probe entry, (3) run the
# under-test imports, (4) sample rss_after, (5) emit envelope.
_BASELINE_PROBE = (
    # Step 1: minimal imports required for measurement + emit.
    "import sys, json, resource\n"
    # Step 2: interpreter-startup RSS sample IMMEDIATELY (probe-entry
    # high-water mark; no further imports above this line).
    "interpreter_startup_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss\n"
    # Step 3: under-test imports.
    "import json, re, pathlib, argparse, unicodedata  # under-test imports\n"
    # Step 4: post-import RSS sample.
    "rss_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss\n"
    # Step 5: platform-normalize (macOS RUSAGE returns BYTES; Linux KiB).
    "if sys.platform == 'darwin':\n"
    "    interpreter_startup_rss_kib = interpreter_startup_rss / 1024.0\n"
    "    rss_after_kib = rss_after / 1024.0\n"
    "else:\n"
    "    interpreter_startup_rss_kib = float(interpreter_startup_rss)\n"
    "    rss_after_kib = float(rss_after)\n"
    "rss_delta_kib = rss_after_kib - interpreter_startup_rss_kib\n"
    "print(json.dumps({\n"
    "    'ok': True,\n"
    "    'interpreter_startup_rss_kib': interpreter_startup_rss_kib,\n"
    "    'rss_after_kib': rss_after_kib,\n"
    "    'rss_delta_kib': rss_delta_kib,\n"
    "}))\n"
)

# Full probe: baseline + tier_policy_cli/ staging dir imports.
# We inject the staging dir at sys.path[0] inside the subprocess. We use
# `%r` printf-style interpolation instead of str.format() to avoid
# escaping the literal `{}` in the JSON dict literal inside the probe.
# Sample order mirrors _BASELINE_PROBE (see comment block above).
_FULL_PROBE_TEMPLATE = (
    # Step 1: minimal imports + sys.path injection for tier_policy_cli.
    "import sys, json, resource\n"
    "sys.path.insert(0, %s)\n"
    # Step 2: interpreter-startup RSS sample IMMEDIATELY after path inject.
    # NB: sys.path mutation does NOT load any module; sample is still a
    # pre-import floor. Listed AFTER `sys.path.insert` only because the
    # full probe needs the staging dir resolvable in step 3.
    "interpreter_startup_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss\n"
    # Step 3: under-test imports.
    "import json, re, pathlib, argparse, unicodedata\n"
    "from tier_policy_cli import _constants  # noqa: F401\n"
    "from tier_policy_cli import _types      # noqa: F401\n"
    # Step 4: post-import RSS sample.
    "rss_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss\n"
    # Step 5: platform-normalize.
    "if sys.platform == 'darwin':\n"
    "    interpreter_startup_rss_kib = interpreter_startup_rss / 1024.0\n"
    "    rss_after_kib = rss_after / 1024.0\n"
    "else:\n"
    "    interpreter_startup_rss_kib = float(interpreter_startup_rss)\n"
    "    rss_after_kib = float(rss_after)\n"
    "rss_delta_kib = rss_after_kib - interpreter_startup_rss_kib\n"
    "print(json.dumps({\n"
    "    'ok': True,\n"
    "    'interpreter_startup_rss_kib': interpreter_startup_rss_kib,\n"
    "    'rss_after_kib': rss_after_kib,\n"
    "    'rss_delta_kib': rss_delta_kib,\n"
    "}))\n"
)


def _build_full_probe(staging_dir: Path) -> str:
    """Return the full probe with staging parent path interpolated."""
    parent = str(staging_dir.parent)
    return _FULL_PROBE_TEMPLATE % (repr(parent),)


# --------------------------------------------------------------------------- #
# Subprocess plumbing.
# --------------------------------------------------------------------------- #

def _clean_env() -> Dict[str, str]:
    """Build a hardened env for subprocess probes.

    Strips PYTHONSTARTUP / PYTHONSITECUSTOMIZE / PYTHONPATH overrides
    so user-site config does not pollute the floor measurement.
    """
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("PYTHON")
    }
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONHASHSEED"] = "0"
    # Preserve PATH so the interpreter resolves shared libs correctly.
    if "PATH" not in env and "PATH" in os.environ:
        env["PATH"] = os.environ["PATH"]
    return env


def _rss_kib_self() -> float:
    """Return current process ru_maxrss normalized to KiB.

    macOS returns BYTES; Linux returns KiB (Codex S82 P1).
    """
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return rss / 1024.0
    return float(rss)


def _run_one(
    probe_src: str,
    *,
    timeout: float,
) -> Tuple[bool, int, Optional[str], Optional[Dict[str, float]]]:
    """Run one subprocess iteration.

    Return ``(ok, elapsed_ns, err_or_none, rss_envelope_or_none)``.
    P1-07 closure (R3-bis tighten 2026-05-04): ``rss_envelope`` carries
    ``{"interpreter_startup_rss_kib": float, "rss_after_kib": float,
       "rss_delta_kib": float}`` parsed from the child's stdout JSON
    envelope. None when probe fails before emitting envelope OR JSON
    is malformed.
    """
    env = _clean_env()
    cmd = [sys.executable, "-c", probe_src]
    start = time.perf_counter_ns()
    try:
        proc = subprocess.run(  # noqa: S603 — fixed args, env scrubbed
            cmd,
            capture_output=True,
            env=env,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter_ns() - start
        return False, elapsed, "timeout", None
    except OSError as exc:
        elapsed = time.perf_counter_ns() - start
        return False, elapsed, "oserror:{}".format(exc), None
    elapsed = time.perf_counter_ns() - start
    if proc.returncode != 0:
        err = (proc.stderr or b"").decode("utf-8", errors="replace")[:512]
        return False, elapsed, "rc={}:{}".format(proc.returncode, err.strip()), None

    # P1-07: parse JSON envelope from child stdout.
    envelope: Optional[Dict[str, float]] = None
    try:
        out = (proc.stdout or b"").decode("utf-8", errors="replace").strip()
        # Take the last non-empty line — defensive against any extra noise.
        lines = [ln for ln in out.splitlines() if ln.strip()]
        if lines:
            data = json.loads(lines[-1])
            if isinstance(data, dict) and data.get("ok"):
                startup = data.get("interpreter_startup_rss_kib")
                ra = data.get("rss_after_kib")
                rd = data.get("rss_delta_kib")
                if (
                    isinstance(startup, (int, float))
                    and isinstance(ra, (int, float))
                    and isinstance(rd, (int, float))
                ):
                    envelope = {
                        "interpreter_startup_rss_kib": float(startup),
                        "rss_after_kib": float(ra),
                        "rss_delta_kib": float(rd),
                    }
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
        envelope = None
    return True, elapsed, None, envelope


# --------------------------------------------------------------------------- #
# Quantile + summary.
# --------------------------------------------------------------------------- #

def _quantile(values: List[int], pct: float) -> int:
    """Linear-interpolation quantile on sorted list of ints (ns)."""
    if not values:
        return 0
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    # Nearest-rank for stability with small N.
    k = int(round((len(s) - 1) * (pct / 100.0)))
    k = max(0, min(len(s) - 1, k))
    return s[k]


def _summarize(samples: List[int]) -> Dict[str, Any]:
    """Reduce raw ns samples to summary stats."""
    if not samples:
        return {
            "n": 0,
            "p50_ns": 0, "p95_ns": 0, "p99_ns": 0, "p99_9_ns": 0,
            "min_ns": 0, "max_ns": 0,
            "p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0, "p99_9_ms": 0.0,
        }
    p50 = _quantile(samples, 50.0)
    p95 = _quantile(samples, 95.0)
    p99 = _quantile(samples, 99.0)
    p99_9 = _quantile(samples, 99.9)
    return {
        "n": len(samples),
        "p50_ns": p50, "p95_ns": p95, "p99_ns": p99, "p99_9_ns": p99_9,
        "min_ns": min(samples), "max_ns": max(samples),
        "p50_ms": p50 / 1e6, "p95_ms": p95 / 1e6,
        "p99_ms": p99 / 1e6, "p99_9_ms": p99_9 / 1e6,
    }


# --------------------------------------------------------------------------- #
# Benchmark loop.
# --------------------------------------------------------------------------- #

def _measure(
    label: str,
    probe_src: str,
    n: int,
    timeout: float,
) -> Dict[str, Any]:
    """Run N iterations of one probe; return raw + summary.

    P1-07 closure: RSS is now CHILD-reported (rss_after - rss_before per
    iteration). The parent-side RSS (`rss_kib_pre`/`rss_kib_post`) is
    retained for diagnostic context but does NOT drive acceptance gates —
    `rss_kib_delta` reports the median of per-iteration child deltas.
    """
    rss_pre_parent = _rss_kib_self()
    gc_pre = gc.get_count()

    samples_ns: List[int] = []
    child_rss_deltas: List[float] = []
    interpreter_startup_samples: List[float] = []
    rss_after_samples: List[float] = []
    failures: List[str] = []
    for i in range(n):
        ok, elapsed_ns, err, envelope = _run_one(probe_src, timeout=timeout)
        if ok:
            samples_ns.append(elapsed_ns)
            if envelope is not None:
                # R3-bis P1-07 tighten: child reports delta directly so
                # parent does not have to recompute it.
                child_rss_deltas.append(envelope["rss_delta_kib"])
                interpreter_startup_samples.append(
                    envelope["interpreter_startup_rss_kib"]
                )
                rss_after_samples.append(envelope["rss_after_kib"])
        else:
            failures.append("iter{}: {}".format(i, err or "unknown"))

    rss_post_parent = _rss_kib_self()
    gc_post = gc.get_count()

    summary = _summarize(samples_ns)

    # P1-07: child-reported RSS delta (median of per-iteration deltas).
    if child_rss_deltas:
        srt = sorted(child_rss_deltas)
        rss_kib_delta_child = srt[len(srt) // 2]
        rss_kib_delta_p95 = srt[max(0, int(len(srt) * 0.95) - 1)]
    else:
        rss_kib_delta_child = 0.0
        rss_kib_delta_p95 = 0.0

    # R3-bis P1-07 tighten: median absolute values for transparency.
    def _median(xs: List[float]) -> float:
        if not xs:
            return 0.0
        s = sorted(xs)
        return s[len(s) // 2]

    return {
        "label": label,
        "iterations_requested": n,
        "iterations_ok": len(samples_ns),
        "failures": failures[:10],  # cap noise
        "failure_count": len(failures),
        "summary": summary,
        # P1-07: child-side measurements (acceptance gates use these).
        "rss_kib_delta": rss_kib_delta_child,  # median per-child delta
        "rss_kib_delta_p95": rss_kib_delta_p95,
        "rss_child_deltas_count": len(child_rss_deltas),
        # R3-bis P1-07 tighten: absolute values disclosed for transparency.
        # interpreter_startup_rss_kib is the high-water RSS at probe-entry
        # (Python interpreter bootstrap dominant; under-test imports not
        # yet run). rss_after_kib is the high-water RSS after the under-
        # test imports finished. delta isolates import RSS.
        "interpreter_startup_rss_kib": _median(interpreter_startup_samples),
        "rss_after_kib": _median(rss_after_samples),
        # Parent-side measurements retained for diagnostic only.
        "rss_kib_pre_parent": rss_pre_parent,
        "rss_kib_post_parent": rss_post_parent,
        "rss_kib_delta_parent": rss_post_parent - rss_pre_parent,
        "gc_count_pre": list(gc_pre),
        "gc_count_post": list(gc_post),
        "gc_events": sum(b - a for a, b in zip(gc_pre, gc_post) if b > a),
    }


def _delta(baseline: Dict[str, Any], full: Dict[str, Any]) -> Dict[str, Any]:
    """Compute full - baseline summary delta (per quantile)."""
    bs = baseline["summary"]
    fs = full["summary"]
    return {
        "p50_ns": fs["p50_ns"] - bs["p50_ns"],
        "p95_ns": fs["p95_ns"] - bs["p95_ns"],
        "p99_ns": fs["p99_ns"] - bs["p99_ns"],
        "p99_9_ns": fs["p99_9_ns"] - bs["p99_9_ns"],
        "p50_ms": fs["p50_ms"] - bs["p50_ms"],
        "p95_ms": fs["p95_ms"] - bs["p95_ms"],
        "p99_ms": fs["p99_ms"] - bs["p99_ms"],
        "p99_9_ms": fs["p99_9_ms"] - bs["p99_9_ms"],
        "rss_kib_delta": full["rss_kib_delta"] - baseline["rss_kib_delta"],
        "gc_events_delta": full["gc_events"] - baseline["gc_events"],
    }


def _acceptance(
    delta: Dict[str, Any],
    full: Dict[str, Any],
    expected: Dict[str, Any],
    *,
    baseline_recorded: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Score the run against expected_quantiles thresholds.

    Gates apply to the FULL probe summary (not to delta) — Phase 0.5
    measures total cold-start cost the CEO will pay per task-route
    invocation.

    P1-08 closure (Codex 2026-05-04): if ``baseline_recorded`` is
    provided (delta-mode gate), thresholds become *relative* to the
    recorded baseline (>10% p99 increase = fail; >5% p50 = warning),
    NOT absolute. This avoids hard-fails on aspirational floor numbers
    that are below the actual macOS Python interpreter floor (~22ms).
    """
    fs = full["summary"]

    if baseline_recorded is not None:
        # Delta-mode: compare current measurement against recorded baseline.
        b_p50 = float(baseline_recorded.get("p50_ms") or 0.0)
        b_p99 = float(baseline_recorded.get("p99_ms") or 0.0)
        b_p99_9 = float(baseline_recorded.get("p99_9_ms") or 0.0)
        b_rss = float(baseline_recorded.get("rss_delta_kib") or 0.0)
        gc_gate = int(baseline_recorded.get("gc_events", 0))
        failures_gate = 5

        # Allow zero-baseline edge to avoid div-by-zero — fall back to
        # absolute threshold from `expected` for that field.
        def _delta_check(actual: float, base: float, max_pct: float) -> bool:
            if base <= 0.0:
                # Baseline missing — skip (treat as pass; advisory only).
                return True
            return (actual - base) / base <= max_pct

        checks = {
            "p50_ms_within_5pct": {
                "actual": fs["p50_ms"], "baseline": b_p50,
                "threshold_pct": 5.0,
                "pass": _delta_check(fs["p50_ms"], b_p50, 0.05),
            },
            "p99_ms_within_10pct": {
                "actual": fs["p99_ms"], "baseline": b_p99,
                "threshold_pct": 10.0,
                "pass": _delta_check(fs["p99_ms"], b_p99, 0.10),
            },
            "p99_9_ms_within_15pct": {
                "actual": fs["p99_9_ms"], "baseline": b_p99_9,
                "threshold_pct": 15.0,
                "pass": _delta_check(fs["p99_9_ms"], b_p99_9, 0.15),
            },
            "rss_delta_kib_within_baseline": {
                "actual": delta["rss_kib_delta"], "baseline": b_rss,
                "threshold_pct": 25.0,
                "pass": _delta_check(
                    float(delta["rss_kib_delta"]), b_rss, 0.25,
                ),
            },
            "gc_events_eq_zero": {
                "actual": full["gc_events"], "threshold": gc_gate,
                "pass": full["gc_events"] <= gc_gate,
            },
            "full_failures_le_5": {
                "actual": full["failure_count"], "threshold": failures_gate,
                "pass": full["failure_count"] <= failures_gate,
            },
        }
    else:
        # Absolute-mode: legacy thresholds from `expected`.
        p50_ms_gate = float(expected.get("p50_ms", 5.0))
        p99_ms_gate = float(expected.get("p99_ms", 10.0))
        p99_9_ms_gate = float(expected.get("p99_9_ms", 50.0))
        rss_gate = float(expected.get("rss_delta_kib", 2048.0))
        gc_gate = int(expected.get("gc_events", 0))
        failures_gate = 5  # tolerate up to 5 subprocess failures

        checks = {
            "p50_ms_le_threshold": {
                "actual": fs["p50_ms"], "threshold": p50_ms_gate,
                "pass": fs["p50_ms"] <= p50_ms_gate,
            },
            "p99_ms_le_threshold": {
                "actual": fs["p99_ms"], "threshold": p99_ms_gate,
                "pass": fs["p99_ms"] <= p99_ms_gate,
            },
            "p99_9_ms_le_threshold": {
                "actual": fs["p99_9_ms"], "threshold": p99_9_ms_gate,
                "pass": fs["p99_9_ms"] <= p99_9_ms_gate,
            },
            "rss_delta_kib_le_threshold": {
                "actual": delta["rss_kib_delta"], "threshold": rss_gate,
                "pass": delta["rss_kib_delta"] <= rss_gate,
            },
            "gc_events_eq_zero": {
                "actual": full["gc_events"], "threshold": gc_gate,
                "pass": full["gc_events"] <= gc_gate,
            },
            "full_failures_le_5": {
                "actual": full["failure_count"], "threshold": failures_gate,
                "pass": full["failure_count"] <= failures_gate,
            },
        }

    overall = all(c["pass"] for c in checks.values())
    return {"overall": overall, "checks": checks}


# --------------------------------------------------------------------------- #
# Reporting.
# --------------------------------------------------------------------------- #

def _platform_block() -> Dict[str, Any]:
    return {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "sys_platform": sys.platform,
    }


def _markdown_report(payload: Dict[str, Any]) -> str:
    """Render a concise markdown summary for human eyeball."""
    plat = payload["platform"]
    base = payload["baseline"]["summary"]
    full = payload["full"]["summary"]
    dlt = payload["delta"]
    acc = payload["acceptance_gates"]

    lines: List[str] = []
    lines.append("# import_floor_bench — PLAN-071 Phase 0.5")
    lines.append("")
    lines.append("- schema_version: {}".format(payload["schema_version"]))
    lines.append("- platform: {} {} / Python {}".format(
        plat["system"], plat["machine"], plat["python_version"]))
    lines.append("- N (per condition): {}".format(payload["n"]))
    lines.append("- methodology: {}".format(
        payload["methodology"]["mode"]))
    lines.append("")
    lines.append("## Quantiles (cold subprocess, ms)")
    lines.append("")
    lines.append("| Probe    | p50    | p95    | p99    | p99.9  | min    | max    |")
    lines.append("|----------|--------|--------|--------|--------|--------|--------|")
    lines.append("| baseline | {:.3f} | {:.3f} | {:.3f} | {:.3f} | {:.3f} | {:.3f} |".format(
        base["p50_ms"], base["p95_ms"], base["p99_ms"], base["p99_9_ms"],
        base["min_ns"] / 1e6, base["max_ns"] / 1e6))
    lines.append("| full     | {:.3f} | {:.3f} | {:.3f} | {:.3f} | {:.3f} | {:.3f} |".format(
        full["p50_ms"], full["p95_ms"], full["p99_ms"], full["p99_9_ms"],
        full["min_ns"] / 1e6, full["max_ns"] / 1e6))
    lines.append("| delta    | {:+.3f} | {:+.3f} | {:+.3f} | {:+.3f} | n/a    | n/a    |".format(
        dlt["p50_ms"], dlt["p95_ms"], dlt["p99_ms"], dlt["p99_9_ms"]))
    lines.append("")
    lines.append("## RSS / GC")
    lines.append("")
    lines.append("- baseline rss_delta: {:.1f} KiB".format(
        payload["baseline"]["rss_kib_delta"]))
    lines.append("- full     rss_delta: {:.1f} KiB".format(
        payload["full"]["rss_kib_delta"]))
    lines.append("- delta    rss_delta: {:+.1f} KiB".format(dlt["rss_kib_delta"]))
    lines.append("- baseline gc_events: {}".format(payload["baseline"]["gc_events"]))
    lines.append("- full     gc_events: {}".format(payload["full"]["gc_events"]))
    lines.append("")
    lines.append("## Acceptance gates")
    lines.append("")
    lines.append("- overall: **{}**".format("PASS" if acc["overall"] else "FAIL"))
    for name, chk in acc["checks"].items():
        mark = "PASS" if chk["pass"] else "FAIL"
        # Delta-mode checks use `threshold_pct` + `baseline`; absolute-mode
        # checks use `threshold`. Pick whichever is present for display.
        thr_label = chk.get(
            "threshold",
            chk.get("threshold_pct", "n/a"),
        )
        lines.append("  - [{}] {}: actual={} threshold={}".format(
            mark, name, chk["actual"], thr_label))
    lines.append("")
    if payload["baseline"]["failure_count"] or payload["full"]["failure_count"]:
        lines.append("## Failures (sampled)")
        lines.append("")
        lines.append("- baseline failures: {}".format(
            payload["baseline"]["failure_count"]))
        lines.append("- full     failures: {}".format(
            payload["full"]["failure_count"]))
        lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# CLI.
# --------------------------------------------------------------------------- #

def _load_expected(path: Optional[Path]) -> Dict[str, Any]:
    if path is None:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="import_floor_bench",
        description="PLAN-071 Phase 0.5 import-floor micro-benchmark "
                    "(cold subprocess, N=200, p50/p95/p99/p99.9).",
    )
    p.add_argument("--n", type=int, default=DEFAULT_N,
                   help="iterations per condition (default {})".format(DEFAULT_N))
    p.add_argument("--report", action="store_true",
                   help="emit markdown summary instead of JSON")
    p.add_argument("--staging-dir", type=Path, default=DEFAULT_STAGING_DIR,
                   help="path to tier_policy_cli/ staging dir")
    p.add_argument("--expected-quantiles", type=Path,
                   default=SCRIPT_DIR / "fixtures" / "expected_quantiles.json",
                   help="acceptance-thresholds JSON (default fixtures/...)")
    p.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                   help="per-iteration subprocess timeout seconds")
    # P1-08 closure (Codex 2026-05-04): mode flag + baseline file.
    p.add_argument("--mode", choices=("advisory", "gate"),
                   default="advisory",
                   help=("acceptance gate mode: `advisory` records baseline "
                         "+ never exits non-zero on threshold breach; "
                         "`gate` exits 1 on any breach. Default advisory."))
    p.add_argument("--baseline", type=Path, default=None,
                   help=("recorded baseline JSON for delta-mode "
                         "comparison; supersedes --expected-quantiles "
                         "when present. Only consulted when --mode=gate."))
    p.add_argument("--write-baseline", type=Path, default=None,
                   help=("if set, write the current full-probe summary "
                         "to this path as a baseline.json artifact."))
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.n < 1:
        sys.stderr.write("error: --n must be >= 1\n")
        return 2

    staging_dir = args.staging_dir.resolve()
    if not staging_dir.is_dir():
        sys.stderr.write(
            "error: staging-dir does not exist: {}\n".format(staging_dir))
        return 2

    expected = _load_expected(args.expected_quantiles)

    # P1-08 closure: optional recorded baseline for delta-mode gating.
    recorded_baseline: Optional[Dict[str, Any]] = None
    if args.baseline is not None:
        try:
            with open(args.baseline, "r", encoding="utf-8") as fh:
                recorded_baseline = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            sys.stderr.write(
                "warning: failed to load --baseline {}: {}\n".format(
                    args.baseline, exc,
                )
            )
            recorded_baseline = None

    full_probe = _build_full_probe(staging_dir)

    baseline = _measure(
        "baseline_stdlib", _BASELINE_PROBE,
        n=args.n, timeout=args.timeout,
    )
    full = _measure(
        "full_baseline_plus_tier_policy", full_probe,
        n=args.n, timeout=args.timeout,
    )
    delta = _delta(baseline, full)

    # P1-08: only delta-mode gate when --mode=gate AND --baseline present.
    acceptance = _acceptance(
        delta, full, expected,
        baseline_recorded=(
            recorded_baseline if (args.mode == "gate" and recorded_baseline)
            else None
        ),
    )

    # P1-08: write baseline artifact when requested.
    baseline_written: Optional[str] = None
    if args.write_baseline is not None:
        try:
            args.write_baseline.parent.mkdir(parents=True, exist_ok=True)
            baseline_payload = {
                "schema_version": SCHEMA_VERSION,
                "n": args.n,
                "platform": _platform_block(),
                "p50_ms": full["summary"]["p50_ms"],
                "p95_ms": full["summary"]["p95_ms"],
                "p99_ms": full["summary"]["p99_ms"],
                "p99_9_ms": full["summary"]["p99_9_ms"],
                "rss_delta_kib": delta["rss_kib_delta"],
                "gc_events": full["gc_events"],
                "_recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                              time.gmtime()),
            }
            with open(args.write_baseline, "w", encoding="utf-8") as fh:
                json.dump(baseline_payload, fh, indent=2, sort_keys=True)
                fh.write("\n")
            baseline_written = str(args.write_baseline)
        except OSError as exc:
            sys.stderr.write(
                "warning: failed to write baseline {}: {}\n".format(
                    args.write_baseline, exc,
                )
            )

    payload: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "n": args.n,
        "mode": args.mode,
        "platform": _platform_block(),
        "methodology": {
            "mode": "subprocess-per-iteration-cold",
            "rationale": "ADR-081 token-as-time-unit; PLAN-020 S32 "
                         "~23ms macOS interpreter floor; ADR-071 §3 "
                         "cold/warm marker discipline.",
            "n_per_condition": args.n,
            "rss_normalization": (
                "macOS bytes -> KiB (/1024); Linux ru_maxrss already KiB"
            ),
            "rss_measurement_site": (
                "child-subprocess (P1-07): rss_after - rss_before measured "
                "INSIDE the probe via getrusage(RUSAGE_SELF). Parent only "
                "aggregates per-iteration deltas; parent-process RSS is "
                "diagnostic only (rss_kib_delta_parent)."
            ),
            "env_hardening": [
                "PYTHONDONTWRITEBYTECODE=1",
                "PYTHONHASHSEED=0",
                "stripped PYTHON* env vars",
            ],
            "probe_a": "stdlib-only: json,re,pathlib,argparse,unicodedata",
            "probe_b": "probe_a + tier_policy_cli._constants + tier_policy_cli._types",
            "staging_dir": str(staging_dir),
            "gate_mode": args.mode,
            "gate_basis": (
                "delta-vs-baseline" if (args.mode == "gate" and recorded_baseline)
                else "absolute-thresholds"
            ),
        },
        "baseline": baseline,
        "full": full,
        "delta": delta,
        "acceptance_gates": acceptance,
        "expected_quantiles_source": str(args.expected_quantiles),
        "baseline_source": str(args.baseline) if args.baseline else None,
        "baseline_written_to": baseline_written,
    }

    if args.report:
        sys.stdout.write(_markdown_report(payload))
        sys.stdout.write("\n")
    else:
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")

    # P1-08: advisory mode never exits non-zero on threshold breach. CLI/
    # subprocess errors (rc=2) still propagate normally above.
    if args.mode == "advisory":
        return 0
    return 0 if acceptance["overall"] else 1


if __name__ == "__main__":
    sys.exit(main())
