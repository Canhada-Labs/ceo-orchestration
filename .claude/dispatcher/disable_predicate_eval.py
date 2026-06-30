"""Disable-predicate evaluator — PLAN-081 Phase 2 deliverable.

Typed state-machine evaluator for ``disable_predicates`` declared in
``.claude/dispatcher/routing-matrix.yaml``. Consumed by
``routing_matrix_loader.is_pair_rail_enabled()`` to decide whether the
pair-rail is currently enabled for an archetype.

## Threat-model T-4 mitigations

This evaluator NEVER blocks the user session — it returns a Boolean
("did this predicate fire?") and lets the caller decide fallback policy.
Fail-open invariant: any internal error defaults to ``False`` (predicate
did NOT fire), preserving the pair-rail.

## R1 S-Perf-Unseen-1 — bounded tail-scan

All metric queries against ``audit-log.jsonl`` use a **bounded tail-scan**:
the file is read backward starting from the last byte, capped at
``CEO_PAIR_RAIL_AUDIT_TAIL_N`` records (default 10000). This guarantees
``evaluate_predicate()`` returns in <100ms on audit-logs up to ~50,000
records, well below the 100ms p99 budget per
``disable_predicate_eval`` Phase 2 exit criterion.

The bounded tail-scan is implemented via **chunked reverse-read**:
read 64 KiB chunks from end-of-file, split on newlines, accumulate up
to N records. JSON parsing happens lazily — only on records that pass
the cheap ``action`` substring filter.

## Predicate types (typed state machine)

Each predicate type maps to one ``_evaluate_*`` arm. Adding a new type
requires:

1. Add to ``_KNOWN_PREDICATE_TYPES`` in routing-matrix-loader.
2. Add ``_evaluate_<type>`` arm here with the same signature.
3. Add the dispatch entry in ``evaluate_predicate``.
4. Add test fixture in ``test_disable_predicate_eval.py``.

Stdlib-only. Python ≥3.9 compatibility — uses ``typing.Optional/List``
(no PEP 604 ``X | Y``).
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union

# ---------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------

#: Default cap on records inspected per evaluation. Override via
#: ``CEO_PAIR_RAIL_AUDIT_TAIL_N`` env var. Capped at 100k absolute upper
#: bound to enforce the <100ms perf budget regardless of operator override.
DEFAULT_AUDIT_TAIL_N: int = 10000

#: Hard upper bound on the override value (defense-in-depth against
#: operator misconfiguration).
MAX_AUDIT_TAIL_N: int = 100_000

#: Reverse-read chunk size in bytes (64 KiB).
_REVERSE_CHUNK_SIZE: int = 64 * 1024

#: Hard wall-clock cap (milliseconds). The evaluator returns False if it
#: detects elapsed time crossing the cap during tail-scan (fail-OPEN).
DEFAULT_EVAL_TIMEOUT_MS: int = 100

#: Substring filter applied to raw audit-log lines BEFORE JSON parse,
#: to avoid parsing every event for an `action` we don't care about.
#: Tolerates both compact ``json.dumps(separators=(",", ":"))`` output
#: (``"action":"foo"``) and default ``json.dumps`` output
#: (``"action": "foo"`` with the standard separator space) — only the
#: ``"action"`` key prefix is asserted.
_ACTION_PREFIX_HINT: str = '"action"'

# Metric → source action mapping (mirror of routing-matrix.yaml metrics
# table). Keep in sync with the matrix file. The loader does not pass
# the matrix into the evaluator; this table is the runtime source of
# truth for action filtering.
_METRIC_TO_ACTION: Dict[str, str] = {
    "codex_outage_minutes": "pair_rail_codex_unavailable",
    "fp_rate_30d": "pair_rail_case_emit",
    "disagreement_rate_30d": "pair_rail_case_emit",
    "codex_latency_p95_s": "dispatcher_route",
    "u7_rubric_gap_pp": "pair_rail_promotion_emit",
    "u2_breaches_count": "codex_writeguard_block",
}


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------


def evaluate_predicate(
    predicate: Any,
    audit_log_path: Optional[Path] = None,
    *,
    timeout_ms: Optional[int] = None,
    tail_n: Optional[int] = None,
    now_ts: Optional[float] = None,
) -> bool:
    """Return True if ``predicate`` fires given the current audit-log state.

    Args:
        predicate: a ``Predicate`` NamedTuple from ``routing_matrix_loader``
            (duck-typed; only ``.type``, ``.metric``, ``.operator``,
            ``.value``, ``.window_minutes``, ``.window_days`` accessed).
        audit_log_path: explicit path override (test). Defaults to the
            user-scoped audit-log under
            ``~/.claude/projects/<project>/audit-log.jsonl``.
        timeout_ms: per-evaluation wall-clock cap. Default
            ``DEFAULT_EVAL_TIMEOUT_MS``. The evaluator polls elapsed
            time at chunk boundaries — exceeding the cap returns False
            (fail-OPEN, predicate did not fire).
        tail_n: explicit cap on records inspected. Default reads
            ``CEO_PAIR_RAIL_AUDIT_TAIL_N`` env (clamped to
            ``MAX_AUDIT_TAIL_N``).
        now_ts: explicit "now" Unix timestamp (test override). Defaults
            to ``time.time()``.

    Returns:
        True if the predicate fired (operator+value gate breached),
        False otherwise. ANY internal error → False (fail-OPEN).
    """
    try:
        ptype = getattr(predicate, "type", None)
        metric = getattr(predicate, "metric", None)
        operator = getattr(predicate, "operator", None)
        value = getattr(predicate, "value", None)
        window_minutes = getattr(predicate, "window_minutes", None)
        window_days = getattr(predicate, "window_days", None)

        if not all((ptype, metric, operator)) or value is None:
            return False

        path = audit_log_path or _resolve_audit_log_path()
        if path is None or not path.exists():
            return False

        cap = tail_n if tail_n is not None else _resolve_tail_n()
        budget_ms = timeout_ms if timeout_ms is not None else DEFAULT_EVAL_TIMEOUT_MS
        now = now_ts if now_ts is not None else time.time()
        start_clock = time.monotonic()

        action_filter = _METRIC_TO_ACTION.get(metric)
        if not action_filter:
            return False

        records = _bounded_tail_records(
            path,
            tail_n=cap,
            action_filter=action_filter,
            start_clock=start_clock,
            budget_ms=budget_ms,
        )

        if ptype == "duration_threshold":
            metric_value = _evaluate_duration(
                records, metric, now, window_minutes
            )
        elif ptype == "numeric_threshold":
            metric_value = _evaluate_numeric(
                records, metric, now, window_minutes, window_days
            )
        elif ptype == "boolean":
            metric_value = _evaluate_boolean(records, metric, now, window_minutes)
        else:
            return False

        return _apply_operator(metric_value, operator, value)
    except Exception:
        return False


# ---------------------------------------------------------------------
# Bounded tail-scan
# ---------------------------------------------------------------------


def _bounded_tail_records(
    path: Path,
    *,
    tail_n: int,
    action_filter: str,
    start_clock: float,
    budget_ms: int,
) -> List[Dict[str, Any]]:
    """Reverse-scan ``path`` and return up to ``tail_n`` parsed records
    whose ``action`` matches ``action_filter``.

    The function reads chunks of ``_REVERSE_CHUNK_SIZE`` bytes from the
    file end backwards, collecting newline-delimited lines into a buffer.
    Cheap substring filter applied BEFORE JSON parse.

    Returns the records in **chronological order** (oldest first).
    """
    if tail_n <= 0:
        return []
    out: List[Dict[str, Any]] = []
    seen_count = 0
    try:
        with path.open("rb") as fp:
            fp.seek(0, os.SEEK_END)
            file_size = fp.tell()
            if file_size == 0:
                return []
            offset = file_size
            buffer = b""
            while offset > 0 and seen_count < tail_n:
                # Budget check
                elapsed_ms = (time.monotonic() - start_clock) * 1000.0
                if elapsed_ms >= budget_ms:
                    break
                read_size = min(_REVERSE_CHUNK_SIZE, offset)
                offset -= read_size
                fp.seek(offset)
                chunk = fp.read(read_size)
                buffer = chunk + buffer
                # Process complete lines, keep trailing partial-line
                # in `buffer` for the next iteration.
                lines = buffer.split(b"\n")
                # If we're not at the start of file, the first line may be
                # partial — preserve it.
                if offset > 0:
                    buffer = lines[0]
                    lines = lines[1:]
                else:
                    buffer = b""
                # Process lines in reverse to honor "chronological order"
                # at the END of out — we'll reverse() before return.
                for line in reversed(lines):
                    if seen_count >= tail_n:
                        break
                    if not line:
                        continue
                    seen_count += 1
                    # Cheap substring filter
                    if action_filter.encode("ascii") not in line:
                        continue
                    if _ACTION_PREFIX_HINT.encode("ascii") not in line:
                        continue
                    try:
                        rec = json.loads(line.decode("utf-8", errors="replace"))
                    except (ValueError, UnicodeDecodeError):
                        continue
                    if not isinstance(rec, dict):
                        continue
                    if rec.get("action") != action_filter:
                        continue
                    out.append(rec)
            # If the whole file fit in the buffer and we still haven't
            # processed it, flush.
            if buffer and seen_count < tail_n:
                line = buffer
                seen_count += 1
                if (
                    action_filter.encode("ascii") in line
                    and _ACTION_PREFIX_HINT.encode("ascii") in line
                ):
                    try:
                        rec = json.loads(line.decode("utf-8", errors="replace"))
                        if isinstance(rec, dict) and rec.get("action") == action_filter:
                            out.append(rec)
                    except (ValueError, UnicodeDecodeError):
                        pass
    except OSError:
        return []
    out.reverse()
    return out


# ---------------------------------------------------------------------
# Predicate-type evaluators (typed state-machine arms)
# ---------------------------------------------------------------------


def _evaluate_duration(
    records: List[Dict[str, Any]],
    metric: str,
    now: float,
    window_minutes: Optional[int],
) -> float:
    """Sum durations from `records` over the trailing window.

    Each ``pair_rail_codex_unavailable`` event is assumed to represent a
    single "outage minute" unit — Phase 2 simplification (events are
    rate-limited at one-per-minute by the upstream emitter). Phase 4 may
    upgrade this to integrate ``elapsed_minutes`` payload field if the
    schema gains one.

    Returns the total minutes inside the window (0 if no records).
    """
    if window_minutes is None or window_minutes <= 0:
        return 0.0
    window_start = now - (window_minutes * 60.0)
    minutes = 0.0
    for rec in records:
        ts = _coerce_record_ts(rec)
        if ts is None or ts < window_start:
            continue
        # 1 minute per outage event (rate-limited upstream).
        minutes += 1.0
    return minutes


def _evaluate_numeric(
    records: List[Dict[str, Any]],
    metric: str,
    now: float,
    window_minutes: Optional[int],
    window_days: Optional[int],
) -> float:
    """Aggregate a numeric metric over the trailing window."""
    window_start = _resolve_window_start(now, window_minutes, window_days)
    if metric == "fp_rate_30d":
        return _fp_rate(records, window_start, label_kind="fp")
    if metric == "disagreement_rate_30d":
        return _disagreement_rate(records, window_start)
    if metric == "codex_latency_p95_s":
        return _latency_p95(records, window_start)
    if metric == "u7_rubric_gap_pp":
        return _latest_field_value(records, "rubric_gap_pp")
    return 0.0


def _evaluate_boolean(
    records: List[Dict[str, Any]],
    metric: str,
    now: float,
    window_minutes: Optional[int],
) -> float:
    """Return a boolean-as-float (0.0 / 1.0) over the trailing window."""
    window_start = _resolve_window_start(now, window_minutes, None)
    if metric == "u2_breaches_count":
        count = _window_count(records, window_start)
        return 1.0 if count > 0 else 0.0
    # Generic: count records in window
    count = _window_count(records, window_start)
    return 1.0 if count > 0 else 0.0


# ---------------------------------------------------------------------
# Aggregation primitives
# ---------------------------------------------------------------------


def _resolve_window_start(
    now: float,
    window_minutes: Optional[int],
    window_days: Optional[int],
) -> float:
    """Compute the trailing-window cutoff (Unix epoch seconds)."""
    if window_minutes and window_minutes > 0:
        return now - (window_minutes * 60.0)
    if window_days and window_days > 0:
        return now - (window_days * 86400.0)
    # No window → entire scanned record set
    return 0.0


def _coerce_record_ts(rec: Dict[str, Any]) -> Optional[float]:
    """Best-effort conversion of an audit-log record's ``ts`` to Unix epoch."""
    ts = rec.get("ts")
    if isinstance(ts, (int, float)):
        return float(ts)
    if isinstance(ts, str):
        # ISO 8601 with optional Z suffix
        try:
            s = ts.rstrip("Z")
            # Truncate fractional seconds beyond microseconds
            if "." in s:
                base, frac = s.split(".", 1)
                # Preserve the timezone suffix if present
                tz = ""
                for marker in ("+", "-"):
                    if marker in frac:
                        idx = frac.index(marker)
                        tz = frac[idx:]
                        frac = frac[:idx]
                frac = frac[:6]  # microseconds max
                s = f"{base}.{frac}{tz}"
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.timestamp()
        except (ValueError, TypeError):
            return None
    return None


def _window_count(records: List[Dict[str, Any]], window_start: float) -> int:
    n = 0
    for rec in records:
        ts = _coerce_record_ts(rec)
        if ts is None or ts < window_start:
            continue
        n += 1
    return n


def _fp_rate(
    records: List[Dict[str, Any]],
    window_start: float,
    *,
    label_kind: str,
    min_denominator: int = 5,
) -> float:
    """False-positive rate over the trailing window.

    Numerator: Case-B events labeled ``"fp"`` via ``audit-log-labels.jsonl``
    (Phase 6 deliverable). For Phase 2 evaluator, we rely on a
    ``label`` field embedded in the event itself (Phase 6 will refactor
    to read the labels store; for now Phase 6 deferral leaves this at
    advisory). Returns 0.0 if denominator < ``min_denominator``.

    Denominator: total Case-B events in window.
    """
    case_b_total = 0
    case_b_labeled_fp = 0
    for rec in records:
        ts = _coerce_record_ts(rec)
        if ts is None or ts < window_start:
            continue
        case = rec.get("case")
        if case != "B":
            continue
        case_b_total += 1
        if rec.get("label") == "fp":
            case_b_labeled_fp += 1
    if case_b_total < min_denominator:
        return 0.0
    return case_b_labeled_fp / case_b_total


def _disagreement_rate(
    records: List[Dict[str, Any]],
    window_start: float,
    *,
    min_denominator: int = 5,
) -> float:
    """Disagreement rate (Case-E share over total cases A-E)."""
    cases_total = 0
    case_e = 0
    for rec in records:
        ts = _coerce_record_ts(rec)
        if ts is None or ts < window_start:
            continue
        case = rec.get("case")
        if case in ("A", "B", "C", "D", "E"):
            cases_total += 1
            if case == "E":
                case_e += 1
    if cases_total < min_denominator:
        return 0.0
    return case_e / cases_total


def _latency_p95(
    records: List[Dict[str, Any]],
    window_start: float,
    *,
    min_denominator: int = 10,
) -> float:
    """95th percentile of latency wall-clock, nearest-rank method.

    Reads from ``wall_clock_ms`` (preferred — integer milliseconds per
    Codex iter 1 P0-1 canonical_json no-float policy) and divides by
    1000 to obtain seconds for percentile comparison. Falls back to
    legacy ``wall_clock_s`` (float seconds) for back-compat with any
    pre-P0-1 records still in the audit-log.

    Nearest-rank percentile formula (R1 P1-7 fix): for sorted samples
    of length ``n``, the p95 rank index (zero-based) is
    ``ceil(0.95 * n) - 1`` clamped to ``[0, n-1]``. The previous
    ``int(0.95 * n + 0.5) - 1`` form rounded-to-nearest, which
    underestimated for small n (e.g. n=12 → rank=10 not 11; should
    select the 11th sorted value, not the 10th).
    """
    import math

    samples: List[float] = []
    for rec in records:
        ts = _coerce_record_ts(rec)
        if ts is None or ts < window_start:
            continue
        wall_ms = rec.get("wall_clock_ms")
        if isinstance(wall_ms, int) and not isinstance(wall_ms, bool) and wall_ms >= 0:
            samples.append(wall_ms / 1000.0)
            continue
        # Legacy fallback: wall_clock_s (float seconds, pre-P0-1 records).
        wall = rec.get("wall_clock_s")
        if isinstance(wall, (int, float)) and not isinstance(wall, bool) and wall >= 0:
            samples.append(float(wall))
    if len(samples) < min_denominator:
        return 0.0
    samples.sort()
    # Nearest-rank percentile: ceil(0.95 * n) - 1 (zero-indexed).
    rank = math.ceil(0.95 * len(samples)) - 1
    rank = max(0, min(rank, len(samples) - 1))
    return samples[rank]


def _latest_field_value(
    records: List[Dict[str, Any]],
    field: str,
) -> float:
    """Return the most recent record's ``field`` value (numeric coerced)."""
    if not records:
        return 0.0
    # records is in chronological order — last is most recent
    for rec in reversed(records):
        v = rec.get(field)
        if isinstance(v, (int, float)):
            return float(v)
    return 0.0


# ---------------------------------------------------------------------
# Operator application
# ---------------------------------------------------------------------


def _apply_operator(metric_value: float, operator: str, threshold: Any) -> bool:
    """Apply ``operator`` between ``metric_value`` and ``threshold``."""
    try:
        thr = float(threshold) if isinstance(threshold, bool) else float(threshold)
    except (TypeError, ValueError):
        return False
    if operator == ">":
        return metric_value > thr
    if operator == ">=":
        return metric_value >= thr
    if operator == "<":
        return metric_value < thr
    if operator == "<=":
        return metric_value <= thr
    if operator == "==":
        return metric_value == thr
    return False


# ---------------------------------------------------------------------
# Path / env resolution
# ---------------------------------------------------------------------


def _resolve_audit_log_path() -> Optional[Path]:
    """Locate the user-scoped audit-log path.

    Resolution order:
      1. ``CEO_AUDIT_LOG_PATH`` env (test override)
      2. ``~/.claude/projects/<project>/audit-log.jsonl`` where
         ``<project>`` is the slugified CWD (matches audit_log.py emit
         path semantics).
    """
    override = os.environ.get("CEO_AUDIT_LOG_PATH")
    if override:
        return Path(override)
    home = os.environ.get("HOME") or os.path.expanduser("~")
    if not home:
        return None
    project_dir_override = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir_override:
        cwd = Path(project_dir_override)
    else:
        cwd = Path.cwd()
    slug = str(cwd).replace("/", "-")
    if slug.startswith("-"):
        slug = slug[1:]
    candidate = Path(home) / ".claude" / "projects" / slug / "audit-log.jsonl"
    if candidate.exists():
        return candidate
    # Fallback: short slug = basename
    short_slug = cwd.name
    candidate2 = Path(home) / ".claude" / "projects" / short_slug / "audit-log.jsonl"
    if candidate2.exists():
        return candidate2
    return candidate  # may not exist; caller handles


def _resolve_tail_n() -> int:
    """Resolve the ``CEO_PAIR_RAIL_AUDIT_TAIL_N`` override, clamped."""
    raw = os.environ.get("CEO_PAIR_RAIL_AUDIT_TAIL_N", "").strip()
    if not raw:
        return DEFAULT_AUDIT_TAIL_N
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_AUDIT_TAIL_N
    if n <= 0:
        return DEFAULT_AUDIT_TAIL_N
    return min(n, MAX_AUDIT_TAIL_N)


# ---------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------


def _main() -> int:
    """Manual smoke test: evaluate one synthetic predicate against the
    user audit-log."""
    from collections import namedtuple

    SyntheticPredicate = namedtuple(
        "SyntheticPredicate",
        ["id", "type", "metric", "operator", "value", "window_minutes", "window_days"],
    )
    pred = SyntheticPredicate(
        id="codex_outage_5min",
        type="duration_threshold",
        metric="codex_outage_minutes",
        operator=">",
        value=5,
        window_minutes=60,
        window_days=None,
    )
    fired = evaluate_predicate(pred)
    print(f"predicate {pred.id} fired={fired}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
