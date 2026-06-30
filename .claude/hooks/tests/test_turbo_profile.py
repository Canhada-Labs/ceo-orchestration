"""Pytest wrapper for turbo_profile.py selftest.

This wrapper runs turbo_profile.py with --selftest flag via subprocess.
It is resilient to both pre-wiring (module in wave2/) and post-wiring
(module in .claude/hooks/) contexts.
"""
import os
import subprocess
import sys


def test_selftest():
    """Run turbo_profile.py --selftest and assert rc==0."""
    # Compute hooks dir as parent of tests dir (post-wiring location).
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    hooks_dir = os.path.dirname(os.path.dirname(tests_dir))
    module_path = os.path.join(hooks_dir, "turbo_profile.py")

    # Fallback to wave2 staging dir if module not at hooks location (pre-wiring).
    if not os.path.exists(module_path):
        wave2_dir = os.path.dirname(tests_dir)
        module_path = os.path.join(wave2_dir, "turbo_profile.py")

    r = subprocess.run(
        [sys.executable, module_path, "--selftest"],
        capture_output=True,
    )
    assert r.returncode == 0, r.stderr.decode()
