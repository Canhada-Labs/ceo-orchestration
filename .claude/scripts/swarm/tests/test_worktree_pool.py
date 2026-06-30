"""PLAN-050 Phase 7b (C4) — worktree pool tests.

Uses a real ephemeral git repo in tmp_path to exercise the full
subprocess path. Fast because commits are tiny (1 file, 1 line).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from .._worktree_pool import (
    WorktreePool,
    WorktreePoolError,
    WorktreeSlot,
)


# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------
@pytest.fixture
def ephemeral_repo(tmp_path: Path) -> Path:
    """Create a minimal git repo at tmp_path and return its root."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@test"], check=True
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "test"], check=True
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "commit.gpgsign", "false"], check=True
    )
    (repo / "seed.txt").write_text("seed\n")
    subprocess.run(["git", "-C", str(repo), "add", "seed.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", "seed"], check=True
    )
    return repo


# -----------------------------------------------------------------------
# Validation
# -----------------------------------------------------------------------
def test_init_rejects_non_positive_size(ephemeral_repo: Path) -> None:
    with pytest.raises(ValueError):
        WorktreePool(base_repo=ephemeral_repo, size=0)
    with pytest.raises(ValueError):
        WorktreePool(base_repo=ephemeral_repo, size=-1)


def test_init_rejects_non_git_base(tmp_path: Path) -> None:
    not_a_repo = tmp_path / "not_a_repo"
    not_a_repo.mkdir()
    pool = WorktreePool(base_repo=not_a_repo, size=1)
    with pytest.raises(WorktreePoolError, match="not a git"):
        pool.init()


# -----------------------------------------------------------------------
# Happy path
# -----------------------------------------------------------------------
def test_init_creates_n_worktrees(ephemeral_repo: Path) -> None:
    with WorktreePool(base_repo=ephemeral_repo, size=3) as pool:
        assert pool.free_slots() == 3
        assert pool.pool_dir.is_dir()
        for i in range(3):
            wt = pool.pool_dir / f"loop-{i}"
            assert wt.is_dir()
            assert (wt / "seed.txt").is_file()


def test_acquire_returns_unique_paths(ephemeral_repo: Path) -> None:
    with WorktreePool(base_repo=ephemeral_repo, size=2) as pool:
        p1 = pool.acquire("L1")
        p2 = pool.acquire("L2")
        assert p1 != p2
        assert pool.free_slots() == 0
        assert pool.busy_slots() == {"L1": p1, "L2": p2}


def test_acquire_exhausted_raises(ephemeral_repo: Path) -> None:
    with WorktreePool(base_repo=ephemeral_repo, size=1) as pool:
        pool.acquire("L1")
        with pytest.raises(WorktreePoolError, match="exhausted"):
            pool.acquire("L2")


def test_release_frees_slot(ephemeral_repo: Path) -> None:
    with WorktreePool(base_repo=ephemeral_repo, size=2) as pool:
        p = pool.acquire("L1")
        assert pool.free_slots() == 1
        pool.release(p)
        assert pool.free_slots() == 2


def test_release_resets_dirty_worktree(ephemeral_repo: Path) -> None:
    """Release must leave the worktree at HEAD."""
    with WorktreePool(base_repo=ephemeral_repo, size=1) as pool:
        p = pool.acquire("L1")
        # Pollute with uncommitted change + untracked file.
        (p / "seed.txt").write_text("mutated!\n")
        (p / "trash.txt").write_text("ignored\n")
        pool.release(p)
        assert (p / "seed.txt").read_text() == "seed\n"
        assert not (p / "trash.txt").exists()


def test_release_unknown_path_raises(ephemeral_repo: Path) -> None:
    with WorktreePool(base_repo=ephemeral_repo, size=1) as pool:
        pool.acquire("L1")
        with pytest.raises(WorktreePoolError, match="unknown worktree"):
            pool.release(Path("/tmp/nowhere"))


def test_double_release_is_noop(ephemeral_repo: Path) -> None:
    with WorktreePool(base_repo=ephemeral_repo, size=1) as pool:
        p = pool.acquire("L1")
        pool.release(p)
        # Second release on the same path returns cleanly.
        pool.release(p)
        assert pool.free_slots() == 1


def test_acquire_before_init_raises(ephemeral_repo: Path) -> None:
    pool = WorktreePool(base_repo=ephemeral_repo, size=1)
    with pytest.raises(WorktreePoolError, match="not initialized"):
        pool.acquire("L1")


def test_teardown_removes_all_worktrees(ephemeral_repo: Path) -> None:
    pool = WorktreePool(base_repo=ephemeral_repo, size=2)
    pool.init()
    worktree_paths = [s.path for s in pool._slots]
    for p in worktree_paths:
        assert p.is_dir()
    pool.teardown()
    for p in worktree_paths:
        assert not p.exists(), f"worktree {p} survived teardown"


def test_teardown_idempotent(ephemeral_repo: Path) -> None:
    pool = WorktreePool(base_repo=ephemeral_repo, size=1)
    pool.init()
    pool.teardown()
    pool.teardown()  # No raise; second call is NOOP.


def test_init_idempotent(ephemeral_repo: Path) -> None:
    pool = WorktreePool(base_repo=ephemeral_repo, size=1)
    pool.init()
    pool.init()  # Second call returns cleanly.
    assert pool.free_slots() == 1
    pool.teardown()


def test_context_manager_init_and_teardown(ephemeral_repo: Path) -> None:
    with WorktreePool(base_repo=ephemeral_repo, size=1) as pool:
        assert pool.free_slots() == 1
    # After the with-block, slots are torn down.
    assert pool._slots == []


def test_reuse_after_release(ephemeral_repo: Path) -> None:
    """Per C4: slots are reused across acquire/release cycles."""
    with WorktreePool(base_repo=ephemeral_repo, size=1) as pool:
        p1 = pool.acquire("L1")
        pool.release(p1)
        p2 = pool.acquire("L2")
        # Same slot, reused.
        assert p1 == p2


# -----------------------------------------------------------------------
# WorktreeSlot dataclass sanity
# -----------------------------------------------------------------------
def test_worktree_slot_defaults() -> None:
    s = WorktreeSlot(path=Path("/tmp/x"))
    assert s.busy_with is None
    assert s.path == Path("/tmp/x")


# -----------------------------------------------------------------------
# F-11-11-4: atexit + SIGTERM cleanup
# -----------------------------------------------------------------------
def test_atexit_registered_on_init(ephemeral_repo: Path) -> None:
    """atexit cleanup is registered when pool is initialized."""
    pool = WorktreePool(base_repo=ephemeral_repo, size=1)
    pool.init()
    # After init, teardown idempotently; no error expected.
    pool.teardown()
    # No exception = pass.


def test_cleanup_on_exit_idempotent(ephemeral_repo: Path) -> None:
    """_cleanup_on_exit is safe to call on an un-initialized pool."""
    pool = WorktreePool(base_repo=ephemeral_repo, size=1)
    # Must not raise even before init()
    pool._cleanup_on_exit()
    # Also safe after init+teardown
    pool.init()
    pool.teardown()
    pool._cleanup_on_exit()  # second call must also be safe


def test_sigterm_handler_chains_to_prior_handler(ephemeral_repo: Path) -> None:
    """SIGTERM handler restores + chains to the handler installed before the
    pool hooked SIGTERM, instead of clobbering it to SIG_DFL (Codex P2)."""
    import signal as _signal

    calls = {"prior": 0}

    def _prior(signum, frame):  # noqa: ANN001
        calls["prior"] += 1

    original = _signal.signal(_signal.SIGTERM, _prior)
    try:
        pool = WorktreePool(base_repo=ephemeral_repo, size=1)
        pool.init()
        # init() captured _prior as the previous handler.
        assert pool._prev_sigterm is _prior, "prior SIGTERM handler not captured"
        # Invoke the pool handler directly (prev is callable → chains, no raise).
        pool._sigterm_handler(_signal.SIGTERM, None)
        assert calls["prior"] == 1, "prior SIGTERM handler was not chained to"
        # And SIGTERM is restored to the prior handler, not SIG_DFL.
        assert _signal.getsignal(_signal.SIGTERM) is _prior
        pool.teardown()
    finally:
        _signal.signal(_signal.SIGTERM, original)


def test_sigterm_handler_honours_prior_sig_ign(ephemeral_repo: Path) -> None:
    """If SIGTERM was SIG_IGN before the pool, the handler restores SIG_IGN and
    does NOT terminate (no re-raise)."""
    import signal as _signal

    original = _signal.signal(_signal.SIGTERM, _signal.SIG_IGN)
    try:
        pool = WorktreePool(base_repo=ephemeral_repo, size=1)
        pool.init()
        assert pool._prev_sigterm == _signal.SIG_IGN
        # Must return without raising (honours the ignore policy).
        pool._sigterm_handler(_signal.SIGTERM, None)
        assert _signal.getsignal(_signal.SIGTERM) == _signal.SIG_IGN
        pool.teardown()
    finally:
        _signal.signal(_signal.SIGTERM, original)
