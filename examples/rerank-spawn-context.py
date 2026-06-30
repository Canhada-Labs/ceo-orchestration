#!/usr/bin/env python3
"""rerank-spawn-context.py — re-rank retrieval candidates with bge-reranker.

PLAN-062 Phase 2 — adopter-side example. NOT part of framework core
(ADR-002 stdlib-only). Install dependencies in YOUR venv, not
.claude/rag/venv:

    python3 -m venv .my-rerank-venv
    source .my-rerank-venv/bin/activate
    pip install sentence-transformers torch

Use:

    python3 examples/rerank-spawn-context.py \\
        --task "audit src/auth.ts for timing oracles" \\
        --candidates /tmp/candidates.txt \\
        --top 3 > /tmp/context.txt

    .claude/scripts/inject-agent-context.sh "Staff Code Reviewer" \\
        "audit src/auth.ts for timing oracles" \\
        --context-file /tmp/context.txt

Input format (--candidates):
    One candidate per line. Each line is a string the LLM will
    eventually see (e.g., "src/auth.ts:45 — async function ...").
    No format restrictions — bge ranks them as-is.

Output format (stdout):
    Top-N candidates in re-ranked order. One per line. Plus a
    trailing comment line with the relevance scores for transparency.

Why this isn't shipped in the framework core:
    - ADR-002 enforces stdlib-only.
    - sentence-transformers + torch is ~2 GiB.
    - 80% of adopters don't need it.
    - This doc-and-recipe approach lets adopters wire when needed.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Tuple


def load_candidates(path: Path) -> List[str]:
    """Load one-per-line candidate strings, stripping blanks."""
    if not path.is_file():
        sys.stderr.write(f"error: candidates file not found: {path}\n")
        sys.exit(2)
    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not lines:
        sys.stderr.write(f"error: no candidates in {path}\n")
        sys.exit(2)
    return lines


def rerank_with_bge(
    task: str,
    candidates: List[str],
    top_n: int,
    model_name: str = "BAAI/bge-reranker-v2-m3",
) -> List[Tuple[str, float]]:
    """Rerank candidates against task with bge-reranker-v2.

    Returns list of (candidate, score) tuples in descending score order,
    truncated to top_n.

    Lazy-imports sentence_transformers — module raises a clear error
    if not installed.
    """
    try:
        from sentence_transformers import CrossEncoder
    except ImportError:
        sys.stderr.write(
            "error: sentence-transformers not installed. Run:\n"
            "  pip install sentence-transformers torch\n"
            "in your adopter venv (NOT framework venv).\n"
        )
        sys.exit(3)

    model = CrossEncoder(model_name)

    pairs = [(task, candidate) for candidate in candidates]
    scores = model.predict(pairs)

    ranked = sorted(
        zip(candidates, scores),
        key=lambda pair: float(pair[1]),
        reverse=True,
    )
    return [(c, float(s)) for c, s in ranked[:top_n]]


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Re-rank retrieval candidates with bge-reranker-v2."
    )
    parser.add_argument(
        "--task",
        required=True,
        help="The spawn task description (used as query for re-rank)",
    )
    parser.add_argument(
        "--candidates",
        required=True,
        type=Path,
        help="Path to one-per-line candidate file",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=3,
        help="Number of top candidates to keep (default: 3 — see "
        "Lost-in-the-Middle, Liu et al, TACL 2024)",
    )
    parser.add_argument(
        "--model",
        default="BAAI/bge-reranker-v2-m3",
        help="HuggingFace model name (default: bge-reranker-v2-m3)",
    )
    args = parser.parse_args(argv)

    candidates = load_candidates(args.candidates)
    if len(candidates) < args.top:
        sys.stderr.write(
            f"warning: only {len(candidates)} candidates loaded; "
            f"requested top {args.top}. Returning all.\n"
        )

    ranked = rerank_with_bge(
        task=args.task,
        candidates=candidates,
        top_n=args.top,
        model_name=args.model,
    )

    # Output: one candidate per line, then trailing comment with scores
    for candidate, _score in ranked:
        print(candidate)

    print()
    print("# Re-rank scores:")
    for candidate, score in ranked:
        # Truncate long candidates in the comment for readability
        display = candidate if len(candidate) < 80 else candidate[:77] + "..."
        print(f"#   {score:.4f}  {display}")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
