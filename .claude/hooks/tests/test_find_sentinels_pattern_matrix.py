"""_find_sentinels pattern-matrix tests (fixture-based).

Builds a synthetic ``.claude/plans/`` tree in a tmpdir and asserts that
``_find_sentinels`` discovers each supported sentinel path pattern and
rejects a novel (non-allowlisted) ``architect/*`` subdir. This does NOT
depend on the live plan corpus — the distributed repo ships only schemas,
examples, and test fixtures under ``.claude/plans/``.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS = REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))


class TestFindSentinelsPatternMatrix(unittest.TestCase):
    """Explicit glob union + grandfather allowlist (synthetic tree)."""

    # Every sentinel path the pattern union in _find_sentinels should find.
    _SENTINELS = (
        "PLAN-100/architect/round-4/approved.md",
        "PLAN-085/approved.md",
        "PLAN-085/wave-0-approved.md",
        "PLAN-083/architect/wave-0a/approved.md",
        "PLAN-083/architect/wave-0b/approved.md",
        "PLAN-083/architect/wave-1-2/approved.md",
        "PLAN-083/architect/wave-minus-1/approved.md",
        "PLAN-083/staging/review/approved.md",
        "PLAN-085/approved-amendment-2026-05-12.md",
    )
    # A novel architect/* subdir NOT in the pattern union — must be ignored.
    _ORPHAN = "PLAN-200/architect/novel-subdir/approved.md"

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="ceo-sentinels-")).resolve()
        plans = self.root / ".claude" / "plans"
        for rel in self._SENTINELS + (self._ORPHAN,):
            p = plans / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("approved (synthetic test fixture)\n", encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def _names(self) -> list:
        from check_canonical_edit import _find_sentinels
        sentinels = _find_sentinels(self.root)
        return [str(p.relative_to(self.root)) for p in sentinels]

    def test_discovers_round_n_pattern(self) -> None:
        self.assertTrue(
            any("architect/round-4/approved.md" in n for n in self._names()),
            msg="round-4 sentinel not discovered",
        )

    def test_discovers_plan_root_sentinel(self) -> None:
        self.assertTrue(
            any(n == ".claude/plans/PLAN-085/approved.md" for n in self._names()),
            msg="plan-root sentinel PLAN-085/approved.md not discovered",
        )

    def test_discovers_wave_dash_n_amendment_pattern(self) -> None:
        self.assertTrue(
            any("wave-0-approved.md" in n for n in self._names()),
            msg="wave-0-approved.md (S109 pattern) not discovered",
        )

    def test_discovers_plan083_grandfathered_subdirs(self) -> None:
        names = self._names()
        for needle in (
            "PLAN-083/architect/wave-0a",
            "PLAN-083/architect/wave-0b",
            "PLAN-083/architect/wave-1-2",
            "PLAN-083/architect/wave-minus-1",
            "PLAN-083/staging/review",
        ):
            with self.subTest(needle=needle):
                self.assertTrue(
                    any(needle in n for n in names),
                    msg=f"grandfathered {needle} not discovered",
                )

    def test_discovers_amendment_file(self) -> None:
        self.assertTrue(
            any("approved-amendment-2026-05-12.md" in n for n in self._names()),
            msg="amendment file not discovered",
        )

    def test_rejects_novel_orphan_subdir(self) -> None:
        """A novel architect/* subdir not in the pattern union is NOT trusted."""
        self.assertFalse(
            any("novel-subdir" in n for n in self._names()),
            msg="orphan novel subdir must not be discovered (no catch-all wildcard)",
        )

    def test_no_duplicates_in_result(self) -> None:
        from check_canonical_edit import _find_sentinels
        sentinels = _find_sentinels(self.root)
        self.assertEqual(
            len(sentinels), len(set(sentinels)),
            msg="duplicate sentinels in _find_sentinels output",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
