"""PLAN-179 rail round-10 [P1] — state_store × GC deletion coordination.

The race: `_ensure_open` runs BEFORE FileLock acquisition, so the
continuity GC (which unlinks aged session stores under that same lock)
can delete the db underneath a connection opened earlier — the writer
then commits into an UNLINKED inode and the snapshot is lost invisibly.

The cure: `_reopen_if_vanished()` runs as the first statement inside
every FileLock critical section. Under the lock the check is race-free:
if the db path exists, the GC cannot remove it until release; if it
vanished, the store reopens (recreating the file) and the write lands
on disk.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

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
_CANONICAL = _LIVE_HOOKS / "_lib" / "state_store.py"
_STAGED = (
    _repo_root / ".claude" / "plans" / "PLAN-179" / "staged-w01"
    / ".claude" / "hooks" / "_lib" / "state_store.py"
)
_MARKER = "_reopen_if_vanished"


def _pick(canonical: Path, staged: Path, marker: str) -> Path:
    try:
        if canonical.is_file() and marker in canonical.read_text(encoding="utf-8"):
            return canonical
    except OSError:
        pass
    if staged.is_file() and marker in staged.read_text(encoding="utf-8"):
        return staged
    raise FileNotFoundError(
        "state_store with the round-10 GC coordination not found in "
        "canonical (%s) or staged (%s)" % (canonical, staged)
    )


_SS_PATH = _pick(_CANONICAL, _STAGED, _MARKER)

if str(_LIVE_HOOKS) not in sys.path:
    sys.path.insert(0, str(_LIVE_HOOKS))

from _lib.testing import TestEnvContext  # noqa: E402


def _load_ss():
    spec = importlib.util.spec_from_file_location(
        "_plan179_state_store_under_test", str(_SS_PATH)
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.modules.pop(spec.name, None)
    return mod


_ss = _load_ss()


class GcCoordinationBase(TestEnvContext):
    STORE = "scratchpad-session"
    SCOPE = "session-" + "cd34" * 8

    def setUp(self):
        super().setUp()
        self.state_root = Path(self.project_dir) / "state"
        self._env = mock.patch.dict(
            os.environ, {"CEO_STATE_ROOT": str(self.state_root)}, clear=False
        )
        self._env.start()
        self.addCleanup(self._env.stop)

    def _unlink_store_files(self):
        """What the GC does under the lock: remove db + WAL + SHM."""
        store_dir = self.state_root / self.STORE
        for suffix in (".sqlite", ".sqlite-wal", ".sqlite-shm"):
            p = store_dir / (self.SCOPE + suffix)
            try:
                p.unlink()
            except OSError:
                pass


class TestWriteSurvivesGcDeletion(GcCoordinationBase):
    def test_cached_connection_write_lands_after_gc_unlink(self):
        """THE round-10 control: a store object holding a connection opened
        BEFORE the GC unlink must still produce an on-disk write — not a
        commit into an unlinked inode."""
        store = _ss.SqliteStateStore(self.STORE, self.SCOPE)
        store.set("k1", "before-gc")
        self._unlink_store_files()
        store.set("k2", "after-gc")  # would vanish without the reopen guard
        store.close()

        fresh = _ss.SqliteStateStore(self.STORE, self.SCOPE)
        try:
            self.assertEqual(fresh.get("k2"), b"after-gc",
                             "the post-GC write never reached the disk path")
            # k1 died with the collected store — that is the GC's contract.
            self.assertIsNone(fresh.get("k1"))
        finally:
            fresh.close()

    def test_read_after_gc_unlink_is_a_clean_miss(self):
        store = _ss.SqliteStateStore(self.STORE, self.SCOPE)
        store.set("k1", "value")
        self._unlink_store_files()
        try:
            self.assertIsNone(store.get("k1"))
        finally:
            store.close()

    def test_untouched_store_roundtrips_normally(self):
        """Negative control: with no GC interference the guard must be
        invisible — same store object, same values."""
        store = _ss.SqliteStateStore(self.STORE, self.SCOPE)
        try:
            store.set("k", "v")
            self.assertEqual(store.get("k"), b"v")
        finally:
            store.close()


if __name__ == "__main__":
    unittest.main()
