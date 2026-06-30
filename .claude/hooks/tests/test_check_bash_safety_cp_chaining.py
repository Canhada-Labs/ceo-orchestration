#!/usr/bin/env python3
"""S207 — regression coverage for the cp-into-canonical hole in the Bash interceptor.

The E3 canonical-write matchers (cp/mv/ln/truncate/rm, sed -i, perl/ruby/awk -i) used the GLOBAL
``tokens[-1]`` as the target, so ANY shell chaining moved the real destination out of tokens[-1] and slipped
through: ``cp evil .claude/hooks/x.py && echo`` landed a file in a canonical dir undetected (this is how four
hook files were landed in S207). The fix makes target resolution SEGMENT-LOCAL (a robust ``shlex`` lexer with
``punctuation_chars`` that isolates ( ) ; < > | & ` even when adjacent), reconstructs directory landing
paths, normalises absolute paths + command basenames, and splits cp/mv/rm/truncate/touch semantics.

These tests pin the bypass closure AND the false-positive boundary (reading a canonical file, writing /tmp,
touch reference flags must stay allowed). Stdlib only, Python >= 3.9.

WIRING NOTE: lives in .claude/hooks/tests/ (not canonical-guarded) and asserts the LIVE module behaviour.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

import check_bash_safety  # noqa: E402

_REPO = str(Path(__file__).resolve().parents[3])   # …/ceo-orchestration


def _chk(cmd):
    return check_bash_safety._e3_check_canonical_path_write(cmd)


# Every command WRITES/MUTATES a canonical path → must return a deny reason.
BYPASS_BLOCK = [
    # the root-cause: shell chaining after a file-mover
    "cp evil .claude/hooks/x.py && echo done",
    "cp evil .claude/hooks/x.py || true",
    "cp evil .claude/hooks/x.py ; ls",
    "cp evil .claude/hooks/x.py | cat",
    # adjacent (un-spaced) operators
    "cp evil .claude/hooks/x.py&&echo ok",
    "mv evil .claude/hooks/x.py;echo",
    "printf x>.claude/hooks/x.py",
    # mv/rm/truncate canonical source / multi-target
    "mv .claude/hooks/x.py /tmp/x.py",
    "mv -t /tmp .claude/hooks/x.py",
    "rm .claude/hooks/x.py /tmp/other",
    "truncate -s0 .claude/hooks/x.py /tmp/other",
    # command substitution (segmented away)
    "$(cp evil .claude/hooks/x.py)",
    "echo $(cp evil .claude/hooks/x.py)",
    "`cp evil .claude/hooks/x.py`",
    # absolute / escaped command names
    "/bin/cp evil .claude/hooks/x.py",
    "/usr/bin/sed -i s/x/y/ .claude/hooks/x.py",
    "\\cp evil .claude/hooks/x.py",
    # newly-covered copy commands
    "install -m644 evil .claude/hooks/x.py",
    "rsync evil .claude/hooks/x.py",
    "ditto evil .claude/hooks/x.py",
    # directory destinations + -t target-directory
    "cp -t .claude/hooks evil.py",
    "cp --target-directory=.claude/hooks evil.py",
    "cp evil.py .claude/hooks/",
    "cp a.py b.py .claude/hooks/",
    # touch a canonical path
    "touch .claude/hooks/x.py",
    "touch .claude/hooks/x.py && echo",
    # bare forms must STILL block (no regression)
    "cp evil .claude/hooks/x.py",
    "mv evil PROTOCOL.md",
    "cat evil > .claude/hooks/x.py",
]

# Legitimate commands → must NOT false-positive (return None).
ALLOW = [
    "touch -r .claude/hooks/x.py /tmp/out",       # -r is a READ reference, not a target
    "touch -d .claude/hooks/x.py /tmp/out",       # -d consumes its value
    "cp .claude/hooks/x.py /tmp/backup.py",       # READ canonical, write /tmp
    "cp .claude/hooks/foo.py /tmp/ ; echo done",
    "cp .claude/hooks/x.py /tmp/",
    "cp a.py b.py",
    "cp a.py b.py && echo done",
    "mv /tmp/x /tmp/y",
    "rm /tmp/junk.txt && echo",
    "sed -i s/a/b/ /tmp/file.txt",
    "rsync -av src/ /tmp/dest/",
    "grep -r foo .claude/hooks/",
    "cp evil.sh .claude/hooks/",                  # .sh is NOT a .py guard → allowed
    "touch /tmp/marker",
    "git commit -m 'cp into .claude/hooks'",       # message text, not a write
    "echo hello",
]


@pytest.mark.parametrize("cmd", BYPASS_BLOCK)
def test_canonical_write_bypass_is_blocked(cmd):
    assert _chk(cmd) is not None, "expected a deny reason for: %s" % cmd


@pytest.mark.parametrize("cmd", ALLOW)
def test_legitimate_command_not_false_positive(cmd):
    assert _chk(cmd) is None, "unexpected block for: %s" % cmd


def test_absolute_canonical_path_under_repo_root(monkeypatch):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", _REPO)
    assert _chk("cd /tmp && cp evil %s/.claude/hooks/x.py" % _REPO) is not None
    assert _chk("cp evil %s/.claude/settings.json && echo" % _REPO) is not None
    # absolute path OUTSIDE the repo root is not canonical
    assert _chk("cp evil /tmp/elsewhere/.claude/hooks/x.py") is None


def test_fail_closed_on_unbalanced_quote():
    # shlex parse failure must fail-CLOSED (deny), never silently allow.
    assert _chk("cp evil 'unterminated .claude/hooks/x.py") is not None
