"""PLAN-088 W1.3 / W6.1 — top-level estimation calibrator orchestrator.

Consumes the audit-log emit stream (or a windowed slice), classifies
closed plans by estimate accuracy, computes Bayesian-refined posterior
via `_lib.estimation.bayesian`, and writes the refreshed
`calibration-baseline.yaml` artifact.

Fires `estimate_calibrator_pipeline_run` audit-emit on each invocation
per AC12 closure contract.

Stdlib-only. Python >= 3.9.

Public API:
  run(audit_log_path, baseline_yaml_path, trigger_source) -> dict
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_LIB_DIR = Path(__file__).resolve().parent.parent
if str(_LIB_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR.parent))

# Conditional imports so the module loads in adopter environments where
# audit_emit may be partially staged. Pipeline fails-open per CLAUDE.md
# hook discipline.
try:
    from _lib import audit_emit as _audit_emit
except Exception:  # pragma: no cover — defensive
    _audit_emit = None  # type: ignore[assignment]

from _lib.estimation import bayesian


def _read_audit_log_iter(audit_log_path: Path):
    """Yield each event dict from the audit-log JSONL. Best-effort."""
    if not audit_log_path.exists():
        return
    try:
        with audit_log_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    except OSError:
        return


def _collect_closed_plans(events) -> List[Dict[str, float]]:
    """Extract estimated_lower / upper / actual hour tuples from
    plan_transition events with from_status=executing + to_status=done.

    Returns a list of dicts ready for bayesian.batch_update_from_plans().
    """
    out: List[Dict[str, float]] = []
    for e in events:
        if e.get("action") != "plan_transition":
            continue
        if e.get("from_status") != "executing":
            continue
        if e.get("to_status") != "done":
            continue
        # Estimated bounds + actual carried on the plan_transition event
        # via PLAN-084 Wave 0.5 schema (frontmatter `compute_hours`
        # tuple + commit timestamp delta).
        lo = e.get("estimated_hours_lower", e.get("compute_hours_lower", -1))
        up = e.get("estimated_hours_upper", e.get("compute_hours_upper", -1))
        act = e.get("actual_hours", e.get("wallclock_hours", -1))
        try:
            lo_f = float(lo)
            up_f = float(up)
            act_f = float(act)
        except (TypeError, ValueError):
            continue
        if lo_f < 0 or up_f < 0 or act_f < 0:
            continue
        out.append({
            "estimated_hours_lower": lo_f,
            "estimated_hours_upper": up_f,
            "actual_hours": act_f,
        })
    return out


def _write_baseline_yaml(
    baseline_path: Path,
    posterior_alpha: int,
    posterior_beta: int,
    plans_observed: int,
    successes: int,
    failures: int,
) -> bool:
    """Write minimal YAML baseline (stdlib-only emit, no third-party libs).

    Schema:
        prior_alpha: <int>
        prior_beta:  <int>
        posterior_alpha: <int>
        posterior_beta:  <int>
        posterior_mean_basis_points: <int 0..1000>
        plans_observed: <int>
        successes: <int>
        failures: <int>
    """
    try:
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        mean_bp = bayesian.posterior_mean_basis_points(posterior_alpha, posterior_beta)
        prior_a, prior_b = bayesian._init_priors()
        body = (
            "# PLAN-088 W6.1 calibration baseline (auto-generated).\n"
            "prior_alpha: %d\n"
            "prior_beta: %d\n"
            "posterior_alpha: %d\n"
            "posterior_beta: %d\n"
            "posterior_mean_basis_points: %d\n"
            "plans_observed: %d\n"
            "successes: %d\n"
            "failures: %d\n"
            % (prior_a, prior_b, posterior_alpha, posterior_beta, mean_bp,
               plans_observed, successes, failures)
        )
        baseline_path.write_text(body, encoding="utf-8")
        return True
    except OSError:
        return False


def run(
    audit_log_path: Optional[Path] = None,
    baseline_yaml_path: Optional[Path] = None,
    trigger_source: str = "nightly_cron",
    session_id: str = "",
    project: str = "",
) -> Dict[str, Any]:
    """Run the calibrator pipeline.

    Returns a dict with the posterior + plan-count summary. Fires
    `emit_estimate_calibrator_pipeline_run` per AC12 closure contract.

    trigger_source ∈ {nightly_cron, plan_close_hook} per W1.3 spec.

    Args:
        audit_log_path: defaults to
            ~/.claude/projects/ceo-orchestration/audit-log.jsonl
        baseline_yaml_path: defaults to
            .claude/plans/PLAN-084/canonical/calibration-baseline.yaml
        trigger_source: nightly_cron OR plan_close_hook
        session_id: passed through to audit emit
        project: passed through to audit emit
    """
    if audit_log_path is None:
        home = Path(os.path.expanduser("~"))
        audit_log_path = home / ".claude" / "projects" / "ceo-orchestration" / "audit-log.jsonl"
    if baseline_yaml_path is None:
        repo_root = Path.cwd()
        baseline_yaml_path = (
            repo_root / ".claude" / "plans" / "PLAN-084" / "canonical"
            / "calibration-baseline.yaml"
        )

    events = list(_read_audit_log_iter(audit_log_path))
    plans = _collect_closed_plans(events)
    posterior_alpha, posterior_beta, successes, failures = (
        bayesian.batch_update_from_plans(plans)
    )

    write_ok = _write_baseline_yaml(
        baseline_yaml_path, posterior_alpha, posterior_beta,
        len(plans), successes, failures,
    )

    summary = {
        "trigger_source": trigger_source,
        "plans_observed": len(plans),
        "successes": successes,
        "failures": failures,
        "posterior_alpha": posterior_alpha,
        "posterior_beta": posterior_beta,
        "posterior_mean_basis_points": bayesian.posterior_mean_basis_points(
            posterior_alpha, posterior_beta
        ),
        "baseline_written": write_ok,
    }

    # Fire audit emit (best-effort; never raise)
    if _audit_emit is not None and hasattr(_audit_emit, "emit_estimate_calibrator_pipeline_run"):
        try:
            _audit_emit.emit_estimate_calibrator_pipeline_run(
                session_id=session_id,
                pipeline_phase="completed",
                plans_consumed=len(plans),
                posterior_alpha_basis_points=posterior_alpha,
                posterior_beta_basis_points=posterior_beta,
                trigger_source=trigger_source,
                project=project,
            )
        except Exception:  # pragma: no cover — defensive
            pass

    return summary
