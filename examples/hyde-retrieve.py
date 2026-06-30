#!/usr/bin/env python3
"""hyde-retrieve.py — HyDE retrieval recipe (Gao et al ACL 2023).

PLAN-062 Phase 4 — adopter-side example. NOT part of framework core
(ADR-002 stdlib-only). Install in YOUR venv, not .claude/rag/venv:

    python3 -m venv .my-hyde-venv
    source .my-hyde-venv/bin/activate
    pip install anthropic sentence-transformers torch

Use:

    python3 examples/hyde-retrieve.py \\
        --query "como funciona o double-entry ledger?" \\
        --kb-dir ./docs ./src \\
        --top 3 \\
        --model claude-haiku-4-5

Output:
    Top-N matching files/chunks on stdout (one per line, with score).
    Hypothetical doc on stderr for transparency.

Why this isn't shipped in the framework core:
    - ADR-002 enforces stdlib-only.
    - anthropic SDK + sentence-transformers + torch is heavy.
    - Most adopters (Tier 0) don't need HyDE.
    - The recipe is more useful as adopter-controlled code.

This script is INTENTIONALLY minimal:
    - In-memory chunk store (not vector DB) — replace for prod
    - Single query, no batch
    - Single embedding model
    - No retry/backoff on Anthropic API errors

For production, see HYDE-RECIPE.md §6.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Tuple


HYPOTHETICAL_PROMPT = (
    "Write a 100-150 word technical paragraph that would answer the "
    "following query, in the style of project documentation. Be "
    "specific and use technical terminology that would appear in "
    "actual code or technical docs. Do not hedge — write as if "
    "stating known facts.\n\n"
    "Query: {query}\n\n"
    "Hypothetical answer paragraph:"
)


def collect_chunks(kb_dirs: List[Path], chunk_size: int = 400) -> List[Tuple[Path, int, str]]:
    """Walk kb_dirs, collect text files, chunk by paragraph blocks.

    Returns list of (file_path, chunk_index, text) tuples.
    Skips binary files, .git/, node_modules/, vendor/.
    """
    skip_dirs = {".git", "node_modules", "vendor", "__pycache__", ".venv", "venv"}
    text_exts = {".md", ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".sh", ".yaml", ".yml", ".toml", ".txt"}

    chunks: List[Tuple[Path, int, str]] = []
    for kb_dir in kb_dirs:
        if not kb_dir.is_dir():
            sys.stderr.write(f"warning: kb_dir not found: {kb_dir}\n")
            continue
        for path in kb_dir.rglob("*"):
            if any(part in skip_dirs for part in path.parts):
                continue
            if not path.is_file() or path.suffix not in text_exts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue

            # Simple chunking: paragraphs joined to ~chunk_size words
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            current: List[str] = []
            current_words = 0
            chunk_idx = 0
            for para in paragraphs:
                para_words = len(para.split())
                if current_words + para_words > chunk_size and current:
                    chunks.append((path, chunk_idx, "\n\n".join(current)))
                    chunk_idx += 1
                    current = [para]
                    current_words = para_words
                else:
                    current.append(para)
                    current_words += para_words
            if current:
                chunks.append((path, chunk_idx, "\n\n".join(current)))

    return chunks


def gen_hypothetical(query: str, model: str = "claude-haiku-4-5") -> str:
    """Generate a hypothetical doc paragraph via Anthropic SDK."""
    try:
        import anthropic
    except ImportError:
        sys.stderr.write(
            "error: anthropic SDK not installed. Run:\n"
            "  pip install anthropic\n"
        )
        sys.exit(3)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.stderr.write(
            "error: ANTHROPIC_API_KEY not set. Export it before running.\n"
        )
        sys.exit(4)

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=300,
        messages=[
            {
                "role": "user",
                "content": HYPOTHETICAL_PROMPT.format(query=query),
            }
        ],
    )
    # Guard: response.content[0] is a TextBlock for normal text completions
    # but could be tool_use / thinking / etc. for advanced configs.
    block = response.content[0]
    if not hasattr(block, "text"):
        sys.stderr.write(
            f"error: unexpected response block type: {type(block).__name__}\n"
            f"  expected TextBlock; got block without .text attribute.\n"
        )
        sys.exit(5)
    return block.text


def embed_and_search(
    hypothetical: str,
    chunks: List[Tuple[Path, int, str]],
    top_n: int,
    model_name: str = "BAAI/bge-large-en-v1.5",
) -> List[Tuple[Path, int, str, float]]:
    """Embed hypothetical + all chunks; cosine similarity top-N."""
    try:
        from sentence_transformers import SentenceTransformer, util
    except ImportError:
        sys.stderr.write(
            "error: sentence-transformers not installed. Run:\n"
            "  pip install sentence-transformers torch\n"
        )
        sys.exit(3)

    model = SentenceTransformer(model_name)

    chunk_texts = [text for _path, _idx, text in chunks]
    chunk_embs = model.encode(chunk_texts, convert_to_tensor=True)
    hyde_emb = model.encode([hypothetical], convert_to_tensor=True)

    scores = util.cos_sim(hyde_emb, chunk_embs)[0]
    top_indices = scores.argsort(descending=True)[:top_n]

    out: List[Tuple[Path, int, str, float]] = []
    for idx_t in top_indices:
        idx = int(idx_t)
        path, chunk_idx, text = chunks[idx]
        out.append((path, chunk_idx, text, float(scores[idx])))
    return out


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="HyDE retrieval recipe.")
    parser.add_argument("--query", required=True, help="User query")
    parser.add_argument(
        "--kb-dir",
        action="append",
        type=Path,
        required=True,
        help="Knowledge-base directory to index (repeatable)",
    )
    parser.add_argument("--top", type=int, default=3, help="Top N (default 3)")
    parser.add_argument(
        "--model",
        default="claude-haiku-4-5",
        help="Anthropic model for hypothetical gen (default haiku-4-5)",
    )
    parser.add_argument(
        "--embed-model",
        default="BAAI/bge-large-en-v1.5",
        help="Embedding model (default bge-large-en-v1.5)",
    )
    args = parser.parse_args(argv)

    sys.stderr.write(f"=== HyDE retrieval ===\n")
    sys.stderr.write(f"Query: {args.query}\n")
    sys.stderr.write(f"KB dirs: {[str(d) for d in args.kb_dir]}\n")
    sys.stderr.write(f"Indexing chunks...\n")

    chunks = collect_chunks(args.kb_dir)
    sys.stderr.write(f"Loaded {len(chunks)} chunks.\n")
    if not chunks:
        sys.stderr.write("error: no chunks loaded; check --kb-dir paths.\n")
        return 2

    sys.stderr.write(f"Generating hypothetical via {args.model}...\n")
    hypothetical = gen_hypothetical(args.query, model=args.model)
    sys.stderr.write("\n--- Hypothetical doc (discarded after retrieval) ---\n")
    sys.stderr.write(hypothetical)
    sys.stderr.write("\n--- end hypothetical ---\n\n")

    sys.stderr.write(f"Embedding + searching with {args.embed_model}...\n")
    results = embed_and_search(
        hypothetical=hypothetical,
        chunks=chunks,
        top_n=args.top,
        model_name=args.embed_model,
    )

    # Output: stdout = top-N results
    print(f"# HyDE top-{args.top} for: {args.query}")
    print()
    for path, chunk_idx, text, score in results:
        print(f"## {path}:{chunk_idx} (score={score:.4f})")
        print()
        print(text[:500] + ("..." if len(text) > 500 else ""))
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
