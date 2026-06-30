#!/usr/bin/env python3
"""generate_flip_metrics — synthetic flip-metric audit event generator.

PLAN-012 Phase 2 D9. Backfills realistic distributions of the four
volume-bound flip-metric events so flip-decision math (Wilson upper-CI,
per-mode error, Mann-Whitney drift) can be validated BEFORE Sprint-15/16
live windows open.

Events (1:1 with shipped schemas):
    output_safety_flag    — ADR-036 (7 reason families)
    budget_exceeded       — ADR-033 (legitimate flag)
    otel_export_dropped   — ADR-035
    confidence_gate_claim — ADR-018/019 (claim_kind)

CLI: ``--event X --n N --fp-rate R --out PATH [--seed S]``.
Output is JSONL round-trippable through ``audit-query.py``.
Stdlib-only; Python >=3.9.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


# Event kinds — stays in lockstep with owning ADR tables.
SUPPORTED_EVENTS: Tuple[str, ...] = (
    "output_safety_flag",
    "budget_exceeded",
    "otel_export_dropped",
    "confidence_gate_claim",
)

# ADR-036 §Pattern families (7 — must match schema row).
OUTPUT_SAFETY_FAMILIES: Tuple[str, ...] = (
    "api_key", "jwt", "private_key", "connection_string",
    "email", "cpf", "credit_card",
)

# ADR-018 claim grammar — kept in sync with SPEC/v1/audit-log.schema.md.
CLAIM_KINDS: Tuple[str, ...] = (
    "architecture_decision", "security_finding", "performance_claim",
    "test_coverage_claim", "dependency_impact",
)


def _iso(ts: datetime) -> str:
    """ISO-8601 with explicit Z suffix."""
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _plan_ids(n: int, rng: random.Random) -> List[str]:
    candidates = [f"PLAN-{i:03d}" for i in range(1, 30)]
    return [rng.choice(candidates) for _ in range(n)]


def _seed_time(rng: random.Random, base: Optional[datetime] = None) -> datetime:
    if base is None:
        base = datetime(2026, 4, 1, tzinfo=timezone.utc)
    return base + timedelta(hours=rng.uniform(0, 24 * 30))


def _base_row(action: str, adr: str, plan_id: str, ts: datetime, rng: random.Random) -> Dict[str, Any]:
    """Shared envelope for every synthetic row."""
    return {
        "action": action,
        "ts": _iso(ts),
        "project": "ceo-orchestration",
        "session_id": f"synth-{rng.randrange(10**9):09d}",
        "plan_id": plan_id,
        "adr": adr,
        "synthetic": True,
    }


def _emit_output_safety_flag(
    rng: random.Random, fp_rate: float, plan_id: str, ts: datetime
) -> Dict[str, Any]:
    """Synthesize ``output_safety_flag`` (ADR-036)."""
    row = _base_row("output_safety_flag", "ADR-036", plan_id, ts, rng)
    row["reason_code"] = rng.choice(OUTPUT_SAFETY_FAMILIES)
    row["is_false_positive"] = rng.random() < fp_rate
    row["mode"] = "flag"
    return row


def _emit_budget_exceeded(
    rng: random.Random, fp_rate: float, plan_id: str, ts: datetime
) -> Dict[str, Any]:
    """Synthesize ``budget_exceeded`` (ADR-033).

    fp_rate controls fraction flagged as legitimate (FP for the flip
    criterion: ADR-033 §Legitimacy).
    """
    row = _base_row("budget_exceeded", "ADR-033", plan_id, ts, rng)
    row["tokens_observed"] = rng.randint(100_001, 400_000)
    row["cap"] = 100_000
    row["scope"] = rng.choice(["per_spawn", "per_plan"])
    row["legitimate"] = rng.random() < fp_rate
    return row


def _emit_otel_export_dropped(
    rng: random.Random, fp_rate: float, plan_id: str, ts: datetime
) -> Dict[str, Any]:
    """Synthesize ``otel_export_dropped`` (ADR-035).

    fp_rate = fraction of drops caused by exporter bug (FP) vs real
    downstream outage (TP).
    """
    is_fp = rng.random() < fp_rate
    row = _base_row("otel_export_dropped", "ADR-035", plan_id, ts, rng)
    row["reason"] = rng.choice(
        ("scheme_not_allowed", "host_not_in_allowlist")
        if is_fp
        else ("timeout", "receiver_unreachable", "payload_too_large")
    )
    row["queue_depth"] = rng.randint(0, 1000)
    row["is_false_positive"] = is_fp
    return row


def _emit_confidence_gate_claim(
    rng: random.Random, fp_rate: float, plan_id: str, ts: datetime
) -> Dict[str, Any]:
    """Synthesize ``confidence_gate_claim`` (ADR-018/019)."""
    is_fp = rng.random() < fp_rate
    row = _base_row("confidence_gate_claim", "ADR-019", plan_id, ts, rng)
    row["claim_kind"] = rng.choice(CLAIM_KINDS)
    row["confidence"] = round(
        rng.uniform(0.20, 0.55) if is_fp else rng.uniform(0.60, 0.95), 3
    )
    row["is_false_positive"] = is_fp
    return row


# Dispatch map — adding a new event kind is one-line here.
_EMITTERS = {
    "output_safety_flag": _emit_output_safety_flag,
    "budget_exceeded": _emit_budget_exceeded,
    "otel_export_dropped": _emit_otel_export_dropped,
    "confidence_gate_claim": _emit_confidence_gate_claim,
}


def generate_records(
    event: str, n: int, fp_rate: float, seed: int = 0
) -> List[Dict[str, Any]]:
    """Return exactly ``n`` synthetic records for the named event.

    Reproducibility: same ``seed`` yields byte-identical output.
    """
    if event not in SUPPORTED_EVENTS:
        raise ValueError(
            f"unsupported event {event!r} — known events: {SUPPORTED_EVENTS}"
        )
    if n < 0:
        raise ValueError(f"--n must be non-negative, got {n}")
    if not (0.0 <= fp_rate <= 1.0):
        raise ValueError(f"--fp-rate must be in [0.0, 1.0], got {fp_rate}")

    rng = random.Random(seed)
    plan_pool = _plan_ids(n, rng)
    emitter = _EMITTERS[event]
    rows: List[Dict[str, Any]] = []
    for idx in range(n):
        ts = _seed_time(rng)
        rows.append(emitter(rng, fp_rate, plan_pool[idx], ts))
    return rows


def write_jsonl(rows: Iterable[Dict[str, Any]], out_path: Path) -> int:
    """Write rows as JSONL; return byte count written."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with out_path.open("w", encoding="utf-8") as fp:
        for row in rows:
            line = json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            total += fp.write(line)
    return total


def build_parser() -> argparse.ArgumentParser:
    """Argparse CLI surface. Stdlib only."""
    p = argparse.ArgumentParser(
        prog="generate_flip_metrics",
        description=(
            "Synthesize flip-metric audit events (PLAN-012 D9). "
            "Writes JSONL compatible with audit-query.py."
        ),
    )
    p.add_argument(
        "--event",
        required=True,
        choices=SUPPORTED_EVENTS,
        help="Event kind to synthesize.",
    )
    p.add_argument(
        "--n",
        required=True,
        type=int,
        help="Number of records to emit (non-negative).",
    )
    p.add_argument(
        "--fp-rate",
        required=True,
        type=float,
        help="False-positive rate, [0.0, 1.0].",
    )
    p.add_argument(
        "--out",
        required=True,
        type=Path,
        help="Output JSONL path (parent dir created if missing).",
    )
    p.add_argument(
        "--seed",
        default=0,
        type=int,
        help="RNG seed (default 0). Same seed + same args = byte-identical.",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        rows = generate_records(args.event, args.n, args.fp_rate, args.seed)
    except ValueError as exc:
        parser.error(str(exc))
        return 2  # unreachable — argparse exits 2
    written = write_jsonl(rows, args.out)
    print(
        f"OK: wrote {len(rows)} {args.event} records "
        f"({written} bytes) to {args.out}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover — CLI entry
    sys.exit(main())
