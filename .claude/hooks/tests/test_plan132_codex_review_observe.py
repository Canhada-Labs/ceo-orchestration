"""PLAN-132 / ADR-145 — Component A regression.

Pins the review-intent gate (R2) + branch-binding hash parity (R1) for the
codex_review_invoked emit folded into check_codex_response.py. The gate must be
high-precision (positives emit, generation/topic-only prompts do NOT), and the
emitted target_ref_hash must be byte-identical to persona_demand_scan's so the
resolver can stitch the match.
"""
from __future__ import annotations

import hashlib
import sys
import unicodedata
from pathlib import Path
from unittest import mock


def _repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / ".claude" / "hooks").is_dir():
            return parent
    raise RuntimeError("repo root with .claude/hooks/ not found")


_ROOT = _repo_root()
sys.path.insert(0, str(_ROOT / ".claude" / "hooks"))
sys.path.insert(0, str(_ROOT / ".claude" / "scripts"))

from _lib.testing import TestEnvContext  # noqa: E402
import check_codex_response as ccr  # noqa: E402
import persona_demand_scan as pds  # noqa: E402


class TestReviewIntentGate(TestEnvContext):
    POSITIVES = [
        "Please review this diff for correctness:\n```\ndiff --git a/x b/x\n@@ -1 +1 @@\n```",
        "Review the uncommitted changes for bugs",
        "As a code reviewer, find bugs in:\n```python\nx=1\n```",
        "Audit this patch:\n```\n+ foo()\n```",
        "refute this change:\n```\n--- a\n+++ b\n```",
    ]
    NEGATIVES = [
        # generation-led, even though it name-drops audit/diff/security
        "codex, write me a function that audits the diff for security",
        "review this product spec for typos",       # verb but no diff/code artifact
        "security audit of our auth system",         # topic nouns only
        "implement a code reviewer agent",           # generation, no real verb/framing
        "summarize the changes in this file",        # no review verb, no diff
        # Codex pair-rail P1 #1: soft "code reviewer" framing must NOT qualify a
        # generation request as a review, even with a code fence present.
        "As a code reviewer, implement this fix:\n```python\nx = 1\n```",
        "",                                          # empty
    ]

    def test_positives_emit(self):
        for p in self.POSITIVES:
            self.assertTrue(ccr._is_review_intent(p), f"should be review-intent: {p!r}")

    def test_negatives_suppressed(self):
        # Bias to under-emission: a false match would silently GREEN the detector.
        for p in self.NEGATIVES:
            self.assertFalse(ccr._is_review_intent(p), f"should NOT be review-intent: {p!r}")

    def test_non_string_inputs_safe(self):
        for bad in (None, 123, [], {}):
            self.assertFalse(ccr._is_review_intent(bad))


class TestBranchBinding(TestEnvContext):
    def test_branch_hash_byte_identical_to_scanner(self):
        for br in ("feature/foo", "claude/s221-codex-match", "fix-bug-9", "x"):
            mine = hashlib.sha256(
                unicodedata.normalize("NFKC", "branch:" + br).encode("utf-8")
            ).hexdigest()[:12]
            self.assertEqual(mine, pds._target_ref_hash("branch:" + br),
                             f"hash must match scanner for branch {br!r}")

    def test_trunk_and_detached_yield_empty(self):
        # We can't fake a git branch here, but the function must return '' for
        # trunk/empty/failure paths — assert the contract on a non-repo cwd.
        h = ccr._current_branch_target_ref_hash("/nonexistent-path-xyz")
        self.assertEqual(h, "")


class TestObserveFailOpen(TestEnvContext):
    def test_observe_never_raises(self):
        class _Ev:
            tool_input = None
        # No tool_input dict, bogus object, kill-switch — none may raise.
        ccr._observe_codex_review(_Ev())
        ccr._observe_codex_review(object())
        with mock.patch.dict("os.environ", {"CEO_CODEX_REVIEW_OBSERVE": "0"}):
            ccr._observe_codex_review(_Ev())  # kill-switch path


if __name__ == "__main__":
    import unittest
    unittest.main()
