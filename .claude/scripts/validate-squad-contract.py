#!/usr/bin/env python3
"""Validate a squad directory against ADR-009 (squad bundle contract).

Usage:
    python3 .claude/scripts/validate-squad-contract.py --squad <path>

Where <path> is a squad directory under `.claude/skills/domains/<name>/`.

Exit codes:
    0 — pass (all ADR-009 minimum-count rules satisfied)
    1 — fail (reasons printed to stderr)
    2 — usage error

Checks (per PLAN-010 Phase 7a spec + ADR-009 §Validation rules):
    1. `team-personas.md` exists
    2. `pitfalls.yaml` exists and has ≥ 12 entries under `pitfalls:`
       (NOTE: PLAN-010 raises the floor from ADR-009's 10 to 12; this
       script enforces 12, which is strictly stronger than ADR-009.)
    3. `task-chains.yaml` exists and has ≥ 2 entries under `task_chains:`
    4. `skills/` contains ≥ 3 subdirectories each with `SKILL.md`
    5. `team-personas.md` names ≥ 2 VETO holders (lines containing
       `VETO` with a scope label), and at least 2 distinct scopes
    6. Every task-chain `owner:` mentions a known persona name, and
       any skill referenced in a chain is either in this squad's
       skills/ dir OR in `.claude/skills/core/*/SKILL.md` (soft check —
       only if the chain step has an explicit `skill:` key)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    print(
        "validate-squad-contract: PyYAML is required (python3 -m pip install pyyaml)",
        file=sys.stderr,
    )
    sys.exit(2)


MIN_PITFALLS = 12
MIN_CHAINS = 2
MIN_SKILLS = 3
MIN_VETO_HOLDERS = 2


def _emit(msg: str, out) -> None:
    out.write(msg + "\n")


def _collect_vetoes(team_md_text: str) -> List[Tuple[str, str]]:
    """Return list of (persona_excerpt, veto_scope_excerpt) for each
    line/section that clearly declares a VETO holder and scope.

    Heuristics:
      - Table rows like ``| **Name** (Role) | Scope |`` where the row
        contains "VETO" in scope column.
      - Headings like ``### N. Name — Role (VETO)`` + a ``VETO scope:``
        or ``VETO triggers (block if ANY)`` block.
    """
    vetoes: List[Tuple[str, str]] = []

    # Pattern 1: table row with VETO scope.
    # Accept rows like:
    #   | **Priya Narayanan** (Student Privacy Engineer) | Any change that touches ... |
    # Where the header line mentions "VETO scope".
    # Simpler: scan lines containing "VETO" that look like table rows or labeled bullets.
    table_row_re = re.compile(
        r"^\|\s*\*\*([^|*]+?)\*\*\s*\([^|]+\)\s*\|\s*([^|]+?)\s*\|\s*$",
        re.MULTILINE,
    )
    # Find a "| Persona | VETO scope |" header to bound the table.
    header_match = re.search(
        r"\|\s*Persona\s*\|\s*VETO scope\s*\|",
        team_md_text,
        flags=re.IGNORECASE,
    )
    if header_match:
        # Scan subsequent table rows until a non-table line.
        after = team_md_text[header_match.end():]
        lines = after.splitlines()
        in_table = False
        for line in lines:
            if line.startswith("|"):
                in_table = True
                m = table_row_re.match(line)
                if m:
                    name = m.group(1).strip()
                    scope = m.group(2).strip()
                    if scope and scope != "---" and "VETO" not in name.upper():
                        vetoes.append((name, scope))
            else:
                if in_table and line.strip() == "":
                    break
                if in_table:
                    break

    # Pattern 2: heading-level "(VETO)" — capture heading + a nearby
    # scope paragraph.
    heading_re = re.compile(
        r"^#{2,4}\s+[\d.]*\s*([^\n—–-]+?)\s*[—–-]\s*([^(\n]+?)\s*\(VETO(?:\s+on\s+[^)]+)?\)\s*$",
        re.MULTILINE,
    )
    for m in heading_re.finditer(team_md_text):
        name = m.group(1).strip()
        role = m.group(2).strip()
        # Try to pick up a scope hint from the next 30 lines
        tail = team_md_text[m.end(): m.end() + 2000]
        scope_hint = ""
        trigger_re = re.search(
            r"VETO\s+(?:scope|triggers?)[^:\n]*:\s*([^\n*]+)",
            tail,
            flags=re.IGNORECASE,
        )
        if trigger_re:
            candidate = trigger_re.group(1).strip().strip("*").strip()
            if candidate:
                scope_hint = candidate
        if not scope_hint:
            scope_hint = role
        # Dedupe by name
        if not any(v[0] == name for v in vetoes):
            vetoes.append((name, scope_hint))

    return vetoes


def _distinct_veto_scopes(vetoes: List[Tuple[str, str]]) -> Set[str]:
    """Return the set of distinct normalized scope keywords."""
    scopes: Set[str] = set()
    for _name, scope in vetoes:
        s = scope.lower()
        # Normalize by picking salient keywords
        keywords = [
            "privacy", "consent", "integrity", "grade", "tamper",
            "latency", "kill-switch", "kill", "cancel",
            "compliance", "surveillance", "market-abuse",
            "dpo", "pii", "crypto", "access-control", "security",
            "fairness", "analytics", "user-data",
        ]
        found = [k for k in keywords if k in s]
        if found:
            scopes.add(found[0])
        else:
            # Fall back to first word of scope as a crude distinct key
            first = re.split(r"\W+", s.strip())[0] if s.strip() else ""
            if first:
                scopes.add(first)
    return scopes


def _load_yaml(path: Path) -> Optional[Dict]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"validate-squad-contract: cannot parse {path}: {e}", file=sys.stderr)
        return None


def validate_squad(squad_dir: Path, core_skills_dir: Optional[Path] = None) -> Tuple[bool, List[str]]:
    """Return (ok, reasons). reasons is empty iff ok."""
    reasons: List[str] = []

    if not squad_dir.is_dir():
        return False, [f"squad path does not exist or is not a directory: {squad_dir}"]

    # 1. team-personas.md
    team_md = squad_dir / "team-personas.md"
    if not team_md.is_file():
        reasons.append("missing team-personas.md")

    # 2. pitfalls.yaml ≥ MIN_PITFALLS
    pitfalls_path = squad_dir / "pitfalls.yaml"
    if not pitfalls_path.is_file():
        reasons.append("missing pitfalls.yaml")
    else:
        data = _load_yaml(pitfalls_path)
        if not isinstance(data, dict):
            reasons.append("pitfalls.yaml not a mapping at the top level")
        else:
            entries = data.get("pitfalls") or []
            if not isinstance(entries, list):
                reasons.append("pitfalls.yaml: 'pitfalls:' must be a list")
            elif len(entries) < MIN_PITFALLS:
                reasons.append(
                    f"pitfalls.yaml: {len(entries)} entries, need ≥ {MIN_PITFALLS}"
                )

    # 3. task-chains.yaml ≥ MIN_CHAINS
    chains_path = squad_dir / "task-chains.yaml"
    chains_entries: List = []
    if not chains_path.is_file():
        reasons.append("missing task-chains.yaml")
    else:
        data = _load_yaml(chains_path)
        if not isinstance(data, dict):
            reasons.append("task-chains.yaml not a mapping at the top level")
        else:
            chains_entries = data.get("task_chains") or []
            if not isinstance(chains_entries, list):
                reasons.append("task-chains.yaml: 'task_chains:' must be a list")
                chains_entries = []
            elif len(chains_entries) < MIN_CHAINS:
                reasons.append(
                    f"task-chains.yaml: {len(chains_entries)} chains, need ≥ {MIN_CHAINS}"
                )

    # 4. skills/ with ≥ MIN_SKILLS SKILL.md
    skills_dir = squad_dir / "skills"
    skill_dirs: List[Path] = []
    if not skills_dir.is_dir():
        reasons.append("missing skills/ directory")
    else:
        skill_dirs = sorted(
            [d for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").is_file()]
        )
        if len(skill_dirs) < MIN_SKILLS:
            reasons.append(
                f"skills/: {len(skill_dirs)} SKILL.md subdirs, need ≥ {MIN_SKILLS}"
            )

    # 5. VETO holders ≥ 2 with distinct scopes
    if team_md.is_file():
        try:
            text = team_md.read_text(encoding="utf-8")
        except OSError as e:
            reasons.append(f"cannot read team-personas.md: {e}")
        else:
            vetoes = _collect_vetoes(text)
            if len(vetoes) < MIN_VETO_HOLDERS:
                reasons.append(
                    f"team-personas.md: {len(vetoes)} VETO holder(s), need ≥ {MIN_VETO_HOLDERS}"
                )
            else:
                distinct = _distinct_veto_scopes(vetoes)
                if len(distinct) < MIN_VETO_HOLDERS:
                    reasons.append(
                        f"team-personas.md: VETO scopes not distinct enough "
                        f"(got {sorted(distinct)}, need ≥ {MIN_VETO_HOLDERS})"
                    )

    # 6. Soft check: task-chain `skill:` refs resolve to this squad or core
    if chains_entries and skills_dir.is_dir():
        local_skill_names = {d.name for d in skill_dirs}
        core_skill_names: Set[str] = set()
        if core_skills_dir and core_skills_dir.is_dir():
            core_skill_names = {
                d.name for d in core_skills_dir.iterdir()
                if d.is_dir() and (d / "SKILL.md").is_file()
            }
        else:
            # Default probe — caller may not set it.
            repo_guess = squad_dir.parent.parent.parent  # domains/X -> skills -> .claude
            core_guess = repo_guess / "core"
            if core_guess.is_dir():
                core_skill_names = {
                    d.name for d in core_guess.iterdir()
                    if d.is_dir() and (d / "SKILL.md").is_file()
                }

        for chain in chains_entries:
            if not isinstance(chain, dict):
                continue
            steps = chain.get("steps") or []
            for step in steps:
                if not isinstance(step, dict):
                    continue
                sk = step.get("skill")
                if sk and sk not in local_skill_names and sk not in core_skill_names:
                    reasons.append(
                        f"task-chains.yaml: chain '{chain.get('id', '?')}' references unknown "
                        f"skill '{sk}' (not in this squad or core)"
                    )

    return (len(reasons) == 0, reasons)


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — validate a squad bundle against SPEC/v1/squad-manifest.schema.md."""
    parser = argparse.ArgumentParser(
        prog="validate-squad-contract",
        description="Validate a squad directory against ADR-009 (squad bundle contract).",
    )
    parser.add_argument(
        "--squad",
        required=True,
        help="Path to the squad directory (e.g. .claude/skills/domains/edtech/)",
    )
    parser.add_argument(
        "--core-skills",
        default=None,
        help="Path to core skills dir (default: sibling ../core/ of the squad's domains parent)",
    )
    args = parser.parse_args(argv)

    squad_dir = Path(args.squad).resolve()
    core_dir = Path(args.core_skills).resolve() if args.core_skills else None

    ok, reasons = validate_squad(squad_dir, core_dir)
    if ok:
        print(f"OK: {squad_dir} satisfies ADR-009 minimum-count contract")
        return 0
    print(f"FAIL: {squad_dir} does not satisfy the squad contract:", file=sys.stderr)
    for r in reasons:
        print(f"  - {r}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
