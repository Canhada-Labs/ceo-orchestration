"""PLAN-114 FIX-3 (spec_CANONCODE §F-11-11-1-g7h8i9j0) — swarm activation smoke.

Verifies that the Layer-1 env kill-switch gate responds correctly to
CEO_SWARM presence/absence, providing CI coverage that the swarm
activation path is reachable and behaves as designed.

Tests are intentionally minimal (smoke) — full gate enforcement coverage
lives in test_loop_runner_gate_enforcement.py.

No hypothesis. stdlib + pytest only (matches the rest of swarm/tests/).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Ensure .claude/scripts is on sys.path so relative imports work whether
# pytest collects this file from the repo root or from within scripts/.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_SCRIPTS_DIR = _REPO_ROOT / ".claude" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def swarm_env(tmp_path, monkeypatch):
    """Set up a minimal swarm-enabled environment in a temp directory.

    Creates .claude/swarm-enabled sentinel, sets CEO_SWARM=1 and
    CEO_SWARM_VIBECODER_ENABLED=1, and changes cwd to tmp_path.
    Restores environment on teardown (via monkeypatch).
    """
    sentinel_dir = tmp_path / ".claude"
    sentinel_dir.mkdir(parents=True)
    sentinel = sentinel_dir / "swarm-enabled"
    sentinel.touch()
    monkeypatch.setenv("CEO_SWARM", "1")
    monkeypatch.setenv("CEO_SWARM_VIBECODER_ENABLED", "1")
    monkeypatch.chdir(tmp_path)
    return {"sentinel": sentinel, "tmp_path": tmp_path}


# ---------------------------------------------------------------------------
# Layer-1 env kill-switch tests
# ---------------------------------------------------------------------------

def test_swarm_kill_switch_layer1_ceo_swarm_unset(monkeypatch):
    """Layer-1 kill switch: CEO_SWARM absent → swarm disabled (tripped=True)."""
    from swarm.coordinator import env_kill_switch_tripped
    monkeypatch.delenv("CEO_SWARM", raising=False)
    assert env_kill_switch_tripped() is True


def test_swarm_kill_switch_layer1_ceo_swarm_zero(monkeypatch):
    """Layer-1 kill switch: CEO_SWARM=0 → swarm disabled (tripped=True)."""
    from swarm.coordinator import env_kill_switch_tripped
    monkeypatch.setenv("CEO_SWARM", "0")
    assert env_kill_switch_tripped() is True


def test_swarm_kill_switch_layer1_ceo_swarm_set(swarm_env, monkeypatch):
    """Layer-1 kill switch: CEO_SWARM=1 → not tripped by layer-1 alone."""
    from swarm.coordinator import env_kill_switch_tripped
    assert env_kill_switch_tripped() is False


def test_swarm_kill_switch_layer1_disable_flag(swarm_env, monkeypatch):
    """Layer-1 kill switch: CEO_AUTONOMOUS_LOOPS_DISABLE=1 overrides CEO_SWARM=1."""
    from swarm.coordinator import env_kill_switch_tripped
    monkeypatch.setenv("CEO_AUTONOMOUS_LOOPS_DISABLE", "1")
    assert env_kill_switch_tripped() is True


# ---------------------------------------------------------------------------
# Layer-2 sentinel file kill-switch test
# ---------------------------------------------------------------------------

def test_swarm_kill_switch_layer2_sentinel_absent(tmp_path):
    """Layer-2 kill switch: sentinel file absent → tripped=False (no kill)."""
    from swarm.coordinator import sentinel_file_kill_switch_tripped
    absent = tmp_path / ".claude" / "swarm-kill"
    # File does not exist → kill switch is NOT tripped (normal operation)
    assert sentinel_file_kill_switch_tripped(absent) is False


def test_swarm_kill_switch_layer2_sentinel_present(tmp_path):
    """Layer-2 kill switch: sentinel file present → tripped=True (halt)."""
    from swarm.coordinator import sentinel_file_kill_switch_tripped
    sentinel = tmp_path / ".claude" / "swarm-kill"
    sentinel.parent.mkdir(parents=True)
    sentinel.touch()
    assert sentinel_file_kill_switch_tripped(sentinel) is True


def test_swarm_enabled_sentinel_present_layer2_not_tripped(swarm_env):
    """Layer-2 kill-switch NOT tripped when no kill file is present.

    swarm-enabled is the activation sentinel; sentinel_file_kill_switch_tripped
    checks a *separate* kill-file path. With no kill file present the
    layer-2 gate is not tripped (returns False = allow).
    """
    from swarm.coordinator import sentinel_file_kill_switch_tripped
    kill_file = swarm_env["tmp_path"] / ".claude" / "swarm-kill"
    # kill_file does not exist → not tripped
    assert sentinel_file_kill_switch_tripped(kill_file) is False
