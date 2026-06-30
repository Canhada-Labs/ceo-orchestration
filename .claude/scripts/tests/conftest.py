"""PLAN-119 WS-A — pytest conftest for ``.claude/scripts/tests/`` (net-new).

This tree had **no conftest of its own** and ~398 raw ``unittest.TestCase``
subclasses (not ``TestEnvContext``) — the highest-risk unguarded test tree for
LIVE audit-log pollution (security P0-2 / qa RC-1 / Codex R1 P2). Any of them
that triggers an audit emit wrote to the real ``~/.claude`` chain.

This conftest registers the suite-wide audit-dir isolation REDIRECT fixtures
(``_lib.test_isolation``) so the session redirect covers the scripts test tree
even when pytest is invoked against it directly (e.g. the ``validate.yml``
scripts step). The redirect is idempotent across the three conftests that
register it — a no-op here if the root conftest already redirected.

Also seeds ``sys.path`` (``.claude/scripts`` + ``.claude/hooks``) for the same
reason the root conftest does, so scripts tests resolve both their own modules
and ``_lib.*`` without a per-file ``sys.path.insert``.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Seed sys.path BEFORE importing _lib.test_isolation, so this conftest is
# self-sufficient regardless of conftest import ordering.
_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent)            # .claude/scripts
_HOOKS_DIR = str(Path(__file__).resolve().parent.parent.parent / "hooks")  # .claude/hooks
for _p in (_HOOKS_DIR, _SCRIPTS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from _lib.test_isolation import (  # noqa: E402,F401
    _ceo_audit_isolation_session,
    _ceo_audit_isolation_check,
)


def pytest_collectstart(collector):  # noqa: D401
    """Ensure ``.claude/scripts`` + ``.claude/hooks`` are on sys.path BEFORE any
    scripts test module imports (mirror of the hooks-tests conftest)."""
    for _p in (_HOOKS_DIR, _SCRIPTS_DIR):
        if _p not in sys.path:
            sys.path.insert(0, _p)
