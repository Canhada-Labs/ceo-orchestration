"""PLAN-104 Wave E — relative microbenchmarks for persona-demand scanning."""
from __future__ import annotations

import fnmatch
import hashlib
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


def _find_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".claude" / "scripts").is_dir():
            return parent
    raise RuntimeError("repo root with .claude/scripts/ not found")


_REPO_ROOT = _find_repo_root()
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "scripts"))
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))

from _lib.testing import TestEnvContext


def _elapsed(work):
    started = time.perf_counter()
    value = work()
    return time.perf_counter() - started, value


def _p95(samples):
    ordered = sorted(samples)
    return ordered[max(0, (len(ordered) * 95 + 99) // 100 - 1)]


def _paired_p95(work, reference):
    measured = []
    references = []
    for trial in range(7):
        first, second = (work, reference) if trial % 2 == 0 else (reference, work)
        first_seconds, _ = _elapsed(first)
        second_seconds, _ = _elapsed(second)
        if first is work:
            measured.append(first_seconds)
            references.append(second_seconds)
        else:
            references.append(first_seconds)
            measured.append(second_seconds)
    return _p95(measured), _p95(references)


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


@unittest.skipIf(
    os.environ.get("CEO_PLAN104_MICROBENCH_SKIP") == "1",
    "microbench skipped via CEO_PLAN104_MICROBENCH_SKIP=1",
)
class TestDetectorLatencyBudget(TestEnvContext):
    """AC7: cost is relative to equivalent work measured in the process."""

    def setUp(self):
        super().setUp()
        import persona_demand_scan as ds
        self.ds = ds

    def test_path_matcher_p95_budget(self):
        paths = [
            "src/auth.py", "tests/test_foo.py", "detections/aws.sigma",
            "README.md", "src/main.go", "package.json", "src/utils.py",
            "lib/oauth_helper.py", "siem-rules/edr.yaml", "mutmut.cfg",
        ] * 50

        def detector():
            for path in paths:
                self.ds._path_matches(path, self.ds.AUTH_PATTERNS)
                self.ds._path_matches(path, self.ds.TEST_PATTERNS)
                self.ds._path_matches(path, self.ds.DETECT_PATTERNS)

        def reference():
            for path in paths:
                for patterns in (self.ds.AUTH_PATTERNS, self.ds.TEST_PATTERNS, self.ds.DETECT_PATTERNS):
                    any(fnmatch.fnmatch(path, pattern) for pattern in patterns)

        detector_p95, reference_p95 = _paired_p95(detector, reference)
        self.assertLess(detector_p95 / max(reference_p95, 1e-12), 3)

    def test_demand_id_compute_p95_budget(self):
        preimages = ["file_edit_auth:src/foo_%s.py:abcdef1234" % i for i in range(1000)]

        def detector():
            return [self.ds._demand_id(preimage) for preimage in preimages]

        def reference():
            return [hashlib.sha256(value.encode("utf-8")).hexdigest()[:16] for value in preimages]

        detector_p95, reference_p95 = _paired_p95(detector, reference)
        self.assertEqual(detector(), reference())
        self.assertLess(detector_p95 / max(reference_p95, 1e-12), 4)

    def test_full_scan_subprocess_p95_budget(self):
        with tempfile.TemporaryDirectory(prefix="plan104-branches-") as directory:
            repo = Path(directory)
            self._make_many_branch_repo(repo, 76)
            detector_p95, reference_p95 = _paired_p95(
                lambda: list(self.ds._scan_branch_ahead(repo)),
                lambda: self._reference_branch_scan(repo),
            )
            events = list(self.ds._scan_branch_ahead(repo))
        self.assertEqual(len(events), 76)
        self.assertLess(detector_p95 / max(reference_p95, 1e-12), 1.8)

    def _reference_branch_scan(self, repo: Path):
        base = _git(repo, "rev-parse", "main")
        branches = _git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads/").splitlines()
        return [_git(repo, "rev-list", "--count", "%s..%s" % (base, branch)) for branch in branches if branch != "main"]

    def _make_many_branch_repo(self, repo: Path, branch_count: int) -> None:
        subprocess.run(["git", "init", "--initial-branch=main", str(repo)], check=True, capture_output=True)
        _git(repo, "config", "user.email", "test@example.invalid")
        _git(repo, "config", "user.name", "Test")
        (repo / "base").write_text("base\n", encoding="utf-8")
        _git(repo, "add", "base")
        _git(repo, "commit", "-m", "base")
        base = _git(repo, "rev-parse", "HEAD")
        (repo / "ahead").write_text("ahead\n", encoding="utf-8")
        _git(repo, "add", "ahead")
        _git(repo, "commit", "-m", "ahead")
        ahead = _git(repo, "rev-parse", "HEAD")
        _git(repo, "update-ref", "refs/heads/main", base)
        for number in range(branch_count):
            _git(repo, "update-ref", "refs/heads/synthetic-%03d" % number, ahead)


if __name__ == "__main__":
    unittest.main()
