"""PLAN-050 Phase 5a — STAGED pytest conftest for `.claude/hooks/tests/`.

**Status: STAGED.** Target path `.claude/hooks/tests/conftest.py` is
canonical-guarded under `.claude/**/conftest.py` (ADR-031). Merge
requires sentinel extension of round-16 OR a new round covering
`conftest.py` files under `.claude/`.

## Purpose

Replace the `sys.path.insert(0, ...)` scatter in 91 test files with a
single pytest-level path fixup. After this lands + 7-day soak on
main, **Phase 5b** retires every `sys.path.insert` call across the
hook test tree.

Mirror template of `.claude/scripts/tests/conftest.py` which already
provides the same service for the scripts test tree.

## Migration contract

1. `validate.yml` must switch the hook-test step runner from
   `python3 -m unittest discover .claude/hooks/tests/` →
   `python3 -m pytest .claude/hooks/tests/ -q`. See staged patch at
   `.claude/plans/PLAN-050/staged-code/validate_yml_pytest_migration.md`.
2. Before removing any `sys.path.insert` from a test file, capture
   the `__file__`-resolved paths and assert they match after removal.
3. Ship-criterion: `grep -rn 'sys.path.insert' .claude/hooks/tests`
   returns 0 hits AND pytest + unittest discover both green.
4. Baseline hooks/tests collection = 3.4s → gate = ≤5.4s.

## Proof-of-equivalence

Before removing the first sys.path.insert:

    python3 -m pytest .claude/hooks/tests/ --collect-only -q | sort > before.txt

After the conftest lands:

    python3 -m pytest .claude/hooks/tests/ --collect-only -q | sort > after.txt
    diff before.txt after.txt  # must be empty
"""
from __future__ import annotations

import sys
from pathlib import Path

# PLAN-119 WS-A — register the suite-wide audit-dir isolation REDIRECT fixtures
# in this subtree too (defense-in-depth; idempotent — a no-op if the root
# conftest already redirected). Ensure `.claude/hooks/` is importable first so
# `_lib.test_isolation` resolves even if this conftest is imported before the
# root conftest seeds sys.path under some invocation orderings.
_HOOKS_DIR = str(Path(__file__).resolve().parent.parent)
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)
from _lib.test_isolation import (  # noqa: E402,F401
    _ceo_audit_isolation_session,
    _ceo_audit_isolation_check,
)


def pytest_collectstart(collector):  # noqa: D401
    """Ensure `.claude/hooks/` is on sys.path BEFORE any test module imports.

    Hook unit tests import modules like `check_agent_spawn`, `audit_log`,
    `_lib.output_scan`, etc. These live under `.claude/hooks/`. We add
    that directory to sys.path once here so every test module can
    `from _lib import output_scan` without a manual sys.path.insert.

    Using `pytest_collectstart` (fires before test module import) avoids
    the late-binding hazard of `pytest_configure`.
    """
    hooks_dir = Path(__file__).resolve().parent.parent
    hooks_dir_str = str(hooks_dir)
    if hooks_dir_str not in sys.path:
        sys.path.insert(0, hooks_dir_str)


# PLAN-118 AC-B7 — canonical `_lib/` path for the HMAC-trio post-collection
# snapshot guard. Resolved at conftest import time from this file's
# location (`<repo>/.claude/hooks/tests/conftest.py` → parent.parent =
# `<repo>/.claude/hooks/` → `_lib/`). Used by
# pytest_collection_finish() below to verify that no test file's
# sys.path.insert() polluted the HMAC trio before any test body runs.
_CANONICAL_HOOKS_DIR = Path(__file__).resolve().parent.parent
_CANONICAL_LIB_DIR_FOR_SNAPSHOT = _CANONICAL_HOOKS_DIR / "_lib"
_HMAC_TRIO_MODULE_NAMES = ("_lib.audit_emit", "_lib.audit_hmac", "_lib.canonical_json")


def pytest_collection_finish(session):  # noqa: D401
    """PLAN-118 AC-B7 — sys.modules snapshot guard (REQUIRED, was optional).

    Fires AFTER pytest collection completes, BEFORE any test body runs.
    For each of the HMAC trio (`_lib.audit_emit` / `_lib.audit_hmac` /
    `_lib.canonical_json`) currently in :data:`sys.modules`, reads
    ``<mod>.__file__``, resolves to absolute, asserts the parent is
    the canonical ``.claude/hooks/_lib/`` directory.

    On mismatch: ``pytest.fail()`` (NOT plain ``assert`` — assert in
    conftest can be silently caught + the file accidentally collected
    as a test item).

    This is the only layer that catches pollution sourced from a
    DIFFERENT test file's ``sys.path.insert`` BEFORE any test body
    executes. Defense-in-depth alongside:
      - audit_hmac._ensure_canonical_lib_modules (runtime fail-CLOSED
        at compute_entry_hmac entry) — catches at HMAC-emit time
      - test_lib_canonical_import.py (in-process PASS + subprocess FAIL
        regression) — catches at test-runtime

    Modules NOT yet imported at collection-finish are skipped (the
    pytest collector may import them later when their first consumer
    test loads).
    """
    import pytest  # local import — avoid top-level pytest dep in conftest

    for mod_name in _HMAC_TRIO_MODULE_NAMES:
        mod = sys.modules.get(mod_name)
        if mod is None:
            continue  # collector hasn't loaded it yet — skip
        mod_file = getattr(mod, "__file__", None)
        if mod_file is None:
            continue  # builtins / namespace — skip
        try:
            resolved_parent = Path(mod_file).resolve().parent
        except (OSError, ValueError):
            continue  # symlink loop / weird path — skip
        if resolved_parent != _CANONICAL_LIB_DIR_FOR_SNAPSHOT:
            pytest.fail(
                f"PLAN-118 AC-B7 — sys.modules pollution detected at "
                f"collection-finish: {mod_name} resolves to a non-"
                f"canonical _lib/ parent. Some test file's sys.path."
                f"insert() shadowed the canonical _lib/ before this "
                f"test session loaded the module. Hint: search for "
                f"`sys.path.insert` in .claude/hooks/tests/ + recent "
                f"PRs; the offender is a test that loads a stale `_lib` "
                f"BEFORE the canonical one. (Resolved parent + canonical "
                f"parent intentionally NOT echoed to avoid leaking "
                f"absolute paths into CI logs — verify locally.)",
                pytrace=False,
            )
