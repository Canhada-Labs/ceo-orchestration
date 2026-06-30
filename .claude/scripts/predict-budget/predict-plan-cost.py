#!/usr/bin/env python3
"""predict-plan-cost — predictive budgeting for plan cost estimation.

SPEC/v1/predict-budget.schema.md v1.0.0-rc.1 (experimental).
ADR-047 §Decision: Option C (Bayesian bucketed).

- Median-based point estimate from historical plan totals
- Confidence-tier-driven bucket width (cold_start=100%, low=50%,
  medium/high=30%; one-way ratchet per §8.1)
- Training window EXCLUDES events with ``veto_triggered`` or
  ``budget_bypass_used``
- Cold-start (<3 historical plans) emits ``confidence=cold_start`` +
  bucket="unknown" — no fabricated range
- Output: bucketed tokens (e.g. ``"100k-130k"``) + schema_version +
  warnings. **No raw dollar figures** (Tier 2).

## Usage

    predict-plan-cost.py --plan-file .claude/plans/PLAN-014-*.md
    predict-plan-cost.py --plan-file <path> --json
    predict-plan-cost.py --plan-file <path> --backtest

Exit codes (SPEC §4):
    0 ok / 2 missing_input / 3 plan_parse_error / 4 audit_parse_error
    5 cache_write_error / 6 invalid_args / 7 backtest_failed

Stdlib only. Python >= 3.9 compatible.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple


# -----------------------------------------------------------------------------
# Path bootstrap
# -----------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_HOOKS_DIR = _SCRIPT_DIR.parent.parent / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _lib import audit_emit as _audit_emit  # type: ignore
except Exception:  # noqa: BLE001
    _audit_emit = None


# -----------------------------------------------------------------------------
# SPEC constants
# -----------------------------------------------------------------------------
SCHEMA_VERSION = "1.0.0-rc.1"

EXIT_OK = 0
EXIT_MISSING_INPUT = 2
EXIT_PLAN_PARSE = 3
EXIT_AUDIT_PARSE = 4
EXIT_CACHE_WRITE = 5
EXIT_INVALID_ARGS = 6
EXIT_BACKTEST_FAIL = 7

# Confidence tiers — per SPEC §5.3
CONFIDENCE_COLD_START_MAX = 2  # < 3 => cold_start
CONFIDENCE_LOW_MAX = 5          # 3..5 => low
CONFIDENCE_MEDIUM_MAX = 9       # 6..9 => medium; >=10 => high

RATIO_COLD_START = 1.0
RATIO_LOW = 0.5
RATIO_MEDIUM = 0.3
RATIO_HIGH = 0.3

# Excluded flags per ADR-047 §2.2 / SPEC §2.2
EXCLUDED_ACTIONS = {"veto_triggered", "budget_bypass_used"}

# Bounds
PLAN_FILE_MAX_BYTES = 1 * 1024 * 1024
AUDIT_LINE_CAP = 1_000_000
DEFAULT_TRAINING_WINDOW = 10
MAX_TRAINING_WINDOW = 50
CACHE_ENTRY_MAX_BYTES = 64 * 1024


# -----------------------------------------------------------------------------
# Plan file helpers
# -----------------------------------------------------------------------------


def _plan_id_from_file(path: Path) -> str:
    """Extract PLAN-NNN from frontmatter ``id:`` or filename."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    m = re.search(r"^id:\s*(PLAN-\d{3})", text, re.MULTILINE)
    if m:
        return m.group(1)
    # Fallback: parse from filename
    m2 = re.search(r"(PLAN-\d{3})", path.name)
    return m2.group(1) if m2 else ""


def _plan_id_from_any(raw: str) -> str:
    m = re.search(r"(PLAN-\d{3})", raw or "")
    return m.group(1) if m else ""


def _plan_hash(path: Path) -> str:
    """sha256 hex[:16] of plan file bytes."""
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    return hashlib.sha256(data).hexdigest()[:16]


# -----------------------------------------------------------------------------
# Audit log reader
# -----------------------------------------------------------------------------


def _default_audit_log() -> Path:
    env = os.environ.get("CEO_AUDIT_LOG_PATH")
    if env:
        return Path(env)
    home = os.environ.get("HOME") or str(Path.home())
    return Path(home) / ".claude" / "projects" / "ceo-orchestration" / "audit-log.jsonl"


class _AuditParseError(Exception):
    pass


def _read_events(path: Path, line_cap: int = AUDIT_LINE_CAP) -> Iterator[Dict[str, Any]]:
    if not path.is_file():
        return
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for lineno, line in enumerate(f, start=1):
                if lineno > line_cap:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    raise _AuditParseError(f"line {lineno}: malformed JSONL") from None
    except OSError as e:
        raise _AuditParseError(f"cannot read {path}: {e}") from e


# -----------------------------------------------------------------------------
# Training-data aggregation
# -----------------------------------------------------------------------------


def aggregate_plan_totals(
    events: Iterable[Dict[str, Any]],
) -> Tuple[Dict[str, Dict[str, int]], Dict[str, int]]:
    """Return (per_plan_totals, excluded_reasons).

    per_plan_totals: {PLAN-NNN: {tokens_in, tokens_out, tokens_total,
                                 spawn_count, excluded}}
    excluded_reasons: {action_name: count} across the whole window.
    """
    events_list = list(events)

    # First pass: mark which sessions have excluded actions (poisoning guard).
    excluded_sessions: set = set()
    excluded_reasons: Dict[str, int] = {}
    for e in events_list:
        action = e.get("action", "")
        if action in EXCLUDED_ACTIONS:
            sid = e.get("session_id", "") or ""
            if sid:
                excluded_sessions.add(sid)
            excluded_reasons[action] = excluded_reasons.get(action, 0) + 1

    # Second pass: aggregate agent_spawn tokens by plan_id, SKIPPING
    # excluded sessions entirely (conservative — drops whole session).
    per_plan: Dict[str, Dict[str, int]] = {}
    for e in events_list:
        if e.get("action") != "agent_spawn":
            continue
        sid = e.get("session_id", "") or ""
        if sid in excluded_sessions:
            continue
        pid = e.get("plan_id") or _plan_id_from_any(e.get("desc_preview", ""))
        if not pid:
            continue
        agg = per_plan.setdefault(pid, {
            "tokens_in": 0,
            "tokens_out": 0,
            "tokens_total": 0,
            "spawn_count": 0,
        })
        ti = e.get("tokens_in")
        to = e.get("tokens_out")
        if isinstance(ti, int):
            agg["tokens_in"] += ti
        if isinstance(to, int):
            agg["tokens_out"] += to
        agg["spawn_count"] += 1

    for pid, agg in per_plan.items():
        agg["tokens_total"] = agg["tokens_in"] + agg["tokens_out"]

    return per_plan, excluded_reasons


# -----------------------------------------------------------------------------
# Bucketing + confidence
# -----------------------------------------------------------------------------


def pick_confidence(n_plans: int) -> Tuple[str, float]:
    """Return (confidence_label, ratio)."""
    if n_plans <= CONFIDENCE_COLD_START_MAX:
        return "cold_start", RATIO_COLD_START
    if n_plans <= CONFIDENCE_LOW_MAX:
        return "low", RATIO_LOW
    if n_plans <= CONFIDENCE_MEDIUM_MAX:
        return "medium", RATIO_MEDIUM
    return "high", RATIO_HIGH


def build_bucket(point_estimate: int, ratio: float) -> str:
    """Return bucket string like ``"120k-180k"`` in thousands-of-tokens.

    Lower bound clamped to 0. Rounded to nearest 1000 then reported in k.
    """
    if point_estimate <= 0:
        return "0k-0k"
    half = point_estimate * ratio
    lower = max(0, round((point_estimate - half) / 1000) * 1000)
    upper = round((point_estimate + half) / 1000) * 1000
    if upper < lower:
        upper = lower
    return f"{lower // 1000}k-{upper // 1000}k"


# -----------------------------------------------------------------------------
# Prediction core
# -----------------------------------------------------------------------------


def predict_for_plan(
    plan_id: str,
    per_plan: Dict[str, Dict[str, int]],
    training_window: int = DEFAULT_TRAINING_WINDOW,
) -> Dict[str, Any]:
    """Produce the prediction payload for ``plan_id``.

    Selection: use ALL plans in ``per_plan`` that are NOT ``plan_id``
    itself, capped at ``training_window`` most-numerous. Naming ordering
    (PLAN-003..PLAN-013) is used as the stable sort.
    """
    other_plans = [p for p in per_plan if p != plan_id]
    other_plans.sort()
    if training_window > MAX_TRAINING_WINDOW:
        training_window = MAX_TRAINING_WINDOW
    training = other_plans[:training_window]

    confidence, ratio = pick_confidence(len(training))

    warnings: List[str] = []

    if confidence == "cold_start":
        warnings.append("cold_start")
        return {
            "tokens_in_bucket": "unknown",
            "tokens_out_bucket": "unknown",
            "tokens_total_bucket": "unknown",
            "confidence": confidence,
            "bucket_half_width_ratio": ratio,
            "bucketing_strategy": "relative_ci",
            "training_plans": training,
            "point_in": 0,
            "point_out": 0,
            "point_total": 0,
            "warnings": warnings,
        }

    ins = [per_plan[p]["tokens_in"] for p in training]
    outs = [per_plan[p]["tokens_out"] for p in training]
    totals = [per_plan[p]["tokens_total"] for p in training]

    point_in = int(statistics.median(ins)) if ins else 0
    point_out = int(statistics.median(outs)) if outs else 0
    point_total = int(statistics.median(totals)) if totals else 0

    if point_total == 0:
        warnings.append("zero_median")

    # Check for unusual spread → spread warning (high variance)
    if len(totals) >= 3 and point_total > 0:
        try:
            pstdev = statistics.pstdev(totals)
            if pstdev > 1.5 * point_total:
                warnings.append("high_variance_training")
        except statistics.StatisticsError:
            pass

    if len(training) < 6:
        warnings.append("training_window_narrow")

    return {
        "tokens_in_bucket": build_bucket(point_in, ratio),
        "tokens_out_bucket": build_bucket(point_out, ratio),
        "tokens_total_bucket": build_bucket(point_total, ratio),
        "confidence": confidence,
        "bucket_half_width_ratio": ratio,
        "bucketing_strategy": "relative_ci",
        "training_plans": training,
        "point_in": point_in,
        "point_out": point_out,
        "point_total": point_total,
        "warnings": warnings,
    }


# -----------------------------------------------------------------------------
# Cache
# -----------------------------------------------------------------------------


def _cache_dir() -> Path:
    override = os.environ.get("CEO_PREDICT_CACHE_DIR")
    if override:
        return Path(override)
    project = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if not project:
        home = os.environ.get("HOME") or str(Path.home())
        return Path(home) / ".claude" / "projects" / "ceo-orchestration" / "predict-cache"
    return Path(project) / "state" / "predict-cache"


def _write_cache(cache_dir: Path, plan_hash: str, payload: Dict[str, Any]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(cache_dir, 0o700)
    except OSError:
        pass
    path = cache_dir / f"{plan_hash}.json"
    data = json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2)
    if len(data.encode("utf-8")) > CACHE_ENTRY_MAX_BYTES:
        # Truncate training_plans list to fit cache budget (advisory)
        payload = dict(payload)
        training = payload.get("training", {})
        if isinstance(training, dict):
            training["training_plans"] = training.get("training_plans", [])[:10]
        data = json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2)
    tmp = path.with_suffix(".tmp")
    try:
        tmp.write_text(data, encoding="utf-8")
        os.replace(str(tmp), str(path))
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


# -----------------------------------------------------------------------------
# Audit emit
# -----------------------------------------------------------------------------


def _emit_query(plan_id: str, bucket_total: str, confidence: str, window: int) -> None:
    if _audit_emit is None:
        return
    try:
        _audit_emit.emit_prediction_queried(
            plan_id=plan_id,
            bucket_range=bucket_total,
            confidence=confidence,
            training_window_plans=window,
        )
    except Exception:  # noqa: BLE001
        pass


# -----------------------------------------------------------------------------
# Backtest
# -----------------------------------------------------------------------------


def backtest(
    per_plan: Dict[str, Dict[str, int]],
    training_window: int = DEFAULT_TRAINING_WINDOW,
) -> Dict[str, Any]:
    """Leave-one-out backtest: predict each historical plan's total from
    the OTHERS, compare bucket to actual.

    Returns {count, within_ci_count, within_ci_ratio, per_plan: [...]}.
    """
    plan_ids = sorted(per_plan.keys())
    results: List[Dict[str, Any]] = []
    within = 0
    for target in plan_ids:
        actual = per_plan[target]["tokens_total"]
        pred = predict_for_plan(target, per_plan, training_window)
        bucket = pred.get("tokens_total_bucket", "unknown")
        if bucket == "unknown":
            within_ci = None
        else:
            try:
                lo_k, hi_k = bucket.split("-")
                lo = int(lo_k.rstrip("k")) * 1000
                hi = int(hi_k.rstrip("k")) * 1000
                within_ci = lo <= actual <= hi
            except (ValueError, IndexError):
                within_ci = None
        if within_ci:
            within += 1
        results.append({
            "plan_id": target,
            "actual_total": actual,
            "predicted_bucket": bucket,
            "confidence": pred.get("confidence"),
            "within_ci": within_ci,
        })
    denom = sum(1 for r in results if r["within_ci"] is not None)
    ratio = (within / denom) if denom else None
    return {
        "count": len(results),
        "within_ci_count": within,
        "within_ci_ratio": ratio,
        "meets_70_percent_gate": (ratio is not None and ratio >= 0.70),
        "per_plan": results,
    }


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the plan-cost predictor CLI."""
    p = argparse.ArgumentParser(
        prog="predict-plan-cost.py",
        description="Predictive budgeting for plan cost estimation (SPEC/v1/predict-budget.schema.md)",
    )
    p.add_argument("--plan-file", required=False)
    p.add_argument("--audit-log", default=None)
    p.add_argument("--training-plans", type=int, default=DEFAULT_TRAINING_WINDOW)
    p.add_argument("--confidence", choices=["ci", "low"], default="ci")
    p.add_argument("--out", choices=["stdout", "file", "cache"], default="stdout")
    p.add_argument("--cache-dir", default=None)
    p.add_argument("--backtest", action="store_true")
    p.add_argument("--no-cache", action="store_true")
    p.add_argument("--json", action="store_true", default=True,
                   help="JSON output (default)")
    return p


def _fail(code: int, name: str, detail: str) -> int:
    sys.stderr.write(
        json.dumps({"error": name, "exit": code, "detail": detail}, ensure_ascii=False) + "\n"
    )
    return code


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — project a plan's multi-model dispatch cost + tokens."""
    parser = build_parser()
    args = parser.parse_args(argv)

    log_path = Path(args.audit_log) if args.audit_log else _default_audit_log()
    events: List[Dict[str, Any]] = []
    if log_path.is_file():
        try:
            events = list(_read_events(log_path))
        except _AuditParseError as e:
            return _fail(EXIT_AUDIT_PARSE, "audit_parse_error", str(e))

    per_plan, excluded_reasons = aggregate_plan_totals(events)

    if args.backtest:
        bt = backtest(per_plan, args.training_plans)
        envelope = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _utc_iso(),
            "mode": "backtest",
            "excluded_reasons": excluded_reasons,
            "backtest": bt,
        }
        sys.stdout.write(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n")
        if bt.get("count", 0) == 0:
            return EXIT_BACKTEST_FAIL
        return EXIT_OK

    if not args.plan_file:
        return _fail(EXIT_INVALID_ARGS, "invalid_args",
                     "--plan-file is required unless --backtest")

    plan_path = Path(args.plan_file)
    if not plan_path.is_file():
        return _fail(EXIT_MISSING_INPUT, "missing_input",
                     f"plan file not found: {plan_path}")
    if plan_path.stat().st_size > PLAN_FILE_MAX_BYTES:
        return _fail(EXIT_PLAN_PARSE, "plan_parse_error",
                     f"plan file too large ({plan_path.stat().st_size} > {PLAN_FILE_MAX_BYTES})")

    plan_id = _plan_id_from_file(plan_path)
    if not plan_id:
        return _fail(EXIT_PLAN_PARSE, "plan_parse_error",
                     "could not extract PLAN-NNN id from frontmatter or filename")

    plan_hash = _plan_hash(plan_path)

    pred = predict_for_plan(plan_id, per_plan, args.training_plans)

    training_obj = {
        "historical_plans_count": len([p for p in per_plan if p != plan_id]),
        "training_plans": pred.get("training_plans", []),
        "excluded_event_count": sum(excluded_reasons.values()),
        "excluded_reasons": excluded_reasons,
        "median_tokens_in": pred.get("point_in", 0),
        "median_tokens_out": pred.get("point_out", 0),
    }

    envelope = {
        "schema_version": SCHEMA_VERSION,
        "plan_id": plan_id,
        "plan_hash": plan_hash,
        "prediction": {
            "tokens_in_bucket": pred["tokens_in_bucket"],
            "tokens_out_bucket": pred["tokens_out_bucket"],
            "tokens_total_bucket": pred["tokens_total_bucket"],
            "confidence": pred["confidence"],
            "bucket_half_width_ratio": pred["bucket_half_width_ratio"],
            "bucketing_strategy": pred["bucketing_strategy"],
        },
        "training": training_obj,
        "emitted_audit_event": True,
        "generated_at": _utc_iso(),
        "warnings": pred.get("warnings", []),
    }

    _emit_query(
        plan_id=plan_id,
        bucket_total=pred["tokens_total_bucket"],
        confidence=pred["confidence"],
        window=len(pred.get("training_plans", [])),
    )

    # Cache write
    if not args.no_cache:
        cache_dir = Path(args.cache_dir) if args.cache_dir else _cache_dir()
        try:
            _write_cache(cache_dir, plan_hash, envelope)
        except OSError as e:
            return _fail(EXIT_CACHE_WRITE, "cache_write_error", str(e))

    sys.stdout.write(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n")
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
