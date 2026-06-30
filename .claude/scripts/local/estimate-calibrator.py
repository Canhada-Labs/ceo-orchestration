#!/usr/bin/env python3
"""PLAN-084 AC12b — estimate-calibrator.

Auto-runs over .claude/plans/PLAN-*.md `completed_at` data; emits
per-class median + p90 + variance to:
  .claude/plans/PLAN-084/canonical/calibration-baseline.yaml

Per Owner velocity-thesis (feedback_owner_velocity_thesis.md):
- predicted compute_hours vs actual completion span (close_ts - draft_ts)
- predicted budget_tokens vs actual rollup (via _lib/tokens.py)
- predicted owner_physical_min vs observed GPG commit count

Class buckets:
- audit-class (PLAN-058, PLAN-066, PLAN-084 — large multi-day audits)
- execution-class (PLAN-064..083 — feature execution)
- ceremony-class (closure / status-flip / tag-bump)
- debate-only-class (R1+R2 only, no execution)

PLAN-113 WIRE-DEADMOD: integrates _lib/estimation/pipeline.py Bayesian
posterior (PLAN-088 W6.1) as an optional supplementary section in the
output YAML. The pipeline reads audit-log plan_transition events to derive
estimate accuracy from actual execution data (orthogonal to frontmatter
completeness). When audit-log has no qualifying events, the section is
emitted with plans_observed=0 and the prior defaults.

Add ``--bayesian`` flag to include the Bayesian section (default OFF,
consistent with WIRE-DEADMOD default-OFF posture for new features).

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# PLAN-113 WIRE-DEADMOD — lazy-import the Bayesian estimation pipeline.
# Default-OFF: only runs when --bayesian flag is present. Fail-open: if
# the _lib module is unavailable the script still emits the Stage-1 output.
_ESTIMATION_PIPELINE_AVAILABLE = False
_estimation_pipeline = None

def _try_load_estimation_pipeline() -> None:
    """Import _lib.estimation.pipeline if _lib is on sys.path. Idempotent."""
    global _ESTIMATION_PIPELINE_AVAILABLE, _estimation_pipeline  # noqa: PLW0603
    if _ESTIMATION_PIPELINE_AVAILABLE:
        return
    try:
        # Hooks _lib lives at <repo>/.claude/hooks/_lib; scripts/local is two
        # levels up from _lib, so we climb: local/ -> scripts/ -> .claude/ ->
        # repo root -> .claude/hooks/.
        _this = Path(__file__).resolve()
        hooks_dir = _this.parents[3] / ".claude" / "hooks"
        if str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))
        from _lib.estimation import pipeline as _ep  # type: ignore[import-not-found]
        _estimation_pipeline = _ep
        _ESTIMATION_PIPELINE_AVAILABLE = True
    except Exception:
        pass


_FRONT_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(path: Path) -> Dict:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return {}
    m = _FRONT_RE.match(text)
    if not m:
        return {}
    front = {}
    body = m.group(1)
    for line in body.splitlines():
        if ":" not in line:
            continue
        if line.startswith("  "):
            continue  # skip nested
        key, _, value = line.partition(":")
        front[key.strip()] = value.strip().strip('"').strip("'")
    return front


def parse_iso_date(s: str) -> Optional[datetime]:
    s = s.strip().strip('"').strip("'")
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def classify_plan(plan_path: Path, front: Dict) -> str:
    pid = front.get("id", "")
    title = front.get("title", "").lower()
    tags = front.get("tags", "").lower()
    if "audit" in title or "audit-final" in tags:
        return "audit-class"
    if "ceremony" in title or "closeout" in title:
        return "ceremony-class"
    if "debate" in title or front.get("status", "") == "reviewed":
        return "debate-only-class"
    return "execution-class"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--plans-dir", type=Path, default=Path(".claude/plans/"))
    p.add_argument("--output", type=Path, default=Path(".claude/plans/PLAN-084/canonical/calibration-baseline.yaml"))
    p.add_argument("--n", type=int, default=50, help="Take last N closed plans")
    p.add_argument(
        "--bayesian",
        action="store_true",
        default=False,
        help=(
            "PLAN-113 WIRE-DEADMOD: supplement output with Bayesian posterior "
            "from _lib/estimation/pipeline.py (reads audit-log plan_transition "
            "events). Default OFF — requires audit-log with qualifying events."
        ),
    )
    args = p.parse_args()

    plan_files = []
    for f in args.plans_dir.glob("PLAN-*.md"):
        front = parse_frontmatter(f)
        if front.get("status", "") == "done":
            plan_files.append((f, front))

    plan_files.sort(key=lambda x: x[1].get("id", ""))
    plan_files = plan_files[-args.n:]

    by_class: Dict[str, List[Dict]] = {}
    for path, front in plan_files:
        klass = classify_plan(path, front)
        by_class.setdefault(klass, []).append({
            "path": str(path),
            "id": front.get("id", "?"),
            "estimated_compute_hours": front.get("estimate.compute_hours", ""),
            "estimated_budget_tokens": front.get("budget_tokens", ""),
            "estimated_owner_physical_min": front.get("estimate.owner_physical_min", ""),
            "created": front.get("created", ""),
            "completed_at": front.get("completed_at", ""),
            "status": front.get("status", ""),
        })

    # Per-class median bias estimator (limited by frontmatter quality)
    stats: Dict[str, Dict] = {}
    for klass, entries in by_class.items():
        stats[klass] = {
            "plan_count": len(entries),
            "plan_ids": [e["id"] for e in entries[:10]],
            "estimate_completeness": sum(1 for e in entries if e.get("estimated_compute_hours")) / len(entries) if entries else 0,
            "completed_at_coverage": sum(1 for e in entries if e.get("completed_at")) / len(entries) if entries else 0,
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as out:
        out.write("# AC12b — calibration baseline\n")
        out.write(f"# Generated by estimate-calibrator.py\n")
        out.write(f"\n")
        out.write(f"total_plans_analyzed: {len(plan_files)}\n")
        out.write(f"\n")
        out.write("per_class:\n")
        for klass, s in sorted(stats.items()):
            out.write(f"  {klass}:\n")
            out.write(f"    plan_count: {s['plan_count']}\n")
            out.write(f"    estimate_completeness: {s['estimate_completeness']:.2%}\n")
            out.write(f"    completed_at_coverage: {s['completed_at_coverage']:.2%}\n")
            out.write(f"    sample_plan_ids: [{', '.join(s['plan_ids'])}]\n")

        out.write(f"\n")
        out.write("methodology_note: |\n")
        out.write("  Stage 1 (this baseline): plan_count + frontmatter completeness per class.\n")
        out.write("  Stage 2 (PLAN-085+): joins with _lib/tokens.py rollup + commit timestamps\n")
        out.write("  to compute true predicted/actual ratios. Requires _lib/tokens.py\n")
        out.write("  per-plan attribution which is currently sketchy per Wave C.5 audit.\n")
        out.write("\n")
        out.write("known_bias_baseline:\n")
        out.write("  source: feedback_owner_velocity_thesis.md\n")
        out.write("  claim: CEO over-estimates by 1-2 orders of magnitude (weeks-vs-hours)\n")
        out.write("  status: documented_but_not_quantified\n")
        out.write("  evolution_roadmap_item: PLAN-085-estimate-calibration-quantification\n")

    # PLAN-113 WIRE-DEADMOD — optional Bayesian posterior section.
    # Runs estimation/pipeline.py against the audit-log. Default-OFF.
    if args.bayesian:
        _try_load_estimation_pipeline()
        if _ESTIMATION_PIPELINE_AVAILABLE and _estimation_pipeline is not None:
            try:
                # Pass a sidecar YAML path so pipeline.run() does NOT
                # overwrite the main calibration-baseline.yaml output.
                # The Bayesian section is appended below directly.
                _bayes_sidecar = args.output.with_suffix(".bayesian.yaml")
                bayes_summary: Dict[str, Any] = _estimation_pipeline.run(
                    baseline_yaml_path=_bayes_sidecar,
                    trigger_source="plan_close_hook",
                )
                with args.output.open("a", encoding="utf-8") as out:
                    out.write("\n")
                    out.write("# PLAN-113 WIRE-DEADMOD — Bayesian posterior\n")
                    out.write("# Source: _lib/estimation/pipeline.py (audit-log plan_transition events)\n")
                    out.write("bayesian_posterior:\n")
                    out.write(f"  plans_observed: {bayes_summary.get('plans_observed', 0)}\n")
                    out.write(f"  successes: {bayes_summary.get('successes', 0)}\n")
                    out.write(f"  failures: {bayes_summary.get('failures', 0)}\n")
                    out.write(f"  posterior_alpha: {bayes_summary.get('posterior_alpha', 0)}\n")
                    out.write(f"  posterior_beta: {bayes_summary.get('posterior_beta', 0)}\n")
                    out.write(f"  posterior_mean_basis_points: {bayes_summary.get('posterior_mean_basis_points', 0)}\n")
                    out.write(f"  trigger_source: {bayes_summary.get('trigger_source', 'plan_close_hook')}\n")
                print(
                    f"Bayesian posterior: {bayes_summary.get('plans_observed', 0)} qualifying "
                    f"plan_transition events; posterior_mean="
                    f"{bayes_summary.get('posterior_mean_basis_points', 0)}/1000"
                )
            except Exception as exc:
                print(f"Bayesian pipeline failed (non-fatal): {exc}", file=sys.stderr)
        else:
            print(
                "Bayesian pipeline unavailable (--bayesian flag set but "
                "_lib/estimation/pipeline.py could not be imported).",
                file=sys.stderr,
            )

    print(f"Analyzed {len(plan_files)} plans across {len(stats)} classes")
    print(f"Output: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
