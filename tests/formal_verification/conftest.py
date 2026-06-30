"""Conftest for formal-verification conformance harness (PLAN-013 Phase D.8).

Bootstraps ``sys.path`` so the tests can import both ``_lib`` (from
``.claude/hooks/``) and the local ``mutation_fixtures/`` package
(historically ``mutations/``; renamed in PLAN-019 Phase 1 P0-04).

Tests run as ``python3 -m pytest tests/formal_verification/`` OR
``python3 -m unittest discover tests/formal_verification``. Both work
because every test class subclasses ``TestEnvContext`` (which itself
subclasses ``unittest.TestCase``). TestEnvContext manages env isolation
per PLAN-013 ADJ-022 (no raw monkeypatch.setenv in test bodies).

NO raw ``monkeypatch.setenv`` anywhere — TestEnvContext owns all env.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make `.claude/hooks/` importable so tests can reuse `_lib.testing`,
# `_lib.adapters.live._breaker`, and `_lib.audit_emit`.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

# Make the local package importable (for pytest auto-discovery of
# `mutation_fixtures.breaker.*` etc.). Pytest does this via rootdir+
# testpaths, but we also add the directory explicitly so
# `python3 -m unittest` works.
_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

REPO_ROOT = _REPO_ROOT
HOOKS_DIR = _HOOKS_DIR
