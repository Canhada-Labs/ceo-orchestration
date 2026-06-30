#!/usr/bin/env python3
"""benchmark-fallback-scorer.py — deterministic keyword-match scorer.

PLAN-011 Phase 3 / §H7 consensus. When the LLM judge is unreachable
(network down, adapter init failure, same-adapter collision), this
scorer is the fallback. It produces a grade with the SAME JSON shape
as `benchmark-judge.py` so downstream auditing is shape-stable.

## Algorithm (deterministic)

For each rubric item:
1. Extract stopword-free keywords from the item's `description`.
2. If ALL keywords appear case-insensitively in the response, the item
   is counted as matched at full weight.
3. If SOME keywords appear, the item is counted at `matched / total`
   fraction of the weight (partial credit).
4. If NONE appear, the item contributes 0.

The overall score is the sum of per-item contributions, normalised to
[0, 10] to match the LLM judge scale. `all_or_nothing` scoring short-
circuits to 10 if every item matches completely, else 0.

## Usage

    python3 benchmark-fallback-scorer.py \\
        --response-file response.txt \\
        --rubric-file rubric.json \\
        [--task-context "short task desc"]

## Exit codes

    0 — grade produced
    2 — input/config error (missing files, bad JSON, empty rubric)

Output JSON shape:

    {
      "benchmark": "<slug>",
      "judge_adapter": "fallback",
      "forward": {"score": 0-10, "refused": false, "flags": [], "reasoning": "..."},
      "reverse": {...},          # same as forward (deterministic; no position bias)
      "delta": 0.0,
      "recommend_human_review": false
    }
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


# Minimal English stopword list — avoids stdlib NLTK dependency.
# Stopwords are removed from rubric descriptions before keyword match.
_STOPWORDS: Set[str] = {
    "a", "an", "and", "are", "as", "at", "be", "by", "every", "for",
    "from", "has", "have", "in", "is", "it", "its", "of", "on", "one",
    "or", "that", "the", "this", "to", "was", "were", "will", "with",
    "all", "any", "each", "least",
}

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-]{1,}")


def extract_keywords(text: str) -> List[str]:
    """Lowercase + word-boundary split; drop stopwords + short tokens.

    Returns a deduped list preserving first-occurrence order (for
    deterministic diagnostics).
    """
    if not text:
        return []
    seen: Set[str] = set()
    out: List[str] = []
    for raw in _WORD_RE.findall(text.lower()):
        if len(raw) < 3:
            continue
        if raw in _STOPWORDS:
            continue
        if raw in seen:
            continue
        seen.add(raw)
        out.append(raw)
    return out


def response_tokens(text: str) -> Set[str]:
    """Return the lowercase token set for membership tests."""
    if not text:
        return set()
    return {m.group(0) for m in _WORD_RE.finditer(text.lower())}


def score_rubric(rubric: Dict[str, Any], response: str) -> Dict[str, Any]:
    """Score a response against a rubric.

    Returns the same shape as the LLM judge grade (with `score` in
    0..10), plus a `breakdown` list for diagnostics.
    """
    if not isinstance(rubric, dict):
        raise ValueError("rubric must be a dict")
    items = rubric.get("items") or []
    if not items:
        raise ValueError("rubric.items must be non-empty")
    scoring = rubric.get("scoring", "weighted_average")
    resp_tokens = response_tokens(response)

    total_weight = 0.0
    earned = 0.0
    breakdown: List[Dict[str, Any]] = []

    for item in items:
        weight = float(item.get("weight", 0.0))
        total_weight += weight
        description = str(item.get("description", ""))
        keywords = extract_keywords(description)
        if not keywords:
            # No meaningful keywords — grant half credit (description is
            # too short to pattern-match; don't penalise the rubric for
            # sparse descriptions).
            earned += weight * 0.5
            breakdown.append(
                {
                    "id": item.get("id"),
                    "matched": 0,
                    "total_keywords": 0,
                    "fraction": 0.5,
                    "weight": weight,
                    "contribution": round(weight * 0.5, 4),
                }
            )
            continue
        matched = sum(1 for kw in keywords if kw in resp_tokens)
        fraction = matched / len(keywords)
        earned += weight * fraction
        breakdown.append(
            {
                "id": item.get("id"),
                "matched": matched,
                "total_keywords": len(keywords),
                "fraction": round(fraction, 4),
                "weight": weight,
                "contribution": round(weight * fraction, 4),
            }
        )

    if total_weight <= 0:
        raise ValueError("rubric weights must sum to >0")

    if scoring == "all_or_nothing":
        all_full = all(entry["fraction"] == 1.0 for entry in breakdown if entry["total_keywords"] > 0)
        score_0_10 = 10.0 if all_full else 0.0
    else:
        # weighted_average — normalise to 0..10
        score_0_10 = round((earned / total_weight) * 10.0, 3)

    return {
        "score": score_0_10,
        "reasoning": (
            "deterministic keyword-match fallback; "
            f"{sum(e['matched'] for e in breakdown)} of "
            f"{sum(e['total_keywords'] for e in breakdown)} keywords matched"
        ),
        "refused": False,
        "flags": ["fallback"],
        "breakdown": breakdown,
    }


def grade(response: str, rubric: Dict[str, Any], benchmark_slug: str = "") -> Dict[str, Any]:
    """Public entry point: return the same envelope shape as benchmark-judge."""
    fwd = score_rubric(rubric, response)
    # Fallback scorer is deterministic ⇒ forward == reverse, delta == 0.
    return {
        "benchmark": benchmark_slug,
        "judge_adapter": "fallback",
        "forward": fwd,
        "reverse": dict(fwd),
        "delta": 0.0,
        "recommend_human_review": False,
    }


# ---------------------------------------------------------------------------
# Rubric loader (shared shape with benchmark-judge)
# ---------------------------------------------------------------------------


def load_rubric(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"rubric file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"rubric JSON parse error: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("rubric top-level must be an object")
    if "items" not in data:
        raise ValueError("rubric missing required field: items")
    if not isinstance(data["items"], list) or not data["items"]:
        raise ValueError("rubric.items must be non-empty list")
    return data


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="benchmark-fallback-scorer.py",
        description="Deterministic keyword-match fallback scorer (PLAN-011 Phase 3 / §H7)",
    )
    p.add_argument("--benchmark", default="", help="Benchmark slug (optional label)")
    p.add_argument("--response-file", required=True, help="Path to candidate response")
    p.add_argument("--rubric-file", required=True, help="Path to rubric JSON")
    p.add_argument("--task-context", default="", help="Short task description (unused)")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — deterministic fallback scorer when LLM judge is unavailable."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        rubric = load_rubric(Path(args.rubric_file))
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    try:
        response = Path(args.response_file).read_text(encoding="utf-8")
    except OSError as e:
        print(f"ERROR: cannot read response file: {e}", file=sys.stderr)
        return 2

    try:
        result = grade(response, rubric, benchmark_slug=args.benchmark)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
