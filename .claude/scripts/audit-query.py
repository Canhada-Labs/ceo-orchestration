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
from _audit_query import queries as _queries
from _audit_query import reporting as _reporting


def _bind_query_functions():
    """Re-home extracted functions in this module's historical globals.

    Tests and downstream scripts load this hyphenated file by path and patch
    its globals.  FunctionType keeps the implementation in a real module
    while making those patches visible to the extracted code.
    """
    bound = {}
    for implementation in (_queries, _reporting):
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
_BY_DOMAIN_DEFAULT_WINDOW_DAYS = 30

# Sentinel used when no dispatch_archetype_hint is available
_UNKNOWN_BUCKET = "UNKNOWN"

# Default policy file location (relative to repo root, resolved at runtime)
_GRANDFATHER_POLICY_RELPATH = ".claude/policies/grandfather-cap.policy.yaml"


def _parse_domain_date(raw: str) -> Optional[datetime]:
    """Parse YYYY-MM-DD into a UTC-aware datetime (midnight UTC).

    Returns None on failure (not sys.exit — caller handles the error).
    """
    try:
        dt = datetime.strptime(raw.strip(), "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _resolve_window_bounds(
    args,
) -> Tuple[Optional[datetime], Optional[datetime], str]:
    """Resolve --window / --start / --end into (start_dt, end_dt, window_label).

    Returns (start_dt, end_dt, label) where:
      - start_dt: inclusive lower bound (UTC midnight); None means no lower bound
      - end_dt:   inclusive upper bound (UTC now for default windows)
      - label:    human-readable description of the window

    Validates start <= end; prints error + sys.exit(1) on invalid input.
    """
    now = datetime.now(timezone.utc)
    # --start / --end take precedence over --window
    start_raw = getattr(args, "start", None)
    end_raw = getattr(args, "end", None)
    window_raw = getattr(args, "window", None) or f"{_BY_DOMAIN_DEFAULT_WINDOW_DAYS}d"

    if start_raw or end_raw:
        if not start_raw or not end_raw:
            print(
                "[audit-query] ERROR: by-domain: --start and --end must both be provided",
                file=sys.stderr,
            )
            sys.exit(1)
        start_dt = _parse_domain_date(start_raw)
        end_dt = _parse_domain_date(end_raw)
        if start_dt is None:
            print(
                f"[audit-query] ERROR: by-domain: invalid --start date {start_raw!r} "
                "(use YYYY-MM-DD)",
                file=sys.stderr,
            )
            sys.exit(1)
        if end_dt is None:
            print(
                f"[audit-query] ERROR: by-domain: invalid --end date {end_raw!r} "
                "(use YYYY-MM-DD)",
                file=sys.stderr,
            )
            sys.exit(1)
        # Make end_dt the end of that calendar day (23:59:59 UTC)
        end_dt = end_dt.replace(hour=23, minute=59, second=59)
        if start_dt > end_dt:
            print(
                f"[audit-query] ERROR: by-domain: --start ({start_raw}) is after "
                f"--end ({end_raw})",
                file=sys.stderr,
            )
            sys.exit(1)
        label = f"{start_raw} to {end_raw}"
        return start_dt, end_dt, label

    # Parse --window (e.g. "30d", "7d")
    m = re.fullmatch(r"(\d+)([dhm])", window_raw.strip().lower())
    if not m:
        print(
            f"[audit-query] ERROR: by-domain: invalid --window {window_raw!r}; "
            "expected e.g. 30d, 7d, 14d",
            file=sys.stderr,
        )
        sys.exit(1)
    n, unit = int(m.group(1)), m.group(2)
    delta = {"d": timedelta(days=n), "h": timedelta(hours=n), "m": timedelta(minutes=n)}[unit]
    start_dt = now - delta
    label = f"trailing {window_raw}"
    return start_dt, now, label


def _load_sunset_domains(args) -> Optional[List[str]]:
    """Load sunset domain list for --check-reopen.

    Sources (in priority order):
    1. CEO_GRANDFATHER_POLICY_PATH env var
    2. <repo_root>/.claude/policies/grandfather-cap.policy.yaml (if exists)
    3. stdin JSON list (if CEO_BY_DOMAIN_SUNSET_STDIN=1)

    Returns a list of domain slugs, or None if the policy file is not found
    and stdin mode is not active. An empty list [] means "policy found but
    no sunset members".
    """
    # Check env override
    policy_path_env = os.environ.get("CEO_GRANDFATHER_POLICY_PATH")
    if policy_path_env:
        p = Path(policy_path_env)
        if p.is_file():
            return _parse_sunset_from_policy(p)
        print(
            f"[audit-query] WARN: CEO_GRANDFATHER_POLICY_PATH={policy_path_env!r} "
            "not found; no sunset list loaded",
            file=sys.stderr,
        )
        return []

    # Try conventional project-relative path via CLAUDE_PROJECT_DIR or cwd
    for base_env in ("CLAUDE_PROJECT_DIR",):
        base = os.environ.get(base_env)
        if base:
            p = Path(base) / _GRANDFATHER_POLICY_RELPATH
            if p.is_file():
                return _parse_sunset_from_policy(p)

    # Try cwd-relative (developer convenience)
    p = Path(_GRANDFATHER_POLICY_RELPATH)
    if p.is_file():
        return _parse_sunset_from_policy(p)

    # Stdin JSON fallback (CEO_BY_DOMAIN_SUNSET_STDIN=1 for testing)
    if os.environ.get("CEO_BY_DOMAIN_SUNSET_STDIN") == "1":
        try:
            raw = sys.stdin.read()
            data = json.loads(raw)
            if isinstance(data, list):
                return [str(x) for x in data if x]
        except (json.JSONDecodeError, OSError):
            pass
        return []

    return None  # policy not found — caller will skip reopen check


def _parse_sunset_from_policy(path: Path) -> List[str]:
    """Extract sunset domain members from grandfather-cap.policy.yaml.

    Parses the YAML manually using stdlib (no PyYAML dependency).
    Looks for `domain_bundles.members:` list block.

    Returns list of domain slug strings (may be empty).
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    # Simple line-based YAML parser for the members list.
    # We scan for "members:" under "domain_bundles:" section.
    in_domain_bundles = False
    in_members = False
    members: List[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped == "domain_bundles:":
            in_domain_bundles = True
            in_members = False
            continue
        if in_domain_bundles:
            # Another top-level key → leave domain_bundles section
            if stripped and not line.startswith(" ") and not line.startswith("\t"):
                in_domain_bundles = False
                in_members = False
                continue
            if stripped == "members:":
                in_members = True
                continue
            if in_members:
                if stripped.startswith("- "):
                    member = stripped[2:].strip()
                    if member:
                        members.append(member)
                elif stripped and not stripped.startswith("-"):
                    # End of list
                    in_members = False

    return members


def _load_sunset_reopen_options(args) -> Optional[Dict[str, bool]]:
    """M2-CDX-4 + M2-CDX-7 (Codex Phase 1 iter 1) — load reopen filter flags.

    Returns dict with `requires_hint_match` and `unknown_excluded` boolean
    flags read from the same grandfather-cap.policy.yaml as
    `_load_sunset_domains`. Defaults to {True, True} if either flag is
    missing/unparseable. Returns None if the policy file is not found.
    """
    # Reuse the same path resolution as _load_sunset_domains for consistency
    policy_path_env = os.environ.get("CEO_GRANDFATHER_POLICY_PATH")
    candidates: List[Path] = []
    if policy_path_env:
        candidates.append(Path(policy_path_env))
    base = os.environ.get("CLAUDE_PROJECT_DIR")
    if base:
        candidates.append(Path(base) / _GRANDFATHER_POLICY_RELPATH)
    candidates.append(Path(_GRANDFATHER_POLICY_RELPATH))

    for p in candidates:
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        return _parse_sunset_reopen_flags(text)
    return None


def _parse_sunset_reopen_flags(text: str) -> Dict[str, bool]:
    """Parse `sunset_reopen_requires_hint_match` and `sunset_reopen_unknown_excluded`.

    Both flags default to True if missing (defensive — secure-by-default).
    """
    requires_hint_match = True
    unknown_excluded = True
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#"):
            continue
        if s.startswith("sunset_reopen_requires_hint_match:"):
            v = s.split(":", 1)[1].strip().lower()
            requires_hint_match = (v == "true" or v.startswith("true"))
        elif s.startswith("sunset_reopen_unknown_excluded:"):
            v = s.split(":", 1)[1].strip().lower()
            unknown_excluded = (v == "true" or v.startswith("true"))
    return {
        "requires_hint_match": requires_hint_match,
        "unknown_excluded": unknown_excluded,
    }


def _entry_ts_to_dt(ts: str) -> Optional[datetime]:
    """Parse a log entry `ts` field into a UTC datetime."""
    if not ts:
        return None
    try:
        s = ts[:-1] + "+00:00" if ts.endswith("Z") else ts
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def cmd_by_domain(entries: List[Dict[str, Any]], args) -> Dict[str, Any]:
    """`audit-query by-domain` — spawn activity grouped by dispatch_archetype_hint.

    PLAN-080 Phase 1 — domain-level observability for squad-bundle governance.

    Groups `agent_spawn` events by `dispatch_archetype_hint` field if present;
    falls back to `archetype` field, then to the "UNKNOWN" bucket. Entries
    outside the requested time window are excluded.

    Output columns:
      Domain | Spawns | First seen | Last seen | hint_coverage_pct

    Sorted deterministically by domain name (alphabetic, UNKNOWN last).

    With --check-reopen: additionally filters to domains present in the sunset
    list from grandfather-cap.policy.yaml. Reports domains with >= 1 spawn
    where hint matches a sunset domain (UNKNOWN excluded per M2-CDX-7).
    """
    start_dt, end_dt, window_label = _resolve_window_bounds(args)

    # Load sunset list + reopen options if --check-reopen requested
    check_reopen = getattr(args, "check_reopen", False)
    sunset_domains: Optional[List[str]] = None
    # M2-CDX-4 + M2-CDX-7 (Codex Phase 1 iter 1): honor policy flags.
    # Defaults match policy semantics when flags missing/unparseable.
    requires_hint_match = True       # sunset_reopen_requires_hint_match (default true per §8)
    unknown_excluded = True          # sunset_reopen_unknown_excluded (M2-CDX-7 default true)
    if check_reopen:
        sunset_domains = _load_sunset_domains(args)
        sunset_options = _load_sunset_reopen_options(args)
        if sunset_options is not None:
            requires_hint_match = sunset_options.get("requires_hint_match", True)
            unknown_excluded = sunset_options.get("unknown_excluded", True)
        if sunset_domains is None:
            print(
                "[audit-query] WARN: by-domain --check-reopen: no sunset policy file "
                "found; skipping reopen filter. Set CEO_GRANDFATHER_POLICY_PATH or "
                "place grandfather-cap.policy.yaml at "
                f"{_GRANDFATHER_POLICY_RELPATH}",
                file=sys.stderr,
            )

    # Aggregation state per domain bucket
    # domain → {spawns, first_ts, last_ts, with_hint, total}
    domain_agg: Dict[str, Dict[str, Any]] = {}

    total_in_window = 0
    total_with_hint = 0

    for e in entries:
        if e.get("action") != "agent_spawn":
            continue

        ts_raw = e.get("ts", "")
        entry_dt = _entry_ts_to_dt(ts_raw)

        # Apply window filter
        if start_dt is not None and entry_dt is not None:
            if entry_dt < start_dt:
                continue
        if end_dt is not None and entry_dt is not None:
            if entry_dt > end_dt:
                continue

        total_in_window += 1

        # Determine domain bucket
        hint = e.get("dispatch_archetype_hint")
        if hint and isinstance(hint, str) and hint.strip():
            domain = hint.strip()
            has_hint = True
            total_with_hint += 1
        else:
            # Fallback: archetype field
            arch = e.get("archetype")
            if arch and isinstance(arch, str) and arch.strip():
                domain = arch.strip()
            else:
                domain = _UNKNOWN_BUCKET
            has_hint = False

        bucket = domain_agg.setdefault(
            domain,
            {
                "spawns": 0,
                "first_ts": ts_raw or "",
                "last_ts": ts_raw or "",
                "with_hint": 0,
                "total": 0,
            },
        )
        bucket["spawns"] += 1
        bucket["total"] += 1
        if has_hint:
            bucket["with_hint"] += 1
        if ts_raw:
            if not bucket["first_ts"] or ts_raw < bucket["first_ts"]:
                bucket["first_ts"] = ts_raw
            if ts_raw > bucket["last_ts"]:
                bucket["last_ts"] = ts_raw

    # Build output rows
    rows: List[Dict[str, Any]] = []
    for domain in sorted(domain_agg.keys(), key=lambda d: ("" if d != _UNKNOWN_BUCKET else "\xff") + d):
        b = domain_agg[domain]
        hint_pct = round(b["with_hint"] / b["total"] * 100, 1) if b["total"] > 0 else 0.0
        row: Dict[str, Any] = {
            "domain": domain,
            "spawns": b["spawns"],
            "first_seen": b["first_ts"][:10] if b["first_ts"] else "",
            "last_seen": b["last_ts"][:10] if b["last_ts"] else "",
            "hint_coverage_pct": hint_pct,
        }
        rows.append(row)

    # Apply --check-reopen filter
    # M2-CDX-7: UNKNOWN excluded when sunset_reopen_unknown_excluded=true (default)
    # M2-CDX-4: When sunset_reopen_requires_hint_match=true (default), only
    #   spawns whose ORIGINAL audit row carried `dispatch_archetype_hint`
    #   (has_hint=True) qualify for reopen. archetype-fallback rows do not
    #   trigger reopen (per PLAN-080 §8: "spawn carries dispatch_archetype_hint
    #   matching the sunset domain's archetype set").
    if check_reopen and sunset_domains is not None:
        sunset_set = set(sunset_domains)
        reopen_rows = []
        for r in rows:
            if unknown_excluded and r["domain"] == _UNKNOWN_BUCKET:
                continue
            if r["domain"] not in sunset_set:
                continue
            if r["spawns"] < 1:
                continue
            if requires_hint_match:
                # Reopen requires at least one hint-source spawn matching this
                # sunset domain. Use the per-bucket `with_hint` count from the
                # aggregation — bucket["with_hint"] tracks how many spawns in
                # this domain bucket arrived with dispatch_archetype_hint set.
                bucket = domain_agg.get(r["domain"], {})
                if int(bucket.get("with_hint", 0)) < 1:
                    continue
            reopen_rows.append(r)
    else:
        reopen_rows = []

    # Build markdown table
    def _md_table(table_rows: List[Dict[str, Any]]) -> str:
        if not table_rows:
            return "| Domain | Spawns | First seen | Last seen | hint_coverage_pct |\n" \
                   "| ------ | ------ | ---------- | --------- | ----------------- |\n" \
                   "| (no results) | - | - | - | - |\n"
        lines = [
            "| Domain | Spawns | First seen | Last seen | hint_coverage_pct |",
            "| ------ | ------ | ---------- | --------- | ----------------- |",
        ]
        for r in table_rows:
            lines.append(
                f"| {r['domain']} | {r['spawns']} | {r['first_seen']} "
                f"| {r['last_seen']} | {r['hint_coverage_pct']}% |"
            )
        return "\n".join(lines) + "\n"

    output: Dict[str, Any] = {
        "query": "by-domain",
        "version": "1",
        "window": window_label,
        "total_spawns_in_window": total_in_window,
        "overall_hint_coverage_pct": (
            round(total_with_hint / total_in_window * 100, 1)
            if total_in_window > 0
            else 0.0
        ),
        "domain_count": len(rows),
        "domains": rows,
        "markdown_table": _md_table(rows),
    }

    if check_reopen:
        output["check_reopen"] = {
            "sunset_domains_loaded": len(sunset_domains) if sunset_domains is not None else 0,
            "reopen_candidates": reopen_rows,
            "reopen_count": len(reopen_rows),
            "note": (
                "Domains from sunset list with >= 1 spawn in window. "
                "UNKNOWN bucket excluded per M2-CDX-7."
            ),
        }

    return output


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def render(result: Any, *, as_json: bool, as_csv: bool) -> str:
    """Render query results into the requested output format (text / json / markdown)."""
    if as_json:
        return json.dumps(result, indent=2, ensure_ascii=True)
    if as_csv and isinstance(result, list) and result and isinstance(result[0], dict):
        buf = io.StringIO()
        fieldnames = sorted({k for e in result for k in e.keys()})
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for e in result:
            writer.writerow(e)
        return buf.getvalue()

    # Default: pretty-print
    if isinstance(result, dict):
        # by-domain: prefer the embedded markdown table for human output
        if result.get("query") == "by-domain" and "markdown_table" in result:
            lines = [
                f"window: {result.get('window', '')}",
                f"total_spawns: {result.get('total_spawns_in_window', 0)}",
                f"overall_hint_coverage: {result.get('overall_hint_coverage_pct', 0)}%",
                f"domain_count: {result.get('domain_count', 0)}",
                "",
                result["markdown_table"],
            ]
            if "check_reopen" in result:
                cr = result["check_reopen"]
                lines += [
                    "--- Reopen check ---",
                    f"sunset_domains_loaded: {cr.get('sunset_domains_loaded', 0)}",
                    f"reopen_candidates: {cr.get('reopen_count', 0)}",
                ]
                for row in cr.get("reopen_candidates", []):
                    lines.append(f"  * {row['domain']} ({row['spawns']} spawns)")
            return "\n".join(lines)
        return _format_dict(result)
    if isinstance(result, list):
        if not result:
            return "(no results)"
        if isinstance(result[0], dict):
            return _format_table(result)
        return "\n".join(str(x) for x in result)
    return str(result)


def _format_dict(d: Dict[str, Any]) -> str:
    lines = []
    for key, value in d.items():
        if isinstance(value, (list, dict)):
            lines.append(f"{key}:")
            sub = _format_dict(value) if isinstance(value, dict) else _format_list_under(value)
            for ln in sub.split("\n"):
                lines.append(f"  {ln}")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


def _format_list_under(items: List[Any]) -> str:
    if not items:
        return "(empty)"
    if isinstance(items[0], dict):
        return _format_table(items)
    return "\n".join(f"- {x}" for x in items)


def _format_table(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "(no rows)"
    fieldnames = list(rows[0].keys())
    # Compute column widths
    widths = {f: len(f) for f in fieldnames}
    str_rows = []
    for r in rows:
        str_row = {}
        for f in fieldnames:
            s = str(r.get(f, ""))
            str_row[f] = s
            if len(s) > widths[f]:
                widths[f] = min(len(s), 80)
        str_rows.append(str_row)
    header = " | ".join(f.ljust(widths[f]) for f in fieldnames)
    sep = "-+-".join("-" * widths[f] for f in fieldnames)
    body = "\n".join(
        " | ".join(str(r[f])[: widths[f]].ljust(widths[f]) for f in fieldnames)
        for r in str_rows
    )
    return f"{header}\n{sep}\n{body}"


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# PLAN-081 Phase 6-bis — Pair-Rail label store + fp-rate aggregator + Codex
# writeguard summary (R1 S-TDE-3 + S-TDE Q2). Owner labels Case B verdicts
# post-hoc; fp-rate computes lower/upper bounds; codex-writeguard-summary
# aggregates deny-list hits.
# ---------------------------------------------------------------------------

_LABEL_STORE_PATH = (
    Path(__file__).resolve().parent / "audit-log-labels.jsonl"
)
# ADR-108 §Operational labeling protocol: Owner labels Case-B verdicts with
# fp (false-positive — Codex was wrong; close as advisory), tp (true-positive
# — block stands), or triage_pending (extends grace by 24h; max 1 extension
# before mechanical close-as-advisory). retracted is added for explicit Owner
# revocation of a prior label (creates a new chain entry that supersedes).
_LABEL_VALID_CASES = frozenset(["A", "B", "C", "D", "E", "F"])
_LABEL_VALID_LABELS = frozenset(["fp", "tp", "triage_pending", "retracted"])


def _label_store_path() -> Path:
    """Return the labels jsonl path; env override for tests."""
    override = os.environ.get("CEO_PAIR_RAIL_LABEL_STORE_PATH")
    return Path(override) if override else _LABEL_STORE_PATH


def _canonical_json_for_chain(record: Dict[str, Any]) -> str:
    """Canonical JSON for HMAC chain — sort keys + no whitespace + UTF-8."""
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _compute_label_hmac(prev_hmac_hex: str, record: Dict[str, Any]) -> str:
    """Compute HMAC-SHA256 over (prev_hmac || canonical_record) using
    the same key as `audit_hmac.get_or_create_key()`. Each record's
    `hmac` field links to the previous record's hmac forming a chain.

    Hexlified output for jsonl-friendly storage.
    """
    import hmac as _hmac
    import hashlib as _hashlib
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks" / "_lib"))
    try:
        import audit_hmac  # type: ignore
        key = audit_hmac.get_or_create_key()
    except Exception:
        # Fallback: deterministic per-project SHA-256 chain when key infra
        # unavailable (e.g. fresh adopter clone). This still provides
        # tamper-evidence (mutating an old record breaks subsequent chain
        # verification) but is not authenticated against an external key.
        key = b"ceo-pair-rail-label-chain-fallback-key-v1"
    msg = (prev_hmac_hex + _canonical_json_for_chain(record)).encode("utf-8")
    return _hmac.new(key, msg, _hashlib.sha256).hexdigest()


def _load_label_records() -> List[Dict[str, Any]]:
    """Read label jsonl + verify HMAC chain. Returns list of records or [].

    On HMAC mismatch, raises ValueError with the offending record index.
    """
    p = _label_store_path()
    if not p.exists():
        return []
    records: List[Dict[str, Any]] = []
    prev_hmac = ""  # genesis
    with p.open("r", encoding="utf-8") as fh:
        for idx, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"audit-log-labels.jsonl record {idx}: invalid JSON: {e}"
                ) from e
            stored_hmac = rec.pop("hmac", "")
            record_for_compute = dict(rec)
            expected_hmac = _compute_label_hmac(prev_hmac, record_for_compute)
            if stored_hmac != expected_hmac:
                raise ValueError(
                    f"audit-log-labels.jsonl record {idx}: HMAC chain broken "
                    f"(stored={stored_hmac[:16]}, computed={expected_hmac[:16]})"
                )
            rec["hmac"] = stored_hmac
            records.append(rec)
            prev_hmac = stored_hmac
    return records


def _append_label_record(record: Dict[str, Any]) -> str:
    """Append a record to label store with HMAC chain link. Returns the new HMAC."""
    p = _label_store_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    records = _load_label_records()
    prev_hmac = records[-1]["hmac"] if records else ""
    new_hmac = _compute_label_hmac(prev_hmac, record)
    full_record = dict(record)
    full_record["hmac"] = new_hmac
    with p.open("a", encoding="utf-8") as fh:
        fh.write(_canonical_json_for_chain(full_record) + "\n")
    return new_hmac


def cmd_label(entries, args) -> Dict[str, Any]:
    """Owner labels a pair_rail_case event post-hoc. PLAN-081 Phase 6-bis.

    Append-only via HMAC chain to `.claude/scripts/audit-log-labels.jsonl`.
    The Owner labels Case B (Claude PASS + Codex BLOCK) verdicts per
    ADR-108 §Owner labeling protocol with one of:

    - fp (false-positive — Codex was wrong; close as advisory)
    - tp (true-positive — block stands)
    - triage_pending (extends grace by 24h; max 1 extension before
      mechanical close-as-advisory)
    - retracted (creates new chain entry that supersedes the latest
      prior label for the same run_id; if retracted is the most-recent
      entry, the event reverts to unlabeled status in fp-rate computations)

    fp-rate aggregator (cmd_fp_rate) denominator behavior: case_b_total
    ALWAYS includes every Case-B event in the window. The numerator
    counts only `fp` labels for the lower bound; unlabeled +
    triage_pending count as worst-case FP for the upper bound. See
    cmd_fp_rate docstring for the Wilson 95% bounds details.
    """
    run_id = getattr(args, "run_id", None)
    case = getattr(args, "case", None)
    label = getattr(args, "label", None)
    note = getattr(args, "note", "") or ""

    if not run_id:
        return {"verdict": "ERROR", "reason": "--run-id required"}
    if case not in _LABEL_VALID_CASES:
        return {
            "verdict": "ERROR",
            "reason": f"--case must be one of {sorted(_LABEL_VALID_CASES)}, got {case!r}",
        }
    if label not in _LABEL_VALID_LABELS:
        return {
            "verdict": "ERROR",
            "reason": f"--label must be one of {sorted(_LABEL_VALID_LABELS)}, got {label!r}",
        }

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    record = {
        "ts": ts,
        "run_id": run_id,
        "case": case,
        "label": label,
        "note_bucket": "empty" if not note else (
            "short" if len(note) <= 50 else "medium" if len(note) <= 200 else "long"
        ),
    }
    new_hmac = _append_label_record(record)
    return {
        "verdict": "OK",
        "run_id": run_id,
        "case": case,
        "label": label,
        "ts": ts,
        "hmac_prefix": new_hmac[:16],
    }


def _wilson_bounds(successes: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """95% Wilson score interval for binomial proportion (ADR-108 §FP-rate).

    More accurate than naive (p ± z·sqrt(p(1-p)/n)) at small n or
    extreme p. Returns (lower, upper) ∈ [0, 1].
    """
    if n <= 0:
        return 0.0, 0.0
    p = successes / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denom
    half_width = (z * ((p * (1.0 - p) + z2 / (4.0 * n)) / n) ** 0.5) / denom
    lo = max(0.0, center - half_width)
    hi = min(1.0, center + half_width)
    return lo, hi


def cmd_fp_rate(entries, args) -> Dict[str, Any]:
    """PLAN-081 Phase 6-bis (R1 S-TDE-3 + ADR-108 §FP-rate): Case-B
    false-positive rate aggregator with 95% Wilson score interval.

    The Wilson interval provides robust lower/upper bounds at small n or
    extreme proportions, which a simple Laplace bound underestimates. Per
    ADR-108 §FP-rate, the reopen criterion fires when fp_rate_30d > 30%
    via `disable_predicate_eval.py` `fp_rate_30d_above_30pct` predicate.

    Labels per ADR-108 §Owner labeling protocol:
    - `fp` = labeled false-positive — counted in numerator + denominator
    - `tp` = labeled true-positive — counted in denominator (not in fp num)
    - `triage_pending` = grace extended — counted in denominator (still
      provisional; treated as labeled-pending for Wilson computation)
    - `retracted` = supersedes prior label — most-recent non-retracted
      label wins; if retracted is the latest entry for a run_id, the
      event reverts to unlabeled
    The denominator (case_b_total) ALWAYS includes every Case-B event in
    the window — labeled or not. Wilson upper bound treats unlabeled +
    triage_pending as worst-case FP.

    Window selection via --window-days (default 30).
    """
    window_days = getattr(args, "window_days", None)
    if window_days is None:
        window_days = 30  # default 30-day window per ADR-108 §FP-rate

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)
    cutoff_iso = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Filter pair_rail_case events in window — only Case B (asymmetric case)
    case_b_total = 0
    case_b_run_ids: List[str] = []
    for e in entries:
        if e.get("action") != "pair_rail_case":
            continue
        if str(e.get("ts", "")) < cutoff_iso:
            continue
        if e.get("case") != "B":
            continue
        case_b_total += 1
        rid = str(e.get("run_id") or e.get("pair_rail_run_id") or "")
        if rid:
            case_b_run_ids.append(rid)

    # Load labels + match by run_id (latest label wins per run_id; retracted
    # entries supersede prior labels)
    try:
        labels = _load_label_records()
    except ValueError as exc:
        return {"verdict": "ERROR", "reason": str(exc)}

    label_index: Dict[str, str] = {}  # run_id → most-recent non-retracted label
    for r in labels:
        if r.get("case") != "B":
            continue
        rid = str(r.get("run_id", ""))
        lab = str(r.get("label", ""))
        if lab == "retracted":
            label_index.pop(rid, None)
        else:
            label_index[rid] = lab

    labeled_fp = 0
    labeled_tp = 0
    labeled_triage = 0
    unlabeled = 0
    for rid in case_b_run_ids:
        lab = label_index.get(rid)
        if lab == "fp":
            labeled_fp += 1
        elif lab == "tp":
            labeled_tp += 1
        elif lab == "triage_pending":
            labeled_triage += 1
        else:
            unlabeled += 1

    # Wilson 95% bounds: numerator = labeled_fp, denominator = case_b_total
    # Upper bound assumes both unlabeled AND triage_pending are worst-case
    # FP per ADR-108 §FP-rate + cmd_label/cmd_fp_rate docstring contract
    # (Codex iter-6 P2 fix — implementation now matches docstring).
    fp_lo, _ = _wilson_bounds(labeled_fp, case_b_total)
    worst_case_fp = labeled_fp + unlabeled + labeled_triage
    _, fp_hi_via_worst = _wilson_bounds(worst_case_fp, case_b_total)
    fp_hi = fp_hi_via_worst

    # Reopen threshold per ADR-108 §FP-rate (default 0.30 — the 30% bar that
    # triggers `fp_rate_30d_above_30pct` predicate in disable_predicate_eval.py)
    threshold = float(getattr(args, "reopen_threshold", None) or 0.30)
    trigger_reopen = fp_lo > threshold

    return {
        "window_days": window_days,
        "window_start": cutoff_iso,
        "window_end": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "case_b_total": case_b_total,
        "case_b_labeled_fp": labeled_fp,
        "case_b_labeled_tp": labeled_tp,
        "case_b_labeled_triage": labeled_triage,
        "case_b_unlabeled": unlabeled,
        "fp_rate_lower_bound": round(fp_lo, 4),
        "fp_rate_upper_bound": round(fp_hi, 4),
        "wilson_z": 1.96,
        "reopen_threshold": threshold,
        "trigger_reopen": trigger_reopen,
        "predicate_ref": "fp_rate_30d_above_30pct",
    }


def cmd_case_summary(entries, args) -> Dict[str, Any]:
    """PLAN-081 Phase 6-bis (ADR-108 §Operational): Cases A-F distribution.

    Aggregates `pair_rail_case` audit events over the window and returns
    counts + percentages for each Case (A=both PASS, B=Claude PASS+Codex
    BLOCK, C=Claude BLOCK+Codex PASS, D=both BLOCK, E=Jaccard divergence,
    F=Codex outage). Operators use this to monitor healthy distribution
    per ADR-108 §Operational (Case A typically 70-85%; Case F < 2%).
    """
    window_days = getattr(args, "window_days", None)
    if window_days is None:
        window_days = 7  # default 7-day window (faster operational signal)

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)
    cutoff_iso = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    per_case: Dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0}
    unknown_case = 0
    precondition_met_count = 0
    precondition_not_met_count = 0  # Case B'
    for e in entries:
        if e.get("action") != "pair_rail_case":
            continue
        if str(e.get("ts", "")) < cutoff_iso:
            continue
        case = str(e.get("case") or "")
        if case in per_case:
            per_case[case] += 1
            if case == "B":
                pm = e.get("precondition_met")
                if pm is True or pm == "true":
                    precondition_met_count += 1
                elif pm is False or pm == "false":
                    precondition_not_met_count += 1
        else:
            unknown_case += 1

    total = sum(per_case.values()) + unknown_case
    per_case_pct = {
        k: round(v / total * 100.0, 2) if total else 0.0
        for k, v in per_case.items()
    }

    # Healthy distribution sentinels per ADR-108 §Operational
    healthy_ranges = {
        "A": (70.0, 85.0),
        "B": (1.0, 8.0),
        "C": (2.0, 10.0),
        "D": (1.0, 5.0),
        "E": (1.0, 5.0),
        "F": (0.0, 2.0),
    }
    health = {}
    for k, pct in per_case_pct.items():
        lo, hi = healthy_ranges[k]
        if total == 0:
            health[k] = "NO_DATA"
        elif lo <= pct <= hi:
            health[k] = "OK"
        elif pct < lo:
            health[k] = "LOW"
        else:
            health[k] = "HIGH"

    return {
        "window_days": window_days,
        "window_start": cutoff_iso,
        "window_end": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_pair_rail_case_events": total,
        "case_counts": per_case,
        "case_percentages": per_case_pct,
        "unknown_case_count": unknown_case,
        "case_b_precondition_met": precondition_met_count,
        "case_b_precondition_not_met": precondition_not_met_count,
        "health_per_case": health,
    }


def cmd_codex_writeguard_summary(entries, args) -> Dict[str, Any]:
    """PLAN-081 Phase 6-bis (R1 S-TDE Q2): Codex codando deny-list hit summary.

    Aggregates `pair_rail_codex_denylist_hit` audit events by target_path
    bucket. Surfaces top-attempted forbidden paths so operators can detect
    deny-list coverage gaps.
    """
    window_days = getattr(args, "window_days", None)
    if window_days is None:
        window_days = 30

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)
    cutoff_iso = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    per_path: Dict[str, int] = {}
    total_hits = 0
    for e in entries:
        if e.get("action") != "pair_rail_codex_denylist_hit":
            continue
        if str(e.get("ts", "")) < cutoff_iso:
            continue
        path = str(e.get("target_path_bucket") or e.get("target_path") or "unknown")
        per_path[path] = per_path.get(path, 0) + 1
        total_hits += 1

    top_n = int(getattr(args, "top", None) or 10)
    top_paths = sorted(per_path.items(), key=lambda kv: (-kv[1], kv[0]))[:top_n]

    return {
        "window_days": window_days,
        "window_start": cutoff_iso,
        "window_end": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_hits": total_hits,
        "unique_paths": len(per_path),
        "top_paths": [{"path_bucket": p, "hits": c} for p, c in top_paths],
    }


# ---------------------------------------------------------------------------
# PLAN-113 Phase B, Wave W1 — critical-security-action reader (audit-reader
# coverage). These 38 actions are emitted by hooks but had NO reader handler
# in this CLI, so an operator could not surface them (PLAN-112 finding class
# "Critical action has no reader handler"). cmd_critical reads the registry
# below and surfaces, per action, count + first/last timestamp + a compact
# set of SAFE summary fields ALREADY PRESENT on the event (never invented).
# Actions with ZERO occurrences are still listed (count=0) so a
# missing-but-expected critical event is visible — surfacing ABSENCE is the
# whole point.
# ---------------------------------------------------------------------------

_CRITICAL_SECURITY_ACTIONS: Tuple[str, ...] = (
    # --- federation (cross-machine peer trust / write-mode) ---
    "federation_autonomous_call_blocked",
    "federation_cert_revoked",
    "federation_event_action_blocked",
    "federation_hmac_secret_rotated",
    "federation_key_floor_rejected",
    "federation_lan_bind_denied",
    "federation_peer_revoked_remote",
    "federation_scope_denied",
    "federation_spki_fingerprint_mismatch",
    "federation_tamper_detected",
    "federation_write_attempt_blocked",
    "federation_write_endpoint_denied",
    # --- mcp (bearer-token / tenant isolation) ---
    "mcp_bearer_replay_rejected",
    "mcp_cross_tenant_denied",
    "mcp_non_loopback_rejected",
    # --- sentinel-signer (GPG quorum / rotation / revocation) ---
    "gpg_signed",
    "gpg_verified",
    "sentinel_signer_expiry_warned",
    "sentinel_signer_quorum_attempted",
    "sentinel_signer_quorum_failed",
    "sentinel_signer_revoked",
    "sentinel_signer_rotated",
    # --- trading (kill-switch / write-override) ---
    "trading_kill_switch_disabled",
    "trading_kill_switch_invoked",
    "trading_write_override_used",
    # --- credential (age / emergency override) ---
    "credential_blocked_due_to_age",
    "credential_emergency_override_used",
    # --- audit-spool (tamper detection) ---
    "audit_spool_tamper_detected",
    # --- governance (kernel / kill-switch / overrides / pair-rail / swarm) ---
    "anti_ceo_overhead_override_used",
    "bash_canonical_bypass_invoked",
    "confidence_gate_blocked",
    "kernel_extension_landed",
    "kill_switch_invoked",
    "live_adapter_blocked",
    "pair_rail_codex_injection_detected",
    "pair_rail_outgoing_redaction_applied",
    "phase_c_enforcing_flipped",
    "swarm_layer_3_4_blocked",
)

# Map each critical action to its domain group (for the table/json output).
# Domains mirror the comment blocks in _CRITICAL_SECURITY_ACTIONS above.
_CRITICAL_ACTION_DOMAIN: Dict[str, str] = {
    # federation
    "federation_autonomous_call_blocked": "federation",
    "federation_cert_revoked": "federation",
    "federation_event_action_blocked": "federation",
    "federation_hmac_secret_rotated": "federation",
    "federation_key_floor_rejected": "federation",
    "federation_lan_bind_denied": "federation",
    "federation_peer_revoked_remote": "federation",
    "federation_scope_denied": "federation",
    "federation_spki_fingerprint_mismatch": "federation",
    "federation_tamper_detected": "federation",
    "federation_write_attempt_blocked": "federation",
    "federation_write_endpoint_denied": "federation",
    # mcp
    "mcp_bearer_replay_rejected": "mcp",
    "mcp_cross_tenant_denied": "mcp",
    "mcp_non_loopback_rejected": "mcp",
    # sentinel-signer
    "gpg_signed": "sentinel-signer",
    "gpg_verified": "sentinel-signer",
    "sentinel_signer_expiry_warned": "sentinel-signer",
    "sentinel_signer_quorum_attempted": "sentinel-signer",
    "sentinel_signer_quorum_failed": "sentinel-signer",
    "sentinel_signer_revoked": "sentinel-signer",
    "sentinel_signer_rotated": "sentinel-signer",
    # trading
    "trading_kill_switch_disabled": "trading",
    "trading_kill_switch_invoked": "trading",
    "trading_write_override_used": "trading",
    # credential
    "credential_blocked_due_to_age": "credential",
    "credential_emergency_override_used": "credential",
    # audit-spool
    "audit_spool_tamper_detected": "audit-spool",
    # governance
    "anti_ceo_overhead_override_used": "governance",
    "bash_canonical_bypass_invoked": "governance",
    "confidence_gate_blocked": "governance",
    "kernel_extension_landed": "governance",
    "kill_switch_invoked": "governance",
    "live_adapter_blocked": "governance",
    "pair_rail_codex_injection_detected": "governance",
    "pair_rail_outgoing_redaction_applied": "governance",
    "phase_c_enforcing_flipped": "governance",
    "swarm_layer_3_4_blocked": "governance",
}

# Allowlist of SAFE, schema-stable scalar summary keys to echo when present
# on a critical event. We never echo arbitrary fields (avoids surfacing
# large/unexpected payloads) and never INVENT a field — only keys in this set
# that actually exist on the event dict are surfaced, and only scalar values
# (str/int/float/bool). These keys are all part of audit_emit's per-action
# allowlists (already scrubbed at emit time) so echoing them is safe.
_CRITICAL_SAFE_SUMMARY_KEYS: Tuple[str, ...] = (
    "session_id",
    "project",
    "reason",
    "reason_code",
    "scope",
    "phase",
    "migration_phase",
    "env_value",
    "mode",
    "outcome",
    "decision",
    "peer_id",
    "endpoint",
    "tenant",
    "signer",
    "key_id",
    "fingerprint",
    "loop_id",
    "redaction_count",
    "field_count",
)


def cmd_critical(entries: List[Dict[str, Any]], args) -> Dict[str, Any]:
    """`audit-query critical` — surface the 38 critical-security actions.

    PLAN-113 Phase B, Wave W1 (audit-reader-coverage). Each action in
    ``_CRITICAL_SECURITY_ACTIONS`` is emitted by a hook but had no reader
    handler, so an operator could not query it. This command aggregates,
    per critical action that appears in the log: ``count``, first/last ISO
    timestamp, and a compact set of SAFE summary fields drawn from the
    LATEST matching event (only keys in ``_CRITICAL_SAFE_SUMMARY_KEYS`` that
    are actually present + scalar — no invented fields).

    Actions with ZERO occurrences are STILL emitted with ``count=0`` so a
    missing-but-expected critical event is visible (surfacing absence is the
    whole point of the reader-coverage gap PLAN-112 found).

    ``--action <name>`` drills into one action; the name must be in the
    registry (else error). Output is a table (default) or JSON (``--json``).

    Output envelope (mirrors the other v-era commands):
        {"query": "critical", "version": "1",
         "data": {"action_filter": ..., "total_critical_events": N,
                  "present_action_count": M, "registry_size": 38,
                  "actions": [{action, domain, count, first_ts, last_ts,
                               last_summary: {...}}, ...]}}
    """
    action_filter = getattr(args, "action", None)
    if action_filter is not None:
        if action_filter not in _CRITICAL_SECURITY_ACTION_SET:
            print(
                f"[audit-query] ERROR: critical: unknown --action "
                f"{action_filter!r}; must be one of the "
                f"{len(_CRITICAL_SECURITY_ACTIONS)} registry actions",
                file=sys.stderr,
            )
            sys.exit(1)
        registry: Tuple[str, ...] = (action_filter,)
    else:
        registry = _CRITICAL_SECURITY_ACTIONS

    # Single pass: accumulate count / first_ts / last_ts / latest-event
    # safe-summary per critical action. We only track actions in `registry`.
    registry_set = set(registry)
    agg: Dict[str, Dict[str, Any]] = {
        a: {"count": 0, "first_ts": "", "last_ts": "", "last_summary": {}}
        for a in registry
    }
    total_critical_events = 0

    for e in entries:
        action = e.get("action")
        if action not in registry_set:
            continue
        a = agg[action]
        a["count"] += 1
        total_critical_events += 1
        ts = str(e.get("ts") or "")
        if ts:
            if not a["first_ts"] or ts < a["first_ts"]:
                a["first_ts"] = ts
            if ts >= a["last_ts"]:
                a["last_ts"] = ts
                a["last_summary"] = _critical_safe_summary(e)

    actions: List[Dict[str, Any]] = []
    present_action_count = 0
    # Stable order: by domain, then action name (registry is the universe).
    for action in sorted(
        registry,
        key=lambda x: (_CRITICAL_ACTION_DOMAIN.get(x, "zzz"), x),
    ):
        a = agg[action]
        if a["count"] > 0:
            present_action_count += 1
        actions.append(
            {
                "action": action,
                "domain": _CRITICAL_ACTION_DOMAIN.get(action, "unknown"),
                "count": a["count"],
                "first_ts": a["first_ts"],
                "last_ts": a["last_ts"],
                "last_summary": a["last_summary"],
            }
        )

    data = {
        "action_filter": action_filter,
        "registry_size": len(_CRITICAL_SECURITY_ACTIONS),
        "total_critical_events": total_critical_events,
        "present_action_count": present_action_count,
        "absent_action_count": len(registry) - present_action_count,
        "actions": actions,
    }
    return {
        "query": "critical",
        "version": "1",
        "data": data,
    }


# Set form for O(1) membership tests (validation + per-entry filter).
_CRITICAL_SECURITY_ACTION_SET = frozenset(_CRITICAL_SECURITY_ACTIONS)


def _critical_safe_summary(event: Dict[str, Any]) -> Dict[str, Any]:
    """Echo only the SAFE, scalar summary keys present on a critical event.

    Never invents a field: iterates ``_CRITICAL_SAFE_SUMMARY_KEYS`` and copies
    a key only when it exists on the event AND its value is a scalar
    (str/int/float/bool). This keeps the per-action summary compact and avoids
    surfacing large/unexpected payloads.
    """
    out: Dict[str, Any] = {}
    for key in _CRITICAL_SAFE_SUMMARY_KEYS:
        if key not in event:
            continue
        val = event[key]
        if isinstance(val, bool) or isinstance(val, (str, int, float)):
            out[key] = val
    return out


def _build_shared_parser(*, for_subcommand: bool = False) -> argparse.ArgumentParser:
    """Return a parent parser with the shared flags.

    The same flags are registered on the top-level parser AND on every
    sub-command, so users can write either::

        audit-query.py summary --log X --json
        audit-query.py --log X --json summary  # same result

    Precedence rule: the top-level copy owns the real defaults; the
    sub-command copy (``for_subcommand=True``) registers every flag with
    ``default=argparse.SUPPRESS``, so a sub-command that does not repeat
    a flag keeps the value given before it. A flag given on BOTH sides
    resolves to the sub-command-level value. argparse parses a
    sub-command into a fresh namespace and copies every attribute back —
    with real defaults there, ``--log X summary`` silently read the
    default log instead of X (FD-23).
    """
    def _default(value: Any) -> Any:
        return argparse.SUPPRESS if for_subcommand else value

    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument(
        "--log",
        default=_default(None),
        help="Path to audit-log.jsonl (default: CEO_AUDIT_LOG_PATH or ~)",
    )
    shared.add_argument(
        "--include-rotated",
        action="store_true",
        default=_default(False),
        help="Also read audit-log-YYYY-MM*.jsonl siblings",
    )
    shared.add_argument("--json", dest="as_json", action="store_true", default=_default(False))
    shared.add_argument("--csv", dest="as_csv", action="store_true", default=_default(False))
    shared.add_argument(
        "--errors-path",
        default=_default(None),
        help="Override path for the `errors` sub-command",
    )
    return shared


def _add_v1_subparsers(sub: "argparse._SubParsersAction",
                       shared: argparse.ArgumentParser) -> None:
    """Register the original v1 sub-commands (summary/by-skill/... export)."""
    sub.add_parser(
        "summary",
        parents=[shared],
        help="Overview: count, range, top skills, compliance",
    )

    byskill = sub.add_parser("by-skill", parents=[shared], help="Rank skills by usage count")
    byskill.add_argument("--top", type=int, default=10)

    sub.add_parser("compliance", parents=[shared], help="Governance compliance breakdown")

    byday = sub.add_parser("by-day", parents=[shared], help="Spawns-per-day histogram")
    byday.add_argument("--days", type=int, default=14)

    search = sub.add_parser("search", parents=[shared], help="Regex-match against desc_preview")
    search.add_argument("regex")

    since = sub.add_parser("since", parents=[shared], help="Entries on or after a date")
    since.add_argument("iso_date", help="YYYY-MM-DD or full ISO 8601")

    sub.add_parser("errors", parents=[shared], help="Tail the audit-log.errors breadcrumb file")

    stats_p = sub.add_parser(
        "stats",
        parents=[shared],
        help="Prompt-length + response_kind distributions + latency; "
             "--tool-latency for per-tool lifecycle buckets",
    )
    # PLAN-125 WS-1 — per-tool-call lifecycle latency view. Bucket-counts ONLY
    # (the tool_call_lifecycle_recorded action carries NO raw duration_ms per
    # MF-SEC-3), so this is a histogram, NOT percentiles.
    stats_p.add_argument(
        "--tool-latency",
        dest="tool_latency",
        action="store_true",
        help="Per-tool_name_enum duration_bucket histogram (+ success / orphan "
             "rollups) from tool_call_lifecycle_recorded rows. Bucket-counts "
             "only — no percentiles (raw duration_ms is never recorded).",
    )

    export = sub.add_parser("export", parents=[shared], help="Dump all entries in csv/json/tsv")
    export.add_argument(
        "--format", dest="export_format", choices=["csv", "json", "tsv"], default="json"
    )


def _add_v2_subparsers(sub: "argparse._SubParsersAction",
                       shared: argparse.ArgumentParser) -> None:
    """Register Sprint 5 A.2 v2 event-stream sub-commands."""
    sub.add_parser(
        "debate",
        parents=[shared],
        help="Debate rounds: grouped by (plan_id, round) with agents + consensus",
    )
    sub.add_parser(
        "plans",
        parents=[shared],
        help="Plan status transitions per plan_id",
    )
    sub.add_parser(
        "vetoes",
        parents=[shared],
        help="Veto events aggregated by (hook, reason_code)",
    )
    sub.add_parser(
        "benchmarks",
        parents=[shared],
        help=(
            "Benchmark runs aggregated by skill — harbor-style row: "
            "pass_rate + cost + compute + turns (PLAN-133 C4)"
        ),
    )
    sub.add_parser(
        "lessons",
        parents=[shared],
        help="Lesson-write events grouped by archetype + trigger",
    )
    sub.add_parser(
        "metrics",
        parents=[shared],
        help="Cross-cutting derived metrics (veto rate, debate completion)",
    )
    sub.add_parser(
        "health",
        parents=[shared],
        help="Framework health verdict (PASS / WARN / FAIL / NO_DATA)",
    )
    sub.add_parser(
        "tokens",
        parents=[shared],
        help="Spawn token aggregates (PLAN-006 Phase 5a / ADR-016)",
    )


def _add_sprint8_9_subparsers(sub: "argparse._SubParsersAction",
                               shared: argparse.ArgumentParser) -> None:
    """Register confidence-gate + ADR-020 + lesson-effectiveness commands."""
    # Sprint 8 Phase 2 — confidence_gate aggregates (ADR-018)
    claims = sub.add_parser(
        "claims",
        parents=[shared],
        help="Confidence-gate verification aggregates (pass/fail by kind + agent)",
    )
    claims.add_argument("--kind", help="Filter by claim kind (e.g. path_exists)")
    claims.add_argument("--agent", help="Filter by agent name")
    claims.add_argument(
        "--failed-only",
        action="store_true",
        help="Only include events with ≥1 failed claim",
    )

    # Sprint 9 Phase 2 (ADR-020) — prune-restore-ratio measurement
    prr = sub.add_parser(
        "prune-restore-ratio",
        parents=[shared],
        help="Ratio of restored/archived lessons over a time window (ADR-020)",
    )
    prr.add_argument(
        "--since", default="24h",
        help="Window start: 24h / 7d / 30m / ISO 8601 / 'all' (default 24h)",
    )
    prr.add_argument(
        "--until", default=None,
        help="Window end: ISO 8601 (default: now)",
    )

    # Sprint 9 Phase 3 (PLAN-009 P3.4) — Architect outcome tracking
    aout = sub.add_parser(
        "architect-outcomes",
        parents=[shared],
        help="Per-lesson hit/miss from Architect spawns (ADR-015 amended)",
    )
    aout.add_argument(
        "--since", default="24h",
        help="Window start: 24h / 7d / 30m / ISO 8601 / 'all' (default 24h)",
    )
    aout.add_argument(
        "--consumer", default="architect",
        choices=["architect", "benchmark"],
        help="Filter by consumer (default: architect)",
    )
    aout.add_argument(
        "--include-window-only", action="store_true",
        help="Include pre-Sprint-9 window-only events (dirty signal)",
    )

    # Sprint 9 Phase 5 (PLAN-009 P5.1) — lessons effectiveness ranking
    leff = sub.add_parser(
        "lessons-effectiveness",
        parents=[shared],
        help="Per-lesson effectiveness ranking (PLAN-009 Phase 5)",
    )
    leff.add_argument("--since", default="24h",
                      help="Window start (default 24h; 'all' for no filter)")
    leff.add_argument("--include-window-only", action="store_true")
    leff.add_argument("--by", default="effectiveness",
                      choices=["effectiveness", "recency", "injections"],
                      help="Sort axis (default: effectiveness)")
    leff.add_argument("--top", type=int, default=0, help="Return top N")
    leff.add_argument("--bottom", type=int, default=0, help="Return bottom N")


def _add_plan015_subparsers(sub: "argparse._SubParsersAction",
                             shared: argparse.ArgumentParser) -> None:
    """Register PLAN-015 adopter-triage sub-commands."""
    # PLAN-015 Phase 0.5 — adopter-side weekly triage
    wks = sub.add_parser(
        "weekly-summary",
        parents=[shared],
        help="Week-over-week spawn/veto/plan trend for adopter triage (PLAN-015)",
    )
    wks.add_argument("--window", default="7d",
                     help="Window length: 7d (default), 14d, 30d, or 'all'")
    wks.add_argument("--now", default=None,
                     help="Override 'now' with an ISO-8601 timestamp (testing)")

    # PLAN-025 Batch D F-obs-001 — ADR-052 multi-model spawn distribution.
    # Referenced from SLO-SLA.md + DAY-1-CHECKLIST; was missing pre-Batch-D.
    spawn_stats = sub.add_parser(
        "spawn-stats",
        parents=[shared],
        help="Spawn distribution by skill + model (PLAN-025 F-obs-001; ADR-052)",
    )
    spawn_stats.add_argument(
        "--since",
        default=None,
        help="Filter to entries at or after this ISO-8601 timestamp or relative (e.g. '7d')",
    )
    spawn_stats.add_argument(
        "--by",
        default="model",
        choices=("model", "skill", "both"),
        help="Group-by dimension (default: model)",
    )


def _add_plan080_subparsers(sub: "argparse._SubParsersAction",
                             shared: argparse.ArgumentParser) -> None:
    """Register PLAN-080 Phase 1 sub-commands.

    by-domain: group spawn events by dispatch_archetype_hint for squad-bundle
    governance observability (PLAN-080 Phase 1 / ADR-112).
    """
    by_domain = sub.add_parser(
        "by-domain",
        parents=[shared],
        help=(
            "Group agent_spawn events by dispatch_archetype_hint domain "
            "(PLAN-080 Phase 1 / ADR-112)"
        ),
    )
    # Window options — mutually exclusive groups handled in cmd_by_domain
    by_domain.add_argument(
        "--window",
        default=f"{_BY_DOMAIN_DEFAULT_WINDOW_DAYS}d",
        metavar="WINDOW",
        help=(
            "Trailing window (e.g. 30d, 7d, 14d). "
            f"Default: {_BY_DOMAIN_DEFAULT_WINDOW_DAYS}d. "
            "Ignored when --start/--end are provided."
        ),
    )
    by_domain.add_argument(
        "--start",
        default=None,
        metavar="YYYY-MM-DD",
        help="Start date (inclusive). Must be paired with --end.",
    )
    by_domain.add_argument(
        "--end",
        default=None,
        metavar="YYYY-MM-DD",
        help="End date (inclusive). Must be paired with --start.",
    )
    by_domain.add_argument(
        "--check-reopen",
        action="store_true",
        dest="check_reopen",
        help=(
            "Filter output to sunset domains (from grandfather-cap.policy.yaml) "
            "with >= 1 spawn. UNKNOWN bucket excluded per M2-CDX-7."
        ),
    )


def _add_plan081_subparsers(sub: "argparse._SubParsersAction",
                             shared: argparse.ArgumentParser) -> None:
    """Register PLAN-081 Phase 6-bis sub-commands.

    label: Owner labels a pair_rail_case event post-hoc (R1 S-TDE-3).
    fp-rate: false-positive rate aggregator with reopen-trigger threshold.
    codex-writeguard-summary: aggregates pair_rail_codex_denylist_hit events
                              by target_path bucket (R1 S-TDE Q2).
    """
    # --- label ---
    label_p = sub.add_parser(
        "label",
        parents=[shared],
        help="Append a Case-B verdict label to audit-log-labels.jsonl (PLAN-081 Phase 6-bis)",
    )
    label_p.add_argument(
        "--run-id", required=True, dest="run_id",
        help="pair_rail_promotion_run_id (UUID hex) of the event being labeled",
    )
    label_p.add_argument(
        "--case", required=True, choices=sorted(_LABEL_VALID_CASES),
        help="Case letter A-F to label",
    )
    label_p.add_argument(
        "--label", required=True, choices=sorted(_LABEL_VALID_LABELS),
        help="Verdict label: fp | tp | triage_pending | retracted (per ADR-108 §Owner labeling protocol)",
    )
    label_p.add_argument(
        "--note", default="",
        help="Optional free-form note (length is bucketed in audit emit; content NOT stored)",
    )

    # --- fp-rate ---
    fp_p = sub.add_parser(
        "fp-rate",
        parents=[shared],
        help="Case-B false-positive rate aggregator (PLAN-081 Phase 6-bis R1 S-TDE-3)",
    )
    fp_p.add_argument(
        "--window-days", type=int, default=30, dest="window_days",
        help="Trailing window in days (default 30)",
    )
    fp_p.add_argument(
        "--reopen-threshold", type=float, default=0.30, dest="reopen_threshold",
        help="trigger_reopen=true when fp_rate_lower_bound > threshold (default 0.30 per ADR-108 §FP-rate)",
    )

    # --- case-summary ---
    cs_p = sub.add_parser(
        "case-summary",
        parents=[shared],
        help="Cases A-F distribution rollup over window (PLAN-081 Phase 6-bis ADR-108 §Operational)",
    )
    cs_p.add_argument(
        "--window-days", type=int, default=7, dest="window_days",
        help="Trailing window in days (default 7 — faster operational signal than 30d)",
    )

    # --- codex-writeguard-summary ---
    cw_p = sub.add_parser(
        "codex-writeguard-summary",
        parents=[shared],
        help="Codex codando deny-list hit summary by path bucket (PLAN-081 Phase 6-bis R1 S-TDE Q2)",
    )
    cw_p.add_argument(
        "--window-days", type=int, default=30, dest="window_days",
        help="Trailing window in days (default 30)",
    )
    cw_p.add_argument(
        "--top", type=int, default=10,
        help="Top N most-attempted forbidden paths (default 10)",
    )


def _add_plan113_subparsers(sub: "argparse._SubParsersAction",
                            shared: argparse.ArgumentParser) -> None:
    """Register PLAN-113 Phase B Wave W1 sub-command.

    critical: surface the 38 critical-security actions (count + first/last
    ts + safe summary), listing zero-occurrence actions so missing-but-
    expected critical events are visible (audit-reader-coverage gap).
    """
    crit = sub.add_parser(
        "critical",
        parents=[shared],
        help=(
            "Surface critical-security actions (count + last-seen + safe "
            "summary); absent actions listed with count=0 (PLAN-113 W1)"
        ),
    )
    crit.add_argument(
        "--action",
        default=None,
        metavar="ACTION",
        help=(
            "Drill into a single critical action (must be one of the "
            "registry actions; errors otherwise)"
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    """Construct the full audit-query argparse tree.

    Delegates each era of sub-commands to a private helper
    (``_add_v1_subparsers`` / ``_add_v2_subparsers`` /
    ``_add_sprint8_9_subparsers`` / ``_add_plan015_subparsers`` /
    ``_add_plan080_subparsers`` / ``_add_plan081_subparsers``). The
    public contract of this function is unchanged — callers get back
    an ``argparse.ArgumentParser`` with ``cmd`` as the required
    subcommand. Sub-commands get the SUPPRESS-default copy of the shared
    flags (precedence rule in ``_build_shared_parser``).
    """
    shared = _build_shared_parser()
    sub_shared = _build_shared_parser(for_subcommand=True)

    parser = argparse.ArgumentParser(
        prog="audit-query.py",
        parents=[shared],
        description="Query the ceo-orchestration agent spawn audit log",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  audit-query.py summary\n"
            "  audit-query.py by-skill --top 10\n"
            "  audit-query.py compliance --json\n"
            "  audit-query.py search 'security' --include-rotated\n"
            "  audit-query.py by-day --days 7\n"
            "  audit-query.py since 2026-04-01\n"
            "  audit-query.py export --format csv > spawns.csv\n"
            "  audit-query.py stats --json\n"
            "  audit-query.py errors\n"
            "  audit-query.py by-domain --window 30d\n"
            "  audit-query.py by-domain --start 2026-04-01 --end 2026-05-01\n"
            "  audit-query.py by-domain --window 30d --check-reopen\n"
            "  audit-query.py critical\n"
            "  audit-query.py critical --action kill_switch_invoked --json\n"
        ),
    )

    sub = parser.add_subparsers(dest="cmd", required=True)
    _add_v1_subparsers(sub, sub_shared)
    _add_v2_subparsers(sub, sub_shared)
    _add_sprint8_9_subparsers(sub, sub_shared)
    _add_plan015_subparsers(sub, sub_shared)
    _add_plan080_subparsers(sub, sub_shared)
    _add_plan081_subparsers(sub, sub_shared)
    _add_plan113_subparsers(sub, sub_shared)

    return parser


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


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
