#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WS-4 P0 regression: --ceremony user must PRESERVE a real adopter repo.

The empty-target test (test_install_user_no_writes_outside_claude.py) only proves
nothing is CREATED outside .claude/ into a bare dir. This test covers the actual
P0 (Codex 019e8093): a fresh `--ceremony user` install into a repo that ALREADY
HAS its own files (package.json, README.md, a CLAUDE.md full of {{...}}
placeholders, docs/guide.md, .gitignore) must leave every one of those files
BYTE-IDENTICAL — in particular the adopter's CLAUDE.md must NOT have its
{{PROJECT_NAME}} (or any {{...}}) substituted by install.sh's placeholder pass.

Convention (matches the sibling WS-4 tests + test_install_sh_session_75_flags.py):
subclass TestEnvContext from _lib/testing.py; drive scripts/install.sh via
subprocess; CEO_INSTALL_SKIP_SELF_SHA=1.

Asserts:
  - install rc == 0;
  - every pre-existing non-.claude file is byte-identical (sha256 unchanged);
  - the adopter CLAUDE.md still contains the literal `{{PROJECT_NAME}}`;
  - `.claude/` was created.
"""
from __future__ import annotations

import hashlib
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

# Pre-existing adopter files. CLAUDE.md is deliberately seeded with {{...}}
# placeholders that the maintainer ceremony WOULD substitute — under user
# ceremony they must survive verbatim.
_ADOPTER_FILES = {
    "package.json": '{\n  "name": "adopter-app",\n  "version": "1.2.3"\n}\n',
    "README.md": "# Adopter App\n\nThis is the adopter's own README. Do not touch.\n",
    "CLAUDE.md": (
        "# {{PROJECT_NAME}} - adopter context\n"
        "Owner: {{OWNER_NAME}}\n"
        "Deploy: {{DEPLOY_COMMAND}}\n"
        "This is the adopter's pre-existing CLAUDE.md and must NOT be rewritten.\n"
    ),
    os.path.join("docs", "guide.md"): "# Guide\n\nAdopter docs. {{PROJECT_NAME}} stays literal here too.\n",
    ".gitignore": "node_modules/\n*.log\n",
}


def _install_env():
    env = dict(os.environ)
    env["CEO_INSTALL_SKIP_SELF_SHA"] = "1"
    env["CEO_RAG_INSTALL_PROMPT"] = "0"
    return env


def _sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


class TestInstallUserPreservesExistingRepo(TestEnvContext):
    """--ceremony user must not create OR modify anything outside .claude/."""

    def setUp(self):
        super().setUp()
        if not os.path.isfile(INSTALL_SH):
            self.skipTest("install.sh missing")
        # If the WS-4 bundle has not been applied yet, --ceremony is unknown and
        # install.sh exits 2 on the unknown flag; skip cleanly in that case.
        with open(INSTALL_SH, "r", encoding="utf-8") as fh:
            if "WS4-ceremony-case" not in fh.read():
                self.skipTest("WS-4 --ceremony not applied to install.sh yet")

    def test_user_ceremony_preserves_adopter_files(self):
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(["git", "init", "-q", td], check=True)

            # Seed the adopter's pre-existing files (incl. a nested docs/ dir).
            for rel, content in _ADOPTER_FILES.items():
                dest = os.path.join(td, rel)
                parent = os.path.dirname(dest)
                if parent:
                    os.makedirs(parent, exist_ok=True)
                with open(dest, "w", encoding="utf-8") as fh:
                    fh.write(content)

            before = {rel: _sha256(os.path.join(td, rel)) for rel in _ADOPTER_FILES}

            res = subprocess.run(
                ["bash", INSTALL_SH, td, "--ceremony", "user"],
                cwd=_REPO_ROOT, env=_install_env(),
                capture_output=True, text=True, timeout=600,
            )
            self.assertEqual(
                res.returncode, 0,
                msg="user-ceremony install failed (rc=%d)\nSTDOUT:\n%s\nSTDERR:\n%s"
                    % (res.returncode, res.stdout, res.stderr),
            )

            # Every pre-existing file must be byte-identical afterward.
            for rel in _ADOPTER_FILES:
                dest = os.path.join(td, rel)
                self.assertTrue(os.path.isfile(dest), msg="adopter file vanished: %s" % rel)
                self.assertEqual(
                    before[rel], _sha256(dest),
                    msg="user ceremony MODIFIED a pre-existing non-.claude file: %s" % rel,
                )

            # Specifically: the adopter CLAUDE.md placeholder must survive literally.
            with open(os.path.join(td, "CLAUDE.md"), "r", encoding="utf-8") as fh:
                claude_md = fh.read()
            self.assertIn(
                "{{PROJECT_NAME}}", claude_md,
                msg="install.sh SUBSTITUTED the adopter's CLAUDE.md {{PROJECT_NAME}} "
                    "under --ceremony user (must not touch root files)",
            )

            # .claude/ must have been created.
            self.assertTrue(
                os.path.isdir(os.path.join(td, ".claude")),
                msg="user ceremony did not create .claude/",
            )


if __name__ == "__main__":
    unittest.main()
