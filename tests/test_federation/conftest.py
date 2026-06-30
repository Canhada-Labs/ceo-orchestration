"""Test-isolation for the federation suite (PLAN-112-FOLLOWUP PHASE2).

The audit_emit spool writer keeps module-level caches (project/state dir)
and a per-process spool. A test that points the audit log at a temp dir +
flips CEO_AUDIT_SYNC_MODE (e.g. test_attck_fixtures_fpr's _RealEmitLog) can
leave a cached spool dir / leftover spool records that then drain into the
NEXT test's CEO_AUDIT_LOG_PATH — making, say, test_write_endpoints' single
audit-event assertion see a second line. This autouse fixture resets the
spool-writer module state around every federation test so the suite is
order-independent (CI collects alphabetically: test_attck before
test_write_endpoints).
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

_HOOKS = Path(__file__).resolve().parents[2] / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

_LEAKY_ENV = (
    "CEO_AUDIT_SYNC_MODE",
    "CEO_AUDIT_LOG_DIR",
    "CEO_AUDIT_LOG_PATH",
    "CEO_AUDIT_LOG_LOCK",
    "CEO_AUDIT_LOG_ERR",
)


def _reset_spool() -> None:
    try:
        from _lib import spool_writer  # type: ignore
    except Exception:
        return
    for fn in ("_reset_for_test", "_reset_caches_for_test"):
        f = getattr(spool_writer, fn, None)
        if callable(f):
            try:
                f()
            except Exception:
                pass


def _snapshot_identity_module():
    """Capture the identity module binding in BOTH sys.modules AND the
    `_lib.federation` package attribute. test_write_endpoints swaps in a JSON
    `_StubIdentityModule`; other tests import the REAL identity. Whichever a
    test installs must not bleed into the next (a `from _lib.federation import
    identity` resolves via the PACKAGE ATTRIBUTE, not sys.modules — so both
    must be restored)."""
    snap = {"sysmod": sys.modules.get("_lib.federation.identity", KeyError)}
    pkg = sys.modules.get("_lib.federation")
    snap["pkgattr"] = getattr(pkg, "identity", KeyError) if pkg else KeyError
    snap["pkg"] = pkg
    return snap


def _restore_identity_module(snap):
    if snap["sysmod"] is KeyError:
        sys.modules.pop("_lib.federation.identity", None)
    else:
        sys.modules["_lib.federation.identity"] = snap["sysmod"]
    pkg = snap.get("pkg")
    if pkg is not None:
        if snap["pkgattr"] is KeyError:
            if hasattr(pkg, "identity"):
                try:
                    delattr(pkg, "identity")
                except AttributeError:
                    pass
        else:
            pkg.identity = snap["pkgattr"]


@pytest.fixture(autouse=True)
def _federation_audit_isolation():
    saved = {k: os.environ.get(k) for k in _LEAKY_ENV}
    _id_snap = _snapshot_identity_module()
    # Clear to a clean baseline so a prior test's leaked CEO_AUDIT_SYNC_MODE /
    # log-dir cannot bleed into this one. Tests that need specific values set
    # them in their own setUp (which runs after this fixture's setup phase).
    for k in _LEAKY_ENV:
        os.environ.pop(k, None)
    # Give every federation test its OWN spool dir so a prior test's leftover
    # spool records can never push THIS test's spool over the drain threshold
    # and flush an extra audit record into its CEO_AUDIT_LOG_PATH (the
    # root cause of the cross-file test_write_endpoints failures).
    spool_dir = tempfile.mkdtemp(prefix="fed-spool-")
    os.environ["CEO_AUDIT_LOG_DIR"] = spool_dir
    _reset_spool()
    try:
        yield
    finally:
        _reset_spool()
        _restore_identity_module(_id_snap)
        shutil.rmtree(spool_dir, ignore_errors=True)
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
