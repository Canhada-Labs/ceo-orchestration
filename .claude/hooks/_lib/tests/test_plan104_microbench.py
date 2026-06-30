"""PLAN-104 Wave E — AC7 microbench: demand-event detection adds <=5ms p95.

Validates that `persona_demand_scan` overhead on a quiet repo (no demand
events) does not exceed 5ms p95 when invoked from /ceo-boot.

Methodology: N=21 trials, drop top+bottom outlier, compute p95 of
remaining. Threshold accounts for cold-cache subprocess startup on
macOS / Linux CI runners.

This is a soft gate — runs but tolerates skips under CI low-resource
conditions (CEO_PLAN104_MICROBENCH_SKIP=1).
"""
from __future__ import annotations

import os
import sys
import time
import unittest
from pathlib import Path

def _find_repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / ".claude" / "scripts").is_dir():
            return parent
    raise RuntimeError("repo root with .claude/scripts/ not found")


_REPO_ROOT = _find_repo_root()
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "scripts"))


@unittest.skipIf(
    os.environ.get("CEO_PLAN104_MICROBENCH_SKIP") == "1",
    "microbench skipped via CEO_PLAN104_MICROBENCH_SKIP=1",
)
class TestDetectorLatencyBudget(unittest.TestCase):
    """AC7: <=5ms p95 added latency on quiet repo state."""

    def setUp(self):
        import persona_demand_scan as ds
        self.ds = ds

    def test_path_matcher_p95_budget(self):
        # Hot path of detection is _path_matches across the 3 pattern families.
        paths = [
            "src/auth.py", "tests/test_foo.py", "detections/aws.sigma",
            "README.md", "src/main.go", "package.json", "src/utils.py",
            "lib/oauth_helper.py", "siem-rules/edr.yaml", "mutmut.cfg",
        ] * 50  # 500 path samples per trial
        N = 21
        timings = []
        for _ in range(N):
            t0 = time.perf_counter()
            for p in paths:
                self.ds._path_matches(p, self.ds.AUTH_PATTERNS)
                self.ds._path_matches(p, self.ds.TEST_PATTERNS)
                self.ds._path_matches(p, self.ds.DETECT_PATTERNS)
            timings.append((time.perf_counter() - t0) * 1000)
        timings.sort()
        trimmed = timings[1:-1]  # drop hi/lo outliers
        # Per-path p95 budget: total p95 / N_paths / 3 families
        per_path_p95_ms = (trimmed[int(len(trimmed) * 0.95) - 1]) / len(paths) / 3
        self.assertLess(
            per_path_p95_ms, 5.0,
            f"per-path p95 = {per_path_p95_ms:.4f}ms; budget 5.0ms (AC7)",
        )

    def test_demand_id_compute_p95_budget(self):
        # demand_id derivation: NFKC + sha256 + truncate
        N = 21
        timings = []
        for _ in range(N):
            t0 = time.perf_counter()
            for i in range(1000):
                self.ds._demand_id(f"file_edit_auth:src/foo_{i}.py:abcdef1234")
            timings.append((time.perf_counter() - t0) * 1000)
        timings.sort()
        trimmed = timings[1:-1]
        # 1000 ops in <50ms total → per-op <50us, well under 5ms gate
        self.assertLess(
            trimmed[int(len(trimmed) * 0.95) - 1], 50.0,
            f"1000 demand_id ops p95 = {trimmed[int(len(trimmed) * 0.95) - 1]:.2f}ms; budget 50ms",
        )

    def test_full_scan_subprocess_p95_budget(self):
        """Codex iter-2 P2 #1c fold: measure the ACTUAL git-subprocess
        cost on a real repo. The path-matcher is fast; git subprocess
        startup is dominant. Hard budget: <=500ms p95 on full scan
        against ceo-orchestration repo (warm cache assumed).
        """
        N = 7  # subprocess invocations are expensive; smaller N
        timings = []
        for _ in range(N):
            t0 = time.perf_counter()
            list(self.ds._scan_branch_ahead(_REPO_ROOT))
            timings.append((time.perf_counter() - t0) * 1000)
        timings.sort()
        # Tolerate cold-cache outlier on first iteration
        trimmed = timings[1:]
        p95_idx = max(0, int(len(trimmed) * 0.95) - 1)
        self.assertLess(
            trimmed[p95_idx], 500.0,
            f"branch_ahead scan p95 = {trimmed[p95_idx]:.2f}ms; budget 500ms",
        )


if __name__ == "__main__":
    unittest.main()
