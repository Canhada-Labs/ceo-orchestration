#!/usr/bin/env python3
"""PLAN-084 Wave 0.7 — verify-scope-coverage.

Cross-references scope.yaml ∀ files vs recursive findings-A/**/*.yaml.

Per R2-iter-2 CODEX-P0-3 + CODEX-P0-4:
- recursive glob walks per-archetype nested subdirs
- coverage_kind ∈ {line-level, triage-level} required for each in-scope file
- exit 0 iff missing == 0 AND coverage_kinds.none == 0

Stdlib only.

Usage:
  python3 .claude/scripts/local/verify-scope-coverage.py \
    .claude/plans/PLAN-084/scope.yaml \
    'findings-A/**/*.yaml' \
    --json
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


def parse_scope_yaml(path: Path) -> List[Dict]:
    entries: List[Dict] = []
    in_files = False
    pat = re.compile(
        r"\s*-\s*\{path:\s*([^,]+),\s*sha256:\s*([0-9a-f]+),\s*subcorpus:\s*([^,]+),\s*coverage_kind:\s*([^}]+)\}"
    )
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("files:"):
            in_files = True
            continue
        if not in_files:
            continue
        m = pat.match(line)
        if m:
            entries.append({
                "path": m.group(1).strip(),
                "sha256": m.group(2).strip(),
                "subcorpus": m.group(3).strip(),
                "coverage_kind": m.group(4).strip(),
            })
    return entries


def collect_finding_files(plan_dir: Path, glob_pattern: str) -> List[Path]:
    """Recursively walk findings-A/ + gap-B/ + per-subsystem-C/ for *.yaml."""
    out: List[Path] = []
    # Support: findings-A/**/*.yaml, gap-B/*.yaml, per-subsystem-C/*.yaml
    base, _, pat = glob_pattern.partition("/**/")
    if pat:
        # recursive
        for f in (plan_dir / base).rglob(pat):
            out.append(f)
    else:
        for f in (plan_dir / glob_pattern).parent.glob((plan_dir / glob_pattern).name):
            out.append(f)
    return out


def parse_findings_coverage(finding_files: List[Path]) -> Dict[str, str]:
    """Extract `file: <path>` + `coverage_kind: <kind>` per finding entry.

    Returns dict[file_path → highest_coverage_kind] (line-level wins over triage-level).
    """
    coverage_priority = {"line-level": 2, "triage-level": 1, "none": 0}
    by_file: Dict[str, str] = {}
    for ff in finding_files:
        try:
            text = ff.read_text(encoding="utf-8")
        except Exception:
            continue
        cur_file: Optional[str] = None
        cur_cov: Optional[str] = None
        for line in text.splitlines():
            mfile = re.match(r"\s*file:\s*(.+)", line)
            if mfile:
                if cur_file and cur_cov:
                    if coverage_priority.get(cur_cov, 0) > coverage_priority.get(by_file.get(cur_file, "none"), 0):
                        by_file[cur_file] = cur_cov
                cur_file = mfile.group(1).strip().strip('"').strip("'")
                cur_cov = None
                continue
            mcov = re.match(r"\s*coverage_kind:\s*(.+)", line)
            if mcov:
                cur_cov = mcov.group(1).strip().strip('"').strip("'")
        if cur_file and cur_cov:
            if coverage_priority.get(cur_cov, 0) > coverage_priority.get(by_file.get(cur_file, "none"), 0):
                by_file[cur_file] = cur_cov
    return by_file


def parse_intent_matrix(path: Path) -> List[str]:
    """Extract glob patterns for skip subcorpora (excluded_intentionally)."""
    skip_globs: List[str] = []
    in_subcorpora = False
    in_skip = False
    in_glob = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("subcorpora:"):
            in_subcorpora = True
            continue
        if not in_subcorpora:
            continue
        s = line.rstrip()
        if re.match(r"^\s*-\s*id:\s*", s):
            id_val = s.split("id:", 1)[1].strip()
            in_skip = id_val in {"adr_superseded_retracted", "plans_archive"}
            in_glob = False
        elif in_skip and "intent:" in s and "skip" in s:
            pass  # already in skip
        elif s.endswith("glob:"):
            in_glob = True
        elif in_glob and re.match(r"^\s{4,}-\s+", s):
            if in_skip:
                glob_val = s.split("-", 1)[1].strip()
                skip_globs.append(glob_val)
        elif not s.startswith(" "):
            in_glob = False
    return skip_globs


def is_excluded(path_str: str, skip_globs: List[str]) -> bool:
    for glob in skip_globs:
        if fnmatch.fnmatch(path_str, glob):
            return True
    return False


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("scope_yaml", type=Path)
    p.add_argument("findings_glob", nargs="?", default="findings-A/**/*.yaml")
    p.add_argument("--intent-matrix", type=Path, default=Path(".claude/plans/PLAN-084/intent-matrix.yaml"))
    p.add_argument("--plan-dir", type=Path, default=Path(".claude/plans/PLAN-084"))
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if not args.scope_yaml.exists():
        print(f"scope_yaml not found: {args.scope_yaml}", file=sys.stderr)
        return 3
    scope = parse_scope_yaml(args.scope_yaml)
    if not scope:
        print(f"scope_yaml parsed 0 entries", file=sys.stderr)
        return 3

    skip_globs: List[str] = []
    if args.intent_matrix.exists():
        skip_globs = parse_intent_matrix(args.intent_matrix)

    finding_files = collect_finding_files(args.plan_dir, args.findings_glob)
    coverage_by_file = parse_findings_coverage(finding_files)

    covered: List[str] = []
    missing: List[str] = []
    excluded: List[str] = []
    coverage_kinds: Dict[str, int] = {"line-level": 0, "triage-level": 0, "none": 0}

    for entry in scope:
        path_str = entry["path"]
        if is_excluded(path_str, skip_globs):
            excluded.append(path_str)
            continue
        kind = coverage_by_file.get(path_str, "none")
        coverage_kinds[kind] = coverage_kinds.get(kind, 0) + 1
        if kind == "none":
            missing.append(path_str)
        else:
            covered.append(path_str)

    total_in_scope = len(covered) + len(missing)
    coverage_pct = (len(covered) / total_in_scope) if total_in_scope else 0.0

    result = {
        "covered_count": len(covered),
        "missing_count": len(missing),
        "excluded_intentionally_count": len(excluded),
        "coverage_pct": round(coverage_pct, 4),
        "coverage_kinds": coverage_kinds,
        "missing": missing[:50],  # top-50 sample for stdout
        "excluded_intentionally": excluded[:50],
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"covered: {len(covered)}")
        print(f"missing: {len(missing)}")
        print(f"excluded_intentionally: {len(excluded)}")
        print(f"coverage_pct: {coverage_pct:.2%}")
        print(f"coverage_kinds: {coverage_kinds}")

    return 0 if (len(missing) == 0 and coverage_kinds.get("none", 0) == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
