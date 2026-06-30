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
import tarfile
import tempfile
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "install-npm.sh"


def _have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


# Gate the entire module on npm + node availability. install-npm.sh
# exits with code 3 when either is missing; we skip instead of testing
# that error path (not the primary acceptance target for P1-QA-7).
pytestmark = pytest.mark.skipif(
    not (_have("npm") and _have("node")),
    reason="npm/node not available in PATH",
)


@pytest.fixture
def clean_npm_dir():
    """Snapshot + restore npm/ dir because install-npm.sh stages source
    files *into* npm/ and leaves them behind after a successful run.

    We don't want subsequent tests (or subsequent pytest invocations) to
    pick up stale staged content — so we capture the pre-test tarball
    list and clean anything added by the test.
    """
    npm_dir = _REPO_ROOT / "npm"
    before = set()
    if npm_dir.exists():
        before = {p.name for p in npm_dir.iterdir()}
    yield npm_dir
    if npm_dir.exists():
        # Remove any *.tgz created and any staged dirs that weren't present
        # before the test ran (scripts/, templates/, .claude/, SPEC/, etc.).
        _STAGED_NAMES = {"scripts", "templates", ".claude", "SPEC",
                         "VERSION", "LICENSE", "README.md", "PROTOCOL.md"}
        for entry in npm_dir.iterdir():
            if entry.name in before:
                continue
            if entry.suffix == ".tgz" or entry.name in _STAGED_NAMES:
                if entry.is_dir():
                    shutil.rmtree(entry, ignore_errors=True)
                else:
                    entry.unlink(missing_ok=True)


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
        proc = _run_script("--smoke", timeout=300.0)
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
