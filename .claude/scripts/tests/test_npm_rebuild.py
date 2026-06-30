"""Smoke + post-rebuild idempotency tests for scripts/npm-rebuild.sh.

Closes Session 75 Codex Finding 3 + Owner D1: npm/ is generated, not
hand-edited. The CI gate `verify-npm-bundle-sync` requires the
canonical .claude/ + npm/.claude/ to be byte-equivalent (modulo
__pycache__/.coverage exclusions).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402
REBUILD_SH = REPO_ROOT / "scripts" / "npm-rebuild.sh"
VERSION_FILE = REPO_ROOT / "VERSION"
NPM_VERSION = REPO_ROOT / "npm" / "VERSION"
NPM_PKG = REPO_ROOT / "npm" / "package.json"

# These tests shell out against the SHARED repo-level npm/ bundle (a real
# directory, not a tmp copy), so a whole-tree `pytest -n auto` run can
# co-schedule them against other npm/-touching tests and flake
# (test_dry_rebuild_is_idempotent failed 2/2 full-parallel local runs,
# green solo and green in CI's isolated scripts/tests invocation).
# S220 serial mechanism is the canonical fix for this class.
import pytest  # noqa: E402

pytestmark = pytest.mark.serial


class NpmRebuildTest(TestEnvContext):
    def test_script_executable(self) -> None:
        self.assertTrue(REBUILD_SH.is_file(), f"missing: {REBUILD_SH}")
        self.assertTrue(os.access(REBUILD_SH, os.X_OK), "npm-rebuild.sh not executable")

    def test_version_files_in_sync(self) -> None:
        """Post-rebuild invariant: VERSION == npm/VERSION == package.json.version."""
        if not (NPM_VERSION.is_file() and NPM_PKG.is_file()):
            self.skipTest("npm bundle not present in repo (release-only artifact)")
        repo_version = VERSION_FILE.read_text(encoding="utf-8").strip()
        npm_version = NPM_VERSION.read_text(encoding="utf-8").strip()
        pkg = json.loads(NPM_PKG.read_text(encoding="utf-8"))
        pkg_version = pkg["version"]
        self.assertEqual(
            repo_version, npm_version,
            f"VERSION ({repo_version}) != npm/VERSION ({npm_version}) — "
            "run: bash scripts/npm-rebuild.sh",
        )
        self.assertEqual(
            repo_version, pkg_version,
            f"VERSION ({repo_version}) != npm/package.json version ({pkg_version}) — "
            "run: bash scripts/npm-rebuild.sh",
        )

    def test_dry_rebuild_is_idempotent(self) -> None:
        """Rebuilding twice in a row produces no diff in canonical-mirrored
        sub-trees (.claude/hooks, .claude/scripts).

        Cost basis (PLAN-119-FOLLOWUP WS-1, measured S184): on a clean bundle the
        full rebuild (rsync legs <0.2s + ``npm pack --dry-run`` <5s) runs in ~2.3s.
        The dominant cost is ``npm pack`` statting the bundle tree to apply
        ``.npmignore``; a stale gitignored ``npm/.claude/plans/`` (a prior
        ``install-npm.sh`` ``cp -r`` artifact, ~250k files / 4.3 GB) used to push
        that to ~430s and time the test out on dev envs. ``npm-rebuild.sh`` now
        prunes that subtree, so the FIRST run on a polluted dev env spends a
        one-time ~30s on the ``rm`` then is fast thereafter; CI starts clean.
        The per-subprocess ``timeout=60`` is the HARD ceiling — it absorbs the
        one-time prune yet a genuine ~10x rebuild regression (or a re-leak of
        ``plans/`` into the pack) still fails (the latter also trips the
        file-count guard in npm-rebuild.sh)."""
        if not REBUILD_SH.is_file():
            self.skipTest("rebuild script missing")
        # Capture mtimes of a sample file before
        sample = REPO_ROOT / "npm" / ".claude" / "hooks" / "audit_log.py"
        if not sample.exists():
            self.skipTest("npm bundle hooks not present")

        # PLAN-119-FOLLOWUP WS-1 — PLANT cruft so the post-rebuild no-cruft
        # assertions below are NON-vacuous (adversarial-verify: a clean dest would
        # pass identically with --delete-excluded/prune removed). The rebuild must
        # actively REMOVE these. All are gitignored under npm/, self-cleaned by the
        # rebuild — no teardown needed.
        planted_pycache = REPO_ROOT / "npm" / ".claude" / "hooks" / "__pycache__"
        planted_pycache.mkdir(parents=True, exist_ok=True)
        (planted_pycache / "ws1_probe.cpython-39.pyc").write_bytes(b"\x00cruft")
        planted_plans = REPO_ROOT / "npm" / ".claude" / "plans" / "PLAN-PROBE"
        planted_plans.mkdir(parents=True, exist_ok=True)
        (planted_plans / "stale.md").write_text("ws1 prune probe\n", encoding="utf-8")

        # First rebuild (idempotent re-sync).
        proc1 = subprocess.run(
            ["bash", str(REBUILD_SH)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(proc1.returncode, 0, msg=proc1.stdout + proc1.stderr)

        # Hash hooks dir
        h1 = subprocess.check_output(
            "find npm/.claude/hooks -type f \\( -name '*.py' -o -name '*.sh' \\) "
            "! -path '*/__pycache__/*' ! -path '*/.pytest_cache/*' "
            "! -name '.coverage' ! -name '*.bak*' "
            "-exec sha256sum {} \\; | sort | sha256sum",
            shell=True, cwd=str(REPO_ROOT), text=True, timeout=30,
        ).strip()

        # Second rebuild — must be byte-identical
        proc2 = subprocess.run(
            ["bash", str(REBUILD_SH)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(proc2.returncode, 0, msg=proc2.stdout + proc2.stderr)
        h2 = subprocess.check_output(
            "find npm/.claude/hooks -type f \\( -name '*.py' -o -name '*.sh' \\) "
            "! -path '*/__pycache__/*' ! -path '*/.pytest_cache/*' "
            "! -name '.coverage' ! -name '*.bak*' "
            "-exec sha256sum {} \\; | sort | sha256sum",
            shell=True, cwd=str(REPO_ROOT), text=True, timeout=30,
        ).strip()
        self.assertEqual(h1, h2, "npm-rebuild.sh is not idempotent — second run produced different output")

        # PLAN-119-FOLLOWUP WS-1 — post-sync no-cruft path-set assertion (R-PERF5).
        # A transfer file-count would pass while stale cruft already in the dest
        # persists, so assert on the actual path-set: rsync --delete-excluded must
        # leave no __pycache__/.pyc in the mirrored dest, and the prune must have
        # removed the stale out-of-scope npm/.claude/plans/ that made `npm pack`
        # take ~430s.
        hooks_dir = REPO_ROOT / "npm" / ".claude" / "hooks"
        pycache = [str(p.relative_to(REPO_ROOT)) for p in hooks_dir.rglob("__pycache__")]
        self.assertEqual(pycache, [], f"stale __pycache__ left in npm bundle: {pycache[:5]}")
        pyc = [str(p.relative_to(REPO_ROOT)) for p in hooks_dir.rglob("*.pyc")]
        self.assertEqual(pyc, [], f"stale .pyc left in npm bundle: {pyc[:5]}")
        stale_plans = REPO_ROOT / "npm" / ".claude" / "plans"
        self.assertFalse(
            stale_plans.exists(),
            "stale out-of-scope npm/.claude/plans not pruned by npm-rebuild.sh "
            "(the ~430s npm-pack bottleneck — PLAN-119-FOLLOWUP WS-1)",
        )


if __name__ == "__main__":
    unittest.main()
