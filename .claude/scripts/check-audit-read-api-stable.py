#!/usr/bin/env python3
"""check-audit-read-api-stable — audit-log + session-graph read-API freeze guard.

PLAN-014 Phase F.0 + ADJ-011 (VP Engineering §Phase-F pre-work). Pattern
precedent: ``check-audit-registry-coverage.py`` (PLAN-013 Gap #3 fix).

During Phase F, three new capabilities (replay + predict + cross-plan-memory)
all consume the **audit-log read API** and the **session-graph derived
registry** to reconstruct plan context. If a refactor REMOVES or RENAMES
a public read function under our feet, every Phase F downstream breaks
silently.

This script FREEZES the public read-API surface at a pinned baseline. Any
commit that removes or renames a baseline function trips exit 1. Adding
new functions (additive) is fine.

## What it guards

- ``.claude/hooks/_lib/audit_emit.py::iter_events`` — public event iterator
- ``.claude/scripts/audit-query.py`` sub-command dispatch table

## Baseline (v1.0.0-rc.1)

Public read-API functions / subcommands that MUST EXIST across v1:

  iter_events
  read_entries                (audit-query.py)
  discover_logs               (audit-query.py)
  default_log_path            (audit-query.py)
  cmd_summary                 (audit-query.py)
  cmd_by_skill                (audit-query.py)
  cmd_compliance              (audit-query.py)
  cmd_by_day                  (audit-query.py)
  cmd_search                  (audit-query.py)
  cmd_since                   (audit-query.py)
  cmd_stats                   (audit-query.py)
  cmd_export                  (audit-query.py)
  cmd_debate                  (audit-query.py)
  cmd_plans                   (audit-query.py)
  cmd_vetoes                  (audit-query.py)
  cmd_benchmarks              (audit-query.py)
  cmd_lessons                 (audit-query.py)
  cmd_metrics                 (audit-query.py)
  cmd_health                  (audit-query.py)
  cmd_tokens                  (audit-query.py)

Baseline lives in this script (BASELINE_FUNCS). To tighten (add a new
must-exist function) is MINOR-bump additive. To REMOVE from the baseline
is MAJOR-bump (forbidden in v1 without new SPEC file).

## Exit codes

  0 — baseline intact (all functions present); any ADDITIONS are reported
      advisory
  1 — drift detected (baseline function missing or renamed)
  2 — internal error (missing source file, malformed AST)

Stdlib only. Python 3.9+.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# -----------------------------------------------------------------------------
# Baseline — pinned v1.0.0-rc.1
# -----------------------------------------------------------------------------

AUDIT_EMIT_REL = Path(".claude/hooks/_lib/audit_emit.py")
AUDIT_QUERY_REL = Path(".claude/scripts/audit-query.py")

BASELINE: Dict[str, Set[str]] = {
    # module-rel-path: {required public function names}
    str(AUDIT_EMIT_REL): {
        "iter_events",
    },
    str(AUDIT_QUERY_REL): {
        "read_entries",
        "discover_logs",
        "default_log_path",
        "cmd_summary",
        "cmd_by_skill",
        "cmd_compliance",
        "cmd_by_day",
        "cmd_search",
        "cmd_since",
        "cmd_stats",
        "cmd_export",
        "cmd_debate",
        "cmd_plans",
        "cmd_vetoes",
        "cmd_benchmarks",
        "cmd_lessons",
        "cmd_metrics",
        "cmd_health",
        "cmd_tokens",
    },
}


# -----------------------------------------------------------------------------
# AST extraction
# -----------------------------------------------------------------------------


def public_function_names(path: Path) -> Set[str]:
    """Return public top-level function defs from a Python file (stdlib-ast)."""
    if not path.is_file():
        raise FileNotFoundError(f"cannot read {path}")
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(src, filename=str(path))
    except (OSError, SyntaxError) as e:
        raise RuntimeError(f"AST parse failed for {path}: {e}") from e
    names: Set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                names.add(node.name)
    return names


# -----------------------------------------------------------------------------
# Check
# -----------------------------------------------------------------------------


def check_baseline(
    repo_root: Path,
    baseline: Dict[str, Set[str]] = BASELINE,
) -> Tuple[int, Dict[str, Dict[str, List[str]]]]:
    """Run the baseline check.

    Returns (exit_code, report) where report is:
        {rel_path: {missing: [...], extras: [...]}}
    """
    report: Dict[str, Dict[str, List[str]]] = {}
    worst = 0

    for rel_path, required in sorted(baseline.items()):
        abs_path = repo_root / rel_path
        try:
            present = public_function_names(abs_path)
        except FileNotFoundError as e:
            report[rel_path] = {"missing": sorted(required), "extras": [], "error": [str(e)]}
            worst = max(worst, 2)
            continue
        except RuntimeError as e:
            report[rel_path] = {"missing": [], "extras": [], "error": [str(e)]}
            worst = max(worst, 2)
            continue

        missing = sorted(required - present)
        extras = sorted(present - required)
        report[rel_path] = {"missing": missing, "extras": extras}
        if missing:
            worst = max(worst, 1)

    return worst, report


def format_report(report: Dict[str, Dict[str, List[str]]], verbose: bool) -> str:
    """Format the audit-query read-API stability report as human-readable text."""
    lines: List[str] = []
    for rel_path, info in sorted(report.items()):
        missing = info.get("missing", [])
        extras = info.get("extras", [])
        err = info.get("error", [])
        if err:
            lines.append(f"[FAIL] {rel_path}")
            for e in err:
                lines.append(f"  error: {e}")
            continue
        if missing:
            lines.append(f"[FAIL] {rel_path}")
            for m in missing:
                lines.append(f"  MISSING baseline function: {m}")
        elif verbose:
            lines.append(f"[OK]   {rel_path}  (baseline {len(info.get('missing', []))} missing, {len(extras)} additions)")
        if extras and verbose:
            for x in extras:
                lines.append(f"  additive (not in baseline): {x}")
    return "\n".join(lines) or "(no report items)"


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="check-audit-read-api-stable.py",
        description="Freeze-check for audit-log + session-graph read API (PLAN-014 F.0)",
    )
    p.add_argument("--repo-root", default=None,
                   help="Repo root (default: cwd)")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--json", action="store_true")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — assert audit-query read-API output shape is unchanged."""
    parser = build_parser()
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path.cwd()

    exit_code, report = check_baseline(repo_root)

    if args.json:
        import json as _json
        payload = {"exit": exit_code, "report": {
            k: {"missing": v.get("missing", []), "extras": v.get("extras", []),
                "error": v.get("error", [])}
            for k, v in report.items()
        }}
        sys.stdout.write(_json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    else:
        out = format_report(report, args.verbose)
        sys.stdout.write(out + "\n")
        if exit_code == 0:
            sys.stdout.write("OK: read-API baseline intact\n")
        elif exit_code == 1:
            sys.stdout.write("FAIL: read-API drift — baseline function missing/renamed\n")
        else:
            sys.stdout.write("ERROR: internal failure (missing file or parse error)\n")

    return exit_code


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
