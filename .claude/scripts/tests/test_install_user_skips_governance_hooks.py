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


_GOVERNANCE_HOOKS = (
    "check_plan_edit",
    "check_arbitration_kernel",
    "check_tier_policy",
    "check_canonical_edit",
    "check_protocol_semver_cascade",
    "check_skill_patch_sentinel",
    "check_scratchpad_access",
    "check_skill_reference_read",
    "check_skill_bootstrap_post",
    "check_bash_canonical_forensic",
)
_KEEP_HOOKS = (
    "check_agent_spawn",
    "check_bash_safety",
    "audit_log",
    "UserPromptSubmit",
)


class TestInstallUserSkipsGovernanceHooks(TestEnvContext):
    """User settings.json omits the 10 governance/sentinel/kernel hooks but KEEPS
    the advisory/safety hooks + core spawn/audit + the UserPromptSubmit optimizer."""

    def test_install_user_skips_governance_hooks(self):
        with tempfile.TemporaryDirectory() as target:
            cp = _run_install(target, "--ceremony", "user")
            self.assertEqual(cp.returncode, 0, msg=cp.stderr + cp.stdout)
            with open(os.path.join(target, ".claude", "settings.json")) as fh:
                settings = json.load(fh)
            cmds = " ".join(_all_commands(settings))
            for gov in _GOVERNANCE_HOOKS:
                self.assertNotIn(
                    gov + ".py", cmds,
                    msg="governance hook %s should NOT be registered for user" % gov,
                )
            for keep in _KEEP_HOOKS:
                self.assertIn(
                    keep + ".py", cmds,
                    msg="hook %s should be registered for user" % keep,
                )


if __name__ == "__main__":
    unittest.main()
