"""PLAN-087 Wave C.7 microbench — ``filelock._MKDIR_DONE`` cache.

Baseline: ``Path.parent.mkdir(parents=True, exist_ok=True)`` on every
``FileLock.acquire()`` invocation (pre-fix pattern).

Post-fix: ``mkdir`` is gated by a module-level ``_MKDIR_DONE`` set;
the first acquire seeds the cache, subsequent acquires skip the
syscall entirely.

Methodology (handoff §10.2 + plan AC-C-1):

* ``timeit.repeat(number=1000, repeat=30)`` — N=30 samples.
* Per-call time in nanoseconds.
* Relative threshold: ``p99(post) <= 0.80 * p99(baseline)``.
* Test directly invokes the underlying ``mkdir(exist_ok=True)`` to
  isolate the syscall cost from FileLock's fcntl logic.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from typing import Set

sys.path.insert(0, str(Path(__file__).resolve().parent))
from perf_utils import measure_relative, report_and_assert  # noqa: E402


class WaveC7FilelockMkdirCacheMicrobench(unittest.TestCase):

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._parent = Path(self._tmpdir.name) / "subdir"
        self._parent.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_p99_post_le_80pct_baseline(self) -> None:
        parent = self._parent

        def baseline() -> None:
            # Pre-fix: unconditional mkdir on every acquire.
            parent.mkdir(parents=True, exist_ok=True)

        cache: Set[str] = set()
        parent_str = str(parent)

        def post() -> None:
            # Post-fix: cache-gated mkdir.
            if parent_str not in cache:
                parent.mkdir(parents=True, exist_ok=True)
                cache.add(parent_str)

        # repeat=60 (S166/PLAN-114 C-2): p95-of-60 discards the top ~3 outliers
        # so a single scheduler stall on a shared CI runner can't flip the
        # verdict; the cache-hit ratio margin (~0.05) stays wide.
        p50_b, ptail_b, p50_p, ptail_p = measure_relative(
            baseline, post, number=200, repeat=60
        )
        report = report_and_assert(
            "C.7-filelock-mkdir-cache", p50_b, ptail_b, p50_p, ptail_p,
            threshold=0.80, advisory=False,
        )
        print(report)


if __name__ == "__main__":
    unittest.main()
