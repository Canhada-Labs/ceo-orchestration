#!/usr/bin/env python3
"""PLAN-090 AMENDMENT-1 / Wave A.10 — confidence-gate empirical baseline.

Reads audit-log.jsonl over the last 30d, groups `claim_emitted` events by
`claim_type`, computes per-class FPR estimates via paired
`confidence_gate_verdict` events, and emits a baseline report at
`.claude/plans/PLAN-090/wave-a10-confidence-baseline.md`.

NO mode flip — measurement-only deliverable. PLAN-100 consumes the report
to decide per-class promotion (HIGH_CONFIDENCE_BLOCK / MED_ADVISORY /
LOW_ADVISORY).

Stdlib only. Per ADR-126 §Part 5 the script lives in `.claude/scripts/`
(framework core, not a sidecar).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# stdlib-only — explicitly avoid any third-party dep.

DEFAULT_WINDOW_DAYS = 30
DEFAULT_MIN_SAMPLES = 5  # below this: emit INSUFFICIENT_DATA rows
PLAN_100_MIN_SAMPLES = 200  # PLAN-100 promotion gate; documented for context


def _audit_log_path() -> Path:
    """Locate audit-log.jsonl per CEO_AUDIT_LOG_PATH or default home path."""
    env = os.environ.get("CEO_AUDIT_LOG_PATH")
    if env:
        return Path(env)
    home = Path(os.environ.get("HOME") or Path.home())
    return (
        home / ".claude" / "projects" / "ceo-orchestration" / "audit-log.jsonl"
    )


def _parse_iso(ts: str) -> Optional[dt.datetime]:
    """Best-effort ISO-8601 parse. Returns None on malformed input."""
    if not ts:
        return None
    candidates = (
        ts.replace("Z", "+00:00"),
        ts,
    )
    for c in candidates:
        try:
            d = dt.datetime.fromisoformat(c)
            if d.tzinfo is None:
                d = d.replace(tzinfo=dt.timezone.utc)
            return d
        except (TypeError, ValueError):
            continue
    return None


def _scan_log(
    log_path: Path,
    cutoff: dt.datetime,
) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, List[Dict[str, Any]]]]:
    """Return (claims_by_type, verdicts_by_claim_id) over the time window.

    Both maps key off the same `claim_type` and `claim_id` discriminators
    so verdicts can be paired with claims in O(n).
    """
    claims_by_type: Dict[str, List[Dict[str, Any]]] = {}
    verdicts_by_claim_id: Dict[str, List[Dict[str, Any]]] = {}
    if not log_path.is_file():
        return claims_by_type, verdicts_by_claim_id

    with log_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = _parse_iso(ev.get("ts") or "")
            if ts is None or ts < cutoff:
                continue
            action = ev.get("action") or ""
            if action == "claim_emitted":
                claim_type = (ev.get("claim_type") or "").strip()
                if not claim_type:
                    claim_type = "unclassified"
                claims_by_type.setdefault(claim_type, []).append(ev)
            elif action == "confidence_gate_verdict":
                claim_id = (ev.get("claim_id") or "").strip()
                if claim_id:
                    verdicts_by_claim_id.setdefault(claim_id, []).append(ev)
    return claims_by_type, verdicts_by_claim_id


def _compute_fpr_per_class(
    claims_by_type: Dict[str, List[Dict[str, Any]]],
    verdicts_by_claim_id: Dict[str, List[Dict[str, Any]]],
    min_samples: int,
) -> List[Dict[str, Any]]:
    """For each claim-class, compute (n, false_positives, fpr_basis_points).

    A "false positive" = the gate emitted a `claim_emitted` and a later
    `confidence_gate_verdict` event paired the same `claim_id` with
    `verdict == "refuted"` or `was_false_positive == True`.
    """
    rows: List[Dict[str, Any]] = []
    for class_name in sorted(claims_by_type.keys()):
        events = claims_by_type[class_name]
        n = len(events)
        if n < min_samples:
            rows.append({
                "class": class_name,
                "n": n,
                "false_positives": 0,
                "fpr_basis_points": None,
                "status": "INSUFFICIENT_DATA",
            })
            continue
        false_positives = 0
        for ev in events:
            claim_id = (ev.get("claim_id") or "").strip()
            if not claim_id:
                continue
            paired = verdicts_by_claim_id.get(claim_id, [])
            if any(
                (v.get("verdict") == "refuted")
                or v.get("was_false_positive") is True
                for v in paired
            ):
                false_positives += 1
        fpr_basis_points = int(round((false_positives / float(n)) * 10000))
        rows.append({
            "class": class_name,
            "n": n,
            "false_positives": false_positives,
            "fpr_basis_points": fpr_basis_points,
            "status": "OK" if n >= PLAN_100_MIN_SAMPLES else "BELOW_PROMOTION_GATE",
        })
    return rows


def _render_report(
    rows: List[Dict[str, Any]],
    window_days: int,
    cutoff: dt.datetime,
    now: dt.datetime,
) -> str:
    distinct = sum(1 for r in rows if r["n"] > 0)
    md = [
        "# PLAN-090 Wave A.10 (AMENDMENT-1) — confidence-gate empirical baseline",
        "",
        f"Window: last {window_days}d (from {cutoff.isoformat()} to {now.isoformat()})",
        "",
        f"**Distinct claim-classes observed: {distinct}**",
        "",
        "Per-class FPR estimate via paired `confidence_gate_verdict` events.",
        f"`INSUFFICIENT_DATA` rows have n < {DEFAULT_MIN_SAMPLES}; PLAN-100",
        f"promotion gate requires n >= {PLAN_100_MIN_SAMPLES}.",
        "",
        "| Class | n | FP | FPR (bps) | Status |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        fpr = r["fpr_basis_points"]
        fpr_str = "—" if fpr is None else str(fpr)
        md.append(
            f"| `{r['class']}` | {r['n']} | {r['false_positives']} | "
            f"{fpr_str} | {r['status']} |"
        )
    md.append("")
    md.append("## Invariant assertion")
    md.append("")
    md.append(
        "No mode flip applied — `check_confidence_gate.py` remains ADVISORY. "
        "ADR-118-AMEND-1 §6 cites this report; PLAN-100 consumes it for "
        "future per-class BLOCK_MODE promotion decisions."
    )
    md.append("")
    return "\n".join(md)


def _emit_audit(rows: List[Dict[str, Any]]) -> None:
    """Best-effort audit emit. Fail-soft if audit_emit not on sys.path."""
    try:
        sys.path.insert(
            0,
            str(Path(__file__).resolve().parents[1] / "hooks"),
        )
        from _lib import audit_emit
    except Exception:
        return
    fn = getattr(audit_emit, "emit_confidence_gate_baseline_emitted", None)
    if not callable(fn):
        return
    distinct = sum(1 for r in rows if r["n"] > 0)
    insufficient = sum(1 for r in rows if r["status"] == "INSUFFICIENT_DATA")
    try:
        fn(
            distinct_classes=distinct,
            insufficient_data_classes=insufficient,
            rows_total=len(rows),
        )
    except Exception:
        return


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--window-days", type=int, default=DEFAULT_WINDOW_DAYS,
        help=f"Backfill window (default: {DEFAULT_WINDOW_DAYS})",
    )
    parser.add_argument(
        "--min-samples", type=int, default=DEFAULT_MIN_SAMPLES,
        help="Minimum samples per class to compute FPR; below → INSUFFICIENT_DATA",
    )
    parser.add_argument(
        "--audit-log", type=Path, default=None,
        help="Override audit-log.jsonl path (default: CEO_AUDIT_LOG_PATH or $HOME path)",
    )
    parser.add_argument(
        "--report-path", type=Path, default=Path(
            ".claude/plans/PLAN-090/wave-a10-confidence-baseline.md"
        ),
        help="Output report path",
    )
    args = parser.parse_args(argv)

    log_path = args.audit_log or _audit_log_path()
    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(days=int(args.window_days))

    claims, verdicts = _scan_log(log_path, cutoff)
    rows = _compute_fpr_per_class(claims, verdicts, int(args.min_samples))
    report = _render_report(rows, int(args.window_days), cutoff, now)

    out_path = args.report_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")

    _emit_audit(rows)

    distinct = sum(1 for r in rows if r["n"] > 0)
    print(
        f"confidence-gate-backfill: {distinct} distinct claim-class(es) "
        f"over {args.window_days}d -> {out_path}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
