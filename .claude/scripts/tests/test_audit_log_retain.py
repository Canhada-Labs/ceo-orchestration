"""Tests for audit-log-retain.py (PLAN-113 W7-OPS F-6.1-audit-log-retention-002).

Exercises:
- Archive discovery (pattern matching)
- compute_deletable: count policy, age policy, both policies, neither
- compute_deletable: newest-archive protection (P0 data-loss fix)
- compute_deletable: manifest-anchor protection (P0 data-loss fix)
- compute_deletable: AND semantics when both policies active
- Dry-run vs apply mode
- No-op when no archives present
- Fail-open on missing audit dir
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "audit-log-retain.py"

sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402


def _load_module():
    spec = importlib.util.spec_from_file_location("audit_log_retain", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_mod = _load_module()


class TestArchiveDiscovery(unittest.TestCase):
    """Pattern matching for rotated archive filenames."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _make(self, name: str, content: str = "x") -> Path:
        p = self.tmpdir / name
        p.write_text(content)
        return p

    def test_discovers_monthly_archive(self):
        self._make("audit-log-2026-04.jsonl")
        archives = _mod.discover_archives(self.tmpdir)
        names = [p.name for _, p in archives]
        self.assertIn("audit-log-2026-04.jsonl", names)

    def test_discovers_collision_suffix_archive(self):
        self._make("audit-log-2026-04-1.jsonl")
        self._make("audit-log-2026-04-99.jsonl")
        archives = _mod.discover_archives(self.tmpdir)
        names = [p.name for _, p in archives]
        self.assertIn("audit-log-2026-04-1.jsonl", names)
        self.assertIn("audit-log-2026-04-99.jsonl", names)

    def test_excludes_active_log(self):
        self._make("audit-log.jsonl")
        archives = _mod.discover_archives(self.tmpdir)
        names = [p.name for _, p in archives]
        self.assertNotIn("audit-log.jsonl", names)

    def test_excludes_errors_sidecar(self):
        self._make("audit-log.errors")
        archives = _mod.discover_archives(self.tmpdir)
        names = [p.name for _, p in archives]
        self.assertNotIn("audit-log.errors", names)

    def test_excludes_unrelated_files(self):
        self._make("README.md")
        self._make("audit-log.lock")
        archives = _mod.discover_archives(self.tmpdir)
        self.assertEqual(len(archives), 0)

    def test_sorted_newest_first(self):
        now = time.time()
        old = self._make("audit-log-2026-01.jsonl")
        new = self._make("audit-log-2026-04.jsonl")
        os.utime(old, (now - 200, now - 200))
        os.utime(new, (now - 10, now - 10))
        archives = _mod.discover_archives(self.tmpdir)
        self.assertEqual(archives[0][1].name, "audit-log-2026-04.jsonl")
        self.assertEqual(archives[1][1].name, "audit-log-2026-01.jsonl")

    def test_empty_dir_returns_empty(self):
        archives = _mod.discover_archives(self.tmpdir)
        self.assertEqual(archives, [])

    def test_nonexistent_dir_returns_empty(self):
        archives = _mod.discover_archives(self.tmpdir / "nonexistent")
        self.assertEqual(archives, [])


class TestComputeDeletable(unittest.TestCase):
    """compute_deletable: count + age + combined + disabled policies."""

    def _make_archives(
        self, count: int, age_seconds_list: list
    ) -> list:
        """Return fake (mtime, path) tuples sorted newest-first."""
        now = time.time()
        result = []
        for i, age_s in enumerate(age_seconds_list):
            p = Path(f"/fake/audit-log-2026-{i:02d}.jsonl")
            mtime = now - age_s
            result.append((mtime, p))
        result.sort(key=lambda t: t[0], reverse=True)
        return result

    def test_count_policy_keeps_n(self):
        archives = self._make_archives(5, [10, 20, 30, 40, 50])
        deletable = _mod.compute_deletable(archives, keep_count=3, keep_days=0)
        self.assertEqual(len(deletable), 2)

    def test_count_policy_disabled(self):
        archives = self._make_archives(5, [10, 20, 30, 40, 50])
        deletable = _mod.compute_deletable(archives, keep_count=0, keep_days=0)
        self.assertEqual(len(deletable), 0)

    def test_age_policy_drops_old(self):
        now = time.time()
        recent = (now - 10, Path("/fake/audit-log-2026-04.jsonl"))
        old = (now - 400 * 86400, Path("/fake/audit-log-2025-01.jsonl"))
        archives = [recent, old]  # newest first
        deletable = _mod.compute_deletable(archives, keep_count=0, keep_days=365)
        self.assertIn(old[1], deletable)
        self.assertNotIn(recent[1], deletable)

    def test_age_policy_disabled(self):
        now = time.time()
        very_old = (now - 1000 * 86400, Path("/fake/audit-log-2023-01.jsonl"))
        archives = [very_old]
        deletable = _mod.compute_deletable(archives, keep_count=0, keep_days=0)
        self.assertEqual(len(deletable), 0)

    def test_both_policies_and_semantics(self):
        """File must be outside BOTH thresholds to be deleted (AND semantics)."""
        now = time.time()
        archives = [
            (now - 1, Path("/fake/audit-log-2026-04.jsonl")),   # newest; always protected
            (now - 10, Path("/fake/audit-log-2026-03.jsonl")),  # recent; kept by age (idx=1 < 2)
            (now - 400 * 86400, Path("/fake/audit-log-2025-01.jsonl")),  # old + beyond count
        ]
        deletable = _mod.compute_deletable(archives, keep_count=2, keep_days=365)
        # audit-log-2025-01 is beyond BOTH count (idx=2>=2) AND age (400>365) → deleted
        self.assertIn(archives[2][1], deletable)
        # audit-log-2026-03 is young (age keeps it) even though idx=1 is within count
        self.assertNotIn(archives[1][1], deletable)
        # Newest is always protected
        self.assertNotIn(archives[0][1], deletable)

    def test_no_archives_returns_empty(self):
        deletable = _mod.compute_deletable([], keep_count=12, keep_days=365)
        self.assertEqual(deletable, [])

    # ------------------------------------------------------------------
    # P0 data-loss fix: newest-archive protection
    # ------------------------------------------------------------------

    def test_single_old_archive_never_deleted_newest_protection(self):
        """(a) Single 400-day-old archive + aggressive keep-days must NOT be deleted.

        This is the P0 scenario: the only archive is both the newest and the
        oldest; deleting it would destroy all audit history.  The newest-archive
        guard must protect it unconditionally.
        """
        now = time.time()
        single = (now - 400 * 86400, Path("/fake/audit-log-2025-01.jsonl"))
        archives = [single]
        deletable = _mod.compute_deletable(archives, keep_count=0, keep_days=365)
        self.assertEqual(deletable, [], "Newest archive must never be deleted")

    def test_newest_archive_protected_even_beyond_count(self):
        """Newest archive is protected even when keep_count=1 and there are 3 archives."""
        now = time.time()
        archives = [
            (now - 1, Path("/fake/audit-log-2026-04.jsonl")),    # newest → protected
            (now - 50 * 86400, Path("/fake/audit-log-2026-03.jsonl")),
            (now - 100 * 86400, Path("/fake/audit-log-2026-02.jsonl")),
        ]
        deletable = _mod.compute_deletable(archives, keep_count=1, keep_days=0)
        # idx=1 and idx=2 are beyond count → deletable; idx=0 is newest → protected
        self.assertNotIn(archives[0][1], deletable)
        self.assertIn(archives[1][1], deletable)
        self.assertIn(archives[2][1], deletable)

    # ------------------------------------------------------------------
    # P0 data-loss fix: manifest-anchor protection
    # ------------------------------------------------------------------

    def test_manifest_anchor_never_deleted(self):
        """(b) Archive named in protected_names (manifest anchor) is never deleted.

        Even when the archive is old and beyond both count and age thresholds,
        the manifest anchor must survive so HMAC chain reconstruction is possible.
        """
        now = time.time()
        anchor_name = "audit-log-2025-01.jsonl"
        archives = [
            (now - 1, Path("/fake/audit-log-2026-04.jsonl")),          # newest
            (now - 400 * 86400, Path(f"/fake/{anchor_name}")),          # old but anchored
        ]
        deletable = _mod.compute_deletable(
            archives,
            keep_count=0,
            keep_days=365,
            protected_names={anchor_name},
        )
        names = [p.name for p in deletable]
        self.assertNotIn(anchor_name, names, "Manifest anchor must never be deleted")

    # ------------------------------------------------------------------
    # Normal case: genuinely stale archives are still cleaned up
    # ------------------------------------------------------------------

    def test_stale_archives_beyond_both_policies_deleted(self):
        """(c) Multiple old archives beyond BOTH count and age are still deleted."""
        now = time.time()
        archives = [
            (now - 1, Path("/fake/audit-log-2026-05.jsonl")),             # newest → protected
            (now - 10, Path("/fake/audit-log-2026-04.jsonl")),             # recent; within count
            (now - 400 * 86400, Path("/fake/audit-log-2025-01.jsonl")),    # old + beyond count
            (now - 500 * 86400, Path("/fake/audit-log-2024-12.jsonl")),    # older + beyond count
        ]
        # keep_count=2, keep_days=365: idx=0,1 within count; idx=2,3 beyond count AND old
        deletable = _mod.compute_deletable(archives, keep_count=2, keep_days=365)
        self.assertNotIn(archives[0][1], deletable, "Newest must not be deleted")
        self.assertNotIn(archives[1][1], deletable, "Within count and recent must not be deleted")
        self.assertIn(archives[2][1], deletable, "Beyond both policies must be deleted")
        self.assertIn(archives[3][1], deletable, "Beyond both policies must be deleted")


class TestCLI(TestEnvContext):
    """CLI: dry-run, apply, missing dir, env-var resolution."""

    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()
        super().tearDown()

    def _make_archive(self, name: str, age_days: float = 0.0) -> Path:
        p = self.tmpdir / name
        p.write_text("x")
        if age_days > 0:
            mtime = time.time() - age_days * 86400
            os.utime(p, (mtime, mtime))
        return p

    def test_dry_run_does_not_delete(self):
        self._make_archive("audit-log-2026-04.jsonl", age_days=400)
        rc = _mod.main(["--keep-count", "0", "--keep-days", "1",
                         "--audit-dir", str(self.tmpdir)])
        self.assertEqual(rc, 0)
        self.assertTrue((self.tmpdir / "audit-log-2026-04.jsonl").exists())

    def test_apply_deletes_old_files(self):
        # Use --keep-count 0 so only age policy is active; old archive is deleted,
        # recent one (the newest) is protected by the newest-archive guard.
        self._make_archive("audit-log-2026-04.jsonl", age_days=400)
        self._make_archive("audit-log-2026-05.jsonl", age_days=1)
        rc = _mod.main(["--keep-count", "0", "--keep-days", "365", "--apply",
                         "--audit-dir", str(self.tmpdir)])
        self.assertEqual(rc, 0)
        self.assertFalse((self.tmpdir / "audit-log-2026-04.jsonl").exists())
        self.assertTrue((self.tmpdir / "audit-log-2026-05.jsonl").exists())

    def test_apply_keep_count_deletes_excess(self):
        for i in range(5):
            self._make_archive(f"audit-log-2026-0{i+1}.jsonl", age_days=i * 10)
        rc = _mod.main(["--keep-count", "3", "--keep-days", "0", "--apply",
                         "--audit-dir", str(self.tmpdir)])
        self.assertEqual(rc, 0)
        remaining = list(self.tmpdir.glob("audit-log-2026-*.jsonl"))
        self.assertEqual(len(remaining), 3)

    def test_no_archives_exits_zero(self):
        rc = _mod.main(["--apply", "--audit-dir", str(self.tmpdir)])
        self.assertEqual(rc, 0)

    def test_missing_audit_dir_arg_exits_two(self):
        rc = _mod.main(["--apply", "--audit-dir", str(self.tmpdir / "nonexistent")])
        self.assertEqual(rc, 2)

    def test_no_audit_dir_found_exits_zero(self):
        """When env resolution fails, the script exits 0 (nothing to do)."""
        # Restore the AUDIT anchors on teardown — popping them unrestored defeats
        # the suite-wide audit-dir redirect for later sequential tests. NOTE: we do
        # NOT restore CLAUDE_PROJECT_DIR — leaving it popped (as before) is correct;
        # restoring it to its (possibly temp) start value steers later subprocess
        # tests (generate-dispatch / benchmarks-replay resolve the repo via
        # CLAUDE_PROJECT_DIR) at an empty dir -> "no native agent files found".
        for _k in ("CEO_AUDIT_LOG_DIR", "CEO_AUDIT_LOG_PATH"):
            self.addCleanup(
                lambda k=_k, v=os.environ.get(_k):
                os.environ.__setitem__(k, v) if v is not None else os.environ.pop(k, None)
            )
        os.environ.pop("CEO_AUDIT_LOG_DIR", None)
        os.environ.pop("CEO_AUDIT_LOG_PATH", None)
        os.environ.pop("CLAUDE_PROJECT_DIR", None)
        # Force HOME to a temp dir that doesn't have ~/.claude/projects/ceo-orchestration
        import tempfile as _tmpfile
        with _tmpfile.TemporaryDirectory() as fake_home:
            old_home = os.environ.get("HOME")
            try:
                os.environ["HOME"] = fake_home
                rc = _mod.main(["--apply"])
            finally:
                if old_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = old_home
        self.assertEqual(rc, 0)

    def test_env_var_CEO_AUDIT_LOG_DIR_resolution(self):
        """CEO_AUDIT_LOG_DIR env var directs the script to the right directory."""
        # Use two archives so the 400-day-old one is NOT the newest and gets deleted
        # by the age policy alone (--keep-count 0 disables count).
        # Restore on teardown instead of a bare unguarded `del` after main():
        # if main() raised or an earlier assert failed, the old code left
        # CEO_AUDIT_LOG_DIR pointing at self.tmpdir (which tearDown deletes),
        # breaking the anchor for every later sequential test.
        self.addCleanup(
            lambda v=os.environ.get("CEO_AUDIT_LOG_DIR"):
            os.environ.__setitem__("CEO_AUDIT_LOG_DIR", v) if v is not None
            else os.environ.pop("CEO_AUDIT_LOG_DIR", None)
        )
        os.environ["CEO_AUDIT_LOG_DIR"] = str(self.tmpdir)
        self._make_archive("audit-log-2026-04.jsonl", age_days=400)
        self._make_archive("audit-log-2026-05.jsonl", age_days=1)
        rc = _mod.main(["--keep-count", "0", "--keep-days", "1", "--apply"])
        self.assertEqual(rc, 0)
        self.assertFalse((self.tmpdir / "audit-log-2026-04.jsonl").exists())

    def test_active_log_never_deleted(self):
        """audit-log.jsonl must never appear in the deletable set."""
        (self.tmpdir / "audit-log.jsonl").write_text("active")
        self._make_archive("audit-log-2026-04.jsonl", age_days=400)
        rc = _mod.main(["--keep-days", "1", "--apply",
                         "--audit-dir", str(self.tmpdir)])
        self.assertEqual(rc, 0)
        self.assertTrue((self.tmpdir / "audit-log.jsonl").exists())


    def test_dry_run_never_deletes_stale_archives(self):
        """(d) Dry-run (no --apply) never deletes even genuinely stale archives."""
        self._make_archive("audit-log-2025-01.jsonl", age_days=500)
        self._make_archive("audit-log-2025-02.jsonl", age_days=450)
        self._make_archive("audit-log-2026-05.jsonl", age_days=1)
        # No --apply → dry-run; all files must survive.
        rc = _mod.main(["--keep-count", "1", "--keep-days", "30",
                         "--audit-dir", str(self.tmpdir)])
        self.assertEqual(rc, 0)
        self.assertTrue((self.tmpdir / "audit-log-2025-01.jsonl").exists())
        self.assertTrue((self.tmpdir / "audit-log-2025-02.jsonl").exists())
        self.assertTrue((self.tmpdir / "audit-log-2026-05.jsonl").exists())

    def test_manifest_anchor_protected_in_apply_mode(self):
        """Manifest-anchored archive survives even with aggressive policy + --apply."""
        import json as _json
        anchor_name = "audit-log-2025-01.jsonl"
        manifest = {"previous_archive_filename": anchor_name, "version": 1}
        (self.tmpdir / "audit-log.rotation-manifest.json").write_text(
            _json.dumps(manifest), encoding="utf-8"
        )
        self._make_archive(anchor_name, age_days=400)
        self._make_archive("audit-log-2026-05.jsonl", age_days=1)
        # Aggressive policy: only keep 1 archive, 30-day window.
        rc = _mod.main(["--keep-count", "1", "--keep-days", "30", "--apply",
                         "--audit-dir", str(self.tmpdir)])
        self.assertEqual(rc, 0)
        # Anchor must survive despite being old and beyond count.
        self.assertTrue((self.tmpdir / anchor_name).exists(),
                        "Manifest anchor must not be deleted")


if __name__ == "__main__":
    unittest.main()
