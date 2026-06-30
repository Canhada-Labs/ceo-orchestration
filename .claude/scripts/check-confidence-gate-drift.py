#!/usr/bin/env python3
"""PLAN-100 Wave B.3 / PLAN-106 Wave F.1 — confidence-gate drift detector.

PLAN-106 Wave F.1 refactor (Codex R2 P2 Item-8 fold):
- Extract pure-logic into a side-effect-free importable function
  `detect_drift_7d(window_days=7, threshold_bps=200, audit_log_path=None)
  -> Tuple[bool, str, dict]` callable from ceo-boot.py.
- Move `sys.path` mutation INTO `main()` (CLI entry only). Before
  this refactor, the script mutated sys.path at module-import time
  (lines 32-37 in v1.34.0); a future ceo-boot dispatcher importing
  this module would inherit the mutation. After F.1, `detect_drift_7d`
  imports cleanly without side-effects.

PLAN-100 Wave B.3 original surface preserved (`main()` CLI behaviour
unchanged):

Reads the audit-log, computes per-class 7-day rolling FPR (verifier-fail
rate) for classes in HIGH_CONFIDENCE_BLOCK tier, and emits
`confidence_gate_fp_drift_detected` when threshold is breached.

Threshold per ADR-019-AMEND-1 §6: > 2% (200 bps) rolling FPR.

Invocation:
    python3 .claude/scripts/check-confidence-gate-drift.py
    python3 .claude/scripts/check-confidence-gate-drift.py --window-days 7 --threshold-bps 200
    python3 .claude/scripts/check-confidence-gate-drift.py --emit  # actually emit
    python3 .claude/scripts/check-confidence-gate-drift.py --json  # machine-readable

Importable surface (PLAN-106 Wave F.1):
    from check_confidence_gate_drift import detect_drift_7d
    drift, summary, detail = detect_drift_7d(window_days=7, threshold_bps=200)

Stdlib only. Python >= 3.9.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_DEFAULT_WINDOW_DAYS = 7
_DEFAULT_THRESHOLD_BPS = 200  # 2.0% per ADR-019-AMEND-1 §6
_DEFAULT_AUTO_DEMOTE_COOLING_HOURS = 24

# PLAN-106 Wave F.1 — `sys.path` mutation MOVED to main(). Module-import
# stays side-effect-free for the importable `detect_drift_7d` surface
# consumed by ceo-boot.py CHECKS registry.


def _load_class_tiers(repo_root: Path) -> Dict[str, str]:
    """Load per-class tier config from canonical location."""
    config = repo_root / ".claude" / "data" / "confidence-gate-class-tiers.json"
    try:
        if not config.is_file():
            return {}
        with open(config, "rb") as f:
            data = json.loads(f.read().decode("utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError, ValueError, UnicodeError):
        return {}
    tiers = data.get("tiers") if isinstance(data, dict) else None
    if not isinstance(tiers, dict):
        return {}
    return {str(k): str(v) for k, v in tiers.items() if isinstance(v, str)}


def _resolve_audit_log() -> Path:
    """Resolve the audit-log.jsonl path."""
    env = os.environ.get("CEO_AUDIT_LOG_PATH")
    if env:
        return Path(env)
    home = os.environ.get("HOME") or os.path.expanduser("~")
    return Path(home) / ".claude" / "projects" / "ceo-orchestration" / "audit-log.jsonl"


def _scan_audit_log_for_verdicts(
    log_path: Path,
    cutoff_iso: str,
) -> Dict[str, Tuple[int, int]]:
    """Walk audit-log and accumulate (n, fail_n) per class within window.

    Returns: dict[class_kind] -> (total_n, fail_n).
    Considers only `confidence_gate_verdict` events with ts >= cutoff_iso.
    """
    counts: Dict[str, List[int]] = {}  # class -> [n, fail_n]
    if not log_path.is_file():
        return {}
    try:
        with open(log_path, "rb") as f:
            for raw in f:
                try:
                    rec = json.loads(raw.decode("utf-8", errors="replace"))
                except (json.JSONDecodeError, ValueError, UnicodeError):
                    continue
                if rec.get("action") != "confidence_gate_verdict":
                    continue
                ts = rec.get("ts")
                if not isinstance(ts, str) or ts < cutoff_iso:
                    continue
                kind = rec.get("verifier_kind") or ""
                if not isinstance(kind, str) or not kind:
                    continue
                verdict = rec.get("verdict")
                if not isinstance(verdict, str):
                    continue
                bucket = counts.setdefault(kind, [0, 0])
                bucket[0] += 1
                if verdict == "fail":
                    bucket[1] += 1
    except OSError:
        return {}
    return {k: (v[0], v[1]) for k, v in counts.items()}


def _compute_drift(
    counts: Dict[str, Tuple[int, int]],
    class_tiers: Dict[str, str],
    threshold_bps: int,
    min_sample: int = 10,
) -> List[Dict[str, object]]:
    """Identify HIGH_CONFIDENCE_BLOCK classes with rolling FPR > threshold.

    Returns list of drift dicts.
    """
    drifts: List[Dict[str, object]] = []
    for cls, tier in class_tiers.items():
        if tier != "HIGH_CONFIDENCE_BLOCK":
            continue
        n, fail_n = counts.get(cls, (0, 0))
        if n < min_sample:
            continue
        fpr_bps = int(round((fail_n / float(n)) * 10000))
        if fpr_bps <= threshold_bps:
            continue
        drifts.append({
            "drift_class": cls,
            "sample_n": n,
            "fail_n": fail_n,
            "fpr_bps": fpr_bps,
            "threshold_bps": threshold_bps,
        })
    return drifts


def _format_human(drifts: List[Dict[str, object]], window_days: int) -> str:
    if not drifts:
        return f"No drift detected (window={window_days}d).\n"
    lines = [f"DRIFT DETECTED (window={window_days}d):"]
    for d in drifts:
        lines.append(
            f"  - {d['drift_class']}: n={d['sample_n']}, fail={d['fail_n']}, "
            f"FPR={d['fpr_bps']/100.0:.2f}% (threshold={d['threshold_bps']/100.0:.2f}%)"
        )
    lines.append("Auto-demote at: " + (
        datetime.now(timezone.utc) + timedelta(hours=_DEFAULT_AUTO_DEMOTE_COOLING_HOURS)
    ).isoformat().replace("+00:00", "Z"))
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# PLAN-106 Wave F.1 — IMPORTABLE SURFACE for ceo-boot.py Tier-S check.
# ---------------------------------------------------------------------------

def detect_drift_7d(
    window_days: int = _DEFAULT_WINDOW_DAYS,
    threshold_bps: int = _DEFAULT_THRESHOLD_BPS,
    audit_log_path: Optional[Path] = None,
    min_sample: int = 10,
    repo_root: Optional[Path] = None,
) -> Tuple[bool, str, Dict[str, Any]]:
    """PLAN-106 Wave F.1 — side-effect-free drift detection.

    Returns (drift_detected, summary, detail_dict).

    Args:
        window_days: rolling window for FPR computation (default 7).
        threshold_bps: drift threshold in basis points (default 200 = 2%).
        audit_log_path: explicit path override; None → resolve from env/HOME.
        min_sample: minimum n required per class to compute FPR (default 10).
        repo_root: explicit repo root override; None → infer from cwd.

    Semantics:
        - No tier config → returns (False, "no-tier-config", {"drifts": []})
          for fail-OPEN behavior.
        - Audit-log absent → returns (False, "no-audit-log", {"drifts": []})
          for fresh-install fail-OPEN.
        - Drift found → returns (True, summary, {"drifts": [...]})
          but does NOT emit (ceo-boot read-only check; emission stays in
          the standalone CLI via `--emit` flag).
    """
    if repo_root is None:
        repo_root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    if audit_log_path is None:
        audit_log_path = _resolve_audit_log()

    class_tiers = _load_class_tiers(repo_root)
    if not class_tiers:
        return False, "no-tier-config", {"drifts": [], "reason": "no-tier-config"}

    if not audit_log_path.is_file():
        return False, "no-audit-log", {"drifts": [], "reason": "no-audit-log"}

    cutoff_iso = (
        datetime.now(timezone.utc) - timedelta(days=window_days)
    ).isoformat().replace("+00:00", "Z")

    counts = _scan_audit_log_for_verdicts(audit_log_path, cutoff_iso)
    drifts = _compute_drift(counts, class_tiers, threshold_bps, min_sample)

    if drifts:
        cls_list = ",".join(str(d["drift_class"]) for d in drifts)
        summary = f"drift detected: {len(drifts)} class(es) — {cls_list}"
        return True, summary, {"drifts": drifts, "window_days": window_days}
    return False, "no drift", {"drifts": [], "window_days": window_days}


def main() -> int:
    # PLAN-106 Wave F.1 — sys.path mutation ONLY at CLI entry, not at
    # module import (matches PLAN-100 Wave 0.5 idempotency-split discipline).
    _here = Path(__file__).resolve()
    _repo_root = _here.parents[2] if "/scripts/" in str(_here) else _here.parents[3]
    _hooks_lib = _repo_root / ".claude" / "hooks"
    if _hooks_lib.is_dir() and str(_hooks_lib) not in sys.path:
        sys.path.insert(0, str(_hooks_lib))

    parser = argparse.ArgumentParser(
        description="ADR-019-AMEND-1 §6 drift detector (7-day rolling FPR > 2%).",
    )
    parser.add_argument("--window-days", type=int, default=_DEFAULT_WINDOW_DAYS)
    parser.add_argument("--threshold-bps", type=int, default=_DEFAULT_THRESHOLD_BPS)
    parser.add_argument("--min-sample", type=int, default=10)
    parser.add_argument("--audit-log", default=None)
    parser.add_argument("--emit", action="store_true",
                        help="Emit confidence_gate_fp_drift_detected on drift")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    log_path = Path(args.audit_log) if args.audit_log else _resolve_audit_log()

    drift, _summary, detail = detect_drift_7d(
        window_days=args.window_days,
        threshold_bps=args.threshold_bps,
        audit_log_path=log_path,
        min_sample=args.min_sample,
        repo_root=_repo_root,
    )

    drifts = detail.get("drifts", [])

    if args.json:
        print(json.dumps({
            "window_days": args.window_days,
            "drifts": drifts,
            "reason": detail.get("reason"),
        }, indent=2))
    else:
        if detail.get("reason") == "no-tier-config":
            print("No tier config — drift detector skipped (fail-OPEN).")
        elif detail.get("reason") == "no-audit-log":
            print("No audit-log present — drift detector skipped (fail-OPEN).")
        else:
            print(_format_human(drifts, args.window_days))

    if args.emit and drifts:
        try:
            from _lib import audit_emit  # type: ignore[import]
            auto_demote_at = (
                datetime.now(timezone.utc) + timedelta(hours=_DEFAULT_AUTO_DEMOTE_COOLING_HOURS)
            ).isoformat().replace("+00:00", "Z")
            for d in drifts:
                audit_emit.emit_confidence_gate_fp_drift_detected(
                    drift_class=str(d["drift_class"]),
                    window_days=int(args.window_days),
                    fpr_bps=int(d["fpr_bps"]),
                    threshold_bps=int(args.threshold_bps),
                    sample_n=int(d["sample_n"]),
                    auto_demote_at=auto_demote_at,
                    agent_name="check-confidence-gate-drift",
                    source="periodic",
                    session_id="",
                    project=str(_repo_root),
                )
        except Exception as e:
            sys.stderr.write(
                f"[check-confidence-gate-drift] emit failed: {type(e).__name__}: {e}\n"
            )

    return 0  # drift is observational, NOT a CI failure


if __name__ == "__main__":
    sys.exit(main())
