"""PLAN-179 rail round-7 [P1] — GC expires a session store as a UNIT.

The class this file closes: `gc_orphan_session_stores` used to shard by FILE
name and expire per file, so the four components of one store (`.sqlite`,
`.sqlite.lock`, `-wal`, `-shm`) landed in DIFFERENT sweeps and an ACTIVE
store (fresh WAL, stale db mtime) could lose a sidecar. The cure shards by
SCOPE (stem), decides expiry from the newest DATA mtime, and both decides
and unlinks under the store's own FileLock — a busy lock means an active
writer and skips the store.

Coverage mechanics (rail round-10 [P2]): scopes are processed in
lexicographic order ROTATED past a persisted resume cursor, so a
deadline/cap break never starves the same tail twice. Small directories
are fully decided in a single sweep.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

# --- Locate repo root + the staged/live module, CANONICAL-FIRST. ---
_THIS = Path(__file__).resolve()
_repo_root = None
for parent in _THIS.parents:
    if (parent / ".claude" / "hooks" / "_lib").is_dir() and (
        parent / ".claude" / "plans"
    ).is_dir():
        _repo_root = parent
        break
assert _repo_root is not None, "could not locate repo root from test path"
_LIVE_HOOKS = _repo_root / ".claude" / "hooks"
_CANONICAL_SP = _LIVE_HOOKS / "_lib" / "scratchpad_lib.py"
_STAGED_SP = (
    _repo_root / ".claude" / "plans" / "PLAN-179" / "staged-w01"
    / ".claude" / "hooks" / "_lib" / "scratchpad_lib.py"
)
# Marker unique to the round-7 cure: pre-ceremony only the staged copy has
# it; post-ceremony the canonical copy carries it and the pack is gone.
_SP_MARKER = "_SESSION_STORE_DATA_SUFFIXES"


def _pick(canonical: Path, staged: Path, marker: str) -> Path:
    try:
        if canonical.is_file() and marker in canonical.read_text(encoding="utf-8"):
            return canonical
    except OSError:
        pass
    if staged.is_file() and marker in staged.read_text(encoding="utf-8"):
        return staged
    raise FileNotFoundError(
        "scratchpad_lib with the round-7 GC not found in canonical (%s) or "
        "staged (%s); marker=%r" % (canonical, staged, marker)
    )


_SP_PATH = _pick(_CANONICAL_SP, _STAGED_SP, _SP_MARKER)

if str(_LIVE_HOOKS) not in sys.path:
    sys.path.insert(0, str(_LIVE_HOOKS))  # canonical _lib package

from _lib.testing import TestEnvContext  # noqa: E402


def _load_sp():
    """Load the module under test under a NON-canonical name, transiently
    bound (tests/conftest.py collection-finish guard: no pollution)."""
    spec = importlib.util.spec_from_file_location(
        "_plan179_gc_sp_under_test", str(_SP_PATH)
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.modules.pop(spec.name, None)
    return mod


_sp = _load_sp()

_SCOPE = "session-" + "ab12" * 8          # matches _SESSION_SCOPE_ID_RE
_TTL = 72 * 3600


class GcStoreUnitBase(TestEnvContext):
    def setUp(self):
        super().setUp()
        self.state_root = Path(self.project_dir) / "state"
        self.store_dir = self.state_root / _sp.SESSION_SCRATCHPAD_STORE_NAME
        self.store_dir.mkdir(parents=True)
        self.now = time.time()
        self.old = self.now - _TTL - 3600
        self.fresh = self.now - 60

    def _mk(self, scope, **mtimes):
        """Create store files; kwargs: db/lock/wal/shm = mtime or None."""
        names = {
            "db": scope + ".sqlite",
            "lock": scope + ".sqlite.lock",
            "wal": scope + ".sqlite-wal",
            "shm": scope + ".sqlite-shm",
        }
        paths = {}
        for key, mtime in mtimes.items():
            if mtime is None:
                continue
            p = self.store_dir / names[key]
            p.write_bytes(b"x")
            os.utime(str(p), (mtime, mtime))
            paths[key] = p
        return paths

    def _sweep(self, **kw):
        """One sweep; returns removals."""
        kw.setdefault("ttl_seconds", _TTL)
        kw.setdefault("now", self.now)
        env = {"CEO_STATE_ROOT": str(self.state_root)}
        with mock.patch.dict(os.environ, env, clear=False):
            return _sp.gc_orphan_session_stores(**kw)

    def _sweep_all(self, **kw):
        """Two sweeps (a full cursor wrap for small dirs); total removals."""
        return self._sweep(**kw) + self._sweep(**kw)


class TestExpiredStoreCollectedAsUnit(GcStoreUnitBase):
    def test_expired_store_data_collected_lock_preserved(self):
        """Rail round-9 [P2]: the DATA components go; the `.sqlite.lock`
        is NEVER unlinked — deleting a lock inode under a blocked waiter
        creates dual critical sections."""
        paths = self._mk(_SCOPE, db=self.old, lock=self.old,
                         wal=self.old, shm=self.old)
        removed = self._sweep_all()
        self.assertEqual(removed, 3)
        for key in ("db", "wal", "shm"):
            self.assertFalse(paths[key].exists(),
                             "%s survived the sweep" % paths[key].name)
        self.assertTrue(paths["lock"].exists(),
                        "the lock file must NEVER be unlinked")

    def test_all_components_fall_in_the_same_sweep(self):
        """THE round-7 regression control: the components of one store are
        decided together — a single sweep collects all three data files."""
        self._mk(_SCOPE, db=self.old, lock=self.old,
                 wal=self.old, shm=self.old)
        self.assertEqual(self._sweep(), 3)

    def test_cursor_resumes_past_the_previous_prefix(self):
        """Rail round-10 [P2] regression: with the cursor pointing at scope
        A, the next sweep must start at the scope AFTER it (B) — a break
        that always restarts from the top starved the tail forever."""
        scope_a = "session-" + "aa11" * 8
        scope_b = "session-" + "ff99" * 8
        self._mk(scope_a, db=self.old, wal=self.old, shm=self.old)
        b = self._mk(scope_b, db=self.old, wal=self.old, shm=self.old)
        (self.store_dir / _sp._GC_CURSOR_NAME).write_text(
            scope_a, encoding="utf-8"
        )
        # Budget for exactly ONE store: the one past the cursor goes first.
        self.assertEqual(self._sweep(max_files=3), 3)
        for p in b.values():
            self.assertFalse(
                p.exists(),
                "the scope PAST the cursor was not processed first",
            )
        self.assertTrue((self.store_dir / (scope_a + ".sqlite")).exists())

    def test_orphan_lock_alone_is_left_alone(self):
        """Round-9 declared residual: a lock-only scope is not collectable
        (no data), and the lock inode must stay stable for any waiter."""
        paths = self._mk(_SCOPE, lock=self.old)
        self.assertEqual(self._sweep_all(), 0)
        self.assertTrue(paths["lock"].exists())


class TestActiveStoreIsUntouched(GcStoreUnitBase):
    def test_fresh_wal_protects_stale_siblings(self):
        """THE positive control for the finding: stale db + fresh WAL is an
        ACTIVE store (WAL activity leaves the main db mtime stale) — no
        component may be removed."""
        paths = self._mk(_SCOPE, db=self.old, lock=self.old,
                         wal=self.fresh, shm=self.old)
        self.assertEqual(self._sweep_all(), 0)
        for p in paths.values():
            self.assertTrue(p.exists(), "%s was removed from an ACTIVE store"
                            % p.name)

    def test_fully_fresh_store_untouched(self):
        paths = self._mk(_SCOPE, db=self.fresh, lock=self.fresh,
                         wal=self.fresh, shm=self.fresh)
        self.assertEqual(self._sweep_all(), 0)
        for p in paths.values():
            self.assertTrue(p.exists())

    def test_held_lock_skips_the_store(self):
        """A writer holding the store's flock means ACTIVE regardless of
        mtimes — the GC must skip, never dispute."""
        paths = self._mk(_SCOPE, db=self.old, lock=self.old,
                         wal=self.old, shm=self.old)
        marker = Path(self.project_dir) / "holder-ready"
        holder = (
            "import fcntl, os, sys, time\n"
            "fd = os.open(sys.argv[1], os.O_CREAT | os.O_WRONLY, 0o600)\n"
            "fcntl.flock(fd, fcntl.LOCK_EX)\n"
            "open(sys.argv[2], 'w').write('locked')\n"
            "time.sleep(30)\n"
        )
        child = subprocess.Popen(
            [sys.executable, "-c", holder,
             str(paths["lock"]), str(marker)],
        )
        try:
            deadline = time.time() + 10
            while not marker.is_file():
                if time.time() >= deadline:
                    self.fail("lock-holder child never signalled readiness")
                if child.poll() is not None:
                    self.fail("lock-holder child exited early")
                time.sleep(0.05)
            self.assertEqual(self._sweep_all(), 0)
            for p in paths.values():
                self.assertTrue(
                    p.exists(),
                    "%s was removed while the store lock was HELD" % p.name,
                )
        finally:
            child.kill()
            child.wait()


class TestCapDiscipline(GcStoreUnitBase):
    def test_cap_splits_across_rotations_lock_always_survives(self):
        """When max_files truncates mid-store, the next rotation finishes
        the DATA collection; the lock file survives both (round-9)."""
        paths = self._mk(_SCOPE, db=self.old, lock=self.old,
                         wal=self.old, shm=self.old)
        first = self._sweep(max_files=2)
        self.assertEqual(first, 2)
        second = self._sweep_all(max_files=10)
        self.assertEqual(first + second, 3)
        for key in ("db", "wal", "shm"):
            self.assertFalse(paths[key].exists())
        self.assertTrue(paths["lock"].exists())


class TestForeignFilesUntouched(GcStoreUnitBase):
    def test_non_store_names_survive(self):
        stray = self.store_dir / "not-a-session-store.txt"
        stray.write_text("keep me", encoding="utf-8")
        os.utime(str(stray), (self.old, self.old))
        self._mk(_SCOPE, db=self.old, wal=self.old, shm=self.old)
        cursor = self.store_dir / _sp._GC_CURSOR_NAME
        self._sweep_all()
        self.assertTrue(stray.exists())
        self.assertTrue(cursor.is_file(), "resume cursor should persist")
        self.assertEqual(
            cursor.read_text(encoding="utf-8").strip(), _SCOPE,
            "cursor must record the last DECIDED scope",
        )


if __name__ == "__main__":
    unittest.main()
