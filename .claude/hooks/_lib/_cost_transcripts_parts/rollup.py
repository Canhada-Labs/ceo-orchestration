"""Extracted cost-transcripts implementation: rollup."""
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

ROOT_ENV = "CEO_COST_TRANSCRIPTS_DIR"

#: The `--source` domain, shared by both callers.
SOURCE_CHOICES = ("transcripts", "audit", "both")

TRANSCRIPTS_BANNER = "=== SOURCE: TRANSCRIPTS (message.usage -- PRIMARY) ==="
AUDIT_BANNER = "=== SOURCE: AUDIT LOG (governance ledger -- SECONDARY) ==="


def transcript_rollup(
    project_dir: Any,
    cutoff: Optional[datetime] = None,
    pricing_arg: Optional[str] = None,
    by: str = "model",
    until: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Scan + dedup + price `project_dir`, returning the rollup as data.

    `cutoff` is an aware datetime; records strictly older are dropped.
    `until` is the UPPER bound, INCLUSIVE at record resolution; records
    stamped after it are dropped. `None` on either side means unbounded
    there. This is the single pipeline the CLI itself runs, so the API
    and the printed report can never disagree.
    """
    _split_by(by)  # validate the breakdown BY NAME before any I/O
    project_dir = Path(project_dir)
    pricing_result = load_pricing(pricing_arg)

    top_files, sub_files = discover_files(project_dir)
    counters = ScanCounters()
    records = scan_files(top_files, "assento", project_dir, counters)
    records += scan_files(sub_files, "subagent", project_dir, counters)

    # ONE timestamp field carries BOTH bounds: `UsageRecord.ts`, the
    # parsed `timestamp` of the transcript line. A window whose two ends
    # filtered different fields would be a lie, so the two filters sit
    # here, adjacent, over the same attribute. The upper bound is
    # INCLUSIVE at record resolution (`<=`, never `<`): a record stamped
    # exactly at the bound belongs to the window.
    if cutoff is not None:
        records = [r for r in records if r.ts >= cutoff]
    if until is not None:
        records = [r for r in records if r.ts <= until]

    deduped, dropped = dedup(records)
    counters.deduped_records = len(deduped)

    priced = price_records(deduped, pricing_result.table)

    unresolved: Dict[str, Dict[str, float]] = {}
    for p in priced:
        if not p.resolved:
            d = unresolved.setdefault(p.rec.model, _bucket_totals())
            d["turns"] += 1
            for cls in _TOKEN_CLASSES:
                d[cls] += getattr(p.rec, cls)

    grand, role_totals, group_totals = aggregate(priced, by)
    # AC-13: the routing invariant is asserted by the SAME pipeline the
    # report and both callers run, over the SAME window, so no renderer can
    # print a total without the verdict that travels with it.
    routing = routing_invariant_safe(project_dir, cutoff=cutoff, until=until)
    return {
        "project_dir": str(project_dir),
        "pricing_result": pricing_result,
        "pricing_source": pricing_result.source,
        "pricing_used_fallback": pricing_result.used_fallback,
        "by": by,
        "files": {"assento": len(top_files), "subagent": len(sub_files)},
        "counters": counters,
        "dropped_duplicates": dropped,
        "unresolved_models": unresolved,
        "grand_total": grand,
        "by_role": role_totals,
        "by_dimension": group_totals,
        "routing": routing,
    }


def resolve_root(root_arg: Optional[str] = None) -> Optional[Path]:
    """Flag > `$CEO_COST_TRANSCRIPTS_DIR` > `_lib.runtime_paths`."""
    if root_arg:
        return Path(root_arg)
    env = os.environ.get(ROOT_ENV)
    if env:
        return Path(env)
    return _default_project_dir()


def explicit_root_given(root_arg: Optional[str] = None) -> bool:
    """True when the CALLER pinned the corpus (flag or env), not the
    ambient project resolver. Rail r2 P1-1 turns on this distinction.
    """
    return bool(root_arg) or bool(os.environ.get(ROOT_ENV))


#: The env carriers that point the SECONDARY (audit) ledger somewhere
#: specific. Rail r3 P1-1: a flag is not the only way to override it.
AUDIT_PATH_ENV_CARRIERS = ("CEO_AUDIT_LOG_PATH", "CEO_AUDIT_LOG_DIR")


def audit_source_is_pinned(
    path_arg: Optional[str] = None,
    carriers: Optional[Tuple[str, ...]] = None,
) -> bool:
    """True when the audit ledger was pointed at a specific place.

    ``carriers`` names the env vars the CALLER actually obeys; the
    default is every carrier this instrument knows about. A caller that
    ignores one of them must say so, or the cross-project pairing check
    suppresses its PRIMARY block over an override that moved nothing
    (rail S341 r1 [P2]: ``budget-summary.py`` resolves its audit dir
    from ``CEO_AUDIT_LOG_DIR`` alone, while ``ceo-cost.py`` honours both
    and therefore passes nothing).
    """
    if path_arg:
        return True
    keys = AUDIT_PATH_ENV_CARRIERS if carriers is None else tuple(carriers)
    return any(os.environ.get(k) for k in keys)


def collect(
    root_arg: Optional[str] = None,
    cutoff: Optional[datetime] = None,
    by: str = "model",
    note: Optional[str] = None,
    audit_override: bool = False,
) -> Dict[str, Any]:
    """Caller-facing collector: a JSON-safe rollup, or a labelled note.

    NEVER raises: an absent root, an unreadable corpus or an internal
    failure comes back as `{'available': False, 'reason': ...}` so the
    SECONDARY (audit) source keeps rendering unchanged.
    """
    # Rail r2 P1-1: when the caller pointed the SECONDARY source at an
    # explicit path (--log / --audit-dir) but left the PRIMARY one to the
    # ambient project resolver, the report would juxtapose project A's
    # transcripts with project B's audit log. Refuse the pairing by name
    # rather than print two ledgers from two projects side by side.
    if audit_override and not explicit_root_given(root_arg):
        return {
            "available": False,
            "reason": (
                "the audit source was pointed at an explicit path but no "
                "transcripts root was given - refusing to pair one "
                "project's transcripts with another project's audit log "
                "(pass --transcripts-root or set %s)" % ROOT_ENV
            ),
        }
    root = resolve_root(root_arg)
    if root is None:
        return {
            "available": False,
            "reason": (
                "could not resolve a transcripts root (pass the flag or "
                "set %s)" % ROOT_ENV
            ),
        }
    if not root.is_dir():
        return {
            "available": False,
            "reason": "transcripts root does not exist: %s" % root,
        }
    try:
        res = transcript_rollup(root, cutoff=cutoff, by=by)
    except Exception as exc:  # pragma: no cover - fail-soft envelope
        return {
            "available": False,
            "reason": "transcripts rollup failed: %s" % type(exc).__name__,
        }
    # Rail r1 P1-1: a corrupted line, a line without a timestamp or an
    # unreadable file is SILENTLY dropped by scan_files() — publishing
    # the total without those counters would present a partial figure as
    # the authoritative one. They travel with the payload and
    # `incomplete` makes the renderers say so.
    c = res["counters"]
    return {
        "available": True,
        "root": str(root),
        "by": by,
        "note": note,
        "pricing_source": res["pricing_source"],
        "files": res["files"],
        "totals": res["grand_total"],
        "by_role": res["by_role"],
        "by_dimension": res["by_dimension"],
        "unresolved_models": res["unresolved_models"],
        "routing": res["routing"],
        "scan": {
            "files_scanned": c.files_scanned,
            "lines_seen": c.lines_seen,
            "candidate_lines": c.candidate_lines,
            "corrupted_lines": c.corrupted_lines,
            "missing_timestamp": c.missing_timestamp,
            "unreadable_files": c.unreadable_files,
            "missing_usage_keys": c.missing_usage_keys,
            "assistant_without_usage": c.assistant_without_usage,
            "sidechain_in_toplevel_skipped": (
                c.sidechain_in_toplevel_skipped
            ),
            "dropped_duplicates": res["dropped_duplicates"],
        },
        "incomplete": bool(
            c.corrupted_lines
            or c.missing_timestamp
            or c.unreadable_files
            # Rail r2 P1-2: an assistant record whose `usage` object
            # carries NEITHER core token key is schema drift, not
            # contract - it is a dropped turn. Measured 0 on the live
            # corpus (80,811 candidate lines), so this fires only when
            # the harness schema actually moves.
            or c.missing_usage_keys
            or c.assistant_without_usage
        ),
    }


def render_block(collected: Optional[Dict[str, Any]]) -> List[str]:
    """Render the PRIMARY-source block as lines (no trailing blank)."""
    out: List[str] = [TRANSCRIPTS_BANNER]
    if not collected or not collected.get("available"):
        reason = (collected or {}).get("reason") or "unavailable"
        out.append("transcripts source UNAVAILABLE: %s" % reason)
        return out
    out.append("root: %s" % collected["root"])
    out.append("pricing: %s" % collected["pricing_source"])
    out.append(
        "files: %d assento + %d subagent"
        % (collected["files"]["assento"], collected["files"]["subagent"])
    )
    if collected.get("incomplete"):
        s = collected.get("scan") or {}
        out.append(
            "WARNING: INCOMPLETE SCAN - this total is a LOWER BOUND: "
            "%d corrupted line(s), %d line(s) without a timestamp, "
            "%d unreadable file(s), %d usage record(s) missing both core "
            "token keys and %d assistant line(s) with no usage object "
            "were skipped."
            % (
                s.get("corrupted_lines", 0),
                s.get("missing_timestamp", 0),
                s.get("unreadable_files", 0),
                s.get("missing_usage_keys", 0),
                s.get("assistant_without_usage", 0),
            )
        )
    if collected.get("note"):
        out.append(collected["note"])
    unresolved = collected.get("unresolved_models") or {}
    if unresolved:
        out.append(
            "warning: %d model id(s) absent from the pricing table, "
            "priced as $0 and never guessed: %s"
            % (len(unresolved), ", ".join(sorted(unresolved.keys())))
        )
    out.append("")
    head = "%-12s %8s %13s %13s %13s %13s %11s" % (
        "role", "turns", "input", "cache_w", "cache_r", "output", "cost",
    )
    out.append(head)
    for role in ("assento", "subagent"):
        d = collected["by_role"].get(role) or _bucket_totals()
        out.append(
            "%-12s %8s %13s %13s %13s %13s %11s"
            % (
                role,
                _fmt_int(d["turns"]),
                _fmt_int(d["input_tokens"]),
                _fmt_int(d["cache_write_5m"] + d["cache_write_1h"]),
                _fmt_int(d["cache_read_tokens"]),
                _fmt_int(d["output_tokens"]),
                _fmt_usd(d["usd"]),
            )
        )
    g = collected["totals"]
    out.append("")
    out.append(
        "%-40s %8s %11s %8s" % (collected["by"], "turns", "cost", "share%")
    )
    rows = sorted(
        collected["by_dimension"].items(),
        key=lambda kv: kv[1]["usd"],
        reverse=True,
    )
    denom = g["usd"] or 1.0
    for k, d in rows[:20]:
        out.append(
            "%-40s %8s %11s %7.1f%%"
            % (
                str(k)[:40],
                _fmt_int(d["turns"]),
                _fmt_usd(d["usd"]),
                100.0 * d["usd"] / denom,
            )
        )
    if len(rows) > 20:
        out.append("... (+%d rows omitted)" % (len(rows) - 20))
    out.append("")
    out.append(
        "TRANSCRIPTS TOTAL: %s turns, %s in, %s out, %s cache-read, "
        "%s cache-write, %s"
        % (
            _fmt_int(g["turns"]),
            _fmt_int(g["input_tokens"]),
            _fmt_int(g["output_tokens"]),
            _fmt_int(g["cache_read_tokens"]),
            _fmt_int(g["cache_write_5m"] + g["cache_write_1h"]),
            _fmt_usd(g["usd"]),
        )
    )
    out.extend(_routing_lines(collected.get("routing")))
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

