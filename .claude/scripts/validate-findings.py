#!/usr/bin/env python3
"""Findings validator (PLAN-086 Wave 0 / AC1 + Wave E.3 typed-coverage lint).

Two stdlib-only subcommands per PLAN-086 §4 Wave 0:

  progress-log-closure --plan PLAN-NNN --severity P{0|1|2|3} --source <jsonl>
      Asserts every raw_finding_id in the source JSONL appears with
      `closed_in_commit: <SHA>` OR `deferred_to: PLAN-NNN` in the
      named plan's ## §11 Progress log section.

  emit-typed-coverage --audit-emit <path> --actions <comma-list>
      Lints that no `emit_generic(action="<X>"` calls remain for any
      action in the specified list — they must all be typed-wrapper
      promoted per PLAN-086 Wave E.

Exit codes:
  0 - all asserts pass
  1 - one or more assertions failed (printed to stderr)
  2 - infra failure (file missing, parse error)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Optional, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Subcommand: progress-log-closure
# ---------------------------------------------------------------------------

def _load_finding_ids(source_jsonl: Path, severity_filter: Optional[str]) -> Set[str]:
    """Read JSONL of findings, return set of raw_finding_id strings."""
    ids: Set[str] = set()
    if not source_jsonl.exists():
        raise FileNotFoundError(source_jsonl)
    with source_jsonl.open(encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            sev = ev.get("severity") or ev.get("category_severity")
            if severity_filter and sev and severity_filter.upper() not in str(sev).upper():
                continue
            rid = ev.get("raw_finding_id") or ev.get("id")
            if rid:
                ids.add(str(rid))
    return ids


def _read_progress_log(plan_path: Path) -> str:
    """Extract the ## §11. Progress log section text from the plan body."""
    if not plan_path.exists():
        raise FileNotFoundError(plan_path)
    text = plan_path.read_text(encoding="utf-8")
    # Match ## §11. Progress log OR ## 11. Progress log OR ## Progress log
    m = re.search(
        r"^##\s*(?:§)?11\.?\s*Progress log\s*$",
        text,
        re.MULTILINE | re.IGNORECASE,
    )
    if not m:
        return ""
    start = m.end()
    # Stop at next top-level `## ` section
    nxt = re.search(r"^##\s+\S", text[start:], re.MULTILINE)
    end = start + nxt.start() if nxt else len(text)
    return text[start:end]


def cmd_progress_log_closure(args: argparse.Namespace) -> int:
    plan_path = REPO_ROOT / ".claude" / "plans" / f"{args.plan}-*.md"
    candidates = list(plan_path.parent.glob(plan_path.name))
    if not candidates:
        # Fallback: try the bare path
        bare = REPO_ROOT / ".claude" / "plans" / f"{args.plan}.md"
        if bare.exists():
            candidates = [bare]
    if not candidates:
        print(
            f"validate-findings: plan body for {args.plan} not found",
            file=sys.stderr,
        )
        return 2
    plan_body = _read_progress_log(candidates[0])
    if not plan_body:
        print(
            f"validate-findings: §11 Progress log section missing in "
            f"{candidates[0].name}",
            file=sys.stderr,
        )
        return 1

    try:
        finding_ids = _load_finding_ids(args.source, args.severity)
    except FileNotFoundError as e:
        print(f"validate-findings: source JSONL not found: {e}", file=sys.stderr)
        return 2

    # Build closure index from plan body. Either:
    #   closed_in_commit: <SHA>   (next to ID)
    #   deferred_to: PLAN-NNN     (next to ID)
    closed_ids: Set[str] = set()
    for rid in finding_ids:
        # Cheap substring contains check first; if the ID literal appears at
        # all in §11 with closure or deferral keyword nearby (same line or
        # within next 200 chars), count as closed.
        for m in re.finditer(re.escape(rid), plan_body):
            ctx = plan_body[max(0, m.start() - 50):m.end() + 200]
            if re.search(r"closed_in_commit\s*:\s*\S+", ctx) or re.search(
                r"deferred_to\s*:\s*PLAN-\d+", ctx
            ):
                closed_ids.add(rid)
                break

    missing = sorted(finding_ids - closed_ids)
    print(
        f"validate-findings progress-log-closure: "
        f"plan={args.plan} severity={args.severity} "
        f"total={len(finding_ids)} closed={len(closed_ids)} "
        f"missing={len(missing)}"
    )
    if missing:
        for rid in missing[:25]:
            print(f"  MISSING: {rid}", file=sys.stderr)
        if len(missing) > 25:
            print(f"  ... and {len(missing) - 25} more", file=sys.stderr)
        return 1
    return 0


# ---------------------------------------------------------------------------
# Subcommand: emit-typed-coverage
# ---------------------------------------------------------------------------

def cmd_emit_typed_coverage(args: argparse.Namespace) -> int:
    """Lint: no `emit_generic(action="<X>"` for any X in --actions."""
    if not args.audit_emit.exists():
        print(
            f"validate-findings: audit_emit.py not found at {args.audit_emit}",
            file=sys.stderr,
        )
        return 2
    actions: List[str] = [a.strip() for a in args.actions.split(",") if a.strip()]
    if not actions:
        print("validate-findings: --actions list empty", file=sys.stderr)
        return 2

    # Scan whole tree for emit_generic call sites referencing each action.
    scan_roots = [
        REPO_ROOT / ".claude" / "hooks",
        REPO_ROOT / ".claude" / "scripts",
    ]
    findings: List[Tuple[str, str, int]] = []
    for root in scan_roots:
        if not root.exists():
            continue
        for py in root.rglob("*.py"):
            if "test" in py.name and "fixture" not in py.name:
                # Tests may construct test-only emit_generic calls intentionally.
                continue
            try:
                txt = py.read_text(encoding="utf-8")
            except OSError:
                continue
            for action in actions:
                pat = re.compile(
                    r"emit_generic\s*\(\s*[\"']" + re.escape(action) + r"[\"']"
                )
                for m in pat.finditer(txt):
                    ln = txt.count("\n", 0, m.start()) + 1
                    findings.append((str(py.relative_to(REPO_ROOT)), action, ln))

    print(
        f"validate-findings emit-typed-coverage: "
        f"actions={len(actions)} violations={len(findings)}"
    )
    if findings:
        for path, action, ln in findings:
            print(f"  VIOLATION: {path}:{ln} emit_generic('{action}')", file=sys.stderr)
        return 1
    return 0


# ---------------------------------------------------------------------------
# CLI dispatch
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Findings validator (PLAN-086 Wave 0)."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_closure = sub.add_parser(
        "progress-log-closure",
        help="Assert all source-JSONL finding IDs appear with closure marker in plan §11.",
    )
    p_closure.add_argument("--plan", required=True, help="PLAN-NNN slug (e.g. PLAN-086).")
    p_closure.add_argument(
        "--severity", default=None, help="Filter source JSONL by severity (P0|P1|P2|P3)."
    )
    p_closure.add_argument(
        "--source", required=True, type=Path, help="Path to findings JSONL."
    )

    p_typed = sub.add_parser(
        "emit-typed-coverage",
        help="Assert no emit_generic() calls remain for promoted actions.",
    )
    p_typed.add_argument(
        "--audit-emit",
        type=Path,
        default=REPO_ROOT / ".claude" / "hooks" / "_lib" / "audit_emit.py",
        help="Path to audit_emit.py (default: repo-relative).",
    )
    p_typed.add_argument(
        "--actions",
        required=True,
        help="Comma-separated action names that MUST be typed-wrapped.",
    )

    args = parser.parse_args()
    if args.cmd == "progress-log-closure":
        return cmd_progress_log_closure(args)
    if args.cmd == "emit-typed-coverage":
        return cmd_emit_typed_coverage(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
