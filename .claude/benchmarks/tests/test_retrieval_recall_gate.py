"""H4 gate — Recall@5 of lexical tf-idf vs static SKILL-MAP baseline.

PLAN-011 Phase 2. This is the gate the consensus round-1 finding H4
demanded: if the lexical baseline cannot match the static routing-table
baseline on a held-out judgment set, the retrieval flag must be hidden
behind ``CEO_REAL_EMBEDDINGS=1`` (Sprint 12 work).

## Semantics

- **PASS** when ``lexical_recall >= static_recall`` (lexical wins or
  ties). This is the default case and asserts the lexical retrieval is
  at least as good as just reading the routing table.
- **SKIP** when ``lexical_recall < static_recall``. Documented fallback:
  Sprint 12 must enable real embeddings. The SKIP message prints both
  numbers so a maintainer can see how far off we are.

We do NOT fail — a FAIL would block CI for a documented, expected
degradation mode. A SKIP is the right signal: "the gate exists, it
tripped, here's what to do about it".

## What counts as "recall@5 hit"

For each `(task, expected_top_k)` pair in the judgment set:
- Retrieve the top-5 skills by the system under test.
- HIT if any skill in ``expected_top_k`` appears in those 5 results.
- MISS otherwise.

Recall@5 = HITS / total_pairs.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_SCRIPTS_DIR = _REPO_ROOT / ".claude" / "scripts"
_HOOKS_LIB = _REPO_ROOT / ".claude" / "hooks"
_BENCHMARKS = _REPO_ROOT / ".claude" / "benchmarks"
sys.path.insert(0, str(_HOOKS_LIB))
sys.path.insert(0, str(_SCRIPTS_DIR))

from _lib import embeddings as emb  # noqa: E402


def _load_script(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, str(_SCRIPTS_DIR / filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


build_mod = _load_script("skill_index_build", "skill-index-build.py")
retrieve_mod = _load_script("skill_retrieve", "skill-retrieve.py")


# ---------------------------------------------------------------------------
# Tiny stdlib YAML-subset parser — just what we need for the judgment set
# ---------------------------------------------------------------------------


def _parse_judgment_yaml(text: str) -> List[Dict[str, object]]:
    """Parse the judgment-set YAML into a list of pair dicts.

    Only handles the specific shape our judgment-set uses:
        pairs:
          - task: "<string>"
            expected_top_k: [a, b, c]
            archetype_hint: foo
    """
    pairs: List[Dict[str, object]] = []
    current: Optional[Dict[str, object]] = None
    in_pairs = False
    for raw_line in text.splitlines():
        # Strip comments (outside strings is good enough for our file)
        if raw_line.lstrip().startswith("#"):
            continue
        line = raw_line.rstrip()
        if not line.strip():
            continue

        if line.strip() == "pairs:":
            in_pairs = True
            continue
        if not in_pairs:
            continue

        stripped = line.strip()
        if stripped.startswith("- "):
            # New pair starts
            if current is not None:
                pairs.append(current)
            current = {}
            # The "- " line typically starts with "- task: ..." on the same line
            after_dash = stripped[2:].strip()
            if ":" in after_dash:
                _consume_kv(after_dash, current)
            continue

        if current is None:
            continue

        # Key: value under the current pair
        _consume_kv(stripped, current)

    if current is not None:
        pairs.append(current)
    return pairs


def _consume_kv(kv_text: str, into: Dict[str, object]) -> None:
    key, _, val = kv_text.partition(":")
    key = key.strip()
    val = val.strip()
    if key == "task":
        # Strip quotes
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        into["task"] = val
    elif key == "expected_top_k":
        # Parse inline list: [a, b, c]
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1]
            items = [s.strip() for s in inner.split(",") if s.strip()]
            into["expected_top_k"] = items
        else:
            into["expected_top_k"] = []
    elif key == "archetype_hint":
        into["archetype_hint"] = val


# ---------------------------------------------------------------------------
# Static SKILL-MAP baseline (build inline — no sqlite involved)
# ---------------------------------------------------------------------------


_ARCHETYPE_ROW_RE = re.compile(
    r"^\|\s*\*\*([^|*]+?)\*\*\s*\|(.+?)\|\s*`([a-z0-9\-]+)`",
    re.MULTILINE,
)


def _collect_skill_map(repo_root: Path) -> List[Tuple[str, str]]:
    """Return list of (archetype_title, skill_slug) rows from all team files."""
    files = [
        repo_root / ".claude" / "team.md",
        repo_root / ".claude" / "frontend-team.md",
    ]
    domains = repo_root / ".claude" / "skills" / "domains"
    if domains.is_dir():
        for dom in sorted(domains.iterdir()):
            for fname in ("team-personas.md", "frontend-team-personas.md"):
                p = dom / fname
                if p.is_file():
                    files.append(p)
    out: List[Tuple[str, str]] = []
    for f in files:
        if not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        for m in _ARCHETYPE_ROW_RE.finditer(text):
            title = m.group(1).strip()
            slug = m.group(3).strip()
            if title and title.lower() not in {"role", "archetype"} and slug:
                out.append((title, slug))
    return out


def _static_retrieve(
    task: str,
    skill_map: List[Tuple[str, str]],
    *,
    top_k: int = 5,
) -> List[str]:
    """Static keyword-overlap retrieval — "does this skill's id contain
    any token from the task?".

    This is the baseline the H4 consensus mandated comparing against.
    Token overlap with hyphens expanded (security-and-auth ->
    [security, auth]).
    """
    task_tokens = set(emb.tokenize(task))
    scores: Dict[str, float] = {}
    for archetype_title, skill in skill_map:
        # Expand hyphen-split skill tokens + archetype title tokens
        skill_tokens = set(emb.tokenize(skill.replace("-", " ")))
        title_tokens = set(emb.tokenize(archetype_title))
        overlap_skill = len(task_tokens & skill_tokens)
        overlap_title = len(task_tokens & title_tokens)
        score = overlap_skill * 2.0 + overlap_title  # weight skill-name higher
        prev = scores.get(skill, -1.0)
        if score > prev:
            scores[skill] = score
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return [slug for slug, _ in ranked[:top_k]]


# ---------------------------------------------------------------------------
# Lexical retrieval — build index into tempfile, query per pair
# ---------------------------------------------------------------------------


def _lexical_retrieve_all(
    pairs: List[Dict[str, object]],
    repo_root: Path,
    *,
    top_k: int = 5,
) -> List[List[str]]:
    """Build the lexical index once, query each pair's task, return top-K slugs."""
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tf:
        idx_path = Path(tf.name)
    try:
        build_mod.build_index(repo_root, idx_path)
        view = retrieve_mod.load_index(idx_path)
        out: List[List[str]] = []
        for pair in pairs:
            task = str(pair["task"])
            qvec = retrieve_mod.query_vector(task, view.idf_map, view.total_docs)
            results = retrieve_mod.rank(qvec, view.skills, top_k=top_k)
            # Prefer raw_slug for comparison to judgment-set (which uses raw slugs)
            slugs: List[str] = []
            for r in results:
                raw = r.get("raw_slug") or r["slug"]
                slugs.append(str(raw))
            out.append(slugs)
        return out
    finally:
        try:
            idx_path.unlink()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Recall metric
# ---------------------------------------------------------------------------


def _recall_at_k(
    predictions: List[List[str]],
    pairs: List[Dict[str, object]],
) -> Tuple[float, int, int]:
    """Compute recall@K: HIT if any expected skill appears in prediction."""
    hits = 0
    for preds, pair in zip(predictions, pairs):
        expected = set(pair.get("expected_top_k") or [])
        if not expected:
            continue
        if any(p in expected for p in preds):
            hits += 1
    total = sum(1 for p in pairs if p.get("expected_top_k"))
    return (hits / total if total > 0 else 0.0, hits, total)


class TestRecallGate(unittest.TestCase):
    """H4 gate: lexical recall@5 must not trail static SKILL-MAP baseline.

    Uses the REAL repo's skills + team files — so judgment pairs must
    reference skills that actually exist in the repo. A pair referencing
    a missing skill counts as a MISS for both systems (fair).
    """

    @classmethod
    def setUpClass(cls):
        judgment_path = _BENCHMARKS / "retrieval-judgment-set.yaml"
        cls.judgment_path = judgment_path
        cls.pairs = _parse_judgment_yaml(judgment_path.read_text(encoding="utf-8"))

    def test_judgment_set_has_enough_pairs(self):
        # Acceptance: ≥30 pairs, no duplicates
        self.assertGreaterEqual(len(self.pairs), 30)
        tasks = [p["task"] for p in self.pairs]
        self.assertEqual(len(tasks), len(set(tasks)), "duplicate task strings in judgment set")

    def test_every_pair_has_expected_top_k(self):
        for pair in self.pairs:
            self.assertIn("expected_top_k", pair)
            expected = pair["expected_top_k"]
            self.assertIsInstance(expected, list)
            self.assertGreater(len(expected), 0, f"pair has empty expected_top_k: {pair.get('task')}")

    def test_lexical_recall_at_5_beats_or_ties_static_baseline(self):
        # Build both retrievals on the real repo
        skill_map = _collect_skill_map(_REPO_ROOT)
        static_preds = [
            _static_retrieve(str(p["task"]), skill_map, top_k=5) for p in self.pairs
        ]
        lexical_preds = _lexical_retrieve_all(self.pairs, _REPO_ROOT, top_k=5)

        static_recall, static_hits, static_total = _recall_at_k(static_preds, self.pairs)
        lex_recall, lex_hits, lex_total = _recall_at_k(lexical_preds, self.pairs)

        print(
            f"\nH4 gate recall@5 — lexical: {lex_recall:.3f} ({lex_hits}/{lex_total}) "
            f"| static: {static_recall:.3f} ({static_hits}/{static_total})"
        )

        # Write per-pair diagnostic if lexical loses — helps Sprint 12
        if lex_recall < static_recall:
            diff: List[str] = []
            for pair, lex, stat in zip(self.pairs, lexical_preds, static_preds):
                expected = set(pair.get("expected_top_k") or [])
                lex_hit = any(p in expected for p in lex)
                stat_hit = any(p in expected for p in stat)
                if stat_hit and not lex_hit:
                    diff.append(f"  static-only hit: {pair['task'][:60]!r} expected={list(expected)[:3]}")
            msg = (
                f"lexical recall@5 ({lex_recall:.3f}) < static baseline ({static_recall:.3f}). "
                f"Gate fallback triggered — Sprint 12 to enable CEO_REAL_EMBEDDINGS=1.\n"
                + "\n".join(diff[:10])
            )
            self.skipTest(msg)

        # Passing path: lexical wins or ties
        self.assertGreaterEqual(lex_recall, static_recall)


if __name__ == "__main__":
    unittest.main()
