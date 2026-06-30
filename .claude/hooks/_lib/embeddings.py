"""Lexical tf-idf retrieval primitives — stdlib-only, no external deps.

PLAN-011 Phase 2. See ADR-029 for the decision to ship lexical first and
gate real embeddings behind ``CEO_REAL_EMBEDDINGS=1``.

## Design

The retrieval baseline is a bag-of-words tf-idf with **sublinear term
frequency** scaling and **smoothed inverse document frequency**:

- **Term frequency (sublinear):** ``1 + log(tf)`` (natural log). A term
  appearing 10 times in a long SKILL.md should NOT dominate a term
  appearing 1 time in a short description by a factor of 10.
- **Inverse document frequency (smoothed):** ``log((N+1) / (df+1)) + 1``.
  The ``+1`` in numerator + denominator prevents divide-by-zero on
  unseen terms; the outer ``+ 1`` prevents idf==0 for terms appearing
  in every document (still a faint signal vs idf==0 "throw away term").
- **Cosine similarity:** ``dot(a, b) / (‖a‖ · ‖b‖)``. Returns 0.0 on
  either empty vector (never raises).

All math runs on ``math.log`` and ``math.sqrt`` — no numpy, no sklearn.
The vectors are ``dict[str, float]`` (sparse; terms not in the vector
contribute zero).

## Feature flag

Callers invoke ``get_embedder()``. The returned callable takes a
``(text, idf_map)`` pair and returns a vector dict.

- Default: lexical tf-idf (this module's ``tfidf_vector``).
- ``CEO_REAL_EMBEDDINGS=1`` + a reachable provider: attempts to call a
  real embedding endpoint. Sprint 11 does NOT ship the provider — the
  env var is reserved. Turning it on without a provider falls back to
  lexical and logs a breadcrumb via the ``audit-log.errors`` file.

## Stopword list

A small inline English stopword list (50 words) dampens the most common
words. Not comprehensive — the idf penalty already discounts them. We
keep it inline so the retrieval is deterministic without a data file.
"""

from __future__ import annotations

import math
import os
import re
import sys
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple


# Small inline stopword list — keep small (≤50 words), inline, deterministic.
# These are the words that would otherwise dominate tf without contributing
# semantic signal. We do NOT try to cover everything; idf smoothing
# naturally discounts the rest.
_STOPWORDS: Set[str] = {
    "a", "an", "the", "and", "or", "but", "if", "then", "when",
    "of", "for", "to", "in", "on", "by", "at", "with", "from", "as",
    "is", "are", "was", "were", "be", "been",
    "do", "does", "did",
    "has", "have", "had",
    "it", "its", "this", "that", "these", "those",
    "we", "our", "you", "your", "they", "their",
    "not", "no",
    "so", "than", "such",
}


# Tokenizer regex: word characters (unicode-aware) of length >= 2.
# Hyphens inside a word (e.g. "frontend-data-layer") split — we want the
# parts to match "frontend" OR "data" OR "layer" independently. This
# matters for SKILL.md filenames.
_TOKEN_RE = re.compile(r"[A-Za-z0-9]+", re.UNICODE)


def tokenize(text: str, *, drop_stopwords: bool = True, min_len: int = 2) -> List[str]:
    """Tokenize text into lowercase word tokens.

    Strips punctuation, splits on whitespace and non-word boundaries,
    drops tokens shorter than ``min_len``, optionally drops stopwords.

    Args:
        text: input string (may be multi-line).
        drop_stopwords: filter the inline stopword list. Default True.
        min_len: minimum token length. Default 2.

    Returns:
        List of lowercase tokens, in original order. Preserves duplicates
        (the caller computes tf).
    """
    if not text:
        return []
    tokens = [m.group(0).lower() for m in _TOKEN_RE.finditer(text)]
    if min_len > 1:
        tokens = [t for t in tokens if len(t) >= min_len]
    if drop_stopwords:
        tokens = [t for t in tokens if t not in _STOPWORDS]
    return tokens


def tf(tokens: Iterable[str]) -> Dict[str, int]:
    """Compute raw term frequency: dict term -> count."""
    out: Dict[str, int] = {}
    for t in tokens:
        out[t] = out.get(t, 0) + 1
    return out


def sublinear_tf(tf_dict: Dict[str, int]) -> Dict[str, float]:
    """Sublinear tf scaling: ``1 + log(tf)`` (natural log).

    Rationale: raw tf means a term appearing 100 times dominates a term
    appearing 10 times by a factor of 10 — but the second occurrence of
    a term is far less informative than the first. ``1 + log(tf)``
    compresses the dynamic range while preserving monotonicity:

        tf=1  -> 1.0
        tf=2  -> 1.693
        tf=10 -> 3.303
        tf=100 -> 5.605

    Returns a new dict with float values.
    """
    out: Dict[str, float] = {}
    for term, count in tf_dict.items():
        if count <= 0:
            continue
        out[term] = 1.0 + math.log(count)
    return out


def idf(doc_token_sets: List[Set[str]], total_docs: Optional[int] = None) -> Dict[str, float]:
    """Smoothed inverse document frequency over a corpus.

    Formula: ``idf(t) = log((N + 1) / (df(t) + 1)) + 1``

    Where:
    - N = total number of documents
    - df(t) = number of documents containing term t
    - The ``+1`` smoothing prevents divide-by-zero on a hypothetical
      unseen term (df=0 -> idf = log(N+1) + 1 > 0).
    - The outer ``+1`` prevents idf==0 for terms that appear in EVERY
      document — they still carry a faint signal vs a term we never
      saw. Some corpora (Lucene classic idf) do ``+1`` inside only;
      we follow scikit-learn's smooth_idf=True convention.

    Args:
        doc_token_sets: list of token-sets, one per document. Each set
            is the UNIQUE tokens in that document.
        total_docs: optional override for N. If None, derived from
            ``len(doc_token_sets)``.

    Returns:
        dict term -> idf_value (float). Terms never seen are absent;
        callers should fall back to the smoothed formula using the
        returned total_docs for unseen-term idf.
    """
    n = int(total_docs) if total_docs is not None else len(doc_token_sets)
    if n <= 0:
        return {}
    # Count document frequency: in how many docs does each term appear?
    df_counter: Dict[str, int] = {}
    for doc_terms in doc_token_sets:
        for t in doc_terms:
            df_counter[t] = df_counter.get(t, 0) + 1
    # Smoothed idf
    out: Dict[str, float] = {}
    for term, df_val in df_counter.items():
        out[term] = math.log((n + 1) / (df_val + 1)) + 1.0
    return out


def tfidf_vector(
    text: str,
    idf_map: Dict[str, float],
    *,
    total_docs: Optional[int] = None,
    drop_stopwords: bool = True,
) -> Dict[str, float]:
    """Compute a tf-idf vector for one document text.

    Uses ``sublinear_tf`` for the tf side and the supplied ``idf_map``
    for the idf side. Terms in ``text`` not present in ``idf_map`` fall
    back to the smoothed idf for an unseen term (``log((N+1)/1) + 1``)
    when ``total_docs`` is provided; otherwise they contribute zero.

    Args:
        text: document text (string).
        idf_map: precomputed idf values from a reference corpus.
        total_docs: N from the reference corpus. Enables unseen-term
            handling; if None, unseen terms get weight 0.0.
        drop_stopwords: forwarded to ``tokenize``.

    Returns:
        dict term -> weight (float). Sparse; omitted terms are 0.0.
    """
    tokens = tokenize(text, drop_stopwords=drop_stopwords)
    if not tokens:
        return {}
    tf_dict = tf(tokens)
    stf = sublinear_tf(tf_dict)
    unseen_idf = None
    if total_docs is not None and total_docs > 0:
        unseen_idf = math.log((total_docs + 1) / 1) + 1.0
    out: Dict[str, float] = {}
    for term, tf_weight in stf.items():
        term_idf = idf_map.get(term)
        if term_idf is None:
            if unseen_idf is None:
                continue
            term_idf = unseen_idf
        out[term] = tf_weight * term_idf
    return out


def cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
    """Cosine similarity of two sparse vectors.

    ``cos(a, b) = dot(a, b) / (‖a‖ · ‖b‖)``

    Returns 0.0 if either vector is empty or has zero magnitude.
    Guaranteed to be in ``[0.0, 1.0]`` when both vectors have
    non-negative weights (which lexical tf-idf always produces).

    Symmetric: ``cosine(a, b) == cosine(b, a)`` (to float precision).
    Identity: ``cosine(a, a) == 1.0`` for any non-empty a (to float
    precision).

    Args:
        a, b: sparse vectors as dict[str, float].

    Returns:
        Float similarity in [0.0, 1.0].
    """
    if not a or not b:
        return 0.0
    # Iterate the smaller dict for dot product
    if len(a) > len(b):
        a, b = b, a
    dot = 0.0
    for term, w_a in a.items():
        w_b = b.get(term)
        if w_b is not None:
            dot += w_a * w_b
    if dot == 0.0:
        return 0.0
    norm_a = math.sqrt(sum(w * w for w in a.values()))
    norm_b = math.sqrt(sum(w * w for w in b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# Feature flag — get_embedder()
# ---------------------------------------------------------------------------

Embedder = Callable[[str, Dict[str, float]], Dict[str, float]]


def _lexical_embedder(text: str, idf_map: Dict[str, float]) -> Dict[str, float]:
    """Default lexical tf-idf embedder (used when the flag is off)."""
    return tfidf_vector(text, idf_map)


def _real_embedder_available() -> bool:
    """Is a real embedding provider reachable? Sprint 11: always False.

    Sprint 11 reserves the ``CEO_REAL_EMBEDDINGS=1`` flag and the
    ``get_embedder()`` seam but does NOT ship a provider. Later sprints
    can land OpenAI/local wrapper here and flip this to True.
    """
    return False


def _breadcrumb(msg: str) -> None:
    """Write a single-line breadcrumb to audit-log.errors if configured."""
    err_path = os.environ.get("CEO_AUDIT_LOG_ERR")
    if not err_path:
        return
    try:
        Path(err_path).parent.mkdir(parents=True, exist_ok=True)
        with open(err_path, "a", encoding="utf-8") as fh:
            fh.write(f"embeddings: {msg}\n")
    except OSError:
        pass


def get_embedder() -> Embedder:
    """Return the active embedder callable.

    Returns:
        Callable (text, idf_map) -> vector dict.

    Behavior:
        - Default: lexical tf-idf.
        - If ``CEO_REAL_EMBEDDINGS=1`` AND a real provider is reachable,
          returns the real embedder. Sprint 11 never reaches this
          branch (no provider shipped).
        - If ``CEO_REAL_EMBEDDINGS=1`` without a provider, falls back
          to lexical and writes a breadcrumb.
    """
    want_real = os.environ.get("CEO_REAL_EMBEDDINGS") == "1"
    if want_real:
        if _real_embedder_available():
            # Sprint 12+ will replace this branch with a real provider call.
            return _lexical_embedder  # pragma: no cover (never reached in Sprint 11)
        _breadcrumb("CEO_REAL_EMBEDDINGS=1 but no provider available — falling back to lexical")
    return _lexical_embedder


__all__ = [
    "Embedder",
    "cosine",
    "get_embedder",
    "idf",
    "sublinear_tf",
    "tf",
    "tfidf_vector",
    "tokenize",
]
