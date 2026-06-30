"""install.sh atomic install + rollback-on-failure smoke tests.

PLAN-019 Phase 2 Wave 2A Agent W2A-3 — covers:
  - F-CHAOS-2 / DevOps-P1-1: atomic install + trap cleanup_on_failure
  - P2-2: jq missing + --stack explicit exits rc=3 (used as the failure
    injection vector because it's the only reliable, hook-safe way to
    force install.sh to abort mid-way without destructive shell tricks)
  - DevOps-P1-1 rollback semantics: existing $TARGET/.claude/ content
    is snapshotted to mktemp tempdir and restored verbatim on failure.

The sandbox strategy:
  1. Build a jq-less PATH by symlinking only the binaries install.sh
     actually needs (bash, cp, mv, sed, grep, find, mkdir, ls, cat,
     diff, sort, mktemp, basename, dirname, readlink, chmod, wc, uniq,
     printf) — but NOT jq — into a mktemp dir.
  2. Prepopulate $TARGET/.claude/ with user data the installer must
     never destroy.
  3. Invoke install.sh with `--stack node` (explicitly supplied) under
     the jq-less PATH. This triggers build_settings -> rc=3, which
     propagates through the trap and restores the pre-install
     snapshot.
  4. Assert $TARGET/.claude/ is EXACTLY the original user data (no
     framework files leaked in).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import List

import pytest

from .conftest import REPO_ROOT


INSTALL_SH = REPO_ROOT / "scripts" / "install.sh"

# Minimum set of coreutils install.sh invokes.
# Note: install.sh preflight requires sed + git (Wave 3B P2-SEC-F); jq is
# checked later at stack-merge time (P2-2) and is our failure vector.
_SANDBOX_BINS = (
    "bash",
    "cp",
    "mv",
    "rm",
    "mkdir",
    "ls",
    "cat",
    "sed",
    "grep",
    "find",
    "sort",
    "mktemp",
    "basename",
    "dirname",
    "readlink",
    "chmod",
    "diff",
    "wc",
    "uniq",
    "printf",
    "env",
    "true",
    "false",
    "tr",
    "awk",
    "head",
    "tail",
    "git",  # Wave 3B P2-SEC-F preflight requires git (passes), jq still missing
)


def _resolve_binary(name: str) -> str:
    """Resolve a binary in the real PATH; skip the test if unavailable."""
    path = shutil.which(name)
    if not path:
        pytest.skip(f"binary '{name}' not available — cannot build sandbox PATH")
    return path


def _make_jq_less_sandbox(tmp: Path) -> Path:
    """Build a PATH directory with every binary install.sh needs EXCEPT jq."""
    bindir = tmp / "sandbox-bin"
    bindir.mkdir()
    for name in _SANDBOX_BINS:
        real = _resolve_binary(name)
        (bindir / name).symlink_to(real)
    # IMPORTANT: no jq symlink — that's the failure injection vector.
    assert not (bindir / "jq").exists()
    return bindir


def _run_install(
    target: Path,
    sandbox_bin: Path,
    extra_args: List[str],
    timeout: float = 90.0,
) -> subprocess.CompletedProcess:
    env = {
        "PATH": str(sandbox_bin),
        "HOME": str(target.parent),
        "TMPDIR": str(target.parent),
    }
    cmd = [
        str(sandbox_bin / "bash"),
        str(INSTALL_SH),
        str(target),
        *extra_args,
    ]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )


# --------------------------------------------------------------------------
# Scenario 1: failure mid-install rolls back to pre-install state
# --------------------------------------------------------------------------


def test_install_sh_rollback_on_failure(tmp_path: Path):
    """jq-missing + --stack node explicit -> rc=3, .claude/ restored verbatim."""
    sandbox_bin = _make_jq_less_sandbox(tmp_path)

    target = tmp_path / "target-repo"
    target.mkdir()
    (target / ".git").mkdir()

    # Pre-install user data that MUST survive the failed install.
    target_claude = target / ".claude"
    target_claude.mkdir()
    (target_claude / "user-data.json").write_text(
        '{"precious":"do not delete"}\n', encoding="utf-8"
    )
    (target_claude / "notes.md").write_text("# adopter notes\n", encoding="utf-8")

    before_files = sorted(p.name for p in target_claude.iterdir())

    result = _run_install(
        target,
        sandbox_bin,
        ["--stack", "node", "--profile", "core"],
    )

    # rc=3 is the P2-2 "jq missing + explicit stack" contract.
    assert result.returncode == 3, (
        f"expected rc=3 (jq-missing + --stack node), got {result.returncode}\n"
        f"stdout={result.stdout[-1500:]}\nstderr={result.stderr[-1500:]}"
    )

    # Post-rollback .claude/ must be EXACTLY the two files we placed.
    after_files = sorted(p.name for p in target_claude.iterdir())
    assert after_files == before_files, (
        f"rollback failed — expected {before_files}, got {after_files}\n"
        f"stderr tail: {result.stderr[-800:]}"
    )

    # User content intact (byte-exact).
    assert (target_claude / "user-data.json").read_text(encoding="utf-8") == (
        '{"precious":"do not delete"}\n'
    )
    assert (target_claude / "notes.md").read_text(encoding="utf-8") == (
        "# adopter notes\n"
    )

    # Stderr should include both the rollback-start and rollback-complete lines.
    assert "::error::install failed" in result.stderr, result.stderr[-500:]
    assert "::error::rollback complete" in result.stderr, result.stderr[-500:]


# --------------------------------------------------------------------------
# Scenario 2: success path never invokes rollback
# --------------------------------------------------------------------------


def test_install_sh_success_no_rollback_message(tmp_path: Path):
    """Normal install finishes cleanly with no rollback stderr."""
    target = tmp_path / "target-repo"
    target.mkdir()
    (target / ".git").mkdir()

    # Use the real PATH (has jq) — no failure injection.
    result = subprocess.run(
        ["bash", str(INSTALL_SH), str(target), "--profile", "core"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"install failed rc={result.returncode}\n"
        f"stderr={result.stderr[-800:]}"
    )
    assert "::error::install failed" not in result.stderr, (
        "rollback messaging leaked on successful install"
    )
    assert "::error::rollback complete" not in result.stderr
    # Sanity: hooks landed.
    assert (target / ".claude" / "hooks" / "check_agent_spawn.py").is_file()


# --------------------------------------------------------------------------
# Scenario 3: --dry-run never writes
# --------------------------------------------------------------------------


def test_install_sh_dry_run_leaves_target_empty(tmp_path: Path):
    """--dry-run exits 0, writes nothing to target."""
    target = tmp_path / "target-repo"
    target.mkdir()

    result = subprocess.run(
        ["bash", str(INSTALL_SH), "--dry-run", str(target), "--profile", "core"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"dry-run failed rc={result.returncode}\n"
        f"stderr={result.stderr[-800:]}"
    )
    # Target dir must remain empty (no .claude, no CLAUDE.md, etc.)
    contents = list(target.iterdir())
    assert contents == [], f"dry-run wrote to target: {contents}"

    # Preview output must mention "Dry-run complete"
    assert "Dry-run complete" in result.stdout, result.stdout[-500:]
