"""install.sh smoke tests — verify a dry install produces expected layout.

scripts/install.sh does not have a `--dry-run` flag (as of PLAN-010).
Instead, we point it at a throwaway tmpdir (the ceo_env.project_dir is
already isolated) and assert the copied layout.

We do NOT execute the full install on every run — we target the fast
subset (core profile, no stack) and rely on the install flag
idempotency (re-run is safe) for the second scenario.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from .conftest import REPO_ROOT


@pytest.fixture
def fresh_target(tmp_path: Path) -> Path:
    """Fresh empty target repo for install.sh to populate."""
    target = tmp_path / "target-repo"
    target.mkdir()
    # install.sh expects the target to look like a git repo-ish dir;
    # just provide a .git placeholder for CODEOWNERS wiring hints.
    (target / ".git").mkdir()
    return target


def _run_install(target: Path, *extra_args: str, timeout: float = 90.0) -> subprocess.CompletedProcess:
    """Invoke scripts/install.sh against the target. Capture all output."""
    cmd = ["bash", str(REPO_ROOT / "scripts" / "install.sh"), str(target), *extra_args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=timeout,
    )


# --------------------------------------------------------------------------
# Scenario 1: install.sh populates target with expected structure
# --------------------------------------------------------------------------

def test_install_creates_expected_layout(fresh_target: Path):
    """After install, target has .claude/hooks, skills/core, plans schemas, ADR template."""
    result = _run_install(fresh_target, "--profile", "core")
    assert result.returncode == 0, (
        f"install.sh failed rc={result.returncode}\n"
        f"stdout={result.stdout[-2000:]}\nstderr={result.stderr[-2000:]}"
    )

    target_claude = fresh_target / ".claude"
    assert target_claude.is_dir(), "no .claude/ in target"
    # Core structural expectations (debate C5 list)
    expected_paths = [
        target_claude / "hooks" / "check_agent_spawn.py",
        target_claude / "hooks" / "audit_log.py",
        target_claude / "hooks" / "check_bash_safety.py",
        target_claude / "hooks" / "check_plan_edit.py",
        target_claude / "skills" / "core",
        target_claude / "plans" / "PLAN-SCHEMA.md",
        target_claude / "plans" / "AUDIT-LOG-SCHEMA.md",
        target_claude / "plans" / "DEBATE-SCHEMA.md",
        target_claude / "adr" / "README.md",
        target_claude / "settings.json",
    ]
    missing = [str(p.relative_to(fresh_target)) for p in expected_paths if not p.exists()]
    assert not missing, f"install missing: {missing}"


# --------------------------------------------------------------------------
# Scenario 2: install.sh is idempotent — re-running does not clobber edits
# --------------------------------------------------------------------------

def test_install_is_idempotent_and_preserves_user_edits(fresh_target: Path):
    """Re-running install.sh must not overwrite an edited CLAUDE.md."""
    r1 = _run_install(fresh_target, "--profile", "core")
    assert r1.returncode == 0, f"first install failed: {r1.stderr[-500:]}"

    claude_md = fresh_target / "CLAUDE.md"
    if not claude_md.exists():
        # install.sh only writes CLAUDE.md if missing; ensure we have
        # something to protect.
        claude_md.write_text("# user-edited content\n", encoding="utf-8")
    else:
        original = claude_md.read_text(encoding="utf-8")
        claude_md.write_text(original + "\n# USER ADDITION\n", encoding="utf-8")

    r2 = _run_install(fresh_target, "--profile", "core")
    assert r2.returncode == 0, f"second install failed: {r2.stderr[-500:]}"

    content = claude_md.read_text(encoding="utf-8")
    assert "# USER ADDITION" in content or "# user-edited" in content, (
        "install.sh clobbered CLAUDE.md — expected idempotent behavior"
    )

    # Ensure tests/ and legacy/ subdirs were NOT installed into the
    # target (install.sh excludes these per I-4).
    assert not (fresh_target / ".claude" / "hooks" / "tests").exists(), (
        "install.sh leaked hooks/tests/ into target — I-4 regression"
    )
