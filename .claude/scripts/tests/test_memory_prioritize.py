"""PLAN-046 Cluster 1.3 — memory_prioritize tests."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_SCRIPT = _REPO_ROOT / ".claude" / "scripts" / "memory-prioritize.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("memory_prioritize", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
from _lib.testing import TestEnvContext  # noqa: E402


class MemoryPrioritizeTest(TestEnvContext):

    def setUp(self) -> None:
        super().setUp()
        self.mod = _load_module()
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: _rmtree(self.tmp))
        self.mem = self.tmp / "memory"
        self.mem.mkdir()

    def _write(self, name: str, body: str = "# file\n") -> Path:
        p = self.mem / name
        p.write_text(body, encoding="utf-8")
        return p

    # --- signals

    def test_recency_signal_monotonic(self) -> None:
        newer = self.mod._recency_signal(1.0)
        older = self.mod._recency_signal(200.0)
        self.assertGreater(newer, older)
        self.assertGreater(newer, 0.0)
        self.assertLessEqual(newer, 1.0)

    def test_recency_zero_hours_approaches_one(self) -> None:
        self.assertAlmostEqual(self.mod._recency_signal(0.0), 1.0, places=3)

    def test_recency_infinity_is_zero(self) -> None:
        self.assertEqual(self.mod._recency_signal(float("inf")), 0.0)

    def test_access_signal_saturates(self) -> None:
        self.assertEqual(self.mod._access_signal(0), 0.0)
        self.assertGreater(self.mod._access_signal(5), 0.0)
        self.assertEqual(self.mod._access_signal(9999), 1.0)

    def test_centrality_signal_saturates(self) -> None:
        self.assertEqual(self.mod._centrality_signal(0), 0.0)
        self.assertGreater(self.mod._centrality_signal(2), 0.0)
        self.assertEqual(self.mod._centrality_signal(9999), 1.0)

    def test_bayes_posterior_uniform_prior(self) -> None:
        self.assertAlmostEqual(self.mod._bayes_posterior_mean([]), 0.5)

    def test_bayes_posterior_updates_towards_evidence(self) -> None:
        low = self.mod._bayes_posterior_mean([0.1] * 5)
        high = self.mod._bayes_posterior_mean([0.9] * 5)
        self.assertLess(low, 0.5)
        self.assertGreater(high, 0.5)

    # --- cross-link collection

    def test_collect_inbound_links(self) -> None:
        self._write("a.md", "See [B](b.md) and [C](./c.md).")
        self._write("b.md", "stub")
        self._write("c.md", "stub")
        counts = self.mod._collect_inbound_links(self.mem)
        self.assertEqual(counts.get("b.md", 0), 1)
        self.assertEqual(counts.get("c.md", 0), 1)

    def test_collect_inbound_links_ignores_non_md(self) -> None:
        (self.mem / "ignore.txt").write_text("[x](x.md)", encoding="utf-8")
        self._write("seed.md", "content")
        counts = self.mod._collect_inbound_links(self.mem)
        self.assertNotIn("x.md", counts)

    # --- end-to-end

    def test_prioritize_sorts_desc_by_score(self) -> None:
        old = self._write("old.md", "stub")
        # Force very old mtime
        past = time.time() - 10 * 24 * 3600
        os.utime(old, (past, past))
        fresh = self._write("fresh.md", "stub")

        rows = self.mod.prioritize(self.mem)
        self.assertGreaterEqual(len(rows), 2)
        names = [r["name"] for r in rows]
        fresh_idx = names.index("fresh.md")
        old_idx = names.index("old.md")
        self.assertLess(fresh_idx, old_idx,
                        "fresh file should outrank old file")

    def test_prioritize_skips_memory_index(self) -> None:
        self._write("MEMORY.md", "index")
        self._write("topic.md", "content")
        rows = self.mod.prioritize(self.mem)
        names = [r["name"] for r in rows]
        self.assertNotIn("MEMORY.md", names)
        self.assertIn("topic.md", names)

    def test_prioritize_handles_missing_dir(self) -> None:
        rows = self.mod.prioritize(Path("/tmp/nonexistent-memory-dir-xxyyzz"))
        self.assertEqual(rows, [])

    def test_render_markdown_contains_header(self) -> None:
        self._write("a.md", "x")
        rows = self.mod.prioritize(self.mem)
        md = self.mod.render_markdown(rows, limit=None)
        self.assertIn("Memory prioritization report", md)
        self.assertIn("| # | File |", md)

    def test_render_jsonl_parseable(self) -> None:
        self._write("a.md", "x")
        self._write("b.md", "x")
        rows = self.mod.prioritize(self.mem)
        output = self.mod.render_jsonl(rows, limit=None)
        for line in output.splitlines():
            parsed = json.loads(line)
            self.assertIn("name", parsed)
            self.assertIn("score", parsed)

    def test_limit_truncates_output(self) -> None:
        for i in range(5):
            self._write(f"f{i}.md", "x")
        rows = self.mod.prioritize(self.mem)
        md = self.mod.render_markdown(rows, limit=2)
        # 4 header lines + 2 data rows = 6 lines
        self.assertEqual(
            sum(1 for l in md.splitlines() if l.startswith("| ") and " `f" in l),
            2,
        )

    # --- retention / rotation (PLAN-113 W7, finding F-6-6.7) ---------------

    def _seed_aged(self, count: int) -> None:
        """Write ``count`` files with staggered mtimes (f0 = oldest)."""
        now = time.time()
        for i in range(count):
            p = self._write(f"f{i}.md", f"content {i}")
            # older index = older file => lower recency score
            age = (count - i) * 24 * 3600
            os.utime(p, (now - age, now - age))

    def test_select_prune_candidates_returns_tail(self) -> None:
        self._seed_aged(5)
        rows = self.mod.prioritize(self.mem)
        cand = self.mod.select_prune_candidates(rows, keep=3)
        # 5 scored, keep 3 => 2 candidates
        self.assertEqual(len(cand), 2)
        # candidates are the lowest-scored files (the oldest: f0, f1)
        names = {c["name"] for c in cand}
        self.assertEqual(names, {"f0.md", "f1.md"})

    def test_select_prune_candidates_keep_ge_total_is_empty(self) -> None:
        self._seed_aged(3)
        rows = self.mod.prioritize(self.mem)
        self.assertEqual(self.mod.select_prune_candidates(rows, keep=10), [])

    def test_prune_dry_run_moves_nothing(self) -> None:
        self._seed_aged(5)
        summary = self.mod.prune(self.mem, keep=2, apply=False)
        self.assertFalse(summary["apply"])
        self.assertEqual(len(summary["archived"]), 3)
        # Dry-run: every source file still present, no archive dir created.
        for i in range(5):
            self.assertTrue((self.mem / f"f{i}.md").is_file())
        self.assertFalse((self.mem / "archive").exists())

    def test_prune_apply_archives_lowest_scored(self) -> None:
        self._seed_aged(5)
        summary = self.mod.prune(self.mem, keep=2, apply=True)
        self.assertTrue(summary["apply"])
        self.assertEqual(len(summary["archived"]), 3)
        archive = self.mem / "archive"
        self.assertTrue(archive.is_dir())
        # The two highest-scored (newest: f3, f4) remain in place.
        self.assertTrue((self.mem / "f3.md").is_file())
        self.assertTrue((self.mem / "f4.md").is_file())
        # The three lowest (f0, f1, f2) moved into archive/ (reversible).
        for n in ("f0.md", "f1.md", "f2.md"):
            self.assertFalse((self.mem / n).is_file())
            self.assertTrue((archive / n).is_file())

    def test_prune_archive_dir_mode_0700(self) -> None:
        self._seed_aged(3)
        self.mod.prune(self.mem, keep=1, apply=True)
        archive = self.mem / "archive"
        self.assertTrue(archive.is_dir())
        mode = oct(archive.stat().st_mode & 0o777)
        self.assertEqual(mode, oct(0o700))

    def test_prune_never_touches_memory_index(self) -> None:
        self._write("MEMORY.md", "index")
        self._seed_aged(3)
        self.mod.prune(self.mem, keep=0 + 1, apply=True)
        # MEMORY.md is excluded from scoring => never an archive candidate.
        self.assertTrue((self.mem / "MEMORY.md").is_file())
        self.assertFalse((self.mem / "archive" / "MEMORY.md").exists())

    def test_prune_no_clobber_existing_archive_target(self) -> None:
        self._seed_aged(3)
        archive = self.mem / "archive"
        archive.mkdir()
        # Pre-place an archived version of the lowest-scored file.
        (archive / "f0.md").write_text("OLD-ARCHIVED", encoding="utf-8")
        summary = self.mod.prune(self.mem, keep=1, apply=True)
        # f0.md should be skipped (no-clobber), its old archive preserved.
        skipped_names = {s["name"] for s in summary["skipped"]}
        self.assertIn("f0.md", skipped_names)
        self.assertEqual(
            (archive / "f0.md").read_text(encoding="utf-8"), "OLD-ARCHIVED"
        )
        # And the source f0.md stays put (not lost).
        self.assertTrue((self.mem / "f0.md").is_file())

    def test_prune_does_not_re_archive_files_in_archive_dir(self) -> None:
        self._seed_aged(3)
        # First pass archives the lowest 2.
        self.mod.prune(self.mem, keep=1, apply=True)
        # Second pass with the same cap: archive/ files are not scored
        # (prioritize globs the memory dir top-level only), so nothing new.
        summary = self.mod.prune(self.mem, keep=1, apply=True)
        # Only 1 file remains at top level (the kept one) => 0 candidates.
        self.assertEqual(len(summary["archived"]), 0)

    def test_prune_missing_dir_is_noop(self) -> None:
        summary = self.mod.prune(Path("/tmp/nope-xyzzy-memdir"), keep=5, apply=True)
        self.assertEqual(summary["archived"], [])
        self.assertEqual(summary["total_scored"], 0)

    def test_render_prune_summary_dry_run_label(self) -> None:
        self._seed_aged(3)
        summary = self.mod.prune(self.mem, keep=1, apply=False)
        out = self.mod.render_prune_summary(summary)
        self.assertIn("DRY-RUN", out)
        self.assertIn("Would archive", out)

    def test_render_prune_summary_applied_label(self) -> None:
        self._seed_aged(3)
        summary = self.mod.prune(self.mem, keep=1, apply=True)
        out = self.mod.render_prune_summary(summary)
        self.assertIn("APPLIED", out)

    # --- CLI gate: --prune is default-off + requires --keep ----------------

    def test_cli_prune_requires_keep(self) -> None:
        rc = self.mod.main(["--memory-dir", str(self.mem), "--prune"])
        self.assertEqual(rc, 2)

    def test_cli_prune_rejects_zero_keep(self) -> None:
        rc = self.mod.main(
            ["--memory-dir", str(self.mem), "--prune", "--keep", "0"]
        )
        self.assertEqual(rc, 2)

    def test_cli_no_prune_flag_is_report_only(self) -> None:
        self._seed_aged(4)
        rc = self.mod.main(["--memory-dir", str(self.mem)])
        self.assertEqual(rc, 0)
        # No --prune => nothing archived, behaviour unchanged.
        self.assertFalse((self.mem / "archive").exists())
        for i in range(4):
            self.assertTrue((self.mem / f"f{i}.md").is_file())

    def test_cli_prune_dry_run_default(self) -> None:
        self._seed_aged(4)
        rc = self.mod.main(
            ["--memory-dir", str(self.mem), "--prune", "--keep", "2"]
        )
        self.assertEqual(rc, 0)
        # Dry-run by default (no --apply): nothing moved.
        self.assertFalse((self.mem / "archive").exists())

    def test_cli_prune_apply_moves(self) -> None:
        self._seed_aged(4)
        rc = self.mod.main(
            ["--memory-dir", str(self.mem), "--prune", "--keep", "2", "--apply"]
        )
        self.assertEqual(rc, 0)
        self.assertTrue((self.mem / "archive").is_dir())
        self.assertEqual(
            sum(1 for p in (self.mem / "archive").iterdir() if p.is_file()), 2
        )


def _rmtree(path: Path) -> None:
    import shutil
    try:
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
