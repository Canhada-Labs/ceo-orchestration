"""Extracted cost-transcripts implementation: cli."""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_SINCE_RE = re.compile(r"^(\d+)([dh])$")


def _parse_since(expr: str) -> timedelta:
    m = _SINCE_RE.match(expr.strip())
    if not m:
        raise argparse.ArgumentTypeError(
            "invalid --since %r; expected <N>d or <N>h (documented: 30d, 7d, 24h)" % expr
        )
    n = int(m.group(1))
    return timedelta(days=n) if m.group(2) == "d" else timedelta(hours=n)


def _parse_instant(expr: str, flag: str = "--until") -> datetime:
    """An ABSOLUTE ISO-8601 window bound, read by the SAME reader the records use.

    ``_parse_ts`` is what turns a transcript line's ``timestamp`` into
    ``UsageRecord.ts``; parsing a bound with it is what keeps the bound
    and the field it filters from drifting apart -- a ``Z`` suffix, an
    explicit offset and a naive value are all read exactly as a record's
    own stamp would be. BOTH absolute bounds go through this ONE function
    (``--until``, and ``--since-at`` since rail r4), so the two ends of a
    closed window can never be read by two different grammars. Both are
    INCLUSIVE at record resolution: a record stamped exactly at a bound
    is INSIDE the window.
    """
    dt = _parse_ts(expr.strip() if isinstance(expr, str) else expr)
    if dt is None:
        raise argparse.ArgumentTypeError(
            "invalid %s %r; expected an ISO-8601 instant such as "
            "2026-09-02T12:55:05.807Z, 2026-09-02T12:55:05.807+00:00 or "
            "2026-09-02 (a naive value is read as UTC)" % (flag, expr)
        )
    return dt


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ceo-cost-transcripts.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Cost/token report from harness-native transcripts "
            "(message.usage), because ceo-cost.py / budget-summary.py's "
            "audit-log rollup carries ~0 tokens (PLAN-186 W0; report "
            "docs/research/s339-orchestrator-study/05-finops-routing.md P0-1)."
        ),
        epilog=(
            "Pricing source (default): an EMBEDDED table — report "
            "05-finops-routing.md \xa71.4, itself sourced from "
            "docs/provider-pricing.md's primary table + cache-tier "
            "multiplier section. cost-table.yaml (next to this script) has "
            "NO cache-read/cache-write columns, so it structurally cannot "
            "supply this instrument's pricing shape on its own; when it "
            "parses, its base input/output rates are used and the "
            "Owner-ratified corrections (claude-sonnet-5 -> $2/$10, "
            "2026-09-01, CLAUDE.md commit e47bf5d) are layered on top "
            "ONLY where the file's row actually differs; since "
            "b6dce78 the in-tree file already carries that row, so "
            "the correction is a no-op and the report's pricing: line "
            "says so. Pass --pricing "
            "explicitly to use a different file's rates as-is (no "
            "correction applied). Cache-read multiplier: 0.10x base "
            "(" + _cache_read_exceptions_text() + "). Cache-write multiplier: 1.25x "
            "base at the 5-minute TTL, 2.00x at the 1-hour TTL. "
            "WINDOW: the LOWER bound is either --since (a span measured "
            "back from now) or --since-at <ISO-8601> (an absolute "
            "instant), and --until <ISO-8601> is the UPPER one; all "
            "three filter the SAME record timestamp (UsageRecord.ts), "
            "and the absolute bounds are INCLUSIVE at RECORD resolution "
            "-- a record stamped exactly at a bound is kept, its "
            "neighbour 1 ms away is not. --since-at with --until is a "
            "CLOSED window that is REPRODUCIBLE: re-run tomorrow it "
            "selects the same records, which --since cannot promise "
            "because its bound moves with the wall clock. With the "
            "two-dimension cut (--by role,model) they make PLAN-186 "
            "AC-1's byte-for-byte check reproducible from this CLI "
            "alone, with no external harness."
        ),
    )
    # The window's LOWER bound has exactly TWO spellings and they are
    # mutually exclusive at the PARSER level: a run cannot carry both a
    # relative and an absolute lower bound with one of them silently
    # winning (rail r4 [P1]).
    lower = p.add_mutually_exclusive_group()
    lower.add_argument(
        "--since",
        default="30d",
        type=str,
        help=(
            "LOWER bound of the window, RELATIVE to now: <N>d or <N>h "
            "(default 30d; 7d and 24h also documented). Filters "
            "UsageRecord.ts. Because it is measured back from the wall "
            "clock, the SAME command run later selects a DIFFERENT set "
            "of records -- use --since-at when the window has to be "
            "reproducible."
        ),
    )
    lower.add_argument(
        "--since-at",
        default=None,
        metavar="ISO8601",
        help=(
            "LOWER bound of the window as an ABSOLUTE instant, INCLUSIVE "
            "at record resolution (e.g. 2026-08-03T00:00:00Z; a naive "
            "value is read as UTC). Filters the SAME field --since and "
            "--until do (UsageRecord.ts). Mutually exclusive with "
            "--since: passing both is refused BY NAME (rc 2). Together "
            "with --until it makes a CLOSED, REPRODUCIBLE window -- the "
            "same command tomorrow returns the same numbers. "
            "Default: the relative --since."
        ),
    )
    p.add_argument(
        "--until",
        default=None,
        metavar="ISO8601",
        help=(
            "UPPER bound of the window, INCLUSIVE at record resolution "
            "(e.g. 2026-09-02T12:55:05.807Z; a naive value is read as "
            "UTC). Filters the SAME field --since does (UsageRecord.ts), "
            "so the two bounds always describe one window. Rail r2 "
            "[P2]: the default is NO upper bound, not `now` -- "
            "defaulting to `now` would SILENTLY drop a "
            "clock-skewed future-dated record, and a report that "
            "hides records is worse than one that shows them. "
            "Default: unbounded above."
        ),
    )
    p.add_argument(
        "--project-dir",
        default=None,
        help=(
            "harness transcripts root (the dir holding <session>.jsonl + "
            "<session>/subagents/**). Default: _lib.runtime_paths."
            "runtime_state_dir() — same resolver as "
            "'python3 .claude/hooks/_lib/runtime_paths.py --state-dir'."
        ),
    )
    p.add_argument("--json", action="store_true", help="emit JSON instead of a human table")
    p.add_argument(
        "--by",
        action="append",
        default=None,
        metavar="DIM[,DIM...]",
        help=(
            "breakdown dimension(s) for the report table, comma-separated; "
            "the ORDER given is the grouping order (default: model). "
            "Valid: " + ", ".join(sorted(_GROUP_KEYS)) + ". Example: "
            "--by role,model. A malformed value is refused BY NAME (rc 2), "
            "never silently reduced to one dimension -- and so is a "
            "REPEATED flag (--by role --by model), which argparse's "
            "default `store` action would resolve by keeping only the "
            "LAST value, dropping a dimension without a word."
        ),
    )
    p.add_argument(
        "--pricing",
        default=None,
        metavar="YAML",
        help="cost-table.yaml-shaped file; default: cost-table.yaml next to this script (see epilog)",
    )
    p.add_argument(
        "--assert-routing",
        action="store_true",
        help=(
            "turn the ROUTING INVARIANT verdict (PLAN-186 AC-13: served "
            "model == declared model, VETO archetypes served inside the "
            "floor) into the exit code: 0 GREEN, 1 RED, 3 not proven "
            "(INCONCLUSIVE or VACUOUS). The verdict is evaluated and "
            "printed on EVERY run; without this flag the exit code stays "
            "0 so a cost report is never broken by a routing finding."
        ),
    )
    return p


def _default_project_dir() -> Optional[Path]:
    if _rp is None:
        return None
    try:
        return _rp.runtime_state_dir()
    except Exception:
        return None


def _fmt_usd(v: float) -> str:
    return "$%.2f" % v


def _fmt_int(v: float) -> str:
    return "{:,}".format(int(v))


def _window_label(args: argparse.Namespace) -> str:
    """The window as the report prints it: the lower bound the run really
    APPLIED (relative `--since` or absolute `--since-at`), plus the upper
    one when `--until` was given. Never invents a bound the run did not
    apply -- which is why `main()` blanks `since_raw` under `--since-at`
    instead of leaving the unused `30d` default to be printed here.
    """
    if getattr(args, "since_at_raw", None) is not None:
        lower = "%s (limite inferior ABSOLUTO, inclusivo)" % args.since_at_raw
    else:
        lower = args.since_raw
    if getattr(args, "until_raw", None) is None:
        return lower
    return "%s ate %s (limite superior INCLUSIVO)" % (lower, args.until_raw)


def _human_report(
    args: argparse.Namespace,
    project_dir: Path,
    pricing_result: PricingResult,
    counters: ScanCounters,
    grand: Dict[str, float],
    role_totals: Dict[str, Dict[str, float]],
    group_totals: Dict[str, Dict[str, float]],
    unresolved: Dict[str, Dict[str, float]],
    elapsed_s: float,
    routing: Optional[Dict[str, Any]] = None,
) -> str:
    lines: List[str] = []
    lines.append("ceo-cost-transcripts — janela: %s" % _window_label(args))
    lines.append("project-dir: %s" % project_dir)
    lines.append("pricing: %s" % pricing_result.source)
    lines.append(
        "arquivos: %d assento + %d subagente | linhas: %d vistas, %d candidatas, "
        "%d corrompidas, %d sem timestamp, %d ilegiveis"
        % (
            args.n_top_files,
            args.n_sub_files,
            counters.lines_seen,
            counters.candidate_lines,
            counters.corrupted_lines,
            counters.missing_timestamp,
            counters.unreadable_files,
        )
    )
    lines.append(
        "dedup: %d registros unicos (%d duplicatas descartadas); "
        "sidechain-em-topo ignorado: %d"
        % (counters.deduped_records, args.n_dropped_dupes, counters.sidechain_in_toplevel_skipped)
    )
    if unresolved:
        tot_unresolved_turns = sum(int(v["turns"]) for v in unresolved.values())
        lines.append(
            "AVISO: %d modelo(s) nao resolvido(s) na tabela de precos, %d turnos, "
            "custo reportado como $0 para eles (nunca inventado): %s"
            % (len(unresolved), tot_unresolved_turns, ", ".join(sorted(unresolved.keys())))
        )
    lines.append("")
    lines.append("TOTAIS POR PAPEL")
    header = "%-12s %8s %14s %14s %14s %14s %14s %12s" % (
        "papel", "turnos", "input", "cache_w5m", "cache_w1h", "cache_read", "output", "USD",
    )
    lines.append(header)
    for role in ("assento", "subagent"):
        d = role_totals.get(role, _bucket_totals())
        lines.append(
            "%-12s %8s %14s %14s %14s %14s %14s %12s"
            % (
                role,
                _fmt_int(d["turns"]),
                _fmt_int(d["input_tokens"]),
                _fmt_int(d["cache_write_5m"]),
                _fmt_int(d["cache_write_1h"]),
                _fmt_int(d["cache_read_tokens"]),
                _fmt_int(d["output_tokens"]),
                _fmt_usd(d["usd"]),
            )
        )
    lines.append(
        "%-12s %8s %14s %14s %14s %14s %14s %12s"
        % (
            "TOTAL",
            _fmt_int(grand["turns"]),
            _fmt_int(grand["input_tokens"]),
            _fmt_int(grand["cache_write_5m"]),
            _fmt_int(grand["cache_write_1h"]),
            _fmt_int(grand["cache_read_tokens"]),
            _fmt_int(grand["output_tokens"]),
            _fmt_usd(grand["usd"]),
        )
    )
    lines.append("")
    lines.append("QUEBRA POR --by %s (ordenado por USD desc)" % args.by)
    lines.append("%-40s %8s %12s %8s" % (args.by, "turnos", "USD", "share%"))
    rows = sorted(group_totals.items(), key=lambda kv: kv[1]["usd"], reverse=True)
    grand_usd = grand["usd"] or 1.0
    for k, d in rows[:40]:
        share = 100.0 * d["usd"] / grand_usd
        lines.append("%-40s %8s %12s %7.1f%%" % (str(k)[:40], _fmt_int(d["turns"]), _fmt_usd(d["usd"]), share))
    if len(rows) > 40:
        lines.append("... (+%d linhas omitidas)" % (len(rows) - 40))
    lines.append("")
    routing_lines = _routing_lines(routing)
    if routing_lines:
        lines.extend(routing_lines)
        lines.append("")
    lines.append("tempo de execucao: %.2fs" % elapsed_s)
    return "\n".join(lines)


def _json_report(
    args: argparse.Namespace,
    project_dir: Path,
    pricing_result: PricingResult,
    counters: ScanCounters,
    grand: Dict[str, float],
    role_totals: Dict[str, Dict[str, float]],
    group_totals: Dict[str, Dict[str, float]],
    unresolved: Dict[str, Dict[str, float]],
    elapsed_s: float,
    routing: Optional[Dict[str, Any]] = None,
) -> str:
    payload = {
        # Exactly ONE of `since` / `since_at` is non-null: the bound the
        # run actually applied. The unused `--since` default is reported
        # as null rather than as a window nobody asked for.
        "since": args.since_raw,
        "since_at": args.since_at_raw,
        "until": args.until_raw,
        "by": args.by,
        "project_dir": str(project_dir),
        "pricing_source": pricing_result.source,
        "pricing_used_fallback": pricing_result.used_fallback,
        "files": {"assento": args.n_top_files, "subagent": args.n_sub_files},
        "lines": {
            "seen": counters.lines_seen,
            "candidate": counters.candidate_lines,
            "corrupted": counters.corrupted_lines,
            "missing_timestamp": counters.missing_timestamp,
            "unreadable_files": counters.unreadable_files,
        },
        "dedup": {
            "unique_records": counters.deduped_records,
            "dropped_duplicates": args.n_dropped_dupes,
            "sidechain_in_toplevel_skipped": counters.sidechain_in_toplevel_skipped,
        },
        "unresolved_models": unresolved,
        "grand_total": grand,
        "by_role": role_totals,
        "by_" + args.by: group_totals,
        "routing": routing,
        "elapsed_s": elapsed_s,
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def main(argv: Optional[List[str]] = None) -> int:
    t0 = time.time()
    parser = build_parser()
    args = parser.parse_args(argv)
    args.since_raw = args.since
    try:
        args.since = _parse_since(args.since_raw)
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
        return 2  # pragma: no cover - parser.error() calls sys.exit()

    # The two ABSOLUTE bounds, read by the ONE instant parser. The parser
    # already refuses --since together with --since-at, so at most one
    # lower bound reaches the pipeline; when the absolute one is given,
    # `since_raw` is BLANKED so neither the report header nor the JSON
    # can advertise a `30d` default that was never applied.
    args.since_at_raw = args.since_at
    args.until_raw = args.until
    try:
        args.since_at = (
            _parse_instant(args.since_at_raw, "--since-at")
            if args.since_at_raw is not None
            else None
        )
        args.until = (
            _parse_instant(args.until_raw, "--until")
            if args.until_raw is not None
            else None
        )
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
        return 2  # pragma: no cover - parser.error() calls sys.exit()
    if args.since_at is not None:
        args.since_raw = None

    # `--by` is `action="append"`, so a REPEATED flag arrives as a LIST
    # and can be refused. Rail r4 [P1]: with the default `store` action
    # `--by role --by model` kept only `model` and grouped by one
    # dimension without a word -- the exact silent reduction the help
    # promises never happens.
    by_flags = args.by if args.by is not None else ["model"]
    if len(by_flags) > 1:
        parser.error(
            "--by was given %d times (%s); pass ONE --by with a "
            "comma-separated list (e.g. --by %s) -- a repeated flag would "
            "keep only the LAST value and silently drop a dimension"
            % (
                len(by_flags),
                ", ".join(repr(b) for b in by_flags),
                ",".join(by_flags),
            )
        )
        return 2  # pragma: no cover - parser.error() calls sys.exit()
    try:
        args.by = ",".join(_split_by(by_flags[0]))
    except ValueError as exc:
        parser.error("invalid --by %r: %s" % (by_flags[0], exc))
        return 2  # pragma: no cover - parser.error() calls sys.exit()

    if args.project_dir:
        project_dir = Path(args.project_dir)
    else:
        project_dir = _default_project_dir()
        if project_dir is None:
            sys.stderr.write(
                "ceo-cost-transcripts: could not resolve a default --project-dir "
                "(_lib.runtime_paths import failed); pass --project-dir explicitly.\n"
            )
            return 2

    if not project_dir.is_dir():
        sys.stderr.write("ceo-cost-transcripts: --project-dir does not exist: %s\n" % project_dir)
        return 2

    # ONE lower bound reaches the pipeline: the ABSOLUTE `--since-at` if
    # it was given, otherwise `now - --since`. Before rail r4 only the
    # relative form existed, so a command documented as a `closed window`
    # was not reproducible -- its lower end moved with the wall clock.
    if args.since_at is not None:
        cutoff = args.since_at
        lower_flag = "--since-at %s" % args.since_at_raw
    else:
        cutoff = datetime.now(timezone.utc) - args.since
        lower_flag = "--since %s (= %s)" % (args.since_raw, cutoff.isoformat())
    # A window whose upper bound does not STRICTLY follow its lower one
    # is refused BY NAME instead of printing a report over it: an empty
    # report is indistinguishable from a corpus with no records, and the
    # relative lower bound can climb above a fixed `--until` between two
    # runs of the very same command (rail r4 [P1]).
    if args.until is not None and args.until <= cutoff:
        parser.error(
            "--until %s does not follow the window's LOWER bound %s: the "
            "upper bound must be STRICTLY after the lower one, so this run "
            "is refused rather than reported as an empty corpus"
            % (args.until_raw, lower_flag)
        )
        return 2  # pragma: no cover - parser.error() calls sys.exit()

    # ONE pipeline for the CLI and for the programmatic callers
    # (PLAN-186 W0, AC-1b): a second copy here is how the printed report
    # and ceo-cost.py's block would silently disagree.
    rolled = transcript_rollup(
        project_dir,
        cutoff=cutoff,
        pricing_arg=args.pricing,
        by=args.by,
        until=args.until,
    )
    pricing_result = rolled["pricing_result"]
    counters = rolled["counters"]
    args.n_top_files = rolled["files"]["assento"]
    args.n_sub_files = rolled["files"]["subagent"]
    args.n_dropped_dupes = rolled["dropped_duplicates"]
    unresolved_by_model = rolled["unresolved_models"]
    grand = rolled["grand_total"]
    role_totals = rolled["by_role"]
    group_totals = rolled["by_dimension"]
    routing = rolled["routing"]

    elapsed_s = time.time() - t0

    if args.json:
        out = _json_report(
            args, project_dir, pricing_result, counters, grand, role_totals, group_totals, unresolved_by_model, elapsed_s, routing
        )
    else:
        out = _human_report(
            args, project_dir, pricing_result, counters, grand, role_totals, group_totals, unresolved_by_model, elapsed_s, routing
        )
    print(out)
    # AC-13: the verdict was evaluated and printed above on EVERY run; it
    # only becomes the exit code when the caller asks for the gate.
    return routing_rc(routing) if args.assert_routing else 0


