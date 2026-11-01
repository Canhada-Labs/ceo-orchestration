"""labeling audit-query declarations."""

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

__all__ = ('_LABEL_STORE_PATH', '_LABEL_VALID_CASES', '_LABEL_VALID_LABELS', '_label_store_path', '_canonical_json_for_chain', '_compute_label_hmac', '_load_label_records', '_append_label_record', 'cmd_label', '_wilson_bounds', 'cmd_fp_rate', 'cmd_case_summary', 'cmd_codex_writeguard_summary')

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
