#!/usr/bin/env python3
"""audit-query — query the ceo-orchestration agent spawn audit log.

Stdlib-only CLI that reads `audit-log.jsonl` (+ rotated siblings) and
answers common operator questions:

    audit-query.py summary
    audit-query.py by-skill [--top N]
    audit-query.py compliance
    audit-query.py by-day [--days N]
    audit-query.py search <regex>
    audit-query.py since <ISO-date>
    audit-query.py errors
    audit-query.py stats
    audit-query.py export [--format csv|json|tsv]
    audit-query.py by-domain [--window=30d|--start=YYYY-MM-DD --end=YYYY-MM-DD]
                              [--check-reopen]

Default input path:
    ${CEO_AUDIT_LOG_PATH:-$HOME/.claude/projects/<native-slug>/audit-log.jsonl}

Pass `--log <path>` to override or `--include-rotated` to aggregate
across all `audit-log*.jsonl` in the audit directory.

Output formats:
    - Default: human-readable tab-separated table
    - `--json` flag: machine-readable JSON
    - `--csv` flag: CSV

Exit codes:
    0 — success (including empty result set)
    1 — log file missing OR bad query
    2 — unreadable log file (permissions, etc.)
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import csv
import io
import json
import os
import re
import sys
from types import FunctionType
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple
import sys as _sys_rp
from pathlib import Path as _Path_rp
_HOOKS_RP = _Path_rp(__file__).resolve()
for _anc in _HOOKS_RP.parents:
    if (_anc / ".claude" / "hooks" / "_lib").is_dir():
        if str(_anc / ".claude" / "hooks") not in _sys_rp.path:
            _sys_rp.path.insert(0, str(_anc / ".claude" / "hooks"))
        break
from _lib import runtime_paths as _rp  # noqa: E402  # PLAN-182 W1 single resolver


# ---------------------------------------------------------------------------
# Path resolution (mirrors audit_log.py conventions)
# ---------------------------------------------------------------------------


def default_log_path() -> Path:
    """Return the conventional audit log path from env vars / defaults."""
    home = Path(os.environ.get("HOME") or str(Path.home()))
    default_dir = _rp.runtime_state_dir()
    return Path(
        os.environ.get("CEO_AUDIT_LOG_PATH") or str(default_dir / "audit-log.jsonl")
    )


def default_errors_path() -> Path:
    env = os.environ.get("CEO_AUDIT_LOG_ERR")
    if env:
        return Path(env)
    # rail r2 G: family-follows-log — o errors mora ao lado do LOG efetivo
    # (com CEO_AUDIT_LOG_PATH setado, os escritores poem o breadcrumb no
    # parent do PATH; ler do default perderia exatamente esses erros).
    env_log = os.environ.get("CEO_AUDIT_LOG_PATH")
    if env_log:
        return Path(env_log).resolve().parent / "audit-log.errors"
    # rail r3 P2: espelha a cascata dos ESCRITORES — DIR-only poe o
    # breadcrumb sob CEO_AUDIT_LOG_DIR.
    env_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
    if env_dir:
        return Path(env_dir) / "audit-log.errors"
    return _rp.runtime_state_dir() / "audit-log.errors"


def discover_logs(primary: Path, include_rotated: bool) -> List[Path]:
    """Return the list of log files to read, sorted by modification time."""
    if not include_rotated:
        return [primary] if primary.is_file() else []
    if not primary.parent.is_dir():
        return []
    stem = primary.stem  # "audit-log"
    siblings = []
    for candidate in primary.parent.glob(f"{stem}*.jsonl"):
        if candidate.is_file():
            siblings.append(candidate)
    # Sort: primary file last so its entries are newest in the stream
    siblings.sort(key=lambda p: p.stat().st_mtime)
    return siblings


# ---------------------------------------------------------------------------
# Streaming reader — tolerates malformed lines with a stderr breadcrumb
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Perf-P1-002 — large-log materialization warning threshold.
#
# Subcommands that need FULL context (median, percentile, debate grouping,
# weekly-summary) still materialize the list. At this size threshold we
# emit a stderr hint so operators learn the log grew past the streaming
# regime and consider `--include-rotated=false` or log rotation.
# Value = 100_000 entries ≈ ~40-80 MB typical ≈ ~500-900ms parse on a
# modern laptop. Under this bar the materialization is unnoticeable.
_MATERIALIZATION_WARN_THRESHOLD = 100_000


def read_entries(
    paths: Iterable[Path],
    *,
    warn_stream=None,
) -> Iterator[Dict[str, Any]]:
    """Yield parsed JSON entries from the given log paths, streaming.

    Malformed lines are skipped with a breadcrumb to warn_stream.
    Large logs are read line-by-line so memory stays constant.

    Note: warn_stream defaults to None → resolved to sys.stderr at call
    time, not definition time, so test harness stderr redirection works.
    """
    if warn_stream is None:
        warn_stream = sys.stderr
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for lineno, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError as e:
                        print(
                            f"[audit-query] WARN: {path}:{lineno}: "
                            f"skipping malformed JSONL ({e.msg})",
                            file=warn_stream,
                        )
                        continue
                    if not isinstance(entry, dict):
                        continue
                    yield entry
        except OSError as e:
            print(
                f"[audit-query] WARN: cannot read {path}: {e}",
                file=warn_stream,
            )


# ---------------------------------------------------------------------------
# Sub-command implementations
# ---------------------------------------------------------------------------



# Query aggregations live outside this compatibility facade.  The named
# delegates below intentionally remain: downstream consumers load this
# hyphenated file by path and the read-API freeze guard inspects its AST.
from _lib._audit_query import queries as _queries
from _lib._audit_query import reporting as _reporting
from _lib._audit_query import reporting_health as _reporting_health
from _lib._audit_query import domain as _domain
from _lib._audit_query import rendering as _rendering
from _lib._audit_query import labeling as _labeling
from _lib._audit_query import critical as _critical
from _lib._audit_query import parsing as _parsing

_EXTRACTED_MODULES = (
    _domain, _rendering, _labeling, _critical, _parsing,
)
# Copy all declared values with one memo per facade. Mutable dictionaries and
# sets belong to this import, not to the cached declaration templates; a
# single deepcopy also preserves aliases across the exported declarations.
_extracted_declarations = {}
for _section in _EXTRACTED_MODULES:
    for _symbol in _section.__all__:
        _extracted_declarations[_symbol] = getattr(_section, _symbol)
    globals().setdefault("__annotations__", {}).update(
        dict(getattr(_section, "__annotations__", {}))
    )
globals().update(deepcopy(_extracted_declarations))
del _extracted_declarations
# Functions use this facade as their sole global namespace after rebinding.
# A path constant is relative to the original CLI, not its extracted module.
_LABEL_STORE_PATH = Path(__file__).resolve().parent / "audit-log-labels.jsonl"


def _bind_query_functions():
    """Re-home extracted functions in this module's historical globals.

    Tests and downstream scripts load this hyphenated file by path and patch
    its globals.  FunctionType keeps the implementation in a real module
    while making those patches visible to the extracted code.
    """
    bound = {}
    for implementation in (_queries, _reporting, _reporting_health, *_EXTRACTED_MODULES):
        for name, value in vars(implementation).items():
            if not isinstance(value, FunctionType) or value.__module__ != implementation.__name__:
                continue
            clone = FunctionType(value.__code__, globals(), name, value.__defaults__, value.__closure__)
            clone.__kwdefaults__ = value.__kwdefaults__
            clone.__annotations__ = value.__annotations__
            clone.__dict__.update(value.__dict__)
            clone.__doc__ = value.__doc__
            bound[name] = clone
            globals()[name] = clone
    return bound


_query_impls = _bind_query_functions()


def _query_call(name, *args):
    return _query_impls[name](*args)


def cmd_summary(entries, args): return _query_call("cmd_summary", entries, args)
def cmd_by_skill(entries, args): return _query_call("cmd_by_skill", entries, args)
def cmd_compliance(entries, args): return _query_call("cmd_compliance", entries, args)
def cmd_by_day(entries, args): return _query_call("cmd_by_day", entries, args)
def cmd_search(entries, args): return _query_call("cmd_search", entries, args)
def cmd_since(entries, args): return _query_call("cmd_since", entries, args)
def cmd_stats(entries, args): return _query_call("cmd_stats", entries, args)
def cmd_errors(args): return _query_call("cmd_errors", args)
def cmd_debate(entries, args): return _query_call("cmd_debate", entries, args)
def cmd_plans(entries, args): return _query_call("cmd_plans", entries, args)
def cmd_vetoes(entries, args): return _query_call("cmd_vetoes", entries, args)
def _bench_cost_usd(r: Dict[str, Any]) -> float:
    """Per-run benchmark cost in USD. Prefers the int-encoded
    ``cost_usd_cents`` (÷100); falls back to a legacy float ``cost_usd``.
    Returns 0.0 when neither is present (pre-cost-instrumented runs)."""
    cents = r.get("cost_usd_cents")
    if cents is not None:
        try:
            return int(cents) / 100.0
        except (TypeError, ValueError):
            return 0.0
    try:
        return float(r.get("cost_usd") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _bench_duration_s(r: Dict[str, Any]) -> float:
    """Per-run wall-clock (the harbor 'compute' column) in seconds.
    Prefers int-encoded ``duration_ms`` (÷1000); falls back to legacy
    float ``duration_s``."""
    ms = r.get("duration_ms")
    if ms is not None:
        try:
            return int(ms) / 1000.0
        except (TypeError, ValueError):
            return 0.0
    try:
        return float(r.get("duration_s") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _bench_turns(r: Dict[str, Any]) -> int:
    """Per-run scenario count (the harbor 'turns' column). Each scenario
    is one model interaction unit; pass+fail covers every scored
    scenario. Tolerates missing counts."""
    try:
        return int(r.get("pass_count") or 0) + int(r.get("fail_count") or 0)
    except (TypeError, ValueError):
        return 0


def cmd_benchmarks(
    entries: List[Dict[str, Any]], args
) -> List[Dict[str, Any]]:
    """Aggregate benchmark_run rows by skill. Sprint 5 A.2; PLAN-133 C4.

    Reports run count, latest pass_rate, median across runs, cumulative
    lessons_written per skill.

    PLAN-133 C4 (harbor-style row): co-reports **cost + compute + turns
    alongside pass-rate** so a benchmark is never read as a bare scalar.
    The added columns are strictly additive (existing keys unchanged) and
    derive only from fields already on the ``benchmark_run`` event
    (``cost_usd_cents``, ``duration_ms``, ``pass_count``/``fail_count``) —
    no SPEC change is required, so this reader stays $0 and canonical-free.
    """
    by_skill: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for e in entries:
        if e.get("action") != "benchmark_run":
            continue
        by_skill[e.get("skill", "?")].append(e)
    out = []
    for skill in sorted(by_skill.keys()):
        runs = sorted(by_skill[skill], key=lambda r: r.get("ts") or "")
        # Prefer new int-encoded fields (bps ÷ 1000 → float); fall back to
        # the legacy float fields for logs written before the migration.
        def _pass_rate(r: Dict[str, Any]) -> float:
            bps = r.get("pass_rate_bps")
            if bps is not None:
                return int(bps) / 1000.0
            return float(r.get("pass_rate") or 0.0)

        def _floor_rate(r: Dict[str, Any]) -> float:
            bps = r.get("floor_bps")
            if bps is not None:
                return int(bps) / 1000.0
            return float(r.get("floor") or 0.0)

        rates = [_pass_rate(r) for r in runs]
        if rates:
            med = _percentile(sorted(rates), 50)
        else:
            med = 0.0
        latest = runs[-1]
        # PLAN-133 C4 — harbor-style compute/cost/turns co-report.
        # Cumulative across all runs for the skill + the latest single run,
        # so an operator sees both the trend cost and the marginal cost.
        total_cost = sum(_bench_cost_usd(r) for r in runs)
        total_compute_s = sum(_bench_duration_s(r) for r in runs)
        total_turns = sum(_bench_turns(r) for r in runs)
        out.append(
            {
                "skill": skill,
                "runs": len(runs),
                "latest_pass_rate": round(_pass_rate(latest), 3),
                "median_pass_rate": med,
                "last_floor": _floor_rate(latest),
                "latest_ts": latest.get("ts"),
                "total_lessons_written": sum(
                    int(r.get("lessons_written") or 0) for r in runs
                ),
                # --- PLAN-133 C4 harbor-style row (additive) ---
                "latest_cost_usd": round(_bench_cost_usd(latest), 6),
                "total_cost_usd": round(total_cost, 6),
                "latest_compute_s": round(_bench_duration_s(latest), 3),
                "total_compute_s": round(total_compute_s, 3),
                "latest_turns": _bench_turns(latest),
                "total_turns": total_turns,
            }
        )
    return out


def cmd_lessons(entries, args): return _query_call("cmd_lessons", entries, args)
def cmd_lessons_effectiveness(entries, args): return _query_call("cmd_lessons_effectiveness", entries, args)
def cmd_spawn_stats(entries, args): return _query_call("cmd_spawn_stats", entries, args)
def cmd_weekly_summary(entries, args): return _query_call("cmd_weekly_summary", entries, args)
def cmd_architect_outcomes(entries, args): return _query_call("cmd_architect_outcomes", entries, args)
def cmd_prune_restore_ratio(entries, args): return _query_call("cmd_prune_restore_ratio", entries, args)
def cmd_claims(entries, args): return _query_call("cmd_claims", entries, args)
def cmd_metrics(entries, args): return _query_call("cmd_metrics", entries, args)
def cmd_tokens(entries, args): return _query_call("cmd_tokens", entries, args)
def cmd_health(entries, args): return _query_call("cmd_health", entries, args)
def cmd_export(entries, args): return _query_call("cmd_export", entries, args)


for _query_name in (
    "cmd_summary", "cmd_by_skill", "cmd_compliance", "cmd_by_day", "cmd_search",
    "cmd_since", "cmd_stats", "cmd_errors", "cmd_export", "cmd_debate",
    "cmd_plans", "cmd_vetoes", "cmd_lessons", "cmd_lessons_effectiveness",
    "cmd_spawn_stats", "cmd_weekly_summary", "cmd_architect_outcomes",
    "cmd_prune_restore_ratio", "cmd_claims", "cmd_metrics", "cmd_health",
    "cmd_tokens",
):
    _query_wrapper = globals()[_query_name]
    _query_impl = _query_impls[_query_name]
    _query_wrapper.__doc__ = _query_impl.__doc__
    _query_wrapper.__annotations__ = _query_impl.__annotations__
    _query_wrapper.__wrapped__ = _query_impl

# ---------------------------------------------------------------------------
# PLAN-080 Phase 1 — by-domain sub-command
# ---------------------------------------------------------------------------

# Default window for by-domain (calendar days, trailing from UTC midnight)


# Remaining domain implementations are rebound above the CLI entrypoint.
def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — dispatch audit-query sub-commands."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # `errors` subcommand reads a different file, doesn't need the jsonl
    if args.cmd == "errors":
        result = cmd_errors(args)
        print(render(result, as_json=args.as_json, as_csv=args.as_csv))
        return 0

    log_path = Path(args.log) if args.log else default_log_path()
    log_files = discover_logs(log_path, args.include_rotated)

    # Perf-P1-002 — streamable subcommands consume the iterator directly so
    # a 100k-row log does not sit in RAM as a Python list.  Non-streamable
    # subcommands (median / percentile / cross-reference) still materialize
    # but emit a stderr hint when the log crosses the warn threshold.
    _STREAMABLE_CMDS = frozenset({
        "summary", "by-skill", "by-day", "search", "since",
    })

    if not log_files:
        entries_iter: Iterable[Dict[str, Any]] = iter(())
        entries: List[Dict[str, Any]] = []
    elif args.cmd in _STREAMABLE_CMDS:
        entries_iter = read_entries(log_files)
        entries = []  # sentinel — not used on streaming path
    else:
        entries = list(read_entries(log_files))
        entries_iter = entries
        if len(entries) >= _MATERIALIZATION_WARN_THRESHOLD:
            print(
                "[audit-query] NOTE: loaded {n} entries into RAM for "
                "subcommand {cmd!r} (threshold {thr}). Consider rotating "
                "older logs or running a streamable subcommand.".format(
                    n=len(entries),
                    cmd=args.cmd,
                    thr=_MATERIALIZATION_WARN_THRESHOLD,
                ),
                file=sys.stderr,
            )

    if args.cmd == "summary":
        result = cmd_summary(entries_iter, args)
    elif args.cmd == "by-skill":
        result = cmd_by_skill(entries_iter, args)
    elif args.cmd == "compliance":
        result = cmd_compliance(entries, args)
    elif args.cmd == "by-day":
        result = cmd_by_day(entries_iter, args)
    elif args.cmd == "search":
        result = cmd_search(entries_iter, args)
    elif args.cmd == "since":
        result = cmd_since(entries_iter, args)
    elif args.cmd == "stats":
        result = cmd_stats(entries, args)
    elif args.cmd == "export":
        result = cmd_export(entries, args)
        # Export handles its own formatting
        if args.export_format in ("csv", "tsv"):
            sys.stdout.write(result)
            return 0
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    # Sprint 5 A.2 — 7 new sub-commands
    elif args.cmd == "debate":
        result = cmd_debate(entries, args)
    elif args.cmd == "plans":
        result = cmd_plans(entries, args)
    elif args.cmd == "vetoes":
        result = cmd_vetoes(entries, args)
    elif args.cmd == "benchmarks":
        result = cmd_benchmarks(entries, args)
    elif args.cmd == "lessons":
        result = cmd_lessons(entries, args)
    elif args.cmd == "metrics":
        result = cmd_metrics(entries, args)
    elif args.cmd == "health":
        result = cmd_health(entries, args)
    elif args.cmd == "tokens":
        result = cmd_tokens(entries, args)
    elif args.cmd == "claims":
        result = cmd_claims(entries, args)
    elif args.cmd == "prune-restore-ratio":
        result = cmd_prune_restore_ratio(entries, args)
    elif args.cmd == "architect-outcomes":
        result = cmd_architect_outcomes(entries, args)
    elif args.cmd == "lessons-effectiveness":
        result = cmd_lessons_effectiveness(entries, args)
    elif args.cmd == "weekly-summary":
        result = cmd_weekly_summary(entries, args)
    elif args.cmd == "spawn-stats":
        result = cmd_spawn_stats(entries, args)
    # PLAN-080 Phase 1
    elif args.cmd == "by-domain":
        result = cmd_by_domain(entries, args)
    # PLAN-081 Phase 6-bis
    elif args.cmd == "label":
        result = cmd_label(entries, args)
    elif args.cmd == "fp-rate":
        result = cmd_fp_rate(entries, args)
    elif args.cmd == "case-summary":
        result = cmd_case_summary(entries, args)
    elif args.cmd == "codex-writeguard-summary":
        result = cmd_codex_writeguard_summary(entries, args)
    # PLAN-113 Phase B Wave W1 — critical-security-action reader
    elif args.cmd == "critical":
        result = cmd_critical(entries, args)
    else:  # pragma: no cover — argparse prevents this
        parser.error(f"unknown cmd: {args.cmd}")

    print(render(result, as_json=args.as_json, as_csv=args.as_csv))
    return 0


if __name__ == "__main__":
    sys.exit(main())
