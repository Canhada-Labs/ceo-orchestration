#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PLAN-122 WS-4 — install-ceremony tests.

Convention (matches test_install_sh_session_75_flags.py): subclass TestEnvContext
from _lib/testing.py; drive scripts/install.sh via subprocess; CEO_INSTALL_SKIP_SELF_SHA=1.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
# .claude/scripts/tests -> repo root (3 dirs up)
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, os.pardir, os.pardir, os.pardir))
INSTALL_SH = os.path.join(_REPO_ROOT, "scripts", "install.sh")

# TestEnvContext lives under .claude/hooks
sys.path.insert(0, os.path.join(_REPO_ROOT, ".claude", "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402


def _install_env():
    env = dict(os.environ)
    env["CEO_INSTALL_SKIP_SELF_SHA"] = "1"
    env["CEO_RAG_INSTALL_PROMPT"] = "0"
    return env


def _run_install(target, *extra):
    cmd = ["bash", INSTALL_SH, target] + list(extra)
    return subprocess.run(
        cmd, cwd=_REPO_ROOT, env=_install_env(),
        capture_output=True, text=True, timeout=600,
    )


def _run_validate(target):
    vg = os.path.join(target, ".claude", "scripts", "validate-governance.sh")
    return subprocess.run(
        ["bash", vg], cwd=target, capture_output=True, text=True, timeout=600,
    )


def _all_commands(settings):
    out = []
    for _ev, arr in (settings.get("hooks") or {}).items():
        for block in arr:
            for h in block.get("hooks", []):
                out.append(h.get("command", ""))
    return out


class TestInstallDispatcherPresentMaintainer(TestEnvContext):
    """Regression: default (maintainer) install also ships the dispatcher (E6-F5)."""

    def test_install_dispatcher_present_maintainer(self):
        with tempfile.TemporaryDirectory() as target:
            cp = _run_install(target)  # maintainer default
            self.assertEqual(cp.returncode, 0, msg=cp.stderr + cp.stdout)
            disp = os.path.join(target, ".claude", "dispatcher")
            for fn in ("routing-matrix.yaml", "routing-matrix-loader.py"):
                self.assertTrue(
                    os.path.isfile(os.path.join(disp, fn)),
                    msg="missing dispatcher file: %s" % fn,
                )
            vg = _run_validate(target)
            self.assertEqual(vg.returncode, 0, msg=vg.stdout + vg.stderr)


if __name__ == "__main__":
    unittest.main()
