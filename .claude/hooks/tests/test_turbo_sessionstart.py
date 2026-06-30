"""Pytest wrapper for turbo_sessionstart.py selftest.

This wrapper runs turbo_sessionstart.py with --selftest flag via subprocess.
It is resilient to both pre-wiring (module in wave2/) and post-wiring
(module in .claude/hooks/) contexts.

PLAN-135 W2 H6 (STAGED, layered on the LIVE base): the subprocess selftest now also
covers the `sessionTitle` (Claude Code 2.1.152) derivation (single executing plan →
title; zero/ambiguous → no title; turbo-off still titles). This wrapper adds direct
in-process coverage of the `_active_plan_id` derivation. STAGED-ONLY per the COUPLING
RULE — it imports the staged hook, which carries the H6 sessionTitle emit; the live
branch keeps its un-augmented copy and stays green standalone.
"""
import os
import subprocess
import sys


def test_selftest():
    """Run turbo_sessionstart.py --selftest and assert rc==0."""
    # Compute hooks dir as parent of tests dir (post-wiring location).
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    hooks_dir = os.path.dirname(os.path.dirname(tests_dir))
    module_path = os.path.join(hooks_dir, "turbo_sessionstart.py")

    # Fallback to wave2 staging dir if module not at hooks location (pre-wiring).
    if not os.path.exists(module_path):
        wave2_dir = os.path.dirname(tests_dir)
        module_path = os.path.join(wave2_dir, "turbo_sessionstart.py")

    r = subprocess.run(
        [sys.executable, module_path, "--selftest"],
        capture_output=True,
    )
    assert r.returncode == 0, r.stderr.decode()


# ---- PLAN-135 W2 H6 — sessionTitle plan-id derivation (in-process) ----

def _write_plan(plans_dir, name, status):
    os.makedirs(plans_dir, exist_ok=True)
    with open(os.path.join(plans_dir, name), "w", encoding="utf-8") as f:
        f.write("---\nstatus: %s\n---\n# x\n" % status)


def test_active_plan_id_single_executing(tmp_path):
    import turbo_sessionstart
    plans = os.path.join(str(tmp_path), ".claude", "plans")
    _write_plan(plans, "PLAN-134-foo.md", "executing")
    _write_plan(plans, "PLAN-099-bar.md", "done")
    assert turbo_sessionstart._active_plan_id(str(tmp_path)) == "PLAN-134"


def test_active_plan_id_zero_executing_is_none(tmp_path):
    import turbo_sessionstart
    plans = os.path.join(str(tmp_path), ".claude", "plans")
    _write_plan(plans, "PLAN-100-a.md", "reviewed")
    assert turbo_sessionstart._active_plan_id(str(tmp_path)) is None


def test_active_plan_id_ambiguous_is_none(tmp_path):
    import turbo_sessionstart
    plans = os.path.join(str(tmp_path), ".claude", "plans")
    _write_plan(plans, "PLAN-101-a.md", "executing")
    _write_plan(plans, "PLAN-102-b.md", "executing")
    assert turbo_sessionstart._active_plan_id(str(tmp_path)) is None


def test_active_plan_id_missing_dir_is_none(tmp_path):
    import turbo_sessionstart
    assert turbo_sessionstart._active_plan_id(os.path.join(str(tmp_path), "nope")) is None


def test_active_plan_id_only_canonical_id_in_title(tmp_path):
    """The title is always the strict PLAN-NNN form, never the slug tail."""
    import turbo_sessionstart
    plans = os.path.join(str(tmp_path), ".claude", "plans")
    _write_plan(plans, "PLAN-135-anthropic-surface-harvest.md", "executing")
    assert turbo_sessionstart._active_plan_id(str(tmp_path)) == "PLAN-135"
