"""Root conftest.py — canonical sys.path setup for pytest whole-tree.

This file closes PLAN-018 finding P0-04: running ``python3 -m pytest``
from repo root previously failed with 13 mutation-collision errors +
1 profiler isolation leak. The collisions were caused by 114 ad-hoc
``sys.path.insert(0, ...)`` call sites whose ordering under pytest was
non-deterministic, allowing the ``mutations`` package to resolve to
either ``tests/formal_verification/mutations/`` or
``.claude/hooks/tests/mutations/`` unpredictably.

Fix strategy (PLAN-019 Phase 1):

1. **Canonical sys.path seeding (this file).** Pytest imports the
   repo-root ``conftest.py`` BEFORE collecting any test file, so the
   paths we add here are visible to every subsequent test module
   regardless of the order pytest walks them.

2. **Rename collision.** ``tests/formal_verification/mutations/`` was
   renamed to ``tests/formal_verification/mutation_fixtures/`` so
   Python's import machinery can never resolve the same package name
   to two on-disk locations. ``.claude/hooks/tests/mutations/`` is
   unchanged (it's loaded via a path-based ``importlib`` loader in
   ``test_policy_mutations.py``, not via top-level package import,
   so it was never actually ambiguous on its own — the bug surfaced
   only when the formal-verification sibling shared the name).

3. **Subprocess env hygiene.** ``hook-profiler.py::_build_env`` used
   ``os.environ.copy()`` as its base, which leaked the parent
   ``$CLAUDE_PROJECT_DIR`` into the profiled subprocess. The caller
   in ``test_hook_profiler.py`` now starts from a minimal allowlist.

## Legacy sys.path.insert call sites

114 existing ``sys.path.insert(0, ...)`` calls remain in place. They
are now no-ops (the paths are already on ``sys.path`` from this
conftest), but retiring them is explicitly a Phase 2 item
(PLAN-019 §P1-QA-5), not Phase 1. Mechanical removal will happen in
a dedicated commit so the diff is reviewable.

## Why these three paths?

- ``.claude/hooks/`` — hosts ``_lib.*`` (payload, redact, testing,
  policy, audit_emit, adapters, ...) plus the ``check_*.py`` hooks
  themselves. Tests import ``from _lib.testing import TestEnvContext``
  and ``import check_plan_edit as _cpe``.

- ``.claude/scripts/`` — hosts validation/observability scripts that
  some tests import directly. Included for symmetry with the
  per-file ``sys.path.insert`` convention used across 114 test
  modules.

- repo root (``.``) — makes ``tests/formal_verification`` a proper
  top-level package discoverable by pytest rootdir collection.

Order matters: we insert at position 0 (highest priority), hooks
first so ``_lib.*`` resolves before any legacy shadow modules, then
scripts, then repo root last.

## Compatibility with ``python3 -m unittest``

``python3 -m unittest discover`` does NOT import ``conftest.py``; the
existing per-file ``sys.path.insert`` calls still serve that entry
point. That's another reason we defer mass retirement to Phase 2 —
we need to land the unittest-compatible bootstrap alternative first.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.resolve()

# Canonical sys.path additions for pytest whole-tree discovery.
# Order: hooks first (so `_lib.*` resolves), scripts second, root last.
for _rel in (".claude/hooks", ".claude/scripts", "."):
    _candidate = str((_REPO_ROOT / _rel).resolve())
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

# PLAN-119 WS-A — suite-wide audit-dir isolation REDIRECT (keystone).
# Importing these two fixtures by name registers them as autouse for the whole
# test tree (every `testpaths` root), so no test/process can resolve the LIVE
# ~/.claude audit dir and pollute the live chain. The redirect is idempotent
# across the three conftests that register it. See _lib/test_isolation.py.
from _lib.test_isolation import (  # noqa: E402,F401
    _ceo_audit_isolation_session,
    _ceo_audit_isolation_check,
)

import re as _re  # noqa: E402

# S220 — auto-mark timing/perf tests `serial` so the parallel xdist pass (-m 'not serial')
# skips them; a dedicated serial pass runs them. They assert latency/p99/p95 budgets and flake
# under parallel CPU contention. Non-perf serial cases (concurrency, real-repo reads, single-
# process-contract guards) are marked explicitly at the test (decorator / pytestmark).
_SERIAL_NODEID_RE = _re.compile(
    r"(latency|p99|p95|perf|performance|redos|budget|under_\d+m?s|completes|within_tolerance|largepayload|_1mb|_1kb|throughput|elapsed|concurren|producers|async_flush|spool_append|spool_drain|stale_lock|times_out|timeout|timing)",
    _re.IGNORECASE,
)


def pytest_collection_modifyitems(config, items):  # noqa: E302
    import pytest as _pytest
    for _item in items:
        if _SERIAL_NODEID_RE.search(_item.nodeid):
            _item.add_marker(_pytest.mark.serial)


import os as _os  # noqa: E402
import pytest as _pytest_mod  # noqa: E402


_STEERING_PREFIXES = ("CEO_", "CLAUDE_")
_STEERING_EXACT = ("HOME",)


def _is_steering_key(_k):
    return _k.startswith(_STEERING_PREFIXES) or _k in _STEERING_EXACT


@_pytest_mod.fixture(autouse=True)
def _restore_steering_env():
    """Snapshot/restore steering env vars around every test (CI hardening).

    Some tests set ``CLAUDE_PROJECT_DIR`` / ``HOME`` / ``CEO_AUDIT_*`` (via
    ``TestEnvContext`` or directly). Under xdist with an unlucky collection
    order, a value can leak into a later test that resolves a repo path via
    ``os.environ.get("CLAUDE_PROJECT_DIR", <repo_root>)`` (→ looks for real repo
    files inside an empty tmp dir) or reads the audit redirect target (→ sees a
    stale per-test home instead of the session-isolation tmpdir). This only
    reproduces in CI, where worker count differs from local. Snapshotting the
    steering vars per-test and restoring them (remove any added, restore any
    changed) makes these checks deterministic regardless of order. It does NOT
    override a value a test sets for its own duration, and the session-level
    audit isolation (``_lib/test_isolation``) still owns the baseline.
    """
    _saved = {k: v for k, v in _os.environ.items() if _is_steering_key(k)}
    yield
    for _k in [k for k in _os.environ if _is_steering_key(k) and k not in _saved]:
        _os.environ.pop(_k, None)
    for _k, _v in _saved.items():
        _os.environ[_k] = _v
