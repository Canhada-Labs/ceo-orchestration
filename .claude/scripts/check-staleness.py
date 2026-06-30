#!/usr/bin/env python3
"""Check framework artifacts for staleness — advisory, never blocks.

PLAN-004 Phase 6. Walks plans, ADRs, and benchmarks; emits findings
per the observability-and-ops skill contract: `{status, impact,
remediation}` per item.

## What is checked

| Artifact | Rule | Status |
|---|---|---|
| Plan `executing` for > 30d with no commit reference | unhealthy |
| Plan `executing` for > 14d | degraded |
| Plan `draft` for > 30d | degraded |
| ADR `proposed` for > 30d | degraded |
| Benchmark skill last run > 14d | degraded |
| Skill SKILL.md modified but no benchmark run since | degraded |
| Plan `executing` >24h without commit (PLAN-065 §4.4.B mode 8.2) | stranded |
| Plan `reviewed` >7d without dispatch (PLAN-065 §4.4.B mode 8.1) | stranded |

## Usage

    python3 .claude/scripts/check-staleness.py
    python3 .claude/scripts/check-staleness.py --json
    python3 .claude/scripts/check-staleness.py --strict
    python3 .claude/scripts/check-staleness.py --repo-root <path>

Exit code: always 0 (advisory) by default. Use `--strict` to return 1
on any `unhealthy` finding OR any stranded-plan finding (mode 8.1 or
mode 8.2 per PLAN-065 §4.4.B). The `--strict` output prefixes the
classic findings with a mode-classified stranded section.

## Stdlib-only

Uses filesystem walks + file mtime + regex frontmatter. No deps.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Optional import: stranded detector lives in check_plan_edit.py (hooks).
# Keep the script self-contained — fall back to advisory mode if the
# hook module can't be imported (e.g. running under a different repo
# layout). Stranded section just becomes empty in that case.
_HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

_STRANDED_AVAILABLE = False
_cpe = None  # type: ignore[assignment]
try:
    import check_plan_edit as _cpe_canonical  # noqa: E402

    if hasattr(_cpe_canonical, "detect_stranded"):
        _cpe = _cpe_canonical
        _STRANDED_AVAILABLE = True
except Exception:  # pragma: no cover
    _cpe_canonical = None  # type: ignore[assignment]

if not _STRANDED_AVAILABLE:
    # Canonical hook lacks detect_stranded yet — fall back to the
    # PLAN-065 staged-patches `.new` file so the CLI surfaces stranded
    # plans before the canonical ceremony lands. Once the staged patch
    # is promoted to canonical, this fallback is silently bypassed.
    _STAGED = (
        Path(__file__).resolve().parent.parent / "plans" / "PLAN-065"
        / "staged-patches" / "phase-4-b-stranded" / "check_plan_edit.py.new"
    )
    if _STAGED.is_file():
        try:
            from importlib.machinery import SourceFileLoader
            import importlib.util as _ilu
            _loader = SourceFileLoader("check_plan_edit_staged", str(_STAGED))
            _spec = _ilu.spec_from_loader("check_plan_edit_staged", _loader)
            if _spec is not None:
                _mod = _ilu.module_from_spec(_spec)
                # Register in sys.modules BEFORE exec_module so
                # dataclass field-type introspection (Py3.9) can
                # resolve the module's namespace.
                sys.modules["check_plan_edit_staged"] = _mod
                _loader.exec_module(_mod)
                _cpe = _mod
                _STRANDED_AVAILABLE = True
        except Exception:  # pragma: no cover
            pass


def _parse_iso_date(s: str) -> Optional[datetime]:
    """Parse ISO 8601 date; return None on failure."""
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            d = datetime.strptime(s.strip(), fmt)
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return d
        except ValueError:
            continue
    return None


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(text: str) -> Dict[str, str]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    result: Dict[str, str] = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if ":" in line and not line.startswith("#"):
            k, _, v = line.partition(":")
            result[k.strip()] = v.strip()
    return result


# PLAN-138 Wave A — inline `[NEEDS CLARIFICATION]` marker detection.
# A LIVE marker is the actionable colon-question-bracket form appearing
# OUTSIDE fenced code blocks and inline-backtick spans. Definitional /
# illustrative uses (backtick-wrapped or fenced) are EXEMPT, and the
# PLAN-SCHEMA.md definition file is skipped wholesale (the S239 self-trip
# class). The regex is anchored, bounded ([^\]]+ stops at the first
# `]`), and linear-time — no nested/unbounded quantifiers.
_CLARIFICATION_MARKER_RE = re.compile(r"\[NEEDS CLARIFICATION:[^\]]+\]")
# A ```fence``` line opens/closes a fenced code block (``` or ~~~, any
# trailing info-string). We only need line-granular fence tracking.
_FENCE_OPEN_RE = re.compile(r"^\s*(```+|~~~+)")


def _strip_code_spans(text: str) -> str:
    """Return ``text`` with fenced code blocks and inline-backtick spans
    blanked out, so a marker living inside either is not counted.

    Fail-open: on any unexpected input the worst case is that a span is
    left intact (a possible false WARNING), never a crash and never a
    false-negative that hides a real LIVE marker outside code.
    """
    out_lines = []  # type: List[str]
    in_fence = False
    for line in text.splitlines():
        if _FENCE_OPEN_RE.match(line):
            # Toggle fence state; blank the fence line itself.
            in_fence = not in_fence
            out_lines.append("")
            continue
        if in_fence:
            out_lines.append("")
            continue
        # Blank inline-backtick spans on this line. Match the longest
        # run of backticks as the delimiter (CommonMark code-span rule),
        # collapsing `code` / ``co`de`` to spaces. Anchored + bounded.
        out_lines.append(re.sub(r"(`+)(?:.*?)\1", " ", line))
    return "\n".join(out_lines)


def live_clarification_markers(text: str, is_definition_file: bool = False) -> int:
    """Count LIVE `[NEEDS CLARIFICATION: ...]` markers in ``text``.

    LIVE = actionable colon-question-bracket form OUTSIDE fenced code
    blocks and inline-backtick spans. The PLAN-SCHEMA.md definition file
    passes ``is_definition_file=True`` and always returns 0. Fully
    advisory + fail-open: any error returns 0 (degrade to no finding).
    """
    if is_definition_file:
        return 0
    try:
        stripped = _strip_code_spans(text)
        return len(_CLARIFICATION_MARKER_RE.findall(stripped))
    except Exception:  # pragma: no cover - fail-open
        return 0


def _is_plan_schema_file(plan_file: Path) -> bool:
    """True when ``plan_file`` is the §14 definition file (excluded)."""
    return plan_file.name == "PLAN-SCHEMA.md"


def _check_plans(repo: Path, now: datetime) -> List[Dict[str, Any]]:
    findings = []
    plans_dir = repo / ".claude" / "plans"
    if not plans_dir.is_dir():
        return findings
    for plan_file in sorted(plans_dir.glob("PLAN-*.md")):
        try:
            text = plan_file.read_text(encoding="utf-8")
        except OSError:
            continue
        fm = _parse_frontmatter(text)
        status = fm.get("status", "").strip()
        plan_id = fm.get("id", plan_file.stem)

        created = _parse_iso_date(fm.get("created", ""))
        age_days = (now - created).days if created else 0

        related_commits = fm.get("related_commits", "")
        has_commits = bool(related_commits.strip("[] ").strip())

        if status == "executing":
            if age_days > 30 and not has_commits:
                findings.append({
                    "artifact": "plan",
                    "id": plan_id,
                    "path": str(plan_file.relative_to(repo)),
                    "status": "unhealthy",
                    "rule": "plan_executing_abandoned_candidate",
                    "value_days": age_days,
                    "threshold_days": 30,
                    "impact": "plan claims to be executing but has no related commits — abandonment candidate",
                    "remediation": "either commit referencing this plan, update status to 'abandoned' with reason, or delete",
                })
            elif age_days > 14:
                findings.append({
                    "artifact": "plan",
                    "id": plan_id,
                    "path": str(plan_file.relative_to(repo)),
                    "status": "degraded",
                    "rule": "plan_executing_stalled",
                    "value_days": age_days,
                    "threshold_days": 14,
                    "impact": "plan has been executing for >14 days without transition",
                    "remediation": "ship next phase or roll to 'done'/'abandoned'",
                })
        elif status == "draft" and age_days > 30:
            findings.append({
                "artifact": "plan",
                "id": plan_id,
                "path": str(plan_file.relative_to(repo)),
                "status": "degraded",
                "rule": "plan_draft_stale",
                "value_days": age_days,
                "threshold_days": 30,
                "impact": "draft plan has sat uncommitted for >30 days",
                "remediation": "review plan; move to 'reviewed' or 'abandoned'",
            })

        # PLAN-138 Wave A — advisory unresolved-clarification markers.
        # Skip the PLAN-SCHEMA.md definition file (it documents the token).
        n_markers = live_clarification_markers(
            text, is_definition_file=_is_plan_schema_file(plan_file)
        )
        if n_markers > 0:
            findings.append({
                "artifact": "plan",
                "id": plan_id,
                "path": str(plan_file.relative_to(repo)),
                "status": "degraded",
                "rule": "plan_unresolved_clarification",
                "value": n_markers,
                # value_days/threshold_days kept (0) so the human-readable
                # CLI printer (which indexes them directly) stays crash-free.
                "value_days": 0,
                "threshold_days": 0,
                "impact": (
                    "plan carries %d unresolved [NEEDS CLARIFICATION] "
                    "marker(s) — open ambiguity not yet folded into the plan"
                    % n_markers
                ),
                "remediation": "/spawn spec-clarify",
            })
    return findings


def _check_adrs(repo: Path, now: datetime) -> List[Dict[str, Any]]:
    findings = []
    adr_dir = repo / ".claude" / "adr"
    if not adr_dir.is_dir():
        return findings
    for adr_file in sorted(adr_dir.glob("ADR-*.md")):
        try:
            text = adr_file.read_text(encoding="utf-8")
        except OSError:
            continue
        # Extract status from first "## Status: XXX" line
        m = re.search(r"^##\s*Status:\s*(\w+)", text, re.MULTILINE)
        if not m:
            continue
        status = m.group(1).upper()

        # Age from file mtime
        mtime = datetime.fromtimestamp(adr_file.stat().st_mtime, tz=timezone.utc)
        age_days = (now - mtime).days

        if status == "PROPOSED" and age_days > 30:
            findings.append({
                "artifact": "adr",
                "id": adr_file.stem,
                "path": str(adr_file.relative_to(repo)),
                "status": "degraded",
                "rule": "adr_proposed_stale",
                "value_days": age_days,
                "threshold_days": 30,
                "impact": "architectural decision has been PROPOSED >30 days — decision avoidance",
                "remediation": "accept, reject, or supersede; update Status line",
            })
    return findings


def _check_benchmarks(repo: Path, now: datetime) -> List[Dict[str, Any]]:
    findings = []
    bench_dir = repo / ".claude" / "benchmarks"
    if not bench_dir.is_dir():
        return findings
    for y in sorted(bench_dir.glob("*.yaml")):
        mtime = datetime.fromtimestamp(y.stat().st_mtime, tz=timezone.utc)
        age_days = (now - mtime).days
        if age_days > 14:
            findings.append({
                "artifact": "benchmark",
                "id": y.stem,
                "path": str(y.relative_to(repo)),
                "status": "degraded",
                "rule": "benchmark_last_touched_stale",
                "value_days": age_days,
                "threshold_days": 14,
                "impact": "benchmark config hasn't been re-touched in >14 days (proxy for last run)",
                "remediation": "run .claude/scripts/run-skill-benchmark.py against this benchmark",
            })
    return findings


def _check_stranded(repo: Path, now: datetime) -> List[Dict[str, Any]]:
    """PLAN-065 §4.4.B — surface stranded plans (modes 8.1 + 8.2).

    Reuses ``check_plan_edit.detect_stranded`` so the CLI and the
    hook share a single detection implementation. Each result is
    rendered as an additional staleness finding with status
    ``"stranded"`` (a new value distinct from healthy/degraded/
    unhealthy — collapsed to ``unhealthy`` in the overall status
    aggregator only when ``--strict`` is honored by the caller).
    """
    findings: List[Dict[str, Any]] = []
    if not _STRANDED_AVAILABLE:
        return findings
    plans_dir = repo / ".claude" / "plans"
    if not plans_dir.is_dir():
        return findings
    try:
        now_unix = int(now.timestamp())
        strandeds = _cpe.detect_stranded(
            plans_dir, now_unix=now_unix, repo_root=repo,
        )
    except Exception:  # pragma: no cover
        return findings
    for s in strandeds:
        if s.mode == "8.2":
            rule = "plan_stranded_paperclip_in_progress"
            threshold = 1
            impact = (
                "plan claims to be executing but no commit has touched it "
                "in >24h — paperclip-style stranded run (mode 8.2)"
            )
            remediation = (
                "either ship a commit, mark `## Abandonment reason` and "
                "transition to abandoned, or investigate dispatched-run failure"
            )
        elif s.mode == "8.1":
            rule = "plan_stranded_dispatch_failed"
            threshold = 7
            impact = (
                "plan parked in 'reviewed' >7d with no transition to "
                "executing — likely dispatch failed silently (mode 8.1)"
            )
            remediation = (
                "wake Owner: either dispatch executing run or "
                "abandon/refuse the plan"
            )
        else:  # pragma: no cover — defensive
            rule = "plan_stranded_unknown"
            threshold = 0
            impact = "stranded plan in unknown mode"
            remediation = "investigate"
        try:
            rel = str(Path(s.file_path).resolve().relative_to(repo))
        except (OSError, ValueError):
            rel = s.file_path
        findings.append({
            "artifact": "plan",
            "id": s.plan_id,
            "path": rel,
            "status": "stranded",
            "rule": rule,
            "value_days": s.age_days,
            "threshold_days": threshold,
            "mode": s.mode,
            "impact": impact,
            "remediation": remediation,
        })
    return findings


def check_staleness(repo: Path, now: Optional[datetime] = None) -> Dict[str, Any]:
    """Return a full staleness report."""
    now = now or datetime.now(timezone.utc)
    findings = []
    findings.extend(_check_plans(repo, now))
    findings.extend(_check_adrs(repo, now))
    findings.extend(_check_benchmarks(repo, now))
    findings.extend(_check_stranded(repo, now))

    overall = "healthy"
    if any(f["status"] == "unhealthy" for f in findings):
        overall = "unhealthy"
    elif any(f["status"] == "stranded" for f in findings):
        # Stranded is informational-only in default output; CLI maps
        # it to exit-1 when --strict is set (handled in _cli).
        overall = "stranded"
    elif any(f["status"] == "degraded" for f in findings):
        overall = "degraded"

    impact = "NONE"
    if overall == "unhealthy":
        impact = "at least one artifact is in a failed state — investigate"
    elif overall == "stranded":
        impact = (
            "stranded plan(s) detected — see PLAN-065 §4.4.B "
            "(mode 8.1 dispatch failed / mode 8.2 paperclip in_progress)"
        )
    elif overall == "degraded":
        impact = "advisory warnings only — review when convenient"

    return {
        "status": overall,
        "impact": impact,
        "findings_count": len(findings),
        "findings": findings,
        "checked_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def _cli(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="ceo-orchestration staleness checker (advisory)")
    parser.add_argument("--repo-root", default=".", help="project root (default: cwd)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "exit 1 on any unhealthy OR stranded finding "
            "(PLAN-065 §4.4.B mode 8.1 / 8.2)"
        ),
    )
    args = parser.parse_args(argv)

    repo = Path(args.repo_root).resolve()
    report = check_staleness(repo)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"# staleness report — {report['checked_at']}")
        print(f"# overall: {report['status']}  ({report['findings_count']} findings)")
        print(f"# impact:  {report['impact']}")
        # PLAN-065 §4.4.B — strict mode promotes stranded findings to
        # the top of the human-readable list with a mode-classified
        # header. Default mode keeps the historical layout.
        stranded_findings = [f for f in report["findings"] if f.get("status") == "stranded"]
        other_findings = [f for f in report["findings"] if f.get("status") != "stranded"]
        if args.strict and stranded_findings:
            print("\n## stranded plans (PLAN-065 §4.4.B)")
            for f in stranded_findings:
                mode = f.get("mode", "?")
                print(f"  [stranded mode {mode}] {f['id']}  ({f['value_days']}d)")
                print(f"    rule:        {f['rule']}")
                print(f"    impact:      {f['impact']}")
                print(f"    remediation: {f['remediation']}")
                print(f"    path:        {f['path']}")
                print()
            if other_findings:
                print("## other staleness findings")
        if not report["findings"]:
            print("\n  OK: no staleness findings.")
        elif args.strict and stranded_findings:
            for f in other_findings:
                print(f"  [{f['status']:9s}] {f['artifact']:10s} {f['id']}")
                print(f"    rule: {f['rule']} ({f['value_days']}d > {f['threshold_days']}d)")
                print(f"    impact:      {f['impact']}")
                print(f"    remediation: {f['remediation']}")
                print(f"    path:        {f['path']}")
                print()
        else:
            print()
            for f in report["findings"]:
                print(f"  [{f['status']:9s}] {f['artifact']:10s} {f['id']}")
                print(f"    rule: {f['rule']} ({f['value_days']}d > {f['threshold_days']}d)")
                print(f"    impact:      {f['impact']}")
                print(f"    remediation: {f['remediation']}")
                print(f"    path:        {f['path']}")
                print()

    if args.strict and report["status"] in ("unhealthy", "stranded"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
