"""parsing audit-query declarations."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

__all__ = ('_build_shared_parser', '_add_v1_subparsers', '_add_v2_subparsers', '_add_sprint8_9_subparsers', '_add_plan015_subparsers', '_add_plan080_subparsers', '_add_plan081_subparsers', '_add_plan113_subparsers', 'build_parser')

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


