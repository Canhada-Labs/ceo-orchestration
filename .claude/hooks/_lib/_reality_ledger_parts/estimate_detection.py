"""Reality ledger: estimate detection."""

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

def detect_estimate_drift(
    *,
    repo_root: Path,
    plan_files: Optional[List[Path]] = None,
    calibration_csv: Optional[Path] = None,
    git_log_index: Optional[Dict[str, List[Tuple[str, str, bool]]]] = None,
    status_done_transitions: Optional[Dict[str, Tuple[str, str]]] = None,
    audit_emit_module: Optional[Any] = None,
    session_id: str = "",
    project: str = "",
    emit_audit: bool = False,
) -> List[Dict[str, Any]]:
    """Detector #7 — estimate-drift on plan close-outs.

    PLAN-078 Wave 2. Pure function (no global state mutation outside of
    caller-supplied calibration_csv path). Test-friendly:

      - ``plan_files`` override targets a specific subset
      - ``calibration_csv`` override redirects CSV writes (test isolation)
      - ``git_log_index`` override skips real git calls (mock injection;
        used to compute GPG-signed commit count)
      - ``status_done_transitions`` mocks the per-plan ``status: done``
        transition commit (rel_path -> (sha, committer_iso)). When None
        AND ``git_log_index`` is provided, the LAST commit in the index
        is used as the transition (back-compat with existing test fixtures).
        When None AND no index, real ``_git_status_done_transition`` runs.
      - ``audit_emit_module`` allows tests to inject a stub for the typed
        Wave 2 emitters (Codex Fix #1).
      - ``session_id`` / ``project`` flow into emitted events.
      - ``emit_audit`` opt-in flag (CLI ``--emit-audit``) gates emission.

    Returns list of finding dicts. Caller (run_detectors) handles
    redaction + render. Codex W1+W2 fix-pack:

      Fix #1: emits via ``emit_estimate_drift_detected`` /
              ``emit_estimate_drift_systematic_bias`` (typed wrappers)
              instead of generic ``_try_emit_finding`` for detector #7.
      Fix #3: bidirectional — flags both overruns (factor > 1.2) and
              underruns (factor < 0.83 ≈ 1/1.2). Severity uses symmetric
              ratio max(f, 1/f). bias_direction reflects either case.
      Fix #5: span computed as ``status: done`` transition committer-date
              minus plan ``created`` field (NOT first/last edit author-date
              from arbitrary file history). Skips plans whose transition
              cannot be located OR whose span ≤ 0h.
    """
    findings: List[Dict[str, Any]] = []
    if _detect_07_disabled():
        return findings  # bypass

    plans_dir = repo_root / ".claude" / "plans"
    if not plans_dir.exists():
        return findings

    if plan_files is None:
        plan_files = [
            p for p in sorted(plans_dir.glob("PLAN-*.md"))
            if p.is_file() and not _is_excluded(p, repo_root=repo_root)
        ]

    # git_log_index is still used for GPG-signed-commit count regardless
    # of the new transition-commit logic.
    if git_log_index is None and status_done_transitions is None:
        git_log_index = _git_log_paths(repo_root)
    if git_log_index is None:
        git_log_index = {}

    csv_path = calibration_csv or (
        repo_root / ".claude" / "scripts" / "local" / "calibration-history.csv"
    )

    drift_findings_for_summary: List[Dict[str, Any]] = []
    run_iso = _now_iso8601()

    for f in plan_files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        rel = _to_repo_rel(f)
        plan_id_match = _PLAN_FILE_RE.match(f.name)
        if not plan_id_match:
            continue
        plan_id = f"PLAN-{plan_id_match.group(1)}"

        status = _extract_top_level_field(text, "status") or ""
        if status.strip().lower() != "done":
            continue  # detector only fires on close-outs

        est_block = _parse_estimate_block(text)
        compute_raw = est_block.get("compute_hours", "")
        owner_raw = est_block.get("owner_physical_min", "")
        if not compute_raw and not owner_raw:
            continue  # plan has no estimate to drift against

        compute_pair = _coerce_hours_to_pair(compute_raw)
        owner_pair = _coerce_hours_to_pair(owner_raw)
        if compute_pair is None and owner_pair is None:
            continue

        # `created` is the schema-correct field; fall back to `created_at`
        # for plans authored before PLAN-076/077 cluster (Codex CDX-UNIQUE-06).
        created = _extract_top_level_field(text, "created") or \
            _extract_top_level_field(text, "created_at") or ""

        # Resolve commits (for GPG count) — try multiple path forms.
        plan_rel = rel
        commits = git_log_index.get(plan_rel, [])
        if not commits:
            for alt in (
                rel,
                rel.replace(os.sep, "/"),
                str(f.relative_to(repo_root)).replace(os.sep, "/"),
            ):
                commits = git_log_index.get(alt, []) or commits

        # Codex Fix #5: locate the status:done transition commit.
        transition: Optional[Tuple[str, str]] = None
        if status_done_transitions is not None:
            # Test-injected dict — try multiple path forms (matches the
            # git_log_index multi-key fallback above).
            try:
                rel_to_repo = str(f.relative_to(repo_root)).replace(os.sep, "/")
            except ValueError:
                rel_to_repo = ""
            for key in (
                plan_rel,
                rel.replace(os.sep, "/"),
                rel_to_repo,
            ):
                if key and key in status_done_transitions:
                    transition = status_done_transitions[key]
                    break
        elif commits:
            # Back-compat: when caller injected git_log_index without
            # status_done_transitions (existing test fixtures), use the
            # LAST commit (most-recent) as the transition. This matches
            # the prior end-of-history semantics for those fixtures.
            commits_sorted_for_tx = sorted(commits, key=lambda x: x[1])
            last_sha, last_iso, _ = commits_sorted_for_tx[-1]
            transition = (last_sha, last_iso)
        else:
            # Real run: use the per-plan git helper (committer-date of the
            # commit whose patch added `+status: done`).
            transition = _git_status_done_transition(repo_root, plan_rel)

        if transition is None:
            continue  # no transition evidence; skip silently

        closeout_iso = transition[1]
        try:
            closeout_dt = datetime.fromisoformat(closeout_iso.replace("Z", "+00:00"))
        except ValueError:
            continue
        # Start: plan `created` field (date-midnight UTC).
        start_dt = _parse_created_iso(created)
        if start_dt is None:
            # Fallback: if `created` is missing, use earliest commit's date.
            if commits:
                first_iso = sorted(commits, key=lambda x: x[1])[0][1]
                try:
                    start_dt = datetime.fromisoformat(first_iso.replace("Z", "+00:00"))
                except ValueError:
                    continue
            else:
                continue

        span_hours = (closeout_dt - start_dt).total_seconds() / 3600.0
        if span_hours <= 0:
            # Plan created and closed in same commit (PLAN-072 single-commit
            # closeout pattern) OR clock skew. Skip and breadcrumb.
            sys.stderr.write(
                f"[reality-ledger] {plan_id}: span ≤ 0 "
                f"(created={created} closeout={closeout_iso}); skipped\n"
            )
            continue

        # GPG-signed commit count proxies for owner-physical (signing = Owner ceremony)
        gpg_count = sum(1 for c in (commits or []) if len(c) >= 3 and c[2])

        # Optional manual override
        manual_override_raw = _extract_top_level_field(
            text, "actual_owner_physical_min"
        )
        manual_override: Optional[int] = None
        if manual_override_raw:
            try:
                manual_override = int(float(manual_override_raw))
            except ValueError:
                manual_override = None

        # Owner physical estimate: 5min/GPG ceremony floor + manual override.
        actual_owner_min: float
        if manual_override is not None:
            actual_owner_min = float(max(0, min(10000, manual_override)))
        else:
            actual_owner_min = float(gpg_count * 5)

        # Drift factors. Use mid of estimate range as denominator.
        compute_drift = 1.0
        if compute_pair is not None and span_hours > 0:
            est_mid = (compute_pair[0] + compute_pair[1]) / 2.0
            if est_mid > 0:
                compute_drift = span_hours / est_mid

        owner_drift = 1.0
        if owner_pair is not None and actual_owner_min > 0:
            # Only compute the owner-axis ratio when we have a non-zero
            # actual measurement. ``actual_owner_min == 0`` happens when
            # no GPG-signed commits exist for the plan AND no manual
            # override was set; that's "no signal", not "underrun by
            # 100%". Reporting it as drift would flag every plan that
            # closed without an Owner ceremony — too noisy for advisory.
            est_owner_mid = (owner_pair[0] + owner_pair[1]) / 2.0
            if est_owner_mid > 0:
                owner_drift = actual_owner_min / est_owner_mid

        severity = _drift_severity(compute_drift, owner_drift)
        bias = _classify_bias(
            span_hours,
            compute_pair[0] if compute_pair else 0.0,
            compute_pair[1] if compute_pair else 0.0,
        )

        # Codex Fix #3: bidirectional drift detection — flag when
        # max(factor, 1/factor) >= 1.2 in EITHER axis. Equivalent to:
        # factor > 1.2 (overrun) OR factor < 1/1.2 ≈ 0.833 (underrun).
        def _is_drifted(factor: float) -> bool:
            try:
                af = abs(float(factor))
            except (TypeError, ValueError):
                return False
            if af == 0.0:
                return True  # actual=0 with non-zero estimate → underrun
            ratio = af if af >= 1.0 else 1.0 / af
            return ratio >= 1.2

        if not (_is_drifted(compute_drift) or _is_drifted(owner_drift)):
            continue

        finding = _build_finding(
            detector="estimate_drift",
            severity=severity,
            confidence=0.85,
            claim_source_path=f"{rel}:1",
            expected_evidence=(
                f"compute_hours={compute_raw} owner_physical_min={owner_raw}"
            ),
            actual_evidence=(
                f"span_hours={span_hours:.1f} owner_min~={actual_owner_min:.0f} "
                f"gpg_signed_commits={gpg_count}"
            ),
            advisory_action=(
                "review estimate calibration; populate "
                "actual_owner_physical_min in plan frontmatter for accuracy"
            ),
            extra={
                "plan_id": plan_id,
                "compute_drift_factor": round(compute_drift, 3),
                "owner_drift_factor": round(owner_drift, 3),
                "transition_commit_sha": transition[0],
                "closeout_commit_iso": closeout_iso,
                "gpg_signed_commits": gpg_count,
                "actual_owner_min_estimated": round(actual_owner_min, 1),
                "bias_direction": bias,
                "created_field": created,
            },
        )
        findings.append(finding)
        drift_findings_for_summary.append(finding)

        # Codex Fix #1: emit via typed estimate_drift_detected (NOT
        # generic reality_ledger_finding). Caller's --emit-audit gate
        # is honored. Each emit is best-effort + fail-open.
        if emit_audit:
            _emit_estimate_drift_detected_typed(
                audit_emit_module=audit_emit_module,
                session_id=session_id,
                project=project,
                plan_id=plan_id,
                drift_factor_compute=compute_drift,
                drift_factor_owner=owner_drift,
                severity=severity,
                plan_count_in_run=len(plan_files),
                systematic_bias_direction=bias,
            )

        # CSV append (idempotent — Codex Fix #4 dedup excludes run_iso8601)
        csv_row = ",".join([
            plan_id, run_iso,
            f"{compute_pair[0]:.1f}" if compute_pair else "",
            f"{compute_pair[1]:.1f}" if compute_pair else "",
            f"{span_hours:.2f}",
            f"{owner_pair[0]:.0f}" if owner_pair else "",
            f"{actual_owner_min:.0f}",
            f"{compute_drift:.3f}",
            f"{owner_drift:.3f}",
            severity,
            bias,
        ])
        _append_calibration_csv(csv_path, csv_row)

    # Codex Fix #3: systematic bias tracks BOTH directions independently.
    # N≥5 same-direction medium+ findings → emit recommendation.
    if len(drift_findings_for_summary) >= 5:
        bias_counter: Dict[str, int] = {"underestimate": 0, "overestimate": 0}
        compute_factors_by_dir: Dict[str, List[float]] = {
            "underestimate": [], "overestimate": []
        }
        owner_factors_by_dir: Dict[str, List[float]] = {
            "underestimate": [], "overestimate": []
        }
        for fnd in drift_findings_for_summary:
            ex = fnd.get("_extra", {})
            sev = fnd.get("severity", "low")
            if sev not in ("medium", "high"):
                continue
            bd = ex.get("bias_direction", "")
            if bd in ("underestimate", "overestimate"):
                bias_counter[bd] += 1
                compute_factors_by_dir[bd].append(
                    ex.get("compute_drift_factor", 1.0)
                )
                owner_factors_by_dir[bd].append(
                    ex.get("owner_drift_factor", 1.0)
                )
        # Pick first direction crossing 5 (deterministic by dict insertion order)
        for direction, count in bias_counter.items():
            if count >= 5:
                cf = compute_factors_by_dir[direction]
                of = owner_factors_by_dir[direction]
                avg_compute = sum(cf) / max(1, len(cf))
                avg_owner = sum(of) / max(1, len(of))
                # Append a meta-finding (no claim_source_path; recommendation event)
                findings.append(_build_finding(
                    detector="estimate_drift",
                    severity="high",
                    confidence=0.95,
                    claim_source_path="<recommendation-event>",
                    expected_evidence=f"systematic_{direction}_threshold>=5",
                    actual_evidence=(
                        f"plans_affected={count} avg_compute={avg_compute:.2f}× "
                        f"avg_owner={avg_owner:.2f}×"
                    ),
                    advisory_action=(
                        f"systematic {direction}: re-calibrate estimate baselines"
                    ),
                    extra={
                        "systematic_bias_direction": direction,
                        "plans_affected_count": count,
                        "avg_drift_factor_compute": round(avg_compute, 3),
                        "avg_drift_factor_owner": round(avg_owner, 3),
                        "is_recommendation_event": True,
                    },
                ))
                # Codex Fix #1: emit typed systematic_bias event.
                if emit_audit:
                    _emit_estimate_drift_systematic_bias_typed(
                        audit_emit_module=audit_emit_module,
                        session_id=session_id,
                        project=project,
                        bias_direction=direction,
                        plans_affected_count=count,
                        avg_drift_factor_compute=avg_compute,
                        avg_drift_factor_owner=avg_owner,
                    )
                break

    return findings


# ---------------------------------------------------------------------------
# Codex W1+W2 fix-pack #1 — typed Wave 2 audit emit wrappers
# ---------------------------------------------------------------------------


__all__ = ['detect_estimate_drift']
