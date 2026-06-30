"""Tournament reporter — JSONL streaming + hashes-only + aggregate + HMAC anchor.

Round 1 closures:
- C-P0-3: strict schema, hashes-not-raw, default-deny extras, HMAC anchor
- C-P0-8: streaming writer (memory O(concurrent_tasks))
- F-PERF5: tournament_task_scored fields match ceo-cost.py schema for
  transparent aggregate (model + tokens_in + tokens_out)

Schema per SPEC/v1/tournament-report.schema.md:
- task record: type / fixture_id / fixture_sha256 / task_type / model /
  verdict / output_sha256 / tokens_in / tokens_out / cost_usd /
  wall_clock_ms / rationale_sha256? / rationale_length? / confidence?
- aggregate record: type / run_id / fixtures_count / models_count /
  judge_runs / win_rate / total_cost_usd / projected_cost_usd /
  budget_cap_usd / errored_count / tasks_completed / partial /
  abort_reason? / adr052_validation

ADR-052 validation signals:
  - opus_mid_surprise       (security+code review, opus - sonnet < 5pp)
  - sonnet_underperforms    (performance-triage, opus - sonnet > 15pp)
  - haiku_insufficient      (docs-writing, haiku pass-rate < 0.7)
  - opus_confirmed          (security+code review, opus > sonnet + 15pp)
  - haiku_sufficient        (docs-writing, haiku pass-rate >= 0.7)
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


# ─── Content hashes (C-P0-3 — no raw content in reports) ───


def sha256_text(text: Optional[str]) -> str:
    """SHA-256 hex digest of a string (or empty for None)."""
    content = (text or "").encode("utf-8")
    return hashlib.sha256(content).hexdigest()


# ─── Task record emission ───


def make_task_record(
    *,
    fixture_id: str,
    fixture_content: str,
    task_type: str,
    model: str,
    verdict: str,
    output_text: Optional[str],
    tokens_in: int,
    tokens_out: int,
    cost_usd: float,
    wall_clock_ms: int,
    rationale: Optional[str] = None,
    confidence: Optional[float] = None,
    error_reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a strict-schema task record. Hashes-only per C-P0-3.

    `fixture_content` is the raw fixture prompt (used to compute
    fixture_sha256 for integrity — not included in the record itself).
    `output_text` and `rationale` are likewise hashed; only length +
    hash propagate into the report.

    All string values capped at 256 chars per schema.
    """
    rec: Dict[str, Any] = {
        "type": "task",
        "fixture_id": fixture_id[:256] if fixture_id else "",
        "fixture_sha256": sha256_text(fixture_content),
        "task_type": task_type[:64] if task_type else "",
        "model": model[:64] if model else "",
        "verdict": verdict if verdict in ("pass", "fail", "errored") else "errored",
        "output_sha256": sha256_text(output_text),
        "tokens_in": int(tokens_in),
        "tokens_out": int(tokens_out),
        "cost_usd": round(float(cost_usd), 6),
        "wall_clock_ms": int(wall_clock_ms),
    }
    if rationale is not None:
        rec["rationale_sha256"] = sha256_text(rationale)
        rec["rationale_length"] = len(rationale)
    if confidence is not None:
        rec["confidence"] = round(float(confidence), 3)
    if error_reason is not None:
        # error_reason is the only string that may legitimately carry
        # prose — capped at 256 chars per schema default-deny policy.
        rec["error_reason"] = str(error_reason)[:256]
    return rec


# ─── ADR-052 validation signals ───


# Thresholds per ADR-063 §ADR-052 validation logic + ADR-064 §C-P0-1
# statistical-power gate.
#
# PLAN-045 F-12-03 closure: reporter emits `opus_confirmed` at 15pp
# (ADVISORY — directionally meaningful at n=10). learn.py policy-
# change gate sits at 25pp (ADR-064 §C-P0-1 honest power floor for
# n≥30). Reader seeing `opus_confirmed` in the 15-24pp band must NOT
# conclude a policy change is imminent — advisory only. A NEW signal
# `opus_policy_change_worthy` fires at ≥25pp to match learn.py's
# actionable gate. Cross-ref: SPEC/v1/tournament-report.schema.md
# §Statistical-power caveat (staged amendment).
_PP_STATS_NOISE = 0.05           # 5pp sampling noise at n=10
_PP_SIGNIFICANT = 0.15           # ADVISORY — F-PERF4 at n=10
_PP_POLICY_CHANGE_WORTHY = 0.25  # ACTIONABLE — ADR-064 §C-P0-1 gate
_HAIKU_SUFFICIENT_THRESHOLD = 0.7


def validate_adr052(win_rate_matrix: Dict[str, Dict[str, float]]) -> Dict[str, str]:
    """Compare empirical win-rate against ADR-052 tier claims.

    Input shape:
        {
          "security-review": {"claude-opus-4-8": 0.9, "claude-sonnet-4-6": 0.7, ...},
          "code-review":     {...},
          "performance-triage": {...},
          "docs-writing":    {...}
        }

    Returns advisory signal per task-type. Signals are STRINGS mapping to
    documented outcomes. Does NOT auto-revoke VETO floor — Owner action
    required for any ADR-052 amendment per §Consequences.
    """
    signals: Dict[str, str] = {}

    opus = "claude-opus-4-8"
    sonnet = "claude-sonnet-4-6"
    haiku = "claude-haiku-4-5-20251001"

    # Expect Opus > Sonnet on VETO-class tasks
    for vt in ("security-review", "code-review"):
        cell = win_rate_matrix.get(vt, {})
        if not cell:
            signals[vt] = "no_data"
            continue
        opus_wr = cell.get(opus)
        sonnet_wr = cell.get(sonnet)
        if opus_wr is None or sonnet_wr is None:
            signals[vt] = "incomplete_data"
            continue
        gap = opus_wr - sonnet_wr
        if gap >= _PP_POLICY_CHANGE_WORTHY:
            # ACTIONABLE — matches learn.py MIN_GAP_PP (25pp)
            signals[vt] = "opus_policy_change_worthy"
        elif gap >= _PP_SIGNIFICANT:
            # ADVISORY — directionally meaningful at n=10
            signals[vt] = "opus_confirmed"
        elif gap < _PP_STATS_NOISE:
            signals[vt] = "opus_mid_surprise"
        else:
            signals[vt] = "opus_marginal"

    # Expect Opus ≈ Sonnet on performance-triage
    cell = win_rate_matrix.get("performance-triage", {})
    if cell:
        opus_wr = cell.get(opus)
        sonnet_wr = cell.get(sonnet)
        if opus_wr is None or sonnet_wr is None:
            signals["performance-triage"] = "incomplete_data"
        else:
            gap = opus_wr - sonnet_wr
            if gap > _PP_SIGNIFICANT:
                signals["performance-triage"] = "sonnet_underperforms"
            else:
                signals["performance-triage"] = "parity_confirmed"
    else:
        signals["performance-triage"] = "no_data"

    # Expect Haiku sufficient on docs-writing
    cell = win_rate_matrix.get("docs-writing", {})
    if cell:
        haiku_wr = cell.get(haiku)
        if haiku_wr is None:
            signals["docs-writing"] = "incomplete_data"
        elif haiku_wr >= _HAIKU_SUFFICIENT_THRESHOLD:
            signals["docs-writing"] = "haiku_sufficient"
        else:
            signals["docs-writing"] = "haiku_insufficient"
    else:
        signals["docs-writing"] = "no_data"

    # test-design — no prior claim; record pass rates only
    cell = win_rate_matrix.get("test-design", {})
    if cell:
        signals["test-design"] = "no_prior_claim"
    else:
        signals["test-design"] = "no_data"

    return signals


# ─── Win-rate matrix construction ───


def compute_win_rate_matrix(task_records: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """Build win_rate[task_type][model] from task records.

    Per QA F-QA P5 invariant: errored tasks are EXCLUDED from the
    denominator (they are not failures nor successes; they are non-data).

        win_rate[t][m] = pass_count[t][m] / (total[t][m] - errored[t][m])

    If total - errored == 0: return 0.0 (no data, not division-by-zero).
    """
    stats: Dict[str, Dict[str, Dict[str, int]]] = {}
    for rec in task_records:
        if rec.get("type") != "task":
            continue
        tt = rec.get("task_type")
        model = rec.get("model")
        verdict = rec.get("verdict")
        if not tt or not model or not verdict:
            continue
        bucket = stats.setdefault(tt, {}).setdefault(
            model, {"pass": 0, "fail": 0, "errored": 0}
        )
        if verdict in bucket:
            bucket[verdict] += 1

    matrix: Dict[str, Dict[str, float]] = {}
    for tt, models in stats.items():
        matrix[tt] = {}
        for model, counts in models.items():
            total = counts["pass"] + counts["fail"] + counts["errored"]
            non_errored = total - counts["errored"]
            if non_errored <= 0:
                matrix[tt][model] = 0.0
            else:
                matrix[tt][model] = round(counts["pass"] / non_errored, 4)
    return matrix


# ─── HMAC anchor (C-P0-3 — ADR-055 precedent) ───


def compute_report_hmac(report_path: Path) -> Optional[str]:
    """Compute HMAC-chain anchor over a committed tournament report JSONL.

    Uses the same audit-log HMAC chain infrastructure from
    `_lib/audit_hmac.py` (ADR-055). Returns hex digest of the final
    HMAC, suitable for writing to `<report>.hmac` companion file.

    Fail-open: returns None if audit_hmac unavailable or key missing
    (tournament can run without HMAC in dev; CI workflow verifies).
    """
    try:
        _hooks_lib = (
            Path(__file__).resolve().parent.parent.parent / "hooks"
        )
        if str(_hooks_lib) not in sys.path:
            sys.path.insert(0, str(_hooks_lib))
        from _lib import audit_hmac, canonical_json  # type: ignore
    except Exception:
        return None

    try:
        key = audit_hmac.get_or_create_key()
    except Exception:
        return None

    # Chain-walk every JSONL line into an HMAC (prev || canonical(entry))
    prev = b"\x00" * audit_hmac.HMAC_BYTES
    try:
        with report_path.open("r", encoding="utf-8") as handle:
            for raw in handle:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    # Skip malformed lines; HMAC still anchors what valid
                    continue
                prev = audit_hmac.compute_entry_hmac(key, prev, entry)
        return prev.hex()
    except Exception:
        return None


def write_report_anchor(report_path: Path) -> Optional[Path]:
    """Emit `<report>.hmac` companion file with hex digest.

    Returns the anchor path on success, None on fail-open.
    """
    digest = compute_report_hmac(report_path)
    if digest is None:
        return None
    anchor = report_path.with_suffix(report_path.suffix + ".hmac")
    anchor.write_text(digest + "\n", encoding="utf-8")
    return anchor


# ─── Report loader (for downstream consumers) ───


def load_report(report_path: Path) -> Dict[str, Any]:
    """Parse a tournament report JSONL back into task records + aggregate.

    Returns {"tasks": [...], "aggregate": {...}}. Missing aggregate →
    {"aggregate": None}. Malformed lines are skipped silently with a
    parse_errors counter.
    """
    tasks: List[Dict[str, Any]] = []
    aggregate: Optional[Dict[str, Any]] = None
    parse_errors = 0
    with report_path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                parse_errors += 1
                continue
            etype = entry.get("type")
            if etype == "task":
                tasks.append(entry)
            elif etype == "aggregate":
                aggregate = entry
    return {"tasks": tasks, "aggregate": aggregate, "parse_errors": parse_errors}
