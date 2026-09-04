"""Smoke tests for `scripts/install-npm.sh` — PLAN-019 P1-QA-7.

The install-npm.sh script builds a local NPM tarball (`ceo-orchestration`)
and optionally smoke-tests it against a scratch target directory. This
suite verifies the build + install + shim-invoke paths without hitting
the real npm registry.

Skipped gracefully when `npm` or `node` is unavailable in the test env
(CI containers may not have a Node toolchain on every job).

Covers (≥3 tests per acceptance):

1. `install-npm.sh` (no flags) exits 0 and produces a `.tgz` tarball.
2. `install-npm.sh --smoke` runs npm install + shim invoke without errors.
3. `install-npm.sh --help` emits help banner and exits 0.
4. `install-npm.sh` rejects unknown flags (defensive arg parsing).
5. Tarball staged bundle contains expected top-level files.

All scenarios create isolated tmpdirs via pytest's `tmp_path` fixture.
No ambient env mutation; `TestEnvContext` is not required here because
the script under test takes no env dependency beyond PATH for node/npm.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys as _sys
import tarfile
import tempfile
from pathlib import Path
from typing import Dict, Set

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "install-npm.sh"

# `npm/` is a single tree shared by every worker. The fixture below is autouse,
# so under `pytest -n auto` a help/arg test could restore or delete files while
# a build/smoke worker is still staging into the same directory. Serialise both
# the script run and the restore through one cross-process lock. (The CI job
# runs `pytest tests/integration/ -v --tb=short` with no `-n`, so this guards
# the local parallel invocation.)
_sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))
from _lib.filelock import FileLock  # noqa: E402

_NPM_TREE_LOCK = Path(tempfile.gettempdir()) / "ceo-npm-tree.lock"


def _have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


# Gate the entire module on npm + node availability. install-npm.sh
# exits with code 3 when either is missing; we skip instead of testing
# that error path (not the primary acceptance target for P1-QA-7).
pytestmark = pytest.mark.skipif(
    not (_have("npm") and _have("node")),
    reason="npm/node not available in PATH",
)


@pytest.fixture(autouse=True)
def clean_npm_dir():
    """Restore ``npm/`` to its EXACT pre-test bytes.

    ``install-npm.sh`` stages source files *into* ``npm/``. It also
    OVERWRITES tracked files that were already there — ``npm/README.md``
    receives the stale staging copy and ``npm/SHA256SUMS.txt`` gets a line
    appended.

    The previous implementation snapshotted only entry NAMES and skipped
    everything already present (``if entry.name in before: continue``), so
    it was blind to MODIFICATION of existing files. A run therefore
    reverted the reviewed ``npm/README.md`` to an older version while the
    test still reported green, and left ``verify-counts.sh`` exiting 1 with
    a version-drift error — the S288 GA-F3 regression, re-entering through
    the test suite instead of through the release script.

    The contract is now stated positively (``npm/`` ends byte-identical to
    how it started) rather than as a denylist of names to delete, and the
    fixture is ``autouse`` so a test added later cannot silently opt out of
    it. Bounded by construction: ``npm/`` is ~48 KB of tracked files.
    """
    npm_dir = _REPO_ROOT / "npm"
    # Acquire BEFORE the snapshot and hold through the test and the restore.
    # Taking it only around the restore (the first version of this fixture) did
    # not serialise anything that mattered: the snapshot and every
    # `_run_script()` call still ran unlocked, so a worker could stage into
    # `npm/` while another was snapshotting or restoring it. The whole
    # snapshot -> run -> restore cycle is the critical section.
    _lock = FileLock(str(_NPM_TREE_LOCK), timeout=600.0)
    _lock.acquire()
    try:
        yield from _npm_tree_guarded(npm_dir)
    finally:
        _lock.release()


def _npm_tree_guarded(npm_dir):
    """Snapshot, hand the tree to the test, then restore it byte-for-byte."""
    # `paths_before` records EXISTENCE, `files_before` records recoverable
    # CONTENT. They are separate on purpose: a pre-existing file we cannot read
    # (mode 000, for instance) has no bytes to restore, but it must still be
    # recognised as pre-existing — folding the two together would let teardown
    # classify it as "appeared during the test" and delete a developer's file.
    paths_before: Set[Path] = set()
    files_before: Dict[Path, bytes] = {}
    dirs_before: Set[Path] = set()
    if npm_dir.exists():
        for root, _dirnames, filenames in os.walk(npm_dir):
            rootp = Path(root)
            dirs_before.add(rootp)
            for fn in filenames:
                fp = rootp / fn
                paths_before.add(fp)
                try:
                    files_before[fp] = fp.read_bytes()
                except OSError:
                    # Unreadable pre-existing file: recorded in paths_before,
                    # so it is never deleted; simply not restorable.
                    pass
    yield npm_dir
    if not npm_dir.exists():
        return
    _restore_npm_tree(npm_dir, paths_before, files_before, dirs_before)


def _restore_npm_tree(npm_dir, paths_before, files_before, dirs_before):
    """Bring ``npm/`` back to the snapshot taken before the test ran."""

    # 1. Delete every file that appeared during the test (staged sources,
    #    *.tgz, *.tgz.sha256 — the last one the old denylist never matched).
    appeared_dirs = []
    for root, _dirnames, filenames in os.walk(npm_dir):
        rootp = Path(root)
        if rootp not in dirs_before:
            appeared_dirs.append(rootp)
        for fn in filenames:
            fp = rootp / fn
            if fp not in paths_before:
                try:
                    fp.unlink()
                except OSError:
                    pass

    # 2. Remove directories that did not exist before (deepest first).
    for d in sorted(appeared_dirs, key=lambda x: len(x.parts), reverse=True):
        shutil.rmtree(d, ignore_errors=True)

    # 3. Restore any pre-existing file whose bytes the test changed. This
    #    is the half the name-based fixture was missing.
    for fp, data in files_before.items():
        try:
            if not fp.exists() or fp.read_bytes() != data:
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes(data)
        except OSError:
            pass


def _run_script(*args: str, timeout: float = 120.0, env_extra=None):
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(_SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(_REPO_ROOT),
        env=env,
    )


# ---------------------------------------------------------------------------
# Tarball build (no --smoke flag)
# ---------------------------------------------------------------------------


class TestTarballBuild:

    def test_build_succeeds_and_produces_tgz(self, clean_npm_dir):
        """`install-npm.sh` (no flags) exits 0 + leaves a `.tgz` in npm/."""
        proc = _run_script()
        assert proc.returncode == 0, (
            f"install-npm.sh failed rc={proc.returncode}\n"
            f"stdout={proc.stdout[-1000:]}\nstderr={proc.stderr[-1000:]}"
        )
        tgzs = list(clean_npm_dir.glob("*.tgz"))
        assert tgzs, f"no .tgz produced in {clean_npm_dir}"
        # Sanity: tarball must be non-empty.
        for tgz in tgzs:
            assert tgz.stat().st_size > 1024, (
                f"tarball suspiciously small: {tgz} ({tgz.stat().st_size} bytes)"
            )

    def test_tarball_contains_expected_files(self, clean_npm_dir):
        """Staged tarball must include package.json, bin/, and install.sh."""
        proc = _run_script()
        assert proc.returncode == 0, f"build failed: {proc.stderr[-500:]}"
        tgzs = sorted(clean_npm_dir.glob("*.tgz"), key=lambda p: p.stat().st_mtime)
        assert tgzs
        tarball = tgzs[-1]
        with tarfile.open(tarball, "r:gz") as tf:
            names = tf.getnames()
        # npm pack wraps everything under `package/`.
        def _has(rel: str) -> bool:
            return any(n == f"package/{rel}" or n.endswith(f"/{rel}")
                       for n in names)
        for expected in ("package.json", "bin/ceo-orch-init.js",
                         "scripts/install.sh", "README.md"):
            assert _has(expected), (
                f"tarball missing expected file: {expected}\n"
                f"tarball content sample: {names[:20]}"
            )


# ---------------------------------------------------------------------------
# Smoke test (--smoke flag — npm install + shim invoke)
# ---------------------------------------------------------------------------


class TestSmokeInvoke:

    def test_smoke_install_and_shim_help_invocation(self, clean_npm_dir):
        """`install-npm.sh --smoke` runs full install + shim invoke.

        install-npm.sh's `--smoke` path already does:
          - npm install --no-save <tarball> in a scratch tmp dir
          - npx ceo-orchestration <tmp> --profile core
        and asserts post-install artifacts. A zero exit from this flow
        exercises steps 3-5 of the P1-QA-7 acceptance spec in one shot.
        """
        # HERMETIC (S343/S344): npm_config_audit/fund/update_notifier=false keep
        # `npm install --no-save <tarball>` from calling the registry for a LOCAL
        # tarball. Measurements and the CI timeout history live in the pack
        # evidence (PLAN-186 W0, s344 npm-smoke-hermetic-v2), not here.
        # install-npm.sh is CANONICAL, so the cure lives in this env hook; the
        # follow-up for the Owner's ceremony is `--no-audit --no-fund` in the
        # script itself. `timeout=300.0` is UNCHANGED (no relaxation).
        proc = _run_script(
            "--smoke",
            timeout=300.0,
            env_extra={
                "npm_config_audit": "false",
                "npm_config_fund": "false",
                "npm_config_update_notifier": "false",
            },
        )
        assert proc.returncode == 0, (
            f"smoke run failed rc={proc.returncode}\n"
            f"stdout={proc.stdout[-2000:]}\nstderr={proc.stderr[-2000:]}"
        )
        assert "OK: smoke test passed" in proc.stdout, (
            f"smoke path did not emit success marker — stdout tail:\n"
            f"{proc.stdout[-1000:]}"
        )


# ---------------------------------------------------------------------------
# Argparse / help / unknown flags
# ---------------------------------------------------------------------------


class TestHelpAndArgs:

    def test_help_flag_exits_zero_with_usage_text(self):
        """`--help` prints usage banner and exits 0."""
        proc = _run_script("--help", timeout=10.0)
        assert proc.returncode == 0, f"--help returned {proc.returncode}"
        combined = proc.stdout + proc.stderr
        assert "Usage:" in combined or "install-npm.sh" in combined, (
            f"help banner missing — stdout={proc.stdout!r} stderr={proc.stderr!r}"
        )

    def test_short_help_flag_also_exits_zero(self):
        """`-h` short form honored per script argparse."""
        proc = _run_script("-h", timeout=10.0)
        assert proc.returncode == 0

    def test_unknown_flag_rejected(self):
        """Unknown flag → nonzero exit + error message on stderr."""
        proc = _run_script("--bogus-flag", timeout=10.0)
        assert proc.returncode != 0, "unknown flag should exit non-zero"
        assert "unknown arg" in (proc.stderr or "").lower() or \
            "unknown" in (proc.stdout or "").lower()
