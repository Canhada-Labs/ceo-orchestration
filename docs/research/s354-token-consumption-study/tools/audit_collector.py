#!/usr/bin/env python3
"""audit_collector.py — independent re-derivation of the token ledger.

Study artifact (S354 study, lane 3: «validar o coletor»). It does NOT import
``.claude/scripts/ceo-cost-transcripts.py`` — an oracle that reuses the
subject's code cannot catch the subject's mistakes. It re-reads the same
harness-native transcripts with its own code and reports where the two
derivations agree and where they diverge. Where the collector makes a
documented choice (record acceptance, cache-write normalisation, per-field
max dedup, model-id suffix stripping) this file states the rule it mirrors,
so a divergence is attributable to ONE named rule.

Findings it produces (each is a named section of the report):

* COVERAGE — walks EVERY ``*.jsonl`` under the project dir, classifies each
  file as ``assento`` (top-level ``<session>.jsonl``), ``subagent``
  (``*/subagents/**/agent-*.jsonl``) or ``fora`` (anything else), and reports
  whether any ``fora`` file carries assistant records with ``message.usage``
  inside the window — spend the collector cannot see.
* DEDUP — groups records by the collector's key (``message.id``, else
  ``requestId``+``uuid``) and measures how often duplicated keys carry
  DIFFERENT usage snapshots; the first/last/max-per-field totals bound the
  error of each rule.
* BIG WRITES — turns whose cache WRITE exceeds ``--big-write`` tokens, split
  by what the neighbouring records say: ``initial`` (first usage record of
  its transcript: the agent's opening prefix), ``rewrite`` (cache read fell
  below 20 % of the previous turn's: the cached prefix was lost — expiry or
  invalidation) or ``growth`` (cache read continued: large NEW content). The
  threshold is a heuristic; the split is what makes it interpretable.
* INITIAL PREFIX — distribution (p50 / p90 / max) of the FIRST turn's total
  input (fresh + cache read + cache write) per subagent transcript: the
  measured opening context of agents in THIS repo, instead of one probe.
* PRICING — recomputes USD per model from the input/output prices copied
  from ``.claude/scripts/cost-table.yaml`` and the DOCUMENTED cache
  multipliers (read 0.10 × input; ``claude-fable-5-1`` 0.025 × input =
  $0.25/MTok per Anthropic's model notes; 5-minute write 1.25 ×; 1-hour
  write 2.0 ×).
* COMPARE — with ``--compare <collector --json output>``: per-model deltas on
  turns, input, output, cache read, both cache writes, and USD (unrounded and
  relative).
* RAW BY LOCATION — with ``--raw-by-location``: NON-deduplicated sums per
  (location class, model) where the classes are ``top`` (``<session>.jsonl``),
  ``sub_direct`` (``<session>/subagents/agent-*.jsonl``) and ``sub_nested``
  (anything deeper, e.g. ``subagents/workflows/<wf>/…``). With
  ``--stats-cache PATH`` (the harness's local ``stats-cache.json``) it prints
  the ratio of each class combination to that file's ``modelUsage`` — the
  test that recovers what the harness's ``/stats`` counts.

Stdlib only, Python >= 3.9. Read-only: never writes under the project dir.
Never prints transcript contents — only counts and totals.

Usage::

    python3 audit_collector.py --project-dir ~/.claude/projects/<slug> \
        --since-at 2026-09-03T00:00:00Z --until 2026-09-17T23:59:59Z \
        [--compare collector.json] [--raw-by-location [--stats-cache ~/.claude/stats-cache.json]] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

# USD per million tokens: (input, output, cache_read_multiplier_of_input).
# input/output copied from .claude/scripts/cost-table.yaml at commit efe4c609
# (2026-09-17). Cache multipliers: documented API defaults; the Fable 5.1
# override is the $0.25/MTok cache read stated in Anthropic's model notes
# (Fable 5 reads at the standard 0.10 — the cheap read arrived with 5.1).
PRICING: Dict[str, Tuple[float, float, float]] = {
    "claude-opus-5": (5.0, 25.0, 0.10),
    "claude-opus-4-8": (5.0, 25.0, 0.10),
    "claude-sonnet-5": (2.0, 10.0, 0.10),
    "claude-sonnet-4-6": (3.0, 15.0, 0.10),
    "claude-fable-5-1": (10.0, 50.0, 0.025),
    "claude-fable-5": (10.0, 50.0, 0.10),
    "claude-haiku-4-5": (1.0, 5.0, 0.10),
    "claude-haiku-4-5-20251001": (1.0, 5.0, 0.10),
}
WRITE_5M_MULT = 1.25
WRITE_1H_MULT = 2.0
REWRITE_READ_RATIO = 0.20  # cache_read below this fraction of the previous turn's = prefix lost

_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_MODEL_SUFFIX_RE = re.compile(r"\[[^\[\]]*\]$")  # mirrors the collector: strip a trailing "[1m]"

Usage = Tuple[int, int, int, int, int]  # input, output, cache_read, write_5m, write_1h
FIELDS = ("input", "output", "cache_read", "write_5m", "write_1h")


def _as_int(v: object) -> int:
    try:
        return int(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _parse_ts(s: object) -> Optional[datetime]:
    if not isinstance(s, str) or not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_bound(s: Optional[str]) -> Optional[datetime]:
    if s is None:
        return None
    dt = _parse_ts(s)
    if dt is None:
        raise SystemExit("bad ISO-8601 bound: %r" % (s,))
    return dt


def normalize_model(raw: object) -> str:
    if not isinstance(raw, str) or not raw.strip():
        return "(unresolved:%r)" % (raw,)
    return _MODEL_SUFFIX_RE.sub("", raw.strip())


def classify(path: Path, root: Path) -> Tuple[str, str, str]:
    """Returns (role, label, location) — location in {top, sub_direct, sub_nested, fora}."""
    rel = path.relative_to(root).parts
    if len(rel) == 1:
        return "assento", "<session>.jsonl", "top"
    if "subagents" in rel and path.name.startswith("agent-"):
        loc = "sub_direct" if (len(rel) == 3 and rel[1] == "subagents") else "sub_nested"
        return "subagent", "*/subagents/**/agent-*.jsonl", loc
    masked = "/".join(_UUID_RE.sub("<uuid>", p) for p in rel[1:])
    return "fora", masked, "fora"


def iter_lines(path: Path) -> Iterator[dict]:
    with open(path, "rb") as fh:
        for raw in fh:
            if b'"usage"' not in raw or b'"assistant"' not in raw:
                continue
            try:
                obj = json.loads(raw)
            except ValueError:
                continue
            if isinstance(obj, dict) and obj.get("type") == "assistant":
                yield obj


def accept(obj: dict, role: str, counters: Dict[str, int]) -> Optional[Tuple[dict, dict]]:
    """Mirrors the collector's record acceptance. Returns (message, usage) or None."""
    msg = obj.get("message")
    if not isinstance(msg, dict):
        return None
    usage = msg.get("usage")
    if not isinstance(usage, dict):
        return None
    if ("input_tokens" not in usage) and ("output_tokens" not in usage):
        counters["skipped_missing_usage_keys"] += 1
        return None
    if role == "assento" and obj.get("isSidechain") is True:
        counters["skipped_sidechain_in_top"] += 1
        return None
    return msg, usage


def usage_tuple(usage: dict) -> Usage:
    """Mirrors the collector's cache-write normalisation: the split never exceeds the total."""
    c_total = _as_int(usage.get("cache_creation_input_tokens"))
    c_5m = c_1h = 0
    cc = usage.get("cache_creation")
    if isinstance(cc, dict):
        c_5m = _as_int(cc.get("ephemeral_5m_input_tokens"))
        c_1h = _as_int(cc.get("ephemeral_1h_input_tokens"))
    c_1h = min(c_1h, c_total)
    c_5m = min(c_5m, c_total - c_1h)
    c_5m += c_total - c_1h - c_5m
    return (
        _as_int(usage.get("input_tokens")),
        _as_int(usage.get("output_tokens")),
        _as_int(usage.get("cache_read_input_tokens")),
        c_5m,
        c_1h,
    )


def usd_for(model: str, u: Usage) -> Optional[float]:
    p = PRICING.get(model)
    if p is None:
        return None
    inp, out, read_mult = p
    return (
        u[0] * inp
        + u[1] * out
        + u[2] * inp * read_mult
        + u[3] * inp * WRITE_5M_MULT
        + u[4] * inp * WRITE_1H_MULT
    ) / 1_000_000.0


class Group:
    __slots__ = ("first", "last", "max_out", "n", "differs", "model", "role", "first_in_file", "prev_cr", "terminal")

    def __init__(self, u: Usage, model: str, role: str, first_in_file: bool, prev_cr: int) -> None:
        self.first = u
        self.last = u
        self.max_out = u
        self.terminal = u
        self.n = 1
        self.differs = False
        self.model = model
        self.role = role
        self.first_in_file = first_in_file
        self.prev_cr = prev_cr

    def add(self, u: Usage, model: str) -> None:
        self.n += 1
        self.last = u
        if u[1] > self.terminal[1]:
            self.terminal = u
            self.model = model  # collector: metadata from the max-output line
        # per-field max (the collector's merge rule)
        self.max_out = tuple(max(a, b) for a, b in zip(self.max_out, u))  # type: ignore[assignment]
        if u != self.first:
            self.differs = True


def add_usage(acc: Dict[str, int], u: Usage) -> None:
    for k, v in zip(FIELDS, u):
        acc[k] += v


def percentile(sorted_vals: List[int], p: float) -> int:
    if not sorted_vals:
        return 0
    idx = min(len(sorted_vals) - 1, int(round(p * (len(sorted_vals) - 1))))
    return sorted_vals[idx]


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--project-dir", required=True, nargs="+", help="one or more harness project dirs (~/.claude/projects/<slug>); several dirs are aggregated, which is how a machine-wide stats-cache comparison is reproduced")
    ap.add_argument("--since-at", default=None, help="ISO-8601 lower bound, inclusive (UTC if naive); filters each LINE before grouping, like the collector")
    ap.add_argument("--until", default=None, help="ISO-8601 upper bound, inclusive (UTC if naive)")
    ap.add_argument("--compare", default=None, help="path to the collector's --json output for the same window")
    ap.add_argument("--big-write", type=int, default=100_000, help="cache write (tokens) above which a turn is a BIG WRITE (default 100000)")
    ap.add_argument("--raw-by-location", action="store_true", help="also compute NON-deduplicated sums per location class × model")
    ap.add_argument("--stats-cache", default=None, help="harness stats-cache.json to compare the raw-by-location sums against (modelUsage)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    roots: List[Path] = []
    for p in args.project_dir:
        root = Path(os.path.expanduser(p)).resolve()
        if not root.is_dir():
            print("project dir not found: %s" % root, file=sys.stderr)
            return 2
        roots.append(root)
    lo = _parse_bound(args.since_at)
    hi = _parse_bound(args.until)

    files_with_root: List[Tuple[Path, Path]] = []
    for root in roots:
        files_with_root.extend((f, root) for f in sorted(root.rglob("*.jsonl")))
    file_counts: Dict[str, int] = defaultdict(int)
    fora_usage: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    groups: Dict[str, Group] = {}
    counters: Dict[str, int] = defaultdict(int)
    raw_loc: Dict[Tuple[str, str], Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    initial_prefix: List[int] = []  # subagents: first turn's input + cache_read + writes
    peak_context: List[int] = []  # subagents: max over turns of input + cache_read + writes (one value per transcript)

    for path, root in files_with_root:
        role, label, loc = classify(path, root)
        file_counts[role + "|" + label] += 1
        first_seen = True
        prev_cr = 0
        peak = 0
        for obj in iter_lines(path):
            counters["usage_lines_seen"] += 1
            got = accept(obj, role, counters) if role != "fora" else (obj.get("message"), (obj.get("message") or {}).get("usage"))
            if not got or not isinstance(got[1], dict):
                continue
            msg, usage = got
            ts = _parse_ts(obj.get("timestamp"))
            if ts is None:
                counters["skipped_no_timestamp"] += 1
                continue
            if (lo is not None and ts < lo) or (hi is not None and ts > hi):
                counters["out_of_window"] += 1
                continue
            u = usage_tuple(usage)
            model = normalize_model(msg.get("model"))
            if role == "fora":
                acc = fora_usage[label]
                acc["records"] += 1
                acc["cache_read"] += u[2]
                acc["output"] += u[1]
                continue
            if args.raw_by_location:
                r = raw_loc[(loc, model)]
                r["records"] += 1
                add_usage(r, u)
            mid = msg.get("id")
            key = ("mid:" + mid) if isinstance(mid, str) and mid else "req:%s:uuid:%s" % (obj.get("requestId"), obj.get("uuid"))
            if not (isinstance(mid, str) and mid):
                counters["records_without_message_id"] += 1
            g = groups.get(key)
            if g is None:
                groups[key] = Group(u, model, role, first_seen, prev_cr)
                if role == "subagent" and first_seen:
                    initial_prefix.append(u[0] + u[2] + u[3] + u[4])
            else:
                g.add(u, model)
            first_seen = False
            prev_cr = u[2]
            peak = max(peak, u[0] + u[2] + u[3] + u[4])
        if role == "subagent" and peak > 0:
            peak_context.append(peak)

    variants = {"first": defaultdict(int), "last": defaultdict(int), "max_per_field": defaultdict(int)}
    dup_groups = dup_differ = 0
    by_role: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    by_model: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    big: Dict[str, Dict[str, Dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    synthetic = {"turns": 0, "tokens": 0}
    unpriced: Dict[str, int] = defaultdict(int)
    for g in groups.values():
        if g.n > 1:
            dup_groups += 1
            if g.differs:
                dup_differ += 1
        add_usage(variants["first"], g.first)
        add_usage(variants["last"], g.last)
        add_usage(variants["max_per_field"], g.max_out)
        u = g.max_out
        r = by_role[g.role]
        r["turns"] += 1
        for k, v in zip(FIELDS, u):
            r[k] += v
        w = u[3] + u[4]
        if w > args.big_write:
            if g.first_in_file:
                kind = "initial"
            elif g.prev_cr > 0 and u[2] < REWRITE_READ_RATIO * g.prev_cr:
                kind = "rewrite"
            else:
                kind = "growth"
            b = big[g.role][kind]
            b["turns"] += 1
            b["write_tokens"] += w
            b["read_tokens"] += u[2]
        m = by_model[g.model]
        m["turns"] += 1
        for k, v in zip(FIELDS, u):
            m[k] += v
        if g.model == "<synthetic>":
            synthetic["turns"] += 1
            synthetic["tokens"] += sum(u)
        usd = usd_for(g.model, u)
        if usd is None:
            unpriced[g.model] += 1
        else:
            m["usd"] += usd
            r["usd"] += usd

    ip_sorted = sorted(initial_prefix)
    pk_sorted = sorted(peak_context)
    report = {
        "project_dirs": [str(r) for r in roots],
        "window": {"since_at": args.since_at, "until": args.until},
        "files_by_class": dict(sorted(file_counts.items())),
        "counters": dict(counters),
        "coverage_gap_fora_with_usage": {k: dict(v) for k, v in sorted(fora_usage.items())},
        "dedup": {
            "unique_keys": len(groups),
            "keys_with_duplicates": dup_groups,
            "duplicates_with_DIFFERENT_usage": dup_differ,
            "totals_first_wins": dict(variants["first"]),
            "totals_last_wins": dict(variants["last"]),
            "totals_max_per_field": dict(variants["max_per_field"]),
        },
        "big_writes": {"threshold": args.big_write, "by_role_and_kind": {r: {k: dict(v) for k, v in kinds.items()} for r, kinds in big.items()}},
        "initial_prefix_subagents": {
            "n": len(ip_sorted),
            "p50": percentile(ip_sorted, 0.50),
            "p90": percentile(ip_sorted, 0.90),
            "max": ip_sorted[-1] if ip_sorted else 0,
        },
        "peak_context_subagents": {
            "n": len(pk_sorted),
            "p50": percentile(pk_sorted, 0.50),
            "p90": percentile(pk_sorted, 0.90),
            "max": pk_sorted[-1] if pk_sorted else 0,
            "sum": sum(pk_sorted),
        },
        "synthetic": synthetic,
        "unpriced_models": dict(unpriced),
        "by_role_max_per_field": {k: dict(v) for k, v in by_role.items()},
        "by_model_max_per_field": {k: dict(v) for k, v in by_model.items()},
    }

    if args.compare:
        with open(os.path.expanduser(args.compare)) as fh:
            other = json.load(fh)
        their = other.get("by_model") or {}
        deltas: Dict[str, object] = {}
        for model, mine in by_model.items():
            t = their.get(model)
            if not t:
                deltas[model] = "ABSENT in collector output"
                continue
            usd_mine = float(mine["usd"])
            usd_theirs = float(t.get("usd") or 0.0)
            deltas[model] = {
                "turns": int(mine["turns"]) - _as_int(t.get("turns")),
                "input": int(mine["input"]) - _as_int(t.get("input_tokens")),
                "output": int(mine["output"]) - _as_int(t.get("output_tokens")),
                "cache_read": int(mine["cache_read"]) - _as_int(t.get("cache_read_tokens")),
                "write_5m": int(mine["write_5m"]) - _as_int(t.get("cache_write_5m")),
                "write_1h": int(mine["write_1h"]) - _as_int(t.get("cache_write_1h")),
                "usd_delta": usd_mine - usd_theirs,
                "usd_rel": (usd_mine - usd_theirs) / usd_theirs if usd_theirs else None,
            }
        for model in their:
            if model not in by_model:
                deltas[model] = "ABSENT in this audit"
        report["compare_deltas_audit_minus_collector"] = deltas

    if args.raw_by_location:
        raw_out: Dict[str, Dict[str, Dict[str, int]]] = defaultdict(dict)
        for (loc, model), v in raw_loc.items():
            raw_out[model][loc] = dict(v)
        report["raw_by_location"] = {m: dict(v) for m, v in raw_out.items()}
        if args.stats_cache:
            with open(os.path.expanduser(args.stats_cache)) as fh:
                mu = (json.load(fh) or {}).get("modelUsage") or {}
            ratios: Dict[str, Dict[str, Optional[float]]] = {}
            for model in sorted(set(mu) | set(raw_out)):
                s = mu.get(model) or {}
                s_cr = _as_int(s.get("cacheReadInputTokens"))
                s_out = _as_int(s.get("outputTokens"))
                top = raw_out.get(model, {}).get("top", {})
                sd = raw_out.get(model, {}).get("sub_direct", {})
                sn = raw_out.get(model, {}).get("sub_nested", {})
                cr = (top.get("cache_read", 0), sd.get("cache_read", 0), sn.get("cache_read", 0))
                out = (top.get("output", 0), sd.get("output", 0), sn.get("output", 0))
                ratios[model] = {
                    "stats_cache_read": s_cr,
                    "cache_read_top_over_stats": (cr[0] / s_cr) if s_cr else None,
                    "cache_read_top_plus_direct_over_stats": ((cr[0] + cr[1]) / s_cr) if s_cr else None,
                    "cache_read_all_over_stats": (sum(cr) / s_cr) if s_cr else None,
                    "output_top_plus_direct_over_stats": ((out[0] + out[1]) / s_out) if s_out else None,
                }
            report["stats_cache_ratios"] = ratios

    if args.json:
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        print()
        return 0

    def fmt(n: float) -> str:
        return "{:,.0f}".format(n)

    print("audit_collector — %d project dir(s): %s" % (len(roots), ", ".join(r.name for r in roots)[:160]))
    print("window: %s → %s" % (args.since_at or "-inf", args.until or "+inf"))
    print("files by class:")
    for k, v in report["files_by_class"].items():
        if not k.startswith("fora|"):
            print("  %-48s %6d" % (k, v))
    print("  fora|(%d distinct labels)" % sum(1 for k in report["files_by_class"] if k.startswith("fora|")))
    print("counters: %s" % dict(counters))
    print("COVERAGE gap (fora-pattern files WITH usage, in window): %s" % ("none" if not fora_usage else ""))
    for k, v in sorted(fora_usage.items()):
        print("  %-48s records=%d cache_read=%s output=%s" % (k, v["records"], fmt(v["cache_read"]), fmt(v["output"])))
    d = report["dedup"]
    print("DEDUP: unique=%d with_duplicates=%d duplicates_with_DIFFERENT_usage=%d" % (d["unique_keys"], d["keys_with_duplicates"], d["duplicates_with_DIFFERENT_usage"]))
    for name in ("totals_first_wins", "totals_last_wins", "totals_max_per_field"):
        t = d[name]
        print("  %-22s input=%s output=%s cache_read=%s w5m=%s w1h=%s" % (name, fmt(t.get("input", 0)), fmt(t.get("output", 0)), fmt(t.get("cache_read", 0)), fmt(t.get("write_5m", 0)), fmt(t.get("write_1h", 0))))
    print("BIG WRITES (> %s tokens written in one turn), by role and kind:" % fmt(args.big_write))
    for role, kinds in sorted(big.items()):
        for kind, b in sorted(kinds.items()):
            print("  %-9s %-8s turns=%5d write_tokens=%s read_tokens_on_those_turns=%s" % (role, kind, b["turns"], fmt(b["write_tokens"]), fmt(b["read_tokens"])))
    ipx = report["initial_prefix_subagents"]
    print("INITIAL PREFIX (subagents, first turn input+cache): n=%d p50=%s p90=%s max=%s" % (ipx["n"], fmt(ipx["p50"]), fmt(ipx["p90"]), fmt(ipx["max"])))
    pkx = report["peak_context_subagents"]
    print("PEAK CONTEXT (subagents, max turn input+cache per transcript): n=%d p50=%s p90=%s max=%s sum=%s" % (pkx["n"], fmt(pkx["p50"]), fmt(pkx["p90"]), fmt(pkx["max"]), fmt(pkx["sum"])))
    print("SYNTHETIC: turns=%d tokens=%d | UNPRICED: %s" % (synthetic["turns"], synthetic["tokens"], dict(unpriced) or "none"))
    print("BY ROLE (max per field):")
    for role, r in sorted(by_role.items()):
        print("  %-9s turns=%7d input=%s cache_read=%s w5m=%s w1h=%s output=%s USD=%.2f" % (role, int(r["turns"]), fmt(r["input"]), fmt(r["cache_read"]), fmt(r["write_5m"]), fmt(r["write_1h"]), fmt(r["output"]), r["usd"]))
    print("BY MODEL (max per field, USD from PRICING):")
    for model, m in sorted(by_model.items(), key=lambda kv: -kv[1]["usd"]):
        print("  %-28s turns=%7d cache_read=%s output=%s USD=%.2f" % (model, int(m["turns"]), fmt(m["cache_read"]), fmt(m["output"]), m["usd"]))
    if args.compare:
        print("COMPARE (audit − collector), per model:")
        for model, dl in sorted(report["compare_deltas_audit_minus_collector"].items()):
            if isinstance(dl, dict):
                print("  %-28s turns=%+d input=%+d output=%+d cache_read=%+d w5m=%+d w1h=%+d usd=%+.4f (%s)" % (
                    model, dl["turns"], dl["input"], dl["output"], dl["cache_read"], dl["write_5m"], dl["write_1h"], dl["usd_delta"],
                    ("%+.5f%%" % (100 * dl["usd_rel"])) if dl["usd_rel"] is not None else "n/a"))
            else:
                print("  %-28s %s" % (model, dl))
    if args.raw_by_location and args.stats_cache:
        print("RAW BY LOCATION vs stats-cache.modelUsage (cache_read ratios; NO dedup):")
        print("  %-26s %14s %7s %7s %7s | %7s" % ("model", "stats cRead", "top", "top+dir", "all", "out t+d"))
        for model, rr in sorted(report["stats_cache_ratios"].items()):
            f = lambda x: ("%.3f" % x) if isinstance(x, float) else "-"
            print("  %-26s %14s %7s %7s %7s | %7s" % (model, fmt(rr["stats_cache_read"]), f(rr["cache_read_top_over_stats"]), f(rr["cache_read_top_plus_direct_over_stats"]), f(rr["cache_read_all_over_stats"]), f(rr["output_top_plus_direct_over_stats"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
