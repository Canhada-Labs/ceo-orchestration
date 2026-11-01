"""Reality ledger: dispatch."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Tuple

from .constants import *  # shared declaration defaults

def _run_with_timeout(
    fn,
    *,
    timeout_ms: int,
    detector_name: str,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Run a detector with ITIMER guard. Returns (findings, error_str)."""
    budget_s = max(0.001, timeout_ms / 1000.0)
    prev = _install_itimer_guard(budget_s)
    try:
        findings = fn()
        return findings, None
    except ScanBudgetExceeded:
        return [], f"detector {detector_name} timed out after {timeout_ms}ms"
    except Exception as exc:  # pragma: no cover - safety net
        return [], f"detector {detector_name} raised {exc.__class__.__name__}: {exc}"
    finally:
        _clear_itimer_guard(prev)


def run_detectors(
    *,
    repo_root: Path,
    detector_names: Optional[List[str]] = None,
    timeout_ms: int = DEFAULT_DETECTOR_TIMEOUT_MS,
    audit_log_path: Optional[Path] = None,
    emit_audit: bool = False,
    audit_emit_module: Optional[Any] = None,
    session_id: str = "",
    project: str = "",
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Run requested detectors; returns (findings, errors).

    Codex W1+W2 fix-pack #1: detector #7 (estimate_drift) accepts
    ``emit_audit`` + identifier args so it can fire its TYPED emitters
    (``emit_estimate_drift_detected`` / ``emit_estimate_drift_systematic_bias``)
    inline. Other detectors continue to use the generic
    ``_try_emit_finding`` path (handled by the CLI loop).
    """
    selected = detector_names or sorted(DETECTOR_REGISTRY.keys())
    findings: List[Dict[str, Any]] = []
    errors: List[str] = []

    detector_fns = {
        "runtime_read_missing": lambda: detect_runtime_read_missing(
            repo_root=repo_root,
        ),
        "installable_claim_drift": lambda: detect_installable_claim_drift(
            repo_root=repo_root,
        ),
        "model_assignment_divergence": lambda: detect_model_assignment_divergence(
            repo_root=repo_root,
            audit_log_path=audit_log_path,
        ),
        "enforcement_commit_unpopulated": lambda: detect_enforcement_commit_unpopulated(
            repo_root=repo_root,
        ),
        "audit_action_phantom": lambda: detect_audit_action_phantom(
            repo_root=repo_root,
        ),
        # PLAN-078 Wave 2 — Reality Ledger detector #7 (estimate-drift).
        # Codex Fix #1: emit-audit + module + identifiers flow inward so the
        # detector can call its TYPED emit wrappers (NOT generic).
        "estimate_drift": lambda: detect_estimate_drift(
            repo_root=repo_root,
            emit_audit=emit_audit,
            audit_emit_module=audit_emit_module,
            session_id=session_id,
            project=project,
        ),
    }

    for name in selected:
        if name not in detector_fns:
            errors.append(f"unknown detector: {name}")
            continue
        f, err = _run_with_timeout(
            detector_fns[name],
            timeout_ms=timeout_ms,
            detector_name=name,
        )
        if err:
            errors.append(err)
        findings.extend(f)
    return findings, errors


def filter_by_severity(findings: List[Dict[str, Any]], min_severity: str) -> List[Dict[str, Any]]:
    if min_severity not in _SEVERITY_ORDER:
        return findings
    threshold = _SEVERITY_ORDER[min_severity]
    return [f for f in findings if _SEVERITY_ORDER.get(f.get("severity", "low"), 0) >= threshold]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="reality-ledger",
        description=(
            "Adaptive Execution Kernel claim-vs-evidence detector "
            "(advisory-only; never blocks)."
        ),
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json", "jsonl"),
        default="markdown",
    )
    parser.add_argument(
        "--detector",
        action="append",
        default=None,
        help="Run only this detector (repeatable). Default: all 5.",
    )
    parser.add_argument(
        "--severity",
        choices=_SEVERITIES,
        default="low",
        help="Minimum severity to emit (low/medium/high). Default: low.",
    )
    parser.add_argument(
        "--detector-timeout-ms",
        type=int,
        default=DEFAULT_DETECTOR_TIMEOUT_MS,
        help=f"Per-detector timeout. Default: {DEFAULT_DETECTOR_TIMEOUT_MS}.",
    )
    parser.add_argument(
        "--since",
        default=None,
        help=(
            "Time window for audit-log observations (e.g. '30d'). "
            "Reserved for Detector #3 in Phase 4."
        ),
    )
    parser.add_argument(
        "--audit-log",
        default=None,
        help=(
            "Path to audit-log.jsonl. Detector #3 only runs when supplied."
        ),
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file (default: stdout).",
    )
    parser.add_argument(
        "--repo-root",
        default=str(_REPO_ROOT),
        help="Repository root path (test override).",
    )
    parser.add_argument(
        "--emit-audit",
        action="store_true",
        help=(
            "Best-effort audit emit per finding. No-op if "
            "reality_ledger_finding action is not yet registered."
        ),
    )

    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    if not repo_root.exists():
        sys.stderr.write(f"[reality-ledger] repo-root not found: {repo_root}\n")
        return 2

    audit_log_path = Path(args.audit_log).resolve() if args.audit_log else None

    t0 = time.perf_counter()
    findings, errors = run_detectors(
        repo_root=repo_root,
        detector_names=args.detector,
        timeout_ms=args.detector_timeout_ms,
        audit_log_path=audit_log_path,
        # Codex W1+W2 fix-pack #1: detector #7 emits via typed wrappers
        # inline; flow emit_audit + identifiers down so they reach it.
        emit_audit=args.emit_audit,
        session_id=os.environ.get("CEO_SESSION_ID", ""),
        project=os.environ.get("CEO_PROJECT", ""),
    )
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    if errors and not findings:
        # detector internal error path with no salvage
        for e in errors:
            sys.stderr.write(f"[reality-ledger] {e}\n")
        return 2

    if errors:
        # partial run — log errors but continue
        for e in errors:
            sys.stderr.write(f"[reality-ledger] {e}\n")

    findings = filter_by_severity(findings, args.severity)

    # Best-effort audit emit (advisory) — applies to detectors #1-#6 ONLY.
    # Codex W1+W2 fix-pack #1: detector #7 (estimate_drift) already emitted
    # via typed wrappers inline; emitting again via generic
    # ``reality_ledger_finding`` would double-record AND defeat the typed
    # action contract. Skip detector-7 findings here.
    if args.emit_audit:
        for f in findings:
            if f.get("detector") == "estimate_drift":
                continue  # typed emit already fired inside detect_estimate_drift
            _try_emit_finding(f, finding_count_in_run=len(findings))

    # Render
    if args.format == "markdown":
        rendered = render_findings_markdown(findings)
    elif args.format == "json":
        rendered = render_findings_json(findings)
    else:  # jsonl
        rendered = render_findings_jsonl(findings)

    # Append run metadata as a markdown footer (only for markdown)
    if args.format == "markdown":
        rendered = (
            rendered
            + f"\n_run_id: `{uuid.uuid4()}`  ·  duration_ms: `{elapsed_ms}`_\n"
        )

    if args.output:
        try:
            Path(args.output).write_text(rendered, encoding="utf-8")
        except OSError as exc:
            sys.stderr.write(f"[reality-ledger] cannot write output: {exc}\n")
            return 2
    else:
        sys.stdout.write(rendered)
        if not rendered.endswith("\n"):
            sys.stdout.write("\n")

    return 0



__all__ = ['_run_with_timeout', 'run_detectors', 'filter_by_severity', 'main']
