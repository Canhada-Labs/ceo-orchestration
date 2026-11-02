"""Extracted cost-transcripts implementation: records."""
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

def discover_files(project_dir: Path) -> Tuple[List[Path], List[Path]]:
    """Returns (top_level_session_files, subagent_transcript_files)."""
    top = sorted(Path(p) for p in glob.glob(str(project_dir / "*.jsonl")))
    sub = sorted(
        Path(p)
        for p in glob.glob(
            str(project_dir / "*" / "subagents" / "**" / "agent-*.jsonl"),
            recursive=True,
        )
    )
    return top, sub


def _parse_ts(raw: Any) -> Optional[datetime]:
    if not isinstance(raw, str) or not raw:
        return None
    s = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _as_int(v: Any) -> int:
    return int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0


@dataclass
class UsageRecord:
    key: str
    ts: datetime
    model: str  # normalized id, or "(unresolved:<raw>)" when unmatched later
    effort: Optional[str]
    session_id: str
    role: str  # "assento" | "subagent"
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_5m: int = 0
    cache_write_1h: int = 0
    #: False when the line carried no usable ``output_tokens`` (a
    #: ``usage_optional`` read of a turn whose ``usage`` is null, absent or
    #: partial). ``dedup()`` elects the terminal chunk by ``output_tokens``,
    #: so a record without them cannot be ranked: the routing reader must
    #: not pretend it was.
    has_usage: bool = True


@dataclass
class ScanCounters:
    files_scanned: int = 0
    lines_seen: int = 0
    candidate_lines: int = 0
    corrupted_lines: int = 0
    missing_timestamp: int = 0
    missing_usage_keys: int = 0
    assistant_without_usage: int = 0
    sidechain_in_toplevel_skipped: int = 0
    unreadable_files: int = 0
    deduped_records: int = 0
    #: ``usage_optional`` reads only (the routing reader): one entry per
    #: assistant record with no ``message`` object -- nothing, not even a
    #: model id, can be read from it. Each entry is the record's own
    #: timestamp (``None`` when it has no valid one), so the caller can keep
    #: a record that is PROVABLY outside the window out of the verdict.
    unreadable_assistant_ts: List[Optional[datetime]] = field(default_factory=list)


def _extract_record(
    obj: Dict[str, Any],
    role: str,
    fallback_session_id: str,
    counters: ScanCounters,
    usage_optional: bool = False,
) -> Optional[UsageRecord]:
    """One assistant line -> ``UsageRecord`` (or ``None``).

    ``usage_optional`` is the ROUTING reader's switch (PLAN-186 AC-13): the
    served model is a fact of the turn, not of its token bill, so a turn
    whose ``usage`` is ``null``, absent or empty is still READ (zero
    tokens) instead of vanishing. The cost reader keeps the default
    ``False`` and is unchanged: it drops such a turn exactly as before.
    """
    if obj.get("type") != "assistant":
        return None
    msg = obj.get("message")
    if not isinstance(msg, dict):
        if usage_optional:
            counters.unreadable_assistant_ts.append(_parse_ts(obj.get("timestamp")))
        return None
    usage = msg.get("usage")
    if not isinstance(usage, dict):
        if not usage_optional:
            return None
        usage = {}
    elif ("input_tokens" not in usage) and ("output_tokens" not in usage):
        if not usage_optional:
            counters.missing_usage_keys += 1
            return None
    out_tokens = usage.get("output_tokens")
    has_usage = isinstance(out_tokens, int) and not isinstance(out_tokens, bool)
    if role == "assento" and obj.get("isSidechain") is True:
        counters.sidechain_in_toplevel_skipped += 1
        return None

    ts = _parse_ts(obj.get("timestamp"))
    if ts is None:
        counters.missing_timestamp += 1
        return None

    # Every string below is DATA written by the harness (or by whoever can
    # write the transcript) and is later PRINTED by four renderers: it is
    # made printable HERE, once, at the door (``_safe_text``).
    model_raw = msg.get("model")
    model_norm = _safe_text(
        normalize_model_id(model_raw) or "(unresolved:%r)" % (model_raw,), 120
    )

    session_id = obj.get("sessionId")
    if not isinstance(session_id, str) or not session_id:
        session_id = fallback_session_id
    session_id = _safe_text(session_id, 200)

    effort = obj.get("effort")
    effort_val = _safe_text(effort, 40) if isinstance(effort, str) and effort else None

    msg_id = msg.get("id")
    if isinstance(msg_id, str) and msg_id:
        key = "mid:" + msg_id
    else:
        key = "req:%s:uuid:%s" % (obj.get("requestId"), obj.get("uuid"))

    input_tokens = _as_int(usage.get("input_tokens"))
    output_tokens = _as_int(usage.get("output_tokens"))
    cache_read = _as_int(usage.get("cache_read_input_tokens"))
    c_total = _as_int(usage.get("cache_creation_input_tokens"))

    c_5m = c_1h = 0
    cc = usage.get("cache_creation")
    if isinstance(cc, dict):
        c_5m = _as_int(cc.get("ephemeral_5m_input_tokens"))
        c_1h = _as_int(cc.get("ephemeral_1h_input_tokens"))
    # Clamp + "unattributed write assumed 5m" — mirrors
    # budget-summary.py's _read_native_spawn cache-split reconciliation.
    c_1h = min(c_1h, c_total)
    c_5m = min(c_5m, c_total - c_1h)
    c_rest = c_total - c_1h - c_5m
    c_5m += c_rest

    return UsageRecord(
        key=key,
        ts=ts,
        model=model_norm,
        effort=effort_val,
        session_id=session_id,
        role=role,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read,
        cache_write_5m=c_5m,
        cache_write_1h=c_1h,
        has_usage=has_usage,
    )


def scan_files(
    files: List[Path],
    role: str,
    project_dir: Path,
    counters: ScanCounters,
    usage_optional: bool = False,
) -> List[UsageRecord]:
    """Read assistant turns from `files`. ``usage_optional`` is the routing
    reader's switch (see ``_extract_record``): turns without a usable
    ``usage`` are read, not dropped; the default leaves the cost reader as
    it always was."""
    out: List[UsageRecord] = []
    for path in files:
        counters.files_scanned += 1
        if role == "assento":
            fallback_session_id = path.stem
        else:
            try:
                fallback_session_id = path.relative_to(project_dir).parts[0]
            except ValueError:
                fallback_session_id = path.parent.name
        try:
            with path.open("rb") as f:
                for raw in f:
                    counters.lines_seen += 1
                    # Fast pre-filter: every real assistant/usage line
                    # carries both substrings; anything without them is
                    # skipped WITHOUT paying a json.loads (tool results
                    # and user turns dominate the corpus by line count —
                    # measured 330427/409255 skipped this way on the
                    # live corpus, 640MB scanned in ~2.8s).
                    if b'"assistant"' not in raw:
                        continue
                    if b'"usage"' not in raw and not usage_optional:
                        # Rail r3 P1-2: an assistant-shaped line with no
                        # usage substring is either a renamed/removed
                        # field or a torn write - a DROPPED turn, not a
                        # user record. Counted so completeness detection
                        # can see it. (A tear that also loses the
                        # `"assistant"` substring is indistinguishable
                        # from a user turn by construction - that is the
                        # price of the prefilter, and it is declared.)
                        counters.assistant_without_usage += 1
                        continue
                    counters.candidate_lines += 1
                    try:
                        obj = json.loads(raw)
                    except ValueError:
                        counters.corrupted_lines += 1
                        continue
                    if not isinstance(obj, dict):
                        counters.corrupted_lines += 1
                        continue
                    rec = _extract_record(
                        obj, role, fallback_session_id, counters, usage_optional
                    )
                    if rec is not None:
                        out.append(rec)
        except OSError:
            counters.unreadable_files += 1
            continue
    return out


def dedup(records: List[UsageRecord]) -> Tuple[List[UsageRecord], int]:
    """Collapse every record sharing a dedup key into ONE merged record.

    A message.id's usage snapshot is NOT always a static repeat across
    its content-block JSONL lines. Measured on the live subagent corpus
    (PLAN-186 W0 follow-up, cross-model review): 14,054 of 21,414
    multi-line message.id groups (65.6%) carry a PROGRESSIVE
    ``output_tokens`` count that grows monotonically in file-append
    order — zero counter-examples found across the whole corpus — while
    ``input_tokens`` stays constant across every one of those groups
    (cache fields vary in only 4/16,070 multi-line groups; model
    metadata in 3/21,414, evidently harness fallback/streaming
    resolution settling on the first chunk). A first-write-wins or
    arbitrary-line-wins dedup keeps whichever INTERIM snapshot happened
    to land first — for the dominant growth pattern that is the
    SMALLEST output_tokens value, silently undercounting output cost
    for the majority of subagent turns.

    The fix: take the per-field MAXIMUM across every line sharing a key.
    This is exact for the dominant monotonic-growth case (the max IS the
    terminal/final snapshot) and is safe for the small residual where a
    non-output field also varies, since a per-field max can never be
    LOWER than any single observed snapshot — the failure mode this
    replaces. Metadata (model, effort, session_id, role) is taken from
    whichever line in the group has the highest ``output_tokens`` (the
    most-complete/terminal snapshot; on a tie, the LATER line in file
    order); the merged timestamp is the
    EARLIEST line in the group (the turn's start, matching what a plain
    first-write-wins dedup would already have reported for ``--by day``
    bucketing).
    """
    groups: Dict[str, List[UsageRecord]] = {}
    order: List[str] = []
    for rec in records:
        bucket = groups.get(rec.key)
        if bucket is None:
            groups[rec.key] = [rec]
            order.append(rec.key)
        else:
            bucket.append(rec)

    out: List[UsageRecord] = []
    dropped = 0
    for key in order:
        group = groups[key]
        dropped += len(group) - 1
        if len(group) == 1:
            out.append(group[0])
            continue
        # TERMINAL chunk = the highest ``output_tokens``; on a TIE the LATER
        # line in file order (the one the harness streamed last). `max`
        # keeps the FIRST maximum it meets, so the group is walked in
        # reverse: without this, equal counts left the earlier chunk's
        # model/effort/session as the group's, and file order silently
        # decided between two verdicts.
        terminal = max(reversed(group), key=lambda r: r.output_tokens)
        out.append(
            UsageRecord(
                key=key,
                ts=min(r.ts for r in group),
                model=terminal.model,
                effort=terminal.effort,
                session_id=terminal.session_id,
                role=terminal.role,
                input_tokens=max(r.input_tokens for r in group),
                output_tokens=max(r.output_tokens for r in group),
                cache_read_tokens=max(r.cache_read_tokens for r in group),
                cache_write_5m=max(r.cache_write_5m for r in group),
                cache_write_1h=max(r.cache_write_1h for r in group),
            )
        )
    return out, dropped


# ---------------------------------------------------------------------------
# Pricing application + aggregation
# ---------------------------------------------------------------------------


@dataclass
class Priced:
    rec: UsageRecord
    cost_usd: float
    resolved: bool


def price_records(
    records: List[UsageRecord], pricing: Dict[str, Dict[str, float]]
) -> List[Priced]:
    out: List[Priced] = []
    for rec in records:
        base = pricing.get(rec.model)
        if base is None:
            out.append(Priced(rec=rec, cost_usd=0.0, resolved=False))
            continue
        inp = base["input_per_mtok"]
        outp = base["output_per_mtok"]
        read_mult = _cache_read_multiplier(rec.model)
        cost = (
            rec.input_tokens * inp
            + rec.output_tokens * outp
            + rec.cache_read_tokens * inp * read_mult
            + rec.cache_write_5m * inp * _CACHE_WRITE_5M_MULTIPLIER
            + rec.cache_write_1h * inp * _CACHE_WRITE_1H_MULTIPLIER
        ) / 1_000_000.0
        out.append(Priced(rec=rec, cost_usd=cost, resolved=True))
    return out


