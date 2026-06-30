#!/usr/bin/env python3
"""token-budget-guard.py — runtime pause-and-ask guard for plan token budgets.

PLAN-083 Wave 0a sub-agent 0.4 deliverable. Stdlib-only (Python >= 3.9).

Purpose
-------
Intercepts when cumulative token spend on a plan exceeds the pre-task
estimate produced by sub-agent 0.2's `token-estimator.py`. Designed to be
called from `/ceo-boot`, a future PreToolUse hook, or directly by the CEO
between waves.

Two CLI modes
-------------
1. ``check --plan-id PLAN-NNN [--threshold 0.80] [--json]``
   - Read audit-log.jsonl entries scoped to ``plan_id``, sum tokens, compare
     against the estimate file ``<plan-id>.tokens.estimate`` (sibling of the
     plan markdown OR co-located in staging). Exit code 0 if ratio <
     threshold, 1 if ratio >= threshold (caller pauses).
   - First over-threshold detection within the dedup window emits a
     ``token_budget_guard_paused`` audit action; subsequent retries within
     the same window are silent (suppress duplicate emits).

2. ``auto-pause-hook --plan-id PLAN-NNN [--threshold 0.80]``
   - Designed to be invoked by `/ceo-boot` or a future hook. Outputs a JSON
     object on stdout: ``{"decision": "pause"|"continue", "reason": <str>,
     "plan_id": ..., "estimate_tokens": ..., "actual_tokens": ..., "ratio": ...}``.
   - Always exit 0 (callers parse JSON; HookSpec contract requires fail-open).

Safety / Sec MF-3 contract
--------------------------
- Plan IDs are validated against ``^PLAN-[0-9]{3}$`` before any audit emit
  or filename construction (no path traversal).
- Only ``{plan_id, estimate_tokens, actual_tokens, ratio_basis_points}``
  are persisted to audit events — NEVER any token TEXT, prompt body, file
  paths, or estimator metadata. Sec MF-3 field allowlist deny-by-default.
- Volume cap ≤10 emits / sliding 1h window per AC5c (PLAN-083 §6). When
  cap is hit, downgrades to silent allow and writes a once-per-window
  stderr warning.
- Fail-open on missing estimate file: stderr warning + exit 0 (no pause).
- Float ratio converted to int basis points (×1000) before persisting to
  match the canonical-json no-float invariant from PLAN-078 W1+W2 fix-pack.

Audit action: ``token_budget_guard_paused``
- Field allowlist: ``{plan_id, estimate_tokens, actual_tokens,
  ratio_basis_points, threshold_basis_points}``
- Must be registered in 4 sources atomically per S100 L6:
  1. ``_lib/audit_emit.py`` _KNOWN_ACTIONS
  2. SPEC/v1/audit-log.schema.md (caller-supplied row)
  3. tests/test_audit_emit.py expected actions set
  4. tests/test_audit_emit_coverage.py::test_emit_token_budget_guard_paused_basic
  See ``patches/audit-emit-extension.patch`` for the unified diff.

Integration with 0.2 token-estimator.py
---------------------------------------
- Reads ``<plan-id>.tokens.estimate`` JSON file (single-key: ``estimate_tokens: int``;
  fields ``estimate_usd_low/high``, ``wallclock_min_low/high`` IGNORED here).
- If estimate file is absent AND ``token-estimator.py`` is on PATH, calls
  it via subprocess as a fallback (advisory; failure logged + degraded
  to "no estimate available").
- Search order for estimate file:
  1. ``$CEO_TOKEN_ESTIMATE_DIR/<plan-id>.tokens.estimate``
  2. ``.claude/plans/<plan-id>.tokens.estimate``
  3. ``.claude/plans/<plan-id>/<plan-id>.tokens.estimate``
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------

DEFAULT_THRESHOLD = 0.80
ACTION_NAME = "token_budget_guard_paused"
VOLUME_CAP_PER_HOUR = 10  # AC5c
DEDUP_WINDOW_SECONDS = 3600  # 1h sliding window

# Sec MF-3: deny-by-default field allowlist for the audit event.
# This is the caller-supplied subset; auto-baseline (action, ts, session_id,
# project, event_schema, tokens_*, hmac, hmac_error) is added by _write_event.
ALLOWED_FIELDS = frozenset({
    "plan_id",
    "estimate_tokens",
    "actual_tokens",
    "ratio_basis_points",
    "threshold_basis_points",
})

# Plan-id format guard (no path traversal; bounded length).
PLAN_ID_RE = re.compile(r"^PLAN-[0-9]{3}$")

# Repo root resolution: this file lives at
# .claude/plans/PLAN-083/staging/wave-0a/sub-0-4-token-budget-guard/token-budget-guard.py
# When promoted to `.claude/scripts/token-budget-guard.py` the parents[2]
# resolution yields the canonical repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]


# ----------------------------------------------------------------------------
# Path helpers
# ----------------------------------------------------------------------------


def _audit_log_path() -> Path:
    """Resolve audit-log.jsonl path (env-overridable, parity with audit_emit)."""
    env_path = os.environ.get("CEO_AUDIT_LOG_PATH")
    if env_path:
        return Path(env_path)
    env_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
    if env_dir:
        return Path(env_dir) / "audit-log.jsonl"
    home = os.environ.get("HOME") or str(Path.home())
    return Path(home) / ".claude" / "projects" / "ceo-orchestration" / "audit-log.jsonl"


def _state_dir() -> Path:
    """Resolve state dir for dedup + volume-cap bookkeeping."""
    env_dir = os.environ.get("CEO_BUDGET_GUARD_STATE_DIR")
    if env_dir:
        return Path(env_dir)
    home = os.environ.get("HOME") or str(Path.home())
    return Path(home) / ".claude" / "projects" / "ceo-orchestration" / "state" / "token-budget-guard"


def _estimate_paths(plan_id: str) -> List[Path]:
    """Return ordered candidate paths to look for the estimate file."""
    candidates: List[Path] = []
    env_dir = os.environ.get("CEO_TOKEN_ESTIMATE_DIR")
    if env_dir:
        candidates.append(Path(env_dir) / f"{plan_id}.tokens.estimate")
    candidates.append(REPO_ROOT / ".claude" / "plans" / f"{plan_id}.tokens.estimate")
    candidates.append(REPO_ROOT / ".claude" / "plans" / plan_id / f"{plan_id}.tokens.estimate")
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        proot = Path(project_dir)
        candidates.append(proot / ".claude" / "plans" / f"{plan_id}.tokens.estimate")
        candidates.append(proot / ".claude" / "plans" / plan_id / f"{plan_id}.tokens.estimate")
    return candidates


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ----------------------------------------------------------------------------
# Plan-id validation
# ----------------------------------------------------------------------------


def validate_plan_id(plan_id: str) -> str:
    """Validate + return canonical plan_id. Raise ValueError on mismatch."""
    if not isinstance(plan_id, str) or not PLAN_ID_RE.match(plan_id):
        raise ValueError(
            f"invalid plan_id: {plan_id!r} (expected PLAN-NNN with 3 digits)"
        )
    return plan_id


# ----------------------------------------------------------------------------
# Estimate file reader
# ----------------------------------------------------------------------------


def read_estimate(plan_id: str) -> Optional[int]:
    """Return estimate_tokens for ``plan_id`` or None if missing/unreadable.

    Search order:
      1. ``$CEO_TOKEN_ESTIMATE_DIR/<plan-id>.tokens.estimate``
      2. ``.claude/plans/<plan-id>.tokens.estimate``
      3. ``.claude/plans/<plan-id>/<plan-id>.tokens.estimate``
      4. (fallback) ``token-estimator.py`` subprocess if available
    """
    for candidate in _estimate_paths(plan_id):
        if not candidate.is_file():
            continue
        try:
            with candidate.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            print(
                f"# token-budget-guard: estimate file unreadable at "
                f"{candidate}: {type(exc).__name__}",
                file=sys.stderr,
            )
            continue
        if not isinstance(data, dict):
            continue
        est = data.get("estimate_tokens")
        if isinstance(est, int) and est > 0:
            return est
        # Allow legacy schema with high/low band: take midpoint if both ints.
        lo = data.get("estimate_tokens_low")
        hi = data.get("estimate_tokens_high")
        if isinstance(lo, int) and isinstance(hi, int) and lo > 0 and hi >= lo:
            return (lo + hi) // 2
    # Fallback: try invoking the sibling token-estimator.py via subprocess.
    # Bounded by a small timeout; failure is silent (we degrade to "no estimate").
    est_script = _find_token_estimator_script()
    if est_script is not None:
        try:
            import subprocess
            out = subprocess.run(
                [sys.executable, str(est_script), "--plan-id", plan_id, "--json"],
                capture_output=True,
                text=True,
                timeout=5.0,
                check=False,
            )
            if out.returncode == 0 and out.stdout.strip():
                payload = json.loads(out.stdout)
                est = payload.get("estimate_tokens")
                if isinstance(est, int) and est > 0:
                    return est
        except Exception:  # pragma: no cover — fallback is best-effort only
            pass
    return None


def _find_token_estimator_script() -> Optional[Path]:
    """Locate sibling token-estimator.py (post-canonical or staging)."""
    candidates = [
        REPO_ROOT / ".claude" / "scripts" / "token-estimator.py",
        Path(__file__).resolve().parent.parent / "sub-0-2-token-estimator" / "token-estimator.py",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


# ----------------------------------------------------------------------------
# Audit-log reader (sum tokens by plan_id)
# ----------------------------------------------------------------------------


def sum_actual_tokens(plan_id: str, log_path: Optional[Path] = None) -> int:
    """Sum tokens_in + tokens_out across audit events tagged with ``plan_id``.

    We accept any event with matching ``plan_id``. Null token fields count
    as zero (adapter coverage gap, not an error). This deliberately mirrors
    ``audit-query.py cmd_tokens`` semantics so the two values reconcile.
    """
    log = log_path or _audit_log_path()
    if not log.is_file():
        return 0
    total = 0
    try:
        with log.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(e, dict):
                    continue
                if e.get("plan_id") != plan_id:
                    continue
                tin = e.get("tokens_in")
                tout = e.get("tokens_out")
                if isinstance(tin, int):
                    total += tin
                if isinstance(tout, int):
                    total += tout
    except OSError as exc:
        print(
            f"# token-budget-guard: audit-log unreadable at {log}: "
            f"{type(exc).__name__}",
            file=sys.stderr,
        )
        return 0
    return total


# ----------------------------------------------------------------------------
# Volume cap + dedup state
# ----------------------------------------------------------------------------


def _state_file_for_plan(plan_id: str) -> Path:
    """Return the dedup state file path for ``plan_id`` (already validated)."""
    return _state_dir() / f"{plan_id}.dedup.json"


def _volume_cap_file() -> Path:
    return _state_dir() / "volume-cap.json"


def _load_state(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def _save_state(path: Path, data: Dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, sort_keys=True)
        os.replace(tmp, path)
    except OSError:
        pass


def should_emit_dedup(plan_id: str, now: float) -> bool:
    """Return True iff this is the FIRST over-threshold detection in the
    current dedup window. Subsequent retries within the window suppress emit.

    A fresh window starts when:
      - state file is absent
      - last-emit timestamp is older than DEDUP_WINDOW_SECONDS
    """
    sf = _state_file_for_plan(plan_id)
    state = _load_state(sf)
    last_ts = state.get("last_emit_ts")
    if isinstance(last_ts, (int, float)) and (now - last_ts) < DEDUP_WINDOW_SECONDS:
        return False
    return True


def record_emit_dedup(plan_id: str, now: float) -> None:
    """Persist the emit timestamp so subsequent retries are suppressed."""
    sf = _state_file_for_plan(plan_id)
    _save_state(sf, {"last_emit_ts": float(now)})


def check_volume_cap(now: float) -> Tuple[bool, int]:
    """Sliding-window volume cap. Returns (under_cap, current_count).

    Implementation: track emit timestamps in a JSON file under state_dir.
    Trim entries older than 1h. If count >= VOLUME_CAP_PER_HOUR, return False.
    """
    cap_file = _volume_cap_file()
    state = _load_state(cap_file)
    raw = state.get("emit_timestamps") or []
    fresh: List[float] = []
    for ts in raw:
        if isinstance(ts, (int, float)) and (now - ts) < DEDUP_WINDOW_SECONDS:
            fresh.append(float(ts))
    return (len(fresh) < VOLUME_CAP_PER_HOUR, len(fresh))


def record_volume_cap_emit(now: float) -> None:
    """Append the emit timestamp to the volume-cap sliding window."""
    cap_file = _volume_cap_file()
    state = _load_state(cap_file)
    raw = state.get("emit_timestamps") or []
    fresh: List[float] = [
        float(ts)
        for ts in raw
        if isinstance(ts, (int, float)) and (now - ts) < DEDUP_WINDOW_SECONDS
    ]
    fresh.append(float(now))
    _save_state(cap_file, {"emit_timestamps": fresh})


def warn_volume_cap_once(now: float) -> None:
    """Write at most one stderr warning per window when the cap is exhausted."""
    cap_file = _volume_cap_file()
    state = _load_state(cap_file)
    last_warn = state.get("last_warn_ts")
    if isinstance(last_warn, (int, float)) and (now - last_warn) < DEDUP_WINDOW_SECONDS:
        return
    print(
        f"# token-budget-guard: emit volume cap "
        f"({VOLUME_CAP_PER_HOUR}/hr) reached — suppressing further emits",
        file=sys.stderr,
    )
    state["last_warn_ts"] = float(now)
    _save_state(cap_file, state)


# ----------------------------------------------------------------------------
# Audit emit (with Sec MF-3 sanitization)
# ----------------------------------------------------------------------------


def sanitize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Drop any field not in ALLOWED_FIELDS. Sec MF-3 deny-by-default.

    Returns a fresh dict; never mutates the caller's input.
    """
    return {k: v for k, v in event.items() if k in ALLOWED_FIELDS}


def emit_token_budget_guard_paused(
    *,
    plan_id: str,
    estimate_tokens: int,
    actual_tokens: int,
    ratio_basis_points: int,
    threshold_basis_points: int,
    session_id: str = "",
    project: str = "",
) -> None:
    """Emit the ``token_budget_guard_paused`` audit event.

    Uses ``_lib.audit_emit`` if importable; otherwise falls back to a direct
    JSONL append into ``audit-log.jsonl``. Always fail-open: any exception
    is swallowed + breadcrumb is written to stderr.
    """
    # Try the canonical emit path first.
    try:
        # Allow the test harness or future canonical wiring to import
        # _lib.audit_emit. We never raise on import error.
        sys_path_backup = list(sys.path)
        hooks_dir = REPO_ROOT / ".claude" / "hooks"
        if hooks_dir.is_dir() and str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))
        try:
            from _lib import audit_emit as _ae  # type: ignore
        finally:
            sys.path[:] = sys_path_backup
        fn = getattr(_ae, "emit_token_budget_guard_paused", None)
        if fn is not None:
            fn(
                plan_id=plan_id,
                estimate_tokens=int(estimate_tokens),
                actual_tokens=int(actual_tokens),
                ratio_basis_points=int(ratio_basis_points),
                threshold_basis_points=int(threshold_basis_points),
                session_id=session_id,
                project=project,
            )
            return
    except Exception as exc:  # noqa: BLE001 — fail-open contract
        print(
            f"# token-budget-guard: canonical audit_emit unavailable "
            f"({type(exc).__name__}); falling back to direct write",
            file=sys.stderr,
        )

    # Fallback: direct JSONL append (Sec MF-3 sanitized).
    raw_event: Dict[str, Any] = {
        "plan_id": plan_id,
        "estimate_tokens": int(estimate_tokens),
        "actual_tokens": int(actual_tokens),
        "ratio_basis_points": int(ratio_basis_points),
        "threshold_basis_points": int(threshold_basis_points),
    }
    safe = sanitize_event(raw_event)
    safe["action"] = ACTION_NAME
    safe["ts"] = _utc_now_iso()
    safe["session_id"] = session_id
    safe["project"] = project
    safe["event_schema"] = "v2"
    safe["tokens_in"] = None
    safe["tokens_out"] = None
    safe["tokens_total"] = None
    safe["hmac"] = None
    safe["hmac_error"] = None

    log = _audit_log_path()
    try:
        log.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(safe, sort_keys=True) + "\n")
    except OSError as exc:
        print(
            f"# token-budget-guard: audit-log write failed at {log}: "
            f"{type(exc).__name__}",
            file=sys.stderr,
        )


# ----------------------------------------------------------------------------
# Core decision logic
# ----------------------------------------------------------------------------


def evaluate(
    plan_id: str,
    threshold: float,
    now: Optional[float] = None,
) -> Dict[str, Any]:
    """Run the full guard decision pipeline. Returns a verdict dict.

    Verdict keys:
      decision: "pause" | "continue"
      reason: str
      plan_id: str
      estimate_tokens: int | None
      actual_tokens: int
      ratio_basis_points: int | None
      threshold_basis_points: int
      emitted: bool — whether an audit event was actually persisted
      volume_cap_hit: bool — whether the volume cap suppressed emit
    """
    if now is None:
        now = time.time()

    plan_id = validate_plan_id(plan_id)
    threshold_bp = int(round(threshold * 1000))
    estimate = read_estimate(plan_id)
    actual = sum_actual_tokens(plan_id)

    verdict: Dict[str, Any] = {
        "decision": "continue",
        "reason": "",
        "plan_id": plan_id,
        "estimate_tokens": estimate,
        "actual_tokens": actual,
        "ratio_basis_points": None,
        "threshold_basis_points": threshold_bp,
        "emitted": False,
        "volume_cap_hit": False,
    }

    if estimate is None or estimate <= 0:
        verdict["reason"] = "no_estimate_available"
        print(
            f"# token-budget-guard: no estimate available for {plan_id}; "
            f"allow continue",
            file=sys.stderr,
        )
        return verdict

    ratio = actual / estimate if estimate > 0 else 0.0
    ratio_bp = int(round(ratio * 1000))
    verdict["ratio_basis_points"] = ratio_bp

    if ratio < threshold:
        verdict["reason"] = "under_threshold"
        return verdict

    # Over threshold. Decide pause + maybe emit (subject to dedup + cap).
    verdict["decision"] = "pause"
    verdict["reason"] = "over_threshold"

    if not should_emit_dedup(plan_id, now):
        verdict["reason"] = "over_threshold_dedup_suppressed"
        return verdict

    under_cap, _current = check_volume_cap(now)
    if not under_cap:
        verdict["volume_cap_hit"] = True
        verdict["reason"] = "over_threshold_volume_cap_suppressed"
        warn_volume_cap_once(now)
        # Still record dedup so retries respect the window.
        record_emit_dedup(plan_id, now)
        return verdict

    # Emit + record.
    emit_token_budget_guard_paused(
        plan_id=plan_id,
        estimate_tokens=int(estimate),
        actual_tokens=int(actual),
        ratio_basis_points=ratio_bp,
        threshold_basis_points=threshold_bp,
        session_id=os.environ.get("CLAUDE_SESSION_ID", ""),
        project=os.environ.get("CLAUDE_PROJECT_DIR", ""),
    )
    record_volume_cap_emit(now)
    record_emit_dedup(plan_id, now)
    verdict["emitted"] = True
    return verdict


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="token-budget-guard.py",
        description="Pause-and-ask when cumulative tokens on a plan exceed the estimate.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    check = sub.add_parser(
        "check",
        help="Check + maybe emit. Exits 1 if over threshold (caller pauses).",
    )
    check.add_argument("--plan-id", required=True, help="PLAN-NNN")
    check.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"ratio threshold 0.0..1.0 (default {DEFAULT_THRESHOLD})",
    )
    check.add_argument("--json", action="store_true", help="emit verdict JSON to stdout")

    hook = sub.add_parser(
        "auto-pause-hook",
        help="Hook mode: ALWAYS exit 0; emit verdict JSON to stdout.",
    )
    hook.add_argument("--plan-id", required=True)
    hook.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
    )

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not (0.0 <= args.threshold <= 1.0):
        print(
            f"# token-budget-guard: invalid --threshold {args.threshold} "
            f"(must be 0.0..1.0)",
            file=sys.stderr,
        )
        return 2

    try:
        verdict = evaluate(args.plan_id, args.threshold)
    except ValueError as exc:
        print(f"# token-budget-guard: {exc}", file=sys.stderr)
        return 2

    if args.command == "check":
        if args.json:
            print(json.dumps(verdict, sort_keys=True))
        else:
            est = verdict["estimate_tokens"]
            actual = verdict["actual_tokens"]
            ratio_bp = verdict["ratio_basis_points"]
            ratio_str = f"{ratio_bp/1000:.3f}" if ratio_bp is not None else "n/a"
            print(
                f"plan={verdict['plan_id']} estimate={est} actual={actual} "
                f"ratio={ratio_str} decision={verdict['decision']} "
                f"reason={verdict['reason']}"
            )
        return 1 if verdict["decision"] == "pause" else 0

    # auto-pause-hook: emit JSON, ALWAYS exit 0 (hook fail-open contract).
    print(json.dumps(verdict, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
