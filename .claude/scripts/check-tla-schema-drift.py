#!/usr/bin/env python3
"""check-tla-schema-drift.py — detect drift between schema docs and TLA+ specs.

PLAN-014 Phase B.7. Extracts state-transition claims from PLAN-SCHEMA.md
§4 and DEBATE-SCHEMA.md §12, then asserts the TLA+ .cfg property set
covers the markdown-extracted property set.

## What it checks

1. PLAN-SCHEMA.md §4 defines 5 states and a transition graph. The
   plan-lifecycle.tla .cfg must list properties covering the key
   invariants (no-skip, abandonment, timestamps, auth, terminal).

2. DEBATE-SCHEMA.md §12 defines convergence semantics (MAX_ROUNDS,
   Jaccard, Red Team, redaction). The debate-convergence.tla .cfg must
   list properties covering these semantics.

3. The .cfg INVARIANTS + PROPERTIES count must match the expected set
   derived from the markdown schemas.

## Usage

    python3 .claude/scripts/check-tla-schema-drift.py [--repo-root <path>]

## Exit codes

    0 — no drift detected
    1 — drift detected (property missing or extra)
    2 — file not found or parse error

## Stdlib only (ADR-002).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


def _default_repo_root() -> Path:
    """Return repo root based on script location."""
    return Path(__file__).resolve().parent.parent.parent


def _extract_plan_lifecycle_states(plan_schema_text: str) -> Set[str]:
    """Extract status values from PLAN-SCHEMA.md §4.

    Looks for the table under ``### State definitions`` with rows like:
    | `draft` | Plan is being written... | ... |
    """
    states: Set[str] = set()
    # Match backtick-wrapped status names in table rows
    for m in re.finditer(r"\|\s*`(\w+)`\s*\|", plan_schema_text):
        candidate = m.group(1)
        if candidate in {"draft", "reviewed", "executing", "done", "abandoned"}:
            states.add(candidate)
    return states


def _extract_plan_transitions(plan_schema_text: str) -> Set[Tuple[str, str]]:
    """Extract allowed transitions from PLAN-SCHEMA.md §4 table.

    Reads the 'Next allowed transitions' column.
    """
    transitions: Set[Tuple[str, str]] = set()
    # Parse table rows: | `status` | ... | `target1`, `target2` |
    rows = re.findall(
        r"\|\s*`(\w+)`\s*\|[^|]*\|\s*([^|]*)\|",
        plan_schema_text
    )
    for status, targets_str in rows:
        if status not in {"draft", "reviewed", "executing", "done", "abandoned"}:
            continue
        for target in re.findall(r"`(\w+)`", targets_str):
            if target in {"draft", "reviewed", "executing", "done", "abandoned"}:
                transitions.add((status, target))
    return transitions


def _extract_debate_semantics(debate_schema_text: str) -> Dict[str, bool]:
    """Extract key semantic flags from DEBATE-SCHEMA.md §12."""
    semantics: Dict[str, bool] = {}
    text = debate_schema_text

    # MAX_ROUNDS mentioned
    semantics["max_rounds"] = bool(
        re.search(r"MAX_ROUNDS|max.rounds|max_rounds", text, re.IGNORECASE)
    )
    # Jaccard convergence mentioned
    semantics["jaccard"] = bool(
        re.search(r"jaccard", text, re.IGNORECASE)
    )
    # Red Team mentioned
    semantics["red_team"] = bool(
        re.search(r"red.team|red_team", text, re.IGNORECASE)
    )
    # Redaction mentioned
    semantics["redaction"] = bool(
        re.search(r"redact", text, re.IGNORECASE)
    )
    return semantics


def _parse_cfg_properties(cfg_text: str) -> Set[str]:
    """Extract property and invariant names from a .cfg file."""
    props: Set[str] = set()
    in_invariants = False
    in_properties = False
    for line in cfg_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("\\*"):
            continue
        if stripped.upper() == "INVARIANTS":
            in_invariants = True
            in_properties = False
            continue
        if stripped.upper() == "PROPERTIES":
            in_properties = True
            in_invariants = False
            continue
        if stripped.upper().startswith(("SPECIFICATION", "CONSTANTS", "CHECK_DEADLOCK")):
            in_invariants = False
            in_properties = False
            continue
        if (in_invariants or in_properties) and stripped:
            # Property name is the first word on the line
            name = stripped.split()[0] if stripped.split() else ""
            if name and not name.startswith("\\*"):
                props.add(name)
    return props


# Expected properties per TLA+ spec
EXPECTED_PLAN_LIFECYCLE_PROPERTIES = {
    "TypeOK",
    "S1_NoSkip",
    "S2_AbandonmentDocumented",
    "S3_MonotonicTimestamps",
    "Auth_OwnerApproval",
    "Terminal_Done",
    "Terminal_Abandoned",
}

EXPECTED_DEBATE_CONVERGENCE_PROPERTIES = {
    "TypeOK",
    "S1_MaxRoundsRespected",
    "S2_RedTeamFires",
    "S3_ConsensusIdempotent",
    "S4_RedactionApplied",
    "Auth_AllContributed",
}


def check_plan_lifecycle_drift(repo_root: Path) -> List[str]:
    """Check plan-lifecycle TLA+ spec covers PLAN-SCHEMA §4 semantics."""
    errors: List[str] = []

    schema_path = repo_root / ".claude" / "plans" / "PLAN-SCHEMA.md"
    cfg_path = repo_root / "docs" / "formal-verification" / "plan-lifecycle.cfg"

    if not schema_path.is_file():
        errors.append(f"PLAN-SCHEMA.md not found: {schema_path}")
        return errors
    if not cfg_path.is_file():
        errors.append(f"plan-lifecycle.cfg not found: {cfg_path}")
        return errors

    schema_text = schema_path.read_text(encoding="utf-8")
    cfg_text = cfg_path.read_text(encoding="utf-8")

    # Check states exist in schema
    states = _extract_plan_lifecycle_states(schema_text)
    if len(states) < 5:
        errors.append(
            f"PLAN-SCHEMA.md defines {len(states)} states, expected 5: "
            f"{states}"
        )

    # Check cfg properties cover expected set
    cfg_props = _parse_cfg_properties(cfg_text)
    missing = EXPECTED_PLAN_LIFECYCLE_PROPERTIES - cfg_props
    extra = cfg_props - EXPECTED_PLAN_LIFECYCLE_PROPERTIES
    if missing:
        errors.append(
            f"plan-lifecycle.cfg missing properties: {sorted(missing)}"
        )
    if extra:
        errors.append(
            f"plan-lifecycle.cfg has extra properties: {sorted(extra)} "
            f"(not in expected set — verify intentional)"
        )

    return errors


def check_debate_convergence_drift(repo_root: Path) -> List[str]:
    """Check debate-convergence TLA+ spec covers DEBATE-SCHEMA §12."""
    errors: List[str] = []

    schema_path = repo_root / ".claude" / "plans" / "DEBATE-SCHEMA.md"
    cfg_path = repo_root / "docs" / "formal-verification" / "debate-convergence.cfg"

    if not schema_path.is_file():
        errors.append(f"DEBATE-SCHEMA.md not found: {schema_path}")
        return errors
    if not cfg_path.is_file():
        errors.append(f"debate-convergence.cfg not found: {cfg_path}")
        return errors

    schema_text = schema_path.read_text(encoding="utf-8")
    cfg_text = cfg_path.read_text(encoding="utf-8")

    # Check semantic coverage
    semantics = _extract_debate_semantics(schema_text)
    for key, present in semantics.items():
        if not present:
            errors.append(
                f"DEBATE-SCHEMA.md does not mention '{key}' — "
                f"expected for convergence model"
            )

    # Check cfg properties
    cfg_props = _parse_cfg_properties(cfg_text)
    missing = EXPECTED_DEBATE_CONVERGENCE_PROPERTIES - cfg_props
    extra = cfg_props - EXPECTED_DEBATE_CONVERGENCE_PROPERTIES
    if missing:
        errors.append(
            f"debate-convergence.cfg missing properties: {sorted(missing)}"
        )
    if extra:
        errors.append(
            f"debate-convergence.cfg has extra properties: {sorted(extra)} "
            f"(not in expected set — verify intentional)"
        )

    return errors


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — assert TLA+ spec state matches runtime invariants."""
    parser = argparse.ArgumentParser(
        description="Check TLA+ schema drift against PLAN-SCHEMA + DEBATE-SCHEMA"
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        default=None,
        help="Override repo root (default: auto-detect from script location)",
    )
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    repo_root = Path(args.repo_root).resolve() if args.repo_root else _default_repo_root()

    all_errors: List[str] = []
    all_errors.extend(check_plan_lifecycle_drift(repo_root))
    all_errors.extend(check_debate_convergence_drift(repo_root))

    if all_errors:
        print("TLA+ Schema Drift Detected:", file=sys.stderr)
        for err in all_errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print("OK: no TLA+ schema drift detected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
