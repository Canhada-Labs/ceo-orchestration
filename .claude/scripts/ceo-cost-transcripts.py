#!/usr/bin/env python3
"""ceo-cost-transcripts.py — cost/token report derived from harness-native
transcripts (``message.usage`` per assistant turn), NOT the audit log.

## Why this exists (PLAN-186 W0, S339)

``ceo-cost.py`` and ``budget-summary.py``'s audit-log rollup report
``$0.00`` over 30 days because the audit log is a *governance* log (spawns,
vetoes, edits, ceremonies) — it is not a token ledger. The real spend lives
in the harness-native transcripts under
``~/.claude/projects/<slug>/*.jsonl`` (the main/"assento" sessions) and
``~/.claude/projects/<slug>/<session>/subagents/**/agent-*.jsonl`` (spawned
sub-agents, both plain Task-tool and Workflow rails). Each ``type ==
"assistant"`` record carries a full ``message.usage`` snapshot: fresh
input, output, and prompt-cache read/write (split 5-minute / 1-hour TTL).

This is documented in ``docs/research/s339-orchestrator-study/
05-finops-routing.md`` (P0-1, §1, §Metodologia) — that report's own
scratchpad-local aggregator produced **$11,137.97** over 2026-08-03 →
2026-09-02. This script is the in-tree, tested, stdlib-only version of
that instrument.

``budget-summary.py`` already reads *some* native transcripts
(``_read_native_spawn`` / ``collect_native_spawns``, lines 920-1200) but
only under ``<session>/subagents/**`` — it never reads the top-level
``<session>.jsonl`` files, so it is structurally blind to the "assento"
(main session) spend, which the S339 report measured at 71% of the total.
This script reads BOTH trees and separates them.

## Pricing contract

Default pricing is an EMBEDDED table (``_EMBEDDED_PRICING`` below),
sourced from the S339 report §1.2/§1.4, itself derived from
``docs/provider-pricing.md`` (primary table + cache-tier multipliers,
lines ~130-153) and ``budget-summary.py``'s
``_CACHE_READ_MULTIPLIER_OVERRIDES`` (Fable 5.1 cache-read at 0.025x
base, all other models at 0.10x; cache WRITE is 1.25x base at the
5-minute TTL and 2.00x base at the 1-hour TTL — these multipliers are a
structural constant, not something ``cost-table.yaml`` carries).

``--pricing PATH`` (default ``cost-table.yaml`` next to this script)
attempts to load base ``input_per_mtok`` / ``output_per_mtok`` rows from
that file's mini-YAML ``models:`` block. Two cases:

- **Format doesn't match at all** (file missing, unreadable, no
  ``models:`` section found, zero rows extracted): fall back to the
  fully embedded table wholesale. ``cost-table.yaml`` in this repo has
  NO cache-read/cache-write columns at all — this instrument's whole
  point is cache-aware pricing, so a table that cannot express that is,
  by construction, a format mismatch for this use case; the embedded
  table is the one that can.
- **Format parses AND the path is the untouched default**: rows load
  from the file, then the Owner-ratified corrections in
  ``_RATIFIED_OVERRIDES_FOR_DEFAULT_TABLE`` are layered on top — but
  ONLY where the parsed row actually DIFFERS from the ratified rate.
  As of ``b6dce78`` the in-tree ``cost-table.yaml`` already carries the
  ratified ``claude-sonnet-5`` $2/$10 row, so on the default path the
  correction is currently a NO-OP and ``source`` says so. An
  unconditional overwrite would be worse than useless: it would print
  "ratified correction" while correcting nothing, and the day the
  table is legitimately refreshed it would silently mask the new rate.
  An EXPLICIT ``--pricing`` path supplied by the caller is trusted
  as-is, with no correction at all — the caller opted into a specific
  pricing config on purpose.

Cache-read/write multipliers are ALWAYS the structural constants above,
regardless of which base table is in play, applied per-model (Fable 5.1
override on cache read only).

## Corpus contract

- Dedup key: ``message.id`` when present (an API response's usage
  snapshot is identical across every content-block JSONL line the
  harness writes for that one message — thinking/text/tool_use blocks
  each get their own line, all carrying the SAME ``message.usage``);
  falls back to ``requestId`` + record ``uuid`` when ``message.id`` is
  absent. The S339 report's methodology names a
  ``(requestId, apiBlockIndex, message.id)`` key; ``apiBlockIndex`` was
  not observed in this harness version's on-disk schema, so the key
  degrades to what IS observed without inventing a field.
- Role: "assento" for non-sidechain assistant turns in a top-level
  ``<session>.jsonl``; "subagent" for every assistant turn under
  ``<session>/subagents/**/agent-*.jsonl`` regardless of its own
  ``isSidechain`` value (path-shape is the classifier, mirroring
  ``budget-summary.py``'s rail-by-path doctrine — the corpus has no
  reliable field for this). A sidechain turn inside a top-level file (not
  observed in this corpus, but not structurally impossible) is skipped
  rather than double-counted: any Task-tool sub-dispatch already has its
  own dedicated ``agent-*.jsonl``.
- Never touches ``iterations`` on a usage record (it double-counts
  retries — same exclusion the S339 report's methodology names).
- A JSON-parse failure on a candidate line is skipped and counted, never
  raised. An ``unresolved`` model id (not found in the active pricing
  table, after stripping a trailing ``[..]`` context-window suffix such
  as ``[1m]``) is bucketed and reported with its token totals — never
  silently priced at $0 as if it were a genuine zero-cost turn, and never
  guessed.

Stdlib-only, Python >= 3.9. Read-only: this script writes nothing.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# _lib.runtime_paths (read-only import — this script never edits it or
# budget-summary.py; it only consumes the single resolver per CLAUDE.md §4
# "No file in the audit/state family may re-derive the directory locally").
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent  # .claude/scripts -> .claude -> repo root
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _lib import runtime_paths as _rp  # noqa: E402
except Exception:  # pragma: no cover - resolver import must never crash the CLI
    _rp = None


# ---------------------------------------------------------------------------
# Pricing tables
# ---------------------------------------------------------------------------

#: Embedded fallback / correction source. Report 05-finops-routing.md §1.2 +
#: §1.4 (S339, measured 2026-08-03..2026-09-02). Sonnet 5 at the
#: Owner-ratified 2026-09-01 intro rate (CLAUDE.md commit e47bf5d).
_EMBEDDED_PRICING: Dict[str, Dict[str, float]] = {
    "claude-fable-5-1": {"input_per_mtok": 10.00, "output_per_mtok": 50.00},
    "claude-fable-5": {"input_per_mtok": 10.00, "output_per_mtok": 50.00},
    "claude-opus-5": {"input_per_mtok": 5.00, "output_per_mtok": 25.00},
    "claude-opus-4-8": {"input_per_mtok": 5.00, "output_per_mtok": 25.00},
    "claude-sonnet-5": {"input_per_mtok": 2.00, "output_per_mtok": 10.00},
    "claude-sonnet-4-6": {"input_per_mtok": 3.00, "output_per_mtok": 15.00},
    "claude-haiku-4-5": {"input_per_mtok": 1.00, "output_per_mtok": 5.00},
}

#: Applied ONLY on top of a successfully-parsed DEFAULT --pricing path
#: (never on an explicit caller-supplied path), and ONLY where the
#: parsed row differs from the value below. An entry that matches the
#: file is reported as a no-op, never as a correction. See module
#: docstring.
_RATIFIED_OVERRIDES_FOR_DEFAULT_TABLE: Dict[str, Dict[str, float]] = {
    "claude-sonnet-5": {"input_per_mtok": 2.00, "output_per_mtok": 10.00},
}

#: docs/provider-pricing.md lines ~130-153 ("Cache-tier multipliers"):
#: fresh input 1.00x, cache write 5m 1.25x, cache write 1h 2.00x, cache
#: read 0.10x (base input rate) — EXCEPT Fable 5.1 / Mythos 5.1 at 0.025x
#: (pricing page 2026-09-01, ADR-149 Amendment 2). Mirrors
#: budget-summary.py's _CACHE_READ_MULTIPLIER_OVERRIDES exactly.
_CACHE_READ_MULTIPLIER_DEFAULT: float = 0.10
_CACHE_READ_MULTIPLIER_OVERRIDES: Dict[str, float] = {
    "claude-fable-5-1": 0.025,
}
_CACHE_WRITE_5M_MULTIPLIER: float = 1.25
_CACHE_WRITE_1H_MULTIPLIER: float = 2.00

_MODEL_SUFFIX_RE = re.compile(r"\[[^\[\]]*\]$")


def _cache_read_multiplier(model_id: str) -> float:
    return _CACHE_READ_MULTIPLIER_OVERRIDES.get(model_id, _CACHE_READ_MULTIPLIER_DEFAULT)


def normalize_model_id(raw: Optional[str]) -> Optional[str]:
    """Strip a trailing context-window suffix (e.g. ``[1m]``). No guessing."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    return _MODEL_SUFFIX_RE.sub("", raw.strip())


def _parse_cost_table_yaml(text: str) -> Dict[str, Dict[str, float]]:
    """Minimal parser for the ``models:`` block of cost-table.yaml's mini-YAML
    subset (top-level scalars + one level of 2-space-indented nested dicts —
    see that file's own header comment). Extracts ONLY the two numeric
    fields this instrument needs; anything else (``tier``, ``source_url``,
    ...) is ignored. Never raises — a malformed file just yields {}.
    """
    models: Dict[str, Dict[str, float]] = {}
    in_models = False
    current: Optional[str] = None
    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        stripped = raw_line.strip()
        if stripped.startswith("#"):
            continue
        if not raw_line.startswith(" ") and not raw_line.startswith("\t"):
            in_models = raw_line.rstrip() == "models:"
            current = None
            continue
        if not in_models:
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent == 2 and stripped.endswith(":"):
            current = stripped[:-1].strip()
            models.setdefault(current, {})
            continue
        if indent >= 4 and current is not None:
            field_txt = stripped
            if "#" in field_txt:
                field_txt = field_txt.split("#", 1)[0].rstrip()
            if ":" not in field_txt:
                continue
            key, _, val = field_txt.partition(":")
            key = key.strip()
            val = val.strip()
            if key in ("input_per_mtok", "output_per_mtok"):
                try:
                    models[current][key] = float(val)
                except ValueError:
                    continue
    return models


@dataclass
class PricingResult:
    table: Dict[str, Dict[str, float]]
    source: str  # human-readable description for --help / report footer
    used_fallback: bool


def _override_is_a_no_op(
    current: Optional[Dict[str, float]], override: Dict[str, float]
) -> bool:
    """True when the parsed row ALREADY carries every ratified value.

    Guards the one thing an unconditional overwrite cannot express: the
    difference between a stale file that WAS corrected and a file that
    was already right. Missing row / wrong type => not a no-op, so the
    override still lands.
    """
    if not isinstance(current, dict):
        return False
    for key, value in override.items():
        have = current.get(key)
        if isinstance(have, bool) or not isinstance(have, (int, float)):
            return False
        if abs(float(have) - float(value)) > 1e-9:
            return False
    return True


def load_pricing(pricing_arg: Optional[str]) -> PricingResult:
    """Resolve the active {model_id: {input_per_mtok, output_per_mtok}}
    table per the contract in the module docstring."""
    is_default_path = pricing_arg is None
    path = Path(pricing_arg) if pricing_arg else (_SCRIPT_DIR / "cost-table.yaml")

    text: Optional[str] = None
    if path.is_file():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            text = None

    parsed: Dict[str, Dict[str, float]] = _parse_cost_table_yaml(text) if text else {}
    complete_rows = {
        mid: row
        for mid, row in parsed.items()
        if "input_per_mtok" in row and "output_per_mtok" in row
    }

    if not complete_rows:
        return PricingResult(
            table=dict(_EMBEDDED_PRICING),
            source=(
                "embedded (report 05-finops-routing.md \xa71.4; %s could not "
                "be parsed / had no complete models: rows)" % path
            ),
            used_fallback=True,
        )

    table = dict(complete_rows)
    source = "parsed from %s" % path
    if is_default_path:
        # Conditional by construction: an override that merely restates
        # what the file already says is NOT a correction. Reporting it as
        # one prints a fix that fixed nothing, and applying it anyway
        # would silently mask a legitimate refresh of the table.
        applied: List[str] = []
        noop: List[str] = []
        for mid in sorted(_RATIFIED_OVERRIDES_FOR_DEFAULT_TABLE):
            override = _RATIFIED_OVERRIDES_FOR_DEFAULT_TABLE[mid]
            if _override_is_a_no_op(table.get(mid), override):
                noop.append(mid)
                continue
            table[mid] = dict(override)
            applied.append(
                "%s -> $%g/$%g"
                % (
                    mid,
                    override["input_per_mtok"],
                    override["output_per_mtok"],
                )
            )
        if applied:
            source += (
                " + ratified correction (%s; 2026-09-01, CLAUDE.md "
                "e47bf5d)" % ", ".join(applied)
            )
        if noop:
            source += (
                " + ratified correction NOT needed for %s (the file "
                "already carries the ratified rate)" % ", ".join(noop)
            )
    return PricingResult(table=table, source=source, used_fallback=False)


# ---------------------------------------------------------------------------
# Transcript discovery + parsing
# ---------------------------------------------------------------------------


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


def _extract_record(
    obj: Dict[str, Any], role: str, fallback_session_id: str, counters: ScanCounters
) -> Optional[UsageRecord]:
    if obj.get("type") != "assistant":
        return None
    msg = obj.get("message")
    if not isinstance(msg, dict):
        return None
    usage = msg.get("usage")
    if not isinstance(usage, dict):
        return None
    if ("input_tokens" not in usage) and ("output_tokens" not in usage):
        counters.missing_usage_keys += 1
        return None
    if role == "assento" and obj.get("isSidechain") is True:
        counters.sidechain_in_toplevel_skipped += 1
        return None

    ts = _parse_ts(obj.get("timestamp"))
    if ts is None:
        counters.missing_timestamp += 1
        return None

    model_raw = msg.get("model")
    model_norm = normalize_model_id(model_raw) or "(unresolved:%r)" % (model_raw,)

    session_id = obj.get("sessionId")
    if not isinstance(session_id, str) or not session_id:
        session_id = fallback_session_id

    effort = obj.get("effort")
    effort_val = effort if isinstance(effort, str) and effort else None

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
    )


def scan_files(
    files: List[Path], role: str, project_dir: Path, counters: ScanCounters
) -> List[UsageRecord]:
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
                    if b'"usage"' not in raw:
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
                    rec = _extract_record(obj, role, fallback_session_id, counters)
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
    most-complete/terminal snapshot); the merged timestamp is the
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
        terminal = max(group, key=lambda r: r.output_tokens)
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


_GROUP_KEYS = {
    "model": lambda p: p.rec.model,
    "role": lambda p: p.rec.role,
    "session": lambda p: p.rec.session_id,
    "day": lambda p: p.rec.ts.strftime("%Y-%m-%d"),
}

_TOKEN_CLASSES = (
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_5m",
    "cache_write_1h",
)


def _bucket_totals() -> Dict[str, float]:
    return {
        "turns": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_5m": 0,
        "cache_write_1h": 0,
        "usd": 0.0,
    }


def aggregate(priced: List[Priced], by: str) -> Tuple[Dict[str, float], Dict[str, Dict[str, float]], Dict[str, Dict[str, float]]]:
    """Returns (grand_total, role_totals, by-dimension totals)."""
    grand = _bucket_totals()
    role_totals: Dict[str, Dict[str, float]] = {}
    group_totals: Dict[str, Dict[str, float]] = {}
    key_fn = _GROUP_KEYS[by]

    for p in priced:
        for d in (grand, role_totals.setdefault(p.rec.role, _bucket_totals()), group_totals.setdefault(key_fn(p), _bucket_totals())):
            d["turns"] += 1
            for cls in _TOKEN_CLASSES:
                d[cls] += getattr(p.rec, cls)
            d["usd"] += p.cost_usd

    return grand, role_totals, group_totals


# ---------------------------------------------------------------------------
# Programmatic API (PLAN-186 W0, AC-1b)
# ---------------------------------------------------------------------------
#
# `ceo-cost.py` and `budget-summary.py` consume THIS surface, never the
# CLI's stdout. Everything below the `transcript_rollup` line exists so
# the two callers share one root resolver, one collector and one
# renderer — a second grafia of any of them is the exact shape of the
# D1-D4 defect class (CLAUDE.md §5).

#: Env override for the transcripts corpus root. Flag > env > the shared
#: `_lib.runtime_paths` resolver. Tests MUST set this (or pass the flag):
#: nothing here may read the real ~/.claude/projects/<slug> corpus.
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
) -> Dict[str, Any]:
    """Scan + dedup + price `project_dir`, returning the rollup as data.

    `cutoff` is an aware datetime; records strictly older are dropped.
    `None` means the whole corpus. This is the single pipeline the CLI
    itself runs, so the API and the printed report can never disagree.
    """
    if by not in _GROUP_KEYS:
        raise ValueError("unknown breakdown dimension: %r" % (by,))
    project_dir = Path(project_dir)
    pricing_result = load_pricing(pricing_arg)

    top_files, sub_files = discover_files(project_dir)
    counters = ScanCounters()
    records = scan_files(top_files, "assento", project_dir, counters)
    records += scan_files(sub_files, "subagent", project_dir, counters)

    if cutoff is not None:
        records = [r for r in records if r.ts >= cutoff]

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
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

_SINCE_RE = re.compile(r"^(\d+)([dh])$")


def _parse_since(expr: str) -> timedelta:
    m = _SINCE_RE.match(expr.strip())
    if not m:
        raise argparse.ArgumentTypeError(
            "invalid --since %r; expected <N>d or <N>h (documented: 30d, 7d, 24h)" % expr
        )
    n = int(m.group(1))
    return timedelta(days=n) if m.group(2) == "d" else timedelta(hours=n)


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
            "(0.025x for claude-fable-5-1). Cache-write multiplier: 1.25x "
            "base at the 5-minute TTL, 2.00x at the 1-hour TTL."
        ),
    )
    p.add_argument(
        "--since",
        default="30d",
        type=str,
        help="window ending now: <N>d or <N>h (default 30d; 7d and 24h also documented)",
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
        choices=sorted(_GROUP_KEYS.keys()),
        default="model",
        help="breakdown dimension for the report table (default: model)",
    )
    p.add_argument(
        "--pricing",
        default=None,
        metavar="YAML",
        help="cost-table.yaml-shaped file; default: cost-table.yaml next to this script (see epilog)",
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
) -> str:
    lines: List[str] = []
    lines.append("ceo-cost-transcripts — janela: %s" % args.since_raw)
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
) -> str:
    payload = {
        "since": args.since_raw,
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

    # ONE pipeline for the CLI and for the programmatic callers
    # (PLAN-186 W0, AC-1b): a second copy here is how the printed report
    # and ceo-cost.py's block would silently disagree.
    rolled = transcript_rollup(
        project_dir,
        cutoff=datetime.now(timezone.utc) - args.since,
        pricing_arg=args.pricing,
        by=args.by,
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

    elapsed_s = time.time() - t0

    if args.json:
        out = _json_report(
            args, project_dir, pricing_result, counters, grand, role_totals, group_totals, unresolved_by_model, elapsed_s
        )
    else:
        out = _human_report(
            args, project_dir, pricing_result, counters, grand, role_totals, group_totals, unresolved_by_model, elapsed_s
        )
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
