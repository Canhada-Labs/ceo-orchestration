#!/usr/bin/env python3
"""debate-converge.py — Jaccard convergence detector for debate rounds.

PLAN-011 Phase 5. Detects when a debate has converged by computing the
Jaccard similarity of the risk sets between round N and round N-1
across all agent critique files.

## Usage

    debate-converge.py --plan PLAN-NNN --round N [--plans-root <path>]

    N must be >= 2. Round N-1 must exist on disk.

## Algorithm

1. For round N and round N-1, read every `<archetype>.md` file under
   `.claude/plans/PLAN-NNN/debate/round-<N>/` (excluding `proposal.md`,
   `consensus.md`, `synthesis.md`, `red-team.md` — those are CEO/meta
   artifacts, not agent critiques).
2. In each file, locate the `## Risks` heading and extract bullet items
   (lines starting with `- `). Continue through subsequent bullets
   until a new heading (`## `) or EOF.
3. Normalize each risk bullet: lowercase, strip punctuation, collapse
   whitespace, dedupe within a file.
4. Union all risk bullets per round into a set.
5. Compute Jaccard = |A ∩ B| / |A ∪ B| (0 if both sets are empty).
6. Output JSON: `{"jaccard": float, "converged": bool, "red_team_needed": bool}`.

`converged` is True iff jaccard >= threshold (default 0.7).
`red_team_needed` is True iff `converged AND round <= 2`. This is the
M1 anti-groupthink gate from PLAN-011 consensus round 1.

## Why 0.7

See ADR-032 §Decision drivers. 0.7 means ~70% of the risk vocabulary
overlaps between rounds — high enough to distinguish "same topics
reordered" from "genuine agreement". Lower thresholds (0.5) would
declare convergence on largely disjoint sets; higher (0.9) would
require near-exact text, which rarely survives Round→Round agent
paraphrase.

## Exit codes

    0 — convergence computed successfully (JSON printed to stdout)
    1 — bad args / round < 2 / round N-1 missing
    2 — no agent critique files found in either round (zero coverage)
    3 — max_rounds_reached (terminal; orchestrator also exits 3)
"""

from __future__ import annotations

import argparse
import json
import re
import string
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Set


# Default threshold; overridable via --threshold for stress tests.
DEFAULT_JACCARD_THRESHOLD = 0.7

# MAX_ROUNDS — HARD STOP (PLAN-012 Phase 1 D3.5 + debate round-1
# chaos-engineer.md CRITICAL-2 "cost runaway via adversarial injection";
# ADR-032 amendment). compute_convergence() forces outcome
# "max_rounds_reached" when round_number >= MAX_ROUNDS, independent of
# Jaccard score and budget hook state.
MAX_ROUNDS = 5

_OUTCOME_CONVERGED = "converged"
_OUTCOME_DIVERGED = "diverged"
_OUTCOME_MAX_ROUNDS = "max_rounds_reached"


@dataclass
class ConvergenceResult:
    """Structured convergence probe result; see compute_convergence()."""

    convergence_met: bool
    max_rounds_reached: bool
    jaccard_score: float
    threshold: float
    outcome: str  # one of _OUTCOME_*
    round_number: int


# Files that live under round-N/ but are NOT agent critiques.
_NON_CRITIQUE_FILES = {
    "proposal.md",
    "consensus.md",
    "synthesis.md",
    "red-team.md",
    # DEBATE-SCHEMA §13.2 anonymized-synthesis audit record (PLAN-134 W1)
    "anonymization-map.md",
}


_HEADING_RE = re.compile(r"^\s*##\s+(.+?)\s*$")
_BULLET_RE = re.compile(r"^\s*-\s+(.+?)\s*$")

# Punctuation table used for normalization. We replace all ASCII
# punctuation characters with a space (so "rate-limit" -> "rate limit",
# not "ratelimit"); unicode punctuation is collapsed via split().
_PUNCT_TABLE = str.maketrans(string.punctuation, " " * len(string.punctuation))


def _plans_root_default() -> Path:
    """Return the default `.claude/plans/` root based on __file__ location."""
    # __file__ is at .claude/scripts/debate-converge.py — plans root is sibling.
    return Path(__file__).resolve().parent.parent / "plans"


def _round_dir(plans_root: Path, plan_id: str, round_num: int) -> Path:
    return plans_root / plan_id / "debate" / f"round-{round_num}"


def _normalize_risk(text: str) -> str:
    """Normalize a risk bullet for set-membership comparison.

    Steps:
    - lowercase
    - strip ASCII punctuation
    - collapse whitespace (handles unicode spaces via .split())
    - drop leading inline-ID prefixes like "R-VP1:", "R-SEC2 -",
      so two rounds that renumber IDs still match on substance.
    """
    s = text.lower()
    # Strip leading ID markers: "r-xxx:", "r-xxx -", "c1:", "m1:"
    s = re.sub(r"^\s*(r-[a-z0-9]+|c\d+|m\d+|s\d+|h\d+)\s*[:\-—]\s*", "", s)
    s = s.translate(_PUNCT_TABLE)
    s = " ".join(s.split())
    return s


def extract_risks(md_text: str) -> List[str]:
    """Extract and normalize bullet items under the `## Risks` heading.

    Returns a list (order preserved, duplicates allowed; caller dedupes
    via set()).
    """
    lines = md_text.splitlines()
    risks: List[str] = []
    in_risks = False
    for raw in lines:
        heading = _HEADING_RE.match(raw)
        if heading:
            title = heading.group(1).strip().lower()
            # Accept "Risks", "risks (prioritized)", "Risks:"
            if title == "risks" or title.startswith("risks "):
                in_risks = True
                continue
            # Any other heading closes the Risks section
            if in_risks:
                in_risks = False
            continue
        if not in_risks:
            continue
        bullet = _BULLET_RE.match(raw)
        if bullet:
            normalized = _normalize_risk(bullet.group(1))
            if normalized:
                risks.append(normalized)
    return risks


def iter_agent_critiques(round_dir: Path) -> Iterable[Path]:
    """Yield paths of agent critique files under round_dir (alpha-sorted).

    Excludes proposal.md, consensus.md, synthesis.md, red-team.md.
    """
    if not round_dir.is_dir():
        return
    for p in sorted(round_dir.iterdir()):
        if p.name in _NON_CRITIQUE_FILES:
            continue
        if p.suffix != ".md":
            continue
        if not p.is_file():
            continue
        yield p


def collect_risk_set(round_dir: Path) -> Set[str]:
    """Union all agent critique risks in a round into a normalized set."""
    out: Set[str] = set()
    for critique_path in iter_agent_critiques(round_dir):
        try:
            text = critique_path.read_text(encoding="utf-8")
        except OSError:
            continue
        for risk in extract_risks(text):
            out.add(risk)
    return out


def jaccard(a: Set[str], b: Set[str]) -> float:
    """Return Jaccard similarity. Empty/empty = 1.0 by convention (no
    evidence of divergence); anything vs empty = 0.0."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    if union == 0:
        return 1.0  # defensive; unreachable with above guards
    return inter / union


def compute_convergence(
    plans_root: Path,
    plan_id: str,
    round_num: int,
    threshold: float = DEFAULT_JACCARD_THRESHOLD,
) -> dict:
    """Compute Jaccard across round N and N-1. Returns a dict shaped
    like :class:`ConvergenceResult` plus legacy keys (``jaccard``,
    ``converged``, ``red_team_needed``, ``round``, ``plan``, risk counts,
    ``zero_coverage``). When ``round_num >= MAX_ROUNDS``, the outcome
    is terminal: ``max_rounds_reached`` = True, ``convergence_met`` +
    legacy ``converged`` forced False, ``outcome == "max_rounds_reached"``
    regardless of Jaccard (closes PLAN-012 chaos CRITICAL-2)."""
    prev_dir = _round_dir(plans_root, plan_id, round_num - 1)
    cur_dir = _round_dir(plans_root, plan_id, round_num)
    if not prev_dir.is_dir():
        raise FileNotFoundError(f"round {round_num - 1} directory missing: {prev_dir}")
    if not cur_dir.is_dir():
        raise FileNotFoundError(f"round {round_num} directory missing: {cur_dir}")
    max_rounds_reached = bool(round_num >= MAX_ROUNDS)
    prev_set = collect_risk_set(prev_dir)
    cur_set = collect_risk_set(cur_dir)
    zero_coverage = not prev_set and not cur_set
    score = 0.0 if zero_coverage else jaccard(prev_set, cur_set)
    jaccard_converged = (not zero_coverage) and score >= threshold
    # MAX_ROUNDS overrides: even on Jaccard-converged, a run at
    # round >= MAX_ROUNDS is terminal; red-team + consensus gates skip.
    convergence_met = jaccard_converged and not max_rounds_reached
    if max_rounds_reached:
        outcome = _OUTCOME_MAX_ROUNDS
    elif jaccard_converged:
        outcome = _OUTCOME_CONVERGED
    else:
        outcome = _OUTCOME_DIVERGED
    return {
        "jaccard": round(score, 6),
        "converged": bool(convergence_met),
        "red_team_needed": bool(convergence_met and round_num <= 2),
        "round": round_num,
        "plan": plan_id,
        "prev_risk_count": len(prev_set),
        "curr_risk_count": len(cur_set),
        "threshold": threshold,
        "zero_coverage": zero_coverage,
        "convergence_met": bool(convergence_met),
        "max_rounds_reached": max_rounds_reached,
        "jaccard_score": round(score, 6),
        "outcome": outcome,
        "round_number": round_num,
    }


def _parse(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Compute Jaccard convergence for a debate round"
    )
    p.add_argument("--plan", required=True, help="Plan ID (PLAN-NNN)")
    p.add_argument(
        "--round",
        type=int,
        required=True,
        dest="round_num",
        help="Round number (>= 2)",
    )
    p.add_argument(
        "--plans-root",
        type=str,
        default=None,
        help="Override plans root (defaults to ../plans relative to this script)",
    )
    p.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_JACCARD_THRESHOLD,
        help=f"Jaccard threshold for convergence (default {DEFAULT_JACCARD_THRESHOLD})",
    )
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — compute Jaccard convergence across debate rounds."""
    args = _parse(argv if argv is not None else sys.argv[1:])
    if args.round_num < 2:
        print(
            f"ERROR: --round must be >= 2 (got {args.round_num})",
            file=sys.stderr,
        )
        return 1
    if not re.match(r"^PLAN-[0-9]{3}$", args.plan):
        print(
            f"ERROR: --plan must match PLAN-NNN (got {args.plan!r})",
            file=sys.stderr,
        )
        return 1

    plans_root = (
        Path(args.plans_root).resolve() if args.plans_root else _plans_root_default()
    )

    try:
        result = compute_convergence(
            plans_root, args.plan, args.round_num, threshold=args.threshold
        )
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if result.get("zero_coverage"):
        # Still print the JSON (machine-readable) and exit 2
        print(json.dumps(result, sort_keys=True))
        return 2

    # Exit code 3 signals terminal max-rounds-reached to the orchestrator
    # + CI scripts (distinct from exit 0 converged / 1 divergent-under-cap).
    if result.get("max_rounds_reached"):
        print(json.dumps(result, sort_keys=True))
        return 3

    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
