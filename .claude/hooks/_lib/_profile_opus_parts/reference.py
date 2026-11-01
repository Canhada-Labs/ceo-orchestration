"""Extracted implementation: reference."""
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


