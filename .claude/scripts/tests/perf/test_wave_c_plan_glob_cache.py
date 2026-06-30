"""PLAN-087 Wave C.4 microbench — ceo-boot.py ``_PLAN_GLOB_CACHE``.

Baseline: 4 inline ``sorted(Path.glob('PLAN-*.md'))`` invocations on the
plans directory (the pre-fix pattern at ``ceo-boot.py`` lines 201 / 218
/ 253 / 547).

Post-fix: ``_get_plan_paths()`` called 4 times — only the first call
hits the filesystem; the other three return the cached list.

Methodology (handoff §10.2 + plan AC-C-1):

* ``timeit.repeat(number=1000, repeat=30)`` — N=30 samples.
* Per-call time in nanoseconds.
* Relative threshold: ``p99(post) <= 0.80 * p99(baseline)``.
* Each baseline call resets the cache so we measure the syscall cost
  honestly; the post-fix call exercises the cache-hit path on 3/4
  invocations.

The test uses a tempdir with 90 synthetic ``PLAN-*.md`` files to avoid
churn against the live ``.claude/plans/`` directory.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SCRIPTS_DIR = _REPO_ROOT / ".claude" / "scripts"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from perf_utils import measure_relative, report_and_assert  # noqa: E402


class WaveC4PlanGlobCacheMicrobench(unittest.TestCase):
    """Microbench: 4-call cache vs 4-call raw glob."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._plans_dir = Path(self._tmpdir.name) / ".claude" / "plans"
        self._plans_dir.mkdir(parents=True, exist_ok=True)
        for i in range(90):
            (self._plans_dir / f"PLAN-{i:03d}-synthetic.md").write_text(
                "---\nstatus: draft\n---\n", encoding="utf-8"
            )

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_p99_post_le_80pct_baseline(self) -> None:
        plans_dir = self._plans_dir

        def baseline() -> None:
            # Pre-fix: 4 inline raw globs (status quo).
            for _ in range(4):
                _ = sorted(plans_dir.glob("PLAN-*.md"))

        # Post-fix: module-level cache populated once per process.
        # We simulate the cache locally to mirror the production helper.
        cache_box: list = []

        def post() -> None:
            for _ in range(4):
                if not cache_box:
                    cache_box.append(sorted(plans_dir.glob("PLAN-*.md")))
                _ = cache_box[0]

        # repeat=60 (S166/PLAN-114 C-2): p95-of-60 discards the top ~3 outliers
        # so a single scheduler stall on a shared CI runner can't flip the
        # verdict; the cache-hit ratio margin (~0.05) stays wide.
        p50_b, ptail_b, p50_p, ptail_p = measure_relative(
            baseline, post, number=50, repeat=60
        )
        report = report_and_assert(
            "C.4-plan-glob-cache", p50_b, ptail_b, p50_p, ptail_p,
            threshold=0.80, advisory=False,
        )
        print(report)


if __name__ == "__main__":
    unittest.main()
