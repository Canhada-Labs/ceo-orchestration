"""Unit tests for _lib/embeddings.py — stdlib lexical tf-idf primitives.

PLAN-011 Phase 2 acceptance gate: all math functions have behavior
assertions, not just smoke tests. Each test pins exact numbers so a
future refactor of the formula would fail loudly.
"""

from __future__ import annotations

import math
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Import the hooks _lib package
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_HOOKS_LIB = _REPO_ROOT / ".claude" / "hooks"
sys.path.insert(0, str(_HOOKS_LIB))

# Import from state_store's test infra for env isolation
from _lib import embeddings as emb  # noqa: E402


class TestTokenize(unittest.TestCase):
    def test_basic_lowercasing_and_split(self):
        out = emb.tokenize("Hello World FOO", drop_stopwords=False)
        self.assertEqual(out, ["hello", "world", "foo"])

    def test_punctuation_stripped(self):
        out = emb.tokenize("hello, world! foo-bar.baz", drop_stopwords=False)
        # Hyphens and periods split words — "foo-bar.baz" -> foo, bar, baz
        self.assertEqual(out, ["hello", "world", "foo", "bar", "baz"])

    def test_stopwords_dropped_by_default(self):
        out = emb.tokenize("the quick brown fox is in the box")
        # Drops: the, is, in. Keeps: quick, brown, fox, box.
        self.assertEqual(out, ["quick", "brown", "fox", "box"])

    def test_min_len_filter(self):
        out = emb.tokenize("a b cd efg", drop_stopwords=False, min_len=3)
        self.assertEqual(out, ["efg"])

    def test_empty_string_returns_empty_list(self):
        self.assertEqual(emb.tokenize(""), [])
        self.assertEqual(emb.tokenize(None or ""), [])

    def test_preserves_duplicates_for_tf(self):
        # tf() relies on tokenize() preserving duplicates in order
        out = emb.tokenize("foo foo bar foo baz", drop_stopwords=False)
        self.assertEqual(out, ["foo", "foo", "bar", "foo", "baz"])


class TestTfAndSublinearTf(unittest.TestCase):
    def test_tf_counts(self):
        self.assertEqual(emb.tf(["a", "b", "a", "c", "a"]), {"a": 3, "b": 1, "c": 1})

    def test_sublinear_tf_monotonic(self):
        # tf=1 < tf=2 < tf=10 < tf=100 in sublinear scaling
        one = emb.sublinear_tf({"x": 1})["x"]
        two = emb.sublinear_tf({"x": 2})["x"]
        ten = emb.sublinear_tf({"x": 10})["x"]
        hundred = emb.sublinear_tf({"x": 100})["x"]
        self.assertLess(one, two)
        self.assertLess(two, ten)
        self.assertLess(ten, hundred)

    def test_sublinear_tf_exact_values(self):
        out = emb.sublinear_tf({"a": 1, "b": 2, "c": 10})
        # 1 + log(1) = 1.0
        # 1 + log(2) = 1.6931...
        # 1 + log(10) = 3.3026...
        self.assertAlmostEqual(out["a"], 1.0, places=6)
        self.assertAlmostEqual(out["b"], 1.0 + math.log(2), places=6)
        self.assertAlmostEqual(out["c"], 1.0 + math.log(10), places=6)

    def test_sublinear_tf_compresses_dynamic_range(self):
        # Raw tf ratio tf=100:tf=1 = 100:1
        # Sublinear tf ratio must be much smaller (~5.6:1)
        low = emb.sublinear_tf({"x": 1})["x"]
        high = emb.sublinear_tf({"x": 100})["x"]
        ratio = high / low
        self.assertLess(ratio, 10.0, "sublinear_tf should compress 100x -> <10x")

    def test_sublinear_tf_ignores_zero_and_negative(self):
        out = emb.sublinear_tf({"a": 0, "b": -1, "c": 5})
        self.assertNotIn("a", out)
        self.assertNotIn("b", out)
        self.assertIn("c", out)


class TestIdf(unittest.TestCase):
    def test_idf_smoothing_prevents_zero(self):
        # A term in every document should still have a positive idf
        # due to the outer +1.
        docs = [
            {"common", "a"},
            {"common", "b"},
            {"common", "c"},
        ]
        out = emb.idf(docs)
        # df=3, N=3 -> log((3+1)/(3+1)) + 1 = log(1) + 1 = 1.0
        self.assertAlmostEqual(out["common"], 1.0, places=6)
        # df=1, N=3 -> log((3+1)/(1+1)) + 1 = log(2) + 1 ~= 1.693
        self.assertAlmostEqual(out["a"], math.log(2) + 1.0, places=6)

    def test_idf_empty_corpus_returns_empty(self):
        self.assertEqual(emb.idf([]), {})

    def test_idf_explicit_total_docs_override(self):
        # Pretend we saw only 1 doc in a synthetic corpus of size 10
        out = emb.idf([{"rare"}], total_docs=10)
        # df=1, N=10 -> log((10+1)/2) + 1 = log(5.5) + 1 ~= 2.7047
        self.assertAlmostEqual(out["rare"], math.log(5.5) + 1.0, places=6)

    def test_idf_rare_term_ranks_higher_than_common(self):
        docs = [
            {"rare", "common"},
            {"common"},
            {"common"},
            {"common"},
        ]
        out = emb.idf(docs)
        self.assertGreater(out["rare"], out["common"])


class TestTfidfVector(unittest.TestCase):
    def test_basic_composition(self):
        corpus = [
            {"foo", "bar"},
            {"bar", "baz"},
            {"baz", "qux"},
        ]
        idf_map = emb.idf(corpus)
        vec = emb.tfidf_vector("foo bar bar", idf_map, total_docs=3)
        # Should have weights for foo (tf=1) and bar (tf=2)
        self.assertIn("foo", vec)
        self.assertIn("bar", vec)
        # bar appears in 2 docs; foo in 1 doc. "foo" is rarer -> higher idf
        # but "bar" has higher tf. Both must be positive.
        self.assertGreater(vec["foo"], 0)
        self.assertGreater(vec["bar"], 0)

    def test_unseen_term_zero_when_no_total_docs(self):
        vec = emb.tfidf_vector("mysteryword", {"other": 2.0})
        self.assertNotIn("mysteryword", vec)

    def test_unseen_term_has_weight_when_total_docs_provided(self):
        vec = emb.tfidf_vector("mysteryword", {"other": 2.0}, total_docs=10)
        self.assertIn("mysteryword", vec)
        self.assertGreater(vec["mysteryword"], 0)

    def test_empty_text_returns_empty_vector(self):
        self.assertEqual(emb.tfidf_vector("", {"a": 1.0}), {})

    def test_all_stopwords_returns_empty(self):
        vec = emb.tfidf_vector("the and or but", {"a": 1.0})
        self.assertEqual(vec, {})


class TestCosine(unittest.TestCase):
    def test_identity(self):
        # cos(a, a) = 1.0 for any non-empty a
        v = {"foo": 1.0, "bar": 2.0, "baz": 3.5}
        self.assertAlmostEqual(emb.cosine(v, v), 1.0, places=6)

    def test_symmetry(self):
        a = {"x": 1.0, "y": 2.0}
        b = {"x": 0.5, "z": 3.0}
        self.assertAlmostEqual(emb.cosine(a, b), emb.cosine(b, a), places=10)

    def test_orthogonal_vectors_return_zero(self):
        a = {"foo": 1.0, "bar": 1.0}
        b = {"baz": 1.0, "qux": 1.0}
        self.assertEqual(emb.cosine(a, b), 0.0)

    def test_empty_vector_returns_zero(self):
        self.assertEqual(emb.cosine({}, {"x": 1.0}), 0.0)
        self.assertEqual(emb.cosine({"x": 1.0}, {}), 0.0)
        self.assertEqual(emb.cosine({}, {}), 0.0)

    def test_cosine_bounded_in_unit_interval(self):
        # tf-idf produces non-negative weights; cos must be in [0, 1]
        a = {"x": 3.0, "y": 4.0}
        b = {"x": 6.0, "y": 8.0}
        # Same direction -> cos = 1.0
        self.assertAlmostEqual(emb.cosine(a, b), 1.0, places=6)

    def test_cosine_half_overlap(self):
        # Known value: a=(1,0), b=(1,1). cos = 1/sqrt(2) ~= 0.7071
        a = {"x": 1.0}
        b = {"x": 1.0, "y": 1.0}
        self.assertAlmostEqual(emb.cosine(a, b), 1 / math.sqrt(2), places=6)

    def test_zero_norm_handled(self):
        # All-zero weights (shouldn't happen from tfidf, but test robustness)
        a = {"x": 0.0, "y": 0.0}
        b = {"x": 1.0}
        self.assertEqual(emb.cosine(a, b), 0.0)


class TestGetEmbedder(unittest.TestCase):
    def setUp(self):
        self._snapshot = {
            "CEO_REAL_EMBEDDINGS": os.environ.get("CEO_REAL_EMBEDDINGS"),
            "CEO_AUDIT_LOG_ERR": os.environ.get("CEO_AUDIT_LOG_ERR"),
        }

    def tearDown(self):
        for k, v in self._snapshot.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_default_returns_lexical_embedder(self):
        os.environ.pop("CEO_REAL_EMBEDDINGS", None)
        fn = emb.get_embedder()
        vec = fn("hello world", {"hello": 1.0, "world": 1.0})
        self.assertIsInstance(vec, dict)
        self.assertIn("hello", vec)

    def test_real_embeddings_flag_falls_back_when_no_provider(self):
        # Sprint 11 ships no provider — flag should write breadcrumb and
        # return the lexical embedder.
        with tempfile.TemporaryDirectory() as td:
            err_path = Path(td) / "audit-log.errors"
            os.environ["CEO_AUDIT_LOG_ERR"] = str(err_path)
            os.environ["CEO_REAL_EMBEDDINGS"] = "1"
            fn = emb.get_embedder()
            # Still works because it fell back to lexical
            vec = fn("hello", {"hello": 1.0})
            self.assertIn("hello", vec)
            # Breadcrumb should exist
            self.assertTrue(err_path.is_file())
            content = err_path.read_text()
            self.assertIn("CEO_REAL_EMBEDDINGS", content)


class TestStopwordListSize(unittest.TestCase):
    def test_stopword_list_is_bounded(self):
        # Constraint: ≤50 common English words, inline.
        self.assertLessEqual(len(emb._STOPWORDS), 50)
        self.assertGreater(len(emb._STOPWORDS), 20)


if __name__ == "__main__":
    unittest.main()
