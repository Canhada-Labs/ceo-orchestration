#!/usr/bin/env python3
"""check-flip-release-gate-consistency.py — Phase E.4 validator.

Asserts that every workflow with enforcing State >= 1 is listed in
release.yml's WORKFLOWS array. Exit 1 on mismatch.

Per PLAN-014 ADJ-016 / C11: "for each enforcing flip, append
corresponding workflow name to release.yml WORKFLOWS array."

Usage:
    python3 .claude/scripts/check-flip-release-gate-consistency.py

Environment:
    CLAUDE_PROJECT_DIR  — project root (default: cwd)

Exit codes:
    0  — all enforcing workflows present in release.yml WORKFLOWS
    1  — mismatch: at least one enforcing workflow missing
    2  — usage error (release.yml not found, parse failure)
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import List, Optional, Set, Tuple


def _project_root() -> Path:
    """Resolve project root from env or cwd."""
    raw = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if raw:
        return Path(raw)
    return Path.cwd()


def parse_workflows_array(release_yml_content: str) -> Set[str]:
    """Extract workflow filenames from the WORKFLOWS bash array in release.yml.

    Looks for a line matching: WORKFLOWS=(workflow1.yml workflow2.yml ...)
    Returns the set of workflow names found.
    """
    # Match WORKFLOWS=(...) potentially spanning one line
    pattern = r'WORKFLOWS=\(([^)]*)\)'
    match = re.search(pattern, release_yml_content)
    if not match:
        return set()

    inner = match.group(1).strip()
    # Split on whitespace; each token is a workflow filename
    workflows = set()
    for token in inner.split():
        # Strip quotes if present
        token = token.strip("'\"")
        if token:
            workflows.add(token)
    return workflows


def get_enforcing_workflows() -> List[Tuple[str, str]]:
    """Return list of (workflow_filename, flip_description) for all State >= 1 flips.

    This is the authoritative registry of which workflows must appear
    in release.yml WORKFLOWS array. Updated per Phase E flip closures.
    """
    return [
        ("chaos.yml", "Chaos + Load tests (ADR-037 State 0 advisory)"),
        ("otel-smoke.yml", "OTEL smoke (ADR-035 State 0 advisory)"),
        ("perf-profile.yml", "Perf-profile (ADR-024 State 0 advisory)"),
        ("adapter-live.yml", "Live adapter smoke (PLAN-012 Phase 2)"),
        ("red-team.yml", "Red-team eval (ADR-037 State 1 enforcing, PLAN-014 Phase D.3)"),
        ("formal-verify.yml", "Formal verification (ADR-044 State 1 advisory, PLAN-014 Phase B.6)"),
    ]


def check_consistency(
    release_yml_content: str,
    enforcing_workflows: Optional[List[Tuple[str, str]]] = None,
) -> Tuple[bool, List[str], Set[str]]:
    """Check that all enforcing workflows appear in the WORKFLOWS array.

    Returns:
        (ok, missing_list, found_set)
        ok: True if all enforcing workflows present
        missing_list: list of missing workflow filenames
        found_set: set of workflow names found in release.yml
    """
    if enforcing_workflows is None:
        enforcing_workflows = get_enforcing_workflows()

    found = parse_workflows_array(release_yml_content)
    missing = []
    for wf_name, _desc in enforcing_workflows:
        if wf_name not in found:
            missing.append(wf_name)

    return (len(missing) == 0, missing, found)


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point."""
    root = _project_root()
    release_path = root / ".github" / "workflows" / "release.yml"

    if not release_path.is_file():
        print(f"ERROR: release.yml not found at {release_path}", file=sys.stderr)
        return 2

    try:
        content = release_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot read {release_path}: {exc}", file=sys.stderr)
        return 2

    ok, missing, found = check_consistency(content)

    if ok:
        enforcing = get_enforcing_workflows()
        print(f"OK: all {len(enforcing)} enforcing workflows present in release.yml WORKFLOWS")
        print(f"  Found: {sorted(found)}")
        return 0
    else:
        print("FAIL: enforcing workflow(s) missing from release.yml WORKFLOWS array:", file=sys.stderr)
        for wf in missing:
            print(f"  - {wf}", file=sys.stderr)
        print(f"  Found in WORKFLOWS: {sorted(found)}", file=sys.stderr)
        print(f"  Expected (all enforcing): {sorted(wf for wf, _ in get_enforcing_workflows())}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
